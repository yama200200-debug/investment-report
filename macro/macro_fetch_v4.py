import os, sys, json, time, re, html, datetime as dt, urllib.request, urllib.parse

TODAY = dt.date.today()
NOW = dt.datetime.now().isoformat(timespec="seconds")
START = (TODAY - dt.timedelta(days=1096)).isoformat()
UA = os.environ.get("SEC_USER_AGENT", "")

# 仮置き: (系列ID, stale許容日数=as_ofからの経過日数)。後から変更可能
FRED = [
    ("PCEPILFE", 100), ("CPILFESL", 75), ("UNRATE", 75), ("PAYEMS", 75),
    ("FEDFUNDS", 75), ("INDPRO", 75), ("DGS2", 5), ("BAMLH0A0HYM2", 5),
    ("PMAIZMTUSDM", 75), ("PWHEAMTUSDM", 75), ("PSOYBUSDM", 75),
]
ONI_STALE = 100
TSMC_STALE = 60

# 枠のみ(取得しない): (ID, status, note)
SLOTS = [
    ("BDRY", "missing", "取得元・規約未確認のため初期実装では取得しない"),
    ("TAIWAN_EXPORT_ORDERS", "missing", "手入力CSVの読み込みは次の手順"),
    ("CAPEX_GUIDANCE", "missing", "対象企業と数値化ルール未決定"),
    ("KBW_BKX", "excluded", "規約未解決のため対象外(重み0)"),
]

def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")

def rec(id_, value=None, as_of=None, source="", status="missing", note="", history=None):
    return {"id": id_, "value": value, "as_of": as_of, "fetched_at": NOW,
            "source": source, "status": status, "note": note,
            "history_3y": history or []}

def judge(as_of, stale_days):
    age = (TODAY - dt.date.fromisoformat(as_of)).days
    return ("ok" if age <= stale_days else "stale"), age

def fred_one(key, sid, stale_days):
    q = urllib.parse.urlencode({"series_id": sid, "api_key": key,
                                "file_type": "json", "observation_start": START})
    try:
        obs = json.loads(get("https://api.stlouisfed.org/fred/series/observations?" + q))["observations"]
        h = [[o["date"], float(o["value"])] for o in obs if o["value"] not in (".", "")]
        if not h:
            return rec(sid, source="FRED", note="データなし")
        d, v = h[-1]
        st, age = judge(d, stale_days)
        return rec(sid, v, d, "FRED", st, f"経過{age}日", h)
    except Exception as e:
        return rec(sid, source="FRED", note=type(e).__name__)

def oni():
    rid, src = "ONI", "NOAA CPC"
    try:
        seasons = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"]
        h, last = [], ""
        for ln in get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt").splitlines():
            p = ln.split()
            if len(p) >= 4 and p[0] in seasons:
                d = dt.date(int(p[1]), seasons.index(p[0]) + 1, 1).isoformat()
                if d >= START:
                    h.append([d, float(p[3])])
                last = f"{p[0]} {p[1]}"
        if not h:
            return rec(rid, source=src, note="データなし")
        st, age = judge(h[-1][0], ONI_STALE)
        return rec(rid, h[-1][1], h[-1][0], src, st, f"{last} 経過{age}日", h)
    except Exception as e:
        return rec(rid, source=src, note=type(e).__name__)

def tsmc():
    import ssl
    rid, src = "TSMC_REV_MONTHLY", "investor.tsmc.com"
    MON = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7,
           "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12}
    pat = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?\s+([\d,]{5,})\s+(-?[\d.]+)\s*%")
    rows, notes = {}, []
    for y in range(TODAY.year - 3, TODAY.year + 1):
        url = "https://investor.tsmc.com/english/monthly-revenue/%d" % y
        hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.9",
               "Referer": "https://investor.tsmc.com/english/monthly-revenue/2025"}
        body = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=hdr)
                with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
                    body = r.read().decode("utf-8", "replace")
                break
            except Exception as e:
                notes.append("%d:%s" % (y, type(e).__name__))
                time.sleep(2)
        if body is None:
            continue
        t = re.sub(r"<[^>]+>", " ", body)
        t = re.sub(r"&nbsp;|\s+", " ", t)
        seen = set()
        for m in pat.finditer(t):
            mo = MON[m.group(1)]
            if mo in seen:
                continue
            seen.add(mo)
            rows["%d-%02d" % (y, mo)] = (int(m.group(2).replace(",", "")), float(m.group(3)))
        time.sleep(0.5)
    keys = sorted(rows)
    if len(keys) < 24:
        return rec(rid, source=src, note="too few months: %d %s" % (len(keys), notes))
    hist = [[_me4(k), rows[k][0]] for k in keys[-36:]]
    last = keys[-1]
    st, age = judge(_me4(last), TSMC_STALE)
    note = "NT$ million yoy%%=%s months=%d age=%dd retry_notes=%s" % (rows[last][1], len(hist), age, notes)
    return rec(rid, rows[last][0], _me4(last), src, st, note, hist)


