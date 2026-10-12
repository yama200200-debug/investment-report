# GREEN GLOW 引き継ぎ追記（2026-10-12 夜：EDINET個別取得スクリプト修正準備）

対象リポジトリ: `yama200200-debug/investment-report`
既存引き継ぎ: [PROJECT_HANDOFF_2026-10-12_EDINET.md](PROJECT_HANDOFF_2026-10-12_EDINET.md)、[PROJECT_HANDOFF_2026-10-11.md](PROJECT_HANDOFF_2026-10-11.md)、[AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md)
合言葉: **GREEN GLOW再開**

## 1. 現在のローカル状態

ユーザーPCの作業場所は `C:\GREEN_GLOW_EDINET`、PowerShellの `.venv` が開いたままの予定。ユーザーが読み取り専用検査を実行し、4本の現行ファイルについて構文PASS、DOC_IDあり、`APPROVED_TO_RUN` ガードあり、`EDINET_KEY` ガードあり、バックアップ一致=Trueを確認した。

- `edinet_fetch_single_S100T22O.py` — SHA-256 `9ec53387648e3f832d5f8eefcd97a0efaa4345201354fdd923e663bd2e654504`
- `edinet_fetch_single_S100U4Q6.py` — SHA-256 `c54250c6b4e92930aac4a4561962048cf49a081366e03a4d347d45b1241c2f1e`
- `edinet_fetch_single_S100U7KV.py` — SHA-256 `04b55f0168830d9bc5bcad7fc2f83776756734794fc2980c50bb9f76ac886e37`
- `edinet_fetch_single_S100U8T2.py` — SHA-256 `c510043f6a8a9f59f56b863cf1840e86d3d9d59057bf1dad4e839db0322bcc5d`

バックアップディレクトリ: `backup_fetch_scripts_20261012_180253`。4本すべて現行ファイルと一致。

## 2. 候補作成の失敗（必ず注意）

以下の候補ディレクトリが存在する。候補作成に使ったロジックに誤りがあり、候補の一つではファイル先頭のimports、DOC_ID、承認ガード、APIキーガードなどが失われた。4候補が同じSHA-256になったため検査で不合格。候補は未適用。

- `candidate_fetch_scripts_20261012_183103`
- `candidate_fetch_scripts_retry_20261012_183656`
- `candidate_fetch_scripts_clean_20261012_183904`

**候補ファイルは実行・適用しない。** 削除もユーザーの明示承認なしにしない。現行ファイルはバックアップと一致し、変更されていない。

## 3. 保存処理アンカー（4本共通）

各元ファイルは104行。読み取り専用検査で確認した位置:
- 48行目: `out_dir = Path.cwd() / f"edinet_single_{DOC_ID}_{stamp}"`
- 62行目: `created = False`（保存処理開始）
- 67行目以降: PDF/manifestの一時保存と検証
- 82行目以降: 失敗時の後片付け
- 99〜102行目: 既存の日本語完了メッセージ、保存先、サイズ、SHA-256

最後にユーザーへ提示した読み取り専用コマンドは、4本の61〜98行目を表示するもの。**実行結果はこの引き継ぎ作成時点ではまだ受領していない。** 新チャットでは、その結果が実行済みか先に確認する。

## 4. 次の作業

1. まずユーザーに、保存ブロック61〜98行目の読み取り専用表示結果を確認する。
2. 候補を作り直す場合、元ファイル全文を保持し、確認済みの保存処理部分だけを置換する。以前の失敗は誤った位置からソースを切り出し、ファイル先頭を失ったこと。**部分文字列をソース全体として扱わない。**
3. アンカーが期待どおり一意に存在するかを確認し、曖昧なら停止する。
4. 候補は別ディレクトリに作り、元ファイルは変更しない。各候補の構文解析・compile・DOC_ID・承認ガード・APIキーガード・日本語メッセージ保持・保存処理を検証し、差分を確認する。4候補のSHA-256がすべて同じなら異常として停止する。
5. 候補検証が通るまで元ファイルへ適用しない。実API通信やEDINET再取得もしない。
6. APIキーやPDF本体・manifestをGitHubへアップロードしない。GitHubにはこの引き継ぎ情報だけを保存する。

## 5. 新チャット開始用メッセージ

「**GREEN GLOW再開**。GitHubの `PROJECT_HANDOFF_2026-10-12_EDINET_SCRIPT_PREP.md`、`PROJECT_HANDOFF_2026-10-12_EDINET.md`、`PROJECT_HANDOFF_2026-10-11.md)、`AI_DEVELOPMENT_RULES.md` を現在の内容で確認してください。PowerShellは `C:\GREEN_GLOW_EDINET` の `.venv` で開いたままです。個別取得スクリプト4本は現行ファイルとバックアップのSHA-256が一致し、構文・DOC_ID・承認ガード・APIキーガードもPASSです。失敗した候補ディレクトリが3つありますが、未適用で、実行・削除しないでください。最後に提示された読み取り専用コマンドは4本の保存ブロック61〜98行目を表示するものです。その結果を確認し、元ファイルを変更せず候補を作り直すところから進めてください。検証が通るまで元ファイルへの適用やAPI通信をしないでください。現在状態と次の一手を【結論】【手順】【注意】【次アクション】で報告してください。」
