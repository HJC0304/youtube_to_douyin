## 爬虫与自动化工具集合

一个基于 Python 的多功能爬虫与自动化工具集合，包含：
- 基于 Playwright 的 **YouTube 视频搜索与解析**
- 基于 Playwright 的 **YouTube Shorts 视频信息提取**（支持批量处理）
- 基于 Downie 4 的 **YouTube 视频下载**
- 基于 Playwright 的 **抖音创作者平台视频上传**
- 集成 DeepSeek 的 **AI 对话与内容生成**
- **VPN 应用打开**（支持 PrivadoVPN）

## ✨ 主要特性

- 🔍 **YouTube 智能搜索**：自动搜索 YouTube 视频（最多100条）
- 🎯 **智能过滤**：支持多种过滤条件（横屏/竖屏、时长、分辨率、播放量、发布时间、标题匹配）
- 📊 **优先级排序**：支持按分辨率、播放次数、发布时间等维度排序
- 💾 **灵活保存**：可配置保存条数，按日期和域名命名文件
- 🔐 **登录管理**：自动保存和加载 YouTube、抖音 登录信息
- 📝 **详细日志**：每个步骤都有详细的执行日志和倒计时显示
- 🤖 **DeepSeek API**：集成 DeepSeek AI 对话功能，支持智能问答和内容生成
- 📥 **Downie 4 下载集成**：一条命令把 YouTube 链接送入 Downie 4 进行下载
- 📤 **抖音自动上传**：自动打开抖音创作者平台上传页面，上传本地视频、填写标题与话题并发布
- 📹 **YouTube Shorts 批量提取**：从 YouTube 频道 Shorts 页面批量提取视频信息（URL、标题、播放次数），支持从配置文件读取多个 YouTuber 并自动处理
- 🔐 **VPN 应用打开**：自动打开 PrivadoVPN 应用程序，支持检查应用是否已在运行
- 🔄 **自动化工作流**：整合所有功能，实现从视频提取到上传的完整自动化流程，支持步骤控制（跳过指定步骤或只执行部分步骤）

## 功能特性

### 🎯 核心功能：YouTube 搜索

- **自动搜索**：支持在 YouTube 上自动输入搜索词并执行搜索（最多解析100条）
- **智能筛选**：自动点击"最近上传"按钮，筛选最新上传的视频
- **结果解析**：自动解析搜索结果，提取视频详细信息
- **视频过滤**：支持多种过滤条件（横屏/竖屏、时长、分辨率、播放量、发布时间、标题匹配）
- **优先级排序**：支持按分辨率、播放次数、发布时间等维度排序
- **登录管理**：自动保存和加载登录信息（cookies），避免重复登录
- **数据保存**：将搜索结果保存为 JSON 格式，支持按日期和域名命名
- **保存限制**：可配置保存的视频条数，优先保存高质量视频
- **DeepSeek API**：调用 DeepSeek AI 接口，支持智能对话、内容生成等功能

**业务逻辑流程**：
1. **初始化浏览器**：启动 Playwright 浏览器，加载已保存的 cookies（如果存在）
2. **执行搜索**：访问 YouTube 首页，输入搜索关键词，点击搜索按钮
3. **筛选最近上传**（可选）：自动点击"最近上传"按钮，筛选最新上传的视频
4. **解析结果**：遍历搜索结果页面，提取每个视频的详细信息（标题、URL、时长、分辨率、播放次数、发布时间等），最多解析100条
5. **应用过滤条件**：根据配置的过滤规则（横屏/竖屏、时长、分辨率、播放量、发布时间、标题匹配）过滤视频
6. **优先级排序**：按照配置的排序规则（分辨率、播放次数、发布时间等）对视频进行排序
7. **应用保存限制**：根据 `MAX_SAVE_COUNT` 配置，只保存前 N 个高质量视频
8. **保存结果**：将处理后的视频信息保存到 `data/search_result/{日期}_{域名}.json` 文件
9. **等待完成**：等待30秒（倒计时显示），确保操作完成

### 📥 核心功能：Downie 4 YouTube 视频下载

- **自动打开应用**：检测并打开 `Downie 4.app`
- **多种打开方式**：
  - 直接通过 AppleScript 调用 `open location "<url>"`
  - 通过菜单栏 `文件 -> 打开链接` 自动输入 URL
  - 通过 `downie4://x-callback-url/download?url=...` URL scheme 兜底
- **友好日志**：输出每一步的成功/失败信息，便于排查问题

**业务逻辑流程**：
1. **检测应用**：检查 Downie 4 应用是否已安装（macOS 系统）
2. **打开应用**：如果应用未运行，自动启动 Downie 4
3. **尝试多种方式**：按优先级尝试多种方式将 URL 传递给 Downie 4
   - 方式1：使用 AppleScript 的 `open location` 命令（最直接）
   - 方式2：通过菜单栏操作（文件 -> 打开链接）
   - 方式3：使用 URL scheme（`downie4://x-callback-url/download?url=...`）作为兜底方案
4. **验证结果**：检查是否成功创建下载任务
5. **错误处理**：如果所有方式都失败，输出详细的错误信息和建议

### 📹 核心功能：YouTube Shorts 视频信息提取

- **单个频道提取**：从指定 YouTube 频道的 Shorts 页面提取视频信息
- **批量处理**：从 `data/youtubers/youtubers.json` 配置文件读取多个 YouTuber，依次提取每个频道的 Shorts 视频
- **提取信息**：
  - 视频 URL（完整链接和相对路径）
  - 视频标题
  - 播放次数
  - 视频类型（Shorts/普通视频）
  - 视频方向（竖屏/横屏）
- **自动滚动**：自动滚动页面加载更多视频
- **统一保存**：所有 YouTuber 的视频信息保存到同一个文件，格式为 `日期_youtuber_shorts_www.youtube.com.json`
- **登录管理**：支持使用本地 cookies 保持登录状态

**业务逻辑流程**：

**单个频道提取**：
1. **初始化浏览器**：启动 Playwright 浏览器，加载已保存的 cookies（如果存在）
2. **访问 Shorts 页面**：导航到指定的 YouTube Shorts 页面（如 `https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts`）
3. **等待页面加载**：等待视频列表容器（`div#contents`）加载完成
4. **自动滚动**：滚动页面3次，每次滚动到底部并等待2秒，以加载更多视频
5. **解析视频列表**：查找所有视频容器（`div#content`），提取每个视频的详细信息
6. **提取视频信息**：对每个视频提取 URL、标题、播放次数等信息
7. **保存结果**：将提取的视频信息保存到 `data/search_result/{日期}_youtuber_shorts_www.youtube.com.json` 文件

**批量处理**：
1. **读取配置**：从 `data/youtubers/youtubers.json` 读取 YouTuber 列表
2. **遍历处理**：依次处理每个 YouTuber
3. **统一保存**：所有 YouTuber 的视频信息保存到同一个文件（按日期命名）
4. **错误处理**：如果某个 YouTuber 处理失败，记录错误并继续处理下一个
5. **间隔等待**：在处理下一个 YouTuber 之前等待2秒，避免请求过于频繁

### 📤 核心功能：抖音创作者平台视频上传

