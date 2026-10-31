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
    rid, src = "TSMC_REV_MONTHLY", "SEC EDGAR 6-K"
    if "@" not in UA:
        return rec(rid, source=src, note="SEC_USER_AGENT未設定")
    TOK = r"\(?[\d,]+(?:\.\d+)?\)?"
    def num(s):
        s = s.strip()
        neg = s.startswith("(")
        v = float(s.strip("()").replace(",", ""))
        return -v if neg else v
    try:
        sub = json.loads(get("https://data.sec.gov/submissions/CIK0001046179.json", {"User-Agent": UA}))
        r = sub["filings"]["recent"]
        rows = [(r["filingDate"][i], r["accessionNumber"][i], r["primaryDocument"][i])
                for i, f in enumerate(r["form"]) if f == "6-K"]
        for d, acc, doc in rows[:60]:
            url = f"https://www.sec.gov/Archives/edgar/data/1046179/{acc.replace('-', '')}/{doc}"
            time.sleep(0.5)
            try:
                text = html.unescape(re.sub(r"<[^>]+>", " ", get(url, {"User-Agent": UA})))
                text = re.sub(r"\s+", " ", text)
            except Exception:
                continue
            m = re.search(r"net revenue for ([A-Za-z]+ \d{4})", text, re.I)
            if not m:
                continue
            seg = text[m.start(): m.start() + 1500]
            t = re.search(r"Net Revenue\s+((?:" + TOK + r"\s+){7}" + TOK + ")", seg)
            if not t:
                return rec(rid, source=src, note="表の行が取れない(推測補完なし)")
            cur, prev, mom, yago, yoy, ytd, ytd_prev, ytd_yoy = [num(x) for x in t.group(1).split()]
            rev = re.search(r"approximately NT\$\s?([\d,\.]+)\s*billion", seg)
            pct = re.findall(r"(increase|decrease) of ([\d\.]+) percent", seg)
            ytdt = re.search(r"totaled (?:N)?T\$\s?([\d,\.]+)\s*billion", seg)
            ok = []
            if rev:
                ok.append(abs(cur / 1000 - float(rev.group(1).replace(",", ""))) < 0.011)
            if len(pct) >= 2:
                a = float(pct[0][1]) * (-1 if pct[0][0] == "decrease" else 1)
                b = float(pct[1][1]) * (-1 if pct[1][0] == "decrease" else 1)
                ok.append(abs(mom - a) < 0.051)
                ok.append(abs(yoy - b) < 0.051)
            if ytdt:
                ok.append(abs(ytd / 1000 - float(ytdt.group(1).replace(",", ""))) < 0.011)
            if not ok or not all(ok):
                return rec(rid, source=src, note="照合不一致または文章側が取れない(推測補完なし)")
            as_of = dt.datetime.strptime(m.group(1), "%B %Y").date().isoformat()
            st, age = judge(as_of, TSMC_STALE)
            note = f"単位NT$百万 前月比{mom}% 前年比{yoy}% 年初来{ytd:,.0f} 提出日{d} 経過{age}日"
            return rec(rid, cur, as_of, src, st, note)
        return rec(rid, source=src, note="対象の6-Kが見つからない")
    except Exception as e:
        return rec(rid, source=src, note=type(e).__name__)

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
