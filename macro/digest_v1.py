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
    "USDJPY": "USDJPY(円ドル・円高をリスクとする向き・仮置き)",
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

SIGNALS = [
    ("金利の重し", ("FEDFUNDS", "DGS2", "LONG_RATE"), 90.0),
    ("物価・資源の重し", ("PCEPILFE", "CPILFESL", "WTI"), 85.0),
    ("食料価格の重し", GRAINS, 85.0),
]
SHORT = {"PMAIZMTUSDM": "とうもろこし", "PWHEAMTUSDM": "小麦", "PSOYBUSDM": "大豆"}
sc = {r["id"]: r["score"] for r in scored}
sig_lines = []
on_count = 0
for sname, ids, th in SIGNALS:
    if all(i in sc for i in ids):
        avg = sum(sc[i] for i in ids) / len(ids)
        on = avg >= th
        on_count += 1 if on else 0
        detail = " / ".join("%s %.1f点" % (SHORT.get(i, i), sc[i]) for i in ids)
        sig_lines.append("・%s: %s(3項目平均 %.1f点・条件%.0f点以上) %s" % (sname, "点灯" if on else "非点灯", avg, th, detail))
    else:
        sig_lines.append("・%s: 計算不可(項目不足)" % sname)

L = []
L.append("【マクロ景気監視指数(傾向表示)】" + day)
L.append("総合点: %s / データ充足率: %s%%" % (d.get("total_score"), d.get("coverage_pct")))
L.append("読み方: この点数は直近3年の中での位置を示すものです。景気や株価の予測値ではありません。")
L.append("注意: 先行性は統計検証で確認できていません。5日・25日・200日先の数値予測は掲載しません。")
L.append("補足: 重みは全項目均等の仮置きです。AI・半導体枠は仮置き・未検証です。")
L.append("■ 高リスク側 上位5")
for i, x in enumerate(top, 1):
    L.append("%d. %s" % (i, x[2]))
L.append("■ 低リスク側 下位3")
for i, x in enumerate(low, 1):
    L.append("%d. %s" % (i, x[2]))
L.append("■ 観察シグナル(総合点には加算しません・点灯条件は仮置き)")
L.extend(sig_lines)
L.append("・重なり(2つ以上点灯): " + ("あり" if on_count >= 2 else "なし"))
if unscored:
    L.append("■ 未計算: " + " / ".join(name(r) for r in unscored))

out = os.path.join("output", "macro_digest_" + day + ".txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("保存:", out)
print("\n".join(L))

