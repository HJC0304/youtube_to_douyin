"""
YouTube视频搜索功能
实现搜索、筛选和结果解析
使用 Playwright 进行浏览器自动化
"""
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# 导入视频过滤器和配置
try:
    # 尝试从项目根目录导入
    project_root = Path(__file__).parent.parent
    filter_module_path = project_root / "config" / "video_filter_config" / "youtube_filter.py"
    config_module_path = project_root / "config" / "store_config" / "youtube_config.py"
    
    if filter_module_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("youtube_filter", filter_module_path)
        youtube_filter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(youtube_filter)
        YouTubeVideoFilter = youtube_filter.YouTubeVideoFilter
    else:
        # 备用方案：使用 sys.path
        sys.path.insert(0, str(project_root))
        from config.video_filter_config.youtube_filter import YouTubeVideoFilter
    
    # 导入配置
    if config_module_path.exists():
        spec = importlib.util.spec_from_file_location("youtube_config", config_module_path)
        youtube_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(youtube_config)
        MAX_SAVE_COUNT = youtube_config.MAX_SAVE_COUNT
        PRIORITY_ORDER = getattr(youtube_config, 'PRIORITY_ORDER', [])
        PRIORITY_SORT_DIRECTION = getattr(youtube_config, 'PRIORITY_SORT_DIRECTION', {})
    else:
        # 备用方案：使用 sys.path
        sys.path.insert(0, str(project_root))
        from config.store_config.youtube_config import MAX_SAVE_COUNT, PRIORITY_ORDER, PRIORITY_SORT_DIRECTION
        
except ImportError as e:
    # 如果导入失败，使用默认值
    print(f"警告: 无法导入配置模块: {e}")
    MAX_SAVE_COUNT = None
    PRIORITY_ORDER = []
    PRIORITY_SORT_DIRECTION = {}
    class YouTubeVideoFilter:
        def __init__(self):
            self.enabled = False
        def filter_videos(self, videos):
            return videos

# 超时时间常量（30秒）
TIMEOUT = 30000
# YouTube 基础 URL
YOUTUBE_BASE_URL = "https://www.youtube.com"


