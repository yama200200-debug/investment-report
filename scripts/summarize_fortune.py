#!/usr/bin/env python3
"""fortune_validation.json を統計集計し、通常日との差をランダム化検定する。

固定ルール:
- 対象は event_type × FRED series × horizon(1D/5D/20D) の60検定。
- 同日イベントは event 種別ごとに別集計する。
- イベント実績は fortune_validation.json を読むだけで、同ファイルは変更しない。
- 通常日の比較対象は、同じイベント種別・系列・期間・営業日カウント規則で作る。
- イベント日を含む同期間の候補日から、イベント件数と同数の日付を無作為抽出して
  イベント群ラベルを入れ替える permutation test を10,000回行う。
- p値は両側、(極端以上の回数 + 1) / (試行回数 + 1)。
- Bonferroni補正は全60検定に対して行う。
- null は集計から除外し、n を明示する。
- 乱数シードは固定し、同じ入力なら同じ結果になるようにする。
"""
import hashlib
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median

VALIDATION = Path("research-data/validation/fortune_validation.json")
OUT = Path("research-data/validation/fortune_validation_summary.json")
HORIZONS = (1, 5, 20)
SERIES = (
    ("NIKKEI225", "日経平均"),
    ("SP500", "S&P500"),
    ("VIXCLS", "VIX"),
    ("DEXJPUS", "USDJPY(円/ドル)"),
    ("DCOILWTICO", "WTI原油"),
)
EVENT_TYPES = (
    "new_moon",
    "full_moon",
    "mercury_retrograde_start",
    "mercury_retrograde_end",
)
RANDOMIZATION_ITERATIONS = 10_000
RANDOM_SEED = 20261003
BONFERRONI_TESTS = len(EVENT_TYPES) * len(SERIES) * len(HORIZONS)


def load_json_list(path):
    if not path.exists():
        print(f"ERROR: {path} がありません")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print(f"ERROR: {path} が配列ではありません")
        sys.exit(1)
    return data


def fetch_series(series_id, key):
    q = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": "2000-01-01",
    })
    url = "https://api.stlouisfed.org/fred/series/observations?" + q
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))

    obs = []
    for item in data.get("observations", []):
        value = item.get("value")
        if value in (None, "", "."):
            continue
        try:
            obs.append((item["date"], float(value)))
        except (KeyError, TypeError, ValueError):
            continue
    obs.sort()
    return obs


def return_for_target(target_date, obs_dates, obs_vals, horizon):
    """validate_fortune.py と同じ base_prev_close_v1 で対象日からの騰落率を計算。"""
    if not obs_dates or obs_dates[-1] < target_date:
        return None

    base_idx = bisect_left(obs_dates, target_date) - 1
    if base_idx < 0:
        return None

    future_idx = base_idx + horizon
    if future_idx >= len(obs_vals):
        return None

    base = obs_vals[base_idx]
    if base == 0:
        return None
    return (obs_vals[future_idx] / base - 1.0) * 100.0


def stable_seed(key):
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (RANDOM_SEED + int.from_bytes(digest[:8], "big")) % (2**63)


def permutation_p_value(event_values, normal_values, key):
    """同期間の候補日にイベント群ラベルを入れ替える両側 permutation test。"""
    n_event = len(event_values)
    if n_event == 0 or not normal_values:
        return None

    pooled = event_values + normal_values
    observed_diff = fmean(event_values) - fmean(normal_values)
    pooled_mean = fmean(pooled)

    total = len(pooled)
    n_normal = total - n_event
    if n_normal <= 0:
        return None

    rng = random.Random(stable_seed(key))
    extreme = 0

    for _ in range(RANDOMIZATION_ITERATIONS):
        chosen = rng.sample(pooled, n_event)
        chosen_mean = fmean(chosen)
        complement_mean = (pooled_mean * total - chosen_mean * n_event) / n_normal
        diff = chosen_mean - complement_mean
        if abs(diff) >= abs(observed_diff):
            extreme += 1

    return (extreme + 1) / (RANDOMIZATION_ITERATIONS + 1)


def positive_rate(values):
    if not values:
        return None
    return sum(v > 0 for v in values) / len(values)


def build_normal_pool(start_date, end_date, event_dates, obs_dates, obs_vals, horizon):
    """同じ期間のFRED実観測日（営業日）だけを通常日として使う。"""
    event_date_set = set(event_dates)
    lo = bisect_left(obs_dates, start_date)
    hi = bisect_right(obs_dates, end_date)
    values = []
    for target in obs_dates[lo:hi]:
        if target in event_date_set:
            continue
        value = return_for_target(target, obs_dates, obs_vals, horizon)
        if value is not None:
            values.append((target, value))
    return values


