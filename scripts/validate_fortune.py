#!/usr/bin/env python3
"""fortune_records.json のイベントについて、イベント後の市場騰落率(1D/5D/20D)を計算して
research-data/validation/fortune_validation.json に保存する。

固定ルール(rule_version = base_prev_close_v1。結果を見てから変更しない):
  - 対象イベント: tolerance_trading_days が 0 で、target_date_start と target_date_end が同じレコード
  - 基準: イベント日(UTC日付)より前の最後の営業日の終値
  - 1D/5D/20D: 基準から1/5/20営業日後の終値との騰落率(%)。営業日は各系列自身の観測日で数える
  - 保存するのは騰落率だけ。価格の系列は保存しない
  - イベント日をカバーする観測がまだ無い間は、行を作らない(基準日が確定しないため)
  - 20営業日後がまだ無い行は、該当の値を null にして、次回以降の実行で埋める。埋まった値は変更しない
環境変数 FRED_API_KEY が必要(キーは表示しない)。
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path

RECORDS = Path("research-data/fortune/fortune_records.json")
OUT = Path("research-data/validation/fortune_validation.json")
JST = timezone(timedelta(hours=9))
RULE_VERSION = "base_prev_close_v1"
HORIZONS = (1, 5, 20)
SERIES = [
    ("NIKKEI225", "日経平均"),
    ("SP500", "S&P500"),
    ("VIXCLS", "VIX"),
    ("DEXJPUS", "USDJPY(円/ドル)"),
    ("DCOILWTICO", "WTI原油"),
]


def fetch_series(series_id, key):
    q = urllib.parse.urlencode({
        "series_id": series_id, "api_key": key, "file_type": "json",
        "observation_start": "2000-01-01",
    })
    url = "https://api.stlouisfed.org/fred/series/observations?" + q
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    obs = []
    for o in data.get("observations", []):
        v = o.get("value")
        if v in (None, "", "."):
            continue
        try:
            obs.append((o["date"], float(v)))
        except ValueError:
            continue
    obs.sort()
    return obs


def compute_row(record, obs_dates, obs_vals):
    """戻り値: dict(基準日と騰落率) / 基準日が確定しないとき None"""
    ev_date = record["target_date_start"]
    if not obs_dates or obs_dates[-1] < ev_date:
        return None  # イベント日をカバーする観測がまだ無い
    base_idx = bisect_left(obs_dates, ev_date) - 1  # ev_date より前の最後の観測
    if base_idx < 0:
        return None  # 系列の開始より前のイベント
    base = obs_vals[base_idx]
    if base == 0:
        return None
    row = {"base_date": obs_dates[base_idx]}
    for n in HORIZONS:
        i = base_idx + n
        row[f"ret_{n}d_pct"] = round((obs_vals[i] / base - 1.0) * 100.0, 4) if i < len(obs_vals) else None
    return row


def is_complete(row):
    return all(row.get(f"ret_{n}d_pct") is not None for n in HORIZONS)


def load_json_list(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))  # 壊れていたら例外で停止
    if not isinstance(data, list):
        print(f"ERROR: {path} が配列ではありません")
        sys.exit(1)
    return data


def main():
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        print("ERROR: FRED_API_KEY が設定されていません")
        sys.exit(1)

    records = [
        r for r in load_json_list(RECORDS)
        if isinstance(r, dict) and r.get("record_type") == "event"
        and r.get("tolerance_trading_days", 0) == 0
        and r.get("target_date_start") and r.get("target_date_start") == r.get("target_date_end")
    ]
    if not records:
        print("対象イベントがありません")
        return

    rows = load_json_list(OUT)
    index = {(r.get("record_id"), r.get("series_id")): i for i, r in enumerate(rows) if isinstance(r, dict)}
    computed_at = datetime.now(JST).isoformat(timespec="seconds")
    created = updated = 0

    for sid, label in SERIES:
        obs = fetch_series(sid, key)
        if not obs:
            print(f"WARN: {sid} のデータが取得できませんでした。スキップします")
            continue
        dates = [d for d, _ in obs]
        vals = [v for _, v in obs]
        for rec in records:
            k = (rec["record_id"], sid)
            old = rows[index[k]] if k in index else None
            if old is not None and is_complete(old):
                continue  # 確定済みは変更しない
            res = compute_row(rec, dates, vals)
            if res is None:
                continue
            new = {
                "schema_version": 1,
                "record_id": rec["record_id"],
                "event": rec.get("event"),
                "event_date_utc": rec["target_date_start"],
                "series_id": sid,
                "series_name": label,
                "rule_version": RULE_VERSION,
                "computed_at": computed_at,
                **res,
            }
            if old is None:
                rows.append(new)
                index[k] = len(rows) - 1
                created += 1
            else:
                if any(old.get(f"ret_{n}d_pct") != new.get(f"ret_{n}d_pct") for n in HORIZONS):
                    rows[index[k]] = new
                    updated += 1
        time.sleep(0.5)

    if created == 0 and updated == 0:
        print(f"変更なし(既存 {len(rows)}行)")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    done = sum(1 for r in rows if is_complete(r))
    print(f"新規 {created}行、更新 {updated}行(累計 {len(rows)}行、確定 {done}行)")


if __name__ == "__main__":
    main()
