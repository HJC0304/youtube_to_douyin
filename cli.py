"""
命令行工具 - 显示项目支持的所有功能和命令示例
"""
# ji
import argparse
import sys
from typing import Dict, List

from config.store_config.download_config import DEFAULT_VIDEO_DOWNLOAD_DIR


class CrawlerCLI:
    """爬虫项目命令行工具"""
    
    def __init__(self):
        self.features = self._init_features()
    
    def _init_features(self) -> Dict:
        """初始化功能列表"""
        return {
            "youtube_search": {
                "name": "YouTube 视频搜索",
                "description": "在 YouTube 上搜索视频，提取视频信息（标题、链接、观看次数、发布时间等）",
                "module": "youtube_crawler.search_video",
                "class": "YouTubeSearcher",
                "commands": [
                    {
                        "command": "python -m cli youtube search 'Python教程'",
                        "description": "搜索关键词并保存结果",
                        "options": {
                            "--headless": "无头模式运行（不显示浏览器）",
                            "--no-recent": "不点击'最近上传'按钮"
                        }
                    },
                    {
                        "command": "python -m cli youtube search '机器学习' --headless",
                        "description": "在后台搜索（无头模式）",
                    },
                    {
                        "command": "python -m cli youtube search '数据分析' --no-recent",
                        "description": "搜索但不筛选最近上传的视频",
                    }
                ],
                "python_example": """from youtube_crawler.search_video import YouTubeSearcher

with YouTubeSearcher(headless=False) as searcher:
    results = searcher.search_and_save("Python教程", click_recent_upload=True)
    for video in results:
        print(f"标题: {video['title']}")
        print(f"链接: {video['url']}")"""
            },
            "youtube_shorts": {
                "name": "YouTube Shorts 视频提取",
                "description": "从 YouTube 频道 Shorts 页面提取视频信息（URL、标题、播放次数），支持单个频道和批量处理（从 youtubers.json 读取配置，保存到 search_result 文件夹）",
                "module": "youtube_crawler.extract_shorts",
                "class": "YouTubeShortsExtractor",
                "commands": [
                    {
                        "command": "python -m cli youtube shorts 'https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts'",
                        "description": "提取指定频道的 Shorts 视频信息（默认提取20个）",
                        "options": {
                            "--headless": "无头模式运行（不显示浏览器）",
                            "--max": "最大提取视频数量（默认: 20）"
                        }
                    },
                    {
                        "command": "python -m cli youtube shorts 'https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts' --max 50",
                        "description": "提取50个视频",
                    },
                    {
                        "command": "python youtube_crawler/extract_shorts.py --all 20",
                        "description": "批量处理所有 YouTuber（从 data/youtubers/youtubers.json 读取），每个提取20个视频",
                    },
                    {
                        "command": "python youtube_crawler/extract_shorts.py --all 30",
                        "description": "批量处理所有 YouTuber，每个提取30个视频",
                    }
                ],
                "python_example": """from youtube_crawler.extract_shorts import extract_youtube_shorts, extract_all_youtubers_shorts

# 提取单个 YouTuber 的 Shorts 视频信息
videos = extract_youtube_shorts(
    "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts",
    max_videos=20,
    headless=False
)
for video in videos:
    print(f"标题: {video['title']}")
    print(f"URL: {video['url']}")
    print(f"播放次数: {video['view_count']}")

# 批量提取所有 YouTuber 的 Shorts 视频（从 youtubers.json 读取）
all_results = extract_all_youtubers_shorts(max_videos=20, headless=False)
for name, videos in all_results.items():
    print(f"{name}: {len(videos)} 个视频")"""
            },
            "deepseek_api": {
                "name": "DeepSeek API 调用",
                "description": "调用 DeepSeek AI API 进行智能对话、内容生成、代码编写等功能",
                "module": "deepseek.deepseek_api",
                "class": "call_deepseek_api",
                "commands": [
                    {
                        "command": "python -m cli deepseek chat '什么是人工智能？'",
                        "description": "调用 DeepSeek API 进行对话",
                        "options": {
                            "--model": "指定使用的模型（默认: deepseek-chat）",
                            "--temperature": "设置温度参数，控制输出随机性（0-1，默认: 0.7）",
                            "--max-tokens": "设置最大生成 token 数（默认: 2000）",
                            "--api-key": "直接指定 API Key（可选，优先使用配置文件）"
                        }
                    },
                    {
                        "command": "python -m cli deepseek chat '用Python写一个快速排序' --temperature 0.3",
                        "description": "使用较低温度生成代码（更确定）",
                    },
                    {
                        "command": "python -m cli deepseek chat '写一首关于春天的诗' --temperature 0.9 --max-tokens 500",
                        "description": "使用较高温度进行创意写作",
                    }
                ],
                "python_example": """from deepseek.deepseek_api import call_deepseek_api

# 基本调用（API Key 从配置文件或环境变量读取）
result = call_deepseek_api("请用一句话解释什么是人工智能")

# 自定义参数
result = call_deepseek_api(
    prompt="用 Python 写一个快速排序函数",
    temperature=0.3,  # 较低温度，输出更确定
    max_tokens=1000
)

# 直接指定 API Key
result = call_deepseek_api(
    "解释一下机器学习的基本概念",
    api_key="your-api-key-here"
)"""
            },
            "downie_download": {
                "name": "Downie 4 YouTube 视频下载",
                "description": "通过 macOS 应用 Downie 4 下载 YouTube 视频（自动打开应用并填充链接）",
                "module": "downie4.download_youtube",
                "class": "download_youtube_video",
                "commands": [
                    {
                        "command": "python -m cli downie download \"https://www.youtube.com/watch?v=VIDEO_ID\"",
                        "description": "使用 Downie 4 下载指定的 YouTube 视频链接",
                        "options": {}
                    }
                ],
                "python_example": """from downie4.download_youtube import download_youtube_video

url = "https://www.youtube.com/watch?v=VIDEO_ID"
download_youtube_video(url)  # 会自动打开 Downie 4 并填充链接"""
            },
            "youtube_shorts_download": {
                "name": "YouTube Shorts 批量下载",
                "description": "从 data/search_result 目录读取视频 URL，使用 Downie 4 批量下载，自动跳过已下载的视频，保存下载结果到 download_result 文件夹（文件名：youtuber_shorts_www.youtube.com.json）。默认下载当天的视频信息，日期从文件名中提取（格式：yyyyMMdd_youtuber_shorts_www.youtube.com.json）",
                "module": "youtube_crawler.download_shorts",
                "class": "ShortsDownloader",
                "commands": [
                    {
                        "command": "python youtube_crawler/download_shorts.py",
                        "description": "下载当天文件中的所有视频（默认间隔2秒，自动跳过已下载）",
                    },
                    {
                        "command": "python youtube_crawler/download_shorts.py 20251230",
                        "description": "下载指定日期的文件",
                    },
                    {
                        "command": "python youtube_crawler/download_shorts.py 20251230 5",
                        "description": "下载指定日期文件，间隔5秒",
                    }
                ],
                "python_example": """from youtube_crawler.download_shorts import download_shorts_from_file

# 下载最新文件中的所有视频
downloaded = download_shorts_from_file()

# 下载指定日期的文件，间隔3秒
downloaded = download_shorts_from_file(date_str="20251230", delay=3.0)

# 查看下载结果
for video in downloaded:
    if video.get('download_status') == 'success':
        print(f"✅ {video.get('video_filename', 'N/A')}")
    else:
        print(f"❌ {video.get('video_filename', 'N/A')}: {video.get('error', '未知错误')}")"""
            },
            "douyin_login": {
                "name": "抖音创作者平台登录",
                "description": "登录抖音创作者平台并保存登录信息（cookies），登录信息保存后，后续上传视频时会自动加载，无需重复登录",
                "module": "douyin.upload_video",
                "class": "DouyinUploader",
                "commands": [
                    {
                        "command": "python douyin/upload_video.py --login",
                        "description": "登录抖音创作者平台（默认等待60秒）",
                        "options": {
                            "wait_time": "等待登录的时间（秒，可选，默认60秒）"
                        }
                    },
                    {
                        "command": "python douyin/upload_video.py --login 120",
                        "description": "登录并等待120秒",
                    }
                ],
                "python_example": """from douyin.upload_video import login_douyin

# 登录（默认等待60秒）
success = login_douyin(login_url="https://creator.douyin.com/", wait_time=60, headless=False)

if success:
    print("登录成功！登录信息已保存")
else:
    print("登录失败或未完成")"""
            },
            "douyin_upload": {
                "name": "抖音创作者平台视频上传",
                "description": "使用 Playwright 自动化上传本地视频到抖音创作者平台，支持单个视频、批量上传（从文件夹）和智能上传（自动选择当天或指定日期播放量最多的已下载视频）。功能特性：1) 智能标题和话题生成（DeepSeek 元数据优先，回退文件名/标题提取）；2) 智能视频文件匹配（字符串规范化处理，去除不可见字符，统一空格类型，支持前缀匹配）；3) 自动封面选择（点击封面后自动确认）；4) 可见性设置（支持仅自己可见和公开）；5) 文件管理（上传成功后自动移动文件到 upload_douyin 文件夹）；6) 上传结果记录（保存到 upload_result/douyin 文件夹）；7) 支持指定日期上传（通过 --date 参数指定日期，格式：yyyyMMdd）",
                "module": "douyin.upload_video",
                "class": "DouyinUploader",
                "commands": [
                    {
                        "command": "python douyin/upload_video.py \"/path/to/video.mp4\"",
                        "description": "上传单个视频到抖音（默认：仅自己可见，不自动发布）",
                        "options": {
                            "title": "作品标题（可选，默认从文件名提取）",
                            "hashtags": "话题标签（可选，默认从标题提取）",
                            "cover_text": "封面文字（可选，默认使用标题）",
                            "visibility": "可见性（可选，默认'仅自己可见'，可选'公开'）",
                            "auto_publish": "是否自动发布（可选，默认False）"
                        }
                    },
                    {
                        "command": f"python douyin/upload_video.py --folder \"{DEFAULT_VIDEO_DOWNLOAD_DIR}\"",
                        "description": "批量上传文件夹中的所有视频（保持浏览器打开，依次上传）",
                        "options": {
                            "visibility": "可见性（可选，默认'仅自己可见'）",
                            "auto_publish": "是否自动发布（可选，默认False）",
                            "delay": "每个视频上传之间的延迟（秒，可选，默认5秒）"
                        }
                    },
                    {
                        "command": f"python douyin/upload_video.py --folder \"{DEFAULT_VIDEO_DOWNLOAD_DIR}\" \"公开\" true 10",
                        "description": "批量上传，设置为公开，自动发布，间隔10秒",
                    },
                    {
                        "command": "python douyin/upload_video.py --today",
                        "description": f"智能上传：自动读取当天搜索的视频和已下载的视频，选择播放量最多的2个视频进行上传。从 {DEFAULT_VIDEO_DOWNLOAD_DIR} 查找视频文件，上传成功后自动移动到 {DEFAULT_VIDEO_DOWNLOAD_DIR}/upload_douyin 文件夹",
                        "options": {
                            "visibility": "可见性（可选，默认'仅自己可见'，可选'公开'）",
                            "auto_publish": "是否自动发布（可选，默认False）",
                            "download_dir": f"下载目录路径（可选，可指定多个，默认搜索 {DEFAULT_VIDEO_DOWNLOAD_DIR}）"
                        }
                    },
                    {
                        "command": "python douyin/upload_video.py --today \"公开\" true",
                        "description": "智能上传，设置为公开，自动发布",
                    },
                    {
                        "command": f"python douyin/upload_video.py --today \"仅自己可见\" false \"{DEFAULT_VIDEO_DOWNLOAD_DIR}\"",
                        "description": "智能上传，指定下载目录",
                    },
                    {
                        "command": "python douyin/upload_video.py --today --date 20260108",
                        "description": "智能上传指定日期的视频（日期格式：yyyyMMdd，如 20260108 表示 2026年1月8日）",
                        "options": {
                            "--date 或 -d": "指定日期（格式：yyyyMMdd，如 20260108）",
                            "visibility": "可见性（可选，默认'公开'）",
                            "auto_publish": "是否自动发布（可选，默认False）",
                            "download_dir": "下载目录路径（可选）"
                        }
                    },
                    {
                        "command": "python douyin/upload_video.py --today -d 20260108 \"公开\" true",
                        "description": "上传指定日期的视频，设置为公开并自动发布",
                    },
                    {
                        "command": f"python douyin/upload_video.py --today --date 20260108 \"仅自己可见\" false \"{DEFAULT_VIDEO_DOWNLOAD_DIR}\"",
                        "description": "上传指定日期的视频，指定可见性和下载目录",
                    }
                ],
                "python_example": """from douyin.upload_video import DouyinUploader

# 单个视频上传
with DouyinUploader(headless=False) as uploader:
    result = uploader.upload_video(
        video_path="/path/to/video.mp4",
        title=None,  # 从文件名提取
        hashtags=None,  # 从标题提取
        cover_text=None,  # 使用标题
        visibility="仅自己可见",
        auto_publish=False
    )
    print(f"上传结果: {result['success']}")

# 批量上传（从文件夹）
with DouyinUploader(headless=False) as uploader:
    results = uploader.upload_videos_from_folder(
        folder_path=DEFAULT_VIDEO_DOWNLOAD_DIR,
        visibility="仅自己可见",
        auto_publish=False,
        delay=5.0
    )
    for result in results:
        if result.get('success'):
            print(f"✅ {result['video_filename']}")
        else:
            print(f"❌ {result['video_filename']}: {result.get('error', '未知错误')}")

# 智能上传（上传当天播放量最多的已下载视频）
with DouyinUploader(headless=False) as uploader:
    results = uploader.upload_top_videos_from_today(
        download_dirs=None,  # 使用默认目录（DEFAULT_VIDEO_DOWNLOAD_DIR）
        visibility="仅自己可见",
        auto_publish=False,
        max_videos=2  # 最多上传2个视频
    )
    for result in results:
        if result.get('success'):
            print(f"✅ {result.get('video_filename', 'N/A')}")
        else:
            print(f"❌ {result.get('video_filename', 'N/A')}: {result.get('error', '未知错误')}")

# 智能上传（上传指定日期播放量最多的已下载视频）
with DouyinUploader(headless=False) as uploader:
    results = uploader.upload_top_videos_from_today(
        download_dirs=None,  # 使用默认目录（DEFAULT_VIDEO_DOWNLOAD_DIR）
        visibility="公开",
        auto_publish=False,
        max_videos=2,  # 最多上传2个视频
        target_date="20260108"  # 指定日期（格式：yyyyMMdd，如 20260108 表示 2026年1月8日）
    )
    for result in results:
        if result.get('success'):
            print(f"✅ {result.get('video_filename', 'N/A')}")
        else:
            print(f"❌ {result.get('video_filename', 'N/A')}: {result.get('error', '未知错误')}")"""
            },
            "vpn_privadovpn": {
                "name": "PrivadoVPN 应用管理",
                "description": "打开和关闭 PrivadoVPN 应用程序，支持自动点击连接按钮，支持检查应用是否已在运行",
                "module": "vpn.open_privadovpn",
                "class": "open_privadovpn",
                "commands": [
                    {
                        "command": "python vpn/open_privadovpn.py",
                        "description": "打开 PrivadoVPN 应用程序并自动点击连接按钮",
                    },
                    {
                        "command": "python vpn/open_privadovpn.py --close",
                        "description": "关闭 PrivadoVPN 应用程序",
                    },
                    {
                        "command": "python -m cli vpn open",
                        "description": "通过 CLI 打开 PrivadoVPN 并自动连接",
                    },
                    {
                        "command": "python -m cli vpn close",
                        "description": "通过 CLI 关闭 PrivadoVPN",
                    }
                ],
                "python_example": """from vpn.open_privadovpn import (
    open_and_connect_privadovpn, 
    open_privadovpn, 
    check_privadovpn_running, 
    click_connect_button,
    close_privadovpn
)

# 打开 PrivadoVPN 并自动连接（推荐）
success = open_and_connect_privadovpn()
if success:
    print("✅ PrivadoVPN 已打开并尝试连接")

# 仅打开应用（不连接）
success = open_privadovpn()
if success:
    print("✅ PrivadoVPN 已打开")
    # 手动点击连接按钮
    click_connect_button()

# 检查是否正在运行
if check_privadovpn_running():
    print("✅ PrivadoVPN 正在运行中")
else:
    print("❌ PrivadoVPN 未运行")

# 关闭 PrivadoVPN
success = close_privadovpn()
if success:
    print("✅ PrivadoVPN 已关闭")"""
            },
            "workflow_auto": {
                "name": "自动化工作流",
                "description": "完整的自动化工作流：整合 VPN、视频提取、下载和上传功能，实现从视频提取到上传的完整自动化流程。支持灵活的步骤控制：可跳过指定步骤或只执行部分步骤。智能特性：自动去重、智能上传选择（时间优先级和播放量优先级）、如果所有视频已下载则自动跳过下载检测步骤。步骤说明：1) 打开VPN（等待60秒），2) 提取视频（从 youtubers.json 读取），3) 下载视频（自动去重），4) 检测下载完成（如果所有视频已下载则自动跳过），5) 关闭VPN，6) 上传视频（智能选择）",
                "module": "workflow.auto_workflow",
                "class": "AutoWorkflow",
                "commands": [
                    {
                        "command": "python -m cli workflow",
                        "description": "执行完整自动化工作流（默认：每个YouTuber提取1个视频，上传2个视频）",
                        "options": {
                            "--max-videos-per-youtuber": "每个 YouTuber 提取的视频数量（默认: 1）",
                            "--max-upload-videos": "上传的视频数量（默认: 2）",
                            "--skip-steps": "要跳过的步骤编号，用逗号分隔（例如: 1,5）",
                            "--only-steps": "只执行的步骤编号，用逗号分隔（例如: 2,3,4）。如果指定了此参数，--skip-steps 将被忽略"
                        }
                    },
                    {
                        "command": "python -m cli workflow --max-videos-per-youtuber 5 --max-upload-videos 3",
                        "description": "自定义参数执行工作流",
                    },
                    {
                        "command": "python -m cli workflow --skip-steps 1,5",
                        "description": "跳过步骤1（打开VPN）和步骤5（关闭VPN）",
                    },
                    {
                        "command": "python -m cli workflow --only-steps 2,3,4",
                        "description": "只执行步骤2（提取视频）、步骤3（下载视频）、步骤4（检测下载完成）",
                    },
                    {
                        "command": "python -m cli workflow --only-steps 6",
                        "description": "只执行步骤6（上传视频）",
                    },
                    {
                        "command": "python workflow/auto_workflow.py",
                        "description": "直接运行工作流脚本（支持所有参数）",
                    },
                    {
                        "command": "python workflow/auto_workflow.py --skip-steps 1,5",
                        "description": "直接运行脚本，跳过VPN相关步骤",
                    }
                ],
                "python_example": """from workflow.auto_workflow import AutoWorkflow

# 创建并运行工作流（执行所有步骤）
workflow = AutoWorkflow()
success = workflow.run(
    max_videos_per_youtuber=1,  # 每个 YouTuber 提取1个最新视频
    max_upload_videos=2          # 上传播放量最多的2个视频
)

# 跳过指定步骤
success = workflow.run(
    max_videos_per_youtuber=1,
    max_upload_videos=2,
    skip_steps=[1, 5]  # 跳过步骤1（打开VPN）和步骤5（关闭VPN）
)

# 只执行部分步骤
success = workflow.run(
    max_videos_per_youtuber=1,
    max_upload_videos=2,
    only_steps=[2, 3, 4]  # 只执行步骤2、3、4（提取、下载、检测下载完成）
)

if success:
    print("✅ 工作流执行完成")
else:
    print("❌ 工作流执行失败")"""
            }
        }
    
    def show_all_features(self):
        """显示所有支持的功能"""
        print("=" * 80)
        print("🎯 项目支持的所有功能")
        print("=" * 80)
        print()
        
        for feature_id, feature in self.features.items():
            print(f"📦 {feature['name']}")
            print(f"   {feature['description']}")
            print()
            print("   🔧 命令行使用:")
            for cmd_info in feature['commands']:
                print(f"      $ {cmd_info['command']}")
                print(f"        → {cmd_info['description']}")
                if 'options' in cmd_info:
                    for opt, desc in cmd_info['options'].items():
                        print(f"          {opt}: {desc}")
                print()
            print("-" * 80)
            print()
    
    def show_feature_detail(self, feature_id: str):
        """显示特定功能的详细信息"""
        if feature_id not in self.features:
            print(f"❌ 错误: 未找到功能 '{feature_id}'")
            print(f"可用功能: {', '.join(self.features.keys())}")
            return
        
        feature = self.features[feature_id]
        print("=" * 80)
        print(f"📦 {feature['name']}")
        print("=" * 80)
        print()
        print(f"📝 功能描述:")
        print(f"   {feature['description']}")
        print()
        print(f"🔧 命令行使用:")
        for i, cmd_info in enumerate(feature['commands'], 1):
            print(f"   {i}. {cmd_info['command']}")
            print(f"      {cmd_info['description']}")
            if 'options' in cmd_info:
                print(f"      选项:")
                for opt, desc in cmd_info['options'].items():
                    print(f"        {opt}: {desc}")
            print()
        print(f"📚 模块路径: {feature['module']}")
        if 'class' in feature:
            print(f"📚 类/函数名: {feature['class']}")
        print()
    
    def execute_youtube_search(self, query: str, headless: bool = False, 
                                click_recent: bool = True):
        """执行 YouTube 搜索"""
        try:
            from youtube_crawler.search_video import YouTubeSearcher
            
            print(f"🔍 开始搜索: {query}")
            print(f"   模式: {'无头模式' if headless else '正常模式'}")
            print(f"   筛选最近上传: {'是' if click_recent else '否'}")
            print()
            
            with YouTubeSearcher(headless=headless) as searcher:
                results = searcher.search_and_save(query, click_recent_upload=click_recent)
                
                print(f"✅ 搜索完成！找到 {len(results)} 个视频")
                print()
                print("📊 搜索结果:")
                print("-" * 80)
                
                for i, video in enumerate(results[:10], 1):  # 只显示前10个
                    print(f"\n{i}. {video['title']}")
                    print(f"   类型: {'竖屏视频(SHORTS)' if video['is_shorts'] else '普通视频'}")
                    print(f"   观看次数: {video['view_count']}")
                    print(f"   发布时间: {video['publish_time']}")
                    print(f"   链接: {video['url']}")
                
                if len(results) > 10:
                    print(f"\n... 还有 {len(results) - 10} 个结果，请查看保存的文件")
                
                print()
                print(f"💾 结果已保存到: data/search_result/.youtube_video_info.json")
                
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_deepseek_api(self, prompt: str, api_key: str = None,
                             model: str = "deepseek-chat",
                             temperature: float = 0.7,
                             max_tokens: int = 2000):
        """执行 DeepSeek API 调用"""
        try:
            from deepseek.deepseek_api import call_deepseek_api
            
            print(f"🤖 调用 DeepSeek API")
            print(f"   提示词: {prompt}")
            print(f"   模型: {model}")
            print(f"   温度: {temperature}")
            print(f"   最大 tokens: {max_tokens}")
            print()
            
            result = call_deepseek_api(
                prompt=prompt,
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if result:
                print()
                print("✅ API 调用成功")
            else:
                print()
                print("❌ API 调用失败，请检查错误信息")
                
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_downie_download(self, url: str):
        """执行 Downie 4 YouTube 视频下载"""
        try:
            from downie4.download_youtube import download_youtube_video
            
            print(f"📥 使用 Downie 4 下载视频")
            print(f"   URL: {url}")
            print()
            
            success = download_youtube_video(url)
            if success:
                print("✅ 已在 Downie 4 中创建下载任务")
            else:
                print("❌ 创建下载任务失败，请检查 Downie 4 是否已安装并重试")
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_douyin_upload(self, video_path: str, headless: bool = False):
        """执行抖音视频上传"""
        try:
            from douyin.upload_video import upload_video
            
            print(f"📤 上传本地视频到抖音创作者平台")
            print(f"   视频文件: {video_path}")
            print(f"   模式: {'无头模式' if headless else '正常模式'}")
            print()
            
            upload_video(video_path, headless=headless)
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_youtube_shorts(self, shorts_url: str, max_videos: int = 20, headless: bool = False):
        """执行 YouTube Shorts 视频提取"""
        try:
            from youtube_crawler.extract_shorts import extract_youtube_shorts
            
            print(f"📹 提取 YouTube Shorts 视频信息")
            print(f"   URL: {shorts_url}")
            print(f"   最大提取数量: {max_videos}")
            print(f"   模式: {'无头模式' if headless else '正常模式'}")
            print()
            
            videos = extract_youtube_shorts(shorts_url, max_videos=max_videos, headless=headless)
            
            print(f"✅ 提取完成！找到 {len(videos)} 个视频")
            print()
            print("📊 提取结果:")
            print("-" * 80)
            
            for i, video in enumerate(videos[:10], 1):  # 只显示前10个
                print(f"\n{i}. {video.get('title', 'N/A')}")
                print(f"   URL: {video.get('url', 'N/A')}")
                print(f"   播放次数: {video.get('view_count', 'N/A')}")
            
            if len(videos) > 10:
                print(f"\n... 还有 {len(videos) - 10} 个结果，请查看保存的文件")
            
            print()
            print(f"💾 结果已保存到: data/search_result/")
            
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_vpn_open(self):
        """执行打开 PrivadoVPN 应用并连接"""
        try:
            from vpn.open_privadovpn import open_and_connect_privadovpn
            
            print(f"🔐 打开 PrivadoVPN 应用程序并连接")
            print()
            
            # 打开应用并点击连接按钮
            success = open_and_connect_privadovpn()
            
            if success:
                print()
                print("✅ PrivadoVPN 已成功打开并尝试连接")
            else:
                print()
                print("⚠️  打开 PrivadoVPN 成功，但连接按钮可能未找到")
                print("请手动点击连接按钮")
                
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_vpn_close(self):
        """执行关闭 PrivadoVPN 应用"""
        try:
            from vpn.open_privadovpn import close_privadovpn
            
            print(f"🔐 关闭 PrivadoVPN 应用程序")
            print()
            
            # 关闭应用
            success = close_privadovpn()
            
            if success:
                print()
                print("✅ PrivadoVPN 已成功关闭")
            else:
                print()
                print("⚠️  关闭 PrivadoVPN 时出现问题")
                print("请手动关闭应用")
                
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def execute_workflow(self, max_videos_per_youtuber: int = 1, max_upload_videos: int = 2,
                        skip_steps: list = None, only_steps: list = None):
        """执行自动化工作流"""
        try:
            from workflow.auto_workflow import AutoWorkflow
            
            print(f"🚀 启动自动化工作流")
            print(f"   每个 YouTuber 提取视频数: {max_videos_per_youtuber}")
            print(f"   上传视频数: {max_upload_videos}")
            if skip_steps:
                print(f"   跳过步骤: {skip_steps}")
            if only_steps:
                print(f"   只执行步骤: {only_steps}")
            print()
            
            workflow = AutoWorkflow()
            success = workflow.run(
                max_videos_per_youtuber=max_videos_per_youtuber,
                max_upload_videos=max_upload_videos,
                skip_steps=skip_steps,
                only_steps=only_steps
            )
            
            if success:
                print()
                print("✅ 工作流执行完成")
            else:
                print()
                print("⚠️  工作流执行过程中出现问题")
            
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("请确保已安装所有依赖: pip install -r requirements.txt")
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🎯 爬虫项目命令行工具

用法:
    python -m cli <command> [options]
    或
    python main.py list          # 显示所有功能

可用命令:
    list                            显示所有支持的功能
    info <feature>                  显示特定功能的详细信息
    youtube search <query>         执行 YouTube 视频搜索
    youtube shorts <url>           提取 YouTube Shorts 视频信息
    deepseek chat <prompt>         调用 DeepSeek API 进行对话
    downie download <youtube_url>  使用 Downie 4 下载 YouTube 视频
    douyin upload <video_path>     上传本地视频到抖音创作者平台
    vpn open                        打开 PrivadoVPN 应用程序并连接
    vpn close                       关闭 PrivadoVPN 应用程序
    workflow                        执行自动化工作流（提取、下载、上传）

功能列表:
    1. YouTube 视频搜索 - 搜索并提取视频信息，支持过滤和排序
    2. YouTube Shorts 视频提取 - 单个频道或批量提取（从 youtubers.json 读取）
    3. YouTube Shorts 批量下载 - 从搜索结果批量下载视频到本地
    4. Downie 4 YouTube 视频下载 - 使用 macOS Downie 4 下载单个视频
    5. 抖音创作者平台登录 - 登录并保存登录信息
    6. 抖音创作者平台视频上传 - 单个或批量上传视频
    7. DeepSeek API 调用 - AI 对话和内容生成
    8. PrivadoVPN 应用打开 - 打开 PrivadoVPN 应用程序

示例:
    # 显示所有功能
    python main.py list
    python -m cli list
    
    # 查看功能详情
    python -m cli info youtube_search
    python -m cli info youtube_shorts
    python -m cli info youtube_shorts_download
    python -m cli info douyin_upload
    python -m cli info deepseek_api
    
    # YouTube 搜索
    python -m cli youtube search "Python教程"
    python -m cli youtube search "机器学习" --headless
    python -m cli youtube search "数据分析" --no-recent
    
    # YouTube Shorts 提取
    python -m cli youtube shorts "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts"
    python -m cli youtube shorts "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts" --max 50
    python youtube_crawler/extract_shorts.py --all 20  # 批量处理所有 YouTuber
    
    # YouTube Shorts 批量下载
    python youtube_crawler/download_shorts.py  # 下载最新文件
    python youtube_crawler/download_shorts.py 20251230  # 下载指定日期
    python youtube_crawler/download_shorts.py 20251230 5  # 指定日期和间隔
    
    # Downie 4 下载
    python -m cli downie download "https://www.youtube.com/watch?v=VIDEO_ID"
    
    # 抖音登录
    python douyin/upload_video.py --login
    python douyin/upload_video.py --login 120  # 等待120秒
    
    # 抖音上传
    python douyin/upload_video.py "/path/to/video.mp4"
    python douyin/upload_video.py --folder "/path/to/folder"  # 批量上传
    python douyin/upload_video.py --folder "/path/to/folder" "公开" true 10  # 批量上传，公开，自动发布，间隔10秒
    python douyin/upload_video.py --today  # 智能上传：自动选择当天播放量最多的2个已下载视频
    python douyin/upload_video.py --today "公开" true  # 智能上传，公开，自动发布
    
    # DeepSeek API
    python -m cli deepseek chat "什么是人工智能？"
    python -m cli deepseek chat "写一首诗" --temperature 0.9 --max-tokens 500
    
    # PrivadoVPN
    python -m cli vpn open          # 打开并连接
    python -m cli vpn close         # 关闭
    python vpn/open_privadovpn.py   # 打开并连接
    python vpn/open_privadovpn.py --close  # 关闭
    
    # 自动化工作流
    python -m cli workflow                              # 默认：每个YouTuber提取1个视频，上传2个
    python -m cli workflow --max-videos-per-youtuber 5 --max-upload-videos 3  # 自定义参数
    python workflow/auto_workflow.py                    # 直接运行脚本

更多信息:
    查看 README.md 获取详细文档
        """
        print(help_text)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="爬虫项目命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='显示所有支持的功能')
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示特定功能的详细信息')
    info_parser.add_argument('feature', help='功能ID (如: youtube_search)')
    
    # youtube search 命令
    youtube_parser = subparsers.add_parser('youtube', help='YouTube 相关功能')
    youtube_subparsers = youtube_parser.add_subparsers(dest='youtube_command')
    
    search_parser = youtube_subparsers.add_parser('search', help='搜索视频')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('--headless', action='store_true', 
                              help='无头模式运行（不显示浏览器）')
    search_parser.add_argument('--no-recent', action='store_true',
                              help='不点击"最近上传"按钮')
    
    shorts_parser = youtube_subparsers.add_parser('shorts', help='提取 Shorts 视频信息')
    shorts_parser.add_argument('url', help='Shorts 页面 URL (如: https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts)')
    shorts_parser.add_argument('--headless', action='store_true',
                              help='无头模式运行（不显示浏览器）')
    shorts_parser.add_argument('--max', type=int, default=20,
                              help='最大提取视频数量（默认: 20）')
    
    # deepseek chat 命令
    deepseek_parser = subparsers.add_parser('deepseek', help='DeepSeek API 相关功能')
    deepseek_subparsers = deepseek_parser.add_subparsers(dest='deepseek_command')
    
    chat_parser = deepseek_subparsers.add_parser('chat', help='调用 DeepSeek API 进行对话')
    chat_parser.add_argument('prompt', help='输入的提示词')
    chat_parser.add_argument('--model', default='deepseek-chat',
                            help='使用的模型（默认: deepseek-chat）')
    chat_parser.add_argument('--temperature', type=float, default=0.7,
                            help='温度参数，控制输出随机性（0-1，默认: 0.7）')
    chat_parser.add_argument('--max-tokens', type=int, default=2000,
                            help='最大生成 token 数（默认: 2000）')
    chat_parser.add_argument('--api-key', default=None,
                            help='API Key（可选，优先使用配置文件）')
    
    # downie download 命令
    downie_parser = subparsers.add_parser('downie', help='Downie 4 视频下载相关功能')
    downie_subparsers = downie_parser.add_subparsers(dest='downie_command')
    
    downie_download_parser = downie_subparsers.add_parser('download', help='使用 Downie 4 下载 YouTube 视频')
    downie_download_parser.add_argument('url', help='YouTube 视频 URL')
    
    # douyin upload 命令
    douyin_parser = subparsers.add_parser('douyin', help='抖音视频上传相关功能')
    douyin_subparsers = douyin_parser.add_subparsers(dest='douyin_command')
    
    douyin_upload_parser = douyin_subparsers.add_parser('upload', help='上传本地视频到抖音创作者平台')
    douyin_upload_parser.add_argument('video_path', help='本地视频文件路径')
    douyin_upload_parser.add_argument('--headless', action='store_true',
                                      help='无头模式运行（不显示浏览器）')
    
    # vpn 命令
    vpn_parser = subparsers.add_parser('vpn', help='VPN 应用相关功能')
    vpn_subparsers = vpn_parser.add_subparsers(dest='vpn_command')
    
    vpn_open_parser = vpn_subparsers.add_parser('open', help='打开 PrivadoVPN 应用程序')
    vpn_close_parser = vpn_subparsers.add_parser('close', help='关闭 PrivadoVPN 应用程序')
    
    # workflow 命令
    workflow_parser = subparsers.add_parser('workflow', help='自动化工作流')
    workflow_parser.add_argument('--max-videos-per-youtuber', type=int, default=1,
                                help='每个 YouTuber 提取的视频数量（默认: 1）')
    workflow_parser.add_argument('--max-upload-videos', type=int, default=2,
                                help='上传的视频数量（默认: 2）')
    workflow_parser.add_argument('--skip-steps', type=str, default=None,
                                help='要跳过的步骤编号，用逗号分隔（例如: 1,5 表示跳过步骤1和步骤5）')
    workflow_parser.add_argument('--only-steps', type=str, default=None,
                                help='只执行的步骤编号，用逗号分隔（例如: 2,3,4）。如果指定了此参数，--skip-steps 将被忽略')
    
    args = parser.parse_args()
    
    cli = CrawlerCLI()
    
    if not args.command:
        cli.show_help()
        return
    
    if args.command == 'list':
        cli.show_all_features()
    elif args.command == 'info':
        if args.feature:
            cli.show_feature_detail(args.feature)
        else:
            print("❌ 错误: 请指定功能ID")
            print(f"可用功能: {', '.join(cli.features.keys())}")
    elif args.command == 'youtube':
        if args.youtube_command == 'search':
            click_recent = not args.no_recent
            cli.execute_youtube_search(args.query, args.headless, click_recent)
        elif args.youtube_command == 'shorts':
            cli.execute_youtube_shorts(args.url, args.max, args.headless)
        else:
            print("❌ 错误: 请指定 YouTube 子命令")
            print("可用命令: search, shorts")
    elif args.command == 'deepseek':
        if args.deepseek_command == 'chat':
            cli.execute_deepseek_api(
                prompt=args.prompt,
                api_key=args.api_key,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens
            )
        else:
            print("❌ 错误: 请指定 DeepSeek 子命令")
            print("可用命令: chat")
    elif args.command == 'downie':
        if args.downie_command == 'download':
            cli.execute_downie_download(args.url)
        else:
            print("❌ 错误: 请指定 Downie 子命令")
            print("可用命令: download")
    elif args.command == 'douyin':
        if args.douyin_command == 'upload':
            cli.execute_douyin_upload(args.video_path, headless=args.headless)
        else:
            print("❌ 错误: 请指定 Douyin 子命令")
            print("可用命令: upload")
    elif args.command == 'vpn':
        if args.vpn_command == 'open':
            cli.execute_vpn_open()
        elif args.vpn_command == 'close':
            cli.execute_vpn_close()
        else:
            print("❌ 错误: 请指定 VPN 子命令")
            print("可用命令: open, close")
    elif args.command == 'workflow':
        # 解析步骤参数
        skip_steps = None
        if args.skip_steps:
            try:
                skip_steps = [int(s.strip()) for s in args.skip_steps.split(',')]
                invalid_steps = [s for s in skip_steps if s < 1 or s > 6]
                if invalid_steps:
                    print(f"❌ 错误: 无效的步骤编号: {invalid_steps}。步骤编号必须在 1-6 之间")
                    return
            except ValueError:
                print(f"❌ 错误: 无效的步骤编号格式: {args.skip_steps}。请使用逗号分隔的数字，例如: 1,5")
                return
        
        only_steps = None
        if args.only_steps:
            try:
                only_steps = [int(s.strip()) for s in args.only_steps.split(',')]
                invalid_steps = [s for s in only_steps if s < 1 or s > 6]
                if invalid_steps:
                    print(f"❌ 错误: 无效的步骤编号: {invalid_steps}。步骤编号必须在 1-6 之间")
                    return
            except ValueError:
                print(f"❌ 错误: 无效的步骤编号格式: {args.only_steps}。请使用逗号分隔的数字，例如: 2,3,4")
                return
        
        cli.execute_workflow(
            max_videos_per_youtuber=args.max_videos_per_youtuber,
            max_upload_videos=args.max_upload_videos,
            skip_steps=skip_steps,
            only_steps=only_steps
        )
    else:
        cli.show_help()


if __name__ == '__main__':
    main()

