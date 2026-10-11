# GREEN GLOW EDINET MVP 引継ぎ（2026-10-12）

再開キーワード：**GREEN GLOW再開**

## 現在の作業
Windows PC 上で EDINET MVP の小規模試験を準備中。まだ EDINET への接続・実データ取得は実行していない。

## 承認範囲と禁止事項
- 実行環境：ユーザー自身の Windows PC
- 取得対象：P2 のみ（2024-08-01〜2024-08-31）
- ユーザーは、この範囲での実行・実データ取得を承認済み
- コード変更、GitHub Actions 登録、保留事項の解決は別途承認なしに行わない
- APIキーをチャットやGitHubに貼らない。キーの値を出力・保存しない
- 既存データや既存ファイルを推測で変更しない

## Dropbox のスクリプト（確認済み）
- `edinet_fetch.py` v3、7,672 bytes
  - Dropboxフォルダ：`/AI産業サイクル/レビュー専用/20261010_mvp_split_v3/`
- `edinet_parse.py` v3.1、12,720 bytes
  - Dropboxフォルダ：`/AI産業サイクル/レビュー専用/20261010_mvp_split_v3_1/`
- PC上の保存先：`C:\GREEN_GLOW_EDINET\`
- PC上のファイルサイズは一致済み：fetch 7,672 bytes、parse 12,720 bytes
- SHA-256照合は未実施。GitHubにはスクリプト未保存。

## Windows PC の準備状況（ユーザーが実行して確認）
- Python 3.15.0
- 仮想環境：`C:\GREEN_GLOW_EDINET\.venv` 作成済み
- `requests 2.34.2`、`pandas 3.0.6` のインストールと import 確認済み
- PowerShell の現在のセッションで以下を設定済み：
  - `EDINET_WINDOWS=P2`
  - `APPROVED_TO_RUN=YES`
  - `EDINET_KEY` は設定済み（キー値はこのファイルに記録しない）
- 重要：APIキーは現在のPowerShellセッションの環境変数に入っている。PowerShellを閉じると失われるため、次の作業を続ける場合はそのウィンドウを閉じないこと。新しいチャットからPCを直接操作することはできない。

## 次に行うこと（ここから再開）
1. ユーザーの現在の PowerShell（`PS C:\GREEN_GLOW_EDINET>`）で、実行前の最終チェックを行う：
```powershell
if ($env:EDINET_WINDOWS -ne "P2") {
    throw "停止：P2以外が指定されています"
}
if ($env:APPROVED_TO_RUN -ne "YES" -or -not $env:EDINET_KEY) {
    throw "停止：実行承認またはAPIキーの設定を確認してください"
}
Write-Host "最終チェックOK：P2のみ"
```
2. 結果が `最終チェックOK：P2のみ` の場合のみ、承認済みP2取得を実行：
```powershell
.\.venv\Scripts\python.exe .\edinet_fetch.py
```
3. エラーや中断があった場合、結果を確認する前に再実行しない。APIキーを含む出力を共有しない。
4. 実行後、表示された正確な `edinet_raw_...` フォルダ名を使って `run_info.json`、`manifest.csv`、raw JSON件数を点検する。成功しても完全性が保証されたとは扱わない。
5. 取得結果をレビューしてから、初めてネットワーク接続をしないパーサーを実行する：
```powershell
.\.venv\Scripts\python.exe .\edinet_parse.py ".\edinet_raw_YYYYMMDD_HHMMSS"
```
`YYYYMMDD_HHMMSS` は実際のフォルダ名に置換する。実行前にユーザーへ結果確認を求める。

## 未解決・未検証（勝手に解決しない）
- SHA-256によるスクリプト照合
- EDINET API のゼロ件日での `results` キーの公式挙動
- preflight 応答の公式挙動
- `docDescription` と文書種別コードの対応
- M1〜M4
- Python 3.15.0 とスクリプトの実行時互換性（依存ライブラリの import は成功したが、スクリプト全体の実行は未確認）
- EDINET API の公式仕様・ホスト・取得データの完全性

## 再開時の指示
キーワード「GREEN GLOW再開」と、このファイルの内容を参照して、まず現在の PowerShell が開いたままか確認する。次に実行前最終チェックを案内し、P2以外へ対象を拡張しない。既存コードの変更、Actions登録、未解決事項の解決は、ユーザーの別途承認なしに行わない。
