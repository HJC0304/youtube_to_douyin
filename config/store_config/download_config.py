"""
下载与上传归档目录配置。

统一维护项目里与本地视频存储相关的默认目录，避免在业务代码中散落硬编码路径。
修改 DEFAULT_VIDEO_DOWNLOAD_DIR 即可切换本机视频存储目录。
"""

from pathlib import Path


# 默认的视频下载目录（支持 ~ 展开）
DEFAULT_VIDEO_DOWNLOAD_DIR = "~/Downloads/downie4"


def get_default_video_download_dir() -> Path:
    """返回默认视频下载目录。"""
    return Path(DEFAULT_VIDEO_DOWNLOAD_DIR).expanduser()


def get_uploaded_video_archive_dir() -> Path:
    """返回上传成功后的归档目录。"""
    return get_default_video_download_dir() / "upload_douyin"
