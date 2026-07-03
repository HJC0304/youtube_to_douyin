# 产品需求文档 (PRD)
## YouTube视频爬虫与DeepSeek API集成项目

**版本**: 1.0  
**日期**: 2025-12-14  
**文档目的**: 本文档详细描述了项目的所有功能、技术实现、配置选项和使用方式，确保可以根据此文档完全重建项目。

---

## 1. 项目概述

### 1.1 项目名称
YouTube视频爬虫与DeepSeek API集成项目

### 1.2 项目定位
一个基于Playwright的YouTube视频搜索和爬取工具，集成DeepSeek AI API调用功能，支持智能搜索、过滤、排序和AI对话。

### 1.3 核心功能
1. **YouTube视频搜索**: 自动化搜索、解析和保存YouTube视频信息
2. **智能过滤系统**: 支持多种条件过滤视频（横屏/竖屏、时长、分辨率、播放量、发布时间、标题匹配）
3. **优先级排序**: 支持按分辨率、播放次数、发布时间等维度排序
4. **DeepSeek API集成**: 支持调用DeepSeek AI进行智能对话和内容生成
5. **命令行工具**: 提供友好的CLI界面，支持查看功能列表和执行操作

### 1.4 技术栈
- **编程语言**: Python 3.7+
- **浏览器自动化**: Playwright 1.40.0+
- **HTTP请求**: requests 2.31.0+
- **数据格式**: JSON
- **配置文件**: Python模块 + JSON文件

---

## 2. 项目结构

### 2.1 目录结构
```
crawler/
├── cli.py                              # 命令行工具主文件
├── main.py                             # 项目主入口文件
├── requirements.txt                    # Python依赖包列表
├── README.md                           # 项目说明文档
├── PRD.md                              # 产品需求文档（本文档）
│
├── youtube_crawler/                    # YouTube爬虫模块
│   └── search_video.py                 # YouTube搜索核心功能
│
├── deepseek/                           # DeepSeek API模块
│   ├── deepseek_api.py                 # DeepSeek API调用功能
│   └── config/
│       └── deepseek_config.json        # DeepSeek API配置
│
├── config/                             # 配置文件目录
│   ├── video_filter_config/
│   │   └── youtube_filter.py          # 视频过滤配置和逻辑
│   └── store_config/
│       └── youtube_config.py           # 存储和排序配置
│
└── data/                               # 数据存储目录
    ├── cookies/
    │   └── .youtube_cookies.json      # YouTube登录cookies（自动生成）
    └── search_result/
        └── {yyyyMMdd}_{域名}.json      # 搜索结果文件（自动生成）
```

### 2.2 文件说明

#### 2.2.1 核心功能文件

**`youtube_crawler/search_video.py`**
- **功能**: YouTube视频搜索、解析、过滤、排序和保存的核心实现
- **主要类**: `YouTubeSearcher`
- **依赖**: Playwright, 配置文件模块

**`deepseek/deepseek_api.py`**
- **功能**: DeepSeek API调用功能
- **主要函数**: `call_deepseek_api()`
- **依赖**: requests

**`cli.py`**
- **功能**: 命令行工具，提供用户友好的CLI界面
- **主要类**: `CrawlerCLI`
- **功能**: 列出功能、查看详情、执行搜索、调用API

**`main.py`**
- **功能**: 项目入口，默认显示所有功能列表

#### 2.2.2 配置文件

**`config/video_filter_config/youtube_filter.py`**
- **功能**: 定义视频过滤条件和过滤逻辑
- **主要类**: `YouTubeVideoFilter`
- **配置项**: 6种过滤条件（横屏/竖屏、时长、分辨率、播放量、发布时间、标题匹配）

**`config/store_config/youtube_config.py`**
- **功能**: 定义存储和排序配置
- **配置项**: `MAX_SAVE_COUNT`, `PRIORITY_ORDER`, `PRIORITY_SORT_DIRECTION`

**`deepseek/config/deepseek_config.json`**
- **功能**: DeepSeek API密钥配置
- **格式**: JSON
- **字段**: `api_key`

---

## 3. 功能详细设计

### 3.1 YouTube视频搜索功能

#### 3.1.1 功能概述
自动化搜索YouTube视频，提取视频信息，支持过滤、排序和保存。

#### 3.1.2 核心类: YouTubeSearcher

**类定义**:
```python
class YouTubeSearcher:
    def __init__(self, headless: bool = False, browser_type: str = "chromium")
    def search(self, search_query: str, click_recent_upload: bool = True)
    def parse_search_results(self, search_query: str = "") -> List[Dict]
    def save_results(self, results: List[Dict], search_query: str = "")
    def search_and_save(self, search_query: str, click_recent_upload: bool = True) -> List[Dict]
    def load_cookies(self)
    def save_cookies(self)
    def close()
```

**初始化参数**:
- `headless` (bool): 是否使用无头模式，默认False
- `browser_type` (str): 浏览器类型，可选"chromium"、"firefox"、"webkit"，默认"chromium"

**常量定义**:
- `TIMEOUT = 30000`: 所有操作的超时时间（30秒，单位毫秒）
- `YOUTUBE_BASE_URL = "https://www.youtube.com"`: YouTube基础URL

