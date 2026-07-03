"""
YouTube视频过滤配置
支持多种过滤条件，用于筛选搜索结果
"""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

# ============================================================================
# 过滤条件配置（在文件开头，方便设置默认值）
# ============================================================================

# 总开关：是否启用所有过滤（默认：False - 不启用）
FILTER_ENABLED = True

# 1. 横屏/竖屏过滤配置
ORIENTATION_FILTER = {
    'enabled': False,  # 是否启用此过滤（默认：False - 不过滤）
    'allowed': []  # 允许的方向列表，如 ["横屏", "竖屏"] 或 ["横屏"] 或 ["竖屏"]
}

# 2. 视频时长过滤配置
DURATION_FILTER = {
    'enabled': False,  # 是否启用此过滤（默认：False - 不过滤）
    'min_seconds': None,  # 最小时长（秒），如 60 表示至少1分钟
    'max_seconds': None   # 最大时长（秒），如 600 表示最多10分钟
}

# 3. 分辨率过滤配置
RESOLUTION_FILTER = {
    'enabled': False,  # 是否启用此过滤（默认：False - 不过滤）
    'allowed': []  # 允许的分辨率列表，如 ["1080p", "4K", "HD", "720p"]
}

# 4. 播放量过滤配置
VIEW_COUNT_FILTER = {
    'enabled': False,  # 是否启用此过滤（默认：False - 不过滤）
    'min_views': None,  # 最小播放量，如 10000 表示至少1万播放量
    'max_views': None   # 最大播放量，如 1000000 表示最多100万播放量
}

# 5. 发布天数过滤配置
PUBLISH_TIME_FILTER = {
    'enabled': False,  # 是否启用此过滤（默认：False - 不过滤）
    'max_days': None  # 最大发布天数，如 7 表示只保留7天内发布的视频
}

# 6. 标题包含搜索词过滤配置
TITLE_CONTAINS_FILTER = {
    'enabled': True,  # 是否启用此过滤（默认：False - 不过滤）
    'require_all': True  # True: 标题必须包含所有搜索词; False: 包含任意一个即可
}

# ============================================================================
# 使用示例（取消注释以启用）
# ============================================================================
# FILTER_ENABLED = True
# 
# # 只保留横屏视频
# ORIENTATION_FILTER = {
#     'enabled': True,
#     'allowed': ["横屏"]
# }
# 
# # 只保留1-10分钟的视频
# DURATION_FILTER = {
#     'enabled': True,
#     'min_seconds': 60,   # 1分钟
#     'max_seconds': 600  # 10分钟
# }
# 
# # 只保留1080p或4K视频
# RESOLUTION_FILTER = {
#     'enabled': True,
#     'allowed': ["1080p", "4K"]
# }
# 
# # 只保留至少1万播放量的视频
# VIEW_COUNT_FILTER = {
#     'enabled': True,
#     'min_views': 10000
# }
# 
# # 只保留7天内发布的视频
# PUBLISH_TIME_FILTER = {
#     'enabled': True,
#     'max_days': 7
# }
# 
# # 标题必须包含所有搜索词
# TITLE_CONTAINS_FILTER = {
#     'enabled': True,
#     'require_all': True
# }


