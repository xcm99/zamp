import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= Telegram =================
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(msg: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("⚠️ Telegram 未配置，跳过通知")
        return

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        data={
            "chat_id": TG_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        },
        timeout=10
    )

def mask_email(email: str) -> str:
    """
    只显示邮箱前三位，其余用 *** 代替
    例：abc123@gmail.com -> abc***
    """
    return email[:3] + "***"

# ================= Zampto =================
LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"

ZAMPTO_ACCOUNTS_RAW = os.getenv("ZAMPTO_ACCOUNTS")
if not ZAMPTO_ACCOUNTS_RAW:
    raise RuntimeError("❌ 未检测到 ZAMPTO_ACCOUNTS 环境变量")

ACCOUNTS = []
for line in ZAMPTO_ACCOUNTS_RAW.strip().splitlines():
    email, password, server_id = [x.strip() for x in line.split("|")]
    ACCOUNTS.append({
        "email": email,
        "password": password,
        "server_id": server_id
    })

# ================= 核心逻辑 =================
def renew_single_account(account):
    email = account["email"]
    password = account["password"]
    server_id = account["server_id"]

    print(f"\n👤 账号: {email} | VPS: {server_id}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # === 登录 ===
        driver.get(LOGIN_URL)

        email_input = wait.until(
            EC.visibility_of_element_located((By.NAME, "identifier"))
        )
        email_input.clear()
        email_input.send_keys(email)
        driver.find_element(By.NAME, "submit").click()

        password_input = wait.until(
            EC.visibility_of_element_located((By.NAME, "password"))
        )
        password_input.clear()
        password_input.send_keys(password)

        submit_btn = driver.find_element(By.NAME, "submit")
        driver.execute_script("arguments[0].click();", submit_btn)

        wait.until(EC.url_contains("dash.zampto.net"))

        # === 续期 ===
        renew_url = f"https://dash.zampto.net/server?id={server_id}&renew=true"
        driver.get(renew_url)
        time.sleep(5)

        if "login" in driver.current_url:
            raise RuntimeError("登录态丢失，续期失败")

        print(f"✅ 成功：{email} VPS {server_id}")
        return True, email, server_id

    except Exception as e:
        print(f"❌ 失败：{email} VPS {server_id} | {e}")
        return False, email, server_id

    finally:
        driver.quit()

def main():
    success = []
    failed = []

    for account in ACCOUNTS:
        ok, email, sid = renew_single_account(account)
        if ok:
            success.append((email, sid))
        else:
            failed.append((email, sid))

    # === Telegram 汇总 ===
    msg = "📦 <b>Zampto 多账号 VPS 续期结果</b>\n\n"

    if success:
        msg += "✅ <b>成功</b>\n"
        for email, _ in success:
            msg += f"• {mask_email(email)}\n"

    if failed:
        msg += "\n❌ <b>失败</b>\n"
        for email, _ in failed:
            msg += f"• {mask_email(email)}\n"


    send_telegram(msg)

if __name__ == "__main__":
    main()
