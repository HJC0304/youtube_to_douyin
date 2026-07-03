"""
YouTube Shorts 视频信息提取功能
从 YouTube 频道 Shorts 页面提取视频信息
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# 超时时间常量（30秒）
TIMEOUT = 30000
# YouTube 基础 URL
YOUTUBE_BASE_URL = "https://www.youtube.com"


class YouTubeShortsExtractor:
    """YouTube Shorts 视频信息提取器"""
    
    def __init__(self, headless: bool = False, browser_type: str = "chromium", init_browser: bool = True):
        """
        初始化 YouTube Shorts 提取器
        
        Args:
            headless: 是否使用无头模式
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
            init_browser: 是否立即初始化浏览器（默认 True）
        """
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None
        self.cookies_path = Path(__file__).parent.parent / "data" / "cookies" / ".youtube_cookies.json"
        self.result_dir = Path(__file__).parent.parent / "data" / "search_result"
        self.headless = headless
        self.browser_type = browser_type
        self.step_counter = 0
        if init_browser:
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
        self.browser = browser_launcher.launch(headless=self.headless)
        self._log_step("浏览器启动成功", "SUCCESS")
        
        # 创建上下文和页面
        self._log_step("创建浏览器上下文...")
        context = self.browser.new_context()
        self.page = context.new_page()
        self._log_step("页面创建成功", "SUCCESS")
        
        # 加载 cookies（如果存在）
        self.load_cookies()
    
    
    def load_cookies(self):
        """加载保存的 cookies"""
        if not self.cookies_path.exists():
            self._log_step("未找到保存的登录信息文件", "WARNING")
            return False
        
        try:
            import json
            self._log_step("检查是否存在保存的登录信息...")
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                if cookies:
                    self._log_step(f"找到 {len(cookies)} 个 cookies，开始加载...")
                    # 确保 cookies 格式正确
                    valid_cookies = []
                    for cookie in cookies:
                        if isinstance(cookie, dict):
                            if 'domain' not in cookie:
                                cookie['domain'] = '.youtube.com'
                            if 'path' not in cookie:
                                cookie['path'] = '/'
                            valid_cookies.append(cookie)
                    
                    self.page.context.add_cookies(valid_cookies)
                    self._log_step("Cookies 加载成功", "SUCCESS")
                    return True
        except Exception as e:
            self._log_step(f"加载 cookies 失败: {e}", "WARNING")
            return False
    
    def save_cookies(self):
        """保存当前 cookies"""
        try:
            self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
            cookies = self.page.context.cookies()
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            self._log_step("Cookies 保存成功", "SUCCESS")
        except Exception as e:
            self._log_step(f"保存 cookies 失败: {e}", "WARNING")
    
    def _get_result_path(self, youtuber_name: str) -> Path:
        """
        获取结果文件路径，格式：日期_youtuber_shorts_www.youtube.com.json
        注意："youtuber" 是固定字符串，不是变量
        
        Args:
            youtuber_name: YouTuber 名称（从URL中提取，如 KaradenizliMacerac%C4%B1，不包含@）
            
        Returns:
            结果文件路径
        """
        # 生成日期字符串 yyyyMMdd
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 从 YouTube 基础 URL 提取域名
        domain = urlparse(YOUTUBE_BASE_URL).netloc  # 例如: www.youtube.com
        
        # 构建文件名：日期_youtuber_shorts_域名.json
        # 注意："youtuber" 是固定字符串，不是变量
        filename = f"{date_str}_youtuber_shorts_{domain}.json"
        
        # 确保结果目录存在
        self.result_dir.mkdir(parents=True, exist_ok=True)
        
        return self.result_dir / filename
    
    def _extract_youtuber_name(self, url: str) -> str:
        """
        从 URL 中提取 YouTuber 名称
        
        Args:
            url: YouTube Shorts 页面 URL，如 https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts
            
        Returns:
            YouTuber 名称，如 KaradenizliMacerac%C4%B1（不包含@）
        """
        # 匹配 @用户名 格式
        match = re.search(r'@([^/]+)', url)
        if match:
            return match.group(1)
        return "unknown"
    
    def load_youtubers(self, youtubers_path: Optional[Path] = None) -> List[Dict]:
        """
        从 youtubers.json 文件加载 YouTuber 列表
        
        Args:
            youtubers_path: youtubers.json 文件路径，如果为 None 则使用默认路径
            
        Returns:
            YouTuber 列表，每个元素包含 name 和 url
        """
        if youtubers_path is None:
            youtubers_path = Path(__file__).parent.parent / "data" / "youtubers" / "youtubers.json"
        
        try:
            self._log_step(f"读取 YouTuber 列表: {youtubers_path}")
            with open(youtubers_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                youtubers = data.get('youtubers', [])
                self._log_step(f"找到 {len(youtubers)} 个 YouTuber", "SUCCESS")
                return youtubers
        except FileNotFoundError:
            self._log_step(f"文件不存在: {youtubers_path}", "ERROR")
            raise
        except json.JSONDecodeError as e:
            self._log_step(f"JSON 解析失败: {e}", "ERROR")
            raise
        except Exception as e:
            self._log_step(f"读取文件失败: {e}", "ERROR")
            raise
    
    def extract_all_youtubers(self, max_videos: int = 20, youtubers_path: Optional[Path] = None) -> Dict[str, List[Dict]]:
        """
        批量提取所有 YouTuber 的 Shorts 视频信息
        
        Args:
            max_videos: 每个 YouTuber 最大提取视频数量，默认20
            youtubers_path: youtubers.json 文件路径，如果为 None 则使用默认路径
            
        Returns:
            字典，key 为 YouTuber 名称，value 为视频信息列表
        """
        # 加载 YouTuber 列表
        youtubers = self.load_youtubers(youtubers_path)
        
        all_results = {}
        all_videos = []  # 用于保存所有视频到一个文件
        
        # 获取统一的文件路径（所有 YouTuber 保存到同一个文件）
        result_path = self._get_result_path("")  # 传入空字符串，因为文件名是固定的
        
        for i, youtuber in enumerate(youtubers, 1):
            name = youtuber.get('name', '')
            url = youtuber.get('url', '')
            
            if not name or not url:
                self._log_step(f"跳过无效的 YouTuber 条目: {youtuber}", "WARNING")
                continue
            
            self._log_step("=" * 80)
            self._log_step(f"处理 YouTuber {i}/{len(youtubers)}: {name}")
            self._log_step("=" * 80)
            
            try:
                # 提取 YouTuber 名称（不包含@）
                youtuber_name = self._extract_youtuber_name(url)
                
                # 访问页面
                self._log_step("正在访问 Shorts 页面...")
                self.page.goto(url, wait_until="networkidle", timeout=TIMEOUT)
                self._log_step("页面加载成功", "SUCCESS")
                
                # 等待视频列表加载
                self._log_step("等待视频列表加载...")
                self.page.wait_for_selector('div#contents', timeout=TIMEOUT)
                self._log_step("视频列表已加载", "SUCCESS")
                
                # 滚动页面以加载更多视频
                self._log_step("滚动页面以加载更多视频...")
                for j in range(3):
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                self._log_step("页面滚动完成", "SUCCESS")
                
                # 提取视频信息
                self._log_step("开始提取视频信息...")
                videos = self._parse_video_list(max_videos, youtuber_name)
                self._log_step(f"成功提取 {len(videos)} 个视频信息", "SUCCESS")
                
                # 添加到结果中
                all_results[name] = videos
                all_videos.extend(videos)  # 添加到总列表
                
                self._log_step(f"✅ {name} 处理完成，提取了 {len(videos)} 个视频", "SUCCESS")
            except Exception as e:
                self._log_step(f"❌ {name} 处理失败: {e}", "ERROR")
                all_results[name] = []
                continue
            
            # 在处理下一个 YouTuber 之前稍作等待
            if i < len(youtubers):
                time.sleep(2)
        
        # 保存所有视频到一个文件
        if all_videos:
            self._log_step("=" * 80)
            self._log_step(f"保存所有 YouTuber 的视频信息到统一文件...")
            self._save_all_results(all_videos, result_path)
        
        return all_results
    
    def _get_downloaded_urls(self) -> set:
        """
        获取已下载视频的 URL 集合
        
        Returns:
            已下载视频的 URL 集合
        """
        downloaded_urls = set()
        download_result_path = Path(__file__).parent.parent / "data" / "download_result" / "youtuber_shorts_www.youtube.com.json"
        
        if not download_result_path.exists():
            self._log_step("未找到下载记录文件，视为首次下载", "INFO")
            return downloaded_urls
        
        try:
            with open(download_result_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                downloaded_videos = data.get('results', [])
                
                for video in downloaded_videos:
                    url = video.get('url', '')
                    if url:
                        downloaded_urls.add(url)
                
                if downloaded_urls:
                    self._log_step(f"从下载记录文件中找到 {len(downloaded_urls)} 个已下载的视频", "SUCCESS")
                else:
                    self._log_step("下载记录文件中没有已下载的视频", "INFO")
        except Exception as e:
            self._log_step(f"读取下载记录文件失败: {e}", "WARNING")
        
        return downloaded_urls
    
    def _save_all_results(self, videos: List[Dict], result_path: Path):
        """
        保存所有 YouTuber 的视频信息到统一文件（自动过滤已下载的视频）
        
        Args:
            videos: 所有视频信息列表
            result_path: 保存路径
        """
        try:
            self._log_step(f"保存结果到文件: {result_path.name}")
            
            # 步骤1: 读取已下载的视频 URL
            self._log_step("步骤1: 检查已下载的视频...")
            downloaded_urls = self._get_downloaded_urls()
            
            # 步骤2: 过滤掉已下载的视频
            self._log_step("步骤2: 过滤已下载的视频...")
            original_count = len(videos)
            filtered_videos = []
            skipped_count = 0
            
            for video in videos:
                url = video.get('url', '')
                if not url:
                    # 如果没有 URL，也跳过
                    skipped_count += 1
                    continue
                
                if url in downloaded_urls:
                    skipped_count += 1
                else:
                    filtered_videos.append(video)
            
            # 显示过滤结果
            if skipped_count > 0:
                self._log_step(f"✅ 已过滤 {skipped_count} 个已下载的视频（不保存到搜索结果文件）", "SUCCESS")
            
            if not filtered_videos:
                self._log_step("=" * 80)
                self._log_step("✅ 所有视频都已下载，无需保存到搜索结果文件", "SUCCESS")
                self._log_step(f"   总视频数: {original_count}")
                self._log_step(f"   已下载: {skipped_count}")
                self._log_step(f"   需要保存: 0")
                self._log_step("=" * 80)
                return
            
            self._log_step(f"✅ 需要保存 {len(filtered_videos)} 个新视频到搜索结果文件", "SUCCESS")
            self._log_step(f"   总视频数: {original_count}")
            self._log_step(f"   已下载: {skipped_count}")
            self._log_step(f"   需要保存: {len(filtered_videos)}")
            
            # 步骤3: 保存过滤后的结果
            result_data = {
                "total": len(filtered_videos),
                "results": filtered_videos,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            self._log_step(f"结果已保存: {result_path}", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"保存结果失败: {e}", "ERROR")
            raise
    
    def extract_shorts(self, shorts_url: str, max_videos: int = 20) -> List[Dict]:
        """
        从 YouTube Shorts 页面提取视频信息
        
        Args:
            shorts_url: Shorts 页面 URL，如 https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts
            max_videos: 最大提取视频数量，默认20
            
        Returns:
            视频信息列表
        """
        self._log_step(f"开始提取 Shorts 视频信息...")
        self._log_step(f"目标 URL: {shorts_url}")
        self._log_step(f"最大提取数量: {max_videos}")
        
        # 提取 YouTuber 名称
        youtuber_name = self._extract_youtuber_name(shorts_url)
        self._log_step(f"YouTuber 名称: {youtuber_name}")
        
        try:
            # 访问页面
            self._log_step("正在访问 Shorts 页面...")
            self.page.goto(shorts_url, wait_until="networkidle", timeout=TIMEOUT)
            self._log_step("页面加载成功", "SUCCESS")
            
            # 等待视频列表加载
            self._log_step("等待视频列表加载...")
            self.page.wait_for_selector('div#contents', timeout=TIMEOUT)
            self._log_step("视频列表已加载", "SUCCESS")
            
            # 滚动页面以加载更多视频
            self._log_step("滚动页面以加载更多视频...")
            for i in range(3):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
            self._log_step("页面滚动完成", "SUCCESS")
            
            # 提取视频信息
            self._log_step("开始提取视频信息...")
            videos = self._parse_video_list(max_videos, youtuber_name)
            self._log_step(f"成功提取 {len(videos)} 个视频信息", "SUCCESS")
            
            # 保存结果
            result_path = self._get_result_path(youtuber_name)
            self._save_results(videos, youtuber_name, shorts_url, result_path)
            
            return videos
            
        except PlaywrightTimeoutError as e:
            self._log_step(f"操作超时: {e}", "ERROR")
            raise
        except Exception as e:
            self._log_step(f"提取失败: {e}", "ERROR")
            raise
    
    def _parse_video_list(self, max_videos: int, youtuber_name: str = "") -> List[Dict]:
        """
        解析视频列表
        
        Args:
            max_videos: 最大提取数量
            youtuber_name: YouTuber 名称（用于传递给单个视频解析）
            
        Returns:
            视频信息列表
        """
        videos = []
        
        # 查找所有视频容器（id="content" 的 div，在 id="contents" 内）
        try:
            # 先找到 contents 容器
            contents_div = self.page.locator('div#contents')
            
            # 等待至少一个视频加载
            contents_div.locator('div#content').first.wait_for(timeout=10000)
            
            # 在 contents 内查找所有 content div
            # 注意：YouTube 页面可能有多个 id="content" 的元素，我们需要在 contents 内部查找
            video_containers = contents_div.locator('div#content').all()
            
            self._log_step(f"找到 {len(video_containers)} 个视频容器")
            
            # 如果找到的容器少于需要的数量，尝试滚动加载更多
            if len(video_containers) < max_videos:
                self._log_step("视频数量不足，继续滚动加载...")
                for _ in range(2):
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    video_containers = contents_div.locator('div#content').all()
                    if len(video_containers) >= max_videos:
                        break
            
            for i, container in enumerate(video_containers[:max_videos], 1):
                try:
                    video_info = self._parse_single_video(container, i, youtuber_name)
                    if video_info and video_info.get('title'):  # 确保有标题
                        videos.append(video_info)
                        self._log_step(f"  视频 {i}: {video_info.get('title', 'N/A')[:50]}...", "SUCCESS")
                except Exception as e:
                    self._log_step(f"  视频 {i} 解析失败: {e}", "WARNING")
                    continue
                    
        except Exception as e:
            self._log_step(f"解析视频列表失败: {e}", "ERROR")
        
        return videos
    
    def _parse_single_video(self, container, index: int, youtuber_name: str = "") -> Optional[Dict]:
        """
        解析单个视频信息
        
        Args:
            container: 视频容器元素
            index: 视频索引
            youtuber_name: YouTuber 名称（用于 search_query 字段）
            
        Returns:
            视频信息字典，如果解析失败返回 None
        """
        try:
            # 1. 提取视频 URL
            # 查找 a 标签的 href（优先查找指向 /shorts/ 或 /watch 的链接）
            link_element = None
            
            # 先尝试查找指向视频的链接
            video_links = container.locator('a[href*="/shorts/"], a[href*="/watch"]').all()
            if video_links:
                link_element = video_links[0]
            else:
                # 备用：查找第一个 a 标签
                link_element = container.locator('a').first
            
            if not link_element or not link_element.count():
                return None
            
            href = link_element.get_attribute('href')
            if not href:
                return None
            
            # 构建完整 URL
            if href.startswith('/'):
                video_url = urljoin(YOUTUBE_BASE_URL, href)
            elif href.startswith('http'):
                video_url = href
            else:
                video_url = urljoin(YOUTUBE_BASE_URL, '/' + href.lstrip('/'))
            
            # 2. 提取标题
            # 查找 role="presentation" 的 h 标签
            title = ""
            title_element = container.locator('h[role="presentation"]').first
            if title_element.count():
                title = title_element.inner_text().strip()
            else:
                # 备用方案1：查找 id 包含 "title" 的元素
                title_element = container.locator('[id*="title"]').first
                if title_element.count():
                    title = title_element.inner_text().strip()
                else:
                    # 备用方案2：查找 h1-h4 标签
                    title_element = container.locator('h1, h2, h3, h4').first
                    if title_element.count():
                        title = title_element.inner_text().strip()
            
            if not title:
                # 如果还是没找到，尝试从链接的 title 属性获取
                title_attr = link_element.get_attribute('title')
                if title_attr:
                    title = title_attr.strip()
            
            # 3. 提取播放次数
            # 查找 role="text" 的 span 标签
            view_count = "未知"
            text_spans = container.locator('span[role="text"]').all()
            for span in text_spans:
                text = span.inner_text().strip()
                # 检查是否包含播放次数相关的关键词
                if '观看' in text or 'views' in text.lower() or '次' in text or 'view' in text.lower():
                    # 进一步验证：包含数字
                    if re.search(r'\d', text):
                        view_count = text
                        break
            
            # 如果没找到，尝试查找包含数字和"观看"/"views"的文本
            if view_count == "未知":
                all_text = container.inner_text()
                # 使用正则表达式查找播放次数
                view_patterns = [
                    r'(\d+[万千]?次观看)',
                    r'(\d+[万千]? views)',
                    r'(\d+[万千]?次)',
                    r'(\d+[.,]?\d*[万千]? views)',
                    r'(\d+[.,]?\d*[万千]?次)',
                ]
                for pattern in view_patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE)
                    if match:
                        view_count = match.group(1)
                        break
            
            # 如果标题为空，跳过这个视频
            if not title:
                return None
            
            # 判断是否为 Shorts 视频
            is_shorts = '/shorts/' in video_url.lower()
            
            video_info = {
                "search_query": f"@{youtuber_name}" if youtuber_name else "",
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_shorts": is_shorts,
                "orientation": "竖屏" if is_shorts else "横屏",
                "title": title,
                "url": video_url,
                "url_relative": href if href.startswith('/') else '/' + href.lstrip('/'),
                "duration": "未知",
                "resolution": "未知",
                "view_count": view_count,
                "publish_time": "未知"
            }
            
            return video_info
            
        except Exception as e:
            self._log_step(f"解析视频 {index} 时出错: {e}", "WARNING")
            return None
    
    def _save_results(self, videos: List[Dict], youtuber_name: str, shorts_url: str, result_path: Path):
        """
        保存提取结果到文件（自动过滤已下载的视频）
        
        Args:
            videos: 视频信息列表
            youtuber_name: YouTuber 名称
            shorts_url: Shorts 页面 URL
            result_path: 保存路径
        """
        try:
            self._log_step(f"保存结果到文件: {result_path.name}")
            
            # 步骤1: 读取已下载的视频 URL
            self._log_step("步骤1: 检查已下载的视频...")
            downloaded_urls = self._get_downloaded_urls()
            
            # 步骤2: 过滤掉已下载的视频
            self._log_step("步骤2: 过滤已下载的视频...")
            original_count = len(videos)
            filtered_videos = []
            skipped_count = 0
            
            for video in videos:
                url = video.get('url', '')
                if not url:
                    # 如果没有 URL，也跳过
                    skipped_count += 1
                    continue
                
                if url in downloaded_urls:
                    skipped_count += 1
                else:
                    filtered_videos.append(video)
            
            # 显示过滤结果
            if skipped_count > 0:
                self._log_step(f"✅ 已过滤 {skipped_count} 个已下载的视频（不保存到搜索结果文件）", "SUCCESS")
            
            if not filtered_videos:
                self._log_step("=" * 80)
                self._log_step("✅ 所有视频都已下载，无需保存到搜索结果文件", "SUCCESS")
                self._log_step(f"   总视频数: {original_count}")
                self._log_step(f"   已下载: {skipped_count}")
                self._log_step(f"   需要保存: 0")
                self._log_step("=" * 80)
                return
            
            self._log_step(f"✅ 需要保存 {len(filtered_videos)} 个新视频到搜索结果文件", "SUCCESS")
            self._log_step(f"   总视频数: {original_count}")
            self._log_step(f"   已下载: {skipped_count}")
            self._log_step(f"   需要保存: {len(filtered_videos)}")
            
            # 步骤3: 保存过滤后的结果
            result_data = {
                "total": len(filtered_videos),
                "search_query": f"@{youtuber_name}",
                "search_url": shorts_url,
                "search_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "results": filtered_videos,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            self._log_step(f"结果已保存: {result_path}", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"保存结果失败: {e}", "ERROR")
            raise
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.save_cookies()
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


def extract_youtube_shorts(shorts_url: str, max_videos: int = 20, headless: bool = False):
    """
    提取 YouTube Shorts 视频信息的便捷函数
    
    Args:
        shorts_url: Shorts 页面 URL，如 https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts
        max_videos: 最大提取视频数量，默认20
        headless: 是否使用无头模式
        
    Returns:
        视频信息列表
    """
    with YouTubeShortsExtractor(headless=headless) as extractor:
        return extractor.extract_shorts(shorts_url, max_videos)


def extract_all_youtubers_shorts(max_videos: int = 20, headless: bool = False, youtubers_path: Optional[Path] = None):
    """
    批量提取所有 YouTuber 的 Shorts 视频信息（从 youtubers.json 读取）
    
    Args:
        max_videos: 每个 YouTuber 最大提取视频数量，默认20
        headless: 是否使用无头模式
        youtubers_path: youtubers.json 文件路径，如果为 None 则使用默认路径
        
    Returns:
        字典，key 为 YouTuber 名称，value 为视频信息列表
    """
    # 使用上下文管理器，自动处理资源清理
    with YouTubeShortsExtractor(headless=headless) as extractor:
        return extractor.extract_all_youtubers(max_videos, youtubers_path)


def main():
    """主函数 - 用于测试"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python extract_shorts.py <shorts_url> [max_videos]")
        print("  python extract_shorts.py --all [max_videos]  # 批量处理所有 YouTuber")
        print()
        print("示例:")
        print('  python extract_shorts.py "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts" 20')
        print('  python extract_shorts.py --all 20  # 批量处理所有 YouTuber')
        return
    
    # 检查是否是批量处理模式
    if sys.argv[1] == '--all' or sys.argv[1] == '-a':
        max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        try:
            print(f"🔄 开始批量处理所有 YouTuber（每个提取 {max_videos} 个视频）...")
            all_results = extract_all_youtubers_shorts(max_videos, headless=False)
            
            print("\n" + "=" * 80)
            print("✅ 批量处理完成！")
            print("=" * 80)
            for name, videos in all_results.items():
                print(f"\n{name}: {len(videos)} 个视频")
        except Exception as e:
            print(f"❌ 批量处理失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        shorts_url = sys.argv[1]
        max_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        
        try:
            videos = extract_youtube_shorts(shorts_url, max_videos, headless=False)
            print(f"\n✅ 成功提取 {len(videos)} 个视频信息")
            print("\n前5个视频:")
            for i, video in enumerate(videos[:5], 1):
                print(f"\n{i}. {video.get('title', 'N/A')}")
                print(f"   URL: {video.get('url', 'N/A')}")
                print(f"   播放次数: {video.get('view_count', 'N/A')}")
        except Exception as e:
            print(f"❌ 提取失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    import sys
    main()