- **自动上传本地视频**：在 `https://creator.douyin.com/creator-micro/content/upload` 页面自动选择本地视频并上传
- **登录信息复用**：优先加载本地 cookies，尽量免登录，使用 `https://creator.douyin.com/creator-micro/home` 验证登录状态
- **智能标题与话题生成**：
  - 优先通过 DeepSeek 根据视频文件名生成标题、简介和话题
  - 回退时从视频文件名提取标题，并从标题中提取话题标签
  - **时间信息提取**：支持多种时间格式（如 `20251230`、`251230`、`2025-12-30` 等），自动提取并保留在标题中
  - **话题输入优化**：每个话题前自动添加 `#`，逐字符输入，输入后自动按空格确认
- **智能视频文件匹配**：
  - **字符串规范化**：去除不可见字符（零宽空格等），统一空格类型，Unicode 规范化（NFC）
  - **前缀匹配**：通过标题前缀匹配视频文件（保留空格和大小写，至少匹配1/2长度）
  - **多目录搜索**：优先在 `config/store_config/download_config.py` 的 `DEFAULT_VIDEO_DOWNLOAD_DIR` 指定目录查找，支持指定多个搜索目录
  - **详细调试信息**：匹配失败时输出原始和规范化后的字符串，便于排查问题
- **自动封面选择**：
  - 点击封面后自动在弹窗中点击「确定」按钮
  - 支持延迟选择（填写话题后等待30-60秒随机时间）
- **发布流程优化**：
  - 自动选择「仅自己可见」选项（支持二次确认）
  - 选择后等待10-30秒随机时间再发布
  - 严格匹配文本为「发布」的按钮并点击
  - 点击「发布」后等待 30 秒，并打印倒计时与实际等待时间
- **文件管理**：
  - 上传成功后自动将视频文件移动到 `DEFAULT_VIDEO_DOWNLOAD_DIR/upload_douyin` 文件夹
  - 如果文件未找到，使用原始路径并记录日志
- **智能上传功能**：
  - 自动读取当天搜索的视频（`data/search_result/{日期}_youtuber_shorts_www.youtube.com.json`）
  - 自动读取当天下载的视频（`data/download_result/youtuber_shorts_www.youtube.com.json`，通过 `download_time` 匹配）
  - 选择播放量最多的2个视频进行上传
  - 如果选中的视频未找到本地文件，自动选择次优视频
- **上传结果记录**：将上传结果保存到 `data/upload_result/douyin/upload_www.youtube.com.json` 文件

**业务逻辑流程**：

**单个视频上传**：
1. **检查登录状态**：优先从 `data/cookies/.douyin_cookies.json` 加载登录信息，如果未登录则提示需要先登录
2. **访问上传页面**：导航到抖音创作者平台上传页面
3. **验证登录**：使用 `https://creator.douyin.com/creator-micro/home` 验证登录状态，避免不必要的页面刷新
4. **上传视频文件**：
   - 直接查找文件输入框（`input[type='file']`），使用 `set_input_files()` 设置视频文件路径，避免弹出文件选择对话框
   - 关闭可能出现的遮罩/弹窗
5. **等待上传完成**：通过检测页面元素（如"重新上传"按钮）判断上传是否完成，最多等待10分钟
6. **填写作品标题**：
   - 优先使用 DeepSeek 生成的标题，否则从文件名提取
   - **保留时间信息**：自动提取并保留标题中的时间信息（支持多种格式）
   - 填入标题输入框
7. **填写话题标签**：
   - 话题区：第一行填 DeepSeek `profile`，换行后填从标题提取的标签
   - **优化输入方式**：每个话题前自动添加 `#`，逐字符输入，输入后自动按空格确认
8. **延迟等待**：填写话题后等待30-60秒随机时间
9. **选择封面**：
   - 点击 class 前缀为 `maskBox` 的 div（包含 blob URL 的 img）
   - 在弹窗中点击「确定」按钮（查找 `<span class="semi-button-content">确定</span>`）
10. **设置可见性**：
    - 选择「仅自己可见」或「公开」选项（通过 `label` 标签中的 `span` 定位）
    - **二次确认**：确认「仅自己可见」已选中
    - **延迟发布**：选择后等待10-30秒随机时间
11. **发布视频**：点击「发布」按钮，等待30秒（倒计时显示）
12. **文件管理**：上传成功后自动将视频文件移动到 `DEFAULT_VIDEO_DOWNLOAD_DIR/upload_douyin` 文件夹
13. **保存结果**：将上传结果保存到 `data/upload_result/douyin/upload_www.youtube.com.json` 文件

**批量上传**：
1. **扫描文件夹**：扫描指定文件夹中的所有视频文件（支持 .mp4, .mkv, .avi, .mov 等格式）
2. **按文件名排序**：对视频文件按文件名排序
3. **依次上传**：遍历每个视频文件，依次执行上传流程
4. **保持浏览器打开**：上传过程中保持浏览器打开，避免重复登录
5. **会话保持**：每3个视频后执行会话保持操作（随机滚动、鼠标移动），并增加延迟时间（10-20秒）
6. **错误处理**：如果某个视频上传失败，记录错误并继续上传下一个
7. **保存结果**：将所有上传结果保存到统一文件

**智能上传（上传当天播放量最多的视频）**：
1. **读取当天搜索的视频**：从 `data/search_result/{日期}_youtuber_shorts_www.youtube.com.json` 读取当天搜索的视频列表
2. **读取当天下载的视频**：从 `data/download_result/youtuber_shorts_www.youtube.com.json` 读取当天下载的视频（通过 `download_time` 字段匹配日期）
3. **匹配已下载的视频**：通过 URL 匹配，找出既在搜索结果中又在下载结果中的视频
4. **按播放量排序**：对所有匹配的视频按播放量降序排序
5. **查找本地文件**：
   - 在 `DEFAULT_VIDEO_DOWNLOAD_DIR` 指定目录中通过标题前缀匹配查找视频文件
   - 使用字符串规范化处理（去除不可见字符，统一空格类型）
   - 如果未找到，自动选择下一个次优视频
6. **依次上传**：对找到的视频依次执行上传流程（最多上传2个）
7. **文件管理**：上传成功后自动将视频文件移动到 `DEFAULT_VIDEO_DOWNLOAD_DIR/upload_douyin` 文件夹
8. **保存结果**：将所有上传结果保存到统一文件

### 🔐 核心功能：VPN 应用管理

- **自动打开 PrivadoVPN**：使用 macOS 系统命令打开 PrivadoVPN 应用程序
- **自动连接 VPN**：打开应用后自动点击"点击链接"按钮进行连接
- **关闭应用**：支持优雅关闭和强制关闭 PrivadoVPN 应用程序
- **运行状态检查**：自动检查应用是否已在运行，避免重复打开
- **多路径支持**：支持在多个常见安装位置查找应用
- **多种连接方式**：尝试多种方法查找并点击连接按钮（按钮文本、按钮位置等）
- **友好提示**：提供清晰的错误提示和操作反馈

**打开并连接流程**：
1. **检查应用路径**：在以下位置查找 PrivadoVPN 应用
   - `/Applications/PrivadoVPN.app`
   - `/Applications/PrivadoVPN/PrivadoVPN.app`
   - `~/Applications/PrivadoVPN.app`
