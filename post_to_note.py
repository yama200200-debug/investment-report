import os
import time
import requests

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
            return f"てっちゃまの日米投資戦略レポート｜{y}年{m}月{d}日版"
        elif "vol" in name:
            return f"てっちゃまの日米投資戦略レポート {name.upper()}"
    return "てっちゃまの日米投資戦略レポート"

def send_line_message():
    url = get_report_url()
    title = get_report_title()
    
    message = (
        f"📊 {title}\n\n"
        f"✅ GitHubに新しいレポートがアップロードされました！\n\n"
        f"🔗 レポートURL：\n{url}\n\n"
        f"📝 noteに投稿する手順：\n"
        f"1. noteを開く\n"
        f"2. 新規記事作成\n"
        f"3. 「埋め込み」でURLを貼り付け\n"
        f"4. タイトルを入力して公開\n\n"
        f"⏱ 作業時間：約2分"
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
        print("対象のHTMLファイルが見つかりません")
        exit(1)
    
    print(f"対象ファイル: {HTML_FILE}")
    print(f"レポートURL: {get_report_url()}")
    
    success = send_line_message()
    exit(0 if success else 1)