TAIWAN_CSV_PATH = "taiwan_export_orders.csv"
TAIWAN_OK_STATUS = "confirmed"  # 仮置き・要確認

def taiwan_csv():
    import csv
    id_ = "TAIWAN_EXPORT_ORDERS"
    if not os.path.exists(TAIWAN_CSV_PATH):
        return rec(id_, status="missing", note="手入力CSVが見つからない")
    try:
        with open(TAIWAN_CSV_PATH, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f)
                    if (r.get("status") or "").strip() == TAIWAN_OK_STATUS
                    and (r.get("month") or "").strip()
                    and (r.get("orders_total") or "").strip()]
        if not rows:
            return rec(id_, status="missing", note="手入力CSVに有効行なし")
        last = max(rows, key=lambda r: r["month"].strip())
        value = float(last["orders_total"].replace(",", ""))
        note = "unit=%s yoy_pct=%s release_date=%s" % (
            (last.get("unit") or "").strip(),
            (last.get("yoy_pct") or "").strip(),
            (last.get("release_date") or "").strip())
        return rec(id_, value=value, as_of=last["month"].strip(),
                   source="manual:taiwan_export_orders.csv",
                   status="manual", note=note)
    except Exception as e:
        return rec(id_, status="missing", note="手入力CSV読込エラー: " + str(e))


# ---- v4追加: 表示のみ・重み0(仮置き) ----
TW_URL4 = "https://service.moea.gov.tw/EE520/opendata/b.csv"
TW_ITEM4 = "\u5916\u92b7\u8a02\u55ae\u91d1\u984d"
CAPEX4 = [("MSFT", "0000789019", "PaymentsToAcquirePropertyPlantAndEquipment"),
          ("GOOGL", "0001652044", "PaymentsToAcquirePropertyPlantAndEquipment"),
          ("AMZN", "0001018724", "PaymentsToAcquireProductiveAssets"),
          ("META", "0001326801", "PaymentsToAcquirePropertyPlantAndEquipment")]

def _g4(url, headers):
    import urllib.request, ssl
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        return r.read()

def _me4(ym):
    import datetime
    y, m = int(ym[:4]), int(ym[5:7])
    return (datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).isoformat()

def taiwan_auto():
    import csv, io, re
    id_ = "TAIWAN_ORDERS_AUTO"
    try:
        text = _g4(TW_URL4, {"User-Agent": "Mozilla/5.0"}).decode("utf-8-sig", "replace")
        series = []
        for r in list(csv.reader(io.StringIO(text)))[1:]:
            if len(r) < 3 or not r[0].startswith(TW_ITEM4):
                continue
            m = re.match(r"^(\d{2,3})(\d{2})$", r[1].strip())
            if not m:
                continue
            try:
                series.append(("%04d-%s" % (int(m.group(1)) + 1911, m.group(2)), float(r[2])))
            except ValueError:
                continue
        series.sort()
        if len(series) < 14:
            return rec(id_, status="missing", note="too few rows")
        d = dict(series)
        ym, val = series[-1]
        prev = d.get("%d-%s" % (int(ym[:4]) - 1, ym[5:7]))
        yoy = round((val / prev - 1) * 100, 1) if prev else None
        hist = [[_me4(a), b] for a, b in series[-36:]]
        st, age = judge(_me4(ym), 60)
        return rec(id_, value=val, as_of=_me4(ym), source=TW_URL4, status=st,
                   note="USD million, yoy%%=%s, display_only_weight_0" % yoy, history=hist)
    except Exception as e:
        return rec(id_, status="missing", note="error: " + type(e).__name__ + ": " + str(e)[:100])

