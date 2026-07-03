"""
YouTube Shorts 批量下载功能
从 search_result 文件夹读取视频 URL，使用 Downie 4 下载，并保存下载结果
"""
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 导入下载功能
try:
    # 尝试从项目根目录导入
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    from downie4.download_youtube import download_youtube_video
except ImportError as e:
    print(f"❌ 错误: 无法导入 downie4.download_youtube 模块: {e}")
    print("请确保 downie4/download_youtube.py 文件存在")
    sys.exit(1)


class ShortsDownloader:
    """YouTube Shorts 批量下载器"""
    
    def __init__(self):
        """初始化下载器"""
        self.search_result_dir = Path(__file__).parent.parent / "data" / "search_result"
        self.download_result_dir = Path(__file__).parent.parent / "data" / "download_result"
        self.download_result_dir.mkdir(parents=True, exist_ok=True)
        self.step_counter = 0
        self._migration_done = False  # 标记是否已执行迁移
    
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
    
    def find_shorts_result_file(self, date_str: Optional[str] = None) -> Optional[Path]:
        """
        查找 Shorts 结果文件
        
        Args:
            date_str: 日期字符串（格式：yyyyMMdd），如果为 None 则查找当天的文件
            
        Returns:
            文件路径，如果未找到返回 None
        """
        # 如果没有指定日期，使用今天的日期
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
            self._log_step(f"未指定日期，使用今天的日期: {date_str}", "INFO")
        
        # 查找指定日期的文件（仅从 search_result 目录）
            pattern = f"{date_str}_youtuber_shorts_www.youtube.com.json"
            file_path = self.search_result_dir / pattern
        
            if file_path.exists():
                return file_path
        else:
            self._log_step(f"未找到日期为 {date_str} 的文件: {pattern}", "WARNING")
        return None
    
    def load_shorts_results(self, file_path: Path) -> Dict:
        """
        加载 Shorts 结果文件
        
        Args:
            file_path: 结果文件路径
            
        Returns:
            结果数据字典
        """
        try:
            self._log_step(f"读取文件: {file_path.name}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._log_step(f"成功读取 {data.get('total', 0)} 个视频信息", "SUCCESS")
                return data
        except FileNotFoundError:
            self._log_step(f"文件不存在: {file_path}", "ERROR")
            raise
        except json.JSONDecodeError as e:
            self._log_step(f"JSON 解析失败: {e}", "ERROR")
            raise
        except Exception as e:
            self._log_step(f"读取文件失败: {e}", "ERROR")
            raise
    
    def download_videos(self, videos: List[Dict], delay: float = 2.0) -> List[Dict]:
        """
        批量下载视频
        
        Args:
            videos: 视频信息列表
            delay: 每个视频下载之间的延迟（秒），默认2秒
            
        Returns:
            已下载的视频信息列表
        """
        downloaded_videos = []
        total = len(videos)
        
        self._log_step(f"开始批量下载，共 {total} 个视频")
        self._log_step(f"下载间隔: {delay} 秒")
        
        # 只在第一次打开 Downie 4
        downie_opened = False
        
        for i, video in enumerate(videos, 1):
            url = video.get('url', '')
            title = video.get('title', 'N/A')
            
            if not url:
                self._log_step(f"视频 {i}/{total}: 跳过（无 URL）", "WARNING")
                continue
            
            self._log_step("=" * 80)
            self._log_step(f"下载视频 {i}/{total}: {title[:50]}...")
            self._log_step(f"URL: {url}")
            
            try:
                # 第一次下载时打开 Downie 4，后续不再打开
                open_app = not downie_opened
                success = download_youtube_video(url, open_app=open_app)
                
                if success:
                    # 添加下载时间戳
                    video['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    video['download_status'] = "success"
                    downloaded_videos.append(video)
                    self._log_step(f"✅ 视频 {i}/{total} 下载任务已启动", "SUCCESS")
                    downie_opened = True
                else:
                    video['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    video['download_status'] = "failed"
                    self._log_step(f"❌ 视频 {i}/{total} 下载任务启动失败", "ERROR")
                    
            except Exception as e:
                self._log_step(f"❌ 视频 {i}/{total} 下载出错: {e}", "ERROR")
                video['download_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                video['download_status'] = "error"
            
            # 等待一段时间再下载下一个（除了最后一个）
            if i < total:
                self._log_step(f"等待 {delay} 秒后继续...")
                time.sleep(delay)
        
        self._log_step("=" * 80)
        self._log_step(f"批量下载完成，成功: {len(downloaded_videos)}/{total}", "SUCCESS")
        
        return downloaded_videos
    
    def migrate_old_files(self):
        """
        迁移旧格式的文件（带日期前缀）到新格式（无日期前缀）
        """
        # 查找所有旧格式的文件
        old_pattern = "*_youtuber_shorts_www.youtube.com.json"
        old_files = list(self.download_result_dir.glob(old_pattern))
        
        if not old_files:
            return
        
        # 新格式文件名
        new_filename = "youtuber_shorts_www.youtube.com.json"
        new_path = self.download_result_dir / new_filename
        
        # 如果新文件已存在，先加载它
        existing_data = {}
        if new_path.exists():
            try:
                with open(new_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                existing_data = {}
        
        existing_urls = {video.get('url', '') for video in existing_data.get('results', []) if video.get('url')}
        merged_results = existing_data.get('results', []).copy()
        
        # 合并所有旧文件的内容
        for old_file in old_files:
            try:
                with open(old_file, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                    old_results = old_data.get('results', [])
                    
                    for video in old_results:
                        url = video.get('url', '')
                        if url and url not in existing_urls:
                            merged_results.append(video)
                            existing_urls.add(url)
                
                # 删除旧文件
                old_file.unlink()
                self._log_step(f"已迁移并删除旧文件: {old_file.name}", "INFO")
            except Exception as e:
                self._log_step(f"迁移文件 {old_file.name} 失败: {e}", "WARNING")
        
        # 保存合并后的结果
        if merged_results:
            result_data = {
                "total": len(merged_results),
                "results": merged_results,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            self._log_step(f"已迁移 {len(merged_results)} 个视频到新格式文件", "SUCCESS")
    
    def load_existing_downloads(self) -> Dict:
        """
        加载已下载的文件
        
        Returns:
            已下载的视频数据字典，如果文件不存在返回空字典
        """
        # 首次运行时迁移旧文件（只执行一次）
        if not self._migration_done:
            self.migrate_old_files()
            self._migration_done = True
        
        # 固定文件名（不含日期）
        target_filename = "youtuber_shorts_www.youtube.com.json"
        target_path = self.download_result_dir / target_filename
        
        if not target_path.exists():
            return {}
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        except Exception as e:
            self._log_step(f"读取已下载文件失败: {e}", "WARNING")
            return {}
    
    def get_downloaded_urls(self) -> set:
        """
        获取已下载的视频URL集合（从 data/download_result/youtuber_shorts_www.youtube.com.json 读取）
        
        Returns:
            已下载的视频URL集合
        """
        # 固定文件名（不含日期）
        target_filename = "youtuber_shorts_www.youtube.com.json"
        target_path = self.download_result_dir / target_filename
        
        if not target_path.exists():
            self._log_step(f"下载记录文件不存在: {target_path.name}（可能是首次下载）", "INFO")
            return set()
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results = data.get('results', [])
                urls = {video.get('url', '') for video in results if video.get('url')}
                if urls:
                    self._log_step(f"成功读取 {len(urls)} 个已下载的视频URL", "SUCCESS")
                return urls
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._log_step(f"读取下载记录文件失败: {e}，将视为首次下载", "WARNING")
            return set()
        except Exception as e:
            self._log_step(f"读取下载记录文件时出错: {e}，将视为首次下载", "WARNING")
            return set()
    
    def save_download_results(self, downloaded_videos: List[Dict], source_file_path: Path):
        """
        保存下载结果到文件（合并已存在的文件内容）
        
        Args:
            downloaded_videos: 新下载的视频信息列表
            source_file_path: 源文件路径（不再使用，保留以兼容）
        """
        try:
            # 固定文件名（不含日期）
            target_filename = "youtuber_shorts_www.youtube.com.json"
            target_path = self.download_result_dir / target_filename
            
            self._log_step(f"保存下载结果到: {target_path.name}")
            
            # 加载已存在的下载记录
            existing_data = self.load_existing_downloads()
            existing_results = existing_data.get('results', [])
            
            # 创建已存在URL的集合，用于去重
            existing_urls = {video.get('url', '') for video in existing_results if video.get('url')}
            
            # 合并新下载的视频（避免重复）
            merged_results = existing_results.copy()
            new_count = 0
            for video in downloaded_videos:
                url = video.get('url', '')
                if url and url not in existing_urls:
                    merged_results.append(video)
                    existing_urls.add(url)
                    new_count += 1
            
            # 保持与 search_result 文件格式一致（不添加额外字段）
            result_data = {
                "total": len(merged_results),
                "results": merged_results,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            if new_count > 0:
                self._log_step(f"✅ 下载结果已保存: {target_path} (新增 {new_count} 个，总计 {len(merged_results)} 个)", "SUCCESS")
            else:
                self._log_step(f"✅ 下载结果已保存: {target_path} (无新增，总计 {len(merged_results)} 个)", "SUCCESS")
            
        except Exception as e:
            self._log_step(f"保存下载结果失败: {e}", "ERROR")
            raise
    
    def download_from_file(self, date_str: Optional[str] = None, delay: float = 2.0) -> List[Dict]:
        """
        从 Shorts 结果文件读取并下载视频
        
        Args:
            date_str: 日期字符串（格式：yyyyMMdd），如果为 None 则使用当天的文件
            delay: 每个视频下载之间的延迟（秒），默认2秒
            
        Returns:
            已下载的视频信息列表
        """
        # 查找结果文件（仅从 search_result 目录，find_shorts_result_file 会自动处理日期）
        file_path = self.find_shorts_result_file(date_str)
        if not file_path:
            # 获取实际使用的日期（用于错误提示）
            actual_date = date_str if date_str else datetime.now().strftime("%Y%m%d")
            self._log_step(f"未找到日期为 {actual_date} 的 Shorts 结果文件", "ERROR")
            self._log_step(f"查找目录: {self.search_result_dir}", "INFO")
            self._log_step(f"查找模式: {actual_date}_youtuber_shorts_www.youtube.com.json", "INFO")
            raise FileNotFoundError(f"未找到日期为 {actual_date} 的 Shorts 结果文件")
        
        self._log_step(f"找到结果文件: {file_path.name}", "SUCCESS")
        
        # 步骤1: 加载视频列表
        self._log_step("步骤1: 加载视频列表...")
        data = self.load_shorts_results(file_path)
        videos = data.get('results', [])
        
        if not videos:
            self._log_step("文件中没有视频信息", "WARNING")
            return []
        
        self._log_step(f"从文件中读取到 {len(videos)} 个视频", "SUCCESS")
        
        # 步骤2: 检查已下载的视频（从 download_result 文件）
        self._log_step("步骤2: 检查已下载的视频...")
        target_filename = "youtuber_shorts_www.youtube.com.json"
        target_path = self.download_result_dir / target_filename
        self._log_step(f"检查下载记录文件: {target_path}", "INFO")
        
        downloaded_urls = self.get_downloaded_urls()
        
        if downloaded_urls:
            self._log_step(f"✅ 从下载记录文件中找到 {len(downloaded_urls)} 个已下载的视频", "SUCCESS")
        else:
            self._log_step("ℹ️  未找到已下载的视频记录（可能是首次下载）", "INFO")
        
        # 步骤3: 过滤掉已下载的视频
        self._log_step("步骤3: 过滤已下载的视频...")
        videos_to_download = []
        skipped_videos = []
        skipped_count = 0
        
        for video in videos:
            url = video.get('url', '')
            if not url:
                # 如果没有URL，也跳过
                skipped_count += 1
                continue
            
            if url in downloaded_urls:
                skipped_count += 1
                skipped_videos.append(video)
            else:
                videos_to_download.append(video)
        
        # 显示过滤结果
        if skipped_count > 0:
            self._log_step(f"✅ 已过滤 {skipped_count} 个已下载的视频（将跳过）", "SUCCESS")
            # 显示前5个被跳过的视频标题（用于确认）
            if skipped_videos:
                self._log_step("跳过的视频示例（前5个）:", "INFO")
                for i, video in enumerate(skipped_videos[:5], 1):
                    title = video.get('title', 'N/A')[:50]
                    self._log_step(f"  {i}. {title}...", "INFO")
                if len(skipped_videos) > 5:
                    self._log_step(f"  ... 还有 {len(skipped_videos) - 5} 个已下载的视频", "INFO")
        
        if not videos_to_download:
            self._log_step("=" * 80)
            self._log_step("✅ 所有视频都已下载，无需重复下载", "SUCCESS")
            self._log_step(f"   总视频数: {len(videos)}")
            self._log_step(f"   已下载: {skipped_count}")
            self._log_step(f"   需要下载: 0")
            self._log_step("=" * 80)
            return []
        
        self._log_step(f"✅ 需要下载 {len(videos_to_download)} 个新视频", "SUCCESS")
        self._log_step(f"   总视频数: {len(videos)}")
        self._log_step(f"   已下载: {skipped_count}")
        self._log_step(f"   待下载: {len(videos_to_download)}")
        
        # 批量下载
        downloaded_videos = self.download_videos(videos_to_download, delay)
        
        # 只保存成功下载的视频（download_status == "success"）
        success_videos = [v for v in downloaded_videos if v.get('download_status') == 'success']
        
        # 清理下载状态字段，保持与源文件格式一致
        for video in success_videos:
            # 移除 download_status 字段，保留其他字段（包括 download_time）
            video.pop('download_status', None)
        
        # 保存下载结果
        if success_videos:
            self.save_download_results(success_videos, file_path)
        
        return downloaded_videos


def download_shorts_from_file(date_str: Optional[str] = None, delay: float = 2.0) -> List[Dict]:
    """
    从 Shorts 结果文件读取并下载视频的便捷函数
    
    Args:
        date_str: 日期字符串（格式：yyyyMMdd），如果为 None 则使用最新的文件
        delay: 每个视频下载之间的延迟（秒），默认2秒
        
    Returns:
        已下载的视频信息列表
    """
    downloader = ShortsDownloader()
    return downloader.download_from_file(date_str, delay)


def main():
    """主函数"""
    # 检查是否是帮助请求（优先处理）
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("使用方法:")
        print("  python download_shorts.py [date] [delay]")
        print()
        print("参数:")
        print("  date:  日期字符串（格式：yyyyMMdd），可选，默认使用当天的文件")
        print("  delay: 下载间隔（秒），可选，默认2秒")
        print()
        print("说明:")
        print("  - 仅从 data/search_result 目录查找文件")
        print("  - 日期信息从文件名中提取（格式：yyyyMMdd_youtuber_shorts_www.youtube.com.json）")
        print("  - 如果不指定日期，自动使用今天的日期")
        print()
        print("示例:")
        print("  python download_shorts.py                    # 下载当天文件中的所有视频")
        print("  python download_shorts.py 20251230            # 下载指定日期的文件")
        print("  python download_shorts.py 20251230 5        # 下载指定日期文件，间隔5秒")
        return
    
    # 解析参数
    date_str = None
    delay = 2.0
    
    # 第一个参数：日期（可选）
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        if arg1.isdigit() and len(arg1) == 8:
            date_str = arg1
        else:
            print(f"⚠️  警告: 日期参数 '{arg1}' 格式不正确（应为 yyyyMMdd），将使用今天的日期")
    
    # 第二个参数：延迟（可选）
    if len(sys.argv) > 2:
        try:
            delay = float(sys.argv[2])
        except ValueError:
            print(f"⚠️  警告: 延迟参数 '{sys.argv[2]}' 无效，使用默认值 2.0 秒")
    
    try:
        print("=" * 80)
        print("📥 YouTube Shorts 批量下载")
        print("=" * 80)
        print()
        
        # 如果没有指定日期，显示将使用的日期
        if date_str is None:
            today = datetime.now().strftime("%Y%m%d")
            print(f"📅 未指定日期，将下载今天的视频信息（日期: {today}）")
        print()
        
        downloaded = download_shorts_from_file(date_str, delay)
        
        print()
        print("=" * 80)
        print(f"✅ 下载完成！成功下载 {len(downloaded)} 个视频")
        print("=" * 80)
        print(f"📁 下载结果已保存到: data/download_result/")
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

