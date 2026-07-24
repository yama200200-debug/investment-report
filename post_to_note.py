"""
post_to_note.py

役割: 新しいレポートHTMLがGitHub Pagesに公開されたことを
LINE Messaging API (push message) で通知する。

note.com への自動投稿は行わない（NOTE_EMAIL/NOTE_PASSWORD は未使用のまま）。

必要な環境変数:
  LINE_CHANNEL_ACCESS_TOKEN  … LINE Developersコンソールの
                               「チャネルアクセストークン（長期）」
                               ※ GitHub Secretsに新規登録が必要
  LINE_USER_ID               … 通知先ユーザーID（登録済み）
  HTML_FILE                  … 対象のHTMLファイル名（ワークフロー側で算出）
  GITHUB_PAGES_BASE          … 例: https://yama200200-debug.github.io/investment-report/
"""

import os
import sys
import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def build_message(html_file: str, pages_base: str) -> str:
    report_url = pages_base.rstrip("/") + "/" + html_file
    return f"新しいレポートが公開されました\n{report_url}"


def main() -> None:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    html_file = os.environ.get("HTML_FILE")
    pages_base = os.environ.get("GITHUB_PAGES_BASE")

    missing = [
        name
        for name, val in [
            ("LINE_CHANNEL_ACCESS_TOKEN", token),
            ("LINE_USER_ID", user_id),
            ("HTML_FILE", html_file),
            ("GITHUB_PAGES_BASE", pages_base),
        ]
        if not val
    ]
    if missing:
        print(f"必須の環境変数が設定されていません: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    message_text = build_message(html_file, pages_base)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message_text}],
    }

    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=10)

    if resp.status_code != 200:
        print(f"LINE通知の送信に失敗しました: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    print(f"LINE通知を送信しました: {message_text}")


if __name__ == "__main__":
    main()