class YouTubeVideoFilter:
    """YouTube视频过滤器"""
    
    def __init__(self):
        """初始化过滤器，从文件开头的配置读取默认值"""
        # 总开关：是否启用所有过滤
        self.enabled = FILTER_ENABLED
        
        # 1. 横屏/竖屏过滤
        self.orientation_filter = ORIENTATION_FILTER.copy()
        
        # 2. 视频时长过滤
        self.duration_filter = DURATION_FILTER.copy()
        
        # 3. 分辨率过滤
        self.resolution_filter = RESOLUTION_FILTER.copy()
        
        # 4. 播放量过滤
        self.view_count_filter = VIEW_COUNT_FILTER.copy()
        
        # 5. 发布天数过滤
        self.publish_time_filter = PUBLISH_TIME_FILTER.copy()
        
        # 6. 标题包含搜索词过滤
        self.title_contains_filter = TITLE_CONTAINS_FILTER.copy()
    
    def set_orientation_filter(self, enabled: bool, allowed: List[str] = None):
        """
        设置横屏/竖屏过滤
        
        Args:
            enabled: 是否启用
            allowed: 允许的方向列表，如 ["横屏", "竖屏"]
        """
        self.orientation_filter['enabled'] = enabled
        if allowed:
            self.orientation_filter['allowed'] = allowed
    
    def set_duration_filter(self, enabled: bool, min_seconds: Optional[int] = None, 
                           max_seconds: Optional[int] = None):
        """
        设置视频时长过滤
        
        Args:
            enabled: 是否启用
            min_seconds: 最小时长（秒）
            max_seconds: 最大时长（秒）
        """
        self.duration_filter['enabled'] = enabled
        self.duration_filter['min_seconds'] = min_seconds
        self.duration_filter['max_seconds'] = max_seconds
    
    def set_resolution_filter(self, enabled: bool, allowed: List[str] = None):
        """
        设置分辨率过滤
        
        Args:
            enabled: 是否启用
            allowed: 允许的分辨率列表，如 ["1080p", "4K", "HD"]
        """
        self.resolution_filter['enabled'] = enabled
        if allowed:
            self.resolution_filter['allowed'] = allowed
    
    def set_view_count_filter(self, enabled: bool, min_views: Optional[int] = None,
                             max_views: Optional[int] = None):
        """
        设置播放量过滤
        
        Args:
            enabled: 是否启用
            min_views: 最小播放量
            max_views: 最大播放量
        """
        self.view_count_filter['enabled'] = enabled
        self.view_count_filter['min_views'] = min_views
        self.view_count_filter['max_views'] = max_views
    
    def set_publish_time_filter(self, enabled: bool, max_days: Optional[int] = None):
        """
        设置发布天数过滤
        
        Args:
            enabled: 是否启用
            max_days: 最大发布天数（如7表示只保留7天内发布的视频）
        """
        self.publish_time_filter['enabled'] = enabled
        self.publish_time_filter['max_days'] = max_days
    
    def set_title_contains_filter(self, enabled: bool, require_all: bool = True):
        """
        设置标题包含搜索词过滤
        
        Args:
            enabled: 是否启用
            require_all: True表示标题必须包含所有搜索词，False表示包含任意一个即可
        """
        self.title_contains_filter['enabled'] = enabled
        self.title_contains_filter['require_all'] = require_all
    
    def _parse_duration(self, duration_str: str) -> Optional[int]:
        """
        解析时长字符串为秒数
        
        Args:
            duration_str: 时长字符串，如 "10:30" 或 "1:23:45"
            
        Returns:
            秒数，如果解析失败返回None
        """
        if not duration_str or duration_str == "未知":
            return None
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:
                # 格式: MM:SS
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # 格式: HH:MM:SS
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError):
            pass
        return None
    
    def _parse_view_count(self, view_count_str: str) -> Optional[int]:
        """
        解析播放量字符串为数字
        
        Args:
            view_count_str: 播放量字符串，如 "5万次观看", "1.9万次观看", "1000次观看"
            
        Returns:
            播放量数字，如果解析失败返回None
        """
        if not view_count_str or view_count_str == "未知":
            return None
        
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
        return None
    
    def _parse_publish_days(self, publish_time_str: str) -> Optional[int]:
        """
        解析发布时间字符串为天数
        
        Args:
            publish_time_str: 发布时间字符串，如 "22小时前", "1天前", "1周前", "1个月前"
            
        Returns:
            天数，如果解析失败返回None
        """
        if not publish_time_str or publish_time_str == "未知":
            return None
        
        try:
            # 处理小时
            if '小时' in publish_time_str or 'hour' in publish_time_str.lower():
                match = re.search(r'(\d+)', publish_time_str)
                if match:
                    hours = int(match.group(1))
                    return hours / 24  # 转换为天数（小数）
            
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
        return None
    
    def _check_orientation(self, video: Dict) -> bool:
        """检查横屏/竖屏过滤"""
        if not self.orientation_filter['enabled']:
            return True
        
        orientation = video.get('orientation', '')
        allowed = self.orientation_filter['allowed']
        return orientation in allowed if allowed else True
    
    def _check_duration(self, video: Dict) -> bool:
        """检查视频时长过滤"""
        if not self.duration_filter['enabled']:
            return True
        
        duration_str = video.get('duration', '')
        duration_seconds = self._parse_duration(duration_str)
        
        if duration_seconds is None:
            return False  # 无法解析时长，过滤掉
        
        min_seconds = self.duration_filter['min_seconds']
        max_seconds = self.duration_filter['max_seconds']
        
        if min_seconds is not None and duration_seconds < min_seconds:
            return False
        if max_seconds is not None and duration_seconds > max_seconds:
            return False
        
        return True
    
    def _check_resolution(self, video: Dict) -> bool:
        """检查分辨率过滤"""
        if not self.resolution_filter['enabled']:
            return True
        
        resolution = video.get('resolution', '')
        if resolution == "未知":
            return False  # 未知分辨率，过滤掉
        
        allowed = self.resolution_filter['allowed']
        if not allowed:
            return True
        
        # 支持部分匹配（如 "1080p" 匹配 "1080p"）
        resolution_upper = resolution.upper()
        for allowed_res in allowed:
            if allowed_res.upper() in resolution_upper or resolution_upper in allowed_res.upper():
                return True
        
        return False
    
    def _check_view_count(self, video: Dict) -> bool:
        """检查播放量过滤"""
        if not self.view_count_filter['enabled']:
            return True
        
        view_count_str = video.get('view_count', '')
        view_count = self._parse_view_count(view_count_str)
        
        if view_count is None:
            return False  # 无法解析播放量，过滤掉
        
        min_views = self.view_count_filter['min_views']
        max_views = self.view_count_filter['max_views']
        
        if min_views is not None and view_count < min_views:
            return False
        if max_views is not None and view_count > max_views:
            return False
        
        return True
    
    def _check_publish_time(self, video: Dict) -> bool:
        """检查发布天数过滤"""
        if not self.publish_time_filter['enabled']:
            return True
        
        publish_time_str = video.get('publish_time', '')
        publish_days = self._parse_publish_days(publish_time_str)
        
        if publish_days is None:
            return False  # 无法解析发布时间，过滤掉
        
        max_days = self.publish_time_filter['max_days']
        if max_days is not None and publish_days > max_days:
            return False
        
        return True
    
    def _check_title_contains(self, video: Dict) -> bool:
        """检查标题是否包含搜索词"""
        if not self.title_contains_filter['enabled']:
            return True
        
        title = video.get('title', '').lower()
        search_query = video.get('search_query', '')
        
        if not search_query:
            return True  # 没有搜索词，不过滤
        
        # 将搜索词按空格分割
        search_words = search_query.lower().split()
        require_all = self.title_contains_filter['require_all']
        
        if require_all:
            # 标题必须包含所有搜索词
            return all(word in title for word in search_words)
        else:
            # 标题包含任意一个搜索词即可
            return any(word in title for word in search_words)
    
    def filter_videos(self, videos: List[Dict]) -> List[Dict]:
        """
        过滤视频列表
        
        Args:
            videos: 视频列表
            
        Returns:
            过滤后的视频列表
        """
        if not self.enabled:
            return videos
        
        filtered_videos = []
        for video in videos:
            # 依次检查所有过滤条件
            if not self._check_orientation(video):
                continue
            if not self._check_duration(video):
                continue
            if not self._check_resolution(video):
                continue
            if not self._check_view_count(video):
                continue
            if not self._check_publish_time(video):
                continue
            if not self._check_title_contains(video):
                continue
            
            # 通过所有过滤条件
            filtered_videos.append(video)
        
        return filtered_videos
    
    def get_filter_summary(self) -> Dict:
        """
        获取过滤配置摘要
        
        Returns:
            过滤配置字典
        """
        return {
            'enabled': self.enabled,
            'orientation_filter': self.orientation_filter,
            'duration_filter': self.duration_filter,
            'resolution_filter': self.resolution_filter,
            'view_count_filter': self.view_count_filter,
            'publish_time_filter': self.publish_time_filter,
            'title_contains_filter': self.title_contains_filter
        }


