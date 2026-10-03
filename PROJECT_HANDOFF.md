# investment-report プロジェクト引き継ぎ書

更新日: 2026/10/04
対象リポジトリ: yama200200-debug/investment-report
プロジェクト名: 占術シグナル研究＋AI産業サイクル・レーダー

## 1. この文書の目的

この文書は、ChatGPT/Claude AI/その他のAIが新しいチャットから同じ開発状態を再現し、前のチャットで決めた仕様を勝手に変更せず作業を継続するための引き継ぎ情報である。

最優先の共通ルールは、GitHub上の現在ファイルを実際に確認してから作業すること。過去チャットの記憶やこの文書だけを根拠に、ファイル構造・ID・変数名・コードを推測して変更してはいけない。

## 2. AIの役割

### ChatGPT
- GitHub確認・コード実装・Python・統計計算・GitHub Actions・全体アーキテクチャを担当。
- コード/YAML変更前に必ず現在ファイルを取得して確認する。
- 実装上のバグは既存仕様を変えない範囲で自律修正する。
- 統計検証方法そのもの、投資判断ロジック、重要なデータソース変更などは勝手に決定しない。
- Claude AIのレビューが有効な場面では、ユーザーに明示的に
  「【Claude AIへそのまま送ってください】」
  として、Claude向けの完成したメッセージを提示する。

### Claude AI
- Dify/Make/workflow系の実装・レビューを担当。
- ChatGPTが作成したコードや統計実装について、独立したレビューを行う。
- GitHubを直接参照できない場合は、ChatGPTが現在のGitHubコードを取得してレビュー材料を渡す。
- 統計手法そのものを変更する提案は、根拠・影響を明示し、人間の承認が必要な事項として扱う。

### ユーザー
- プロジェクトオーナー。
- 目的、優先順位、重要仕様、AI同士で解決できない事項を判断する。
- 細かい技術作業やコードのコピー役にはしない。

## 3. 開発憲法

GitHubの AI_DEVELOPMENT_RULES.md が共通ルール。

現在確認済みSHA:
31fe2ecbae85b4852fa8ecc587f70a7c6ebfe6d3

主要原則:
- 調査 → 設計 → 実装 → テスト → レビュー → 修正 → 完了確認
- 既存構造を確認してから変更
- 過去データを保護
- 不明点を推測しない
- 確定仕様をAI判断だけで変更しない
- 統計検証は結果を見た後に都合よくルール変更しない
- 完了は「コードを書いた」ではなく、テスト・影響確認・記録まで含む

## 4. プロジェクトの目的

「占術シグナル研究」と「AI産業サイクル・レーダー」は分離して扱う。

### 占術シグナル研究
占術イベントと市場データに統計的な関係があるかを、事後的なルール変更をせず検証する。
「占術が株価を予測する」と仮定して開発しない。

### AI産業サイクル・レーダー
以下5ゲージを別系統で研究する。
- AI需要
- AI生産
- AIインフラ
- AI利益
- AI市場

状態候補:
expansion → overheating → slowdown → contraction → bottoming → recovery

ルールはまだ確定していない。AIが勝手に確定しない。

## 5. 現在の主要データ構造

### Quantpedia
- GitHub ActionsでRSSを自動収集。
- 保存先: research-data/research/research_watch.json
- bodyは保存しない。
- 毎朝7:30 JST。

### Astro events
- scripts/generate_astro_events.py
- .github/workflows/generate_astro_events.yml
- ephem==4.2.1
- 2015～2027を計算。
- fortune_records.json に404件のastro eventを保持。
- イベント:
  - new_moon
  - full_moon
  - mercury_retrograde_start
  - mercury_retrograde_end
- 外部サイトは使用しない。
- MMA手動記録もfortune_records.jsonに入る。

### FRED検証
現在の5系列:
- NIKKEI225 / 日経平均
- SP500 / S&P500
- VIXCLS / VIX
- DEXJPUS / USDJPY(円/ドル)
- DCOILWTICO / WTI原油

scripts/test_fred.py は候補9系列をテストする:
SP500, NASDAQCOMP, NIKKEI225, VIXCLS, DEXJPUS, DCOILWTICO, GOLDAMGBD228NLBM, TOPIX, SOX

### fortune_validation.json
保存先:
research-data/validation/fortune_validation.json

これは原データとして保護する。今回の集計処理で書き換えない。

ルール:
- event dayのprevious observed business-day closeをbaseにする。
- 1D/5D/20Dは各系列の観測日ベース。
- 保存するのはreturnのみ。
- 20D未到達はnull、後日到達したら補完可能だが、完了済み値は変更しない。
- 通常日の比較データはこのファイルには保存しない。

## 6. 現在の統計集計

集計スクリプト:
scripts/summarize_fortune.py

現在SHA:
91edd84f25d7cf02f37f7dad000df266357f4049

出力:
research-data/validation/fortune_validation_summary.json

検定単位:
4 event types × 5 series × 3 horizons = 60 tests

horizon:
1D / 5D / 20D