2. **检查运行状态**：使用 `pgrep` 命令检查应用是否已在运行
3. **打开应用**：如果未运行，使用 `open` 命令打开应用
4. **等待启动**：等待应用完全启动（2秒）
5. **点击连接按钮**：
   - 等待界面加载（3秒）
   - 使用 AppleScript 查找连接按钮（尝试多种方法）
     - 方法1：通过按钮文本查找（"点击链接"、"连接"、"Connect"）
     - 方法2：遍历所有按钮，查找包含连接相关文本的按钮
     - 方法3：点击最大的按钮（通常是主要操作按钮）
     - 方法4：点击窗口中的第一个按钮
     - 方法5：通过按钮描述查找
6. **返回结果**：返回操作是否成功

**关闭应用流程**：
1. **检查运行状态**：使用 `pgrep` 命令检查应用是否正在运行
2. **优雅关闭**：使用 AppleScript 的 `quit` 命令优雅关闭应用
3. **等待关闭**：等待2秒确认应用已关闭
4. **强制关闭**：如果优雅关闭失败，使用 `kill` 命令强制终止进程
5. **验证关闭**：再次检查应用是否已完全关闭
6. **返回结果**：返回操作是否成功

### 📊 提取的信息

- 视频标题
- 完整 URL（包括域名）和相对路径
- 搜索关键词和搜索时间
- 视频类型（普通视频 / 竖屏视频 SHORTS）
- 横屏/竖屏方向
- 视频时长
- 分辨率信息
- 观看次数
- 发布时间

## 安装说明

### 1. 环境要求

- Python 3.7+
- Playwright（会自动下载浏览器）

### 2. 安装依赖

```bash
# 安装 Python 包
pip install -r requirements.txt

# 安装 Playwright 浏览器（必需）
playwright install chromium
```

### 3. 安装 Playwright 浏览器

Playwright 需要下载浏览器二进制文件。安装完 Python 包后，运行：

```bash
# 安装 Chromium（推荐，默认）
playwright install chromium

# 或安装其他浏览器
playwright install firefox
playwright install webkit

# 安装所有浏览器
playwright install
```

**注意**：首次安装会自动下载浏览器，可能需要一些时间。

## 使用方法

### 使用命令行查看功能列表

```bash
# 方式1: 使用 main.py（推荐）
python main.py list

# 方式2: 直接调用 CLI 模块
python -m cli list
```

### DeepSeek 基本使用

```bash
python -m cli deepseek chat "什么是人工智能？"
```
```python
from youtube_crawler.search_video import YouTubeSearcher

# 使用上下文管理器（推荐，自动关闭浏览器）
with YouTubeSearcher(headless=False) as searcher:
    # 执行搜索并保存结果
    # 会自动应用过滤条件和优先级排序
    results = searcher.search_and_save("Python教程", click_recent_upload=True)
    
    # 打印结果
    for video in results:
        print(f"标题: {video['title']}")
        print(f"类型: {'竖屏视频' if video['is_shorts'] else '普通视频'}")
        print(f"方向: {video['orientation']}")
        print(f"时长: {video['duration']}")
        print(f"分辨率: {video['resolution']}")
        print(f"观看次数: {video['view_count']}")
        print(f"发布时间: {video['publish_time']}")
        print(f"链接: {video['url']}")
        print("-" * 50)
```

### 配置过滤和排序

#### 1. 配置视频过滤 (`config/video_filter_config/youtube_filter.py`)

```python
# 启用过滤
FILTER_ENABLED = True

# 只保留横屏视频
ORIENTATION_FILTER = {
    'enabled': True,
    'allowed': ["横屏"]
}

# 只保留1-10分钟的视频
DURATION_FILTER = {
    'enabled': True,
    'min_seconds': 60,   # 1分钟
    'max_seconds': 600   # 10分钟
}

# 标题必须包含所有搜索词
TITLE_CONTAINS_FILTER = {
    'enabled': True,
    'require_all': True
}
```

#### 2. 配置保存和排序 (`config/store_config/youtube_config.py`)

```python
# 只保存前50个视频
MAX_SAVE_COUNT = 50

# 按播放次数优先排序（播放量高的在前）
PRIORITY_ORDER = ['view_count']

# 组合排序：先按分辨率，再按播放次数，最后按发布时间
PRIORITY_ORDER = ['resolution', 'view_count', 'publish_time']
```

### 高级使用

#### 分步执行

```python
from youtube_crawler.search_video import YouTubeSearcher

searcher = YouTubeSearcher(headless=False)

try:
    # 1. 执行搜索
    searcher.search("机器学习", click_recent_upload=True)
    
    # 2. 解析结果
    results = searcher.parse_search_results()
    
    # 3. 保存结果
    searcher.save_results(results)
    
    # 4. 处理结果
    for video in results:
        if not video['is_shorts']:  # 只处理普通视频
            print(video['title'])
finally:
    searcher.close()  # 确保关闭浏览器
```

#### 无头模式运行

```python
# 在后台运行，不显示浏览器窗口
with YouTubeSearcher(headless=True) as searcher:
    results = searcher.search_and_save("数据分析")
```

#### 自定义配置

```python
from youtube_crawler.search_video import YouTubeSearcher

searcher = YouTubeSearcher(headless=False)

# 只搜索，不点击"最近上传"
results = searcher.search_and_save("Python", click_recent_upload=False)

# 手动保存登录信息
searcher.save_cookies()

searcher.close()
```

### 使用 DeepSeek API

**业务逻辑流程**：
1. **读取 API Key**：按优先级从以下位置读取 API Key
   - 直接传入的 `api_key` 参数（最高优先级）
   - `deepseek/config/deepseek_config.json` 配置文件
   - 环境变量 `DEEPSEEK_API_KEY`（最低优先级）
2. **构建请求**：构建 HTTP POST 请求，包含提示词、模型、温度、最大 token 数等参数
3. **发送请求**：向 DeepSeek API 端点发送请求
4. **处理响应**：解析 API 响应，提取生成的文本内容
5. **显示结果**：打印输入参数、API 响应内容和 Token 使用情况
6. **错误处理**：如果请求失败，显示详细的错误信息和建议

#### 基本使用

```python
from deepseek.deepseek_api import call_deepseek_api

# 调用 DeepSeek API（API Key 会自动从配置文件或环境变量读取）
result = call_deepseek_api("请用一句话解释什么是人工智能")

if result:
    # 结果已自动打印，也可以从返回值中获取
    content = result['choices'][0]['message']['content']
    print(f"AI 回复: {content}")
```

#### 自定义参数

```python
from deepseek.deepseek_api import call_deepseek_api

# 使用自定义参数
result = call_deepseek_api(
    prompt="写一首关于春天的诗",
    model="deepseek-chat",
    temperature=0.8,  # 更高的温度，输出更随机
    max_tokens=1000   # 最大生成 token 数
)
```

#### 直接指定 API Key

```python
from deepseek.deepseek_api import call_deepseek_api

# 直接在调用时传入 API Key
result = call_deepseek_api(
    "解释一下机器学习的基本概念",
    api_key="your-api-key-here"
)
```

#### 运行 DeepSeek API 示例

```bash
# 直接运行示例脚本
python deepseek/deepseek_api.py
```

## 运行示例

### 使用命令行工具（推荐）

项目提供了命令行工具，可以方便地查看所有功能和执行操作。

#### 查看所有功能

```bash
# 方式1: 使用 main.py（推荐，会调用 python -m cli list）
python main.py list

# 方式2: 使用 CLI 模块
python -m cli list

# 方式3: 直接运行 CLI
python cli.py list
```