def main():
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        print("ERROR: FRED_API_KEY が設定されていません")
        sys.exit(1)

    rows = load_json_list(VALIDATION)

    grouped = {
        event: {sid: [] for sid, _ in SERIES}
        for event in EVENT_TYPES
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        event = row.get("event")
        sid = row.get("series_id")
        if event in grouped and sid in grouped[event]:
            grouped[event][sid].append(row)

    series_obs = {}
    for sid, label in SERIES:
        obs = fetch_series(sid, key)
        if not obs:
            print(f"WARN: {sid} のFREDデータが取得できませんでした")
            series_obs[sid] = (label, [], [])
        else:
            series_obs[sid] = (label, [d for d, _ in obs], [v for _, v in obs])
        time.sleep(0.5)

    comparisons = []

    for event in EVENT_TYPES:
        for sid, label in SERIES:
            event_rows = grouped[event][sid]
            _, obs_dates, obs_vals = series_obs[sid]

            for horizon in HORIZONS:
                values_by_date = {}
                for row in event_rows:
                    value = row.get(f"ret_{horizon}d_pct")
                    event_date = row.get("event_date_utc")
                    if (
                        event_date
                        and isinstance(value, (int, float))
                        and value is not None
                    ):
                        values_by_date[event_date] = float(value)

                event_values = list(values_by_date.values())
                event_dates = list(values_by_date.keys())

                normal_pairs = []
                if event_dates and obs_dates:
                    start_date = min(event_dates)
                    end_date = max(event_dates)
                    normal_pairs = build_normal_pool(
                        start_date,
                        end_date,
                        event_dates,
                        obs_dates,
                        obs_vals,
                        horizon,
                    )

                normal_values = [v for _, v in normal_pairs]
                p_value = None
                if event_values and normal_values:
                    p_value = permutation_p_value(
                        event_values,
                        normal_values,
                        f"{event}|{sid}|{horizon}",
                    )

                event_mean = fmean(event_values) if event_values else None
                normal_mean = fmean(normal_values) if normal_values else None
                difference = (
                    event_mean - normal_mean
                    if event_mean is not None and normal_mean is not None
                    else None
                )
                adjusted = (
                    min(p_value * BONFERRONI_TESTS, 1.0)
                    if p_value is not None
                    else None
                )

                comparisons.append({
                    "event": event,
                    "series_id": sid,
                    "series_name": label,
                    "horizon_days": horizon,
                    "event_count": len(event_values),
                    "normal_day_count": len(normal_values),
                    "eligible_comparison_dates": len(normal_pairs) + len(event_dates),
                    "event_mean_pct": round(event_mean, 6) if event_mean is not None else None,
                    "event_median_pct": round(median(event_values), 6) if event_values else None,
                    "event_positive_rate": round(positive_rate(event_values), 6) if event_values else None,
                    "normal_day_mean_pct": round(normal_mean, 6) if normal_mean is not None else None,
                    "normal_day_median_pct": round(median(normal_values), 6) if normal_values else None,
                    "normal_day_positive_rate": round(positive_rate(normal_values), 6) if normal_values else None,
                    "difference_mean_pct": round(difference, 6) if difference is not None else None,
                    "p_value_two_sided": round(p_value, 8) if p_value is not None else None,
                    "bonferroni_p_value": round(adjusted, 8) if adjusted is not None else None,
                    "bonferroni_significant_0_05": (
                        adjusted <= 0.05 if adjusted is not None else None
                    ),
                })

    output = {
        "schema_version": 1,
        "source": "research-data/validation/fortune_validation.json",
        "validation_rule": "base_prev_close_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statistics": {
            "event_types": list(EVENT_TYPES),
            "series_count": len(SERIES),
            "horizons_days": list(HORIZONS),
            "planned_test_count": BONFERRONI_TESTS,
            "randomization_iterations": RANDOMIZATION_ITERATIONS,
            "random_seed": RANDOM_SEED,
            "p_value_method": "two-sided permutation test; (extreme_count + 1) / (iterations + 1)",
            "permutation_unit": "event dates are reassigned as whole dates within the same event-type/series/horizon comparison period",
            "normal_day_rule": "same calendar period; only FRED observation dates are eligible; event dates excluded; returns use the same previous-observation base and subsequent-observation counting rule as base_prev_close_v1",
            "bonferroni_method": "p_adjusted = min(p_value * 60, 1.0)",
        },
        "comparisons": comparisons,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"完了: {OUT} ({len(comparisons)}検定枠)")


if __name__ == "__main__":
    main()