#### 3.1.3 搜索流程

**完整搜索流程** (`search_and_save`方法):
1. 加载cookies（如果存在）
2. 访问YouTube首页
3. 输入搜索词到搜索框
4. 点击搜索按钮
5. 点击"最近上传"按钮（可选）
6. 滚动页面加载更多结果
7. 解析搜索结果（最多100条）
8. 应用视频过滤
9. 应用优先级排序
10. 应用保存条数限制
11. 保存结果到文件
12. 等待30秒（显示倒计时）

**详细步骤说明**:

**步骤1: 加载Cookies**
- 文件路径: `data/cookies/.youtube_cookies.json`
- 先访问YouTube首页（用于设置cookies的域名）
- 如果文件存在，加载cookies到浏览器上下文
- 如果cookies加载成功，刷新页面使cookies生效
- 如果文件不存在，跳过（用户需要手动登录）

**步骤2: 访问YouTube首页**
- URL: `https://www.youtube.com`
- 等待页面加载完成（networkidle状态）
- 记录日志: "访问YouTube首页"

**步骤3: 输入搜索词**
- 定位搜索框: `input[name="search_query"][placeholder="搜索"]`
- 清空搜索框
- 输入搜索词
- 记录日志: "输入搜索词: {search_query}"

**步骤4: 点击搜索按钮**
- 定位搜索按钮: `button[aria-label="Search"][title="搜索"]`
- 点击按钮
- 等待搜索结果页面加载
- 记录日志: "点击搜索按钮"

**步骤5: 点击"最近上传"按钮（可选）**
- 如果`click_recent_upload=True`:
  - 查找包含"最近上传"文本的按钮
  - 点击按钮
  - 等待筛选结果加载
  - 记录日志: "点击'最近上传'按钮"
- 如果`click_recent_upload=False`，跳过此步骤

**步骤6: 滚动页面加载结果**
- 滚动到页面底部，触发懒加载
- 等待新内容加载
- 重复滚动多次以确保加载足够内容
- 记录日志: "滚动页面加载更多结果"

**步骤7: 解析搜索结果**
- 定位视频元素: `ytd-video-renderer.style-scope.ytd-item-section-renderer`
- 最多解析100个视频元素
- 对每个视频元素提取以下信息:
  - `title`: 视频标题（从`a#video-title`获取）
  - `url_relative`: 相对URL（从`a#video-title`的href属性获取）
  - `url`: 完整URL（通过`urljoin`拼接）
  - `view_count`: 观看次数（从`div#metadata-line span:first-child`获取）
  - `publish_time`: 发布时间（从`div#metadata-line span:nth-child(2)`获取）
  - `is_shorts`: 是否为竖屏视频（检查`overlay-style="SHORTS"`属性）
  - `orientation`: 横屏/竖屏（SHORTS为竖屏，其他为横屏）
  - `duration`: 视频时长（从视频缩略图上的时长标签获取）
  - `resolution`: 分辨率（从视频信息中提取，如"1080p"、"4K"）
  - `search_query`: 搜索关键词
  - `search_time`: 搜索时间（格式: "YYYY-MM-DD HH:MM:SS"）

**步骤8: 应用视频过滤**
- 如果`FILTER_ENABLED = True`:
  - 创建`YouTubeVideoFilter`实例
  - 调用`filter_videos()`方法过滤视频
  - 记录过滤前后的数量

**步骤9: 应用优先级排序**
- 如果`PRIORITY_ORDER`不为空:
  - 根据`PRIORITY_ORDER`列表中的字段排序
  - 每个字段的排序方向由`PRIORITY_SORT_DIRECTION`决定
  - 支持多字段组合排序

**步骤10: 应用保存条数限制**
- 如果`MAX_SAVE_COUNT`不为None且大于0:
  - 只保留前`MAX_SAVE_COUNT`个视频

**步骤11: 保存结果到文件**
- 文件命名格式: `{yyyyMMdd}_{域名}.json`
  - 例如: `20251214_www.youtube.com.json`
- 文件路径: `data/search_result/`
- JSON格式:
  ```json
  {
    "total": 43,
    "results": [
      {
        "search_query": "搜索关键词",
        "search_time": "2025-12-14 01:42:03",
        "is_shorts": false,
        "orientation": "横屏",
        "title": "视频标题",
        "url": "https://www.youtube.com/watch?v=...",
        "url_relative": "/watch?v=...",
        "duration": "7:01",
        "resolution": "4K",
        "view_count": "6.6万次观看",
        "publish_time": "7天前"
      }
    ],
    "last_updated": "2025-12-14 01:42:03"
  }
  ```
- **重要**: JSON中不包含最外层的`search_query`字段
- **去重逻辑**: 
- 读取已存在的搜索结果文件
- 创建一个以标题为键的字典
- 先添加现有结果到字典
- 添加新结果时，如果标题已存在，则覆盖旧记录
- 记录新增、更新、总数并输出日志
- 记录日志: 显示新增、更新、总数

**步骤12: 等待30秒（倒计时）**
- 显示倒计时: "等待30秒... 29秒... 28秒..."
- 每秒更新一次

