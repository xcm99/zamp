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

    # 1️⃣ 执行 renew
    r = s.get(RENEW_URL, headers=HEADERS, allow_redirects=False, timeout=15)

    if r.status_code in (301, 302):
        loc = r.headers.get("Location", "")
        if "sign-in" in loc:
            fail("Session expired (redirected to login)")

    if r.status_code not in (200, 302):
        fail(f"Unexpected renew status: {r.status_code}")

    # 2️⃣ 再次访问 server 页面，验证状态
    r2 = s.get(SERVER_URL, headers=HEADERS, timeout=15)

    if "sign-in" in r2.url:
        fail("Lost login after renew")

    html = r2.text.lower()

    # === 关键成功特征（可按你页面微调）===
    success_keywords = [
        "next billing",
        "renewed",
        "expires",
        "valid until"
    ]

    if not any(k in html for k in success_keywords):
        fail("Renew page loaded but no success indicators found")

    print("🎉 Zampto VPS renewed successfully")

if __name__ == "__main__":
    main()