# 示例使用
if __name__ == '__main__':
    # 创建过滤器（会自动使用文件开头的配置）
    filter_obj = YouTubeVideoFilter()
    
    # 如果需要，也可以通过代码动态修改配置
    # filter_obj.enabled = True
    # filter_obj.set_orientation_filter(enabled=True, allowed=["横屏"])
    # filter_obj.set_duration_filter(enabled=True, min_seconds=60, max_seconds=600)
    
    # 示例视频数据
    sample_videos = [
        {
            'title': 'Python教程 基础',
            'search_query': 'Python 教程',
            'orientation': '横屏',
            'duration': '10:30',
            'resolution': '1080p',
            'view_count': '5万次观看',
            'publish_time': '1天前'
        },
        {
            'title': 'Java基础',
            'search_query': 'Python 教程',
            'orientation': '横屏',
            'duration': '5:00',
            'resolution': '720p',
            'view_count': '1000次观看',
            'publish_time': '10天前'
        }
    ]
    
    # 过滤视频
    filtered = filter_obj.filter_videos(sample_videos)
    print(f"原始视频数: {len(sample_videos)}")
    print(f"过滤后视频数: {len(filtered)}")
    print(f"过滤配置: {filter_obj.get_filter_summary()}")
    print(f"\n提示: 要修改过滤条件，请编辑文件开头的配置常量（第13-52行）")

