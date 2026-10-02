#!/usr/bin/env python3
"""FREDから各系列を取得できるかのテスト(保存しない・コミットしない)。
環境変数 FRED_API_KEY が必要。キーは表示しない。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SERIES = [
    ("S&P500", "SP500"),
    ("NASDAQ総合", "NASDAQCOMP"),
    ("日経平均", "NIKKEI225"),
    ("VIX", "VIXCLS"),
    ("USDJPY(円/ドル)", "DEXJPUS"),
    ("WTI原油", "DCOILWTICO"),
    ("金(ロンドン)", "GOLDAMGBD228NLBM"),
    ("TOPIX", "TOPIX"),
    ("SOX", "SOX"),
]


def check(series_id, key):
    q = urllib.parse.urlencode({
        "series_id": series_id, "api_key": key, "file_type": "json",
        "observation_start": "2000-01-01",
    })
    url = "https://api.stlouisfed.org/fred/series/observations?" + q
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return f"HTTPエラー {e.code}(系列なしの可能性)"
    except Exception as e:
        return f"失敗 {type(e).__name__}"
    obs = [o for o in data.get("observations", []) if o.get("value") not in (".", "", None)]
    if not obs:
        return "データ0件"
    return f"OK {len(obs)}件 {obs[0]['date']} 〜 {obs[-1]['date']}"


def main():
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        print("ERROR: FRED_API_KEY が設定されていません")
        sys.exit(1)
    for name, sid in SERIES:
        print(f"{name:<16} {sid:<18} {check(sid, key)}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