#### 查看特定功能详情

```bash
python -m cli info youtube_search
python -m cli info youtube_shorts
python -m cli info deepseek_api
python -m cli info downie_download
python -m cli info douyin_upload
```

#### 执行 YouTube 搜索

```bash
# 基本搜索
python -m cli youtube search "Python教程"

# 无头模式搜索（后台运行）
python -m cli youtube search "机器学习" --headless

# 搜索但不筛选最近上传
python -m cli youtube search "数据分析" --no-recent
```

### YouTube Shorts 视频信息提取

```bash
# 提取单个 YouTuber 的 Shorts 视频信息（提取20个）
python -m cli youtube shorts "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts"

# 提取更多视频（50个）
python -m cli youtube shorts "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts" --max 50

# 无头模式提取
python -m cli youtube shorts "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts" --headless

# 批量处理所有 YouTuber（从 youtubers.json 读取）
python youtube_crawler/extract_shorts.py --all 20
```

**批量处理说明**：
1. 在 `data/youtubers/youtubers.json` 文件中配置 YouTuber 列表
2. 运行 `python youtube_crawler/extract_shorts.py --all 20` 批量处理
3. 所有 YouTuber 的视频信息会保存到 `data/search_result/日期_youtuber_shorts_www.youtube.com.json`

**youtubers.json 格式**：
```json
{
    "youtubers": [
        {
            "name": "@KaradenizliMacerac%C4%B1",
            "url": "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts"
        },
        {
            "name": "@bampvideo8k",
            "url": "https://www.youtube.com/@bampvideo8k/shorts"
        }
    ]
}
```

### Downie 4 下载 YouTube 视频

```bash
# 使用 Downie 4 下载 YouTube 视频
python -m cli downie download "https://www.youtube.com/watch?v=VIDEO_ID"
```

### YouTube Shorts 批量下载

```bash
# 下载当天的视频（自动检查已下载记录）
python youtube_crawler/download_shorts.py

# 下载指定日期的视频
python youtube_crawler/download_shorts.py 20251230

# 下载指定日期的视频，间隔5秒
python youtube_crawler/download_shorts.py 20251230 5
```

**业务逻辑流程**：
1. **查找结果文件**：
   - 如果没有指定日期，自动使用今天的日期（从系统时间获取）
   - 从 `data/search_result` 目录查找文件：`{日期}_youtuber_shorts_www.youtube.com.json`
   - 日期信息从文件名中提取（格式：yyyyMMdd）
2. **加载视频列表**：读取搜索结果文件，获取所有视频信息
3. **检查已下载记录**：
   - 从 `data/download_result/youtuber_shorts_www.youtube.com.json` 读取已下载的视频记录
   - 提取所有已下载视频的 URL 集合
   - 如果文件不存在，视为首次下载
4. **过滤已下载视频**：
   - 对比视频 URL，过滤掉已下载的视频
   - 显示过滤统计信息（总视频数、已下载数、待下载数）
   - 显示前5个被跳过视频的标题（用于确认）
   - 如果所有视频都已下载，直接返回，不执行下载
5. **批量下载**：
   - 遍历待下载的视频列表
   - 使用 Downie 4 下载每个视频（只打开一次应用）
   - 每个视频下载之间等待指定时间（默认2秒，可配置）
   - 记录下载状态（success/failed/error）
6. **保存下载记录**：
   - 只保存成功下载的视频（`download_status == "success"`）
   - 合并到已存在的下载记录文件（避免重复）
   - 添加 `download_time` 字段记录下载时间
   - 更新 `last_updated` 字段
7. **去重机制**：通过 URL 对比确保不会重复下载同一个视频

### 抖音创作者平台上传本地视频

```bash
# 单个视频上传（正常模式，有浏览器界面）
python douyin/upload_video.py "/absolute/path/to/video.mp4"

# 单个视频上传（指定标题和话题）
python douyin/upload_video.py "/absolute/path/to/video.mp4" "视频标题" "#话题1 #话题2"

# 批量上传文件夹中的所有视频（目录见 config/store_config/download_config.py 的 DEFAULT_VIDEO_DOWNLOAD_DIR）
python douyin/upload_video.py --folder "<你的视频下载目录>"

# 批量上传（设置为公开，自动发布，间隔10秒）
python douyin/upload_video.py --folder "<你的视频下载目录>" "公开" true 10

# 智能上传：自动选择当天播放量最多的2个已下载视频
python douyin/upload_video.py --today

# 智能上传（设置为公开，自动发布）
python douyin/upload_video.py --today "公开" true

# 智能上传（显式指定下载目录；省略时默认使用 DEFAULT_VIDEO_DOWNLOAD_DIR）
python douyin/upload_video.py --today "仅自己可见" false "<你的视频下载目录>"

> 默认下载目录可在 `config/store_config/download_config.py` 的 `DEFAULT_VIDEO_DOWNLOAD_DIR` 中修改。

# 登录抖音创作者平台（默认等待60秒）
python douyin/upload_video.py --login

# 登录并等待120秒
python douyin/upload_video.py --login 120
```

**功能说明**：
- **单个视频上传**：上传指定的视频文件，支持自定义标题、话题、可见性等
- **批量上传**：从文件夹中读取所有视频文件，依次上传（保持浏览器打开）
- **智能上传**：
  - 自动读取当天搜索的视频和已下载的视频
  - 选择播放量最多的2个视频进行上传
  - 通过标题前缀匹配查找本地视频文件（支持字符串规范化处理）
  - 如果选中的视频未找到，自动选择次优视频
  - 上传成功后自动移动文件到 `upload_douyin` 文件夹
- **登录功能**：登录抖音创作者平台并保存登录信息，后续上传时自动加载

### PrivadoVPN 应用管理

```bash
# 打开并自动连接
python -m cli vpn open
python vpn/open_privadovpn.py

# 关闭应用
python -m cli vpn close
python vpn/open_privadovpn.py --close
```

**功能说明**：
- **自动打开**：自动检查 PrivadoVPN 是否已在运行，如果未运行则自动打开
- **自动连接**：打开应用后自动点击"点击链接"按钮进行 VPN 连接
- **关闭应用**：支持优雅关闭和强制关闭，自动检查关闭状态
- **多路径支持**：自动在多个常见安装位置查找应用
- **智能查找**：尝试多种方法查找连接按钮（按钮文本、按钮位置等）
- **错误提示**：如果应用未找到或连接按钮未找到，会显示详细的错误信息

### 🔄 自动化工作流

自动化工作流整合了所有功能，实现从视频提取到上传的完整流程。

```bash
# 执行完整自动化工作流（默认：每个YouTuber提取1个视频，上传2个视频）
python -m cli workflow

# 自定义参数执行工作流
python -m cli workflow --max-videos-per-youtuber 5 --max-upload-videos 3

# 跳过步骤1（打开VPN）和步骤5（关闭VPN）
python -m cli workflow --skip-steps 1,5

# 只执行步骤2、3、4（提取、下载、检测下载完成）
python -m cli workflow --only-steps 2,3,4

# 只执行上传步骤
python -m cli workflow --only-steps 6

# 直接运行工作流脚本（支持所有参数）
python workflow/auto_workflow.py
python workflow/auto_workflow.py --skip-steps 1,5
python workflow/auto_workflow.py --only-steps 2,3,4
```

