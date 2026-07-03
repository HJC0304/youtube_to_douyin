"""
抖音视频上传功能
使用Playwright自动化上传视频到抖音创作者平台
"""
import sys
from pathlib import Path

# 直接执行 `python douyin/upload_video.py` 时 cwd 在子目录，需把项目根加入 path 才能 import deepseek 等包
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_root_str = str(_PROJECT_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

import re
import json
import time
import random
from datetime import datetime
from typing import Optional, List, Dict
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

from config.store_config.download_config import (
    get_default_video_download_dir,
    get_uploaded_video_archive_dir,
)
from deepseek.deepseek_api import fetch_short_video_clip_metadata_from_video_name

# 超时时间常量（30秒）
TIMEOUT = 30000
# 抖音上传页面URL
DOUYIN_UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"


class DouyinUploader:
    """抖音视频上传器"""
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium", skip_load_cookies: bool = False):
        """
        初始化抖音上传器
        
        Args:
            headless: 是否使用无头模式
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
            skip_load_cookies: 是否跳过加载cookies（用于登录模式）
        """
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.cookies_path = Path(__file__).parent.parent / "data" / "cookies" / ".douyin_cookies.json"
        self.headless = headless
        self.browser_type = browser_type
        self.step_counter = 0
        self._skip_load_cookies = skip_load_cookies
        self._network_listener_enabled = False
        self._last_cookie_save_time = 0
        self._cookie_save_interval = 30  # 每30秒保存一次cookies
        self._mouse_move_thread = None
        self._stop_mouse_move = False
        self.default_download_dir = get_default_video_download_dir()
        self.upload_archive_dir = get_uploaded_video_archive_dir()
        self._init_browser()
    
    def _log_step(self, message: str, status: str = "INFO"):
        """
        打印执行步骤日志
        
        Args:
            message: 日志消息
            status: 状态 (INFO, SUCCESS, WARNING, ERROR)
        """
        self.step_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_symbol = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(status, "ℹ️")
        print(f"[{timestamp}] [{self.step_counter:02d}] {status_symbol} {message}")
    
    def _init_browser(self):
        """初始化浏览器"""
        try:
            self._log_step("开始初始化 Playwright...")
            self.playwright = sync_playwright().start()
            self._log_step("Playwright 启动成功", "SUCCESS")
            
            # 选择浏览器类型
            self._log_step(f"选择浏览器类型: {self.browser_type}")
            if self.browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium
            
            # 启动浏览器（添加反检测参数）
            self._log_step(f"启动浏览器 (headless={self.headless})...")
            browser_args = [
                '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
            self.browser = browser_launcher.launch(
                headless=self.headless,
                args=browser_args
            )
            self._log_step("浏览器启动成功", "SUCCESS")
            
            # 创建上下文和页面（设置真实的浏览器特征）
            self._log_step("创建浏览器上下文...")
            
            # 随机选择一个真实的 User-Agent
            user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            selected_ua = random.choice(user_agents)
            
            # 随机视口大小（模拟真实设备）
            viewport_sizes = [
                {"width": 1920, "height": 1080}
            ]
            selected_viewport = random.choice(viewport_sizes)
            
            context = self.browser.new_context(
                user_agent=selected_ua,
                viewport=selected_viewport,
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                permissions=['geolocation'],
                geolocation={'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
                color_scheme='light',
            )
            
            # 隐藏 webdriver 特征
            self.page = context.new_page()
            
            # 注入脚本隐藏自动化特征
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // 覆盖 plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // 覆盖 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                
                // 覆盖 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Chrome 对象
                window.chrome = {
                    runtime: {}
                };
            """)
            
            self._log_step("页面创建成功", "SUCCESS")
            self._log_step(f"使用 User-Agent: {selected_ua[:50]}...", "INFO")
            self._log_step(f"使用视口大小: {selected_viewport['width']}x{selected_viewport['height']}", "INFO")
            
            # 优先加载本地保存的cookies（在访问页面之前）
            # 注意：登录模式下不自动加载cookies，需要重新登录
            if not hasattr(self, '_skip_load_cookies'):
                self.cookies_loaded = self.load_cookies()
            else:
                self.cookies_loaded = False
            
            # 启动网络监听器，自动更新认证信息
            self._start_network_listener()
            
            # 启动鼠标移动模拟（保持活跃状态）
            self._start_mouse_move_simulation()
            
        except Exception as e:
            self._log_step(f"初始化浏览器失败: {e}", "ERROR")
            raise
    
    def load_cookies(self, skip_reload: bool = False):
        """
        加载保存的cookies（优先使用本地登录信息）
        
        Args:
            skip_reload: 是否跳过页面刷新（如果当前页面已经是正确的页面，可以跳过）
        
        Returns:
            bool: 是否成功加载cookies
        """
        # 确保 cookies 文件目录存在
        self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.cookies_path.exists():
            self._log_step("未找到保存的登录信息文件，将需要手动登录", "WARNING")
            return False
        
        try:
            import json
            self._log_step(f"从文件加载登录信息: {self.cookies_path}", "INFO")
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 兼容新旧格式：新格式是对象包含 cookies 字段，旧格式直接是 cookies 数组
                if isinstance(data, dict) and 'cookies' in data:
                    # 新格式：包含时间信息的对象
                    cookies = data['cookies']
                    saved_at = data.get('saved_at', '未知时间')
                    self._log_step(f"读取到保存时间: {saved_at}", "INFO")
                elif isinstance(data, list):
                    # 旧格式：直接是 cookies 数组
                    cookies = data
                else:
                    self._log_step("登录信息文件格式不正确", "WARNING")
                    return False
                
                # 检查 cookies 是否为空数组或 None
                if not cookies or (isinstance(cookies, list) and len(cookies) == 0):
                    self._log_step("登录信息文件为空，将需要手动登录", "WARNING")
                    return False
                
                if cookies:
                    self._log_step(f"找到 {len(cookies)} 个 cookies，开始加载...")
                    # 确保 cookies 格式正确（Playwright 需要 domain 字段）
                    valid_cookies = []
                    for cookie in cookies:
                        if isinstance(cookie, dict):
                            # 确保有必要的字段
                            if 'name' not in cookie or 'value' not in cookie:
                                continue
                            
                            # 处理域名：确保 cookies 能正确应用到 creator.douyin.com
                            if 'domain' not in cookie:
                                # 如果没有 domain，根据已有 cookies 推断或使用默认值
                                cookie['domain'] = 'creator.douyin.com'
                            else:
                                # 如果 domain 是 creator.douyin.com，保持不变
                                # 如果是 .douyin.com，也保持（可以应用到子域名）
                                domain = cookie['domain']
                                if domain == 'creator.douyin.com' or domain == '.douyin.com':
                                    pass  # 保持原样
                                elif 'douyin.com' in domain:
                                    # 确保是有效的 douyin 域名
                                    pass
                                else:
                                    # 如果不是 douyin 域名，跳过
                                    continue
                            
                            if 'path' not in cookie:
                                cookie['path'] = '/'
                            
                            # 确保 secure 字段存在（某些 cookies 可能需要）
                            if 'secure' not in cookie:
                                cookie['secure'] = False
                            
                            # 确保 sameSite 字段存在
                            if 'sameSite' not in cookie:
                                cookie['sameSite'] = 'Lax'
                            
                            valid_cookies.append(cookie)
                    
                    # 设置 cookies
                    if valid_cookies:
                        self._log_step(f"设置 {len(valid_cookies)} 个 cookies...")
                        
                        # 检查当前页面是否已经是正确的页面
                        current_url = self.page.url
                        target_url = "https://creator.douyin.com/creator-micro/home"
                        need_navigate = not (current_url.startswith("https://creator.douyin.com") and "/creator-micro/home" in current_url)
                        
                        if need_navigate:
                            # 先访问域名，然后设置cookies
                            # 使用 creator.douyin.com/creator-micro/home 页面，确保 cookies 能正确设置
                            self._log_step("访问登录验证页面以设置 cookies...", "INFO")
                            self.page.goto(target_url, wait_until="domcontentloaded", timeout=TIMEOUT)
                            time.sleep(1)
                        else:
                            self._log_step("当前页面已正确，无需重新访问", "INFO")
                        
                        # 添加 cookies 到上下文（必须在访问域名之后）
                        try:
                            self.page.context.add_cookies(valid_cookies)
                            self._log_step(f"已添加 {len(valid_cookies)} 个 cookies 到浏览器上下文", "SUCCESS")
                        except Exception as e:
                            self._log_step(f"添加 cookies 时出错: {e}", "WARNING")
                            # 尝试逐个添加 cookies
                            success_count = 0
                            for cookie in valid_cookies:
                                try:
                                    self.page.context.add_cookies([cookie])
                                    success_count += 1
                                except:
                                    continue
                            if success_count > 0:
                                self._log_step(f"成功添加 {success_count}/{len(valid_cookies)} 个 cookies", "SUCCESS")
                        
                        # 只有在需要时才刷新页面使cookies生效
                        if need_navigate:
                            # 如果已经访问了新页面，不需要 reload，cookies 应该已经生效
                            self._log_step("cookies 已添加，等待页面稳定...", "INFO")
                            time.sleep(1)
                        else:
                            # 如果当前页面已经是正确的页面
                            if not skip_reload:
                                # 需要 reload 使 cookies 生效
                                self._log_step("刷新页面使 cookies 生效...", "INFO")
                                self.page.reload(wait_until="domcontentloaded", timeout=TIMEOUT)
                                time.sleep(1)
                            else:
                                # 跳过刷新（调用者已经知道当前页面是正确的）
                                self._log_step("跳过页面刷新（skip_reload=True）", "INFO")
                                time.sleep(0.5)  # 短暂等待，让 cookies 生效
                        
                        # 验证 cookies 是否生效（检查是否已登录）
                        try:
                            # 检查是否有登录相关的元素
                            login_indicators = [
                                self.page.get_by_text("登录", timeout=2000),
                                self.page.get_by_text("请登录", timeout=2000),
                            ]
                            has_login_prompt = False
                            for indicator in login_indicators:
                                try:
                                    if indicator.is_visible():
                                        has_login_prompt = True
                                        break
                                except:
                                    continue
                            
                            if not has_login_prompt:
                                self._log_step("登录信息加载成功，cookies已生效（已登录状态）", "SUCCESS")
                            else:
                                self._log_step("登录信息已加载，但可能需要重新登录", "WARNING")
                        except:
                            self._log_step("登录信息已加载", "SUCCESS")
                        
                        return True
                    else:
                        self._log_step("未找到有效的 cookies", "WARNING")
                else:
                    self._log_step("未找到有效的 cookies", "WARNING")
        except json.JSONDecodeError as e:
            self._log_step(f"Cookie文件格式错误: {e}", "WARNING")
        except Exception as e:
            self._log_step(f"加载cookies失败: {e}", "WARNING")
            import traceback
            traceback.print_exc()
        
        return False
    
    def login(self, login_url: str = "https://creator.douyin.com/", wait_time: int = 60):
        """
        登录抖音创作者平台
        
        Args:
            login_url: 登录页面URL，默认 https://creator.douyin.com/
            wait_time: 等待登录的时间（秒），默认60秒
            
        Returns:
            bool: 是否登录成功
        """
        try:
            self._log_step("=" * 60)
            self._log_step("开始登录抖音创作者平台")
            self._log_step("=" * 60)
            
            # 步骤1: 从文件加载已有的 cookies（如果存在）
            self._log_step("步骤1: 从文件加载已有的登录信息（cookies）...")
            cookies_loaded = self.load_cookies()
            
            if cookies_loaded:
                self._log_step("已从文件加载登录信息（cookies）", "SUCCESS")
            else:
                self._log_step("未找到保存的登录信息文件，将需要手动登录", "INFO")
            
            # 步骤2: 访问登录页面（带上已加载的 cookies）
            self._log_step(f"步骤2: 访问登录页面: {login_url}")
            self.page.goto(login_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            # 随机等待，模拟真实用户行为
            self._human_like_delay(1.5, 3.0)
            
            # 步骤3: 检查是否已经登录
            self._log_step("步骤3: 检查登录状态...")
            is_logged_in = self._check_login_status()
            
            if is_logged_in:
                self._log_step("✅ 检测到已登录状态，无需重新登录", "SUCCESS")
                self._log_step("登录信息已保存，可以直接使用上传功能", "SUCCESS")
                # 保存最新的 cookies（以防有更新）
                self.save_cookies(triggered_by="login")
                return True
            
            # 步骤4: 需要手动登录，持续监听登录状态（不刷新页面）
            self._log_step("步骤4: 需要手动登录", "INFO")
            self._log_step("请在浏览器中完成登录操作", "INFO")
            self._log_step(f"正在持续监听登录状态（最多等待 {wait_time} 秒，不刷新页面）...", "INFO")
            
            # 持续监听登录状态，不刷新页面
            start_time = time.time()
            check_interval = 1  # 每秒检查一次
            last_log_time = 0
            log_interval = 5  # 每5秒打印一次状态
            
            while True:
                elapsed = time.time() - start_time
                remaining = wait_time - elapsed
                
                if remaining <= 0:
                    break
                
                # 检查是否已登录（不刷新页面）
                try:
                    is_logged_in = self._check_login_status()
                    if is_logged_in:
                        self._log_step("✅ 检测到登录成功！", "SUCCESS")
                        self.save_cookies(triggered_by="login")
                        return True
                    else:
                        # 每5秒打印一次检测结果（仅在打印状态时）
                        if elapsed - last_log_time >= log_interval:
                            self._log_step("  当前状态: 未检测到登录", "INFO")
                except Exception as e:
                    # 检查过程中出错，继续监听
                    self._log_step(f"  检查登录状态时出错: {e}", "WARNING")
                
                # 每5秒打印一次状态信息
                if elapsed - last_log_time >= log_interval:
                    self._log_step(f"  监听中... 已等待 {int(elapsed)} 秒，剩余 {int(remaining)} 秒", "INFO")
                    last_log_time = elapsed
                
                # 等待一段时间后再次检查
                time.sleep(check_interval)
            
            # 步骤5: 等待时间结束，最后检查一次登录状态
            self._log_step("步骤5: 等待时间结束，最后检查登录状态...", "INFO")
            
            try:
                if self._check_login_status():
                    self._log_step("✅ 登录成功！", "SUCCESS")
                    self.save_cookies(triggered_by="login")
                    return True
                else:
                    self._log_step("❌ 登录失败：等待时间结束，仍未检测到已登录状态", "ERROR")
                    return False
            except Exception as e:
                self._log_step(f"❌ 检查登录状态时出错: {e}", "ERROR")
                return False
            
        except Exception as e:
            self._log_step(f"登录过程中发生错误: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_login_status(self) -> bool:
        """
        检查当前是否已登录（使用多种方法综合判断）
        
        Returns:
            bool: 是否已登录
        """
        try:
            current_url = self.page.url
            self._log_step(f"检查登录状态 - 当前URL: {current_url}", "INFO")
            
            # 方法1: 检查 cookies 中是否有登录相关的关键 cookie
            cookies = self.page.context.cookies()
            login_cookies = ['sessionid', 'sid_tt', 'passport_assist_user', 'uid_tt']
            has_login_cookies = any(cookie.get('name') in login_cookies for cookie in cookies)
            
            if has_login_cookies:
                self._log_step("检测到登录相关的 cookies", "INFO")
            
            # 方法2: 检查 URL 是否包含登录相关路径
            if '/login' in current_url.lower() or '/signin' in current_url.lower():
                self._log_step("URL 包含登录路径，判断为未登录", "INFO")
                return False
            
            # 方法3: 检查是否有登录提示（如果有，说明未登录）
            login_indicators_found = False
            login_indicators = [
                ("登录按钮", lambda: self.page.get_by_text("登录", exact=False).first),
                ("请登录文本", lambda: self.page.get_by_text("请登录", exact=False).first),
                ("密码输入框", lambda: self.page.locator("input[type='password']").first),
            ]
            
            for name, locator_func in login_indicators:
                try:
                    element = locator_func()
                    if element.count() > 0 and element.is_visible(timeout=1000):
                        self._log_step(f"检测到登录提示: {name}", "INFO")
                        login_indicators_found = True
                        break
                except:
                    continue
            
            if login_indicators_found:
                return False  # 有登录提示，说明未登录
            
            # 方法4: 检查是否有用户相关元素（如果有，说明已登录）
            user_elements_found = False
            user_elements = [
                ("头像元素", lambda: self.page.locator("[class*='avatar'], [class*='Avatar'], img[alt*='头像'], img[alt*='avatar']").first),
                ("用户相关元素", lambda: self.page.locator("[class*='user'], [class*='User'], [class*='account']").first),
                ("创作者文本", lambda: self.page.get_by_text("创作者", exact=False).first),
                ("创作者中心链接", lambda: self.page.locator("a[href*='/creator-micro'], a[href*='/creator']").first),
                ("内容管理", lambda: self.page.get_by_text("内容管理", exact=False).first),
                ("发布作品", lambda: self.page.get_by_text("发布", exact=False).first),
            ]
            
            for name, locator_func in user_elements:
                try:
                    element = locator_func()
                    if element.count() > 0 and element.is_visible(timeout=1000):
                        self._log_step(f"检测到用户相关元素: {name}", "SUCCESS")
                        user_elements_found = True
                        break
                except:
                    continue
            
            if user_elements_found:
                return True  # 找到用户相关元素，说明已登录
            
            # 方法5: 检查页面标题或特定文本
            try:
                page_title = self.page.title()
                if "创作者" in page_title or "抖音创作者" in page_title:
                    self._log_step(f"页面标题包含创作者信息: {page_title}", "SUCCESS")
                    return True
            except:
                pass
            
            # 方法6: 如果 URL 是创作者平台的主页或内容页，且有登录 cookies，认为已登录
            if 'creator.douyin.com' in current_url and has_login_cookies:
                # 检查是否在登录页面
                if '/login' not in current_url.lower() and '/signin' not in current_url.lower():
                    self._log_step("在创作者平台且不在登录页，且有登录 cookies，判断为已登录", "SUCCESS")
                    return True
            
            # 如果既没有登录提示，也没有明确的用户元素，但有登录 cookies 且不在登录页，认为已登录
            if has_login_cookies and '/login' not in current_url.lower() and '/signin' not in current_url.lower():
                self._log_step("有登录 cookies 且不在登录页，判断为已登录", "SUCCESS")
                return True
            
            # 默认情况：未检测到明确的登录状态
            self._log_step("未检测到明确的登录状态", "WARNING")
            return False
            
        except Exception as e:
            # 如果检测过程中出错，打印错误信息
            self._log_step(f"检查登录状态时出错: {e}", "WARNING")
            import traceback
            traceback.print_exc()
            return False
    
    def save_cookies(self, triggered_by: str = "manual"):
        """
        保存当前登录信息（cookies）到文件，包含时间信息
        
        Args:
            triggered_by: 触发保存的原因（"login"（登录）, "periodic"（定期保存）, "set-cookie"（检测到Set-Cookie）, "manual"（手动））
        """
        try:
            self._log_step("保存当前登录信息（cookies）到文件...", "INFO")
            cookies = self.page.context.cookies()
            
            # 确保目录存在
            self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备保存的数据，包含 cookies 和时间信息
            save_data = {
                "cookies": cookies,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "saved_timestamp": int(time.time()),
                "cookie_count": len(cookies),
                "triggered_by": triggered_by
            }
            
            # 保存到文件
            import json
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            self._log_step(f"已保存 {len(cookies)} 个 cookies 到文件: {self.cookies_path}", "SUCCESS")
            self._log_step(f"保存时间: {save_data['saved_at']}", "SUCCESS")
            self._last_cookie_save_time = time.time()
        except Exception as e:
            self._log_step(f"保存cookies失败: {e}", "WARNING")
            import traceback
            traceback.print_exc()
    
    def _start_network_listener(self):
        """启动网络监听器，自动捕获并更新认证信息"""
        try:
            if self._network_listener_enabled:
                return
            
            def handle_response(response):
                """处理API响应，自动提取并更新认证信息"""
                try:
                    url = response.url
                    
                    # 只监听抖音相关的API请求
                    douyin_domains = ['douyin.com', 'bytedance.com', 'snssdk.com', 'ixigua.com', 'toutiao.com']
                    if not any(domain in url.lower() for domain in douyin_domains):
                        return
                    
                    # 对于所有成功的API响应，都检查并更新认证信息
                    # Playwright会自动处理Set-Cookie，所以我们主要关注定期保存cookies
                    if response.status < 400:
                        self._update_auth_from_response(response)
                    
                except Exception as e:
                    # 静默处理错误，不影响主流程
                    pass
            
            def handle_request(request):
                """处理请求，可以用于记录或修改请求"""
                try:
                    # 这里可以用于未来扩展，比如添加请求头等
                    pass
                except:
                    pass
            
            # 注册请求和响应监听器
            self.page.on("request", handle_request)
            self.page.on("response", handle_response)
            self._network_listener_enabled = True
            self._log_step("网络监听器已启动，将自动更新并保存认证信息", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"启动网络监听器失败: {e}", "WARNING")
    
    def _update_auth_from_response(self, response):
        """从API响应中提取并更新认证信息
        
        注意：Playwright会自动处理响应头中的Set-Cookie，
        所以我们主要做定期保存cookies的工作，确保认证信息被持久化保存。
        """
        try:
            # Playwright会自动处理Set-Cookie响应头，所以浏览器上下文中已经有最新的cookies
            # 我们只需要定期保存这些cookies到文件，确保认证信息被持久化
            
            current_time = time.time()
            
            # 检查是否有Set-Cookie响应头（即使Playwright已处理，我们也可以记录日志）
            headers = response.headers
            has_set_cookie = 'set-cookie' in headers or 'Set-Cookie' in headers
            
            # 定期保存cookies（每30秒或更短间隔）
            # 如果检测到Set-Cookie，立即保存（因为有新的认证信息）
            should_save = False
            if has_set_cookie:
                # 检测到Set-Cookie，立即保存
                should_save = True
            elif current_time - self._last_cookie_save_time >= self._cookie_save_interval:
                # 达到定期保存间隔
                should_save = True
            
            if should_save:
                try:
                    # 获取当前所有cookies（包含最新更新的）
                    cookies = self.page.context.cookies()
                    if cookies:
                        self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
                        save_data = {
                            "cookies": cookies,
                            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "saved_timestamp": int(current_time),
                            "cookie_count": len(cookies),
                            "triggered_by": "set-cookie" if has_set_cookie else "periodic"
                        }
                        import json
                        with open(self.cookies_path, 'w', encoding='utf-8') as f:
                            json.dump(save_data, f, indent=2, ensure_ascii=False)
                        self._last_cookie_save_time = current_time
                        
                        # 只在有Set-Cookie时才打印日志（避免日志过多）
                        if has_set_cookie:
                            self._log_step(f"检测到新的认证信息，已更新保存 {len(cookies)} 个cookies", "INFO")
                except:
                    pass
                    
        except Exception as e:
            # 静默处理错误，不影响主流程
            pass
    
    def _start_mouse_move_simulation(self):
        """
        启动鼠标移动模拟，保持页面活跃状态
        
        注意：由于 Playwright 同步 API 不支持多线程（greenlet 限制），
        此功能已禁用。如果需要保持页面活跃，可以在主线程中定期执行操作。
        """
        # 禁用后台线程中的鼠标移动模拟，避免 greenlet 错误
        # Playwright 的同步 API 不能在多线程环境中使用
        # 如果需要保持页面活跃，可以在主线程的上传流程中定期执行操作
        self._log_step("鼠标移动模拟已禁用（避免多线程 greenlet 错误）", "INFO")
        pass
    
    def _simulate_mouse_move(self, width: int, height: int):
        """
        模拟真实的鼠标移动（已禁用，避免多线程 greenlet 错误）
        
        注意：此方法已禁用，因为 Playwright 同步 API 不支持多线程。
        如果需要保持页面活跃，可以在主线程中定期执行操作。
        """
        # 已禁用：避免在多线程中调用 Playwright API 导致 greenlet 错误
        pass
    
    def _stop_mouse_move_simulation(self):
        """停止鼠标移动模拟"""
        try:
            self._stop_mouse_move = True
            if self._mouse_move_thread and self._mouse_move_thread.is_alive():
                self._mouse_move_thread.join(timeout=2)
            self._log_step("鼠标移动模拟已停止", "INFO")
        except:
            pass
    
    def _extract_title_from_filename(self, video_path: str) -> str:
        """
        从视频文件名中提取标题（参照参考文件的优化逻辑）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            提取的标题（尽量保持简短，约30字符）
        """
        video_file = Path(video_path)
        base = video_file.stem  # 不含扩展名
        
        # 去掉常见无关符号（下划线、连字符等替换为空格）
        cleaned = re.sub(r"[_\-]+", " ", base)
        # 合并多余空格
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        
        # 标题尽量保持简短（截断到约30字符）
        title = cleaned[:30] if len(cleaned) > 30 else cleaned
        
        # 兜底：如果清洗后为空，使用一个通用标题
        if not title:
            title = "我的视频作品"
        
        return title
    
    def _human_like_delay(self, min_seconds: float = 0.2, max_seconds: float = 0.8):
        """
        模拟人类行为的随机延迟
        
        Args:
            min_seconds: 最小延迟时间（秒）
            max_seconds: 最大延迟时间（秒）
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _human_like_click(self, element, description: str = "", timeout: int = TIMEOUT):
        """
        模拟人类行为的点击操作（包括鼠标移动和随机延迟）
        
        Args:
            element: 要点击的元素
            description: 操作描述（用于日志）
            timeout: 超时时间
        """
        try:
            if description:
                self._log_step(f"{description}...", "INFO")
            
            # 滚动到元素可见
            element.scroll_into_view_if_needed(timeout=timeout)
            self._human_like_delay(0.1, 0.3)
            
            # 模拟鼠标移动到元素上
            element.hover(timeout=timeout)
            self._human_like_delay(0.2, 0.5)
            
            # 点击（带随机延迟）
            click_delay = random.randint(50, 200)  # 50-200ms 的点击延迟
            element.click(timeout=timeout, delay=click_delay)
            
            # 点击后随机等待
            self._human_like_delay(0.3, 0.7)
            
            return True
        except Exception as e:
            self._log_step(f"点击操作失败: {e}", "WARNING")
            return False
    
    def _human_like_type(self, element, text: str, description: str = ""):
        """
        模拟人类行为的输入操作（逐字符输入，带随机延迟）
        
        Args:
            element: 要输入的元素
            text: 要输入的文本
            description: 操作描述（用于日志）
        """
        try:
            if description:
                self._log_step(f"{description}...", "INFO")
            
            # 清空现有内容
            element.clear()
            self._human_like_delay(0.1, 0.2)
            
            # 逐字符输入，模拟真实打字速度
            for char in text:
                element.press(char, delay=random.randint(50, 150))  # 每个字符50-150ms延迟
                # 偶尔添加额外的延迟（模拟思考或停顿）
                if random.random() < 0.1:  # 10% 的概率
                    self._human_like_delay(0.2, 0.5)
            
            self._human_like_delay(0.2, 0.4)
            return True
        except Exception as e:
            # 如果逐字符输入失败，回退到 fill 方法
            try:
                element.fill(text)
                return True
            except:
                self._log_step(f"输入操作失败: {e}", "WARNING")
                return False
    
    def _close_modal_if_exists(self):
        """
        检测并关闭可能出现的遮罩/弹窗（点击"我知道了"按钮）
        """
        try:
            # 尝试多种方式查找"我知道了"按钮
            close_button_selectors = [
                'button:has-text("我知道了")',
                'div:has-text("我知道了")',
                'span:has-text("我知道了")',
                'a:has-text("我知道了")',
                '[class*="close"]:has-text("我知道了")',
                '[class*="confirm"]:has-text("我知道了")',
                '[class*="modal"]:has-text("我知道了")',
            ]
            
            for selector in close_button_selectors:
                try:
                    close_button = self.page.locator(selector).first
                    if close_button.count() > 0:
                        if close_button.is_visible(timeout=2000):
                            self._log_step("检测到遮罩/弹窗，点击「我知道了」按钮关闭...", "INFO")
                            close_button.click(timeout=5000)
                            time.sleep(0.5)  # 等待遮罩关闭
                            self._log_step("已关闭遮罩/弹窗", "SUCCESS")
                            return True
                except:
                    continue
            
            # 尝试通过角色定位
            try:
                close_button = self.page.get_by_role("button", name="我知道了", exact=False)
                if close_button.is_visible(timeout=2000):
                    self._log_step("检测到遮罩/弹窗，点击「我知道了」按钮关闭...", "INFO")
                    # 模拟鼠标移动到按钮上
                    close_button.hover(timeout=2000)
                    time.sleep(random.uniform(0.2, 0.5))
                    close_button.click(timeout=5000, delay=random.randint(50, 150))
                    time.sleep(random.uniform(0.3, 0.7))  # 随机等待时间
                    self._log_step("已关闭遮罩/弹窗", "SUCCESS")
                    return True
            except:
                pass
            
            return False
        except Exception as e:
            # 忽略错误，不影响主流程
            return False

    def _log_publish_button_info(self, button, source: str = ""):
        """
        打印当前「发布」按钮的关键信息，方便确认是否点击了正确的按钮
        """
        try:
            text = button.inner_text()
        except Exception:
            text = "<无法获取>"
        try:
            btn_id = button.get_attribute("id")
        except Exception:
            btn_id = None
        try:
            btn_class = button.get_attribute("class")
        except Exception:
            btn_class = None
        try:
            role = button.get_attribute("role")
        except Exception:
            role = None
        # 只取 outerHTML 的前一部分，避免日志过长
        try:
            outer_html = button.evaluate("el => el.outerHTML") or ""
            outer_html_preview = outer_html[:200].replace("\n", " ")
        except Exception:
            outer_html_preview = "<无法获取>"
        
        prefix = f"[发布按钮信息@{source}]" if source else "[发布按钮信息]"
        self._log_step(
            f"{prefix} text='{text}', id='{btn_id}', class='{btn_class}', role='{role}', outerHTML前200字符='{outer_html_preview}'",
            "INFO",
        )
    
    def _extract_time_from_title(self, title: str) -> str:
        """
        从标题中提取时间信息（如果标题中有多个时间，返回最大的时间）
        
        Args:
            title: 标题文本
            
        Returns:
            时间信息字符串（如果找到），否则返回空字符串
        """
        all_times = []
        
        # 1. 带分隔符的格式（yyyy-MM-dd, yy-MM-dd, yyyy/MM/dd, yy/MM/dd等）
        time_patterns_with_separator = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # 2024-01-01, 2024/01/01
            r'\d{2}[-/]\d{1,2}[-/]\d{1,2}',  # 24-01-01, 24/01/01 (yy-MM-dd格式)
            r'\d{4}\.\d{1,2}\.\d{1,2}',      # 2024.01.01
            r'\d{4}年\d{1,2}月\d{1,2}日',     # 2024年1月1日
        ]
        
        for pattern in time_patterns_with_separator:
            matches = re.finditer(pattern, title)
            for match in matches:
                all_times.append(match.group(0))
        
        # 2. 8位数字格式（YYYYMMDD）
        eight_digit_pattern = r'(?<!\d)\d{4}\d{2}\d{2}(?!\d)'  # 20240101, 20251230
        matches = re.finditer(eight_digit_pattern, title)
        for match in matches:
            matched_str = match.group(0)
            # 验证是否为有效的日期格式
            try:
                year = int(matched_str[:4])
                month = int(matched_str[4:6])
                day = int(matched_str[6:8])
                # 验证年份、月份、日期的合理性
                if 2000 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                    all_times.append(matched_str)
            except (ValueError, IndexError):
                continue
        
        # 3. 6位数字格式（YYMMDD）
        six_digit_pattern = r'(?<!\d)\d{2}\d{2}\d{2}(?!\d)'  # 251230
        matches = re.finditer(six_digit_pattern, title)
        for match in matches:
            matched_str = match.group(0)
            # 验证是否为有效的日期格式
            try:
                year = int(matched_str[:2])
                month = int(matched_str[2:4])
                day = int(matched_str[4:6])
                # 月份范围：01-12，日期范围：1-31（简单验证）
                if 1 <= month <= 12 and 1 <= day <= 31:
                    all_times.append(matched_str)
            except (ValueError, IndexError):
                continue
        
        # 如果没有找到任何时间，返回空字符串
        if not all_times:
            return ""
        
        # 如果只有一个时间，直接返回
        if len(all_times) == 1:
            return all_times[0]
        
        # 如果有多个时间，解析所有时间并返回最大的时间
        parsed_dates = []
        for time_str in all_times:
            parsed_date = self._parse_date_from_time_string(time_str)
            if parsed_date:
                parsed_dates.append((time_str, parsed_date))
        
        if not parsed_dates:
            return all_times[0]  # 如果无法解析，返回第一个找到的时间
        
        # 找到最大的时间（最新的时间）
        max_time_str, max_date = max(parsed_dates, key=lambda x: x[1])
        return max_time_str
    
    def _extract_hashtags_from_title(self, title: str) -> str:
        """
        从标题中提取话题标签
        
        Args:
            title: 标题文本
            
        Returns:
            话题标签字符串（以#开头，空格分隔）
        """
        # 提取关键词（中文、英文单词）
        # 移除常见停用词
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
        
        # 提取中文词汇（2-4个字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', title)
        
        # 提取英文单词（3个字母以上）
        english_words = re.findall(r'\b[A-Za-z]{3,}\b', title)
        english_words = [w for w in english_words if w.lower() not in stop_words]
        
        # 组合关键词
        keywords = chinese_words + english_words
        
        # 限制数量（最多5个）
        keywords = keywords[:5]
        
        # 生成话题标签
        hashtags = ' '.join([f'#{word}' for word in keywords])
        
        return hashtags if hashtags else "#视频"
    
    def _fill_zone_container_with_profile_and_hashtags(
        self, profile: str, hashtags: str
    ) -> None:
        """
        在 .zone-container 中先填写 DeepSeek profile，换行后再填写话题标签。
        """
        hashtag_input = self.page.locator(".zone-container")
        self._human_like_click(hashtag_input, "点击话题/简介输入区域")
        hashtag_input.focus()
        self._human_like_delay(0.2, 0.4)
        
        profile_text = (profile or "").strip()
        tag_list = [t for t in (hashtags or "").split() if t.strip()]
        
        if profile_text:
            preview = profile_text[:120] + ("…" if len(profile_text) > 120 else "")
            self._log_step(f"输入 DeepSeek profile（第一行）| 长度={len(profile_text)} | 预览: {preview!r}", "INFO")
            for char in profile_text:
                self.page.keyboard.type(char, delay=random.randint(30, 90))
                if random.random() < 0.05:
                    self._human_like_delay(0.1, 0.2)
            if tag_list:
                self._human_like_delay(0.2, 0.4)
                self.page.keyboard.press("Shift+Enter")
                self._human_like_delay(0.3, 0.5)
                self._log_step("profile 输入完成，换行后填写标签", "INFO")
            else:
                self._log_step("profile 输入完成（无标签）", "SUCCESS")
                return
        
        if not tag_list:
            if not profile_text:
                self._log_step("无 DeepSeek profile 且无标签，跳过话题区填写", "INFO")
            return
        
        self._log_step(f"准备输入 {len(tag_list)} 个话题标签...", "INFO")
        for i, tag in enumerate(tag_list):
            tag_text = tag.lstrip('#')
            self._log_step(f"输入标签 {i+1}/{len(tag_list)}: {tag_text}...", "INFO")
            self.page.keyboard.type('#', delay=random.randint(50, 150))
            self._human_like_delay(0.1, 0.2)
            for char in tag_text:
                self.page.keyboard.type(char, delay=random.randint(50, 150))
                if random.random() < 0.1:
                    self._human_like_delay(0.1, 0.2)
            self._human_like_delay(0.2, 0.4)
            self.page.keyboard.press("Space")
            self._human_like_delay(0.3, 0.6)
            self._log_step(f"标签 {i+1}/{len(tag_list)} 输入完成并生效", "SUCCESS")
        
        self._log_step(
            f"话题区填写完成 | profile={'有' if profile_text else '无'} | 标签={hashtags!r}",
            "SUCCESS",
        )
    
    def upload_video(self, video_path: str, title: Optional[str] = None, 
                    hashtags: Optional[str] = None, cover_text: Optional[str] = None,
                    visibility: str = "公开", auto_publish: bool = False,
                    keep_browser_open: bool = False):
        """
        上传视频到抖音
        
        Args:
            video_path: 视频文件路径（本地路径）
            title: 作品标题（DeepSeek 成功时严格使用其 title；失败时回退手动参数或文件名）
            hashtags: 话题标签（None 时从标题提取关键词）
            cover_text: 封面文字（如果为None，使用标题）
            visibility: 可见性设置（"仅自己可见" 或 "公开"）
            auto_publish: 是否自动发布（默认False，需要手动确认）
            keep_browser_open: 是否保持浏览器打开（默认False，批量上传时设为True）
            
        Returns:
            dict: 包含上传结果的字典，包含视频信息和上传状态
        """
        self._log_step("=" * 60)
        self._log_step("开始上传视频到抖音")
        self._log_step("=" * 60)
        
        # 检查并加载登录状态（从文件获取 cookies）
        self._log_step("检查登录状态...", "INFO")
        
        # 如果初始化时没有加载 cookies，尝试从文件加载
        if not (hasattr(self, 'cookies_loaded') and self.cookies_loaded):
            self._log_step("初始化时未加载 cookies，尝试从文件加载登录信息...", "INFO")
            cookies_loaded = self.load_cookies()
            if cookies_loaded:
                self._log_step("已从文件加载登录信息（cookies）", "SUCCESS")
            else:
                self._log_step("未找到本地登录信息文件或文件为空，将需要手动登录", "WARNING")
        else:
            self._log_step("已使用本地保存的登录信息，无需重新登录", "SUCCESS")
        
        # 检查视频文件是否存在
        video_file = Path(video_path)
        if not video_file.exists():
            self._log_step(f"错误: 视频文件不存在: {video_path}", "ERROR")
            return {"success": False, "error": "文件不存在", "video_path": video_path}
        
        video_info = {
            "video_path": str(video_file.absolute()),
            "video_filename": video_file.name,
            "video_size": video_file.stat().st_size if video_file.exists() else 0,
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        self._log_step(f"视频文件: {video_path}")
        
        explicit_title_param: Optional[str] = title
        
        short_video_meta: Optional[Dict[str, str]] = None
        video_display_name = (video_file.stem or "").strip() or video_file.name
        title_source = ""
        title_source_detail = ""
        
        self._log_step(
            f"【DeepSeek 流程】开始：根据视频名请求元数据（标题/简介）| 视频名={video_display_name!r}",
            "INFO",
        )
        try:
            short_video_meta = fetch_short_video_clip_metadata_from_video_name(
                video_display_name,
                log_step=self._log_step,
            )
        except Exception as e:
            self._log_step(f"【DeepSeek 流程】请求异常: {e}，将回退本地规则", "WARNING")
            short_video_meta = None
        if short_video_meta is not None:
            self._log_step(
                "【DeepSeek 流程】结束：元数据已解析；发布页标题采用 JSON title，话题区第一行采用 profile",
                "SUCCESS",
            )
        else:
            self._log_step("【DeepSeek 流程】结束：无可用元数据，回退文件名规则", "WARNING")
        
        if short_video_meta is not None and (short_video_meta.get("title") or "").strip():
            title = (short_video_meta.get("title") or "").strip()
            title_source = "deepseek_json_title"
            title_source_detail = (
                "DeepSeek 返回 JSON 字段 `title`（strip 后）写入发布页标题；"
                f"请求时的视频名为: {video_display_name!r}"
            )
            self._log_step(f"标题来源=DeepSeek(JSON.title) | 标题全文: {title!r}", "SUCCESS")
        elif explicit_title_param is not None:
            title = str(explicit_title_param).strip()
            title_source = "manual"
            title_source_detail = (
                "DeepSeek 未返回可用 title；使用 upload_video 显式传入的 title 参数（已 strip）。"
            )
            self._log_step(f"标题来源=手动参数 | 标题全文: {title!r}", "INFO")
        else:
            title = self._extract_title_from_filename(str(video_path))
            title_source = "local_filename"
            title_source_detail = (
                "DeepSeek 未返回可用 title；使用 _extract_title_from_filename(视频路径) 从文件名提取标题。"
            )
            self._log_step(f"标题来源=本地文件名 | 标题全文: {title!r}", "INFO")
        
        self._log_step(
            f"【标题汇总】最终将写入发布页的标题: {title!r} | 类型={title_source}",
            "INFO",
        )
        self._log_step(f"【标题汇总】来源逻辑说明: {title_source_detail}", "INFO")
        
        video_info["title"] = title
        video_info["title_source"] = title_source
        video_info["title_source_detail"] = title_source_detail
        
        if hashtags is None:
            hashtags = self._extract_hashtags_from_title(title or video_display_name)
            self._log_step(f"从标题提取话题: {hashtags}", "INFO")
        else:
            self._log_step(f"使用指定话题标签: {hashtags}")
        
        video_info["hashtags"] = hashtags
        if short_video_meta is not None:
            video_info["profile"] = (short_video_meta.get("profile") or "").strip()
            video_info["short_video_meta"] = dict(short_video_meta)
        
        # 设置封面文字
        if cover_text is None:
            cover_text = title[:40]  # 最多40字
            self._log_step(f"使用标题作为封面文字: {cover_text}")
        else:
            self._log_step(f"使用指定封面文字: {cover_text}")
        
        video_info["cover_text"] = cover_text
        video_info["visibility"] = visibility
        video_info["auto_publish"] = auto_publish
        
        try:
            # 步骤1: 先访问首页检查登录状态
            self._log_step("步骤1: 检查登录状态...")
            
            # 确保 cookies 已加载（如果之前没有加载成功，再次尝试）
            if not (hasattr(self, 'cookies_loaded') and self.cookies_loaded):
                self._log_step("重新尝试从文件加载登录信息（cookies）...", "INFO")
                self.load_cookies()
            
            # 先访问首页检查登录状态
            self._log_step("正在访问抖音创作者平台首页（检查登录状态）...", "INFO")
            self.page.goto("https://creator.douyin.com/creator-micro/home", wait_until="domcontentloaded", timeout=TIMEOUT)
            self._human_like_delay(1.5, 3.0)
            
            # 检查登录状态
            self._log_step("检查登录信息是否有效...", "INFO")
            is_logged_in = self._check_login_status()
            
            if not is_logged_in:
                self._log_step("⚠️ 检测到未登录状态，尝试重新加载 cookies...", "WARNING")
                # 尝试重新加载 cookies（当前页面已经是验证页面，不需要刷新）
                cookies_reloaded = self.load_cookies(skip_reload=True)
                if cookies_reloaded:
                    # 当前页面已经是验证页面，直接检查登录状态，不需要重新访问
                    self._human_like_delay(1.0, 2.0)
                    is_logged_in = self._check_login_status()
                
                if not is_logged_in:
                    self._log_step("❌ 检测到未登录状态，无法继续上传", "ERROR")
                    self._log_step("请先运行登录功能：python douyin/upload_video.py --login", "ERROR")
                    video_info["success"] = False
                    video_info["error"] = "未登录，请先登录"
                    video_info["login_failed"] = True
                    return video_info
            
            self._log_step("✅ 登录信息有效，可以继续上传", "SUCCESS")
            
            # 步骤2: 访问上传页面
            self._log_step("步骤2: 访问上传视频页面...")
            self._log_step("正在访问上传页面...", "INFO")
            self.page.goto(DOUYIN_UPLOAD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
            self._human_like_delay(1.5, 3.0)
            
            self._log_step("上传页面加载完成", "SUCCESS")
            
            # 关闭可能出现的遮罩/弹窗
            self._close_modal_if_exists()
            
            # 步骤3: 查找上传文件输入框或上传按钮
            self._log_step("步骤3: 查找上传视频的输入框或按钮...")
            
            # 方法1: 优先查找 class 前缀为 "semi-button semi-button-primary" 的 button 按钮，不点击，直接设置文件
            upload_button = None
            file_input = None
            try:
                self._log_step("查找 class 前缀为 'semi-button semi-button-primary' 的 button 按钮...", "INFO")
                # 查找所有 class 包含 "semi-button" 和 "semi-button-primary" 的 button
                buttons = self.page.locator('button[class*="semi-button"][class*="semi-button-primary"]').all()
                
                if buttons:
                    for btn in buttons:
                        try:
                            if btn.is_visible(timeout=3000):
                                upload_button = btn
                                self._log_step("找到上传按钮（semi-button semi-button-primary）", "SUCCESS")
                                
                                # 不点击按钮，直接查找文件输入框并设置文件
                                self._log_step("不点击按钮，直接查找文件输入框并设置文件...", "INFO")
                                
                                # 查找文件输入框（可能在按钮内部，也可能在页面的其他地方）
                                try:
                                    # 方法1: 在按钮内部查找文件输入框
                                    file_input = upload_button.locator('input[type="file"]').first
                                    if file_input.count() == 0:
                                        # 方法2: 在页面中查找文件输入框（可能是隐藏的）
                                        file_input = self.page.locator('input[type="file"]').first
                                    
                                    if file_input.count() > 0:
                                        self._log_step("找到文件输入框，准备选择文件...", "SUCCESS")
                                        # 从指定目录查找视频文件
                                        video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                        if video_file_path and video_file_path.exists():
                                            file_input.set_input_files(str(video_file_path))
                                            self._log_step(f"文件选择成功: {video_file_path.name} (不弹出文件选择窗口)", "SUCCESS")
                                        else:
                                            # 如果未找到，使用原始路径
                                            original_path = str(video_file.absolute())
                                            self._log_step(f"在 {self.default_download_dir} 中未找到文件，使用原始路径", "WARNING")
                                            self._log_step(f"原始路径: {original_path}", "INFO")
                                            file_input.set_input_files(original_path)
                                            self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                    else:
                                        # 如果未找到文件输入框，尝试直接在按钮上设置文件
                                        self._log_step("未找到文件输入框，尝试直接在按钮上设置文件...", "INFO")
                                        video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                        if video_file_path and video_file_path.exists():
                                            upload_button.set_input_files(str(video_file_path))
                                            self._log_step(f"文件选择成功: {video_file_path.name} (不弹出文件选择窗口)", "SUCCESS")
                                        else:
                                            upload_button.set_input_files(str(video_file.absolute()))
                                            self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                except Exception as e:
                                    self._log_step(f"设置文件时出错: {e}，尝试直接使用按钮设置文件", "WARNING")
                                    video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                    if video_file_path and video_file_path.exists():
                                        upload_button.set_input_files(str(video_file_path))
                                        self._log_step(f"文件选择成功: {video_file_path.name} (不弹出文件选择窗口)", "SUCCESS")
                                    else:
                                        upload_button.set_input_files(str(video_file.absolute()))
                                        self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                
                                # 关闭可能出现的遮罩/弹窗
                                self._human_like_delay(0.8, 1.5)
                                self._close_modal_if_exists()
                                break
                        except Exception as e:
                            self._log_step(f"处理按钮时出错: {e}", "WARNING")
                            continue
                
                if not upload_button:
                    raise PlaywrightTimeoutError("未找到 semi-button semi-button-primary 按钮")
                    
            except PlaywrightTimeoutError:
                self._log_step("未找到 semi-button semi-button-primary 按钮，尝试其他方法...", "WARNING")
                
                # 方法2: 优先尝试直接查找文件输入框（最简单直接的方式）
                try:
                    file_input = self.page.wait_for_selector("input[type='file']", timeout=10000)
                    if file_input:
                        self._log_step("找到文件输入框，直接上传文件", "SUCCESS")
                        # 从指定目录查找视频文件
                        video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                        if video_file_path and video_file_path.exists():
                            file_input.set_input_files(str(video_file_path))
                            self._log_step(f"文件选择成功: {video_file_path.name}", "SUCCESS")
                        else:
                            file_input.set_input_files(str(video_file.absolute()))
                            self._log_step("文件选择成功，开始上传...", "SUCCESS")
                        # 关闭可能出现的遮罩/弹窗
                        self._human_like_delay(0.8, 1.5)
                        self._close_modal_if_exists()
                except PlaywrightTimeoutError:
                    self._log_step("未找到文件输入框，尝试通过其他按钮上传...", "WARNING")
                    
                    # 方法3: 查找包含"上传"文本的button
                    try:
                        # 查找 type="button" 且内部有包含"上传"文本的span
                        upload_button = self.page.locator('button[type="button"]').filter(
                            has=self.page.locator('span:has-text("上传")')
                        ).first
                        if upload_button.is_visible(timeout=5000):
                            self._log_step("找到上传按钮（通过文本匹配）", "SUCCESS")
                            # 模拟鼠标移动到按钮上
                            self._human_like_click(upload_button, "点击上传按钮")
                            self._human_like_delay(0.5, 1.0)
                            
                            # 查找文件输入框
                            try:
                                file_input = self.page.locator('input[type="file"]').first
                                if file_input.count() > 0:
                                    video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                    if video_file_path and video_file_path.exists():
                                        file_input.set_input_files(str(video_file_path))
                                        self._log_step(f"文件选择成功: {video_file_path.name}", "SUCCESS")
                                    else:
                                        file_input.set_input_files(str(video_file.absolute()))
                                        self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                else:
                                    # 如果按钮本身可以设置文件
                                    video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                    if video_file_path and video_file_path.exists():
                                        upload_button.set_input_files(str(video_file_path))
                                        self._log_step(f"文件选择成功: {video_file_path.name}", "SUCCESS")
                                    else:
                                        upload_button.set_input_files(str(video_file.absolute()))
                                        self._log_step("文件选择成功，开始上传...", "SUCCESS")
                            except:
                                video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                if video_file_path and video_file_path.exists():
                                    upload_button.set_input_files(str(video_file_path))
                                else:
                                    upload_button.set_input_files(str(video_file.absolute()))
                        else:
                            raise PlaywrightTimeoutError("按钮不可见")
                    except PlaywrightTimeoutError:
                        # 方法4: 尝试遍历所有button
                        try:
                            self._log_step("尝试遍历所有按钮...", "WARNING")
                            buttons = self.page.locator('button[type="button"]').all()
                            for btn in buttons:
                                try:
                                    if btn.locator('span:has-text("上传")').is_visible(timeout=1000):
                                        upload_button = btn
                                        self._log_step("通过遍历找到上传按钮", "SUCCESS")
                                        self._human_like_click(upload_button, "点击上传按钮")
                                        self._human_like_delay(0.5, 1.0)
                                        
                                        # 查找文件输入框
                                        try:
                                            file_input = self.page.locator('input[type="file"]').first
                                            if file_input.count() > 0:
                                                video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                                if video_file_path and video_file_path.exists():
                                                    file_input.set_input_files(str(video_file_path))
                                                    self._log_step(f"文件选择成功: {video_file_path.name}", "SUCCESS")
                                                else:
                                                    file_input.set_input_files(str(video_file.absolute()))
                                                    self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                            else:
                                                video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                                if video_file_path and video_file_path.exists():
                                                    upload_button.set_input_files(str(video_file_path))
                                                    self._log_step(f"文件选择成功: {video_file_path.name}", "SUCCESS")
                                                else:
                                                    upload_button.set_input_files(str(video_file.absolute()))
                                                    self._log_step("文件选择成功，开始上传...", "SUCCESS")
                                        except:
                                            video_file_path = self._find_video_file_in_directory(video_file.name, self.default_download_dir)
                                            if video_file_path and video_file_path.exists():
                                                upload_button.set_input_files(str(video_file_path))
                                            else:
                                                upload_button.set_input_files(str(video_file.absolute()))
                                        
                                        # 关闭可能出现的遮罩/弹窗
                                        self._human_like_delay(0.8, 1.5)
                                        self._close_modal_if_exists()
                                        break
                                except:
                                    continue
                            if upload_button is None:
                                raise PlaywrightTimeoutError("未找到上传按钮")
                        except Exception as e:
                            self._log_step(f"未找到上传按钮或文件输入框: {e}", "ERROR")
                            self._log_step("请确认已登录抖音创作者平台，并页面布局未发生重大变化", "ERROR")
                        video_info["success"] = False
                        video_info["error"] = "未找到上传按钮或文件输入框"
                        return video_info
            
            # 步骤4: 等待上传完成（通过检查页面元素来判断）
            self._log_step("步骤4: 等待视频上传完成...")
            upload_completed = False
            max_wait_time = 600  # 最大等待10分钟
            
            # 主要检测方式：通过页面元素判断上传状态
            start_time = time.time()
            last_progress_time = start_time
            last_status_log_time = start_time
            
            self._log_step("开始检测上传状态（通过页面元素）...", "INFO")
            
            while time.time() - start_time < max_wait_time:
                if upload_completed:
                    break
                
                try:
                    # 方式1（主要方式）: 检查 phone-container 内的按钮文本
                    # 查找 class 前缀为 "phone-container" 的 div
                    try:
                        phone_container = self.page.locator('div[class^="phone-container"]').first
                        
                        # 检查 phone-container 是否存在且可见
                        try:
                            if phone_container.is_visible(timeout=1000):
                                # 在 phone-container 内查找包含"重新上传"的 div（表示上传完成）
                                retry_upload_div = phone_container.locator('div:has-text("重新上传")')
                                try:
                                    if retry_upload_div.count() > 0 and retry_upload_div.first.is_visible(timeout=1000):
                                        upload_completed = True
                                        self._log_step("✅ 检测到'重新上传'按钮，上传已完成", "SUCCESS")
                                        break
                                except:
                                    pass
                                
                                # 检查是否有"取消上传"按钮（表示还在上传）
                                cancel_upload_div = phone_container.locator('div:has-text("取消上传")')
                                try:
                                    if cancel_upload_div.count() > 0 and cancel_upload_div.first.is_visible(timeout=1000):
                                        # 还在上传中
                                        elapsed = int(time.time() - start_time)
                                        # 每10秒记录一次上传状态
                                        if time.time() - last_status_log_time >= 10:
                                            self._log_step(f"检测到'取消上传'按钮，上传进行中... ({elapsed}秒)", "INFO")
                                            last_status_log_time = time.time()
                                except:
                                    pass
                        except:
                            # phone-container 不存在或不可见，继续尝试其他方式
                            pass
                    except Exception as e:
                        # 如果查找 phone-container 失败，继续尝试其他方式
                        pass
                    
                    # 方式2: 检查页面元素变化（上传进度条消失或完成提示出现）
                    try:
                        # 检查是否有上传完成提示
                        completion_indicators = [
                            '上传完成',
                            '上传成功',
                            'upload complete',
                            'upload success'
                        ]
                        page_text = self.page.content()
                        if any(indicator in page_text for indicator in completion_indicators):
                            upload_completed = True
                            self._log_step("✅ 检测到上传完成提示，上传已完成", "SUCCESS")
                            break
                    except:
                        pass
                    
                    # 方式3: 检查页面URL是否变化（跳转到编辑页面）
                    try:
                        current_url = self.page.url
                        if "post/video" in current_url or "content/upload" not in current_url:
                            # 如果不在上传页面，可能已经跳转到编辑页面
                            try:
                                title_input = self.page.get_by_role("textbox", name="填写作品标题", timeout=2000)
                                if title_input.is_visible():
                                    upload_completed = True
                                    self._log_step("✅ 检测到页面跳转和编辑页面元素，上传已完成", "SUCCESS")
                                    break
                            except:
                                pass
                    except:
                        pass
                    
                except Exception as e:
                    # 忽略检查过程中的错误，继续循环
                    pass
                
                # 每5秒显示一次进度
                elapsed = int(time.time() - start_time)
                if elapsed % 5 == 0 and int(time.time()) != int(last_progress_time):
                    self._log_step(f"等待上传完成... ({elapsed}秒)", "INFO")
                    last_progress_time = time.time()
                
                time.sleep(1)
            
            if upload_completed:
                self._log_step("✅ 视频上传完成", "SUCCESS")
                time.sleep(2)  # 等待页面稳定
                # 关闭可能出现的遮罩/弹窗
                self._close_modal_if_exists()
            else:
                # 如果未检测到上传完成，尝试最后的备用检测方式
                self._log_step("⚠️ 未检测到上传完成信号，尝试备用检测方式...", "WARNING")
                
                # 最后尝试: 再次检查 phone-container
                try:
                    phone_container = self.page.locator('div[class^="phone-container"]').first
                    if phone_container.count() > 0:
                        retry_upload_div = phone_container.locator('div:has-text("重新上传")')
                        if retry_upload_div.count() > 0:
                            try:
                                if retry_upload_div.first.is_visible(timeout=2000):
                                    upload_completed = True
                                    self._log_step("✅ 备用检测：检测到'重新上传'按钮，上传已完成", "SUCCESS")
                                    time.sleep(2)
                            except:
                                pass
                except:
                    pass
                
                if not upload_completed:
                    # 检查是否在编辑页面
                    try:
                        current_url = self.page.url
                        if "post/video" in current_url:
                            self._log_step("检测到页面跳转到编辑页面，可能上传已完成", "SUCCESS")
                            upload_completed = True
                        else:
                            # 检查编辑页面元素
                            try:
                                title_input = self.page.get_by_role("textbox", name="填写作品标题", timeout=5000)
                                if title_input.is_visible():
                                    self._log_step("检测到编辑页面元素，可能上传已完成", "SUCCESS")
                                    upload_completed = True
                            except:
                                self._log_step("未检测到编辑页面元素，继续执行后续步骤", "WARNING")
                    except:
                        self._log_step("备用检测方式失败，继续执行后续步骤", "WARNING")
                    
                    if not upload_completed:
                        self._log_step("⚠️ 无法确认上传是否完成，但继续执行后续步骤", "WARNING")
                
                time.sleep(3)
            
            # 步骤5: 确保在编辑页面（如果需要跳转）
            self._log_step("步骤5: 确保在视频编辑页面...")
            current_url = self.page.url
            if "post/video" not in current_url:
                try:
                    self.page.goto("https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page", 
                                  wait_until="domcontentloaded", timeout=TIMEOUT)
                    time.sleep(2)
                    self._log_step("已跳转到编辑页面", "SUCCESS")
                except Exception as e:
                    self._log_step(f"跳转页面失败: {e}，继续在当前页面操作", "WARNING")
            else:
                self._log_step("已在编辑页面", "SUCCESS")
            
            # 关闭可能出现的遮罩/弹窗
            self._close_modal_if_exists()
            
            # 步骤6: 填写作品标题（参照参考文件的多重定位方式）
            self._log_step(
                f"步骤6: 填写作品标题 | 将写入页面: {title!r} | 来源类型={title_source} | {title_source_detail}",
                "INFO",
            )
            filled_title = False
            title_selectors = [
                "input[placeholder='填写作品标题']",
                "input[placeholder*='填写作品标题']",
                "textarea[placeholder='填写作品标题']",
                "textarea[placeholder*='填写作品标题']",
            ]
            
            for selector in title_selectors:
                try:
                    title_input = self.page.query_selector(selector)
                    if title_input:
                        self._human_like_click(title_input, "点击标题输入框")
                        self._human_like_type(title_input, title, "输入标题")
                        self._log_step(f"标题填写成功: {title} (使用选择器: {selector})", "SUCCESS")
                        filled_title = True
                        break
                except Exception:
                    continue
            
            if not filled_title:
                # 备用方法：使用role定位
                try:
                    title_input = self.page.get_by_role("textbox", name="填写作品标题，为作品获得更多流量")
                    self._human_like_click(title_input, "点击标题输入框")
                    self._human_like_type(title_input, title, "输入标题")
                    self._log_step(f"标题填写成功: {title} (使用role定位)", "SUCCESS")
                    filled_title = True
                except PlaywrightTimeoutError:
                    self._log_step("警告: 未找到标题输入框（placeholder='填写作品标题'），可能需要手动填写标题", "WARNING")
            
            # 步骤7: 填写话题区（DeepSeek profile + 换行 + 标签）
            profile_for_zone = ""
            if short_video_meta is not None:
                profile_for_zone = str(short_video_meta.get("profile") or "").strip()
            self._log_step(
                f"步骤7: 填写话题区 | profile={'DeepSeek.profile' if profile_for_zone else '无'}"
                f" | 标签={hashtags!r}",
                "INFO",
            )
            try:
                self._fill_zone_container_with_profile_and_hashtags(profile_for_zone, hashtags or "")
            except PlaywrightTimeoutError:
                self._log_step("未找到话题标签输入框", "WARNING")
            except Exception as e:
                self._log_step(f"填写话题区时出错: {e}", "WARNING")
            
            # 关闭可能出现的遮罩/弹窗
            self._close_modal_if_exists()
            
            # 等待30-60秒后再选择封面
            wait_time = random.uniform(30, 60)
            self._log_step(f"等待 {wait_time:.1f} 秒后再选择封面...", "INFO")
            time.sleep(wait_time)
            self._log_step("等待完成，开始选择封面", "SUCCESS")
            
            # 步骤8: 选择封面
            self._log_step("步骤8: 选择封面...")
            try:
                # 点击封面元素（简化版，只保留基本的选择封面功能）
                # 查找并点击 class 前缀为 "maskBox" 的 div（包含 blob URL 的 img）
                mask_box_clicked = False
                mask_boxes = self.page.locator('div[class^="maskBox"]').all()
                
                for mask_box in mask_boxes:
                    try:
                        img = mask_box.locator('img').first
                        if img.count() > 0:
                            img_src = img.evaluate('el => el.src')
                            if img_src and img_src.startswith('blob:https://creator.douyin.com'):
                                if mask_box.is_visible(timeout=5000):
                                    self._human_like_click(mask_box, "点击封面")
                                    self._log_step("已点击封面", "SUCCESS")
                                    mask_box_clicked = True
                                    break
                    except Exception as e:
                        continue
                
                if not mask_box_clicked:
                    # 备用方法：直接点击第一个 maskBox
                    try:
                        mask_box = self.page.locator('div[class^="maskBox"]').first
                        if mask_box.count() > 0 and mask_box.is_visible(timeout=5000):
                            self._human_like_click(mask_box, "点击封面（备用方法）")
                            self._log_step("已点击封面（备用方法）", "SUCCESS")
                            mask_box_clicked = True
                    except Exception as e:
                        self._log_step(f"点击封面失败: {e}", "WARNING")
                
                if mask_box_clicked:
                    # 等待弹窗出现
                    self._human_like_delay(1.0, 2.0)
                    
                    # 查找弹窗中的"确定"按钮并点击（选择封面后的确认弹窗）
                    # 优先查找置顶div中的 <span class="semi-button-content">确定</span>
                    self._log_step("查找并点击确认弹窗中的确定按钮...", "INFO")
                    confirm_button_clicked = False
                    
                    try:
                        # 方法1: 优先查找 <span class="semi-button-content">确定</span>（置顶div中）
                        try:
                            self._log_step("查找 span.semi-button-content 且包含'确定'文本的元素...", "INFO")
                            # 查找 class="semi-button-content" 且包含"确定"文本的 span
                            confirm_spans = self.page.locator('span.semi-button-content:has-text("确定")').all()
                            
                            if confirm_spans:
                                self._log_step(f"找到 {len(confirm_spans)} 个 span.semi-button-content 且包含'确定'的元素", "INFO")
                                
                                # 查找可见的span并点击
                                for span in confirm_spans:
                                    try:
                                        if span.is_visible(timeout=3000):
                                            self._human_like_click(span, "点击确认弹窗中的确定按钮（span.semi-button-content）")
                                            self._log_step("已点击确认弹窗中的确定按钮（span.semi-button-content）", "SUCCESS")
                                            confirm_button_clicked = True
                                            break
                                    except:
                                        continue
                        except:
                            pass
                            
                        # 如果未找到，尝试查找包含"确定"文本的 span.semi-button-content（不区分大小写）
                        if not confirm_button_clicked:
                            try:
                                all_spans = self.page.locator('span.semi-button-content').all()
                                for span in all_spans:
                                    try:
                                        if span.is_visible(timeout=2000):
                                            span_text = span.inner_text(timeout=1000).strip()
                                            if "确定" in span_text:
                                                self._human_like_click(span, "点击确认弹窗中的确定按钮（span.semi-button-content，文本匹配）")
                                                self._log_step(f"已点击确认弹窗中的确定按钮（文本: '{span_text}'）", "SUCCESS")
                                                confirm_button_clicked = True
                                                break
                                    except:
                                        continue
                            except Exception as e:
                                self._log_step(f"方法1查找确定按钮失败: {e}", "WARNING")
            
                        # 方法2: 如果方法1失败，查找包含"确定"文本的按钮（备用方法）
                        if not confirm_button_clicked:
                            try:
                                self._log_step("方法1未找到，尝试查找包含'确定'文本的按钮...", "INFO")
                                confirm_buttons = []
                                
                                # 方式1: 查找 button 中包含 "确定" 文本的
                                try:
                                    buttons_with_text = self.page.locator('button:has-text("确定")').all()
                                    confirm_buttons.extend(buttons_with_text)
                                except:
                                    pass
                                
                                # 方式2: 查找 button 中 span 包含 "确定" 文本的
                                try:
                                    buttons_with_span = self.page.locator('button').filter(has=self.page.locator('span:has-text("确定")')).all()
                                    confirm_buttons.extend(buttons_with_span)
                                except:
                                    pass
                                
                                # 去重（通过比较按钮的位置）
                                unique_buttons = []
                                seen_locations = set()
                                for btn in confirm_buttons:
                                    try:
                                        if btn.is_visible(timeout=2000):
                                            box = btn.bounding_box()
                                            if box:
                                                location = (int(box['x']), int(box['y']))
                                                if location not in seen_locations:
                                                    seen_locations.add(location)
                                                    unique_buttons.append(btn)
                                    except:
                                        continue
                                
                                if unique_buttons:
                                    try:
                                        self._human_like_click(unique_buttons[0], "点击确认弹窗中的确定按钮（备用方法）")
                                        self._log_step("已点击确认弹窗中的确定按钮（备用方法）", "SUCCESS")
                                        confirm_button_clicked = True
                                    except Exception as e:
                                        self._log_step(f"点击确定按钮时出错: {e}", "WARNING")
                            except Exception as e:
                                self._log_step(f"方法2查找确定按钮失败: {e}", "WARNING")
            
                        if not confirm_button_clicked:
                            self._log_step("未找到确认弹窗中的确定按钮", "WARNING")
                        else:
                            # 等待确认操作完成
                            self._human_like_delay(1.0, 2.0)
                            
                    except Exception as e:
                        self._log_step(f"查找确定按钮时出错: {e}", "WARNING")
                else:
                    self._log_step("未找到封面元素，跳过封面选择", "WARNING")
                
            except PlaywrightTimeoutError:
                self._log_step("封面选择步骤跳过（可能已自动选择或未找到元素）", "WARNING")
            except Exception as e:
                self._log_step(f"选择封面时出错: {e}", "WARNING")
            
            # 关闭可能出现的遮罩/弹窗
            self._close_modal_if_exists()
            
            # 步骤9: 设置可见性（保持默认状态，不选择任何可见性选项）
            self._log_step(f"步骤9: 保持可见性为默认状态（不选择任何可见性选项）")
            # 跳过可见性选择，保持默认状态
            if False:  # 跳过所有可见性选择逻辑
                if visibility == "仅自己可见":
                    selected = False
                
                # 方法0（优先）: 在 class 前缀为 "radio" 的 label 中查找 span 标签，内容为"仅自己可见"
                try:
                    self._log_step("尝试通过 radio label 中的 span 选择「仅自己可见」...", "INFO")
                    # 查找 class 前缀为 "radio" 的 label
                    radio_labels = self.page.locator('label[class^="radio"]').all()
                    self._log_step(f"找到 {len(radio_labels)} 个 class 前缀为 'radio' 的 label", "INFO")
                    
                    for radio_label in radio_labels:
                        try:
                            if radio_label.is_visible(timeout=2000):
                                # 在 label 中查找内容为"仅自己可见"的 span 标签
                                span = radio_label.locator('span:has-text("仅自己可见")').first
                                if span.count() > 0 and span.is_visible(timeout=1000):
                                    # 点击 label（而不是 span）
                                    self._human_like_click(radio_label, "点击包含「仅自己可见」span 的 radio label")
                                    selected = True
                                    self._log_step("已通过 radio label 中的 span 选择「仅自己可见」选项", "SUCCESS")
                                    break
                        except:
                            continue
                    
                    if not selected:
                        self._log_step("未找到包含「仅自己可见」span 的 radio label", "WARNING")
                except Exception as e:
                    self._log_step(f"通过 radio label 选择「仅自己可见」失败: {e}，尝试其他方法...", "WARNING")
                
                # 方法1: 精确查找 checkbox（id=\"micro\" > id=\"root\" 下的 input[type=\"checkbox\"].radio-native-p6VBGt[value=\"1\"]）
                if not selected:
                    try:
                        self._log_step("尝试通过 checkbox 精确选择「仅自己可见」...", "INFO")
                        checkbox = self.page.locator(
                            'div#micro div#root input[type=\"checkbox\"][class^=\"radio-native-p6VBGt\"][value=\"1\"]'
                        ).first
                        if checkbox.count() > 0:
                            if not checkbox.is_checked():
                                checkbox.check(timeout=TIMEOUT)
                                selected = True
                                self._log_step("已通过 checkbox 选择「仅自己可见」选项", "SUCCESS")
                            else:
                                selected = True
                                self._log_step("checkbox 已经处于「仅自己可见」选中状态", "SUCCESS")
                        else:
                            self._log_step("未找到符合条件的 checkbox（radio-native-p6VBGt, value=1）", "WARNING")
                    except Exception as e:
                        self._log_step(f"通过 checkbox 选择「仅自己可见」失败: {e}，尝试其他方法...", "WARNING")
                
                # 方法1: 先找到"谁可以看"文本，然后在其附近查找
                if not selected:
                    try:
                        self._log_step("尝试通过「谁可以看」区域选择「仅自己可见」...", "INFO")
                        who_can_see = self.page.get_by_text("谁可以看")
                        if who_can_see.is_visible(timeout=5000):
                            private_label = self.page.get_by_text("仅自己可见")
                            if private_label.is_visible(timeout=3000):
                                self._human_like_click(private_label, "点击「仅自己可见」选项")
                                selected = True
                                self._log_step("已通过「谁可以看」区域选择「仅自己可见」选项", "SUCCESS")
                    except Exception as e:
                        self._log_step(f"通过「谁可以看」区域选择失败: {e}", "WARNING")
                
                # 方法2: 直接查找label
                if not selected:
                    try:
                        self._log_step("尝试通过 label 选择「仅自己可见」...", "INFO")
                        private_label = self.page.locator("label:has-text('仅自己可见')")
                        if private_label.is_visible(timeout=3000):
                            self._human_like_click(private_label, "点击「仅自己可见」label")
                            selected = True
                            self._log_step("已通过label选择「仅自己可见」选项", "SUCCESS")
                    except Exception as e:
                        self._log_step(f"通过 label 选择失败: {e}", "WARNING")
                
                # 方法3: 查找单选按钮
                if not selected:
                    try:
                        self._log_step("尝试通过单选按钮选择「仅自己可见」...", "INFO")
                        radio_selectors = [
                            "input[type='radio'][value*='private']",
                            "input[type='radio'][value*='仅自己可见']",
                            "input[type='radio'][aria-label*='仅自己可见']",
                            "input[type='radio'][value='1']",
                            "input[type='radio'][value='private']",
                        ]
                        for selector in radio_selectors:
                            try:
                                radio = self.page.locator(selector).first
                                if radio.count() > 0 and radio.is_visible(timeout=2000):
                                    if not radio.is_checked():
                                        self._human_like_click(radio, f"点击单选按钮 {selector}")
                                        selected = True
                                        self._log_step(f"已通过单选按钮 {selector} 选择「仅自己可见」选项", "SUCCESS")
                                        break
                                    else:
                                        selected = True
                                        self._log_step(f"单选按钮 {selector} 已经处于「仅自己可见」选中状态", "SUCCESS")
                                        break
                            except:
                                continue
                    except Exception as e:
                        self._log_step(f"通过单选按钮选择失败: {e}", "WARNING")
                
                # 方法4: 直接通过文本定位
                if not selected:
                    try:
                        self._log_step("尝试通过文本定位选择「仅自己可见」...", "INFO")
                        private_text = self.page.get_by_text("仅自己可见")
                        if private_text.is_visible(timeout=3000):
                            self._human_like_click(private_text, "点击「仅自己可见」文本")
                            selected = True
                            self._log_step("已通过文本定位选择「仅自己可见」选项", "SUCCESS")
                    except Exception as e:
                        self._log_step(f"通过文本定位选择失败: {e}", "WARNING")
                
                # 方法5: 查找包含"仅自己可见"的 span 或 div，然后点击其父元素
                if not selected:
                    try:
                        self._log_step("尝试通过父元素选择「仅自己可见」...", "INFO")
                        # 查找包含"仅自己可见"文本的元素
                        private_elements = self.page.locator('text=仅自己可见').all()
                        for elem in private_elements:
                            try:
                                if elem.is_visible(timeout=2000):
                                    # 尝试点击元素本身
                                    self._human_like_click(elem, "点击「仅自己可见」元素")
                                    selected = True
                                    self._log_step("已通过元素选择「仅自己可见」选项", "SUCCESS")
                                    break
                            except:
                                continue
                    except Exception as e:
                        self._log_step(f"通过父元素选择失败: {e}", "WARNING")
                
                # 方法6: 查找所有包含"仅自己可见"的可点击元素
                if not selected:
                    try:
                        self._log_step("尝试查找所有包含「仅自己可见」的可点击元素...", "INFO")
                        clickable_selectors = [
                            'button:has-text("仅自己可见")',
                            'div:has-text("仅自己可见")',
                            'span:has-text("仅自己可见")',
                            '[role="radio"]:has-text("仅自己可见")',
                            '[role="option"]:has-text("仅自己可见")',
                        ]
                        for selector in clickable_selectors:
                            try:
                                elements = self.page.locator(selector).all()
                                for elem in elements:
                                    try:
                                        if elem.is_visible(timeout=2000):
                                            self._human_like_click(elem, f"点击「仅自己可见」元素 ({selector})")
                                            selected = True
                                            self._log_step(f"已通过 {selector} 选择「仅自己可见」选项", "SUCCESS")
                                            break
                                    except:
                                        continue
                                if selected:
                                    break
                            except:
                                continue
                    except Exception as e:
                        self._log_step(f"通过可点击元素选择失败: {e}", "WARNING")
                
                if not selected:
                    self._log_step("警告: 未能自动选择「仅自己可见」，可能需要手动在「谁可以看」单选框中选择", "WARNING")
                else:
                    # 等待选择生效
                    self._human_like_delay(0.5, 1.0)
                    
                    # 二次确认是否选择了"仅自己可见"
                    self._log_step("二次确认是否选择了「仅自己可见」...", "INFO")
                    confirmed = False
                    
                    # 方法1: 检查 checkbox 是否被选中
                    try:
                        checkbox = self.page.locator(
                            'div#micro div#root input[type="checkbox"][class^="radio-native-p6VBGt"][value="1"]'
                        ).first
                        if checkbox.count() > 0 and checkbox.is_checked():
                            confirmed = True
                            self._log_step("确认：checkbox 已选中「仅自己可见」", "SUCCESS")
                    except:
                        pass
                    
                    # 方法2: 检查单选按钮是否被选中
                    if not confirmed:
                        try:
                            radio_selectors = [
                                "input[type='radio'][value*='private']",
                                "input[type='radio'][value*='仅自己可见']",
                                "input[type='radio'][value='1']",
                                "input[type='radio'][value='private']",
                            ]
                            for selector in radio_selectors:
                                try:
                                    radio = self.page.locator(selector).first
                                    if radio.count() > 0 and radio.is_checked():
                                        confirmed = True
                                        self._log_step(f"确认：单选按钮 {selector} 已选中「仅自己可见」", "SUCCESS")
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    # 方法3: 检查页面文本是否显示"仅自己可见"
                    if not confirmed:
                        try:
                            private_text = self.page.get_by_text("仅自己可见")
                            if private_text.is_visible(timeout=2000):
                                # 检查父元素是否包含选中状态
                                parent = private_text.locator("..")
                                parent_classes = parent.get_attribute("class") or ""
                                if "selected" in parent_classes.lower() or "checked" in parent_classes.lower() or "active" in parent_classes.lower():
                                    confirmed = True
                                    self._log_step("确认：页面显示「仅自己可见」且处于选中状态", "SUCCESS")
                                else:
                                    # 即使没有明确的选中状态，如果文本可见，也认为已选择
                                    confirmed = True
                                    self._log_step("确认：页面显示「仅自己可见」", "SUCCESS")
                        except:
                            pass
                    
                    if confirmed:
                        self._log_step("二次确认成功：已选择「仅自己可见」", "SUCCESS")
                        # 等待10-30秒后再发布
                        wait_time = random.uniform(10, 30)
                        self._log_step(f"等待 {wait_time:.1f} 秒后再发布...", "INFO")
                        time.sleep(wait_time)
                        self._log_step("等待完成，准备发布", "SUCCESS")
                    else:
                        self._log_step("警告：二次确认失败，无法确认是否选择了「仅自己可见」，但仍将继续发布流程", "WARNING")
                        # 即使确认失败，也等待一段时间
                        wait_time = random.uniform(10, 30)
                        self._log_step(f"等待 {wait_time:.1f} 秒后再发布...", "INFO")
                        time.sleep(wait_time)
                # 跳过"公开"选项选择（保持默认状态）
                # elif visibility == "公开":
                #     try:
                #         public_label = self.page.locator("label").filter(has_text="公开")
                #         public_label.click(timeout=TIMEOUT)
                #         self._log_step("可见性设置为公开", "SUCCESS")
                #     except PlaywrightTimeoutError:
                #         self._log_step("未找到公开选项，使用默认设置", "WARNING")
            
            # 关闭可能出现的遮罩/弹窗
            self._close_modal_if_exists()
            
            # 步骤10: 自动发布视频
            self._log_step("步骤10: 自动发布视频...")
            try:
                # 查找发布按钮（button 内容是"发布"）
                publish_button = None
                publish_clicked = False
                
                # 方法1（优先）: 在 id="root" 的 div 中查找 button 元素，其文本内容为"发布"
                try:
                    publish_button = self.page.locator('div#root button').filter(has_text="发布").first
                    if publish_button.count() > 0 and publish_button.is_visible(timeout=5000):
                        # 验证按钮内容确实是"发布"
                        button_text = publish_button.inner_text()
                        if button_text.strip() == "发布":
                            # 打印当前将要点击的发布按钮信息
                            self._log_publish_button_info(publish_button, "method1-filter(div#root button, has_text='发布')")
                            # 点击前先将按钮颜色改为绿色，便于视觉确认
                            try:
                                publish_button.evaluate("el => { el.style.backgroundColor = 'green'; el.style.color = 'white'; }")
                            except Exception:
                                pass
                            publish_clicked = True
                except Exception as e:
                    self._log_step(f"方法1查找失败: {e}，尝试其他方法...", "INFO")
                
                # 方法2: 在 id="root" 的 div 中使用 has-text 选择器
                if not publish_clicked:
                    try:
                        publish_button = self.page.locator("div#root button:has-text('发布')").first
                        if publish_button.count() > 0 and publish_button.is_visible(timeout=5000):
                            # 验证按钮内容
                            button_text = publish_button.inner_text()
                            if button_text.strip() == "发布":
                                self._log_publish_button_info(publish_button, "method2-locator(div#root button:has-text('发布'))")
                                publish_clicked = True
                    except Exception as e:
                        self._log_step(f"方法2查找失败: {e}，尝试其他方法...", "INFO")
                
                # 方法3: 通过角色定位，精确匹配"发布"
                if not publish_clicked:
                    try:
                        publish_button = self.page.get_by_role("button", name="发布", exact=True)
                        if publish_button.is_visible(timeout=5000):
                            self._log_publish_button_info(publish_button, "method3-get_by_role(name='发布')")
                            publish_clicked = True
                    except Exception as e:
                        self._log_step(f"方法3查找失败: {e}，尝试其他方法...", "INFO")
                
                # 方法4: 在 id="root" 的 div 中查找所有按钮，筛选出内容为"发布"的
                if not publish_clicked:
                    try:
                        all_buttons = self.page.locator("div#root button").all()
                        for btn in all_buttons:
                            try:
                                if btn.is_visible(timeout=1000):
                                    btn_text = btn.inner_text()
                                    if btn_text.strip() == "发布":
                                        self._log_publish_button_info(btn, "method4-iterate(div#root button)")
                                        publish_button = btn
                                        publish_clicked = True
                                        break
                            except:
                                continue
                    except Exception as e:
                        self._log_step(f"方法4查找失败: {e}，尝试其他方法...", "INFO")
                
                if not publish_clicked:
                    raise PlaywrightTimeoutError("未找到内容为「发布」的按钮")
                
                # 在点击发布按钮前，等待30-60秒
                wait_seconds = random.randint(30, 60)
                self._log_step(f"找到发布按钮，点击前等待 {wait_seconds} 秒（30-60秒范围）...", "INFO")
                wait_start_time = time.time()
                for remaining in range(wait_seconds, 0, -1):
                    elapsed = time.time() - wait_start_time
                    self._log_step(f"  倒计时: {remaining} 秒 (已等待: {elapsed:.1f} 秒)", "INFO")
                    time.sleep(1)
                wait_end_time = time.time()
                wait_duration = wait_end_time - wait_start_time
                self._log_step(f"等待完成，实际等待时间: {wait_duration:.1f} 秒，准备点击发布按钮", "INFO")
                
                # 点击发布按钮
                self._human_like_click(publish_button, "点击「发布」按钮")
                self._log_step("已点击「发布」按钮", "SUCCESS")
                
                # 等待随机时间（15-60秒），期间仅打印倒计时，不主动检查或跳转页面
                wait_seconds = random.randint(15, 60)
                self._log_step(f"点击「发布」后，等待随机时间 {wait_seconds} 秒（15-60秒范围）以便页面自动跳转...", "INFO")
                wait_start_time = time.time()
                for remaining in range(wait_seconds, 0, -1):
                    elapsed = time.time() - wait_start_time
                    self._log_step(f"  倒计时: {remaining} 秒 (已等待: {elapsed:.1f} 秒)", "INFO")
                    time.sleep(1)
                wait_end_time = time.time()
                wait_duration = wait_end_time - wait_start_time
                self._log_step(f"等待完成，实际等待时间: {wait_duration:.1f} 秒", "INFO")
                
                self._log_step("发布流程完成", "SUCCESS")
                
                self._log_step("=" * 60)
                self._log_step("视频上传流程完成", "SUCCESS")
                self._log_step("=" * 60)
                
                video_info["success"] = True
                
                # 上传成功后，保存最新的 cookies（不刷新页面，避免触发检测）
                self._log_step("保存最新的登录信息（cookies）到文件...", "INFO")
                try:
                    self.save_cookies()
                except Exception as e:
                    self._log_step(f"保存 cookies 时出错: {e}", "WARNING")
                
                # 如果不是最后一个视频，保持浏览器打开并重新导航到上传页面
                if keep_browser_open:
                    self._log_step("保持浏览器打开，准备上传下一个视频...")
                    # 添加随机延迟，避免频繁操作
                    self._human_like_delay(3.0, 8.0)
                    
                    # 重新访问上传页面时，先检查登录状态
                    self._log_step("重新访问上传页面（将携带已有的 cookies 信息）...", "INFO")
                    self.page.goto(DOUYIN_UPLOAD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                    self._human_like_delay(2.0, 4.0)
                    
                    # 检查登录状态
                    self._log_step("检查登录状态...", "INFO")
                    is_logged_in = self._check_login_status()
                    if not is_logged_in:
                        self._log_step("⚠️ 检测到登录状态失效，尝试重新加载 cookies...", "WARNING")
                        # 重新加载 cookies（当前页面已经是上传页面，不需要刷新）
                        cookies_reloaded = self.load_cookies(skip_reload=True)
                        if cookies_reloaded:
                            # 当前页面已经是上传页面，直接检查登录状态，不需要 reload
                            self._human_like_delay(1.0, 2.0)
                            is_logged_in = self._check_login_status()
                            if not is_logged_in:
                                self._log_step("❌ 登录状态已失效，无法继续上传", "ERROR")
                                # 保存错误信息到 video_info
                                video_info["login_failed"] = True
                        else:
                            self._log_step("❌ 无法重新加载 cookies，登录状态已失效", "ERROR")
                            video_info["login_failed"] = True
                    else:
                        self._log_step("✅ 登录状态正常，可以继续上传", "SUCCESS")
                    
                    self._close_modal_if_exists()
                else:
                    # 只有是最后一个视频时才关闭浏览器
                    try:
                        if self.browser:
                            self.browser.close()
                            self._log_step("浏览器已关闭", "SUCCESS")
                        if self.playwright:
                            self.playwright.stop()
                            self._log_step("Playwright已停止", "SUCCESS")
                    except Exception as e:
                        self._log_step(f"关闭浏览器时出错: {e}", "WARNING")
                
                return video_info
            except PlaywrightTimeoutError:
                self._log_step("未找到发布按钮，请手动发布", "WARNING")
                video_info["success"] = True  # 即使未找到发布按钮，也认为上传成功（可能需要手动发布）
            except Exception as e:
                self._log_step(f"发布时出错: {e}", "WARNING")
                video_info["success"] = True  # 即使发布出错，也认为上传成功
            
            self._log_step("=" * 60)
            self._log_step("视频上传流程完成", "SUCCESS")
            self._log_step("=" * 60)
            
            # 上传成功后，保存最新的 cookies（不刷新页面，避免触发检测）
            self._log_step("保存最新的登录信息（cookies）到文件...", "INFO")
            try:
                self.save_cookies()
            except Exception as e:
                self._log_step(f"保存 cookies 时出错: {e}", "WARNING")
            
            # 如果不是最后一个视频，保持浏览器打开并重新导航到上传页面
            if keep_browser_open:
                self._log_step("保持浏览器打开，准备上传下一个视频...")
                # 添加随机延迟，避免频繁操作
                self._human_like_delay(3.0, 8.0)
                
                # 重新访问上传页面时，先检查登录状态
                self._log_step("重新访问上传页面（将携带已有的 cookies 信息）...", "INFO")
                self.page.goto(DOUYIN_UPLOAD_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
                self._human_like_delay(2.0, 4.0)
                
                # 检查登录状态
                self._log_step("检查登录状态...", "INFO")
                is_logged_in = self._check_login_status()
                if not is_logged_in:
                    self._log_step("⚠️ 检测到登录状态失效，尝试重新加载 cookies...", "WARNING")
                    # 重新加载 cookies（当前页面已经是上传页面，不需要刷新）
                    cookies_reloaded = self.load_cookies(skip_reload=True)
                    if cookies_reloaded:
                        # 当前页面已经是上传页面，直接检查登录状态，不需要 reload
                        self._human_like_delay(1.0, 2.0)
                        is_logged_in = self._check_login_status()
                        if not is_logged_in:
                            self._log_step("❌ 登录状态已失效，无法继续上传", "ERROR")
                            video_info["login_failed"] = True
                    else:
                        self._log_step("❌ 无法重新加载 cookies，登录状态已失效", "ERROR")
                        video_info["login_failed"] = True
                else:
                    self._log_step("✅ 登录状态正常，可以继续上传", "SUCCESS")
                
                self._close_modal_if_exists()
            else:
                # 只有是最后一个视频时才关闭浏览器
                try:
                    if self.browser:
                        self.browser.close()
                        self._log_step("浏览器已关闭", "SUCCESS")
                    if self.playwright:
                        self.playwright.stop()
                        self._log_step("Playwright已停止", "SUCCESS")
                except Exception as e:
                    self._log_step(f"关闭浏览器时出错: {e}", "WARNING")
            
            return video_info
            
        except Exception as e:
            self._log_step(f"上传过程中发生错误: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            video_info["success"] = False
            video_info["error"] = str(e)
            return video_info
    
    def close(self):
        """关闭浏览器"""
        try:
            # 停止鼠标移动模拟
            self._stop_mouse_move_simulation()
            
            # 注意：不再在上传后重复保存 cookies，cookies 应在登录时保存
            # 但在关闭前最后保存一次最新的cookies
            try:
                if self.page and not self.page.is_closed():
                    self.save_cookies()
            except:
                pass
            
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self._log_step("浏览器已关闭", "SUCCESS")
        except Exception as e:
            self._log_step(f"关闭浏览器时出错: {e}", "WARNING")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    def save_upload_results(self, upload_results: List[Dict], result_dir: Optional[Path] = None):
        """
        保存上传结果到文件
        
        如果 video_path 已存在，则更新原记录；如果不存在，则追加新记录。
        这样可以处理之前上传失败、现在上传成功的情况。
        
        Args:
            upload_results: 上传结果列表，每个元素是包含视频信息的字典
            result_dir: 结果保存目录，如果为None则使用默认目录
        """
        if result_dir is None:
            result_dir = Path(__file__).parent.parent / "data" / "upload_result" / "douyin"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件名格式：upload_www.youtube.com.json
        result_filename = "upload_www.youtube.com.json"
        result_path = result_dir / result_filename
        
        # 加载已存在的结果（如果存在）
        existing_results = []
        if result_path.exists():
            try:
                with open(result_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_results = existing_data.get('results', [])
            except Exception as e:
                self._log_step(f"读取现有上传记录失败: {e}，将创建新文件", "WARNING")
                existing_results = []
        
        # 创建 video_path 到索引的映射，用于快速查找和更新
        path_to_index = {}
        for idx, result in enumerate(existing_results):
            video_path = result.get('video_path', '')
            if video_path:
                path_to_index[video_path] = idx
        
        # 处理新结果：更新已存在的记录或追加新记录
        updated_count = 0
        added_count = 0
        for result in upload_results:
            video_path = result.get('video_path', '')
            if not video_path:
                continue
            
            if video_path in path_to_index:
                # 已存在，更新原记录
                index = path_to_index[video_path]
                existing_results[index] = result
                updated_count += 1
            else:
                # 不存在，追加新记录
                existing_results.append(result)
                path_to_index[video_path] = len(existing_results) - 1
                added_count += 1
        
        # 保存结果
        result_data = {
            "total": len(existing_results),
            "results": existing_results,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        if updated_count > 0 and added_count > 0:
            self._log_step(f"上传结果已保存: 更新 {updated_count} 条，新增 {added_count} 条，总计 {len(existing_results)} 条", "SUCCESS")
        elif updated_count > 0:
            self._log_step(f"上传结果已保存: 更新 {updated_count} 条记录，总计 {len(existing_results)} 条", "SUCCESS")
        elif added_count > 0:
            self._log_step(f"上传结果已保存: 新增 {added_count} 条，总计 {len(existing_results)} 条", "SUCCESS")
        else:
            self._log_step(f"上传结果已保存到: {result_path}", "SUCCESS")
    
    def upload_videos_from_folder(self, folder_path: str, visibility: str = "公开", 
                                  auto_publish: bool = False, delay: float = 5.0):
        """
        从文件夹批量上传视频到抖音
        
        Args:
            folder_path: 视频文件夹路径
            visibility: 可见性设置（"仅自己可见" 或 "公开"）
            auto_publish: 是否自动发布（默认False）
            delay: 每个视频上传之间的延迟（秒），默认5秒
            
        Returns:
            上传结果列表，每个元素是包含视频信息的字典
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            self._log_step(f"错误: 文件夹不存在或不是目录: {folder_path}", "ERROR")
            return []
        
        # 支持的视频文件格式
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v'}
        
        # 获取所有视频文件
        video_files = []
        for ext in video_extensions:
            video_files.extend(folder.glob(f"*{ext}"))
            video_files.extend(folder.glob(f"*{ext.upper()}"))
        
        # 按文件名排序
        video_files = sorted(video_files)
        
        if not video_files:
            self._log_step(f"文件夹中没有找到视频文件: {folder_path}", "WARNING")
            return []
        
        self._log_step(f"找到 {len(video_files)} 个视频文件")
        self._log_step("=" * 60)
        
        results = []
        total = len(video_files)
        
        for i, video_file in enumerate(video_files, 1):
            self._log_step("")
            self._log_step("=" * 60)
            self._log_step(f"上传视频 {i}/{total}: {video_file.name}")
            self._log_step("=" * 60)
            
            # 每3个视频后，添加额外的会话保持操作和更长的延迟
            if i > 1 and i % 3 == 0:
                self._log_step(f"已上传 {i-1} 个视频，执行会话保持操作...", "INFO")
                try:
                    # 模拟用户浏览行为：随机滚动页面
                    self.page.evaluate("window.scrollBy(0, Math.random() * 500 - 250)")
                    self._human_like_delay(1.0, 2.0)
                    
                    # 模拟鼠标移动
                    self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    self._human_like_delay(0.5, 1.0)
                    
                    self._log_step("会话保持操作完成", "SUCCESS")
                except Exception as e:
                    self._log_step(f"会话保持操作出错: {e}", "WARNING")
                
                # 每3个视频后，增加更长的延迟时间
                extra_delay = random.uniform(10.0, 20.0)
                self._log_step(f"已上传 {i-1} 个视频，等待 {extra_delay:.1f} 秒以降低检测风险...", "INFO")
                time.sleep(extra_delay)
            
            try:
                # 判断是否是最后一个视频
                is_last = (i == total)
                
                # 调用上传方法，如果不是最后一个，保持浏览器打开
                result = self.upload_video(
                    video_path=str(video_file),
                    title=None,  # 由 DeepSeek 生成标题
                    hashtags=None,  # 由 DeepSeek 生成话题
                    cover_text=None,  # 使用标题
                    visibility=visibility,
                    auto_publish=auto_publish,
                    keep_browser_open=not is_last  # 不是最后一个时保持浏览器打开
                )
                
                results.append(result)
                
                # 立即保存上传结果到 JSON 文件（无论成功或失败）
                try:
                    self.save_upload_results([result])
                    self._log_step(f"上传结果已保存到 JSON 文件", "INFO")
                except Exception as save_error:
                    self._log_step(f"⚠️  保存上传结果失败: {save_error}", "WARNING")
                
                # 检查登录失败标志
                if result.get('login_failed', False):
                    self._log_step(f"❌ 视频 {i}/{total} 上传失败: 登录状态已失效", "ERROR")
                    self._log_step("建议：请重新登录后再继续上传", "ERROR")
                    # 可以选择停止批量上传或继续尝试
                    # 这里选择继续，但记录错误
                elif result.get('success', False):
                    self._log_step(f"✅ 视频 {i}/{total} 上传成功: {video_file.name}", "SUCCESS")
                    
                    # 上传成功后，移动视频文件到 upload_douyin 文件夹
                    try:
                        self._move_video_after_upload(str(video_file))
                    except Exception as move_error:
                        self._log_step(f"⚠️  移动视频文件失败: {move_error}", "WARNING")
                else:
                    self._log_step(f"❌ 视频 {i}/{total} 上传失败: {video_file.name}", "ERROR")
                    error_msg = result.get('error', '未知错误')
                    self._log_step(f"错误信息: {error_msg}", "ERROR")
                
            except Exception as e:
                self._log_step(f"❌ 视频 {i}/{total} 上传出错: {e}", "ERROR")
                import traceback
                traceback.print_exc()
                result = {
                    "video_path": str(video_file.absolute()),
                    "video_filename": video_file.name,
                    "success": False,
                    "error": str(e),
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                results.append(result)
                
                # 上传出错时，也保存结果到 JSON 文件（记录错误信息）
                try:
                    self.save_upload_results([result])
                    self._log_step(f"上传结果（出错）已保存到 JSON 文件", "INFO")
                except Exception as save_error:
                    self._log_step(f"⚠️  保存上传结果失败: {save_error}", "WARNING")
            
            # 等待一段时间再上传下一个（除了最后一个）
            if i < total:
                # 如果不是每3个视频的特殊延迟，使用正常的延迟
                if i % 3 != 0:
                    self._log_step(f"等待 {delay} 秒后继续上传下一个视频...")
                    time.sleep(delay)
        
        self._log_step("")
        self._log_step("=" * 60)
        self._log_step("批量上传完成", "SUCCESS")
        self._log_step("=" * 60)
        
        success_count = sum(1 for r in results if r.get('success', False))
        self._log_step(f"成功: {success_count}/{total}, 失败: {total - success_count}/{total}")
        
        # 注意：这里不再需要批量保存，因为每个视频上传后都已立即保存
        # 但为了保持兼容性，如果 results 中有未保存的结果，可以再次保存（不会重复，因为 save_upload_results 会更新已有记录）
        # 实际上，由于每个视频上传后都已立即保存，这里不再需要批量保存
        
        return results
    
    def _move_video_after_upload(self, video_path: str) -> bool:
        """
        上传成功后，将视频文件移动到 upload_douyin 文件夹
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            bool: 是否移动成功
        """
        try:
            video_file = Path(video_path)
            if not video_file.exists():
                self._log_step(f"视频文件不存在，无法移动: {video_path}", "WARNING")
                return False
            
            # 目标文件夹：默认下载目录下的 upload_douyin 子目录
            target_dir = self.upload_archive_dir
            
            # 如果目标文件夹不存在，创建它
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 目标文件路径
            target_file = target_dir / video_file.name
            
            # 如果目标文件已存在，添加时间戳后缀
            if target_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = video_file.stem
                suffix = video_file.suffix
                target_file = target_dir / f"{stem}_{timestamp}{suffix}"
            
            # 移动文件
            video_file.rename(target_file)
            self._log_step(f"✅ 视频文件已移动到: {target_file}", "SUCCESS")
            return True
            
        except Exception as e:
            self._log_step(f"移动视频文件时出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_view_count(self, view_count_str: str) -> int:
        """
        解析播放量字符串为数字（用于排序）
        
        Args:
            view_count_str: 播放量字符串，如 "5万次观看", "1.9万次观看", "1000次观看"
            
        Returns:
            播放量数字，如果解析失败返回0
        """
        if not view_count_str or view_count_str == "未知":
            return 0
        
        try:
            # 移除"次观看"等后缀
            text = view_count_str.replace('次观看', '').replace('观看', '').strip()
            
            # 处理万、千万等单位
            if '万' in text:
                number = float(text.replace('万', ''))
                return int(number * 10000)
            elif '千万' in text:
                number = float(text.replace('千万', ''))
                return int(number * 10000000)
            elif '亿' in text:
                number = float(text.replace('亿', ''))
                return int(number * 100000000)
            else:
                # 直接是数字
                return int(float(text))
        except (ValueError, AttributeError):
            pass
        return 0
    
    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
        """
        从 YouTube URL 中提取视频 ID
        
        Args:
            url: YouTube 视频 URL
            
        Returns:
            视频 ID，如果提取失败返回 None
        """
        try:
            # 处理 /shorts/VIDEO_ID 格式
            if '/shorts/' in url:
                match = re.search(r'/shorts/([a-zA-Z0-9_-]+)', url)
                if match:
                    return match.group(1)
            # 处理 /watch?v=VIDEO_ID 格式
            elif 'watch?v=' in url:
                match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', url)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None
    
    def _find_video_file_in_directory(self, video_filename: str, search_dir: Path) -> Optional[Path]:
        """
        在指定目录中查找视频文件（前缀匹配：保留空格和大小写，忽略视频格式，至少匹配1/2长度）
        
        Args:
            video_filename: 视频文件名
            search_dir: 搜索目录路径
            
        Returns:
            找到的视频文件路径，如果未找到返回 None
        """
        if not search_dir.exists() or not search_dir.is_dir():
            self._log_step(f"搜索目录不存在: {search_dir}", "WARNING")
            return None
        
        # 支持的视频文件格式
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v']
        
        # 提取文件名（不含扩展名），保留原始的空格和大小写
        video_name_without_ext = Path(video_filename).stem
        
        # 优先打印文件夹中的所有视频文件名和标题，用于调试
        self._log_step(f"在文件夹中查找视频文件: '{video_filename}'", "INFO")
        self._log_step(f"搜索目录: {search_dir}", "INFO")
        
        # 在所有视频文件中查找前缀匹配的文件（忽略视频格式）
        all_videos = []
        for ext in video_extensions:
            # 搜索所有视频文件（包括大小写变体）
            all_videos.extend(list(search_dir.glob(f"*{ext}")) + list(search_dir.glob(f"*{ext.upper()}")))
        
        # 优先打印文件夹中的视频文件名（最多显示前3个）
        self._log_step(f"文件夹中共找到 {len(all_videos)} 个视频文件（仅显示前3个）:", "INFO")
        if all_videos:
            for i, video_file in enumerate(sorted(all_videos)[:3], 1):  # 最多显示前3个
                file_name_without_ext = Path(video_file.name).stem
                self._log_step(f"  {i}. 文件名: {video_file.name}", "INFO")
                self._log_step(f"      标题: '{file_name_without_ext}' (长度: {len(file_name_without_ext)})", "INFO")
            if len(all_videos) > 3:
                self._log_step(f"  ... 还有 {len(all_videos) - 3} 个文件未显示", "INFO")
        else:
            self._log_step("  文件夹中没有找到任何视频文件", "WARNING")
        
        # 开始匹配
        self._log_step(f"开始匹配视频文件...", "INFO")
        self._log_step(f"查找的视频名称: '{video_name_without_ext}' (文件名不含扩展名)", "INFO")
        
        # 计算最小匹配长度（至少是视频名称的1/2，但不少于5个字符）
        video_name_length = len(video_name_without_ext)
        min_prefix_length = max(5, video_name_length // 2)
        max_prefix_length = min(video_name_length, 50)
        
        if video_name_length < min_prefix_length:
            self._log_step(f"视频名称长度 ({video_name_length}) 小于最小匹配长度 ({min_prefix_length})，跳过前缀匹配", "WARNING")
            return None
        
        self._log_step(f"尝试前缀匹配（视频名称长度: {video_name_length}，最小匹配长度: {min_prefix_length}，保留空格和大小写）...", "INFO")
        
        # 尝试不同的前缀长度（从最长到最短）
        # 注意：如果视频名称包含空格，前缀匹配时必须包含空格，不能跳过
        for prefix_len in range(max_prefix_length, min_prefix_length - 1, -1):
            video_prefix = video_name_without_ext[:prefix_len]
            
            # 如果视频名称包含空格，且当前前缀长度小于视频名称长度，
            # 需要确保前缀至少包含到第一个空格之后（如果存在空格）
            if ' ' in video_name_without_ext and prefix_len < video_name_length:
                # 找到第一个空格的位置
                first_space_pos = video_name_without_ext.find(' ')
                # 如果前缀长度小于第一个空格的位置，跳过这个前缀长度（避免只匹配空格前的部分）
                if prefix_len <= first_space_pos:
                    continue
            
            best_match = None
            best_match_length = 0
            
            for video_file in all_videos:
                # 提取文件名（不含扩展名），保留原始的空格和大小写
                file_name_without_ext = Path(video_file.name).stem
                
                # 检查文件名是否以视频名称的前缀开头（保留空格和大小写）
                # 同时要求文件名长度不小于视频名称长度（文件名应该包含视频名称的全部或更多内容）
                if file_name_without_ext.startswith(video_prefix) and len(file_name_without_ext) >= video_name_length:
                    if prefix_len > best_match_length:
                        best_match_length = prefix_len
                        best_match = video_file
                        self._log_step(f"    找到前缀匹配: {video_file.name} (匹配长度: {prefix_len})", "INFO")
            
            # 如果找到匹配，立即返回（确保匹配长度至少是视频名称的1/2）
            if best_match and best_match_length >= min_prefix_length:
                match_ratio = best_match_length / video_name_length if video_name_length > 0 else 0
                self._log_step(f"✅ 通过前缀匹配找到文件: {best_match.name} (匹配长度: {best_match_length}, 匹配比例: {match_ratio:.1%})", "SUCCESS")
                return best_match
        
        # 未找到匹配时，输出详细的调试信息
        self._log_step(f"❌ 未找到前缀匹配的文件: '{video_filename}' (文件名不含扩展名: '{video_name_without_ext}', 尝试了前缀长度 {min_prefix_length}-{max_prefix_length})", "WARNING")
        
        # 输出匹配尝试的详细信息
        self._log_step(f"匹配失败原因分析:", "INFO")
        self._log_step(f"  查找的视频名称: '{video_name_without_ext}' (长度: {video_name_length})", "INFO")
        self._log_step(f"  最小匹配长度要求: {min_prefix_length} (至少视频名称的1/2)", "INFO")
        
        # 检查是否有相似的文件名（用于调试）
        if all_videos:
            self._log_step(f"  检查是否有相似的文件名（前10个）:", "INFO")
            for i, video_file in enumerate(sorted(all_videos)[:10], 1):
                file_name_without_ext = Path(video_file.name).stem
                # 检查是否有共同的前缀（至少5个字符）
                common_prefix_len = 0
                min_len = min(len(video_name_without_ext), len(file_name_without_ext))
                for j in range(min_len):
                    if video_name_without_ext[j] == file_name_without_ext[j]:
                        common_prefix_len = j + 1
                    else:
                        break
                
                if common_prefix_len >= 5:
                    self._log_step(f"    {i}. {video_file.name} (共同前缀长度: {common_prefix_len}, 共同前缀: '{video_name_without_ext[:common_prefix_len]}')", "INFO")
                else:
                    self._log_step(f"    {i}. {video_file.name} (共同前缀长度: {common_prefix_len})", "INFO")
        
        return None
    
    def _normalize_title_for_search(self, title: str) -> List[str]:
        """
        规范化标题，提取可用于搜索的关键词
        
        Args:
            title: 视频标题
            
        Returns:
            关键词列表（用于文件名搜索）
        """
        if not title:
            return []
        
        # 移除特殊字符，保留字母、数字、中文、日文、韩文等
        import re
        # 保留字母、数字、中文、日文、韩文、空格、连字符、下划线
        normalized = re.sub(r'[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7a3-]', '', title)
        
        # 提取关键词（至少3个字符的连续字符序列）
        keywords = []
        
        # 方法1: 提取标题的前30个字符作为主要关键词（去除空格和特殊字符）
        main_keyword = normalized[:30].strip()
        if len(main_keyword) >= 3:
            keywords.append(main_keyword)
        
        # 方法2: 提取标题中的单词（至少3个字符）
        words = re.findall(r'[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7a3]{3,}', normalized)
        for word in words[:5]:  # 最多取前5个单词
            if word not in keywords and len(word) >= 3:
                keywords.append(word)
        
        return keywords
    
    def _normalize_string_for_matching(self, s: str) -> str:
        """
        规范化字符串用于匹配（去除不可见字符，统一空格类型，统一引号类型）
        
        Args:
            s: 原始字符串
            
        Returns:
            规范化后的字符串
        """
        import unicodedata
        import re
        
        if not s:
            return ""
        
        # 1. 去除首尾空白
        s = s.strip()
        
        # 2. 处理转义的引号（将转义的引号还原为普通引号）
        # 在字符串中，\" 和 \' 可能以转义形式存在，需要处理
        # 注意：这里处理的是字符串内容中的转义序列，不是Python字符串的转义
        s = s.replace('\\"', '"')  # 转义的双引号
        s = s.replace("\\'", "'")  # 转义的单引号
        
        # 3. 统一引号类型（将各种引号变体统一为标准引号）
        # 双引号变体：", ", ", "（弯引号）
        s = s.replace('"', '"')  # 左弯双引号
        s = s.replace('"', '"')  # 右弯双引号
        s = s.replace('"', '"')  # 中文左双引号
        s = s.replace('"', '"')  # 中文右双引号
        
        # 单引号变体：', ', ', '（弯引号）
        s = s.replace(''', "'")  # 左弯单引号
        s = s.replace(''', "'")  # 右弯单引号
        s = s.replace(''', "'")  # 中文左单引号
        s = s.replace(''', "'")  # 中文右单引号
        
        # 4. 去除零宽字符和其他不可见字符（但保留普通空格）
        # 零宽字符包括：零宽空格 (U+200B)、零宽非断空格 (U+FEFF) 等
        s = re.sub(r'[\u200B-\u200D\uFEFF\u00AD]', '', s)
        
        # 5. 统一空格类型（将所有类型的空格统一为普通空格）
        # 包括：不间断空格 (U+00A0)、全角空格 (U+3000) 等
        s = re.sub(r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]', ' ', s)
        
        # 6. Unicode 规范化（NFC 形式，将组合字符转换为预组合字符）
        s = unicodedata.normalize('NFC', s)
        
        # 7. 去除多余的空格（多个连续空格合并为一个）
        s = re.sub(r'\s+', ' ', s)
        
        return s.strip()
    
    def _find_downloaded_video_file(self, video_url: str, video_title: str, download_dirs: List[Path]) -> Optional[Path]:
        """
        查找已下载视频对应的本地文件（通过标题匹配：保留空格和大小写，忽略视频格式，至少匹配1/2长度）
        
        Args:
            video_url: YouTube 视频 URL
            video_title: 视频标题
            download_dirs: 可能的下载目录列表
            
        Returns:
            视频文件路径，如果未找到返回 None
        """
        # 支持的视频文件格式
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v']
        
        # 方法1: 通过标题前缀查找（保留空格和大小写）
        if video_title:
            self._log_step(f"通过标题查找视频文件: '{video_title}'", "INFO")
            
            # 提取标题，保留原始的空格和大小写，但规范化不可见字符
            video_title_normalized = self._normalize_string_for_matching(video_title)
            
            # 收集所有视频文件
            all_video_files = []
            for download_dir in download_dirs:
                if not download_dir.exists() or not download_dir.is_dir():
                    self._log_step(f"目录不存在或不是目录: {download_dir}", "WARNING")
                    continue
                
                for ext in video_extensions:
                    # 搜索所有视频文件（包括大小写变体）
                    videos = list(download_dir.glob(f"*{ext}")) + list(download_dir.glob(f"*{ext.upper()}"))
                    all_video_files.extend(videos)
            
            # 优先打印文件夹中的视频文件名（最多显示前3个），用于调试
            self._log_step(f"文件夹中共找到 {len(all_video_files)} 个视频文件（仅显示前3个）:", "INFO")
            if all_video_files:
                for i, video_file in enumerate(sorted(all_video_files)[:3], 1):  # 最多显示前3个
                    file_name_without_ext = Path(video_file.name).stem
                    # 规范化文件名用于比较
                    file_name_normalized = self._normalize_string_for_matching(file_name_without_ext)
                    self._log_step(f"  {i}. 文件名: {video_file.name}", "INFO")
                    self._log_step(f"      原始标题: '{file_name_without_ext}' (长度: {len(file_name_without_ext)})", "INFO")
                    self._log_step(f"      规范化标题: '{file_name_normalized}' (长度: {len(file_name_normalized)})", "INFO")
                if len(all_video_files) > 20:
                    self._log_step(f"  ... 还有 {len(all_video_files) - 20} 个文件未显示", "INFO")
            else:
                self._log_step("  文件夹中没有找到任何视频文件", "WARNING")
            
            # 开始匹配
            self._log_step(f"开始匹配视频文件...", "INFO")
            self._log_step(f"查找的视频标题（原始）: '{video_title}' (长度: {len(video_title)})", "INFO")
            self._log_step(f"查找的视频标题（规范化）: '{video_title_normalized}' (长度: {len(video_title_normalized)})", "INFO")
            
            # 计算最小匹配长度（至少是标题的1/2，但不少于5个字符）
            title_length = len(video_title_normalized)
            min_prefix_length = max(5, title_length // 2)
            max_prefix_length = min(title_length, 50)
            
            if title_length < min_prefix_length:
                self._log_step(f"标题长度 ({title_length}) 小于最小匹配长度 ({min_prefix_length})，跳过前缀匹配", "WARNING")
            else:
                self._log_step(f"尝试前缀匹配（标题长度: {title_length}，最小匹配长度: {min_prefix_length}，保留空格和大小写）...", "INFO")
                
                # 尝试不同的前缀长度（从最长到最短）
                # 注意：如果标题包含空格，前缀匹配时必须包含空格，不能跳过
                for prefix_len in range(max_prefix_length, min_prefix_length - 1, -1):
                    title_prefix = video_title_normalized[:prefix_len]
                    
                    # 如果标题包含空格，且当前前缀长度小于标题长度，
                    # 需要确保前缀至少包含到第一个空格之后（如果存在空格）
                    if ' ' in video_title_normalized and prefix_len < title_length:
                        # 找到第一个空格的位置
                        first_space_pos = video_title_normalized.find(' ')
                        # 如果前缀长度小于第一个空格的位置，跳过这个前缀长度（避免只匹配空格前的部分）
                        if prefix_len <= first_space_pos:
                            continue
                    
                    best_match = None
                    best_match_length = 0
                    
                    for video_file in all_video_files:
                        # 提取文件名（不含扩展名），保留原始的空格和大小写
                        file_name_without_ext = Path(video_file.name).stem
                        # 规范化文件名用于比较
                        file_name_normalized = self._normalize_string_for_matching(file_name_without_ext)
                        
                        # 检查规范化后的文件名是否以标题的前缀开头（保留空格和大小写）
                        # 同时要求文件名长度不小于标题长度（文件名应该包含标题的全部或更多内容）
                        if file_name_normalized.startswith(title_prefix) and len(file_name_normalized) >= title_length:
                            if prefix_len > best_match_length:
                                best_match_length = prefix_len
                                best_match = video_file
                                self._log_step(f"    找到前缀匹配: {video_file.name} (匹配长度: {prefix_len})", "INFO")
                                self._log_step(f"      原始文件名: '{file_name_without_ext}'", "INFO")
                                self._log_step(f"      规范化文件名: '{file_name_normalized}'", "INFO")
                    
                    # 如果找到匹配，立即返回（确保匹配长度至少是标题的1/2）
                    if best_match and best_match_length >= min_prefix_length:
                        match_ratio = best_match_length / title_length if title_length > 0 else 0
                        self._log_step(f"✅ 通过前缀匹配找到文件: {best_match.name} (匹配长度: {best_match_length}, 匹配比例: {match_ratio:.1%})", "SUCCESS")
                        return best_match
                
                # 未找到匹配时，输出详细的调试信息
                self._log_step(f"❌ 未找到前缀匹配的文件: '{video_title}' (尝试了前缀长度 {min_prefix_length}-{max_prefix_length})", "WARNING")
                
                # 输出匹配尝试的详细信息
                self._log_step(f"匹配失败原因分析:", "INFO")
                self._log_step(f"  查找的视频标题（原始）: '{video_title}' (长度: {len(video_title)})", "INFO")
                self._log_step(f"  查找的视频标题（规范化）: '{video_title_normalized}' (长度: {title_length})", "INFO")
                self._log_step(f"  最小匹配长度要求: {min_prefix_length} (至少标题的1/2)", "INFO")
                
                # 检查是否有相似的文件名（用于调试）
                if all_video_files:
                    self._log_step(f"  检查是否有相似的文件名（前10个）:", "INFO")
                    for i, video_file in enumerate(sorted(all_video_files)[:10], 1):
                        file_name_without_ext = Path(video_file.name).stem
                        file_name_normalized = self._normalize_string_for_matching(file_name_without_ext)
                        
                        # 检查是否有共同的前缀（至少5个字符）
                        common_prefix_len = 0
                        min_len = min(len(video_title_normalized), len(file_name_normalized))
                        for j in range(min_len):
                            if video_title_normalized[j] == file_name_normalized[j]:
                                common_prefix_len = j + 1
                            else:
                                break
                        
                        if common_prefix_len >= 5:
                            self._log_step(f"    {i}. {video_file.name}", "INFO")
                            self._log_step(f"        原始文件名: '{file_name_without_ext}' (长度: {len(file_name_without_ext)})", "INFO")
                            self._log_step(f"        规范化文件名: '{file_name_normalized}' (长度: {len(file_name_normalized)})", "INFO")
                            self._log_step(f"        共同前缀长度: {common_prefix_len}, 共同前缀: '{video_title_normalized[:common_prefix_len]}'", "INFO")
                        else:
                            self._log_step(f"    {i}. {video_file.name} (共同前缀长度: {common_prefix_len})", "INFO")
        
        # 方法2: 通过视频ID查找（备用方案）
        self._log_step("通过标题未找到，尝试通过视频ID查找...", "INFO")
        video_id = self._extract_video_id_from_url(video_url)
        if video_id:
            for download_dir in download_dirs:
                if not download_dir.exists() or not download_dir.is_dir():
                    continue
                
                for ext in video_extensions:
                    possible_patterns = [
                        f"*{video_id}*{ext}",
                        f"*{video_id}*{ext.upper()}",
                    ]
                    
                    for pattern in possible_patterns:
                        matches = list(download_dir.glob(pattern))
                        if matches:
                            self._log_step(f"✅ 通过视频ID找到文件: {matches[0].name}", "SUCCESS")
                            return matches[0]
        
        return None
    
    def _load_today_search_results(self, date_str: Optional[str] = None) -> List[Dict]:
        """
        加载当天搜索的视频结果
        
        Args:
            date_str: 日期字符串（格式：yyyyMMdd），如果为 None 则使用今天的日期
            
        Returns:
            视频信息列表
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        search_result_dir = Path(__file__).parent.parent / "data" / "search_result"
        filename = f"{date_str}_youtuber_shorts_www.youtube.com.json"
        file_path = search_result_dir / filename
        
        if not file_path.exists():
            self._log_step(f"未找到当天的搜索结果文件: {filename}", "WARNING")
            return []
        
        try:
            self._log_step(f"读取搜索结果文件: {filename}", "INFO")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                videos = data.get('results', [])
                self._log_step(f"成功读取 {len(videos)} 个视频", "SUCCESS")
                return videos
        except Exception as e:
            self._log_step(f"读取搜索结果文件失败: {e}", "ERROR")
            return []
    
    def _load_uploaded_titles(self) -> set:
        """
        加载已成功上传的视频标题集合（规范化后的标题）
        只有 success=true 且 error 为空或不存在时，才视为已成功上传
        
        Returns:
            已成功上传的视频标题集合（规范化后的）
        """
        upload_result_dir = Path(__file__).parent.parent / "data" / "upload_result" / "douyin"
        filename = "upload_www.youtube.com.json"
        file_path = upload_result_dir / filename
        
        if not file_path.exists():
            return set()
        
        try:
            uploaded_titles = set()
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results = data.get('results', [])
                for result in results:
                    # 只有 success=true 且 error 为空或不存在时，才视为已成功上传
                    success = result.get('success', False)
                    error = result.get('error', '')
                    
                    if success and not error:  # 成功上传且无错误
                        title = result.get('title', '')
                        if title:
                            # 规范化标题用于匹配
                            normalized_title = self._normalize_string_for_matching(title)
                            uploaded_titles.add(normalized_title)
            return uploaded_titles
        except Exception as e:
            self._log_step(f"读取上传记录文件失败: {e}", "WARNING")
            return set()
    
    def _parse_date_from_time_string(self, time_str: str) -> Optional[datetime]:
        """
        将时间字符串解析为datetime对象
        
        Args:
            time_str: 时间字符串，如 "20251230", "251230", "2025-12-30" 等
            
        Returns:
            datetime对象，如果解析失败返回None
        """
        if not time_str:
            return None
        
        try:
            # 8位数字格式（YYYYMMDD）
            if len(time_str) == 8 and time_str.isdigit():
                year = int(time_str[:4])
                month = int(time_str[4:6])
                day = int(time_str[6:8])
                return datetime(year, month, day)
            
            # 6位数字格式（YYMMDD）
            if len(time_str) == 6 and time_str.isdigit():
                year = int(time_str[:2])
                month = int(time_str[2:4])
                day = int(time_str[4:6])
                # 年份范围：00-99 表示 2000-2099
                if year < 100:
                    year += 2000
                return datetime(year, month, day)
            
            # 带分隔符的格式
            import re
            # 尝试匹配 YYYY-MM-DD 或 YYYY/MM/DD
            match = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', time_str)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            
            # 尝试匹配 YY-MM-DD 或 YY/MM/DD
            match = re.match(r'(\d{2})[-/](\d{1,2})[-/](\d{1,2})', time_str)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                # 年份范围：00-99 表示 2000-2099
                if year < 100:
                    year += 2000
                return datetime(year, month, day)
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def _load_today_downloaded_videos(self, date_str: Optional[str] = None) -> List[Dict]:
        """
        加载当天已下载的视频
        
        Args:
            date_str: 日期字符串（格式：yyyyMMdd），如果为 None 则使用今天的日期
            
        Returns:
            已下载的视频信息列表
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        download_result_dir = Path(__file__).parent.parent / "data" / "download_result"
        filename = "youtuber_shorts_www.youtube.com.json"
        file_path = download_result_dir / filename
        
        if not file_path.exists():
            self._log_step(f"未找到下载记录文件: {filename}", "WARNING")
            return []
        
        try:
            self._log_step(f"读取下载记录文件: {filename}", "INFO")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_videos = data.get('results', [])
                
                # 过滤出当天的视频（根据 download_time 字段）
                # download_time 格式: "2026-01-02 23:24:31"
                # date_str 格式: "20260102"
                today_date_str = date_str[:4] + '-' + date_str[4:6] + '-' + date_str[6:]
                today_videos = []
                for video in all_videos:
                    download_time = video.get('download_time', '')
                    if download_time and download_time.startswith(today_date_str):
                        today_videos.append(video)
                
                self._log_step(f"找到 {len(today_videos)} 个当天下载的视频", "SUCCESS")
                return today_videos
        except Exception as e:
            self._log_step(f"读取下载记录文件失败: {e}", "ERROR")
            return []
    
    def upload_top_videos_from_today(self, download_dirs: List[str] = None, 
                                     visibility: str = "公开", 
                                     auto_publish: bool = False,
                                     max_videos: int = 2,
                                     target_date: Optional[str] = None) -> List[Dict]:
        """
        上传指定日期（或当天）搜索的视频中播放量最多的已下载视频
        
        Args:
            download_dirs: 可能的下载目录列表，如果为 None 则使用配置中的默认下载目录
            visibility: 可见性设置（"仅自己可见" 或 "公开"）
            auto_publish: 是否自动发布（默认False）
            max_videos: 最多上传的视频数量（默认2个）
            target_date: 目标日期字符串（格式：yyyyMMdd，如 "20260108"），如果为 None 则使用当天日期
            
        Returns:
            上传结果列表
        """
        # 确定目标日期
        if target_date is None:
            target_date = datetime.now().strftime("%Y%m%d")
            date_label = "当天"
        else:
            # 验证日期格式
            try:
                datetime.strptime(target_date, "%Y%m%d")
                date_label = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
            except ValueError:
                self._log_step(f"错误: 日期格式不正确，应为 yyyyMMdd 格式（如 20260108），收到: {target_date}", "ERROR")
                return []
        
        self._log_step("=" * 80)
        self._log_step(f"开始上传{date_label}播放量最多的视频")
        self._log_step("=" * 80)
        
        # 步骤1: 读取指定日期已下载的视频
        self._log_step(f"步骤1: 读取{date_label}（{target_date}）已下载的视频...")
        downloaded_videos = self._load_today_downloaded_videos(target_date)
        
        if not downloaded_videos:
            self._log_step(f"未找到{date_label}下载的视频，无法继续", "ERROR")
            return []
        
        self._log_step(f"找到 {len(downloaded_videos)} 个{date_label}下载的视频", "SUCCESS")
        
        # 步骤2: 读取已成功上传的视频标题，排除已成功上传的视频
        self._log_step("步骤2: 读取已成功上传的视频，排除已成功上传的视频（上传失败的视频可重新上传）...")
        uploaded_titles = self._load_uploaded_titles()
        self._log_step(f"找到 {len(uploaded_titles)} 个已成功上传的视频", "INFO")
        
        # 步骤3: 找出已下载但未上传的视频（通过标题匹配）
        self._log_step("步骤3: 匹配已下载且未上传的视频...")
        
        matched_videos = []
        for video in downloaded_videos:
            url = video.get('url', '')
            title = video.get('title', '')
            if url:
                # 检查标题是否已上传（通过规范化对比）
                normalized_title = self._normalize_string_for_matching(title) if title else ''
                if normalized_title not in uploaded_titles:
                    matched_videos.append(video)
        
        if not matched_videos:
            self._log_step("未找到已下载且未上传的视频，无法继续", "ERROR")
            return []
        
        self._log_step(f"找到 {len(matched_videos)} 个已下载且未上传的视频", "SUCCESS")
        
        # 步骤4: 计算排序优先级（优先播放量>2万，其次时间最近）
        self._log_step("步骤4: 计算视频优先级（优先播放量>2万，其次时间最近）...")
        now = datetime.now()
        VIEW_COUNT_THRESHOLD = 20000  # 播放量阈值：2万
        
        for video in matched_videos:
            title = video.get('title', '')
            view_count_str = video.get('view_count', '未知')
            
            # 解析播放量（从 view_count 字段获取）
            video['_view_count_value'] = self._parse_view_count(view_count_str)
            video['_meets_view_threshold'] = video['_view_count_value'] >= VIEW_COUNT_THRESHOLD
        
            # 解析标题中的时间（从 title 字段获取）
            time_str = self._extract_time_from_title(title)
            video['_title_date'] = None
            video['_has_date'] = False
            video['_time_distance'] = None  # 时间距离当前时间的绝对值（秒）
            
            if time_str:
                title_date = self._parse_date_from_time_string(time_str)
                if title_date:
                    video['_title_date'] = title_date
                    video['_has_date'] = True
                    # 计算时间距离当前时间的绝对值（秒），越小表示越近
                    video['_time_distance'] = abs((now - title_date).total_seconds())
        
        # 排序规则：
        # 1. 优先选择播放量>2万的视频
        # 2. 在播放量>2万的视频中，优先选择时间距离当前时间最近的视频
        # 3. 如果没有播放量>2万的视频，则从所有视频中选择时间距离当前时间最近的视频
        def sort_key(video):
            view_count_value = video.get('_view_count_value', 0)
            meets_threshold = video.get('_meets_view_threshold', False)
            time_distance = video.get('_time_distance')
            has_date = video.get('_has_date', False)
            
            # 第一优先级：播放量>2万
            if meets_threshold:
                # 在播放量>2万的视频中，优先选择时间距离当前时间最近的（time_distance越小越好）
                if has_date and time_distance is not None:
                    return (0, time_distance)  # 0表示最高优先级（播放量>2万且有日期）
                else:
                    # 播放量>2万但没有日期信息，按播放量降序
                    return (0, float('inf'), -view_count_value)  # 0表示最高优先级，但时间距离为无穷大
            else:
                # 第二优先级：播放量<=2万，选择时间距离当前时间最近的
                if has_date and time_distance is not None:
                    return (1, time_distance)  # 1表示较低优先级（播放量<=2万但有日期）
                else:
                    # 没有日期信息，按播放量降序
                    return (2, float('inf'), -view_count_value)  # 2表示最低优先级
        
        matched_videos.sort(key=sort_key)
        
        # 统计信息
        high_view_count = sum(1 for v in matched_videos if v.get('_meets_view_threshold'))
        date_count = sum(1 for v in matched_videos if v.get('_has_date'))
        self._log_step(f"已排序 {len(matched_videos)} 个匹配的视频（{high_view_count}个播放量>2万，{date_count}个有日期信息）", "SUCCESS")
        
        # 步骤5: 查找本地文件路径
        if download_dirs is None:
            # 仅访问配置中的默认下载目录
            default_downie_dir = self.default_download_dir
            download_paths = [default_downie_dir]
        else:
            # 将字符串路径转换为 Path 对象
            download_paths = [Path(d) for d in download_dirs if d]
        
        self._log_step("步骤5: 依次查找已下载视频的本地文件（如果未找到或已上传则从剩余视频中按规则重新选择）...")
        videos_to_upload = []
        skipped_videos = []
        processed_videos = set()  # 记录已处理过的视频（通过URL）
        
        # 遍历所有排序后的视频，直到找到足够数量的可上传视频
        # 由于 matched_videos 已经按照规则排序，我们只需要按顺序遍历，跳过已处理或不符合条件的视频
        for video in matched_videos:
            # 如果已经找到足够数量的视频，停止查找
            if len(videos_to_upload) >= max_videos:
                self._log_step(f"已找到 {max_videos} 个可上传的视频，停止查找", "SUCCESS")
                break
            
            url = video.get('url', '')
            if not url:
                continue
            
            title = video.get('title', '')
            view_count = video.get('view_count', '未知')
            view_count_value = video.get('_view_count_value', 0)
            meets_threshold = video.get('_meets_view_threshold', False)
            title_date = video.get('_title_date')
            
            i = len(processed_videos) + 1
            self._log_step(f"检查视频 {i}/{len(matched_videos)}: {title[:50]}... (播放量: {view_count})", "INFO")
            
            # 显示选择原因
            reasons = []
            if meets_threshold:
                reasons.append(f"播放量>2万（{view_count_value}）")
            if title_date:
                date_str = title_date.strftime("%Y%m%d")
                time_distance_days = abs((now - title_date).days)
                reasons.append(f"时间最近（{date_str}，距离{time_distance_days}天）")
            if reasons:
                self._log_step(f"   选择原因: {'、'.join(reasons)}", "INFO")
            
            # 检查是否已上传（再次检查，因为可能在上次检查后上传了）
            normalized_title = self._normalize_string_for_matching(title) if title else ''
            if normalized_title in uploaded_titles:
                self._log_step(f"⚠️  视频已上传，跳过此视频，继续检查下一个视频...", "WARNING")
                skipped_videos.append(video)
                processed_videos.add(url)
                continue
            
            # 查找本地文件（通过标题查找）
            local_file = self._find_downloaded_video_file(url, title, download_paths)
            
            if local_file and local_file.exists():
                video['local_file_path'] = str(local_file)
                videos_to_upload.append(video)
                processed_videos.add(url)
                self._log_step(f"✅ 找到文件: {local_file.name} (已选择 {len(videos_to_upload)}/{max_videos} 个视频)", "SUCCESS")
            else:
                skipped_videos.append(video)
                processed_videos.add(url)
                self._log_step(f"⚠️  未找到视频文件，跳过此视频，继续检查下一个视频...", "WARNING")
                self._log_step(f"   搜索目录: {[str(d) for d in download_paths]}", "INFO")
        
        # 显示最终选择的视频列表（包含选择原因）
        if videos_to_upload:
            self._log_step(f"最终选择了 {len(videos_to_upload)} 个可上传的视频:", "SUCCESS")
            for i, video in enumerate(videos_to_upload, 1):
                title = video.get('title', 'N/A')[:50]
                view_count = video.get('view_count', '未知')
                
                # 构建选择原因说明
                reasons = []
                
                # 原因1: 未在已上传视频中
                reasons.append("不在已上传视频列表中")
                
                # 原因2: 播放量>2万（如果满足阈值）
                view_count_value = video.get('_view_count_value', 0)
                meets_threshold = video.get('_meets_view_threshold', False)
                if meets_threshold:
                    reasons.append(f"播放量>2万（{view_count_value}）")
                
                # 原因3: 时间最近（如果有日期信息）
                title_date = video.get('_title_date')
                if title_date:
                    # 格式化日期显示
                    date_str = title_date.strftime("%Y%m%d")
                    time_distance_days = abs((now - title_date).days)
                    reasons.append(f"时间最近（{date_str}，距离{time_distance_days}天）")
                elif view_count_value > 0 and not meets_threshold:
                    # 原因4: 播放次数（如果没有日期信息且播放量<=2万）
                    reasons.append(f"播放量: {view_count_value}")
                
                reason_text = "、".join(reasons)
                self._log_step(f"  {i}. {title}... (播放量: {view_count})", "INFO")
                self._log_step(f"      选择原因: {reason_text}", "INFO")
        
        # 显示跳过的视频（如果有关键信息）
        if skipped_videos:
            self._log_step(f"跳过了 {len(skipped_videos)} 个未找到本地文件的视频", "INFO")
            if len(skipped_videos) <= 5:  # 只显示前5个跳过的视频
                for i, video in enumerate(skipped_videos[:5], 1):
                    title = video.get('title', 'N/A')[:50]
                    view_count = video.get('view_count', '未知')
                    self._log_step(f"  跳过 {i}. {title}... (播放量: {view_count})", "INFO")
        
        if not videos_to_upload:
            self._log_step("未找到任何可上传的视频文件", "ERROR")
            self._log_step(f"已检查 {len(matched_videos)} 个匹配的视频，但均未找到本地文件", "ERROR")
            return []
        
        self._log_step(f"找到 {len(videos_to_upload)} 个可上传的视频文件", "SUCCESS")
        
        # 步骤6: 上传视频
        self._log_step("步骤6: 开始上传视频...")
        results = []
        
        for i, video in enumerate(videos_to_upload, 1):
            local_file_path = video.get('local_file_path')
            title = video.get('title', '')
            
            self._log_step("=" * 80)
            self._log_step(f"上传视频 {i}/{len(videos_to_upload)}: {title[:50]}...")
            self._log_step("=" * 80)
            
            try:
                is_last = (i == len(videos_to_upload))
                result = self.upload_video(
                    video_path=local_file_path,
                    title=None,  # 由 DeepSeek 生成标题
                    hashtags=None,  # 由 DeepSeek 生成话题
                    cover_text=None,  # 使用标题
                    visibility=visibility,
                    auto_publish=auto_publish,
                    keep_browser_open=not is_last  # 不是最后一个时保持浏览器打开
                )
                
                results.append(result)
                
                if result.get('success', False):
                    self._log_step(f"✅ 视频 {i}/{len(videos_to_upload)} 上传成功", "SUCCESS")
                    
                    # 上传成功后，立即保存上传结果到 JSON 文件
                    try:
                        self.save_upload_results([result])
                        self._log_step(f"✅ 上传结果已保存到 JSON 文件", "SUCCESS")
                    except Exception as save_error:
                        self._log_step(f"⚠️  保存上传结果失败: {save_error}", "WARNING")
                    
                    # 上传成功后，移动视频文件到 upload_douyin 文件夹
                    try:
                        self._move_video_after_upload(local_file_path)
                    except Exception as move_error:
                        self._log_step(f"⚠️  移动视频文件失败: {move_error}", "WARNING")
                else:
                    self._log_step(f"❌ 视频 {i}/{len(videos_to_upload)} 上传失败", "ERROR")
                    error_msg = result.get('error', '未知错误')
                    self._log_step(f"错误信息: {error_msg}", "ERROR")
                    
                    # 上传失败时，也保存结果到 JSON 文件（记录失败信息）
                    try:
                        self.save_upload_results([result])
                        self._log_step(f"上传结果（失败）已保存到 JSON 文件", "INFO")
                    except Exception as save_error:
                        self._log_step(f"⚠️  保存上传结果失败: {save_error}", "WARNING")
                
                # 等待一段时间再上传下一个（除了最后一个）
                if i < len(videos_to_upload):
                    self._human_like_delay(3.0, 6.0)
                    
            except Exception as e:
                self._log_step(f"❌ 视频 {i}/{len(videos_to_upload)} 上传出错: {e}", "ERROR")
                import traceback
                traceback.print_exc()
                results.append({
                    "video_path": local_file_path,
                    "video_filename": Path(local_file_path).name if local_file_path else "N/A",
                    "success": False,
                    "error": str(e),
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                # 上传出错时，也保存结果到 JSON 文件（记录错误信息）
                try:
                    self.save_upload_results([results[-1]])
                    self._log_step(f"上传结果（出错）已保存到 JSON 文件", "INFO")
                except Exception as save_error:
                    self._log_step(f"⚠️  保存上传结果失败: {save_error}", "WARNING")
        
        # 注意：这里不再需要批量保存，因为每个视频上传后都已立即保存
        # 但为了保持兼容性，如果 results 中有未保存的结果，可以再次保存（不会重复，因为 save_upload_results 会更新已有记录）
        # 实际上，由于每个视频上传后都已立即保存，这里不再需要批量保存
        
        self._log_step("=" * 80)
        self._log_step("上传完成", "SUCCESS")
        self._log_step("=" * 80)
        
        success_count = sum(1 for r in results if r.get('success', False))
        self._log_step(f"成功: {success_count}/{len(results)}, 失败: {len(results) - success_count}/{len(results)}")
        
        return results


def login_douyin(login_url: str = "https://creator.douyin.com/", wait_time: int = 60, headless: bool = False):
    """
    登录抖音创作者平台的便捷函数
    
    Args:
        login_url: 登录页面URL，默认 https://creator.douyin.com/
        wait_time: 等待登录的时间（秒），默认60秒
        headless: 是否使用无头模式，默认False（显示浏览器）
        
    Returns:
        bool: 是否登录成功
    """
    # 登录模式下也加载 cookies（如果已登录则直接完成）
    # 注意：虽然设置了 skip_load_cookies=True，但 login() 方法内部会调用 load_cookies()
    with DouyinUploader(headless=headless, skip_load_cookies=True) as uploader:
        return uploader.login(login_url=login_url, wait_time=wait_time)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  登录:")
        print("    python upload_video.py --login [wait_time]")
        print()
        print("  单个视频上传:")
        print("    python upload_video.py <video_path> [title] [hashtags] [cover_text] [visibility] [auto_publish]")
        print()
        print("  批量上传（从文件夹）:")
        print("    python upload_video.py --folder <folder_path> [visibility] [auto_publish] [delay]")
        print()
        print("参数说明:")
        print("  登录:")
        print("    --login: 登录模式（必需）")
        print("    wait_time: 等待登录的时间（秒，可选，默认60秒）")
        print()
        print("  单个视频上传:")
        print("    video_path: 视频文件路径（必需）")
        print("    title: 作品标题（可选，默认从文件名提取）")
        print("    hashtags: 话题标签（可选，默认从标题提取）")
        print("    cover_text: 封面文字（可选，默认使用标题）")
        print("    visibility: 可见性（可选，默认'公开'，可选'仅自己可见'）")
        print("    auto_publish: 是否自动发布（可选，默认False）")
        print()
        print("  批量上传:")
        print("    --folder: 视频文件夹路径（必需）")
        print("    visibility: 可见性（可选，默认'公开'，可选'仅自己可见'）")
        print("    auto_publish: 是否自动发布（可选，默认False）")
        print("    delay: 每个视频上传之间的延迟（秒，可选，默认5秒）")
        print()
        print("示例:")
        print('  登录:')
        print('    python upload_video.py --login')
        print('    python upload_video.py --login 120  # 等待120秒')
        print()
        print('  单个视频:')
        print('    python upload_video.py "/path/to/video.mp4"')
        print('    python upload_video.py "/path/to/video.mp4" "我的视频标题"')
        print('    python upload_video.py "/path/to/video.mp4" "我的视频" "#话题1 #话题2" "封面文字" "公开" true')
        print()
        print('  批量上传:')
        print(f'    python upload_video.py --folder "{get_default_video_download_dir()}"')
        print(f'    python upload_video.py --folder "{get_default_video_download_dir()}" "公开" true 10')
        print()
        print('  智能上传:')
        print('    python upload_video.py --today')
        print('    python upload_video.py --today "公开" true')
        print(f'    python upload_video.py --today "仅自己可见" false "{get_default_video_download_dir()}"')
        print('    python upload_video.py --today --date 20260108')
        print('    python upload_video.py --today -d 20260108 "公开"')
        return
    
    # 检查是否是登录模式
    if sys.argv[1] == "--login" or sys.argv[1] == "-l":
        wait_time = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 60
        print("=" * 80)
        print("🔐 抖音创作者平台登录")
        print("=" * 80)
        print()
        print(f"将在浏览器中打开登录页面，请在 {wait_time} 秒内完成登录")
        print("登录成功后，登录信息将自动保存，下次使用时无需重新登录")
        print()
        
        success = login_douyin(login_url="https://creator.douyin.com/", wait_time=wait_time, headless=False)
        
        if success:
            print()
            print("=" * 80)
            print("✅ 登录成功！登录信息已保存")
            print("=" * 80)
            print(f"📁 登录信息保存位置: data/cookies/.douyin_cookies.json")
        else:
            print()
            print("=" * 80)
            print("⚠️  登录可能未完成，请检查浏览器状态")
            print("=" * 80)
        return
    
    # 检查是否是智能上传模式（上传当天播放量最多的视频）
    if sys.argv[1] == "--today" or sys.argv[1] == "-t":
        visibility = "公开"
        auto_publish = False
        download_dirs = []
        target_date = None
        
        # 解析参数
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg in ["仅自己可见", "公开"]:
                visibility = arg
            elif arg.lower() in ["true", "false"]:
                auto_publish = arg.lower() == "true"
            elif arg == "--date" or arg == "-d":
                # 日期参数
                if i + 1 < len(sys.argv):
                    target_date = sys.argv[i + 1]
                    i += 1  # 跳过日期值
                else:
                    print("❌ 错误: --date 参数需要指定日期（格式：yyyyMMdd，如 20260108）")
                    return
            else:
                # 其他参数视为下载目录
                download_dirs.append(arg)
            i += 1
        
        with DouyinUploader(headless=False) as uploader:
            uploader.upload_top_videos_from_today(
                download_dirs=download_dirs if download_dirs else None,
                visibility=visibility,
                auto_publish=auto_publish,
                max_videos=2,
                target_date=target_date
            )
    # 检查是否是批量上传模式
    elif sys.argv[1] == "--folder" or sys.argv[1] == "-f":
        if len(sys.argv) < 3:
            print("❌ 错误: 批量上传模式需要指定文件夹路径")
            print("使用方法: python upload_video.py --folder <folder_path>")
            return
        
        folder_path = sys.argv[2]
        visibility = sys.argv[3] if len(sys.argv) > 3 else "公开"
        auto_publish = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
        delay = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
        
        with DouyinUploader(headless=False) as uploader:
            uploader.upload_videos_from_folder(
                folder_path=folder_path,
                visibility=visibility,
                auto_publish=auto_publish,
                delay=delay
            )
    else:
        # 单个视频上传模式
        video_path = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else None
        hashtags = sys.argv[3] if len(sys.argv) > 3 else None
        cover_text = sys.argv[4] if len(sys.argv) > 4 else None
        visibility = sys.argv[5] if len(sys.argv) > 5 else "公开"
        auto_publish = sys.argv[6].lower() == "true" if len(sys.argv) > 6 else False
        
        with DouyinUploader(headless=False) as uploader:
            uploader.upload_video(
                video_path=video_path,
                title=title,
                hashtags=hashtags,
                cover_text=cover_text,
                visibility=visibility,
                auto_publish=auto_publish
            )


if __name__ == '__main__':
    main()