現在の固定条件:
- randomization iterations = 10,000
- random seed = 20261003
- Bonferroni ×60
- p値は両側
- nullは除外
- event_valuesとnormal_valuesの平均差を比較
- 通常日は同じ期間のFRED実観測日だけを候補とする
- event datesは通常日から除外
- return計算はbase_prev_close_v1と同じ

### 直近の重要修正

以前の実装では通常日候補を暦日ループで作っていたため、週末等が重複して通常日群に入る問題があった。

現在は以下の方針に修正済み:
- FRED実観測日だけを通常日候補にする。
- event dateを除外。
- 期間開始はbisect_left。
- 期間終了はbisect_right。
- したがってend_dateが休日/週末でも、end_dateより後の最初の営業日を誤って含めない。

この修正は統計検証ルールの変更ではなく、通常日候補の実装バグ修正。

## 7. 現在のGitHub Actions

### Summarize Fortune
.github/workflows/summarize_fortune.yml

現在SHA:
7464e2ce6cd0b6c7940c3cb0f7fb34aa6aa8e645

動作:
- Validate Fortune成功後に実行
- workflow_dispatchでも手動実行可能
- Python 3.12
- FRED_API_KEYを使用
- fortune_validation_summary.jsonを生成
- 変更があればGitHubへcommit/push

## 8. 現在の最重要未完了タスク

まだ確認できていないこと:
1. Summarize Fortune Actionsを実行したか
2. fortune_validation_summary.jsonが正常生成されたか
3. 修正後のnormal_day_countが妥当か
4. 通常日平均・p値が修正前からどう変化したか
5. 期間終端の取りこぼし/1件ずれがないか
6. 60検定・10,000回・seed固定・Bonferroni×60が維持されているか
7. 統計手法としてのpermutation実装が仕様と一致しているか

## 9. 重要な未解決統計論点

現在のスクリプトdocstring/metadataでは、
「event dates are reassigned as whole dates」
という説明になっている。

一方、実装の permutation_p_value() は現在、
pooled = event_values + normal_values
として値をsampleしている。

つまり、「日付を無作為化して再計算する」という説明と「return値を直接sampleする」実装に差がある可能性がある。

これは統計検証方法そのものに関係するため、ChatGPTが勝手に変更しない。
まずClaude AIに再レビューしてもらい、必要ならユーザー承認事項として扱う。

また、同一日に複数イベントがある場合の通常日プールで、別イベントの日を通常日として含める可能性がある。この扱いも、現仕様を変更せず、必要ならレビュー対象とする。

## 10. 変更禁止

以下は勝手に変更しない:
- research-data/validation/fortune_validation.json
- fortune_records.json
- 過去の検証結果
- 60検定という枠組み
- 10,000回
- seed=20261003
- Bonferroni×60
- base_prev_close_v1
- プロジェクト目的

統計検証方法そのものの変更も、人間の承認なしには行わない。

## 11. 新しいチャットで最初に行うこと

新チャットでは、まずこの引き継ぎ書を読み、
GitHubの現在状態を確認する。

その後、以下の順番で進める。

1. Summarize FortuneのActions実行状況を確認
2. fortune_validation_summary.jsonの存在・内容を確認
3. normal_day_countを確認
4. 修正前後の差を確認できる場合は比較
5. 期間境界を確認
6. 60/10,000/seed/Bonferroniを確認
7. permutation実装の仕様整合性をレビュー
8. 必要ならClaude AIへレビュー依頼
9. 問題なければ次の開発へ進む

## 12. Claude AIへの確認ルール

Claudeに確認した方がよい場合は、ユーザーに単に「Claudeに聞いてください」と言わない。

必ず、
【Claude AIへそのまま送ってください】
という見出しを付け、Claudeが単独で理解できる完成したメッセージを作る。

ユーザーはClaudeへの技術的な伝言役にならない。

## 13. 新チャット開始時の指示

以下を新チャットの最初のメッセージとして貼り付ければよい。

「このプロジェクト引き継ぎ書を前提に作業を再開してください。
ただし、記載されたSHAや状態を盲目的に信用せず、必ずGitHubの現在ファイルを確認してください。
コード・YAMLを変更する場合は、変更前に対象ファイルを取得して確認してください。
推測で変更しないでください。
まず『現在の状態確認 → 最優先タスク → 次にやること』の順で報告してください。
現在の最優先タスクはSummarize FortuneのActions結果とfortune_validation_summary.jsonの検証です。
統計手法そのものを変更する場合は、勝手に実装せずClaude AIレビューと人間承認に回してください。」

## 14. 完了条件

このプロジェクトでは、コードが書けた時点を完了としない。

最低限:
- 実装済み
- テスト済み
- GitHub現在状態確認済み
- 関連箇所確認済み
- 統計ルール確認済み
- Claudeレビューが必要な場合はレビュー済み
- 重要な変更記録済み
- 次のAIが引き継げる状態

を満たすこと。

---

## 現在の最重要メモ

2026/10/04時点では、
「通常日を暦日で数えてしまう実装バグ」は修正済み。

次はActionsを実行し、生成された
research-data/validation/fortune_validation_summary.json
を実データとしてレビューする段階。

ここから先は、結果を見て都合よく検定ルールを変更しないこと。