def _q4(entries):
    import datetime
    d = {}
    for e in entries:
        if e.get("form") not in ("10-Q", "10-K"):
            continue
        try:
            s0 = datetime.date.fromisoformat(e["start"]); en = datetime.date.fromisoformat(e["end"])
        except Exception:
            continue
        k = (s0, en)
        if k not in d or e.get("filed", "") >= d[k][1]:
            d[k] = (e["val"], e.get("filed", ""))
    q = {}
    for (s0, e), (v, _) in d.items():
        if 80 <= (e - s0).days <= 100:
            q[e] = v
    for (s0, e), (v, _) in d.items():
        if 100 < (e - s0).days <= 380 and e not in q:
            for (s2, e2), (v2, _) in d.items():
                if s2 == s0 and 80 <= (e - e2).days <= 100:
                    q[e] = v - v2
                    break
    return q

def capex_big4():
    import json
    id_ = "AI_CAPEX_BIG4"
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        return rec(id_, status="missing", note="SEC_USER_AGENT not set")
    per, notes = {}, []
    for name, cik, tag in CAPEX4:
        try:
            body = _g4("https://data.sec.gov/api/xbrl/companyconcept/CIK%s/us-gaap/%s.json" % (cik, tag), {"User-Agent": ua})
            j = json.loads(body.decode("utf-8"))
            items = [i for i in j.get("units", {}).get("USD", []) if i.get("end", "") >= "2022-01-01"]
            per[name] = _q4(items)
        except Exception as e:
            notes.append(name + " " + type(e).__name__)
        time.sleep(0.3)
    if len(per) < 4:
        return rec(id_, status="missing", note="companies_ok=%s %s" % (sorted(per), notes))
    ends = sorted(set(per["MSFT"]) & set(per["GOOGL"]) & set(per["AMZN"]) & set(per["META"]))
    if not ends:
        return rec(id_, status="missing", note="no common quarter")
    tot = {e: sum(per[n][e] for n in per) for e in ends}
    last = ends[-1]
    prev = None
    for e2 in ends:
        if abs((last - e2).days - 365) <= 10:
            prev = tot[e2]
    yoy = round((tot[last] / prev - 1) * 100, 1) if prev else None
    hist = [[e.isoformat(), round(tot[e] / 1e9, 3)] for e in ends[-12:]]
    by = {n: round(per[n][last] / 1e9, 3) for n in sorted(per)}
    st, age = judge(last.isoformat(), 150)
    return rec(id_, value=round(tot[last] / 1e9, 3), as_of=last.isoformat(), source="SEC EDGAR XBRL companyconcept",
               status=st, note="USD billion actual cash capex (not guidance), yoy%%=%s, %s, display_only_weight_0" % (yoy, by), history=hist)

key = os.environ.get("FRED_API_KEY", "")
if not key:
    sys.exit("FRED_API_KEY が未設定です")
out = []
for sid, sd in FRED:
    out.append(fred_one(key, sid, sd))
    time.sleep(0.3)
EXTRA = [("VIX", "VIXCLS", 10), ("WTI", "DCOILWTICO", 10), ("USDJPY", "DEXJPUS", 14), ("LONG_RATE", "DGS10", 10)]
for name, sid, sd in EXTRA:
    r = fred_one(key, sid, sd)
    r["id"] = name
    r["note"] = (str(r.get("note", "")) + " FRED:" + sid).strip()
    out.append(r)
    time.sleep(0.3)
out.append(oni())
out.append(tsmc())
out.append(taiwan_csv())
out.append(taiwan_auto())
out.append(capex_big4())
for sid, st, note in SLOTS:
    if sid == "TAIWAN_EXPORT_ORDERS":
        continue
    out.append(rec(sid, status=st, note=note))

os.makedirs("output", exist_ok=True)
path = f"output/raw_{TODAY.isoformat()}.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump({"generated_at": NOW, "records": out}, f, ensure_ascii=False, indent=1)
for r in out:
    print(f"{r['status']:<9}{r['id']:<22}{r['value']}  {r['as_of']}  {r['note']}")
print("保存:", path)
