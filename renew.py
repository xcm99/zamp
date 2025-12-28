import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC




# ================= 配置区 =================
USERNAME = os.getenv("ZAMPTO_EMAIL")
PASSWORD = os.getenv("ZAMPTO_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError("❌ 未检测到 ZAMPTO_USER / ZAMPTO_PASS 环境变量")

SERVER_ID = "2190"

LOGIN_URL = "https://auth.zampto.net/sign-in?app_id=bmhk6c8qdqxphlyscztgl"
DASH_URL = f"https://dash.zampto.net/server?id={SERVER_ID}"
RENEW_URL = f"https://dash.zampto.net/server?id={SERVER_ID}&renew=true"
# =========================================

def run_task():
    print("🚀 启动 Zampto 自动续期流程 (v7 源码精准版)...")

    # --- 浏览器配置 ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # === 步骤 1: 输入账号 ===
        print(f"Testing Login URL: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        print("1️⃣  精准锁定【用户名】输入框 (name='identifier')...")
        # 依据: name="identifier"
        email_input = wait.until(EC.visibility_of_element_located((By.NAME, "identifier")))
        email_input.clear()
        email_input.send_keys(USERNAME)

        print("   点击【登录】按钮 (name='submit')...")
        # 依据: name="submit"
        driver.find_element(By.NAME, "submit").click()

        # === 步骤 2: 输入密码 ===
        print("2️⃣  精准锁定【密码】输入框 (name='password')...")
        # 依据: <input name="password" ...>
        password_input = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        password_input.clear()
        password_input.send_keys(PASSWORD)

        print("   点击【继续】按钮 (name='submit')...")
        # 依据: <button name="submit" ...>
        submit_btn = driver.find_element(By.NAME, "submit")
        driver.execute_script("arguments[0].click();", submit_btn)

        # === 步骤 3: 提取 Cookie ===
        print("3️⃣  等待登录跳转...")
        wait.until(EC.url_contains("dash.zampto.net"))
        print("   ✅ 登录成功，跳转至控制台...")

        driver.get(DASH_URL)
        time.sleep(2)

        # 提取 Session
        cookies = driver.get_cookies()
        phpsessid_value = next((c['value'] for c in cookies if c['name'] == 'PHPSESSID'), None)
        if phpsessid_value:
            print(f"   🔑 PHPSESSID: {phpsessid_value}")
        
        # === 步骤 4: 续期 ===
        print(f"4️⃣  执行续期请求: {RENEW_URL}")
        driver.get(RENEW_URL)
        time.sleep(5)
        
        # 结果判断
        if "login" in driver.current_url:
            print("❌ 失败: 掉线了，被重定向回登录页")
            exit(1)
        else:
             print("🎉 续期脚本执行完毕。")
             print(f"   最终 URL: {driver.current_url}")

    except Exception as e:
        print("\n❌❌❌ 发生错误 ❌❌❌")
        print(f"错误信息: {e}")
        exit(1)

    finally:
        driver.quit()

if __name__ == "__main__":
    run_task()





