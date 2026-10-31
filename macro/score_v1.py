import json, glob, os, sys, datetime as dt

TODAY = dt.date.today()
NOW = dt.datetime.now().isoformat(timespec="seconds")
MIN_POINTS = 20  # 仮置き・後から変更可能

# (ID, 変換, 向き) 変換: level=水準 / yoy=前年比
# 向き: 1=高いほどリスク, -1=低いほどリスク, 0=点数化しない(要確認)
CFG = [
    ("PCEPILFE", "yoy", 1), ("CPILFESL", "yoy", 1),
    ("PAYEMS", "yoy", -1), ("INDPRO", "yoy", -1),
    ("PMAIZMTUSDM", "yoy", 1), ("PWHEAMTUSDM", "yoy", 1), ("PSOYBUSDM", "yoy", 1),
    ("UNRATE", "level", 1), ("FEDFUNDS", "level", 1),
    ("DGS2", "level", 1), ("LONG_RATE", "level", 1),
    ("BAMLH0A0HYM2", "level", 1), ("VIX", "level", 1), ("WTI", "level", 1),
    ("ONI", "level", 1), ("USDJPY", "level", 0),
]
EXTRA = ["TSMC_REV_MONTHLY", "TAIWAN_EXPORT_ORDERS", "CAPEX_GUIDANCE", "BDRY", "KBW_BKX"]
ZERO_W = ["USDJPY", "KBW_BKX"]
AI_IDS = ["TSMC_REV_MONTHLY"]

def yoy_series(h):
    d = {}
    for ds, v in h:
        d[(int(ds[:4]), int(ds[5:7]))] = v
    out = []
    for (y, m), v in sorted(d.items()):
        p = d.get((y - 1, m))
        if p:
            out.append(v / p * 100 - 100)
    return out

def pct(series, x):
    n = len(series)
    less = sum(1 for s in series if s < x)
    eq = sum(1 for s in series if s == x)
    return (less + 0.5 * eq) / n * 100

raw_files = sorted(glob.glob(os.path.join("output", "raw_*.json")))
if not raw_files:
    sys.exit("output/raw_*.json が見つかりません")
raw_path = raw_files[-1]
with open(raw_path, encoding="utf-8") as f:
    raw = json.load(f)
recs = {r["id"]: r for r in raw["records"]}

if not os.path.exists("weights.json"):
    w0 = {c[0]: 1.0 for c in CFG}
    for k in EXTRA:
        w0[k] = 1.0
    for k in ZERO_W:
        w0[k] = 0.0
    with open("weights.json", "w", encoding="utf-8") as f:
        json.dump(w0, f, ensure_ascii=False, indent=1)
    print("weights.json を新規作成(仮置き: 全項目均等)")
with open("weights.json", encoding="utf-8") as f:
    weights = json.load(f)

cfg = {c[0]: c for c in CFG}
rows = []
for id_, w in weights.items():
    r = recs.get(id_)
    row = {"id": id_, "weight": w, "status": r["status"] if r else "none",
           "score": None, "latest": None, "transform": None, "reason": "",
           "tag": "AI・半導体枠: 仮置き・未検証" if id_ in AI_IDS else ""}
    if w <= 0:
        row["reason"] = "重み0(対象外または要確認)"
    elif not r:
        row["reason"] = "rawにない"
    elif r["status"] != "ok":
        row["reason"] = "status=" + r["status"]
    elif not r.get("history_3y"):
        row["reason"] = "履歴なし(点数化せず)"
    elif id_ not in cfg or cfg[id_][2] == 0:
        row["reason"] = "点数化ルール未決定"
    else:
        tf, dirn = cfg[id_][1], cfg[id_][2]
        h = r["history_3y"]
        series = yoy_series(h) if tf == "yoy" else [v for _, v in h]
        if len(series) < MIN_POINTS:
            row["reason"] = "履歴点数不足(%d<%d)" % (len(series), MIN_POINTS)
        else:
            x = series[-1]
            s = pct(series, x)
            if dirn < 0:
                s = 100 - s
            row["score"] = round(s, 1)
            row["latest"] = round(x, 4)
            row["transform"] = tf
            row["reason"] = "前年比%" if tf == "yoy" else "水準"
    rows.append(row)

sc = [x for x in rows if x["score"] is not None]
tw = sum(x["weight"] for x in rows if x["weight"] > 0)
sw = sum(x["weight"] for x in sc)
total = round(sum(x["weight"] * x["score"] for x in sc) / sw, 1) if sw else None
cov = round(sw / tw * 100, 1) if tw else None

out = {"generated_at": NOW, "source_raw": raw_path.replace("\\", "/"),
       "total_score": total, "coverage_pct": cov,
       "note": "全体が仮置き。点数が高いほどリスクが高い。重みは仮置き・自動変更なし",
       "records": rows}
path = "output/score_" + TODAY.isoformat() + ".json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for x in rows:
    print("{:<22}{:<9}w={:<4} score={:<6} latest={:<10} {}".format(
        x["id"], x["status"], x["weight"], str(x["score"]), str(x["latest"]), x["reason"] + " " + x["tag"]))
print("総合点(仮置き):", total, " データ充足率%:", cov)
print("保存:", path)
