import json, glob, os

NAMES = {
    "ONI": "ONI(エルニーニョ指標・太平洋の海面水温の平年差)",
    "LONG_RATE": "LONG_RATE(米10年国債利回り)",
    "DGS2": "DGS2(米2年国債利回り)",
    "WTI": "WTI(原油価格)",
    "PCEPILFE": "PCEPILFE(コアPCE物価・食品とエネルギー除く)",
    "CPILFESL": "CPILFESL(コアCPI・食品とエネルギー除く)",
    "PAYEMS": "PAYEMS(米国非農業部門雇用者数)",
    "INDPRO": "INDPRO(米国鉱工業生産指数)",
    "UNRATE": "UNRATE(米国失業率)",
    "FEDFUNDS": "FEDFUNDS(米政策金利)",
    "BAMLH0A0HYM2": "BAMLH0A0HYM2(米ハイイールド債スプレッド)",
    "VIX": "VIX(恐怖指数)",
    "USDJPY": "USDJPY(円ドル・向き未決定のため点数化対象外)",
    "TSMC_REV_MONTHLY": "TSMC(月次売上)",
    "TAIWAN_EXPORT_ORDERS": "台湾輸出受注",
    "CAPEX_GUIDANCE": "設備投資ガイダンス",
    "BDRY": "BDRY(海運ETF)",
    "KBW_BKX": "KBW(銀行指数・対象外)",
}
GRAINS = ("PMAIZMTUSDM", "PWHEAMTUSDM", "PSOYBUSDM")

files = sorted(glob.glob(os.path.join("output", "score_*.json")))
if not files:
    raise SystemExit("output/score_*.json が見つかりません")
with open(files[-1], encoding="utf-8") as f:
    d = json.load(f)
recs = d.get("records", [])
day = str(d.get("generated_at", ""))[:10]

def name(r):
    return NAMES.get(r["id"], r["id"])

def val(r):
    v = r.get("latest")
    if v is None:
        return ""
    if r.get("transform") == "yoy":
        return "(%.2f%%)" % v
    return "(%.2f)" % v

scored = [r for r in recs if r.get("score") is not None]
unscored = [r for r in recs if r.get("score") is None]
items = []
for r in scored:
    if r["id"] in GRAINS:
        continue
    suffix = "の前年比" if r.get("transform") == "yoy" else ""
    items.append((r["score"], r["score"], name(r) + suffix + " %.1f点" % r["score"] + val(r)))
gr = [r["score"] for r in scored if r["id"] in GRAINS]
if gr:
    t = "穀物3種(とうもろこし・小麦・大豆の国際価格)の前年比 %.1f〜%.1f点" % (min(gr), max(gr))
    items.append((max(gr), min(gr), t))

top = sorted(items, key=lambda x: -x[0])[:5]
low = sorted(items, key=lambda x: x[1])[:3]

L = []
L.append("【マクロ景気監視指数(仮置き)】" + day)
L.append("総合点: %s / データ充足率: %s%%" % (d.get("total_score"), d.get("coverage_pct")))
L.append("注意: 点数は直近3年の中での位置であり、景気の予測値ではありません。重みは全項目均等の仮置きです。AI・半導体枠は仮置き・未検証です。")
L.append("■ 高リスク側 上位5")
for i, x in enumerate(top, 1):
    L.append("%d. %s" % (i, x[2]))
L.append("■ 低リスク側 下位3")
for i, x in enumerate(low, 1):
    L.append("%d. %s" % (i, x[2]))
if unscored:
    L.append("■ 未計算: " + " / ".join(name(r) for r in unscored))
L.append("■ 見通し(5日/25日/200日): 未設計")

out = os.path.join("output", "macro_digest_" + day + ".txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("保存:", out)
print("\n".join(L))

