import os
import requests
from notify import telegram_notify, email_notify

PHPSESSID = os.getenv("ZAMPTO_PHPSESSID")
SERVER_ID = os.getenv("ZAMPTO_SERVER_ID")

if not PHPSESSID or not SERVER_ID:
    raise RuntimeError("Missing PHPSESSID or SERVER_ID")

BASE_URL = "https://dash.zampto.net"
SERVER_URL = f"{BASE_URL}/server?id={SERVER_ID}"
RENEW_URL = f"{SERVER_URL}&renew=true"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": SERVER_URL,
}

def fail(msg: str):
    telegram_notify(f"❌ <b>Zampto Renew Failed</b>\n{msg}")
    email_notify("Zampto Renew Failed", msg)
    raise RuntimeError(msg)

def main():
    print("🚀 Zampto renew start (requests-only)")

    s = requests.Session()
    s.cookies.set("PHPSESSID", PHPSESSID, domain=".zampto.net", path="/")

        # 4️⃣ 打开 VPS 管理页
        driver.get(VPS_MANAGE_URL)

        # 5️⃣ 定位 Renew Server 按钮
renew_btn = wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//a[contains(@onclick,'handleServerRenewal')]")
    )
)

# 6️⃣ 滚动 + 点击
driver.execute_script(
    "arguments[0].scrollIntoView({block:'center'});", renew_btn
)
time.sleep(1)

try:
    renew_btn.click()
except:
    driver.execute_script("arguments[0].click();", renew_btn)

print("✅ Renew Server button clicked")


        # 7️⃣ 可选：确认续期
        if "success" in driver.page_source.lower():
            print("🎉 Renew success")
        else:
            print("⚠️ Renew maybe pending or requires confirmation")

    finally:
        driver.quit()




if __name__ == "__main__":
    main()