**功能说明**：
- **完整流程**：整合了 VPN 管理、视频提取、下载、上传等所有步骤，实现端到端的自动化
- **步骤控制**：支持跳过指定步骤或只执行部分步骤，灵活控制工作流执行
- **步骤说明**：
  1. **打开 VPN**：打开 PrivadoVPN 应用程序，等待60秒确保 VPN 连接网络
  2. **提取视频**：从 youtubers.json 读取配置，批量提取每个 YouTuber 的 YouTube Shorts 视频信息
  3. **下载视频**：使用 Downie 4 下载视频，自动检查已下载记录避免重复下载（通过标题对比去重）
  4. **检测下载完成**：等待所有视频下载完成（最多等待600秒）。如果所有视频都已下载，自动跳过此步骤
  5. **关闭 VPN**：关闭 PrivadoVPN 应用程序，等待60秒确保完全关闭
  6. **上传视频**：智能选择当天播放量最多的视频进行上传，支持标题时间优先级（最近7天，越近越优先）和播放量优先级
- **参数说明**：
  - `--max-videos-per-youtuber`：每个 YouTuber 提取的视频数量（默认: 1）
  - `--max-upload-videos`：上传的视频数量（默认: 2）
  - `--skip-steps`：要跳过的步骤编号，用逗号分隔（例如: 1,5 表示跳过步骤1和步骤5）
  - `--only-steps`：只执行的步骤编号，用逗号分隔（例如: 2,3,4 表示只执行步骤2、3、4）。如果指定了此参数，--skip-steps 将被忽略
- **智能特性**：
  - **自动去重**：下载前检查已下载记录（通过标题对比），避免重复下载
  - **智能跳过**：如果所有视频都已下载，自动跳过下载步骤和下载检测步骤
  - **智能上传选择**：优先选择标题中包含最近7天时间的视频（时间越近优先级越高），否则按播放量排序
  - **上传失败重试**：上传失败的视频（error 不为空）视为未上传，可重新上传
  - **跳过步骤2时自动读取**：如果跳过步骤2（提取视频），自动从当天的结果文件读取视频列表

**业务逻辑流程**：
1. **步骤1：打开 VPN**
   - 打开 PrivadoVPN 应用程序
   - 等待60秒确保 VPN 连接网络
   
2. **步骤2：提取视频**
   - 从 `data/youtubers/youtubers.json` 读取 YouTuber 列表配置
   - 批量提取每个 YouTuber 的 YouTube Shorts 视频信息
   - 结果保存到 `data/search_result/{日期}_youtuber_shorts_www.youtube.com.json`
   
3. **步骤3：下载视频**
   - 从 `data/download_result/youtuber_shorts_www.youtube.com.json` 加载已下载记录
   - 通过标题规范化对比，过滤掉已下载的视频
   - 使用 Downie 4 下载新视频，每个视频之间等待2秒
   - 保存下载结果到文件，添加 download_time 字段
   - 等待180秒让 Downie 4 开始下载
   - **如果所有视频都已下载，返回空列表（步骤4会自动跳过）**
   
4. **步骤4：检测下载完成**
   - 通过标题前缀匹配检查下载目录中的视频文件
   - 每10秒检查一次，最多等待600秒
   - **如果所有视频都已下载（步骤3返回空列表），自动跳过此步骤**
   
5. **步骤5：关闭 VPN**
   - 关闭 PrivadoVPN 应用程序
   - 等待60秒确保完全关闭
   
6. **步骤6：上传视频**
   - 从下载结果中读取今天下载的视频（通过 download_time 字段匹配）
   - 排除已成功上传的视频（success=true 且 error 为空）
   - 按优先级选择视频：标题时间（最近7天，越近越优先）> 播放量
   - 通过标题前缀匹配查找本地视频文件（在 `DEFAULT_VIDEO_DOWNLOAD_DIR` 指定目录）
   - 上传选中的视频到抖音创作者平台（最多上传指定数量）
   - 上传成功后自动移动文件到 `upload_douyin` 文件夹

### Python 代码使用示例

#### YouTube 搜索

```python
from youtube_crawler.search_video import YouTubeSearcher

with YouTubeSearcher(headless=False) as searcher:
    search_query = "你的搜索关键词"
    results = searcher.search_and_save(search_query, click_recent_upload=True)
    
    # 打印结果
    print(f"\n共找到 {len(results)} 个视频:")
    for i, video in enumerate(results, 1):
        print(f"\n{i}.    标题: {video['title']}")
        print(f"   类型: {'竖屏视频(SHORTS)' if video['is_shorts'] else '普通视频'}")
        print(f"   方向: {video['orientation']}")
        print(f"   时长: {video['duration']}")
        print(f"   分辨率: {video['resolution']}")
        print(f"   观看次数: {video['view_count']}")
        print(f"   发布时间: {video['publish_time']}")
        print(f"   链接: {video['url']}")
```

#### YouTube Shorts 提取

```python
from youtube_crawler.extract_shorts import extract_youtube_shorts, extract_all_youtubers_shorts

# 提取单个 YouTuber 的 Shorts 视频
videos = extract_youtube_shorts(
    "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts",
    max_videos=20,
    headless=False
)

for video in videos:
    print(f"标题: {video['title']}")
    print(f"URL: {video['url']}")
    print(f"播放次数: {video['view_count']}")

# 批量提取所有 YouTuber 的 Shorts 视频
all_results = extract_all_youtubers_shorts(max_videos=20, headless=False)
for name, videos in all_results.items():
    print(f"{name}: {len(videos)} 个视频")
```

#### 抖音视频上传

```python
from config.store_config.download_config import DEFAULT_VIDEO_DOWNLOAD_DIR
from douyin.upload_video import DouyinUploader

# 单个视频上传
with DouyinUploader(headless=False) as uploader:
    result = uploader.upload_video(
        video_path="/path/to/video.mp4",
        title=None,  # 优先 DeepSeek 生成，否则从文件名提取
        hashtags=None,  # 优先 DeepSeek 生成，否则从标题提取关键词
        cover_text=None,  # 使用标题
        visibility="仅自己可见",
        auto_publish=False
    )
    if result.get('success'):
        print(f"✅ 上传成功: {result.get('video_filename', 'N/A')}")
    else:
        print(f"❌ 上传失败: {result.get('error', '未知错误')}")

# 批量上传（从文件夹）
with DouyinUploader(headless=False) as uploader:
    results = uploader.upload_videos_from_folder(
        folder_path=DEFAULT_VIDEO_DOWNLOAD_DIR,
        visibility="仅自己可见",
        auto_publish=False,
        delay=5.0  # 每个视频之间的延迟（秒）
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
            print(f"   标题: {result.get('title', 'N/A')}")
            print(f"   话题: {result.get('hashtags', 'N/A')}")
        else:
            print(f"❌ {result.get('video_filename', 'N/A')}: {result.get('error', '未知错误')}")

# 登录抖音创作者平台
from douyin.upload_video import login_douyin

success = login_douyin(
    login_url="https://creator.douyin.com/",
    wait_time=60,  # 等待登录的时间（秒）
    headless=False
)
if success:
    print("✅ 登录成功！登录信息已保存")
else:
    print("❌ 登录失败或未完成")
```

