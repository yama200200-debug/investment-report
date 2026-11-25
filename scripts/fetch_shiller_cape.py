#!/usr/bin/env python3
"""Shiller ie_data.xls から最新月のCAPEを取り出し data/shiller_cape.json に保存する。
失敗した場合は既存のJSONを上書きせず、終了コード1で終わる。"""
import html
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

PAGE_URL = "https://shillerdata.com/"
OUT_PATH = "data/shiller_cape.json"
HEADERS = {"User-Agent": "tetchama-research-bot/1.0 (weekly, 1 file)"}
LINK_RE = re.compile(r"https://img1\.wsimg\.com/blobby/[^\"'\s)<>]*ie_data\.xls[^\"'\s)<>]*")


def find_xls_url(page_html):
    m = LINK_RE.search(html.unescape(page_html))
    if not m:
        raise ValueError("ie_data.xls のリンクがページから見つかりません")
    return m.group(0)


def pick_header_row(df):
    for i in range(min(len(df), 20)):
        if str(df.iat[i, 0]).strip().lower().startswith("date"):
            return i
    raise ValueError("見出し行(Date)が見つかりません")


def pick_cape_col(df, hr):
    heads = [str(df.iat[hr, c]).strip().lower() for c in range(df.shape[1])]
    exact = [c for c, h in enumerate(heads) if h == "cape"]
    if len(exact) == 1:
        return exact[0]
    loose = [c for c, h in enumerate(heads)
             if "cape" in h and "tr" not in h and "excess" not in h]
    if len(loose) == 1:
        return loose[0]
    raise ValueError("CAPE列を一意に特定できません: %s" % heads)


def date_to_ym(x):
    v = float(x)
    year = int(v)
    month = int(round((v - year) * 100))
    if not (1871 <= year <= 2100 and 1 <= month <= 12):
        raise ValueError("日付を解釈できません: %r" % x)
    return "%04d-%02d" % (year, month)


def latest_cape(df):
    hr = pick_header_row(df)
    cc = pick_cape_col(df, hr)
    latest = None
    for r in range(hr + 1, len(df)):
        try:
            ym = date_to_ym(df.iat[r, 0])
            cape = float(df.iat[r, cc])
        except (ValueError, TypeError):
            continue
        if cape != cape:  # NaN
            continue
        latest = (ym, cape)
    if latest is None:
        raise ValueError("有効なCAPE行がありません")
    ym, cape = latest
    if not (5 <= cape <= 100):
        raise ValueError("CAPEが想定範囲外です: %s" % cape)
    return ym, round(cape, 2)


def main():
    page = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
    page.raise_for_status()
    xls_url = find_xls_url(page.text)
    res = requests.get(xls_url, headers=HEADERS, timeout=60)
    res.raise_for_status()
    df = pd.read_excel(io.BytesIO(res.content), sheet_name="Data", header=None)
    ym, cape = latest_cape(df)

    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    if old.get("data_month") == ym and old.get("cape") == cape:
        print("変更なし:", ym, cape)
        return 0
    out = {
        "source": "Robert J. Shiller, ie_data.xls (shillerdata.com)",
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_month": ym,
        "cape": cape,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("更新:", ym, cape)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("失敗:", e, file=sys.stderr)
        sys.exit(1)
