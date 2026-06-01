import os
import requests
from datetime import datetime, timezone, timedelta

LINE_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "U0a00078a576de205f40bf8a05920178b")
HTML_FILE = os.environ.get("HTML_FILE")
GITHUB_PAGES_BASE = os.environ.get("GITHUB_PAGES_BASE")

def get_report_url():
    if HTML_FILE:
        return GITHUB_PAGES_BASE + HTML_FILE
    return GITHUB_PAGES_BASE

def get_report_title():
    if HTML_FILE:
        name = HTML_FILE.replace("investment_report_", "").replace(".html", "")
        if len(name) == 8 and name.isdigit():
            y, m, d = name[:4], name[4:6], name[6:]
            return f"てっちゃまの日米投資戦略レポート｜{y}年{m}月{d}日版 厳選Top10【購入タイミング・出口戦略付き】"
        elif "vol" in name:
            return f"てっちゃまの日米投資戦略レポート {name.upper()}｜日本株・米国株 厳選Top10【購入タイミング・出口戦略付き】"
    # ファイル名がない場合は今日の日付を使う
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    return f"てっちゃまの日米投資戦略レポート｜{today.year}年{today.month:02d}月{today.day:02d}日版 厳選Top10【購入タイミング・出口戦略付き】"

def get_today_date_str():
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst)
    return f"{today.year}年{today.month:02d}月{today.day:02d}日"

def send_line_message():
    url = get_report_url()
    title = get_report_title()
    today = get_today_date_str()

    message = (
        f"noteタイトル：{title}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 てっちゃまの日米投資戦略レポート\n"
        f"{today}版\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"GitHubに本日の投資レポートが公開されました！\n\n"
        f"noteへの投稿手順\n"
        f"1. noteを開く\n"
        f"2. 投稿する → テキスト\n"
        f"3. ＋ → 埋め込み → 下記URLを貼り付け\n"
        f"4. 上記タイトルをコピーして入力\n"
        f"5. 公開ボタンをクリック\n\n"
        f"レポートURL\n"
        f"{url}"
    )

    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }

    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=payload
    )

    print(f"LINE送信結果: {response.status_code}")
    print(f"レスポンス: {response.text}")

    if response.status_code == 200:
        print("✅ LINE通知を送信しました！")
        return True
    else:
        print(f"❌ LINE送信エラー: {response.text}")
        return False

if __name__ == "__main__":
    if not HTML_FILE:
        print("対象のHTMLファイルが見つかりません。今日の日付でタイトルを生成します。")

    print(f"対象ファイル: {HTML_FILE}")
    print(f"レポートURL: {get_report_url()}")
    print(f"タイトル: {get_report_title()}")

    success = send_line_message()
    exit(0 if success else 1)