#### 3.1.4 日志系统

**日志格式**:
- 每个步骤都有详细的日志输出
- 格式: `[步骤编号] [状态] 步骤描述`
- 状态标识:
  - `✅` 成功
  - `⚠️` 警告
  - `❌` 错误
  - `🔄` 进行中

**日志方法**: `_log_step(message: str, status: str = "INFO")`

#### 3.1.5 辅助方法

**`_normalize_url(url_relative: str) -> str`**
- 功能: 将相对URL转换为完整URL
- 使用`urljoin(YOUTUBE_BASE_URL, url_relative)`

**`_extract_duration(video_element) -> Optional[str]`**
- 功能: 从视频元素中提取时长
- 查找时长标签，格式如"7:01"、"1:23:45"

**`_extract_resolution(video_element) -> Optional[str]**
- 功能: 从视频元素中提取分辨率
- 支持格式: "1080p"、"4K"、"HD"、"720p"等

**`_get_result_path(search_query: str = "") -> Path`**
- 功能: 生成结果文件路径
- 格式: `{yyyyMMdd}_{域名}.json`

**`_wait_with_countdown(seconds: int = 30)`**
- 功能: 等待指定秒数，显示倒计时

**`_sort_videos_by_priority(results: List[Dict], priority_order: List[str], sort_direction: Dict[str, str]) -> List[Dict]`**
- 功能: 根据优先级排序视频
- 支持字段: `resolution`, `view_count`, `publish_time`
- 排序方向: `asc`（升序）或`desc`（降序）
- 实现方式: 使用`sorted()`函数和自定义排序键函数

**`_get_resolution_priority(resolution: str) -> int`**
- 功能: 获取分辨率的优先级数值（用于排序）
- 优先级: 8K > 4K > 1440p > 1080p > 720p > HD

**`_get_view_count_value(view_count_str: str) -> int`**
- 功能: 将播放量字符串转换为数值
- 支持格式: "5万次观看"、"1.9万次观看"、"1000次观看"、"1亿次观看"

**`_get_publish_time_value(publish_time_str: str) -> float`**
- 功能: 将发布时间字符串转换为天数（用于排序）
- 支持格式: "1小时前"、"3天前"、"2周前"、"1个月前"

#### 3.1.6 Cookie管理

**保存Cookies**:
- 方法: `save_cookies()`
- 文件路径: `data/cookies/.youtube_cookies.json`
- 格式: JSON数组，包含所有cookies

**加载Cookies**:
- 方法: `load_cookies()`
- 如果文件存在，加载cookies到浏览器上下文
- 如果文件不存在，跳过

**自动保存**:
- 在`close()`方法中自动保存cookies

---

### 3.2 视频过滤系统

#### 3.2.1 功能概述
支持多种条件过滤视频，只有通过所有过滤条件的视频才会被保存。

#### 3.2.2 核心类: YouTubeVideoFilter

**类定义**:
```python
class YouTubeVideoFilter:
    def __init__(self)
    def filter_videos(self, videos: List[Dict]) -> List[Dict]
    def _check_orientation(self, video: Dict) -> bool
    def _check_duration(self, video: Dict) -> bool
    def _check_resolution(self, video: Dict) -> bool
    def _check_view_count(self, video: Dict) -> bool
    def _check_publish_time(self, video: Dict) -> bool
    def _check_title_contains(self, video: Dict) -> bool