#### PrivadoVPN 应用管理

```python
from vpn.open_privadovpn import (
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
    print("✅ PrivadoVPN 已关闭")
```

#### 自动化工作流

```python
from workflow.auto_workflow import AutoWorkflow

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
    print("❌ 工作流执行失败")
```

## 配置说明

### 视频过滤配置 (`config/video_filter_config/youtube_filter.py`)

控制哪些视频会被保存，支持以下过滤条件：

```python
# 总开关
FILTER_ENABLED = True  # 是否启用所有过滤

# 横屏/竖屏过滤
ORIENTATION_FILTER = {
    'enabled': False,
    'allowed': []  # ["横屏"] 或 ["竖屏"] 或 ["横屏", "竖屏"]
}

# 视频时长过滤（秒）
DURATION_FILTER = {
    'enabled': False,
    'min_seconds': None,  # 最小时长
    'max_seconds': None   # 最大时长
}

# 分辨率过滤
RESOLUTION_FILTER = {
    'enabled': False,
    'allowed': []  # ["1080p", "4K", "HD"]
}

# 播放量过滤
VIEW_COUNT_FILTER = {
    'enabled': False,
    'min_views': None,  # 最小播放量
    'max_views': None   # 最大播放量
}

# 发布天数过滤
PUBLISH_TIME_FILTER = {
    'enabled': False,
    'max_days': None  # 最大发布天数（如7表示只保留7天内发布的视频）
}

# 标题包含搜索词过滤
TITLE_CONTAINS_FILTER = {
    'enabled': True,
    'require_all': True  # True: 必须包含所有搜索词; False: 包含任意一个即可
}
```

### 存储配置 (`config/store_config/youtube_config.py`)

控制视频的保存数量和排序方式：

```python
# 保存条数限制
MAX_SAVE_COUNT = 3  # None 表示保存所有通过过滤的视频

# 优先级排序
PRIORITY_ORDER = ['publish_time', 'view_count', 'resolution']
# 可选值：'resolution'（分辨率）、'view_count'（播放次数）、'publish_time'（发布时间）

# 排序方向
PRIORITY_SORT_DIRECTION = {
    'resolution': 'desc',      # 降序：4K > 1080p > 720p
    'view_count': 'desc',      # 降序：播放量高的在前
    'publish_time': 'asc'      # 升序：最新的在前
}
```

### DeepSeek API 配置 (`deepseek/config/deepseek_config.json`)

配置 DeepSeek API 密钥：

```json
{
  "api_key": "your-deepseek-api-key-here"
}
```