class YouTubeSearcher:
    """YouTube搜索器"""
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        初始化YouTube搜索器
        
        Args:
            headless: 是否使用无头模式
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
        """
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.cookies_path = Path(__file__).parent.parent / "data" / "cookies" / ".youtube_cookies.json"
        self.result_dir = Path(__file__).parent.parent / "data" / "search_result"
        self.headless = headless
        self.browser_type = browser_type
        self.step_counter = 0
        self._init_browser()
    
    def _get_result_path(self, search_query: str = "") -> Path:
        """
        获取结果文件路径，格式：yyyyMMdd + 视频网站域名
        
        Args:
            search_query: 搜索关键词（不再用于文件名，保留参数以兼容）
            
        Returns:
            结果文件路径
        """
        # 生成日期字符串 yyyyMMdd
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 从 YouTube 基础 URL 提取域名
        domain = urlparse(YOUTUBE_BASE_URL).netloc  # 例如: www.youtube.com
        
        # 文件命名格式：yyyyMMdd + 视频网站域名
        filename = f"{date_str}_{domain}.json"
        
        return self.result_dir / filename
    
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
            
            # 启动浏览器
            self._log_step(f"启动浏览器 (headless={self.headless})...")
            self.browser = browser_launcher.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )
            self._log_step("浏览器启动成功", "SUCCESS")
            
            # 创建上下文和页面
            self._log_step("创建浏览器上下文和页面...")
            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self.page = context.new_page()
            
            # 添加脚本以隐藏自动化特征
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            self._log_step("页面创建成功，已隐藏自动化特征", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"初始化浏览器失败: {e}", "ERROR")
            self._log_step("请确保已安装 Playwright 浏览器: playwright install chromium", "ERROR")
            raise
    
    def load_cookies(self):
        """
        从本地文件加载对应网站的cookie信息
        
        注意：Playwright 需要先访问域名才能设置 cookies，
        所以此方法需要在访问首页之后调用
        """
        if self.cookies_path.exists():
            try:
                self._log_step("检查是否存在保存的登录信息...")
                with open(self.cookies_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    if cookies:
                        self._log_step(f"找到 {len(cookies)} 个 cookies，开始加载...")
                        # 确保 cookies 格式正确（Playwright 需要 domain 字段）
                        valid_cookies = []
                        for cookie in cookies:
                            if isinstance(cookie, dict):
                                # 确保有必要的字段
                                if 'domain' not in cookie:
                                    cookie['domain'] = '.youtube.com'
                                if 'path' not in cookie:
                                    cookie['path'] = '/'
                                valid_cookies.append(cookie)
                        # 设置 cookies
                        if valid_cookies:
                            self._log_step(f"设置 {len(valid_cookies)} 个 cookies...")
                            self.page.context.add_cookies(valid_cookies)
                            self._log_step("登录信息加载成功", "SUCCESS")
                            return True
                    else:
                        self._log_step("未找到有效的 cookies", "WARNING")
            except Exception as e:
                self._log_step(f"加载cookies失败: {e}", "WARNING")
        else:
            self._log_step("未找到保存的登录信息文件，跳过加载", "WARNING")
        return False
    
    def save_cookies(self):
        """保存当前登录信息（cookies）"""
        try:
            self._log_step("保存当前登录信息...")
            cookies = self.page.context.cookies()
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            self._log_step(f"已保存 {len(cookies)} 个 cookies 到: {self.cookies_path}", "SUCCESS")
        except Exception as e:
            self._log_step(f"保存cookies失败: {e}", "WARNING")
    
    def search(self, search_query: str, click_recent_upload: bool = True):
        """
        执行YouTube搜索
        
        执行顺序：
        1. 优先从本地文件获取cookie信息
        2. 访问youtube首页
        3. 输入搜索词
        4. 点击搜索按钮
        5. 点击"最近上传"按钮
        6. 寻找符合要求的视频
        7. 存储视频信息（在search_and_save中完成）
        
        Args:
            search_query: 搜索关键词
            click_recent_upload: 是否点击"最近上传"按钮
        """
        try:
            self._log_step(f"开始执行搜索，关键词: '{search_query}'")
            
            # 步骤1: 优先从本地文件中获取对应网站的cookie信息
            self._log_step("步骤1: 从本地文件获取cookie信息...")
            # 注意：Playwright 需要先访问域名才能设置 cookies，所以先访问首页
            self._log_step("访问 YouTube 首页（用于设置 cookies）...")
            self.page.goto("https://www.youtube.com/", wait_until="domcontentloaded", timeout=TIMEOUT)
            time.sleep(1)
            
            # 加载已保存的cookies
            cookies_loaded = self.load_cookies()
            if cookies_loaded:
                # 刷新页面使cookies生效
                self._log_step("刷新页面使 cookies 生效...")
                self.page.reload(wait_until="domcontentloaded", timeout=TIMEOUT)
                time.sleep(2)
            
            # 步骤2: 访问youtube首页（如果cookies已加载，此时已在首页）
            if not cookies_loaded:
                self._log_step("步骤2: 访问 YouTube 首页...")
                self.page.goto("https://www.youtube.com/", wait_until="domcontentloaded", timeout=TIMEOUT)
                time.sleep(2)
                self._log_step("页面加载完成", "SUCCESS")
            else:
                self._log_step("步骤2: 已在 YouTube 首页（cookies已生效）", "SUCCESS")
            
            # 步骤3: 输入搜索词
            self._log_step("步骤3: 查找搜索框并输入搜索词...")
            try:
                # 等待搜索框出现
                search_input = self.page.wait_for_selector('input[name="search_query"]', timeout=TIMEOUT)
                self._log_step("搜索框已找到", "SUCCESS")
                self._log_step(f"输入搜索词: '{search_query}'...")
                search_input.fill(search_query)
                self._log_step("搜索词输入完成", "SUCCESS")
            except PlaywrightTimeoutError:
                self._log_step("未找到搜索框，尝试其他定位方式...", "WARNING")
                # 备用方案：通过placeholder定位
                search_input = self.page.wait_for_selector('input[placeholder="搜索"]', timeout=TIMEOUT)
                search_input.fill(search_query)
                self._log_step("使用备用方案输入搜索词成功", "SUCCESS")
            
            time.sleep(1)
            
            # 步骤4: 点击搜索按钮
            self._log_step("步骤4: 点击搜索按钮...")
            try:
                search_button = self.page.wait_for_selector(
                    'button[aria-label="Search"][title="搜索"]',
                    timeout=TIMEOUT,
                    state="visible"
                )
                self._log_step("搜索按钮已找到，准备点击...")
                search_button.click()
                self._log_step("搜索按钮点击成功", "SUCCESS")
            except PlaywrightTimeoutError:
                # 备用方案：通过aria-label定位
                self._log_step("使用备用方案查找搜索按钮...", "WARNING")
                try:
                    search_button = self.page.wait_for_selector('button[aria-label="Search"]', timeout=TIMEOUT)
                    search_button.click()
                    self._log_step("使用备用方案点击搜索按钮成功", "SUCCESS")
                except PlaywrightTimeoutError:
                    # 如果按钮不可见，尝试按回车键
                    self._log_step("搜索按钮不可见，使用回车键触发搜索...", "WARNING")
                    search_input.press("Enter")
                    self._log_step("已通过回车键触发搜索", "SUCCESS")
            
            # 等待搜索结果加载
            self._log_step("等待搜索结果加载...")
            self.page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            time.sleep(2)
            self._log_step("搜索结果加载完成", "SUCCESS")
            
            # 步骤5: 点击"最近上传"按钮
            if click_recent_upload:
                self._log_step("步骤5: 点击'最近上传'按钮...")
                try:
                    # 查找包含"最近上传"文本的按钮
                    buttons = self.page.query_selector_all("button")
                    self._log_step(f"找到 {len(buttons)} 个按钮，正在查找'最近上传'按钮...")
                    found = False
                    for button in buttons:
                        try:
                            # 检查按钮内是否有包含"最近上传"的 div
                            div = button.query_selector("div")
                            if div:
                                text = div.inner_text()
                                if "最近上传" in text:
                                    self._log_step("找到'最近上传'按钮，准备点击...")
                                    button.click()
                                    self._log_step("'最近上传'按钮点击成功", "SUCCESS")
                                    time.sleep(2)  # 等待筛选结果加载
                                    found = True
                                    break
                        except Exception:
                            continue
                    if not found:
                        self._log_step("未找到'最近上传'按钮", "WARNING")
                except Exception as e:
                    self._log_step(f"点击'最近上传'按钮失败: {e}", "WARNING")
            else:
                self._log_step("步骤5: 跳过'最近上传'筛选（click_recent_upload=False）")
            
            # 滚动页面以加载更多结果（在点击"最近上传"之后）
            self._scroll_to_load_results()
            
            # 步骤6: 寻找符合要求的视频（在parse_search_results中完成）
            # 步骤7: 存储视频信息（在save_results中完成）
            
            # 保存cookies（更新登录信息）
            self.save_cookies()
            
            self._log_step("搜索流程执行完成", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"搜索过程出错: {e}", "ERROR")
            raise
    
    def _scroll_to_load_results(self, scroll_times: int = 3):
        """
        滚动页面以加载更多搜索结果
        
        Args:
            scroll_times: 滚动次数
        """
        try:
            self._log_step(f"开始滚动页面以加载更多结果（滚动 {scroll_times} 次）...")
            for i in range(scroll_times):
                self._log_step(f"第 {i+1}/{scroll_times} 次滚动...")
                # 滚动到页面底部
                self.page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                time.sleep(2)  # 等待新内容加载
            self._log_step("页面滚动完成", "SUCCESS")
        except Exception as e:
            self._log_step(f"滚动页面时出错: {e}", "WARNING")
    
    def _normalize_url(self, url: str) -> str:
        """
        规范化 URL，将相对路径转换为完整 URL
        
        Args:
            url: 相对或绝对 URL
            
        Returns:
            完整的 URL
        """
        if not url:
            return ""
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return urljoin(YOUTUBE_BASE_URL, url)
    
    def _extract_duration(self, video_element) -> Optional[str]:
        """
        提取视频时长
        
        Args:
            video_element: 视频元素
            
        Returns:
            时长字符串，如 "10:30" 或 None
        """
        try:
            import re
            
            # 方法1: 查找时长覆盖层（最常见的定位方式）
            duration_element = video_element.query_selector(
                'span.style-scope.ytd-thumbnail-overlay-time-status-renderer'
            )
            if duration_element:
                duration_text = duration_element.inner_text().strip()
                if duration_text and ':' in duration_text:
                    return duration_text
            
            # 方法2: 查找 ytd-thumbnail-overlay-time-status-renderer 内的所有 span
            overlay = video_element.query_selector('ytd-thumbnail-overlay-time-status-renderer')
            if overlay:
                spans = overlay.query_selector_all('span')
                for span in spans:
                    text = span.inner_text().strip()
                    if text and ':' in text:
                        # 验证格式是否为时长（如 1:23 或 10:30:45）
                        if re.match(r'^\d+:\d+(:\d+)?$', text):
                            return text
            
            # 方法3: 查找包含时长的 aria-label
            all_elements = video_element.query_selector_all('[aria-label]')
            for elem in all_elements:
                aria_label = elem.get_attribute('aria-label') or ""
                if ':' in aria_label:
                    # 从 aria-label 中提取时长，如 "时长 10:30" 或 "10:30"
                    match = re.search(r'(\d+:\d+(?::\d+)?)', aria_label)
                    if match:
                        duration = match.group(1)
                        # 验证是否为有效的时长格式（如 1:23 或 10:30:45）
                        if re.match(r'^\d+:\d+(:\d+)?$', duration):
                            return duration
            
            # 方法4: 查找所有包含 ":" 的文本元素
            text_elements = video_element.query_selector_all('span, div')
            for elem in text_elements:
                text = elem.inner_text().strip()
                if text and ':' in text and len(text) < 20:  # 时长通常很短
                    # 验证是否为时长格式（如 1:23 或 10:30:45）
                    if re.match(r'^\d+:\d+(:\d+)?$', text):
                        return text
        except Exception:
            pass
        return None
    
    def _extract_resolution(self, video_element) -> Optional[str]:
        """
        提取视频分辨率信息
        
        Args:
            video_element: 视频元素
            
        Returns:
            分辨率字符串，如 "1080p" 或 None
        """
        try:
            import re
            
            # 注意：YouTube 搜索结果页面通常不直接显示分辨率
            # 分辨率信息通常在视频详情页或播放器中
            # 这里尝试从可能的元素中提取
            
            # 方法1: 查找包含分辨率信息的元素
            resolution_elements = video_element.query_selector_all(
                '[class*="quality"], [class*="resolution"], [class*="hd"], [class*="4k"], [class*="8k"]'
            )
            for elem in resolution_elements:
                text = elem.inner_text().strip()
                if text:
                    # 查找分辨率模式
                    match = re.search(r'(\d+p|HD|4K|8K|720p|1080p|1440p|2160p)', text, re.IGNORECASE)
                    if match:
                        return match.group(1).upper()
            
            # 方法2: 通过 aria-label 查找
            all_elements = video_element.query_selector_all('[aria-label]')
            for elem in all_elements:
                aria_label = elem.get_attribute('aria-label') or ""
                match = re.search(r'(\d+p|HD|4K|8K|720p|1080p|1440p|2160p)', aria_label, re.IGNORECASE)
                if match:
                    return match.group(1).upper()
            
            # 方法3: 从缩略图或元数据中查找
            # 注意：搜索结果页面可能不包含分辨率信息
            # 如果需要准确的分辨率，需要访问视频详情页
        except Exception:
            pass
        return None
    
    def parse_search_results(self, search_query: str = "") -> List[Dict]:
        """
        解析搜索结果
        
        Args:
            search_query: 搜索关键词
            
        Returns:
            包含视频信息的字典列表
        """
        results = []
        
        try:
            self._log_step("开始解析搜索结果...")
            # 查找所有搜索结果
            # 使用更灵活的选择器：ytd-video-renderer标签，且包含style-scope类
            self._log_step("查找视频元素（使用选择器: ytd-item-section-renderer ytd-video-renderer.style-scope）...")
            video_elements = self.page.query_selector_all(
                'ytd-item-section-renderer ytd-video-renderer.style-scope'
            )
            # 如果上面的选择器找不到，尝试更通用的选择器
            if not video_elements:
                self._log_step("使用备用选择器查找视频元素...", "WARNING")
                video_elements = self.page.query_selector_all('ytd-video-renderer')
            
            total_found = len(video_elements)
            # 限制最多解析100条视频
            max_parse_count = 100
            if total_found > max_parse_count:
                self._log_step(f"找到 {total_found} 个搜索结果，限制解析前 {max_parse_count} 个", "WARNING")
                video_elements = video_elements[:max_parse_count]
            else:
                self._log_step(f"找到 {total_found} 个搜索结果", "SUCCESS")
            
            self._log_step("开始解析每个视频的详细信息...")
            for idx, video_element in enumerate(video_elements, 1):
                try:
                    video_info = {}
                    
                    # 保存搜索关键字
                    video_info['search_query'] = search_query
                    
                    # 保存搜索时间信息（和title同级）
                    video_info['search_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 检查是否为竖屏视频（SHORTS）
                    # 检查内部元素是否包含 overlay-style="SHORTS" 属性
                    is_shorts = False
                    try:
                        # 方法1: 通过CSS选择器查找
                        shorts_elements = video_element.query_selector_all('[overlay-style="SHORTS"]')
                        if shorts_elements:
                            is_shorts = True
                        else:
                            # 方法2: 检查所有元素的属性
                            all_elements = video_element.query_selector_all('*')
                            for elem in all_elements:
                                overlay_style = elem.get_attribute('overlay-style')
                                if overlay_style == 'SHORTS':
                                    is_shorts = True
                                    break
                    except Exception:
                        pass
                    video_info['is_shorts'] = is_shorts
                    
                    # 判断横屏/竖屏
                    # SHORTS 通常是竖屏，普通视频通常是横屏
                    if is_shorts:
                        video_info['orientation'] = "竖屏"
                    else:
                        video_info['orientation'] = "横屏"
                    
                    # 获取视频标题和 URL
                    try:
                        title_element = video_element.query_selector('a#video-title')
                        if title_element:
                            video_info['title'] = title_element.get_attribute('title') or title_element.inner_text()
                            relative_url = title_element.get_attribute('href') or ""
                            # 转换为完整 URL（包括域名）
                            video_info['url'] = self._normalize_url(relative_url)
                            # 保存原始相对路径（如果需要）
                            video_info['url_relative'] = relative_url
                        else:
                            video_info['title'] = "未知标题"
                            video_info['url'] = ""
                            video_info['url_relative'] = ""
                    except Exception:
                        video_info['title'] = "未知标题"
                        video_info['url'] = ""
                        video_info['url_relative'] = ""
                    
                    # 提取视频时长
                    duration = self._extract_duration(video_element)
                    video_info['duration'] = duration if duration else "未知"
                    
                    # 提取分辨率信息
                    resolution = self._extract_resolution(video_element)
                    video_info['resolution'] = resolution if resolution else "未知"
                    
                    # 获取观看次数和发布时间
                    try:
                        metadata_element = video_element.query_selector('div#metadata-line')
                        if metadata_element:
                            spans = metadata_element.query_selector_all('span')
                            
                            if len(spans) >= 1:
                                video_info['view_count'] = spans[0].inner_text()
                            else:
                                video_info['view_count'] = "未知"
                            
                            if len(spans) >= 2:
                                video_info['publish_time'] = spans[1].inner_text()
                            else:
                                video_info['publish_time'] = "未知"
                        else:
                            video_info['view_count'] = "未知"
                            video_info['publish_time'] = "未知"
                    except Exception:
                        video_info['view_count'] = "未知"
                        video_info['publish_time'] = "未知"
                    
                    results.append(video_info)
                    
                    # 每解析10个视频打印一次进度
                    if idx % 10 == 0:
                        self._log_step(f"已解析 {idx}/{len(video_elements)} 个视频...")
                    
                except Exception as e:
                    self._log_step(f"解析第 {idx} 个视频信息时出错: {e}", "WARNING")
                    continue
            
            self._log_step(f"成功解析 {len(results)} 个视频信息", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"解析搜索结果时出错: {e}", "ERROR")
        
        return results
    
    def _get_resolution_priority(self, resolution: str) -> int:
        """
        获取分辨率的优先级数值（数值越大优先级越高）
        
        Args:
            resolution: 分辨率字符串，如 "4K", "1080p", "720p"
            
        Returns:
            优先级数值
        """
        if not resolution or resolution == "未知":
            return 0
        
        resolution_upper = resolution.upper()
        priority_map = {
            '8K': 8,
            '2160P': 7,
            '4K': 7,
            '1440P': 6,
            '1080P': 5,
            '1080': 5,
            'HD': 4,
            '720P': 3,
            '720': 3,
            '480P': 2,
            '480': 2,
            '360P': 1,
            '360': 1
        }
        
        for key, value in priority_map.items():
            if key in resolution_upper:
                return value
        
        return 0
    
    def _get_view_count_value(self, view_count_str: str) -> int:
        """
        获取播放量的数值（用于排序）
        
        Args:
            view_count_str: 播放量字符串，如 "5万次观看"
            
        Returns:
            播放量数值
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
    
    def _get_publish_time_value(self, publish_time_str: str) -> float:
        """
        获取发布时间的数值（天数，用于排序）
        
        Args:
            publish_time_str: 发布时间字符串，如 "1天前"
            
        Returns:
            天数（数值越小表示越新）
        """
        if not publish_time_str or publish_time_str == "未知":
            return float('inf')  # 未知时间排在最后
        
        try:
            import re
            # 处理小时
            if '小时' in publish_time_str or 'hour' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    hours = int(match.group(1))
                    return hours / 24  # 转换为天数
            
            # 处理天
            if '天' in publish_time_str or 'day' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    return int(match.group(1))
            
            # 处理周
            if '周' in publish_time_str or 'week' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    weeks = int(match.group(1))
                    return weeks * 7
            
            # 处理月
            if '月' in publish_time_str or 'month' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    months = int(match.group(1))
                    return months * 30  # 近似值
            
            # 处理年
            if '年' in publish_time_str or 'year' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    years = int(match.group(1))
                    return years * 365
        except (ValueError, AttributeError):
            pass
        return float('inf')  # 无法解析的时间排在最后
    
    def _sort_videos_by_priority(self, videos: List[Dict], priority_order: List[str], 
                                 sort_direction: Dict[str, str]) -> List[Dict]:
        """
        根据优先级对视频进行排序
        
        Args:
            videos: 视频列表
            priority_order: 优先级顺序列表，如 ['resolution', 'view_count', 'publish_time']
            sort_direction: 排序方向字典，如 {'resolution': 'desc', 'view_count': 'desc'}
            
        Returns:
            排序后的视频列表
        """
        def get_sort_key(video: Dict) -> tuple:
            """生成排序键"""
            sort_keys = []
            for priority in priority_order:
                if priority == 'resolution':
                    # 分辨率：数值越大优先级越高
                    priority_value = self._get_resolution_priority(video.get('resolution', ''))
                    # 如果是降序，使用负值
                    if sort_direction.get('resolution', 'desc') == 'desc':
                        sort_keys.append(-priority_value)
                    else:
                        sort_keys.append(priority_value)
                elif priority == 'view_count':
                    # 播放次数：数值越大优先级越高
                    view_count_value = self._get_view_count_value(video.get('view_count', ''))
                    # 如果是降序，使用负值
                    if sort_direction.get('view_count', 'desc') == 'desc':
                        sort_keys.append(-view_count_value)
                    else:
                        sort_keys.append(view_count_value)
                elif priority == 'publish_time':
                    # 发布时间：天数越少优先级越高（越新）
                    publish_time_value = self._get_publish_time_value(video.get('publish_time', ''))
                    # 如果是升序（新的在前），直接使用
                    if sort_direction.get('publish_time', 'asc') == 'asc':
                        sort_keys.append(publish_time_value)
                    else:
                        sort_keys.append(-publish_time_value)
                else:
                    # 未知的优先级，使用0
                    sort_keys.append(0)
            return tuple(sort_keys)
        
        # 对视频列表进行排序
        sorted_videos = sorted(videos, key=get_sort_key)
        return sorted_videos
    
    def save_results(self, results: List[Dict], search_query: str = ""):
        """
        保存搜索结果到文件
        
        Args:
            results: 搜索结果列表
            search_query: 搜索关键词
        """
        try:
            self._log_step("开始保存搜索结果...")
            
            # 获取带日期的文件路径
            result_path = self._get_result_path(search_query)
            
            # 确保目录存在
            result_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有结果（如果存在）
            existing_results = []
            if result_path.exists():
                self._log_step("读取已存在的搜索结果文件...")
                try:
                    with open(result_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, list):
                            existing_results = existing_data
                        elif isinstance(existing_data, dict):
                            existing_results = existing_data.get('results', [])
                    self._log_step(f"找到 {len(existing_results)} 个已存在的搜索结果")
                except Exception:
                    self._log_step("读取已存在文件失败，将创建新文件", "WARNING")
            
            # 合并结果，如果标题相同则覆盖
            # 创建一个以标题为键的字典，用于去重和覆盖
            results_dict = {}
            
            # 先添加现有结果
            for existing_result in existing_results:
                title = existing_result.get('title', '')
                if title:
                    results_dict[title] = existing_result
            
            # 添加新结果，如果标题相同则覆盖
            new_count = 0
            update_count = 0
            for new_result in results:
                title = new_result.get('title', '')
                if title:
                    if title in results_dict:
                        self._log_step(f"发现重复标题，覆盖: {title[:50]}...", "WARNING")
                        update_count += 1
                    else:
                        new_count += 1
                    results_dict[title] = new_result
            
            # 转换为列表
            all_results = list(results_dict.values())
            
            # 保存到文件
            self._log_step(f"保存结果到文件（新增: {new_count}, 更新: {update_count}, 总计: {len(all_results)}）...")
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'total': len(all_results),
                    'results': all_results,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, f, indent=2, ensure_ascii=False)
            
            self._log_step(f"已保存 {len(results)} 个搜索结果（新增: {new_count}, 更新: {update_count}, 总计: {len(all_results)} 个）到: {result_path}", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"保存搜索结果失败: {e}", "ERROR")
    
    def _wait_with_countdown(self, seconds: int = 30):
        """
        等待指定秒数，并打印倒计时信息
        
        Args:
            seconds: 等待的秒数
        """
        self._log_step(f"搜索完成，等待 {seconds} 秒后继续...")
        print()
        for remaining in range(seconds, 0, -1):
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\r[{timestamp}] ⏳ 倒计时: {remaining:2d} 秒", end='', flush=True)
            time.sleep(1)
        print()  # 换行
        self._log_step("等待完成", "SUCCESS")
    
    def search_and_save(self, search_query: str, click_recent_upload: bool = True):
        """
        执行搜索并保存结果
        
        Args:
            search_query: 搜索关键词
            click_recent_upload: 是否点击"最近上传"按钮
        """
        self._log_step("=" * 60)
        self._log_step("开始执行完整的搜索和保存流程")
        self._log_step("=" * 60)
        
        self.search(search_query, click_recent_upload)
        results = self.parse_search_results(search_query)
        
        # 应用视频过滤 - 只有满足过滤条件的视频才会被保存
        original_count = len(results)
        self._log_step(f"解析完成，共获取 {original_count} 个视频")
        
        try:
            self._log_step("应用视频过滤条件（只有满足条件的视频才会被保存）...")
            filter_obj = YouTubeVideoFilter()
            
            if filter_obj.enabled:
                self._log_step("过滤功能已启用，开始过滤视频...")
                filtered_results = filter_obj.filter_videos(results)
                filtered_count = len(filtered_results)
                
                self._log_step(f"过滤完成：原始 {original_count} 个 → 过滤后 {filtered_count} 个", "SUCCESS")
                if original_count > filtered_count:
                    removed_count = original_count - filtered_count
                    self._log_step(f"已过滤掉 {removed_count} 个不符合条件的视频，这些视频不会被保存", "WARNING")
                elif original_count == filtered_count:
                    self._log_step("所有视频都通过了过滤条件", "SUCCESS")
                
                # 只使用过滤后的结果（只有这些视频会被保存）
                results = filtered_results
            else:
                self._log_step("过滤功能未启用（FILTER_ENABLED=False），所有视频都会被保存", "WARNING")
                # 即使过滤未启用，仍然应用过滤逻辑（filter_videos 会直接返回原列表）
                # 这样可以确保代码逻辑的一致性
                results = filter_obj.filter_videos(results)
            
            # 应用优先级排序（从配置中读取）
            try:
                priority_order = PRIORITY_ORDER if 'PRIORITY_ORDER' in globals() else []
                priority_sort_direction = PRIORITY_SORT_DIRECTION if 'PRIORITY_SORT_DIRECTION' in globals() else {}
                
                if priority_order and isinstance(priority_order, list) and len(priority_order) > 0:
                    self._log_step(f"应用优先级排序：{', '.join(priority_order)}...")
                    results = self._sort_videos_by_priority(results, priority_order, priority_sort_direction)
                    self._log_step("优先级排序完成", "SUCCESS")
                else:
                    self._log_step("未设置优先级排序（PRIORITY_ORDER=[]），按搜索顺序保存", "INFO")
            except NameError:
                # PRIORITY_ORDER 未定义，使用默认值
                self._log_step("未找到优先级排序配置，按搜索顺序保存", "WARNING")
            
            # 应用保存条数限制（从配置中读取）
            try:
                max_save_count = MAX_SAVE_COUNT if 'MAX_SAVE_COUNT' in globals() else None
                if max_save_count is not None and isinstance(max_save_count, int) and max_save_count > 0:
                    before_limit_count = len(results)
                    results = results[:max_save_count]
                    after_limit_count = len(results)
                    if before_limit_count > after_limit_count:
                        self._log_step(f"应用保存条数限制：从 {before_limit_count} 个视频中只保存前 {max_save_count} 个", "WARNING")
                    else:
                        self._log_step(f"保存条数限制：{max_save_count} 个（当前有 {after_limit_count} 个视频）", "SUCCESS")
                elif max_save_count is None:
                    self._log_step(f"未设置保存条数限制（MAX_SAVE_COUNT=None），将保存所有通过过滤的视频", "INFO")
                else:
                    self._log_step(f"保存条数限制配置无效（MAX_SAVE_COUNT={max_save_count}），将保存所有通过过滤的视频", "WARNING")
            except NameError:
                # MAX_SAVE_COUNT 未定义，使用默认值
                self._log_step("未找到保存条数配置，将保存所有通过过滤的视频", "WARNING")
                
        except Exception as e:
            self._log_step(f"应用过滤时出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            # 如果过滤出错，为了安全起见，不保存任何结果
            self._log_step("由于过滤出错，为了安全起见，不保存任何视频结果", "ERROR")
            results = []
        
        # 保存结果（只保存通过过滤的视频，且不超过配置的条数）
        if results:
            self.save_results(results, search_query)
            self._log_step("=" * 60)
            self._log_step(f"流程完成！共保存 {len(results)} 个通过过滤的视频结果", "SUCCESS")
            self._log_step("=" * 60)
        else:
            self._log_step("=" * 60)
            self._log_step("流程完成！但没有视频通过过滤条件，未保存任何结果", "WARNING")
            self._log_step("=" * 60)
        
        # 搜索完后等待30秒，并打印倒计时信息
        self._wait_with_countdown(30)
        
        return results
    
    def close(self):
        """关闭浏览器"""
        try:
            self._log_step("开始关闭浏览器...")
            if self.page:
                self.page.close()
                self._log_step("页面已关闭")
            if self.browser:
                self.browser.close()
                self._log_step("浏览器已关闭")
            if self.playwright:
                self.playwright.stop()
                self._log_step("Playwright 已停止")
            self._log_step("浏览器关闭完成", "SUCCESS")
        except Exception as e:
            self._log_step(f"关闭浏览器时出错: {e}", "ERROR")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def main():
    """主函数示例"""
    # 使用上下文管理器确保浏览器正确关闭
    with YouTubeSearcher(headless=False) as searcher:
        # 执行搜索
        search_query = "Python教程"
        results = searcher.search_and_save(search_query, click_recent_upload=True)
        
        # 打印结果
        print(f"\n共找到 {len(results)} 个视频:")
        for i, video in enumerate(results, 1):
            print(f"\n{i}.    标题: {video['title']}")
            print(f"   类型: {'竖屏视频(SHORTS)' if video['is_shorts'] else '普通视频'}")
            print(f"   观看次数: {video['view_count']}")
            print(f"   发布时间: {video['publish_time']}")
            print(f"   链接: {video['url']}")


if __name__ == '__main__':
    main()
