# YouTube to Ebook

把喜欢的 YouTube 频道转换为适合阅读的长文章，并制作成 EPUB 电子书。文章由本机 Ollama 模型生成，不需要 Anthropic API。

## 功能

- 获取频道最新的长视频并过滤 Shorts
- 通过 Supadata 获取字幕
- 通过本机 Ollama 把字幕整理成杂志风格文章
- 生成适合手机和电子书阅读器的 EPUB
- 可选使用 Gmail 发送电子书
- 提供 Streamlit 管理界面和 macOS 定时运行配置

## 准备工作

- Python 3.9 或更高版本
- [Ollama](https://ollama.com/download)
- YouTube Data API Key
- Supadata API Key
- Gmail 应用专用密码，仅在需要邮件发送时配置

## 快速开始

```bash
git clone https://github.com/rachelhomeland/youtube-to-ebook.git
cd youtube-to-ebook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

安装并打开 Ollama，然后下载默认模型：

```bash
ollama pull qwen3.5:4b
```

复制配置文件：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写 YouTube 和 Supadata 的 Key：

```dotenv
YOUTUBE_API_KEY=你的_YouTube_API_Key
SUPADATA_API_KEY=你的_Supadata_API_Key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
```

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

启动网页管理界面：

```bash
pip install streamlit
python -m streamlit run dashboard.py
```

## API 配置

### YouTube Data API

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)。
2. 创建项目并启用 YouTube Data API v3。
3. 创建 API Key，填入 `.env` 的 `YOUTUBE_API_KEY`。

### Supadata

1. 在 [Supadata](https://supadata.ai/) 创建账号并获取 API Key。
2. 将 Key 填入 `.env` 的 `SUPADATA_API_KEY`。

Supadata 负责获取视频字幕。它与本地 Ollama 分开工作，因此即使文章生成完全免费，字幕服务仍需要单独配置。

### Gmail，可选

未配置 Gmail 时，`main.py` 会跳过邮件发送，并把 HTML 与 EPUB 保存到 `newsletters/`。需要邮件发送时，在 Google 账号中创建应用专用密码，然后填写：

```dotenv
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

## Ollama 模型

默认模型适合内存较小的 Mac：

```dotenv
OLLAMA_MODEL=qwen3.5:4b
```

内存较充足时可以换成质量更高的模型：

```bash
ollama pull qwen3.5:9b
```

```dotenv
OLLAMA_MODEL=qwen3.5:9b
```

模型在本机运行，不按 Token 收费。首次使用需要下载模型文件。

## macOS 定时运行

本地 Ollama 只能在自己的电脑上访问，因此电子书生成应通过 macOS `launchd` 在本机运行。先记录项目的绝对路径，例如 `/Users/yourname/youtube-to-ebook`，并执行 `mkdir -p logs`。然后在复制 plist 前，将 `run_newsletter.sh` 中全部 3 行（共 4 个路径字符串）、以及 `com.youtube.newsletter.plist` 中全部 4 处 `/Users/bytedance/youtube-newsletter` 替换为该绝对路径。`run_newsletter.sh` 中的 `python3` 也应替换为 `which python3` 输出的路径（如果该 Python 才安装了项目依赖）。

检查 plist 语法后再安装：

```bash
plutil -lint com.youtube.newsletter.plist
cp com.youtube.newsletter.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.youtube.newsletter.plist
```

Mac 必须处于开机状态，Ollama 也必须已经启动。GitHub Actions 只运行测试，不会生成或发送电子书。

## 常见问题

### 无法连接 Ollama

打开 Ollama 应用，并确认本地接口可访问：

```bash
curl http://localhost:11434/api/tags
```

### 提示模型未安装

按照错误信息下载当前配置的模型，例如：

```bash
ollama pull qwen3.5:4b
```

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

测试使用模拟响应，不需要真实 API Key，也不需要正在运行的 Ollama。

## 项目结构

```text
├── main.py                 # 完整处理流程
├── get_videos.py           # 获取频道最新视频
├── get_transcripts.py      # 通过 Supadata 获取字幕
├── ollama_client.py        # 本地 Ollama 配置和状态检查
├── write_articles.py       # 把字幕整理成文章
├── send_email.py           # 生成 EPUB 并发送邮件
├── dashboard.py            # Streamlit 管理界面
├── video_tracker.py        # 避免重复处理视频
├── .env.example            # 配置示例
└── newsletters/            # 本地生成的归档，不提交到 Git
```

## 上游项目与许可证

本项目 Fork 自 [zarazhangrui/youtube-to-ebook](https://github.com/zarazhangrui/youtube-to-ebook)，主要改动是使用本地 Ollama 代替付费 Anthropic API，并补充测试和中文使用说明。

项目使用 [MIT License](LICENSE)。
