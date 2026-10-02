#!/usr/bin/env python3
"""Quantpedia RSS -> research-data/research/research_watch.json
保存するのはメタデータのみ(本文・抜粋は保存しない)。標準ライブラリのみ使用。
使い方: python scripts/collect_quantpedia.py [テスト用のローカルXMLパス]
"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://quantpedia.com/feed"
SOURCE = "quantpedia"
OUT = Path("research-data/research/research_watch.json")
JST = timezone(timedelta(hours=9))
UA = "tetchama-research-watch/1.0 (personal research, once daily)"


def fetch(arg):
    if arg:
        return Path(arg).read_bytes()
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(xml_bytes, retrieved_at):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        guid = (it.findtext("guid") or "").strip() or link
        if not guid:
            continue
        try:
            published = parsedate_to_datetime((it.findtext("pubDate") or "").strip())
            published = published.astimezone(timezone.utc).isoformat()
        except Exception:
            published = ""
        items.append({
            "schema_version": 1,
            "source": SOURCE,
            "guid": guid,
            "title": (it.findtext("title") or "").strip(),
            "url": link,
            "published": published,
            "categories": [c.text.strip() for c in it.findall("category") if c.text],
            "retrieved_at": retrieved_at,
        })
    return items


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    retrieved_at = datetime.now(JST).isoformat(timespec="seconds")
    items = parse(fetch(arg), retrieved_at)
    if not items:
        print("ERROR: RSSから記事を1件も読み取れませんでした(形式変更の可能性)")
        sys.exit(1)

    if OUT.exists():
        records = json.loads(OUT.read_text(encoding="utf-8"))  # 壊れていたら例外で停止(上書きしない)
        if not isinstance(records, list):
            print("ERROR: research_watch.json が配列ではありません")
            sys.exit(1)
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        records = []

    seen = {(r.get("source"), r.get("guid")) for r in records if isinstance(r, dict)}
    new = [i for i in items if (i["source"], i["guid"]) not in seen]
    if not new:
        print(f"新規なし(RSS {len(items)}件、既存 {len(records)}件)")
        return

    records.extend(sorted(new, key=lambda r: r["published"]))
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"新規 {len(new)}件を追加(累計 {len(records)}件)")


if __name__ == "__main__":
    main()
