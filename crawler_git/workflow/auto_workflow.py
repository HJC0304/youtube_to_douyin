"""
自动化工作流：YouTube Shorts 提取、下载和上传

整合 VPN、视频提取、下载和上传功能，实现完整的自动化流程。
支持步骤控制：可跳过指定步骤或只执行部分步骤。

工作流步骤：
1. 打开 VPN（等待60秒确保连接）
2. 提取视频（从 youtubers.json 读取配置，提取 YouTube Shorts）
3. 下载视频（使用 Downie 4 下载，自动去重）
4. 检测下载完成（等待所有视频下载完成，如果所有视频已下载则自动跳过）
5. 关闭 VPN
6. 上传视频（智能选择当天播放量最多的视频）
"""
# chuan
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from config.store_config.download_config import get_default_video_download_dir
from vpn.open_privadovpn import open_and_connect_privadovpn, close_privadovpn
from youtube_crawler.extract_shorts import YouTubeShortsExtractor
from downie4.download_youtube import download_youtube_video
from douyin.upload_video import DouyinUploader


class AutoWorkflow:
    """
    自动化工作流类
    
    整合 VPN、视频提取、下载和上传功能，实现从视频提取到上传的完整自动化流程。
    支持灵活的步骤控制，可以跳过指定步骤或只执行部分步骤。
    """
    
    def __init__(self):
        """初始化工作流，设置项目路径和下载目录"""
        self.project_root = Path(__file__).parent.parent
        self.download_dir = get_default_video_download_dir()
        self.step_counter = 0
    
    def _log_step(self, message: str, status: str = "INFO"):
        """打印执行步骤日志"""
        self.step_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_symbol = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(status, "ℹ️")
        print(f"[{timestamp}] [{self.step_counter:02d}] {status_symbol} {message}")
    
    def _wait_with_countdown(self, seconds: int, message: str = "等待中"):
        """等待指定秒数，显示倒计时"""
        self._log_step(f"{message} ({seconds}秒)...")
        for remaining in range(seconds, 0, -1):
            print(f"   倒计时: {remaining}秒", end='\r')
            time.sleep(1)
        print(f"   {message}完成！" + " " * 20)
    
    def step1_open_vpn(self) -> bool:
        """
        步骤1: 打开 PrivadoVPN 应用程序
        
        打开 PrivadoVPN 应用程序，等待60秒确保 VPN 连接网络。
        
        Returns:
            bool: 是否成功打开 VPN
        """
        self._log_step("=" * 80)
        self._log_step("步骤1: 打开 PrivadoVPN 应用程序")
        self._log_step("=" * 80)
        
        try:
            success = open_and_connect_privadovpn()
            if not success:
                self._log_step("VPN 打开失败", "ERROR")
                return False
            
            # 等待60秒，确保 PrivadoVPN 连接网络
            self._wait_with_countdown(60, "等待 PrivadoVPN 连接网络")
            
            self._log_step("步骤1完成: PrivadoVPN 已打开并连接网络", "SUCCESS")
            return True
        except Exception as e:
            self._log_step(f"步骤1失败: {e}", "ERROR")
            return False
    
    def step2_extract_shorts(self, max_videos_per_youtuber: int = 1) -> List[Dict]:
        """
        步骤2: 从 youtubers.json 提取 YouTube Shorts 视频
        
        从配置文件读取 YouTuber 列表，批量提取每个 YouTuber 的 Shorts 视频信息。
        结果保存到 data/search_result/{日期}_youtuber_shorts_www.youtube.com.json
        
        Args:
            max_videos_per_youtuber: 每个 YouTuber 提取的视频数量，默认1
            
        Returns:
            List[Dict]: 提取的视频信息列表
        """
        self._log_step("=" * 80)
        self._log_step(f"步骤2: 提取 YouTube Shorts 视频（每个 YouTuber 获取 {max_videos_per_youtuber} 个最新视频）")
        self._log_step("=" * 80)
        
        try:
            extractor = YouTubeShortsExtractor(headless=False)
            all_results = extractor.extract_all_youtubers(max_videos=max_videos_per_youtuber)
            
            total_videos = sum(len(videos) for videos in all_results.values())
            self._log_step(f"步骤2完成: 共提取 {total_videos} 个视频", "SUCCESS")
            
            extractor.close()
            
            # 从保存的结果文件读取视频列表
            result_path = extractor._get_result_path("")
            if result_path.exists():
                with open(result_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('results', [])
            
            return []
        except Exception as e:
            self._log_step(f"步骤2失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return []
    
    def step3_download_videos(self, videos: List[Dict], wait_seconds: int = 180) -> List[Dict]:
        """
        步骤3: 使用 Downie 4 下载视频
        
        检查已下载记录（通过标题对比去重），只下载新视频。
        如果所有视频都已下载，返回空列表（步骤4会自动跳过）。
        
        Args:
            videos: 要下载的视频列表
            wait_seconds: 等待 Downie 4 开始下载的时间（秒），默认180秒
            
        Returns:
            List[Dict]: 新下载的视频列表（如果所有视频都已下载，返回空列表）
        """
        self._log_step("=" * 80)
        self._log_step(f"步骤3: 使用 Downie 4 下载视频（等待 {wait_seconds} 秒）")
        self._log_step("=" * 80)
        
        if not videos:
            self._log_step("没有视频需要下载", "WARNING")
            return []
        
        try:
            # 加载已下载记录，用于标题对比去重
            self._log_step("检查已下载的视频（通过标题对比）...")
            download_result_path = self.project_root / "data" / "download_result" / "youtuber_shorts_www.youtube.com.json"
            existing_titles = self._load_downloaded_titles(download_result_path)
            
            if existing_titles:
                self._log_step(f"找到 {len(existing_titles)} 个已下载的视频记录", "SUCCESS")
            
            # 筛选需要下载的视频
            videos_to_download = []
            skipped_count = 0
            
            for video in videos:
                url = video.get('url', '')
                title = video.get('title', '')
                
                if not url or not title:
                    continue
                
                normalized_title = self._normalize_string_for_matching(title)
                if normalized_title in existing_titles:
                    skipped_count += 1
                else:
                    videos_to_download.append(video)
            
            # 如果所有视频都已下载，直接返回
            if skipped_count == len(videos):
                self._log_step(f"所有 {len(videos)} 个视频都已下载，跳过下载步骤", "SUCCESS")
                return []
            
            if skipped_count > 0:
                self._log_step(f"已跳过 {skipped_count} 个重复视频", "INFO")
            self._log_step(f"需要下载 {len(videos_to_download)} 个新视频", "INFO")
            
            # 下载新视频
            downloaded_videos = []
            for i, video in enumerate(videos_to_download, 1):
                url = video.get('url', '')
                title = video.get('title', '未知标题')
                
                self._log_step(f"下载视频 {i}/{len(videos_to_download)}: {title[:50]}...")
                try:
                    if download_youtube_video(url):
                        video_copy = video.copy()
                        video_copy['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        downloaded_videos.append(video_copy)
                        self._log_step(f"视频 {i} 下载任务已创建", "SUCCESS")
                    else:
                        self._log_step(f"视频 {i} 下载任务创建失败", "WARNING")
                    time.sleep(2)  # 每个视频之间等待2秒
                except Exception as e:
                    self._log_step(f"视频 {i} 下载失败: {e}", "ERROR")
            
            self._log_step(f"已创建 {len(downloaded_videos)}/{len(videos_to_download)} 个下载任务", "SUCCESS")
            
            # 保存下载结果
            if downloaded_videos:
                self._save_download_results(downloaded_videos)
            
            # 检查文件是否已下载（智能等待）
            if downloaded_videos:
                self._log_step("检查视频文件是否已下载...", "INFO")
                all_downloaded = self._check_videos_downloaded(downloaded_videos)
                
                if all_downloaded:
                    # 如果所有视频都已下载，只等待10秒稳定时间
                    self._log_step("✅ 所有视频文件已存在，等待10秒稳定时间...", "SUCCESS")
                    self._wait_with_countdown(10, "等待文件稳定")
                    self._log_step("步骤3完成: 所有视频已下载完成", "SUCCESS")
                else:
                    # 如果部分或全部视频未下载，等待较短时间让 Downie 4 开始下载
                    short_wait = min(30, wait_seconds // 6)  # 最多等待30秒，或原等待时间的1/6
                    self._log_step(f"部分视频未下载，等待 {short_wait} 秒让 Downie 4 开始下载...", "INFO")
                    self._wait_with_countdown(short_wait, "等待 Downie 4 开始下载")
                    self._log_step("步骤3完成: 下载任务已创建并等待中", "SUCCESS")
            else:
                # 没有新下载的视频，直接完成
                self._log_step("步骤3完成: 没有新视频需要下载", "SUCCESS")
            
            return downloaded_videos
        except Exception as e:
            self._log_step(f"步骤3失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return []
    
    def _load_downloaded_titles(self, download_result_path: Path) -> set:
        """
        加载已下载视频的标题集合（用于去重）
        
        Args:
            download_result_path: 下载记录文件路径
            
        Returns:
            set: 规范化后的标题集合
        """
        existing_titles = set()
        if download_result_path.exists():
            try:
                with open(download_result_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for video in data.get('results', []):
                        title = video.get('title', '')
                        if title:
                            existing_titles.add(self._normalize_string_for_matching(title))
            except Exception as e:
                self._log_step(f"读取下载记录文件失败: {e}，将视为首次下载", "WARNING")
        return existing_titles
    
    def _save_download_results(self, downloaded_videos: List[Dict]):
        """
        保存下载结果到 data/download_result/youtuber_shorts_www.youtube.com.json
        
        Args:
            downloaded_videos: 新下载的视频信息列表（包含 download_time）
        """
        try:
            download_result_dir = self.project_root / "data" / "download_result"
            download_result_dir.mkdir(parents=True, exist_ok=True)
            target_path = download_result_dir / "youtuber_shorts_www.youtube.com.json"
            
            self._log_step(f"保存下载结果到: {target_path.name}")
            
            # 加载已存在的下载记录
            existing_results = []
            if target_path.exists():
                try:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        existing_results = json.load(f).get('results', [])
                except Exception as e:
                    self._log_step(f"读取现有下载记录失败: {e}，将创建新文件", "WARNING")
            
            # 通过 URL 去重合并
            existing_urls = {v.get('url', '') for v in existing_results if v.get('url')}
            merged_results = existing_results.copy()
            new_count = 0
            
            for video in downloaded_videos:
                url = video.get('url', '')
                if url and url not in existing_urls:
                    merged_results.append(video)
                    existing_urls.add(url)
                    new_count += 1
            
            # 保存结果
            result_data = {
                "total": len(merged_results),
                "results": merged_results,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            status_msg = f"新增 {new_count} 个，总计 {len(merged_results)} 个" if new_count > 0 else f"无新增，总计 {len(merged_results)} 个"
            self._log_step(f"✅ 下载结果已保存: {status_msg}", "SUCCESS")
        except Exception as e:
            self._log_step(f"保存下载结果失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
    
    def _check_videos_downloaded(self, videos: List[Dict]) -> bool:
        """
        检查视频文件是否已下载
        
        Args:
            videos: 要检查的视频列表
            
        Returns:
            bool: 是否所有视频都已下载
        """
        if not videos:
            return True
        
        # 支持的视频文件扩展名
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']
        
        if not self.download_dir.exists():
            return False
        
        # 获取下载目录中的所有视频文件
        all_files = []
        for ext in video_extensions:
            all_files.extend(list(self.download_dir.glob(f"*{ext}")))
        
        # 检查每个视频是否已下载
        found_count = 0
        
        for video in videos:
            video_title = video.get('title', '')
            if not video_title:
                continue
            
            # 规范化标题用于匹配
            normalized_title = self._normalize_string_for_matching(video_title)
            
            # 检查是否有匹配的文件（使用前缀匹配，至少匹配1/2长度）
            found = False
            title_length = len(normalized_title)
            min_prefix_length = max(5, title_length // 2)
            
            for file_path in all_files:
                file_name_without_ext = file_path.stem
                # 规范化文件名
                normalized_filename = self._normalize_string_for_matching(file_name_without_ext)
                
                # 前缀匹配：文件名必须以标题的前缀开头
                if len(normalized_filename) >= min_prefix_length:
                    # 检查文件名是否以标题的前缀开头（至少匹配 min_prefix_length 个字符）
                    for prefix_len in range(len(normalized_title), min_prefix_length - 1, -1):
                        title_prefix = normalized_title[:prefix_len]
                        if normalized_filename.startswith(title_prefix):
                            found = True
                            break
                
                if found:
                    break
            
            if found:
                found_count += 1
        
        return found_count >= len(videos)
    
    def _normalize_string_for_matching(self, s: str) -> str:
        """
        规范化字符串用于匹配
        
        去除不可见字符、统一空格类型、Unicode 规范化，用于视频标题对比去重。
        
        Args:
            s: 原始字符串
            
        Returns:
            规范化后的字符串
        """
        import unicodedata
        import re
        
        if not s:
            return ""
        
        s = s.strip()
        # 去除零宽字符（U+200B, U+FEFF 等）
        s = re.sub(r'[\u200B-\u200D\uFEFF\u00AD]', '', s)
        # 统一空格类型（不间断空格、全角空格等）
        s = re.sub(r'[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]', ' ', s)
        # Unicode 规范化（NFC 形式）
        s = unicodedata.normalize('NFC', s)
        # 合并连续空格
        s = re.sub(r'\s+', ' ', s)
        
        return s.strip()
    
    def step4_check_downloads(self, videos: List[Dict], max_wait_seconds: int = 1200) -> bool:
        """
        步骤4: 检测下载是否完成
        
        只检查本次下载的视频文件（通过标题前缀匹配），最多等待指定时间。
        如果超时仍未全部下载完成，会继续下一步（不终止工作流）。
        
        Args:
            videos: 要检测的视频列表（本次下载的视频）
            max_wait_seconds: 最大等待时间（秒），默认1200秒（20分钟）
            
        Returns:
            bool: 是否所有视频都已下载完成（超时也返回True，继续下一步）
        """
        self._log_step("=" * 80)
        self._log_step(f"步骤4: 检测本次下载的视频是否完成（最多等待 {max_wait_seconds} 秒 / {max_wait_seconds//60} 分钟）")
        self._log_step("=" * 80)
        
        if not videos:
            self._log_step("没有视频需要检测", "WARNING")
            return True
        
        # 支持的视频文件扩展名
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']
        
        start_time = time.time()
        check_interval = 10  # 每10秒检查一次
        
        # 记录下载开始时间，用于筛选本次下载的文件
        download_start_time = time.time()
        # 获取本次下载开始时间（从第一个视频的 download_time 字段，或使用当前时间减去一些缓冲）
        if videos and videos[0].get('download_time'):
            try:
                download_time_str = videos[0].get('download_time')
                download_start_time = datetime.strptime(download_time_str, "%Y-%m-%d %H:%M:%S").timestamp() - 60  # 减去60秒缓冲
            except:
                pass
        
        # 首次列出本次下载的视频文件（只列出在下载开始时间之后修改的文件）
        self._log_step(f"列出本次下载目录中的视频文件（仅检查本次下载的视频）...")
        if self.download_dir.exists():
            all_files = []
            for ext in video_extensions:
                all_files.extend(list(self.download_dir.glob(f"*{ext}")))
            # 筛选本次下载的文件（修改时间在下载开始时间之后）
            recent_files = [f for f in all_files if f.stat().st_mtime >= download_start_time]
            self._log_step(f"找到 {len(recent_files)} 个本次下载的视频文件（总共有 {len(all_files)} 个视频文件）")
            if recent_files:
                for i, f in enumerate(recent_files[:10], 1):  # 只显示前10个
                    self._log_step(f"  文件 {i}: {f.name}")
                if len(recent_files) > 10:
                    self._log_step(f"  ... 还有 {len(recent_files) - 10} 个文件")
        
        while True:
            elapsed_time = time.time() - start_time
            remaining_time = max_wait_seconds - elapsed_time
            
            if remaining_time <= 0:
                self._log_step(f"等待超时（{max_wait_seconds//60} 分钟），未检测到所有视频下载完成", "WARNING")
                self._log_step("将继续进行下一步（上传步骤），未下载完成的视频将在下次运行时处理", "INFO")
                return True  # 超时也返回True，继续下一步
            
            self._log_step(f"检查下载状态（已等待 {int(elapsed_time)} 秒，剩余 {int(remaining_time)} 秒）...")
            
            # 获取下载目录中本次下载的视频文件（只检查修改时间在下载开始时间之后的文件）
            downloaded_files = []
            if self.download_dir.exists():
                for ext in video_extensions:
                    all_files = list(self.download_dir.glob(f"*{ext}"))
                    # 筛选本次下载的文件（修改时间在下载开始时间之后）
                    recent_files = [f for f in all_files if f.stat().st_mtime >= download_start_time]
                    downloaded_files.extend(recent_files)
            
            # 检查每个视频是否已下载
            found_count = 0
            found_videos = []
            
            for video in videos:
                video_title = video.get('title', '')
                if not video_title:
                    continue
                
                # 规范化标题用于匹配
                normalized_title = self._normalize_string_for_matching(video_title)
                
                # 检查是否有匹配的文件（使用前缀匹配，至少匹配1/2长度）
                found = False
                title_length = len(normalized_title)
                min_prefix_length = max(5, title_length // 2)
                
                for file_path in downloaded_files:
                    file_name_without_ext = file_path.stem
                    # 规范化文件名
                    normalized_filename = self._normalize_string_for_matching(file_name_without_ext)
                    
                    # 前缀匹配：文件名必须以标题的前缀开头
                    # 且匹配长度至少为 min_prefix_length
                    if len(normalized_filename) >= min_prefix_length:
                        # 检查文件名是否以标题的前缀开头（至少匹配 min_prefix_length 个字符）
                        for prefix_len in range(len(normalized_title), min_prefix_length - 1, -1):
                            title_prefix = normalized_title[:prefix_len]
                            if normalized_filename.startswith(title_prefix):
                                found = True
                                found_videos.append({
                                    'title': video_title[:50],
                                    'file': file_path.name
                                })
                                break
                    
                    if found:
                        break
                
                if found:
                    found_count += 1
            
            # 显示找到的视频
            if found_videos:
                self._log_step(f"已找到 {found_count}/{len(videos)} 个视频文件:")
                for fv in found_videos:
                    self._log_step(f"  ✓ {fv['title']} -> {fv['file']}")
            
            # 如果所有视频都已找到，退出循环
            if found_count >= len(videos):
                self._log_step(f"步骤4完成: 所有视频已下载完成", "SUCCESS")
                return True
            
            # 等待一段时间后再次检查
            time.sleep(check_interval)
        
        return True  # 理论上不会到达这里，但返回True保证继续执行
    
    def step5_close_vpn(self) -> bool:
        """
        步骤5: 关闭 PrivadoVPN 应用程序
        
        关闭 PrivadoVPN 应用程序，等待60秒确保完全关闭。
        
        Returns:
            bool: 是否成功关闭 VPN
        """
        self._log_step("=" * 80)
        self._log_step("步骤5: 关闭 PrivadoVPN 应用程序")
        self._log_step("=" * 80)
        
        try:
            success = close_privadovpn()
            if success:
                # 等待20秒
                self._wait_with_countdown(20, "等待 PrivadoVPN 完全关闭")
                self._log_step("步骤5完成: PrivadoVPN 已关闭", "SUCCESS")
                return True
            else:
                self._log_step("步骤5失败: PrivadoVPN 关闭时出现问题", "WARNING")
                return False
        except Exception as e:
            self._log_step(f"步骤5失败: {e}", "ERROR")
            return False
    
    def step6_upload_videos(self, max_videos: int = 2) -> bool:
        """
        步骤6: 上传视频到抖音创作者平台
        
        智能选择当天播放量最多的视频进行上传（支持时间优先级和播放量优先级）。
        
        Args:
            max_videos: 上传的视频数量，默认2
            
        Returns:
            bool: 是否成功上传
        """
        self._log_step("=" * 80)
        self._log_step(f"步骤6: 上传播放量最多的 {max_videos} 个视频")
        self._log_step("=" * 80)
        
        try:
            with DouyinUploader(headless=False) as uploader:
                uploader.upload_top_videos_from_today(
                    download_dirs=[str(self.download_dir)],
                    visibility="公开",  # 保持默认状态，不选择"仅自己可见"
                    auto_publish=False,
                    max_videos=max_videos
                )
            
            self._log_step(f"步骤6完成: 已上传 {max_videos} 个视频", "SUCCESS")
            return True
        except Exception as e:
            self._log_step(f"步骤6失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self, max_videos_per_youtuber: int = 1, max_upload_videos: int = 2,
            skip_steps: Optional[List[int]] = None, only_steps: Optional[List[int]] = None) -> bool:
        """
        运行完整自动化工作流
        
        执行从视频提取到上传的完整流程，支持灵活的步骤控制。
        
        Args:
            max_videos_per_youtuber: 每个 YouTuber 提取的视频数量，默认1
            max_upload_videos: 上传的视频数量，默认2
            skip_steps: 要跳过的步骤编号列表（例如：[1, 5]）
            only_steps: 只执行的步骤编号列表（例如：[2, 3, 4]）。如果指定，skip_steps 将被忽略
            
        Returns:
            bool: 工作流是否成功执行
            
        步骤说明：
            1. 打开 VPN（等待60秒确保连接）
            2. 提取视频（从 youtubers.json 读取配置）
            3. 下载视频（自动去重，如果所有视频已下载则跳过步骤4）
            4. 检测下载完成（如果所有视频已下载则自动跳过）
            5. 关闭 VPN
            6. 上传视频（智能选择，支持时间优先级和播放量优先级）
        """
        print("=" * 80)
        print("🚀 开始执行自动化工作流")
        print("=" * 80)
        
        # 处理步骤控制参数
        if only_steps:
            enabled_steps = set(only_steps)
            self._log_step(f"仅执行步骤: {sorted(enabled_steps)}", "INFO")
        elif skip_steps:
            enabled_steps = set(range(1, 7)) - set(skip_steps)
            self._log_step(f"跳过步骤: {sorted(skip_steps)}，将执行步骤: {sorted(enabled_steps)}", "INFO")
        else:
            enabled_steps = set(range(1, 7))  # 默认执行所有步骤
            self._log_step("执行所有步骤", "INFO")
        
        print()
        
        start_time = datetime.now()
        videos = []
        
        try:
            # 步骤1: 打开 VPN
            if 1 in enabled_steps:
                if not self.step1_open_vpn():
                    self._log_step("工作流终止: VPN 打开失败", "ERROR")
                    return False
            else:
                self._log_step("跳过步骤1: 打开 VPN", "INFO")
            
            # 步骤2: 提取视频
            if 2 in enabled_steps:
                videos = self.step2_extract_shorts(max_videos_per_youtuber)
                if not videos:
                    self._log_step("工作流终止: 未提取到视频", "WARNING")
                    return False
            else:
                self._log_step("跳过步骤2: 提取视频", "INFO")
                # 如果跳过提取步骤，尝试从结果文件读取视频列表
                try:
                    result_path = self.project_root / "data" / "search_result"
                    today = datetime.now().strftime("%Y%m%d")
                    filename = f"{today}_youtuber_shorts_www.youtube.com.json"
                    file_path = result_path / filename
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            videos = data.get('results', [])
                            self._log_step(f"从结果文件读取到 {len(videos)} 个视频", "INFO")
                except Exception as e:
                    self._log_step(f"读取结果文件失败: {e}", "WARNING")
            
            # 步骤3: 下载视频
            downloaded_videos = []
            all_videos_already_downloaded = False
            if 3 in enabled_steps:
                downloaded_videos = self.step3_download_videos(videos, wait_seconds=180)
                # 如果步骤3返回空列表，且videos不为空，说明所有视频都已下载
                if not downloaded_videos and videos:
                    all_videos_already_downloaded = True
                    self._log_step("所有视频都已下载，将跳过步骤4（检测下载状态）", "INFO")
                elif not downloaded_videos:
                    self._log_step("工作流继续: 下载任务创建可能有问题", "WARNING")
            else:
                self._log_step("跳过步骤3: 下载视频", "INFO")
            
            # 步骤4: 检测下载完成
            # 如果所有视频都已下载，跳过步骤4
            if 4 in enabled_steps:
                if all_videos_already_downloaded:
                    self._log_step("跳过步骤4: 所有视频都已下载，无需检查下载状态", "INFO")
                elif downloaded_videos:
                    # 只检查本次下载的视频，最多等待20分钟（1200秒）
                    # 如果超时仍未全部下载完成，继续下一步（不终止工作流）
                    self.step4_check_downloads(downloaded_videos, max_wait_seconds=1200)
                else:
                    self._log_step("跳过步骤4: 没有新下载的视频需要检测", "INFO")
            else:
                self._log_step("跳过步骤4: 检测下载完成", "INFO")
            
            # 步骤5: 关闭 VPN
            if 5 in enabled_steps:
                if not self.step5_close_vpn():
                    self._log_step("工作流继续: VPN 关闭可能有问题", "WARNING")
            else:
                self._log_step("跳过步骤5: 关闭 VPN", "INFO")
            
            # 步骤6: 上传视频
            if 6 in enabled_steps:
                if not self.step6_upload_videos(max_upload_videos):
                    self._log_step("工作流终止: 视频上传失败", "ERROR")
                    return False
            else:
                self._log_step("跳过步骤6: 上传视频", "INFO")
            
            # 工作流完成
            end_time = datetime.now()
            duration = end_time - start_time
            
            print()
            print("=" * 80)
            print("✅ 工作流执行完成！")
            print("=" * 80)
            print(f"⏱️  总耗时: {duration}")
            if videos:
                print(f"📊 提取视频数: {len(videos)}")
            print(f"📤 上传视频数: {max_upload_videos}")
            print("=" * 80)
            
            return True
            
        except KeyboardInterrupt:
            self._log_step("工作流被用户中断", "WARNING")
            return False
        except Exception as e:
            self._log_step(f"工作流执行失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="自动化工作流：YouTube Shorts 提取、下载和上传",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
步骤说明：
  1. 打开 VPN
  2. 提取视频
  3. 下载视频
  4. 检测下载完成
  5. 关闭 VPN
  6. 上传视频

示例：
  # 跳过步骤1和步骤5（VPN相关）
  python -m workflow.auto_workflow --skip-steps 1,5
  
  # 只执行步骤2、3、4（提取和下载）
  python -m workflow.auto_workflow --only-steps 2,3,4
  
  # 只执行上传步骤
  python -m workflow.auto_workflow --only-steps 6
        """
    )
    parser.add_argument(
        "--max-videos-per-youtuber",
        type=int,
        default=1,
        help="每个 YouTuber 提取的视频数量（默认: 1）"
    )
    parser.add_argument(
        "--max-upload-videos",
        type=int,
        default=2,
        help="上传的视频数量（默认: 2）"
    )
    parser.add_argument(
        "--skip-steps",
        type=str,
        default=None,
        help="要跳过的步骤编号，用逗号分隔（例如: 1,5 表示跳过步骤1和步骤5）"
    )
    parser.add_argument(
        "--only-steps",
        type=str,
        default=None,
        help="只执行的步骤编号，用逗号分隔（例如: 2,3,4 表示只执行步骤2、3、4）。如果指定了此参数，--skip-steps 将被忽略"
    )
    
    args = parser.parse_args()
    
    # 解析步骤参数
    skip_steps = None
    if args.skip_steps:
        try:
            skip_steps = [int(s.strip()) for s in args.skip_steps.split(',')]
            # 验证步骤编号有效性
            invalid_steps = [s for s in skip_steps if s < 1 or s > 6]
            if invalid_steps:
                print(f"❌ 错误: 无效的步骤编号: {invalid_steps}。步骤编号必须在 1-6 之间")
                sys.exit(1)
        except ValueError:
            print(f"❌ 错误: 无效的步骤编号格式: {args.skip_steps}。请使用逗号分隔的数字，例如: 1,5")
            sys.exit(1)
    
    only_steps = None
    if args.only_steps:
        try:
            only_steps = [int(s.strip()) for s in args.only_steps.split(',')]
            # 验证步骤编号有效性
            invalid_steps = [s for s in only_steps if s < 1 or s > 6]
            if invalid_steps:
                print(f"❌ 错误: 无效的步骤编号: {invalid_steps}。步骤编号必须在 1-6 之间")
                sys.exit(1)
        except ValueError:
            print(f"❌ 错误: 无效的步骤编号格式: {args.only_steps}。请使用逗号分隔的数字，例如: 2,3,4")
            sys.exit(1)
    
    workflow = AutoWorkflow()
    success = workflow.run(
        max_videos_per_youtuber=args.max_videos_per_youtuber,
        max_upload_videos=args.max_upload_videos,
        skip_steps=skip_steps,
        only_steps=only_steps
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

