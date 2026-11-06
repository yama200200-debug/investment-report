import json, glob, os, re

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
    "SHIPPING_PPI": "海運PPI(運賃物価・仮置き・重み0)",
    "TAIWAN_EXPORT_ORDERS": "台湾輸出受注",
    "CAPEX_GUIDANCE": "設備投資ガイダンス",
    "BDRY": "BDRY(海運ETF)",
    "KBW_BKX": "KBW(銀行指数・対象外)",
    "TAIWAN_ORDERS_AUTO": "台湾輸出受注(百万ドル・経済部)",
    "AI_CAPEX_BIG4": "AI大手4社の設備投資(十億ドル・実績)",
    "WB_WHEAT_HRW": "小麦(米HRW・USD/t)",
    "WB_MAIZE": "トウモロコシ(USD/t)",
    "WB_SOYBEANS": "大豆(USD/t)",
}
GRAINS = ("PMAIZMTUSDM", "PWHEAMTUSDM", "PSOYBUSDM")
HIDE_VALUE = ("VIX", "BAMLH0A0HYM2")
HIDE_ITEM = ("BAMLH0A0HYM2",)
REF_IDS = ("SHIPPING_PPI", "TAIWAN_ORDERS_AUTO", "TSMC_REV_MONTHLY", "AI_CAPEX_BIG4", "WB_WHEAT_HRW", "WB_MAIZE", "WB_SOYBEANS")

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
    if r["id"] in HIDE_VALUE:
        return ""
    v = r.get("latest")
    if v is None:
        return ""
    if r.get("transform") == "yoy":
        return "(%.2f%%)" % v
    return "(%.2f)" % v

scored = [r for r in recs if r.get("score") is not None]
unscored = [r for r in recs if r.get("score") is None and r["id"] not in REF_IDS and r["id"] not in ("TAIWAN_EXPORT_ORDERS", "CAPEX_GUIDANCE")]
items = []
for r in scored:
    if r["id"] in GRAINS or r["id"] in HIDE_ITEM:
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

raw_files = sorted(glob.glob(os.path.join("output", "raw_*.json")))
ref_lines = []
if raw_files:
    try:
        with open(raw_files[-1], encoding="utf-8") as f:
            rr = {x.get("id"): x for x in json.load(f).get("records", [])}
    except Exception:
        rr = {}
    for rid in REF_IDS:
        x = rr.get(rid)
        if not x or x.get("status") != "ok" or x.get("value") is None:
            continue
        v = float(x["value"])
        hist = [h[1] for h in (x.get("history_3y") or []) if h[1] is not None]
        yoy = None
        m = re.search(r"yoy%=(-?[0-9.]+)", str(x.get("note", "")))
        if m:
            yoy = float(m.group(1))
        elif len(hist) >= 13 and hist[-13]:
            yoy = (hist[-1] / hist[-13] - 1) * 100
        parts = []
        if yoy is not None:
            parts.append("前年比 %+.1f%%" % yoy)
        if len(hist) >= 20:
            parts.append("直近3年の位置 %.0f点" % (100.0 * sum(1 for h in hist if h <= v) / len(hist)))
        else:
            parts.append("位置は履歴不足のため非表示")
        num = "%.1f" % v if v < 1000 else "{:,.0f}".format(v)
        ref_lines.append("・%s %s(%s)" % (name(x), num, " / ".join(parts)))
if ref_lines:
    L.append("■ 参考表示(総合点には加算しません・点数化なし・重み0)")
    L.extend(ref_lines)
    L.append("出典(小麦・トウモロコシ・大豆): World Bank Commodity Price Data (The Pink Sheet)")

out = os.path.join("output", "macro_digest_" + day + ".txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print("保存:", out)
print("\n".join(L))
