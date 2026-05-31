import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

NOTE_EMAIL = os.environ.get("NOTE_EMAIL")
NOTE_PASSWORD = os.environ.get("NOTE_PASSWORD")
LINE_TOKEN = os.environ.get("LINE_NOTIFY_TOKEN")
HTML_FILE = os.environ.get("HTML_FILE")
GITHUB_PAGES_BASE = os.environ.get("GITHUB_PAGES_BASE")

def send_line_notify(message):
    if LINE_TOKEN and LINE_TOKEN != "dummy_token_for_now":
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
        requests.post(url, headers=headers, data={"message": message})

def get_report_url():
    if HTML_FILE:
        return GITHUB_PAGES_BASE + HTML_FILE
    return GITHUB_PAGES_BASE

def get_report_title():
    if HTML_FILE:
        name = HTML_FILE.replace("investment_report_", "").replace(".html", "")
        if name.startswith("note_vol"):
            vol = name.replace("note_", "").replace("note", "")
            return f"てっちゃまの日米投資戦略レポート{vol.upper()}｜日本株・米国株 厳選Top10【購入タイミング・出口戦略付き】"
        elif len(name) == 8 and name.isdigit():
            y, m, d = name[:4], name[4:6], name[6:]
            return f"てっちゃまの日米投資戦略レポート｜{y}年{m}月{d}日版 厳選Top10【購入タイミング・出口戦略付き】"
    return "てっちゃまの日米投資戦略レポート｜日本株・米国株 厳選Top10"

def post_to_note():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 20)

    try:
        print("noteにログイン中...")
        driver.get("https://note.com/login")
        time.sleep(3)

        email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_field.send_keys(NOTE_EMAIL)

        pass_field = driver.find_element(By.NAME, "password")
        pass_field.send_keys(NOTE_PASSWORD)

        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        time.sleep(5)
        print("ログイン完了")

        print("新規記事作成画面へ移動...")
        driver.get("https://note.com/notes/new")
        time.sleep(5)

        title_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//textarea[@placeholder='タイトル']")))
        title = get_report_title()
        title_field.send_keys(title)
        time.sleep(1)

        body_field = driver.find_element(By.XPATH, "//div[@contenteditable='true']")
        report_url = get_report_url()
        body_content = f"""本日の投資戦略レポートを公開しました。

📊 レポートはこちらからご覧いただけます：
{report_url}

※ CodePenのエリアで「Run Pen」ボタンをクリックするとレポートが表示されます。

#投資 #株式投資 #日本株 #米国株 #NISA #投資初心者"""

        body_field.click()
        body_field.send_keys(body_content)
        time.sleep(2)

        print("埋め込みURLを追加中...")
        driver.execute_script("""
            const event = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true});
            document.activeElement.dispatchEvent(event);
        """)
        time.sleep(1)

        print("公開ボタンをクリック...")
        publish_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'公開設定')]")))
        publish_btn.click()
        time.sleep(3)

        final_publish = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'投稿')]")))
        final_publish.click()
        time.sleep(5)

        current_url = driver.current_url
        print(f"投稿完了！URL: {current_url}")

        send_line_notify(f"\n✅ 投資レポートをnoteに投稿しました！\n\n📰 タイトル：{title}\n🔗 note URL：{current_url}\n📊 レポート：{report_url}")

        return True

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        send_line_notify(f"\n❌ note自動投稿でエラーが発生しました\nエラー内容：{str(e)}")
        return False

    finally:
        driver.quit()

if __name__ == "__main__":
    if not HTML_FILE:
        print("対象のHTMLファイルが見つかりません")
        exit(1)
    print(f"対象ファイル: {HTML_FILE}")
    success = post_to_note()
    exit(0 if success else 1)
