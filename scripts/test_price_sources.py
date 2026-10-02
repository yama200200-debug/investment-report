#!/usr/bin/env python3
"""株価データ取得テスト(保存しない・コミットしない)。
GitHub ActionsからYahoo Financeのチャートデータを取得できるかを、銘柄ごとに表示するだけ。
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SYMBOLS = [
    ("日経平均", "^N225"),
    ("TOPIX", "^TPX"),
    ("TOPIX連動ETF(代替候補)", "1306.T"),
    ("S&P500", "^GSPC"),
    ("NASDAQ総合", "^IXIC"),
    ("SOX", "^SOX"),
    ("VIX", "^VIX"),
    ("USDJPY", "JPY=X"),
    ("金先物", "GC=F"),
    ("WTI原油先物", "CL=F"),
]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def check(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol, safe="") + "?range=15y&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return f"HTTPエラー {e.code}"
    except Exception as e:
        return f"失敗 {type(e).__name__}: {e}"
    try:
        res = data["chart"]["result"][0]
        ts = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
        valid = [(t, c) for t, c in zip(ts, closes) if c is not None]
        first = datetime.fromtimestamp(valid[0][0], timezone.utc).strftime("%Y-%m-%d")
        last = datetime.fromtimestamp(valid[-1][0], timezone.utc).strftime("%Y-%m-%d")
        return f"OK {len(valid)}件 {first} 〜 {last}"
    except Exception as e:
        return f"形式不明 {type(e).__name__}: {str(data)[:120]}"


def main():
    for name, sym in SYMBOLS:
        print(f"{name:<22} {sym:<8} {check(sym)}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
