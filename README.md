# YouTube to Ebook

把喜欢的 YouTube 频道转换为适合阅读的长文章，并制作成 EPUB 电子书。文章由 DeepSeek 云端 API 生成，不需要 Anthropic API，也不需要在电脑上安装本地大模型。

## 功能

- 获取频道最新的长视频并过滤 Shorts
- 可通过链接指定一个或多个视频，按需重新生成
- 通过 Supadata 获取字幕
- 通过 DeepSeek 把字幕整理成杂志风格文章
- 生成适合手机和电子书阅读器的 EPUB
- 可选使用 Gmail 发送电子书
- 提供 Streamlit 管理界面和 macOS 定时运行配置

## 准备工作

- Python 3.9 或更高版本
- DeepSeek API Key
- YouTube Data API Key
- Supadata API Key
- Gmail 应用专用密码，仅在需要邮件发送时配置

DeepSeek 是云端付费服务，会按 Token 计费。生成文章时，视频标题、简介和字幕会发送给 DeepSeek。请先查看 [DeepSeek API 文档](https://api-docs.deepseek.com/) 和[当前价格](https://api-docs.deepseek.com/quick_start/pricing-details-cny/)。

## 快速开始

```bash
git clone https://github.com/rachelhomeland/youtube-to-ebook.git
cd youtube-to-ebook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys)创建 API Key。然后编辑 `.env`，至少填写下面三个服务的 Key：

```dotenv
YOUTUBE_API_KEY=你的_YouTube_API_Key
SUPADATA_API_KEY=你的_Supadata_API_Key
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key

DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
DEEPSEEK_MODEL=deepseek-v4-flash
```

不要把真实 API Key 上传到 GitHub。项目已经忽略本机 `.env` 文件；只需在自己的电脑上填写。

## 配置频道

打开 `get_videos.py`，编辑 `CHANNELS` 列表，使用频道主页上的 `@handle`：

```python
CHANNELS = [
    "@veritasium",
    "@3blue1brown",
]
```

## 运行

运行完整流程：

```bash
python main.py
```

只处理某一个指定视频：

```bash
python main.py --url "https://www.youtube.com/watch?v=视频ID"
```

一次处理多个指定视频时，重复使用 `--url`：

```bash
python main.py \
  --url "https://www.youtube.com/watch?v=第一个视频ID" \
  --url "https://youtu.be/第二个视频ID"
```

指定链接模式会跳过频道扫描和“已处理”过滤，因此同一个视频也可以重新生成；为避免误发邮件，该模式默认只把 HTML 与 EPUB 保存到 `newsletters/`。

频道模式也可以强制只保存到本地：

```bash
python main.py --no-email
```

启动网页管理界面：

```bash
pip install streamlit
python -m streamlit run dashboard.py
```

未配置 Gmail 时，程序不会发送邮件，而是把生成的 HTML 与 EPUB 保存到 `newsletters/`。

## API 配置

### DeepSeek

项目通过 DeepSeek 官方的 Anthropic 兼容接口生成文章：

```dotenv
DEEPSEEK_API_KEY=你的_DeepSeek_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
DEEPSEEK_MODEL=deepseek-v4-flash
```

默认模型是 `deepseek-v4-flash`。如 DeepSeek 后续调整可用模型，可通过 `DEEPSEEK_MODEL` 修改，无需改代码。依赖中的 `anthropic` Python 包只作为兼容接口客户端使用，并不会连接 Anthropic 或要求 Anthropic Key。

### YouTube Data API

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)。
2. 创建项目并启用 YouTube Data API v3。
3. 创建 API Key，填入 `.env` 的 `YOUTUBE_API_KEY`。

### Supadata

1. 在 [Supadata](https://supadata.ai/) 创建账号并获取 API Key。
2. 将 Key 填入 `.env` 的 `SUPADATA_API_KEY`。

Supadata 负责获取视频字幕，DeepSeek 负责把字幕改写成文章，两者需要分别配置。

### Gmail，可选

需要邮件发送时，在 Google 账号中创建应用专用密码，然后填写：

```dotenv
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

## macOS 定时运行

电子书生成可通过 macOS `launchd` 在本机定时运行。先记录项目的绝对路径，例如 `/Users/yourname/youtube-to-ebook`，并执行 `mkdir -p logs`。复制 plist 前，将 `run_newsletter.sh` 中的项目路径、以及 `com.youtube.newsletter.plist` 中全部 `/Users/bytedance/youtube-newsletter` 替换为实际路径。`run_newsletter.sh` 中的 `python3` 也应替换为 `which python3` 输出的路径（如果该 Python 才安装了项目依赖）。

检查 plist 语法后再安装：

```bash
plutil -lint com.youtube.newsletter.plist
cp com.youtube.newsletter.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.youtube.newsletter.plist
```

Mac 必须处于开机并联网状态。GitHub Actions 只运行模拟测试，不会调用 DeepSeek、生成电子书或发送邮件。

## 常见问题

### 提示填写 `DEEPSEEK_API_KEY`

确认已经把 `.env.example` 复制为 `.env`，并把 DeepSeek 开放平台生成的真实 Key 填入 `DEEPSEEK_API_KEY`。不要保留空值或示例文字。

### DeepSeek 返回 401、402 或额度错误

- 401：检查 API Key 是否正确、是否包含多余空格。
- 402 或余额相关提示：登录 DeepSeek 开放平台检查余额和计费状态。
- 模型不存在：到官方文档确认当前模型名，再修改 `DEEPSEEK_MODEL`。

### 自动运行时提示找不到 Python 模块

执行 `which python3` 找到正确的 Python 路径，并更新 `run_newsletter.sh`、Dashboard 启动配置和 plist 中的 Python 路径。

### 没有获取到字幕

确认 `SUPADATA_API_KEY` 有效，并检查该视频是否提供字幕。部分视频可能没有可用字幕。

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest -v
python -m compileall -q .
```

测试使用模拟响应，不需要真实 API Key，也不会产生 DeepSeek 费用。

## 项目结构

```text
├── main.py                 # 完整处理流程
├── get_videos.py           # 获取频道最新视频
├── get_transcripts.py      # 通过 Supadata 获取字幕
├── deepseek_client.py      # DeepSeek 配置和兼容客户端
├── write_articles.py       # 把字幕整理成文章
├── send_email.py           # 生成 EPUB 并可选发送邮件
├── dashboard.py            # Streamlit 管理界面
├── video_tracker.py        # 避免重复处理视频
├── .env.example            # 配置示例
└── newsletters/            # 本地生成的归档，不提交到 Git
```

## 上游项目与许可证

本项目 Fork 自 [zarazhangrui/youtube-to-ebook](https://github.com/zarazhangrui/youtube-to-ebook)，主要改动是使用 DeepSeek API 代替 Anthropic API，并补充测试、中文使用说明和无需 Gmail 的本地归档流程。

项目使用 [MIT License](LICENSE)。