**API Key 获取方式**：
1. 访问 [DeepSeek 官网](https://www.deepseek.com/) 注册账号
2. 在控制台获取 API Key
3. 将 API Key 填入 `deepseek/config/deepseek_config.json` 文件

**API Key 优先级**：
1. 直接传入的 `api_key` 参数（最高优先级）
2. `deepseek/config/deepseek_config.json` 配置文件
3. 环境变量 `DEEPSEEK_API_KEY`（最低优先级）

**使用环境变量**：
```bash
# Linux/macOS
export DEEPSEEK_API_KEY="your-api-key-here"

# Windows
set DEEPSEEK_API_KEY=your-api-key-here
```

## 数据存储

### 登录信息

- **位置**：`data/cookies/.youtube_cookies.json`
- **说明**：自动保存登录 cookies，下次运行时自动加载

### 搜索结果

#### YouTube 搜索结果

- **位置**：`data/search_result/{yyyyMMdd}_{域名}.json`
- **命名格式**：`20251214_www.youtube.com.json`
- **格式**：
```json
{
  "total": 43,
  "results": [
    {
      "search_query": "AAA 2025 SSERAFIM",
      "search_time": "2025-12-14 01:42:03",
      "is_shorts": false,
      "orientation": "横屏",
      "title": "LE SSERAFIM Full Performance at AAA 2025",
      "url": "https://www.youtube.com/watch?v=...",
      "url_relative": "/watch?v=...",
      "duration": "7:01",
      "resolution": "4K",
      "view_count": "6.6万次观看",
      "publish_time": "7天前"
    },
    ...
  ],
  "last_updated": "2025-12-14 01:42:03"
}
```

#### YouTube Shorts 提取结果

- **位置**：`data/search_result/{yyyyMMdd}_youtuber_shorts_{域名}.json`
- **命名格式**：`20251230_youtuber_shorts_www.youtube.com.json`
- **说明**：所有 YouTuber 的 Shorts 视频信息保存在同一个文件中（"youtuber" 是固定字符串）
- **格式**：
```json
{
  "total": 160,
  "results": [
    {
      "search_query": "@KaradenizliMacerac%C4%B1",
      "search_time": "2025-12-30 12:00:00",
      "is_shorts": true,
      "orientation": "竖屏",
      "title": "视频标题",
      "url": "https://www.youtube.com/shorts/VIDEO_ID",
      "url_relative": "/shorts/VIDEO_ID",
      "duration": "未知",
      "resolution": "未知",
      "view_count": "5万次观看",
      "publish_time": "未知"
    },
    ...
  ],
  "last_updated": "2025-12-30 12:30:00"
}
```

#### YouTube Shorts 下载结果

- **位置**：`data/download_result/youtuber_shorts_www.youtube.com.json`
- **说明**：记录所有已下载的视频信息，用于避免重复下载
- **格式**：
```json
{
  "total": 2,
  "results": [
    {
      "search_query": "@KaradenizliMacerac%C4%B1",
      "search_time": "2025-12-30 00:35:20",
      "is_shorts": true,
      "orientation": "竖屏",
      "title": "视频标题",
      "url": "https://www.youtube.com/shorts/VIDEO_ID",
      "url_relative": "/shorts/VIDEO_ID",
      "duration": "未知",
      "resolution": "未知",
      "view_count": "1.8万次观看",
      "publish_time": "未知",
      "download_time": "2025-12-30 01:05:25"
    }
  ],
  "last_updated": "2025-12-30 01:05:27"
}
```

### YouTuber 配置文件

- **位置**：`data/youtubers/youtubers.json`
- **说明**：用于批量处理 YouTube Shorts 提取的 YouTuber 列表
- **格式**：
```json
{
    "youtubers": [
        {
            "name": "@KaradenizliMacerac%C4%B1",
            "url": "https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts"
        },
        {
            "name": "@bampvideo8k",
            "url": "https://www.youtube.com/@bampvideo8k/shorts"
        }
    ]
}
```

### 上传结果

#### 抖音视频上传结果

- **位置**：`data/upload_result/douyin/upload_www.youtube.com.json`
- **说明**：记录所有上传到抖音的视频信息
- **格式**：
```json
{
  "total": 1,
  "results": [
    {
      "video_path": "/absolute/path/to/video.mp4",
      "video_filename": "video.mp4",
      "video_size": 12345678,
      "title": "视频标题",
      "hashtags": "#话题1 #话题2",
      "cover_text": "封面文字",
      "visibility": "仅自己可见",
      "auto_publish": false,
      "upload_time": "2025-12-30 12:00:00",
      "success": true
    }
  ],
  "last_updated": "2025-12-30 12:00:00"
}
```

## API 参考

### YouTubeSearcher 类

#### 初始化

```python
YouTubeSearcher(headless: bool = False)
```

- `headless`: 是否使用无头模式（不显示浏览器窗口）

#### 主要方法

##### `search(search_query: str, click_recent_upload: bool = True)`

执行搜索操作。

- `search_query`: 搜索关键词
- `click_recent_upload`: 是否点击"最近上传"按钮

##### `parse_search_results() -> List[Dict]`

解析当前页面的搜索结果，返回视频信息列表。

##### `save_results(results: List[Dict])`

保存搜索结果到文件。

##### `search_and_save(search_query: str, click_recent_upload: bool = True) -> List[Dict]`

执行搜索、解析和保存的完整流程，返回结果列表。

**执行流程**：
1. 加载 cookies
2. 访问 YouTube 首页
3. 输入搜索词并搜索
4. 点击"最近上传"按钮（可选）
5. 解析搜索结果（最多100条）
6. 应用视频过滤
7. 应用优先级排序
8. 应用保存条数限制
9. 保存结果
10. 等待30秒（倒计时显示）

##### `load_cookies()`

加载已保存的登录信息。

##### `save_cookies()`

保存当前登录信息。

##### `close()`

关闭浏览器。

### YouTubeShortsExtractor 类

#### 初始化

```python
YouTubeShortsExtractor(headless: bool = False, browser_type: str = "chromium")
```

- `headless`: 是否使用无头模式（不显示浏览器窗口）
- `browser_type`: 浏览器类型 ("chromium", "firefox", "webkit")

#### 主要方法

##### `extract_shorts(shorts_url: str, max_videos: int = 20) -> List[Dict]`

从单个 YouTube Shorts 页面提取视频信息。

- `shorts_url`: Shorts 页面 URL，如 `https://www.youtube.com/@KaradenizliMacerac%C4%B1/shorts`
- `max_videos`: 最大提取视频数量，默认20

**返回**：视频信息列表，每个视频包含：
- `title`: 视频标题
- `url`: 完整视频 URL
- `url_relative`: 相对 URL
- `view_count`: 播放次数
- `is_shorts`: 是否为 Shorts 视频
- `orientation`: 视频方向（竖屏/横屏）
- `search_query`: YouTuber 名称（如 `@KaradenizliMacerac%C4%B1`）

##### `extract_all_youtubers(max_videos: int = 20, youtubers_path: Optional[Path] = None) -> Dict[str, List[Dict]]`

批量提取所有 YouTuber 的 Shorts 视频信息。

- `max_videos`: 每个 YouTuber 最大提取视频数量，默认20
- `youtubers_path`: youtubers.json 文件路径，如果为 None 则使用默认路径

**返回**：字典，key 为 YouTuber 名称，value 为视频信息列表

**执行流程**：
1. 从 `data/youtubers/youtubers.json` 读取 YouTuber 列表
2. 依次访问每个 YouTuber 的 Shorts 页面
3. 滚动页面加载更多视频
4. 提取前 N 个视频信息
5. 将所有视频信息保存到统一文件：`日期_youtuber_shorts_www.youtube.com.json`

##### `load_youtubers(youtubers_path: Optional[Path] = None) -> List[Dict]`

从 youtubers.json 文件加载 YouTuber 列表。

- `youtubers_path`: youtubers.json 文件路径，如果为 None 则使用默认路径

**返回**：YouTuber 列表，每个元素包含 `name` 和 `url`

##### `load_cookies()`

加载保存的 cookies。

##### `save_cookies()`

保存当前 cookies。

##### `close()`

关闭浏览器。

### DeepSeek API 函数

#### `call_deepseek_api(prompt, api_key=None, model="deepseek-chat", temperature=0.7, max_tokens=2000)`

调用 DeepSeek API 进行对话。

**参数**：
- `prompt` (str, 必需): 输入的提示词
- `api_key` (str, 可选): API 密钥，如果为 None 则从配置文件或环境变量读取
- `model` (str, 可选): 使用的模型，默认为 "deepseek-chat"
- `temperature` (float, 可选): 温度参数，控制输出的随机性（0-1），默认 0.7
- `max_tokens` (int, 可选): 最大生成 token 数，默认 2000

**返回值**：
- `Dict[str, Any]`: API 响应数据，包含 `choices`、`usage` 等信息
- `None`: 如果请求失败返回 None

**功能特性**：
- ✅ 自动从配置文件或环境变量读取 API Key
- ✅ 打印输入参数和 API 响应内容
- ✅ 显示 Token 使用情况
- ✅ 详细的错误处理和提示信息

**示例**：
```python
from deepseek.deepseek_api import call_deepseek_api

# 基本调用
result = call_deepseek_api("什么是 Python？")

# 自定义参数
result = call_deepseek_api(
    prompt="写一个快速排序算法",
    temperature=0.5,
    max_tokens=1500
)
```

## 项目结构

```
crawler/
├── cli.py                    # 命令行工具
├── main.py                   # 主入口文件
├── youtube_crawler/
│   ├── search_video.py      # YouTube 搜索功能模块
│   └── extract_shorts.py    # YouTube Shorts 视频信息提取模块
├── downie4/
│   └── download_youtube.py  # Downie 4 YouTube 视频下载模块
├── douyin/
│   └── upload_video.py      # 抖音创作者平台视频上传模块
├── vpn/
│   └── open_privadovpn.py   # PrivadoVPN 应用打开模块
├── deepseek/
│   ├── deepseek_api.py      # DeepSeek API 调用模块
│   └── config/
│       └── deepseek_config.json    # DeepSeek API 配置
├── config/
│   ├── video_filter_config/
│   │   └── youtube_filter.py    # 视频过滤配置
│   └── store_config/
│       └── youtube_config.py    # 存储和排序配置
├── data/
│   ├── cookies/
│   │   ├── .youtube_cookies.json      # YouTube 登录信息
│   │   └── .douyin_cookies.json       # 抖音登录信息
│   ├── search_result/
│   │   ├── {yyyyMMdd}_{域名}.json              # YouTube 搜索结果
│   │   └── {yyyyMMdd}_youtuber_shorts_{域名}.json  # YouTube Shorts 提取结果
│   └── youtubers/
│       └── youtubers.json   # YouTuber 列表配置（用于批量提取 Shorts）
├── requirements.txt          # 依赖包
└── README.md                # 本文档
```

## 注意事项

### ⚠️ 重要提示

1. **遵守 YouTube 服务条款**：请确保你的使用符合 YouTube 的服务条款和使用政策
2. **合理使用频率**：避免过于频繁的请求，建议在请求之间添加适当的延迟
3. **Playwright 浏览器**：确保已运行 `playwright install chromium` 安装浏览器
4. **网络环境**：某些地区可能需要代理才能访问 YouTube

### 🔧 常见问题

#### 1. Playwright 浏览器未安装

**错误信息**：`Executable doesn't exist` 或浏览器启动失败

**解决方法**：
```bash
# 安装 Chromium 浏览器
playwright install chromium

# 如果安装失败，可以尝试指定系统
playwright install chromium --with-deps
```

#### 2. Playwright 安装问题

**错误信息**：安装 Playwright 时出错

**解决方法**：
- 确保网络连接正常（需要下载浏览器二进制文件）
- 如果下载慢，可以设置代理：`export HTTPS_PROXY=your_proxy`
- 或手动下载：访问 [Playwright 下载页面](https://playwright.dev/python/docs/browsers)

#### 2. 元素定位失败

**可能原因**：
- YouTube 页面结构发生变化
- 网络加载慢，元素未及时加载

**解决方法**：
- 增加等待时间
- 检查页面是否正常加载
- 更新选择器
- Playwright 的等待机制更智能，通常会自动等待元素出现

#### 3. 浏览器启动慢

**可能原因**：
- 首次启动需要初始化
- 系统资源不足

**解决方法**：
- 首次运行会较慢，后续会更快
- 使用无头模式（`headless=True`）可以加快速度
- 确保系统有足够的内存和 CPU 资源

#### 4. 登录信息失效

**解决方法**：
- 删除 `data/cookies/.youtube_cookies.json`
- 重新运行程序，手动登录一次
- 程序会自动保存新的登录信息

#### 5. 过滤功能不生效

**可能原因**：
- `FILTER_ENABLED = False`（总开关未启用）
- 过滤条件配置不正确

**解决方法**：
- 检查 `config/video_filter_config/youtube_filter.py` 中的 `FILTER_ENABLED` 是否为 `True`
- 检查各个过滤条件的 `enabled` 字段
- 查看日志输出，确认过滤是否执行

#### 6. 优先级排序不生效

**可能原因**：
- `PRIORITY_ORDER = []`（未设置排序）

**解决方法**：
- 在 `config/store_config/youtube_config.py` 中设置 `PRIORITY_ORDER`
- 例如：`PRIORITY_ORDER = ['view_count']` 按播放次数排序

#### 7. DeepSeek API Key 未找到

**错误信息**：`❌ 错误: 未找到 API Key`

**解决方法**：
1. 在 `deepseek/config/deepseek_config.json` 中设置 `api_key`：
   ```json
   {
     "api_key": "your-api-key-here"
   }
   ```
2. 或设置环境变量：
   ```bash
   export DEEPSEEK_API_KEY="your-api-key-here"
   ```
3. 或在调用时直接传入：
   ```python
   call_deepseek_api("prompt", api_key="your-api-key-here")
   ```

#### 8. DeepSeek API 请求失败

**可能原因**：
- API Key 无效或过期
- 网络连接问题
- API 服务暂时不可用

**解决方法**：
- 检查 API Key 是否正确
- 检查网络连接
- 查看错误详情，根据错误信息调整参数
- 确认账户余额是否充足

#### 9. Playwright vs Selenium

**为什么使用 Playwright？**
- ✅ 更快的执行速度
- ✅ 更稳定的元素定位
- ✅ 自动等待机制更智能
- ✅ 内置网络拦截和模拟
- ✅ 更好的跨浏览器支持
- ✅ 不需要单独的驱动管理

## 配置示例

### 示例1：只保存高质量横屏视频

**`config/video_filter_config/youtube_filter.py`**:
```python
FILTER_ENABLED = True
ORIENTATION_FILTER = {
    'enabled': True,
    'allowed': ["横屏"]
}
RESOLUTION_FILTER = {
    'enabled': True,
    'allowed': ["1080p", "4K"]
}
VIEW_COUNT_FILTER = {
    'enabled': True,
    'min_views': 10000  # 至少1万播放量
}
```

**`config/store_config/youtube_config.py`**:
```python
MAX_SAVE_COUNT = 20
PRIORITY_ORDER = ['resolution', 'view_count']
```

### 示例2：只保存最新的视频

**`config/video_filter_config/youtube_filter.py`**:
```python
FILTER_ENABLED = True
PUBLISH_TIME_FILTER = {
    'enabled': True,
    'max_days': 7  # 只保留7天内发布的视频
}
```

**`config/store_config/youtube_config.py`**:
```python
MAX_SAVE_COUNT = 50
PRIORITY_ORDER = ['publish_time', 'view_count']
```

### 示例3：只保存标题包含搜索词的视频

**`config/video_filter_config/youtube_filter.py`**:
```python
FILTER_ENABLED = True
TITLE_CONTAINS_FILTER = {
    'enabled': True,
    'require_all': True  # 标题必须包含所有搜索词
}
```

**`config/store_config/youtube_config.py`**:
```python
MAX_SAVE_COUNT = None  # 保存所有通过过滤的视频
PRIORITY_ORDER = ['view_count']  # 按播放量排序
```

### 示例4：使用 DeepSeek API 进行智能问答

**`deepseek/config/deepseek_config.json`**:
```json
{
  "api_key": "sk-your-api-key-here"
}
```

**Python 代码**:
```python
from deepseek.deepseek_api import call_deepseek_api

# 基本问答
result = call_deepseek_api("解释一下什么是机器学习")

# 代码生成
result = call_deepseek_api(
    "用 Python 写一个快速排序函数",
    temperature=0.3,  # 较低温度，输出更确定
    max_tokens=500
)

# 创意写作
result = call_deepseek_api(
    "写一首关于春天的短诗",
    temperature=0.9,  # 较高温度，输出更随机
    max_tokens=200
)
```

## 功能详解

### 搜索限制

- **最大解析数量**：每次搜索最多解析 100 条视频
- **目的**：提高搜索效率，避免解析过多数据

### 视频过滤

过滤功能在保存前自动应用，只有通过所有过滤条件的视频才会被保存。

**支持的过滤条件**：
1. **横屏/竖屏过滤**：筛选特定方向的视频
2. **时长过滤**：设置视频时长范围（秒）
3. **分辨率过滤**：筛选特定分辨率的视频
4. **播放量过滤**：设置播放量范围
5. **发布天数过滤**：只保留指定天数内发布的视频
6. **标题匹配过滤**：检查标题是否包含搜索词

### 优先级排序

在保存前对视频进行排序，优先保存高质量视频。

**支持的排序维度**：
- **分辨率**：4K > 1080p > 720p > HD
- **播放次数**：播放量高的在前
- **发布时间**：最新的在前

**排序方式**：
- 支持单维度排序：`['view_count']`
- 支持多维度组合排序：`['resolution', 'view_count', 'publish_time']`
- 每个维度可独立设置排序方向（升序/降序）

### 保存限制

- **条数限制**：可配置保存的视频条数（`MAX_SAVE_COUNT`）
- **优先级保存**：结合排序功能，优先保存高质量视频
- **文件命名**：按日期和域名命名，便于管理

## 工作流程

```
1. 从本地文件加载 cookies
2. 访问 YouTube 首页
3. 输入搜索词
4. 点击搜索按钮
5. 点击"最近上传"按钮（可选）
6. 解析搜索结果（最多100条）
7. 应用视频过滤条件
8. 应用优先级排序
9. 应用保存条数限制
10. 保存结果到文件
11. 等待30秒（倒计时显示）
```

## 开发计划

- [x] 支持视频过滤功能
- [x] 支持优先级排序
- [x] 支持保存条数限制
- [x] 支持搜索限制（最多100条）
- [x] 集成 DeepSeek API 功能
- [x] 支持 YouTube Shorts 视频信息提取
- [x] 支持批量处理多个 YouTuber 的 Shorts 提取
- [ ] 支持批量搜索
- [ ] 支持视频详情页信息提取
- [ ] 支持评论爬取
- [ ] 添加代理支持
- [ ] 支持多线程/异步处理
- [ ] 添加数据导出功能（CSV、Excel）
- [ ] 添加 DeepSeek API 命令行工具

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请提交 Issue。

