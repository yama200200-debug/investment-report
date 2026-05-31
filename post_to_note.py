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
        if len(name) == 8 and name.isdigit():
            y, m, d = name[:4], name[4:6], name[6:]
            return f"てっちゃまの日米投資戦略レポート｜{y}年{m}月{d}日版 厳選Top10【購入タイミング・出口戦略付き】"
        elif "vol" in name:
            return f"てっちゃまの日米投資戦略レポート {name.upper()}｜日本株・米国株 厳選Top10【購入タイミング・出口戦略付き】"
    return "てっちゃまの日米投資戦略レポート｜日本株・米国株 厳選Top10"

def post_to_note():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)

    try:
        print("noteのログインページを開いています...")
        driver.get("https://note.com/login")
        time.sleep(5)
        
        print(f"現在のURL: {driver.current_url}")
        print(f"ページタイトル: {driver.title}")

        # メールアドレス入力
        try:
            email_field = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@type='email' or @name='email' or @id='email']")))
            email_field.clear()
            email_field.send_keys(NOTE_EMAIL)
            print("メールアドレスを入力しました")
        except Exception as e:
            print(f"メールアドレス入力エラー: {e}")
            # ページのHTMLを出力してデバッグ
            print(driver.page_source[:2000])
            raise

        time.sleep(1)

        # パスワード入力
        try:
            pass_field = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//input[@type='password' or @name='password' or @id='password']")))
            pass_field.clear()
            pass_field.send_keys(NOTE_PASSWORD)
            print("パスワードを入力しました")
        except Exception as e:
            print(f"パスワード入力エラー: {e}")
            raise

        time.sleep(1)

        # ログインボタンクリック
        try:
            login_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@type='submit']")))
            login_btn.click()
            print("ログインボタンをクリックしました")
        except Exception as e:
            print(f"ログインボタンエラー: {e}")
            raise

        time.sleep(8)
        print(f"ログイン後URL: {driver.current_url}")

        # ログイン確認
        if "login" in driver.current_url:
            print("ログインに失敗しました。メールアドレスとパスワードを確認してください。")
            print(driver.page_source[:1000])
            raise Exception("ログイン失敗")

        print("ログイン成功！新規記事作成画面へ移動...")
        driver.get("https://note.com/notes/new")
        time.sleep(8)
        
        print(f"記事作成ページURL: {driver.current_url}")

        # タイトル入力
        title = get_report_title()
        try:
            title_field = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//textarea[@placeholder='タイトル'] | //input[@placeholder='タイトル'] | //div[@data-placeholder='タイトル']")))
            title_field.click()
            title_field.send_keys(title)
            print(f"タイトルを入力しました: {title}")
        except Exception as e:
            print(f"タイトル入力エラー: {e}")
            raise

        time.sleep(2)

        # 本文入力
        report_url = get_report_url()
        body_content = f"""本日の投資戦略レポートを公開しました。

📊 レポートはこちらからご覧いただけます：
{report_url}

※ページ内の「Run Pen」ボタンをクリックするとレポートが表示されます。

#投資 #株式投資 #日本株 #米国株 #NISA #投資初心者 #てっちゃま"""

        try:
            body_field = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[@contenteditable='true' and not(@data-placeholder='タイトル')]")))
            body_field.click()
            time.sleep(1)
            body_field.send_keys(body_content)
            print("本文を入力しました")
        except Exception as e:
            print(f"本文入力エラー: {e}")
            raise

        time.sleep(2)

        # 公開設定ボタン
        try:
            publish_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'公開設定') or contains(text(),'公開') or contains(@class,'publish')]")))
            publish_btn.click()
            print("公開設定ボタンをクリックしました")
        except Exception as e:
            print(f"公開設定ボタンエラー: {e}")
            # ボタン一覧を表示
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                print(f"ボタン: {btn.text}")
            raise

        time.sleep(4)

        # 投稿ボタン
        try:
            final_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'投稿する') or contains(text(),'投稿') or contains(text(),'公開する')]")))
            final_btn.click()
            print("投稿ボタンをクリックしました")
        except Exception as e:
            print(f"投稿ボタンエラー: {e}")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                print(f"ボタン: {btn.text}")
            raise

        time.sleep(8)

        current_url = driver.current_url
        print(f"✅ 投稿完了！URL: {current_url}")

        send_line_notify(
            f"\n✅ 投資レポートをnoteに投稿しました！\n"
            f"📰 タイトル：{title}\n"
            f"🔗 note URL：{current_url}\n"
            f"📊 レポート：{report_url}"
        )

        return True

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        send_line_notify(f"\n❌ note自動投稿でエラーが発生しました\nエラー内容：{str(e)[:100]}")
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