```

#### 3.2.3 过滤条件配置

所有过滤条件配置在`config/video_filter_config/youtube_filter.py`文件开头，作为全局常量。

**1. 总开关**
```python
FILTER_ENABLED = True  # 是否启用所有过滤
```

**2. 横屏/竖屏过滤**
```python
ORIENTATION_FILTER = {
    'enabled': False,  # 是否启用此过滤
    'allowed': []  # 允许的方向列表: ["横屏"] 或 ["竖屏"] 或 ["横屏", "竖屏"]
}
```

**3. 视频时长过滤**
```python
DURATION_FILTER = {
    'enabled': False,  # 是否启用此过滤
    'min_seconds': None,  # 最小时长（秒），如 60 表示至少1分钟
    'max_seconds': None   # 最大时长（秒），如 600 表示最多10分钟
}
```

**4. 分辨率过滤**
```python
RESOLUTION_FILTER = {
    'enabled': False,  # 是否启用此过滤
    'allowed': []  # 允许的分辨率列表: ["1080p", "4K", "HD", "720p"]
}
```

**5. 播放量过滤**
```python
VIEW_COUNT_FILTER = {
    'enabled': False,  # 是否启用此过滤
    'min_views': None,  # 最小播放量，如 10000 表示至少1万播放量
    'max_views': None   # 最大播放量，如 1000000 表示最多100万播放量
}
```

**6. 发布天数过滤**
```python
PUBLISH_TIME_FILTER = {
    'enabled': False,  # 是否启用此过滤
    'max_days': None  # 最大发布天数，如 7 表示只保留7天内发布的视频
}
```

**7. 标题包含搜索词过滤**
```python
TITLE_CONTAINS_FILTER = {
    'enabled': True,  # 是否启用此过滤
    'require_all': True  # True: 标题必须包含所有搜索词; False: 包含任意一个即可
}
```

#### 3.2.4 过滤逻辑

**过滤流程** (`filter_videos`方法):
1. 如果`FILTER_ENABLED = False`，直接返回所有视频
2. 遍历每个视频，依次检查所有启用的过滤条件
3. 只有通过所有过滤条件的视频才会被保留
4. 返回过滤后的视频列表

**各过滤条件的检查逻辑**:

**横屏/竖屏过滤** (`_check_orientation`):
- 如果未启用，返回True
- 检查视频的`orientation`字段是否在`allowed`列表中
- 支持值: "横屏"、"竖屏"

**时长过滤** (`_check_duration`):
- 如果未启用，返回True
- 解析视频的`duration`字段（格式如"7:01"、"1:23:45"）
- 转换为秒数
- 检查是否在`min_seconds`和`max_seconds`范围内
- 如果`min_seconds`为None，不检查最小值
- 如果`max_seconds`为None，不检查最大值

**分辨率过滤** (`_check_resolution`):
- 如果未启用，返回True
- 检查视频的`resolution`字段是否在`allowed`列表中
- 支持值: "1080p"、"4K"、"HD"、"720p"等

**播放量过滤** (`_check_view_count`):
- 如果未启用，返回True
- 解析视频的`view_count`字段（格式如"5万次观看"、"1.9万次观看"）
- 转换为数值
- 检查是否在`min_views`和`max_views`范围内
- 如果`min_views`为None，不检查最小值
- 如果`max_views`为None，不检查最大值

**发布天数过滤** (`_check_publish_time`):
- 如果未启用，返回True
- 解析视频的`publish_time`字段（格式如"1天前"、"2周前"）
- 转换为天数
- 检查是否小于等于`max_days`
- 如果`max_days`为None，不检查

**标题包含搜索词过滤** (`_check_title_contains`):
- 如果未启用，返回True
- 获取视频的`title`和`search_query`字段
- 将搜索词按空格分割为多个词
- 如果`require_all = True`: 标题必须包含所有搜索词
- 如果`require_all = False`: 标题包含任意一个搜索词即可
- 比较时忽略大小写

#### 3.2.5 解析辅助方法

**`_parse_duration(duration_str: str) -> Optional[int]`**
- 功能: 将时长字符串转换为秒数
- 支持格式: "7:01"（分:秒）、"1:23:45"（时:分:秒）

**`_parse_view_count(view_count_str: str) -> Optional[int]`**
- 功能: 将播放量字符串转换为数值
- 支持格式: "5万次观看"、"1.9万次观看"、"1000次观看"、"1亿次观看"、"1千万次观看"

**`_parse_publish_days(publish_time_str: str) -> Optional[int]`**
- 功能: 将发布时间字符串转换为天数
- 支持格式: "1小时前"、"3天前"、"2周前"、"1个月前"、"1年前"

---

### 3.3 优先级排序系统

#### 3.3.1 功能概述
在保存前对视频进行排序，优先保存高质量视频。

#### 3.3.2 配置

**配置文件**: `config/store_config/youtube_config.py`

**配置项**:

**1. 保存条数限制**
```python
MAX_SAVE_COUNT = 3  # None 表示保存所有通过过滤的视频
```

**2. 优先级排序字段**
```python
PRIORITY_ORDER = ['publish_time', 'view_count', 'resolution']
# 可选值: 'resolution'（分辨率）、'view_count'（播放次数）、'publish_time'（发布时间）
# 空列表 [] 表示不排序，按照搜索顺序保存
```

**3. 排序方向**
```python
PRIORITY_SORT_DIRECTION = {
    'resolution': 'desc',      # 降序：4K > 1080p > 720p
    'view_count': 'desc',      # 降序：播放量高的在前
    'publish_time': 'asc'      # 升序：最新的在前（天数少的在前）
}
```

#### 3.3.3 排序逻辑

**排序方法**: `_sort_videos_by_priority()`

**排序流程**:
1. 如果`PRIORITY_ORDER`为空，不排序，直接返回
2. 定义内部函数`get_sort_key(video: Dict) -> tuple`，生成排序键
3. 对于`PRIORITY_ORDER`列表中的每个字段:
   - 获取该字段的排序方向（从`PRIORITY_SORT_DIRECTION`）
   - 如果未指定方向，使用默认值（resolution和view_count默认desc，publish_time默认asc）
   - 调用对应的转换方法获取可比较的数值
   - 如果是降序，使用负值（对于数值类型）
   - 将值添加到排序键元组中
4. 使用`sorted(videos, key=get_sort_key)`对视频列表进行排序
5. 返回排序后的列表

**字段转换方法**:

**分辨率排序**:
- 使用`_get_resolution_priority()`方法
- 优先级数值: 8K=8, 4K=7, 1440p=6, 1080p=5, 720p=4, HD=3, 其他=0
- 降序: 数值大的在前（4K > 1080p > 720p）
- 升序: 数值小的在前

**播放次数排序**:
- 使用`_get_view_count_value()`方法
- 将播放量字符串转换为数值
- 降序: 播放量高的在前
- 升序: 播放量低的在前

**发布时间排序**:
- 使用`_get_publish_time_value()`方法
- 将发布时间字符串转换为天数
- 降序: 天数多的在前（旧的在前）
- 升序: 天数少的在前（新的在前）

**多字段组合排序**:
- 先按第一个字段排序
- 如果第一个字段值相同，按第二个字段排序
- 以此类推

---

### 3.4 DeepSeek API功能

#### 3.4.1 功能概述
调用DeepSeek AI API进行智能对话、内容生成、代码编写等功能。

#### 3.4.2 核心函数

**函数定义**:
```python
def call_deepseek_api(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> Optional[Dict[str, Any]]
```

**参数说明**:
- `prompt` (str, 必需): 输入的提示词
- `api_key` (str, 可选): API密钥，如果为None则从配置文件或环境变量读取
- `model` (str, 可选): 使用的模型，默认为"deepseek-chat"
- `temperature` (float, 可选): 温度参数，控制输出的随机性（0-1），默认0.7
- `max_tokens` (int, 可选): 最大生成token数，默认2000

**返回值**:
- `Dict[str, Any]`: API响应数据，包含`choices`、`usage`等信息
- `None`: 如果请求失败返回None

#### 3.4.3 API Key获取优先级

1. **直接传入参数**（最高优先级）
   - 如果调用时传入了`api_key`参数，直接使用

2. **配置文件**（次优先级）
   - 文件路径: `deepseek/config/deepseek_config.json`
   - 格式:
     ```json
     {
       "api_key": "your-api-key-here"
     }
     ```
   - 支持多种key名称: `api_key`、`DEEPSEEK_API_KEY`、`apiKey`

3. **环境变量**（最低优先级）
   - 环境变量名: `DEEPSEEK_API_KEY`
   - 使用`os.getenv('DEEPSEEK_API_KEY')`读取

4. **如果都未找到**:
   - 打印错误信息
   - 提示用户配置API Key
   - 返回None

#### 3.4.4 API调用流程

1. **打印输入参数**
   - 显示prompt、model、temperature、max_tokens

2. **获取API Key**
   - 按照优先级顺序尝试获取

3. **构建请求**
   - URL: `https://api.deepseek.com/v1/chat/completions`
   - 请求头:
     ```python
     {
         "Authorization": f"Bearer {api_key}",
         "Content-Type": "application/json"
     }
     ```
   - 请求体:
     ```python
     {
         "model": model,
         "messages": [
             {
                 "role": "user",
                 "content": prompt
             }
         ],
         "temperature": temperature,
         "max_tokens": max_tokens
     }
     ```

4. **发送请求**
   - 使用`requests.post()`发送POST请求
   - 超时时间: 30秒

5. **处理响应**
   - 检查响应状态码
   - 解析JSON响应
   - 提取回复内容（从`choices[0].message.content`）
   - 打印回复内容
   - 打印Token使用情况（`usage`字段）

6. **错误处理**
   - 捕获`requests.exceptions.RequestException`
   - 捕获其他异常
   - 打印详细的错误信息

#### 3.4.5 输出格式

**输入参数输出**:
```
============================================================
📝 输入参数:
   Prompt: 什么是人工智能？
   Model: deepseek-chat
   Temperature: 0.7
   Max Tokens: 2000
============================================================
```

**API响应输出**:
```
============================================================
✅ DeepSeek API 响应:
============================================================
[AI回复内容]
============================================================

📊 Token 使用情况:
   提示词 tokens: 10
   完成 tokens: 50
   总计 tokens: 60
```

---

### 3.5 命令行工具 (CLI)

#### 3.5.1 功能概述
提供友好的命令行界面，支持查看功能列表、查看功能详情、执行搜索和调用API。

#### 3.5.2 核心类: CrawlerCLI

**类定义**:
```python
class CrawlerCLI:
    def __init__(self)
    def _init_features(self) -> Dict
    def show_all_features(self)
    def show_feature_detail(self, feature_id: str)
    def execute_youtube_search(self, query: str, headless: bool = False, click_recent: bool = True)
    def execute_deepseek_api(self, prompt: str, api_key: str = None, model: str = "deepseek-chat", temperature: float = 0.7, max_tokens: int = 2000)
    def show_help(self)
```

#### 3.5.3 功能列表

**功能定义** (`_init_features`方法):

**1. YouTube搜索功能** (`youtube_search`):
- 名称: "YouTube 视频搜索"
- 描述: "在 YouTube 上搜索视频，提取视频信息（标题、链接、观看次数、发布时间等）"
- 模块: "youtube_crawler.search_video"
- 类: "YouTubeSearcher"
- 命令示例:
  - `python -m cli youtube search 'Python教程'`
  - `python -m cli youtube search '机器学习' --headless`
  - `python -m cli youtube search '数据分析' --no-recent`
- Python代码示例: 包含完整的代码示例

**2. DeepSeek API功能** (`deepseek_api`):
- 名称: "DeepSeek API 调用"
- 描述: "调用 DeepSeek AI API 进行智能对话、内容生成、代码编写等功能"
- 模块: "deepseek.deepseek_api"
- 类/函数: "call_deepseek_api"
- 命令示例:
  - `python -m cli deepseek chat '什么是人工智能？'`
  - `python -m cli deepseek chat '用Python写一个快速排序' --temperature 0.3`
  - `python -m cli deepseek chat '写一首关于春天的诗' --temperature 0.9 --max-tokens 500`
- Python代码示例: 包含完整的代码示例

#### 3.5.4 CLI命令

**命令结构**:
```
python -m cli <command> [options]
```

**可用命令**:

**1. `list`**
- 功能: 显示所有支持的功能
- 用法: `python -m cli list`
- 输出: 列出所有功能，包括名称、描述、命令示例、Python代码示例

**2. `info <feature>`**
- 功能: 显示特定功能的详细信息
- 用法: `python -m cli info <feature_id>`
- 示例: `python -m cli info youtube_search`
- 输出: 功能的详细描述、所有命令示例、Python代码示例、模块路径

**3. `youtube search <query>`**
- 功能: 执行YouTube视频搜索
- 用法: `python -m cli youtube search <query> [options]`
- 参数:
  - `query` (必需): 搜索关键词
  - `--headless` (可选): 无头模式运行
  - `--no-recent` (可选): 不点击"最近上传"按钮
- 示例:
  - `python -m cli youtube search "Python教程"`
  - `python -m cli youtube search "机器学习" --headless`
  - `python -m cli youtube search "数据分析" --no-recent`

**4. `deepseek chat <prompt>`**
- 功能: 调用DeepSeek API进行对话
- 用法: `python -m cli deepseek chat <prompt> [options]`
- 参数:
  - `prompt` (必需): 输入的提示词
  - `--model` (可选): 使用的模型，默认"deepseek-chat"
  - `--temperature` (可选): 温度参数，默认0.7
  - `--max-tokens` (可选): 最大生成token数，默认2000
  - `--api-key` (可选): API Key
- 示例:
  - `python -m cli deepseek chat "什么是人工智能？"`
  - `python -m cli deepseek chat "写一首诗" --temperature 0.9 --max-tokens 500`

**5. `help`或默认**
- 功能: 显示帮助信息
- 用法: `python -m cli` 或 `python -m cli help`
- 输出: 命令列表和使用示例

#### 3.5.5 执行方法

**`execute_youtube_search`**:
- 导入`YouTubeSearcher`类
- 创建实例并执行搜索
- 显示搜索结果（前10个）
- 显示保存路径

**`execute_deepseek_api`**:
- 导入`call_deepseek_api`函数
- 调用函数并显示结果
- 处理错误

---

## 4. 数据格式规范

### 4.1 搜索结果JSON格式

**文件命名**: `{yyyyMMdd}_{域名}.json`
- 示例: `20251214_www.youtube.com.json`

**JSON结构**:
```json
{
  "total": 43,
  "results": [
    {
      "search_query": "搜索关键词",
      "search_time": "2025-12-14 01:42:03",
      "is_shorts": false,
      "orientation": "横屏",
      "title": "视频标题",
      "url": "https://www.youtube.com/watch?v=...",
      "url_relative": "/watch?v=...",
      "duration": "7:01",
      "resolution": "4K",
      "view_count": "6.6万次观看",
      "publish_time": "7天前"
    }
  ],
  "last_updated": "2025-12-14 01:42:03"
}
```

**字段说明**:
- `total` (int): 结果总数
- `results` (array): 视频列表
  - `search_query` (string): 搜索关键词
  - `search_time` (string): 搜索时间，格式"YYYY-MM-DD HH:MM:SS"
  - `is_shorts` (boolean): 是否为竖屏视频（SHORTS）
  - `orientation` (string): 横屏/竖屏，值为"横屏"或"竖屏"
  - `title` (string): 视频标题
  - `url` (string): 完整URL
  - `url_relative` (string): 相对URL
  - `duration` (string): 视频时长，格式如"7:01"、"1:23:45"
  - `resolution` (string): 分辨率，如"1080p"、"4K"、"HD"
  - `view_count` (string): 观看次数，如"6.6万次观看"
  - `publish_time` (string): 发布时间，如"7天前"、"2周前"
- `last_updated` (string): 最后更新时间，格式"YYYY-MM-DD HH:MM:SS"

**重要规则**:
- JSON中**不包含**最外层的`search_query`字段
- 如果新视频的标题与已保存视频的标题相同，则**覆盖**旧记录
- 文件使用UTF-8编码，`ensure_ascii=False`确保中文正常显示

### 4.2 Cookies JSON格式

**文件路径**: `data/cookies/.youtube_cookies.json`

**JSON结构**: Playwright cookies数组格式
```json
[
  {
    "name": "cookie_name",
    "value": "cookie_value",
    "domain": ".youtube.com",
    "path": "/",
    "expires": 1234567890,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  }
]
```

### 4.3 DeepSeek配置JSON格式

**文件路径**: `deepseek/config/deepseek_config.json`

**JSON结构**:
```json
{
  "api_key": "your-api-key-here"
}
```

**支持多种key名称**:
- `api_key`
- `DEEPSEEK_API_KEY`
- `apiKey`

---

## 5. 配置系统详细说明

### 5.1 视频过滤配置

**文件**: `config/video_filter_config/youtube_filter.py`

**配置位置**: 文件开头，作为全局常量

**配置项**:

1. **FILTER_ENABLED** (bool)
   - 总开关，控制是否启用所有过滤
   - 默认: `True`

2. **ORIENTATION_FILTER** (dict)
   - 横屏/竖屏过滤
   - 结构:
     ```python
     {
         'enabled': False,
         'allowed': []  # ["横屏"] 或 ["竖屏"] 或 ["横屏", "竖屏"]
     }
     ```

3. **DURATION_FILTER** (dict)
   - 视频时长过滤
   - 结构:
     ```python
     {
         'enabled': False,
         'min_seconds': None,  # 最小时长（秒）
         'max_seconds': None   # 最大时长（秒）
     }
     ```

4. **RESOLUTION_FILTER** (dict)
   - 分辨率过滤
   - 结构:
     ```python
     {
         'enabled': False,
         'allowed': []  # ["1080p", "4K", "HD", "720p"]
     }
     ```

5. **VIEW_COUNT_FILTER** (dict)
   - 播放量过滤
   - 结构:
     ```python
     {
         'enabled': False,
         'min_views': None,  # 最小播放量
         'max_views': None   # 最大播放量
     }
     ```

6. **PUBLISH_TIME_FILTER** (dict)
   - 发布天数过滤
   - 结构:
     ```python
     {
         'enabled': False,
         'max_days': None  # 最大发布天数
     }
     ```

7. **TITLE_CONTAINS_FILTER** (dict)
   - 标题包含搜索词过滤
   - 结构:
     ```python
     {
         'enabled': True,
         'require_all': True  # True: 必须包含所有搜索词; False: 包含任意一个即可
     }
     ```

### 5.2 存储配置

**文件**: `config/store_config/youtube_config.py`

**配置位置**: 文件开头，作为全局常量

**配置项**:

1. **MAX_SAVE_COUNT** (int | None)
   - 过滤后保存的视频条数
   - `None`: 保存所有通过过滤的视频
   - 数字: 只保存前N个视频
   - 默认: `3`

2. **PRIORITY_ORDER** (list)
   - 优先级排序字段列表
   - 可选值: `'resolution'`, `'view_count'`, `'publish_time'`
   - 空列表: 不排序，按照搜索顺序保存
   - 默认: `['publish_time', 'view_count', 'resolution']`

3. **PRIORITY_SORT_DIRECTION** (dict)
   - 每个排序字段的排序方向
   - 键: 排序字段名
   - 值: `'asc'`（升序）或`'desc'`（降序）
   - 默认:
     ```python
     {
         'resolution': 'desc',
         'view_count': 'desc',
         'publish_time': 'asc'
     }
     ```

### 5.3 DeepSeek配置

**文件**: `deepseek/config/deepseek_config.json`

**格式**: JSON

**字段**:
- `api_key` (string): DeepSeek API密钥

---

## 6. 依赖和安装

### 6.1 Python版本要求
- Python 3.7+

### 6.2 Python包依赖

**文件**: `requirements.txt`

**内容**:
```
playwright>=1.40.0
requests>=2.31.0
```

### 6.3 安装步骤

1. **安装Python包**:
   ```bash
   pip install -r requirements.txt
   ```

2. **安装Playwright浏览器**:
   ```bash
   playwright install chromium
   ```
   或安装所有浏览器:
   ```bash
   playwright install
   ```

3. **配置DeepSeek API Key**（可选）:
   - 编辑`deepseek/config/deepseek_config.json`
   - 填入API Key

---

## 7. 使用示例

### 7.1 YouTube搜索示例

**基本使用**:
```python
from youtube_crawler.search_video import YouTubeSearcher

with YouTubeSearcher(headless=False) as searcher:
    results = searcher.search_and_save("Python教程", click_recent_upload=True)
    for video in results:
        print(f"标题: {video['title']}")
        print(f"链接: {video['url']}")
```

**分步执行**:
```python
from youtube_crawler.search_video import YouTubeSearcher

searcher = YouTubeSearcher(headless=False)
try:
    searcher.search("机器学习", click_recent_upload=True)
    results = searcher.parse_search_results()
    searcher.save_results(results)
finally:
    searcher.close()
```

### 7.2 DeepSeek API示例

**基本使用**:
```python
from deepseek.deepseek_api import call_deepseek_api

result = call_deepseek_api("请用一句话解释什么是人工智能")
```

**自定义参数**:
```python
from deepseek.deepseek_api import call_deepseek_api

result = call_deepseek_api(
    prompt="用Python写一个快速排序函数",
    temperature=0.3,
    max_tokens=1000
)
```

### 7.3 CLI使用示例

**查看所有功能**:
```bash
python -m cli list
```

**查看功能详情**:
```bash
python -m cli info youtube_search
python -m cli info deepseek_api
```

**执行搜索**:
```bash
python -m cli youtube search "Python教程"
python -m cli youtube search "机器学习" --headless
```

**调用API**:
```bash
python -m cli deepseek chat "什么是人工智能？"
python -m cli deepseek chat "写一首诗" --temperature 0.9 --max-tokens 500
```

---

## 8. 错误处理

### 8.1 YouTube搜索错误

**常见错误**:
1. **浏览器启动失败**
   - 原因: Playwright浏览器未安装
   - 解决: 运行`playwright install chromium`

2. **元素定位失败**
   - 原因: YouTube页面结构变化或网络慢
   - 解决: 检查网络连接，更新选择器

3. **Cookie加载失败**
   - 原因: Cookie文件格式错误
   - 解决: 删除Cookie文件，重新登录

### 8.2 DeepSeek API错误

**常见错误**:
1. **API Key未找到**
   - 原因: 未配置API Key
   - 解决: 在配置文件或环境变量中设置API Key

2. **请求失败**
   - 原因: 网络问题、API Key无效、账户余额不足
   - 解决: 检查网络、验证API Key、检查账户余额

### 8.3 配置导入错误

**错误处理**:
- 如果配置文件导入失败，使用默认值
- 打印警告信息，但不中断程序执行

---

## 9. 性能优化

### 9.1 搜索限制
- 最多解析100个视频，避免解析过多数据

### 9.2 超时设置
- 所有操作统一使用30秒超时

### 9.3 无头模式
- 支持无头模式运行，提高性能

### 9.4 懒加载
- 通过滚动触发懒加载，确保加载足够内容

---

## 10. 安全考虑

### 10.1 API Key安全
- API Key存储在配置文件中，不应提交到版本控制
- 支持环境变量方式，更安全

### 10.2 Cookie安全
- Cookie文件包含敏感信息，不应分享
- 文件路径: `data/cookies/.youtube_cookies.json`（隐藏文件）

### 10.3 使用规范
- 遵守YouTube服务条款
- 合理使用频率，避免过于频繁的请求

---

## 11. 扩展性设计

### 11.1 模块化设计
- 功能模块独立，易于扩展
- 配置与代码分离

### 11.2 可配置性
- 所有过滤条件和排序规则都可配置
- 支持多种配置方式

### 11.3 易于扩展
- 可以轻松添加新的过滤条件
- 可以轻松添加新的排序字段
- 可以轻松添加新的功能模块

---

## 12. 测试建议

### 12.1 单元测试
- 测试过滤逻辑
- 测试排序逻辑
- 测试数据解析

### 12.2 集成测试
- 测试完整搜索流程
- 测试API调用流程
- 测试CLI命令

### 12.3 端到端测试
- 测试真实搜索场景
- 测试真实API调用场景

---

## 13. 开发规范

### 13.1 代码风格
- 遵循PEP 8规范
- 使用类型提示
- 添加文档字符串

### 13.2 日志规范
- 每个步骤都有详细日志
- 使用统一的日志格式
- 包含状态标识（✅、⚠️、❌、🔄）

### 13.3 错误处理
- 所有可能失败的操作都有错误处理
- 提供清晰的错误信息
- 不中断程序执行（除非必要）

---

## 14. 版本历史

### 版本 1.0 (2025-12-14)
- 初始版本
- 支持YouTube视频搜索
- 支持视频过滤和排序
- 支持DeepSeek API调用
- 支持CLI命令行工具

---

## 15. 附录

### 15.1 关键常量

**超时时间**:
- `TIMEOUT = 30000` (30秒，单位毫秒)

**URL**:
- `YOUTUBE_BASE_URL = "https://www.youtube.com"`
- `DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"`

### 15.2 选择器参考

**YouTube搜索框**:
- `input[name="search_query"][placeholder="搜索"]`

**搜索按钮**:
- `button[aria-label="Search"][title="搜索"]`

**视频元素**:
- `ytd-video-renderer.style-scope.ytd-item-section-renderer`

**视频标题**:
- `a#video-title`

**视频元数据**:
- `div#metadata-line`

### 15.3 数据格式参考

**时长格式**:
- "7:01" (分:秒)
- "1:23:45" (时:分:秒)

**播放量格式**:
- "1000次观看"
- "5万次观看"
- "1.9万次观看"
- "1亿次观看"
- "1千万次观看"

**发布时间格式**:
- "1小时前"
- "3天前"
- "2周前"
- "1个月前"
- "1年前"

**分辨率格式**:
- "1080p"
- "4K"
- "HD"
- "720p"
- "1440p"
- "8K"

---

## 16. 总结

本文档详细描述了YouTube视频爬虫与DeepSeek API集成项目的所有功能、技术实现、配置选项和使用方式。根据此文档，可以完全重建项目，包括：

1. **项目结构**: 完整的目录结构和文件组织
2. **核心功能**: YouTube搜索、视频过滤、优先级排序、DeepSeek API调用
3. **配置系统**: 详细的配置选项和默认值
4. **数据格式**: 完整的JSON格式规范
5. **CLI工具**: 完整的命令行工具设计
6. **错误处理**: 错误处理和解决方案
7. **使用示例**: 各种使用场景的代码示例

所有功能都有详细的实现说明，包括方法签名、参数说明、返回值、处理流程等，确保可以根据此文档完全重建项目。

---

**文档结束**

