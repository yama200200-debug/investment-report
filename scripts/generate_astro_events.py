#!/usr/bin/env python3
"""天文計算で占術イベントの日付を生成し research-data/fortune/fortune_records.json に追記する。
記録するのは「イベントの事実(日時)」のみ。株価への影響などの解釈は保存しない。
イベント: new_moon / full_moon / mercury_retrograde_start / mercury_retrograde_end
使い方: python scripts/generate_astro_events.py [開始年] [終了年]   (既定 2015 2027)
外部サイトには一切アクセスしない。依存: ephem
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ephem

OUT = Path("research-data/fortune/fortune_records.json")
JST = timezone(timedelta(hours=9))
CLASSIFIER_VERSION = "astro_v1"


def to_dt(ed):
    """ephem.Date -> aware datetime (UTC)"""
    return ed.datetime().replace(tzinfo=timezone.utc, microsecond=0)


def merc_lon(d):
    """水星の地心見かけ黄経(度)"""
    m = ephem.Mercury()
    m.compute(d, epoch=d)
    return float(ephem.Ecliptic(m, epoch=d).lon) * 180.0 / 3.141592653589793


def daily_delta(d):
    """前後12時間の黄経差(-180..180)。負なら逆行中"""
    a = merc_lon(ephem.Date(d - 0.5))
    b = merc_lon(ephem.Date(d + 0.5))
    diff = (b - a + 180.0) % 360.0 - 180.0
    return diff


def refine_station(lo, hi):
    """lo(符号A)とhi(符号B)の間で符号が変わる時刻を二分法で求める(約1分精度)"""
    s_lo = daily_delta(lo) < 0
    for _ in range(25):
        mid = (lo + hi) / 2.0
        if (daily_delta(mid) < 0) == s_lo:
            lo = mid
        else:
            hi = mid
    return ephem.Date((lo + hi) / 2.0)


def moon_events(start, end):
    ev = []
    d = ephem.Date(start)
    while True:
        n = ephem.next_new_moon(d)
        if n.datetime().replace(tzinfo=timezone.utc) >= end:
            break
        d = n
        ev.append(("new_moon", "New Moon", to_dt(n)))
    d = ephem.Date(start)
    while True:
        f = ephem.next_full_moon(d)
        if f.datetime().replace(tzinfo=timezone.utc) >= end:
            break
        d = f
        ev.append(("full_moon", "Full Moon", to_dt(f)))
    return ev


def mercury_events(start, end):
    ev = []
    d = ephem.Date(start)
    last = daily_delta(d) < 0
    stop = ephem.Date(end)
    while d < stop:
        nxt = ephem.Date(d + 1.0)
        cur = daily_delta(nxt) < 0
        if cur != last:
            t = refine_station(float(d), float(nxt))
            if cur:  # 順行 -> 逆行
                ev.append(("mercury_retrograde_start", "Mercury stations retrograde", to_dt(t)))
            else:
                ev.append(("mercury_retrograde_end", "Mercury stations direct", to_dt(t)))
        last = cur
        d = nxt
    return ev


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2027
    start = datetime(y0, 1, 1, tzinfo=timezone.utc)
    end = datetime(y1 + 1, 1, 1, tzinfo=timezone.utc)

    events = moon_events(start, end) + mercury_events(start - timedelta(days=2), end)
    events = [e for e in events if start <= e[2] < end]
    events.sort(key=lambda e: (e[2], e[0]))

    if OUT.exists():
        records = json.loads(OUT.read_text(encoding="utf-8"))  # 壊れていたら例外で停止
        if not isinstance(records, list):
            print("ERROR: fortune_records.json が配列ではありません")
            sys.exit(1)
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        records = []

    seen = {r.get("record_id") for r in records if isinstance(r, dict)}
    generated_at = datetime.now(JST).isoformat(timespec="seconds")
    added = 0
    for code, headline, t in events:
        rid = f"astro-{code}-{t.strftime('%Y%m%dT%H%MZ')}"
        if rid in seen:
            continue
        records.append({
            "schema_version": 2,
            "record_id": rid,
            "record_type": "event",
            "source": "ephem_computed",
            "source_role": "computed_event",
            "entry_method": "computed",
            "method": "astronomical_calculation",
            "target_date_start": t.strftime("%Y-%m-%d"),
            "target_date_end": t.strftime("%Y-%m-%d"),
            "tolerance_trading_days": 0,
            "event_time_utc": t.isoformat(),
            "retrieved_at": generated_at,
            "event": code,
            "strength": None,
            "headline": headline,
            "url": "",
            "classifier_version": CLASSIFIER_VERSION,
            "computed_with": f"ephem {ephem.__version__}",
        })
        seen.add(rid)
        added += 1

    if added == 0:
        print(f"新規なし(計算 {len(events)}件、既存 {len(records)}件)")
        return
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"新規 {added}件を追加(累計 {len(records)}件)")


if __name__ == "__main__":
    main()
