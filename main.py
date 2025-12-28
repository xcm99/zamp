#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zampto 登录脚本 - 直接URL续期版本
通过添加renew=true参数直接续期，并输出原始结果
"""

import os
import sys
import time
import json
import random
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError


class ZamptoLogin:
    def __init__(self):
        """初始化，从环境变量读取配置"""
        self.url = os.getenv('ZAMPTO_URL', 'https://hosting.zampto.net')
        self.server_urls = os.getenv('ZAMPTO_SERVER_URLS', '')
        self.auth_url = os.getenv('ZAMPTO_AUTH_URL', 'https://hosting.zampto.net/auth')
        self.accounts_url = os.getenv('ZAMPTO_ACCOUNTS_URL', 'https://accounts.zampto.net/auth')
        
        # 获取认证信息
        self.email = os.getenv('ZAMPTO_EMAIL', '')
        self.password = os.getenv('ZAMPTO_PASSWORD', '')
        
        # 浏览器配置
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # 解析服务器URL列表
        self.server_list = []
        if self.server_urls:
            self.server_list = [url.strip() for url in self.server_urls.split(',') if url.strip()]
    
    def log(self, message, level="INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def has_email_auth(self):
        """检查是否有邮箱密码认证信息"""
        return bool(self.email and self.password)
    
    def check_login_status(self, page):
        """检查是否已登录到hosting页面"""
        try:
            current_url = page.url
            self.log(f"检查登录状态，当前URL: {current_url}")
            
            # 情况1: 已经在hosting首页
            if current_url == self.url or current_url.startswith(self.url + '/'):
                content = page.content().lower()
                if any(keyword in content for keyword in ["welcome back", "dashboard", "server"]):
                    self.log("✅ 已登录到hosting首页")
                    return True
                else:
                    self.log("⚠️ 在hosting页面但未检测到登录迹象")
                    return False
            
            # 情况2: 在accounts页面但显示快速登录（已登录状态）
            elif "accounts.zampto.net" in current_url:
                content = page.content()
                if "quick login" in content.lower() or "快速登录" in content:
                    self.log("✅ 检测到已登录到accounts页面（快速登录界面）")
                    return True
                else:
                    self.log("❌ 在accounts页面但未登录")
                    return False
            
            # 情况3: 验证失败重定向
            elif "secure-failure=validation" in current_url:
                self.log("⚠️ 检测到验证失败重定向，尝试处理...")
                return self.handle_validation_failure(page)
            
            else:
                self.log(f"❌ 未知页面状态: {current_url}")
                return False
                
        except Exception as e:
            self.log(f"检查登录状态时出错: {e}", "ERROR")
            return False
    
    def handle_validation_failure(self, page):
        """处理验证失败的重定向"""
        try:
            self.log("处理验证失败重定向...")
            
            # 保存当前页面状态用于分析
            content = page.content()
            
            # 检查是否是快速登录界面
            if "quick login" in content.lower() and self.email.lower() in content.lower():
                self.log("✅ 检测到快速登录界面，尝试选择当前账户")
                return self.select_current_account_in_quick_login(page)
            # 检查页面内容，确定具体的失败原因
            elif "email" in content.lower() or "password" in content.lower():
                self.log("⚠️ 验证失败但仍有登录表单，尝试重新登录")
                return self.retry_login(page)
            else:
                self.log("⚠️ 验证失败，尝试直接访问首页")
                return self.try_direct_access(page)
                
        except Exception as e:
            self.log(f"处理验证失败时出错: {e}", "ERROR")
            return False
    
    def select_current_account_in_quick_login(self, page):
        """在快速登录界面选择当前账户"""
        try:
            self.log("在快速登录界面选择当前账户...")
            
            # 查找包含邮箱的账户选择按钮
            account_selectors = [
                f'button:has-text("{self.email}")',
                f'div:has-text("{self.email}")',
                f'//*[contains(text(), "{self.email}")]/ancestor::button',
                f'//*[contains(text(), "{self.email}")]/ancestor::div[contains(@class, "button")]',
                'button:has-text("Continue")',
                'button:has-text("Log in")',
                'button:has-text("使用此账户")'
            ]
            
            for selector in account_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        element = elements.first
                        if element.is_visible():
                            self.log(f"找到账户选择元素: {selector}")
                            element.click()
                            time.sleep(3)
                            
                            # 检查是否成功跳转
                            if self.check_login_status(page):
                                return True
                            break
                except Exception as e:
                    self.log(f"尝试选择器 {selector} 时出错: {e}", "DEBUG")
                    continue
            
            self.log("❌ 未找到合适的账户选择按钮，尝试截图分析")
            # 保存截图用于调试
            try:
                page.screenshot(path="quick_login_debug.png")
                self.log("已保存截图: quick_login_debug.png")
            except:
                pass
            
            return False
            
        except Exception as e:
            self.log(f"选择账户时出错: {e}", "ERROR")
            return False
    
    def retry_login(self, page):
        """验证失败后重新尝试登录"""
        try:
            self.log("重新尝试登录...")
            
            # 重新查找登录表单元素
            email_selectors = ['input[name="email"]', 'input[type="email"]']
            password_selectors = ['input[name="password"]', 'input[type="password"]']
            submit_selectors = ['button[type="submit"]']
            
            # 查找并填写表单
            email_field = None
            for selector in email_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        email_field = page.locator(selector).first
                        break
                except:
                    continue
            
            if not email_field:
                self.log("❌ 重新登录: 未找到邮箱输入框")
                return False
            
            password_field = None
            for selector in password_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        password_field = page.locator(selector).first
                        break
                except:
                    continue
            
            if not password_field:
                self.log("❌ 重新登录: 未找到密码输入框")
                return False
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        submit_button = page.locator(selector).first
                        break
                except:
                    continue
            
            if not submit_button:
                self.log("❌ 重新登录: 未找到提交按钮")
                return False
            
            # 清除字段并重新填写
            self.log("重新填写登录信息...")
            email_field.click()
            email_field.fill('')
            self.human_like_typing(email_field, self.email)
            
            password_field.click()
            password_field.fill('')
            self.human_like_typing(password_field, self.password)
            
            time.sleep(1)
            
            # 重新提交
            self.log("重新提交登录表单...")
            submit_button.click()
            time.sleep(5)
            
            # 检查结果
            return self.check_login_status(page)
                
        except Exception as e:
            self.log(f"重新登录时出错: {e}", "ERROR")
            return False
    
    def try_direct_access(self, page):
        """验证失败后尝试直接访问首页"""
        try:
            self.log("尝试直接访问hosting首页...")
            
            # 方法1: 直接访问hosting首页
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3)
            
            if self.check_login_status(page):
                self.log("✅ 直接访问首页成功")
                return True
            
            # 方法2: 访问hosting auth页面
            self.log("尝试访问hosting auth页面...")
            page.goto(self.auth_url, wait_until="domcontentloaded")
            time.sleep(3)
            
            if self.check_login_status(page):
                self.log("✅ 通过auth页面跳转成功")
                return True
            
            # 方法3: 检查是否有重定向或自动跳转
            self.log("检查是否有自动跳转...")
            time.sleep(5)
            
            if self.check_login_status(page):
                self.log("✅ 自动跳转成功")
                return True
            
            self.log("❌ 所有直接访问方法都失败")
            return False
            
        except Exception as e:
            self.log(f"直接访问时出错: {e}", "ERROR")
            return False
    
    def navigate_to_hosting_from_accounts(self, page):
        """从accounts页面跳转到hosting页面"""
        try:
            self.log("从accounts页面跳转到hosting页面...")
            
            # 尝试直接访问hosting首页
            page.goto(self.url, wait_until="domcontentloaded")
            time.sleep(3)
            
            if self.check_login_status(page):
                self.log("✅ 直接跳转到hosting成功")
                return True
            
            # 如果还在accounts页面，尝试访问auth页面
            if "accounts.zampto.net" in page.url:
                page.goto(self.auth_url, wait_until="domcontentloaded")
                time.sleep(3)
                
                if self.check_login_status(page):
                    self.log("✅ 通过auth页面跳转成功")
                    return True
            
            self.log("❌ 无法从accounts页面跳转到hosting")
            return False
            
        except Exception as e:
            self.log(f"跳转到hosting时出错: {e}", "ERROR")
            return False
    
    def handle_cloudflare(self, page):
        """处理Cloudflare验证"""
        try:
            self.log("检查Cloudflare验证...")
            
            # 简单的等待策略
            time.sleep(5)
            
            # 检查页面内容
            content = page.content().lower()
            if "cloudflare" in content or "verifying" in content or "checking" in content:
                self.log("⚠️ 检测到Cloudflare验证，等待完成...")
                # 等待最多20秒
                for i in range(20):
                    time.sleep(1)
                    content = page.content().lower()
                    if "email" in content or "username" in content or "password" in content:
                        self.log("✅ Cloudflare验证完成")
                        return True
                
                self.log("❌ Cloudflare验证超时")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"处理Cloudflare时出错: {e}", "ERROR")
            return False
    
    def human_like_typing(self, element, text, delay_range=(50, 150)):
        """模拟人类输入"""
        for char in text:
            element.press(char)
            time.sleep(random.uniform(delay_range[0]/1000, delay_range[1]/1000))
    
    def perform_login(self, page):
        """执行登录操作"""
        try:
            self.log("执行登录操作...")
            
            # 查找登录表单元素
            email_selectors = ['input[name="email"]', 'input[type="email"]']
            password_selectors = ['input[name="password"]', 'input[type="password"]']
            submit_selectors = ['button[type="submit"]']
            
            # 等待表单加载
            time.sleep(2)
            
            # 查找邮箱输入框
            email_field = None
            for selector in email_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        email_field = page.locator(selector).first
                        break
                except:
                    continue
            
            if not email_field:
                self.log("❌ 未找到邮箱输入框")
                return False
            
            # 查找密码输入框
            password_field = None
            for selector in password_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        password_field = page.locator(selector).first
                        break
                except:
                    continue
            
            if not password_field:
                self.log("❌ 未找到密码输入框")
                return False
            
            # 查找提交按钮
            submit_button = None
            for selector in submit_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        submit_button = page.locator(selector).first
                        break
                except:
                    continue
            
            if not submit_button:
                self.log("❌ 未找到提交按钮")
                return False
            
            # 填写登录信息
            self.log("填写邮箱...")
            email_field.click()
            email_field.fill('')
            self.human_like_typing(email_field, self.email)
            
            self.log("填写密码...")
            password_field.click()
            password_field.fill('')
            self.human_like_typing(password_field, self.password)
            
            time.sleep(1)
            
            # 点击登录按钮
            self.log("点击登录按钮...")
            submit_button.click()
            time.sleep(5)
            
            # 检查登录结果
            return self.check_login_status(page)
                
        except Exception as e:
            self.log(f"登录过程中出错: {e}", "ERROR")
            return False
    
    def login_with_email(self, page):
        """完整的邮箱密码登录流程"""
        try:
            self.log("开始完整的登录流程...")
            
            # 第一步: 访问hosting auth页面
            self.log(f"1. 访问hosting auth页面: {self.auth_url}")
            page.goto(self.auth_url, wait_until="domcontentloaded")
            time.sleep(3)
            
            # 检查是否已经登录
            if self.check_login_status(page):
                return True
            
            # 第二步: 点击Login or Sign Up with Zampto按钮
            self.log("2. 点击Login or Sign Up with Zampto按钮")
            login_button_selectors = [
                'button:has-text("Login or Sign Up with Zampto")',
                'a:has-text("Login or Sign Up with Zampto")',
                '//button[contains(text(), "Login")]',
                '//a[contains(text(), "Login")]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    if selector.startswith('//'):
                        button = page.locator(f'xpath={selector}')
                    else:
                        button = page.locator(selector)
                    
                    if button.count() > 0 and button.first.is_visible():
                        login_button = button.first
                        break
                except:
                    continue
            
            if not login_button:
                self.log("❌ 未找到登录按钮")
                return False
            
            try:
                with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                    login_button.click()
                time.sleep(3)
            except:
                self.log("❌ 点击登录按钮失败或导航超时")
                return False
            
            # 第三步: 处理Cloudflare验证
            if not self.handle_cloudflare(page):
                return False
            
            # 第四步: 执行登录操作
            self.log("3. 执行登录操作")
            login_success = self.perform_login(page)
            
            if login_success:
                self.log("✅ 登录成功")
                return True
            
            # 第五步: 如果登录后还在accounts页面，尝试跳转到hosting
            if "accounts.zampto.net" in page.url:
                self.log("4. 尝试从accounts页面跳转到hosting")
                return self.navigate_to_hosting_from_accounts(page)
            
            return False
                
        except Exception as e:
            self.log(f"完整登录流程中出错: {e}", "ERROR")
            return False

    def renew_server(self, page, server_url):
        """续期服务器 - 直接通过URL参数续期并输出结果"""
        try:
            server_id = server_url.split('id=')[-1] if 'id=' in server_url else "unknown"
            self.log(f"开始处理服务器 {server_id}")
            
            # 构建续期URL
            if '?' in server_url:
                renew_url = f"{server_url}&renew=true"
            else:
                renew_url = f"{server_url}?renew=true"
            
            self.log(f"访问续期URL: {renew_url}")
            
            # 访问续期URL
            page.goto(renew_url, wait_until="networkidle")
            time.sleep(3)
            
            # 获取页面内容
            content = page.content()
            
            # 尝试解析JSON响应
            try:
                # 查找JSON部分
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    json_data = json.loads(json_str)
                    
                    if json_data.get("success", False):
                        renewal_time = json_data.get("renewal", "")
                        next_renewal = json_data.get("nextRenewal", "")
                        self.log(f"✅ 续期成功 - 当前续期: {renewal_time}, 下次续期: {next_renewal}")
                        return f"{server_id}: success - renewal: {renewal_time}, next: {next_renewal}"
                    else:
                        self.log("❌ 续期失败，API返回失败状态")
                        return f"{server_id}: api_failed - {json_str}"
            except json.JSONDecodeError:
                self.log("❌ 无法解析JSON响应")
            
            # 如果无法解析JSON，返回原始内容的前500字符
            content_preview = content[:500].replace('\n', ' ').replace('\r', ' ')
            self.log(f"页面内容预览: {content_preview}...")
            
            return f"{server_id}: {content_preview}..."
                
        except Exception as e:
            self.log(f"续期过程中出错: {e}", "ERROR")
            return f"{server_id}: error - {str(e)}"

    def run(self):
        """主运行函数"""
        self.log("开始 Zampto 自动续期任务")
        
        if not self.has_email_auth():
            return ["error: no_auth"]
        
        if not self.server_list:
            return ["error: no_servers"]
        
        results = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(user_agent=self.user_agent)
                
                # 隐藏自动化特征
                context.add_init_script("""
                    delete navigator.__proto__.webdriver;
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                """)
                
                page = context.new_page()
                page.set_default_timeout(60000)
                
                # 执行登录
                login_success = self.login_with_email(page)
                
                if login_success:
                    for server_url in self.server_list:
                        result = self.renew_server(page, server_url)
                        results.append(result)
                        time.sleep(2)
                else:
                    results = ["login_failed"] * len(self.server_list)
                
                browser.close()
                return results
                
        except Exception as e:
            self.log(f"运行时出错: {e}", "ERROR")
            return ["error: runtime"] * len(self.server_list)
    
    def write_readme_file(self, results):
        """写入README文件"""
        try:
            from datetime import datetime, timezone, timedelta
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
            
            readme_content = f"""# Zampto 自动续期脚本

**最后运行时间**: `{timestamp}` (北京时间)

## 运行结果

"""
            
            for result in results:
                readme_content += f"- {result}\n"
            
            with open('README.md', 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
        except Exception as e:
            self.log(f"写入README失败: {e}", "ERROR")


def main():
    """主函数"""
    login = ZamptoLogin()
    
    if not login.has_email_auth():
        print("❌ 错误：未设置认证信息！")
        sys.exit(1)
    
    if not login.server_list:
        print("❌ 错误：未设置服务器URL列表！")
        sys.exit(1)
    
    results = login.run()
    login.write_readme_file(results)
    
    print("运行结果汇总:")
    for result in results:
        print(f"  - {result}")
    
    if any("login_failed" in result or "error:" in result for result in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
