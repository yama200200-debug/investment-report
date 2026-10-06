# 2026-10-06 新チャット引き継ぎ

対象: yama200200-debug/investment-report
プロジェクト: 占術シグナル研究＋AI産業サイクル・レーダー

## 合言葉

GREEN GLOW再開

この合言葉を新しいチャットで受けたら、このファイルと既存のPROJECT_HANDOFF.mdを確認し、GitHubの現在状態を再取得して続行する。

## 最重要ルール

- GitHubの現在ファイルを実際に確認してから作業する。
- 記載されたSHAや過去チャットの記憶を盲目的に信用しない。
- コード/YAML変更前は必ず対象ファイルの現在版を取得する。
- 推測でファイル構造、ID、変数名、エッジ、仕様を決めない。
- 統計手法・投資判断ロジック・重要データソースを勝手に変更しない。
- Claude AIレビューが必要な場合は、ユーザーがそのまま送れる完成メッセージを作る。
- ユーザーが最終判断者。

## 完了済み：占術統計ベースライン

対象:
4 event types × 5 series × 3 horizons = 60 tests
horizon = 1D / 5D / 20D
permutation = 10,000
seed = 20261003
Bonferroni = ×60
two-sided p-value
p-value = (extreme_count + 1) / (iterations + 1)
return rule = base_prev_close_v1
normal day = 対象event typeが発生していないFRED実観測日
5D/20D = overlapping windows
WTI base <= 0 はreturn計算から除外

最終結果:
- 60 tests
- Bonferroni有意 = 0
- raw p<0.05 = 2
- mercury_retrograde_start × NIKKEI225 × 1D: p=0.00449955, Bonferroni=0.269973
- mercury_retrograde_start × NIKKEI225 × 5D: p=0.03719628, Bonferroni=1
- actual comparisons = planned 60
- eligible comparison date mismatch = 0
- fortune_validation.json = 1768 rows
- Claude AI最終レビュー = 「問題なし」

この統計ベースラインは凍結。結果を見てルール変更しない。

主要SHA:
- scripts/summarize_fortune.py = fe9994b39322b5c7f43517541a2585096888e0d7
- scripts/validate_fortune.py = 0a111babb6545dc3569cd5f7eb61b9ecb8223918
- 既存PROJECT_HANDOFF.md = d7a50e44dc5a4bab9ae857f6a1a447e8076f9a4d

## 現在の最優先：AI産業サイクル・レーダー

まだGitHub実装しない。

候補レイヤー:
A AI需要
B AI生産
C AIインフラ
D AI利益
E AI市場
F 半導体サプライチェーン
G 物流・コンテナ
H 日本実体経済 / METI鉱工業指数(IIP)

半導体仮説:
日本の装置・材料
→ 台湾ファウンドリ/電子部品
→ 韓国メモリ/HBM
→ 米国GPU/クラウド/AI需要
→ 企業決算・利益・株価

物流候補:
Shanghai→New York
Shanghai→Los Angeles
Shanghai→Genoa
Shanghai→Rotterdam
Shanghai→Tokyo/Osaka

IIP候補:
生産、出荷、在庫、在庫率、生産予測指数、業種別IIP

検証仮説:
H1 韓国半導体指標→台湾輸出/輸出受注
H2 台湾輸出/輸出受注→日本IIP等
H3 日本IIP→企業決算等
H4 先行指標→将来の業種/ETF/株価
H5 複数指標同時悪化→将来ドローダウン確率

## AIレーダーで正式採用した統計上のルール

1 Look-ahead bias
2 Data snooping
3 多重比較
4 Survivorship bias
5 ラグ設定
6 変数変換
7 サンプル数
8 欠損処理
9 Point-in-Time性
10 指標間の重複・相関
11 業種・企業選定の妥当性

特に追加された重要ルール:
FとH、GとAI需要などは同じ経済要因を別角度から観測する可能性がある。候補表の「経済的な仮説」に重複可能性を記載する。候補表段階では実相関を断定せず、データ取得後に検証する。H4/H5で同じ情報を二重カウントしない。

候補表Ver.1の項目:
layer / indicator / country-region / primary source / retrieval method / publication frequency / publication timing / Point-in-Time status / available history / observation count / economic hypothesis（重複可能性含む） / pre-fixed lag / pre-fixed variable transform / validation target / representative-company selection rule / missing-revision caveats

Claudeレビューとユーザー承認が終わるまで実装しない。

## 新規検討：中長期マクロ・金融サイクル

2026/10/06開始。

日本:
- 日銀 資金循環統計：家計部門
- 日銀 マネーストック統計：M1/M2等
- 家計金融資産・負債・純資産
- 預金、株式、投資信託等の資産配分

米国:
- Federal Reserve Financial Accounts of the United States (Z.1)
- Household and nonprofit organizations
- Z.1の家計金融資産・負債・純資産
- FRB Money Stock MeasuresのM1/M2

目的:
中長期の景気・金融環境判断、家計流動性・資産配分・負債・純資産、日本米国の金融サイクル比較。

重要:
日本と米国のM1/M2を完全同一概念として扱わない。
「マネー量」と「家計資産配分」を分ける。
まず候補指標表、Point-in-Time、頻度、履歴、改訂、定義差を確認してから実装する。
AI産業サイクルとは別レイヤーで設計する。

## 次チャットで最初にすること

1. このファイルを確認
2. PROJECT_HANDOFF.mdも確認
3. GitHubの現在状態を再取得
4. 現在の最優先タスクを報告
5. 「AI産業サイクル・レーダー 指標候補表 Ver.1」を作成する段階から再開
6. 必要に応じて一次情報源をWebで確認
7. Claude AIへ独立レビューを依頼
8. Claudeレビューとユーザー承認前にはGitHub実装しない

新チャット開始メッセージ:
「GREEN GLOW再開。PROJECT_HANDOFF_2026-10-06.mdとPROJECT_HANDOFF.mdを起点に、GitHubの現在状態を確認して作業を再開してください。記載内容を盲目的に信用せず、必要なファイルは必ず現在版を確認してください。まず現在の状態確認、最優先タスク、次にやることを報告してください。」
