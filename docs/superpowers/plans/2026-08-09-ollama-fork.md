# Ollama-Based YouTube to Ebook Fork Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `rachelhomeland/youtube-to-ebook` as a tested fork that generates articles through a configurable local Ollama model without requiring an Anthropic account.

**Architecture:** Keep the existing video, transcript, ebook, email, dashboard, and tracking modules. Add a focused Ollama adapter that loads configuration, builds the Anthropic-compatible local client, and verifies the local server/model; inject that adapter into the existing article-writing boundary so tests never need live services.

**Tech Stack:** Python 3.8+, `anthropic` Python SDK pointed at Ollama's Anthropic-compatible endpoint, `requests`, `python-dotenv`, `pytest`, Streamlit, GitHub Actions.

## Global Constraints

- Keep the repository name `youtube-to-ebook`.
- Target personal local use on macOS for the first release.
- Default model: `qwen3.5:4b`.
- Default server: `http://localhost:11434`.
- Do not require or document a real Anthropic API key.
- Preserve the MIT license and credit `zarazhangrui/youtube-to-ebook` as the upstream project.
- Keep YouTube Data API, Supadata transcript retrieval, optional Gmail delivery, EPUB generation, tracking, and “The Digest” dashboard identity.
- Do not add multiple model providers, public hosting, dashboard redesign, or cloud ebook generation.
- Tests must not require YouTube, Supadata, Gmail, Ollama, or other credentials.
- Never commit `.env`, credentials, generated newsletters, or personal email addresses.

---

## File Map

- Create `ollama_client.py`: local model configuration, client construction, readiness validation, and user-facing setup errors.
- Modify `write_articles.py`: retain the existing public article functions while using the Ollama adapter and dependency injection.
- Modify `main.py`: provider-neutral command-line wording.
- Create `tests/test_ollama_client.py`: configuration and readiness unit tests.
- Create `tests/test_write_articles.py`: prompt, response, failure, and batch behavior tests.
- Create `tests/test_env_example.py`: parse the shipped example through the real Ollama configuration loader.
- Create `requirements-dev.txt`: repeatable test dependencies.
- Modify `requirements.txt`: remove the unused legacy transcript client while retaining runtime dependencies.
- Modify `.env.example`, `README.md`, `SKILL.md`, and `dashboard.py`: accurate Chinese-first setup and Ollama wording.
- Create `LICENSE`: standard MIT terms crediting the upstream author and fork maintainer.
- Replace `.github/workflows/newsletter.yml` with `.github/workflows/tests.yml`: credential-free validation only.

---

### Task 1: Add the Ollama configuration and readiness adapter

**Files:**
- Create: `ollama_client.py`
- Create: `tests/test_ollama_client.py`
- Create: `requirements-dev.txt`

**Interfaces:**
- Consumes: environment keys `OLLAMA_BASE_URL` and `OLLAMA_MODEL`; Ollama `GET /api/tags`; `anthropic.Anthropic(base_url, api_key)`.
- Produces: `OllamaConfig(base_url: str, model: str)`, `OllamaSetupError`, `load_ollama_config(environ=None)`, `create_ollama_client(config)`, and `ensure_ollama_ready(config, http_get=requests.get)`.

- [ ] **Step 1: Add the test dependency file**

Create `requirements-dev.txt`:

```text
-r requirements.txt
pytest
```

- [ ] **Step 2: Write failing configuration and client-construction tests**

Create `tests/test_ollama_client.py` with these tests:

```python
from unittest.mock import Mock

import pytest
import requests

import ollama_client


def test_load_config_uses_local_defaults():
    config = ollama_client.load_ollama_config({})
    assert config.base_url == "http://localhost:11434"
    assert config.model == "qwen3.5:4b"


def test_load_config_uses_environment_overrides():
    config = ollama_client.load_ollama_config({
        "OLLAMA_BASE_URL": "http://127.0.0.1:11435/",
        "OLLAMA_MODEL": "qwen3.5:9b",
    })
    assert config.base_url == "http://127.0.0.1:11435"
    assert config.model == "qwen3.5:9b"


def test_create_client_targets_ollama(monkeypatch):
    factory = Mock(return_value=object())
    monkeypatch.setattr(ollama_client.anthropic, "Anthropic", factory)
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    client = ollama_client.create_ollama_client(config)
    assert client is factory.return_value
    factory.assert_called_once_with(
        base_url="http://localhost:11434",
        api_key="ollama",
    )
```

- [ ] **Step 3: Run the focused tests and confirm they fail**

Run:

```bash
python -m pytest tests/test_ollama_client.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'ollama_client'`.

- [ ] **Step 4: Implement configuration and client construction**

Create the top half of `ollama_client.py`:

```python
from dataclasses import dataclass
import os

import anthropic
import requests
from dotenv import load_dotenv


DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:4b"


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    model: str


class OllamaSetupError(RuntimeError):
    """Raised when the local Ollama service is not ready."""


def load_ollama_config(environ=None):
    load_dotenv()
    values = os.environ if environ is None else environ
    base_url = values.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = values.get("OLLAMA_MODEL", DEFAULT_MODEL).strip()
    return OllamaConfig(base_url=base_url, model=model)


def create_ollama_client(config):
    return anthropic.Anthropic(
        base_url=config.base_url,
        api_key="ollama",
    )
```

- [ ] **Step 5: Run the configuration tests and confirm they pass**

Run:

```bash
python -m pytest tests/test_ollama_client.py -v
```

Expected: three tests pass.

- [ ] **Step 6: Write failing readiness tests**

Append to `tests/test_ollama_client.py`:

```python
class FakeResponse:
    def __init__(self, models, status_code=200):
        self._models = models
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"models": [{"name": name} for name in self._models]}


def test_readiness_accepts_installed_model():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse(["qwen3.5:4b"]))
    ollama_client.ensure_ollama_ready(config, http_get=http_get)
    http_get.assert_called_once_with(
        "http://localhost:11434/api/tags",
        timeout=5,
    )


def test_readiness_explains_unavailable_server():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(side_effect=requests.ConnectionError("refused"))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "无法连接 Ollama" in str(error.value)
    assert "http://localhost:11434" in str(error.value)


def test_readiness_explains_missing_model():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse(["qwen3.5:9b"]))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "qwen3.5:4b" in str(error.value)
    assert "ollama pull qwen3.5:4b" in str(error.value)


def test_readiness_explains_http_failure():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse([], status_code=500))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "检查 Ollama 状态失败" in str(error.value)
```

- [ ] **Step 7: Run the readiness tests and confirm they fail**

Run:

```bash
python -m pytest tests/test_ollama_client.py -v
```

Expected: four readiness tests fail because `ensure_ollama_ready` is not defined.

- [ ] **Step 8: Implement readiness validation**

Append to `ollama_client.py`:

```python
def ensure_ollama_ready(config, http_get=requests.get):
    tags_url = f"{config.base_url}/api/tags"
    try:
        response = http_get(tags_url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        if isinstance(exc, requests.ConnectionError):
            raise OllamaSetupError(
                f"无法连接 Ollama：请确认应用已经启动，地址为 {config.base_url}"
            ) from exc
        raise OllamaSetupError(f"检查 Ollama 状态失败：{exc}") from exc
    except ValueError as exc:
        raise OllamaSetupError("Ollama 返回了无法解析的状态信息") from exc

    installed = {
        item.get("name")
        for item in payload.get("models", [])
        if item.get("name")
    }
    if config.model not in installed:
        raise OllamaSetupError(
            f"未安装模型 {config.model}，请运行：ollama pull {config.model}"
        )
```

- [ ] **Step 9: Run the adapter tests**

Run:

```bash
python -m pytest tests/test_ollama_client.py -v
```

Expected: all seven tests pass.

- [ ] **Step 10: Commit the adapter**

```bash
git add ollama_client.py tests/test_ollama_client.py requirements-dev.txt
git commit -m "feat: add local Ollama adapter"
```

---

### Task 2: Route article generation through Ollama

**Files:**
- Modify: `write_articles.py:1-108`
- Modify: `main.py:50-52`
- Create: `tests/test_write_articles.py`

**Interfaces:**
- Consumes: `OllamaConfig`, `load_ollama_config`, `create_ollama_client`, and `ensure_ollama_ready` from Task 1.
- Produces: backward-compatible `write_article(video, *, article_client=None, config=None) -> str | None` and `write_articles_for_videos(videos, *, article_client=None, config=None, readiness_check=ensure_ollama_ready) -> list[dict]`.

- [ ] **Step 1: Write failing article-generation tests**

Create `tests/test_write_articles.py`:

```python
from types import SimpleNamespace
from unittest.mock import Mock

from ollama_client import OllamaConfig, OllamaSetupError
import write_articles


CONFIG = OllamaConfig(
    base_url="http://localhost:11434",
    model="qwen3.5:4b",
)


def video(description="Useful description"):
    return {
        "title": "A useful talk",
        "channel": "Example Channel",
        "url": "https://youtube.com/watch?v=example",
        "description": description,
        "transcript": "A complete transcript.",
    }


def client_returning(text):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)]
    )
    return client


def test_write_article_uses_configured_model_and_returns_trimmed_text():
    client = client_returning("  # Generated article  ")
    result = write_articles.write_article(
        video(), article_client=client, config=CONFIG
    )
    assert result == "# Generated article"
    request = client.messages.create.call_args.kwargs
    assert request["model"] == "qwen3.5:4b"
    assert request["max_tokens"] == 8000
    assert "Useful description" in request["messages"][0]["content"]


def test_write_article_allows_missing_description():
    item = video()
    item.pop("description")
    client = client_returning("Article")
    assert write_articles.write_article(
        item, article_client=client, config=CONFIG
    ) == "Article"


def test_write_article_rejects_empty_response(capsys):
    client = client_returning("   ")
    assert write_articles.write_article(
        video(), article_client=client, config=CONFIG
    ) is None
    assert "空内容" in capsys.readouterr().out


def test_write_article_reports_generation_error(capsys):
    client = Mock()
    client.messages.create.side_effect = RuntimeError("generation stopped")
    assert write_articles.write_article(
        video(), article_client=client, config=CONFIG
    ) is None
    output = capsys.readouterr().out
    assert "A useful talk" in output
    assert "generation stopped" in output
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
python -m pytest tests/test_write_articles.py -v
```

Expected: tests fail because the current functions do not accept injected clients/configuration and still use the Claude model constant.

- [ ] **Step 3: Implement the Ollama-backed article path**

Replace the imports, initialization, and `write_article` function in `write_articles.py` with this exact implementation:

```python
from ollama_client import (
    OllamaSetupError,
    create_ollama_client,
    ensure_ollama_ready,
    load_ollama_config,
)


DEFAULT_CONFIG = load_ollama_config()
DEFAULT_CLIENT = create_ollama_client(DEFAULT_CONFIG)


def write_article(video, *, article_client=None, config=None):
    config = config or DEFAULT_CONFIG
    article_client = article_client or DEFAULT_CLIENT
    description = video.get("description", "")
    prompt = f"""You are a skilled magazine writer. Transform this YouTube video transcript into a well-written, engaging article.

VIDEO TITLE: {video['title']}
CHANNEL: {video['channel']}
VIDEO URL: {video['url']}

VIDEO DESCRIPTION:
{description}

TRANSCRIPT:
{video['transcript']}

---

Remix this YouTube transcript into a magazine article. Guidelines:
- Use the video title and description to correct any transcription errors, especially names of people, companies, or technical terms. The description often contains the correct spellings.
- Start with an engaging headline (different from the video title)
- The audience is a curious individual who is generally smart but not a specialist or expert in the area mentioned in the video
- Highly engaging and readable. Wherever jargon or obscure references appear, explain them. Extremely well-written; think New Yorker or the Atlantic
- Capture the key insights, especially contrarian viewpoints, memorable anecdotes, and surprising insights. Preserve key quotes (clean up filler words or transcription errors).
- There's no fixed length requirement; it depends on the length of the original article as well as the insight density. Make your own judgment. This should be a satisfying long-read.
- Do NOT include phrases like "In this video" - write it as a standalone article. Assume the reader has not watched the video and has zero context about it. This article is meant to be as a replacement, not complement, for watching the video.

Format the article in clean markdown."""
    try:
        message = article_client.messages.create(
            model=config.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if not text:
            print(f"  ⚠ Ollama 为《{video['title']}》返回了空内容")
            return None
        return text
    except Exception as exc:
        print(f"  ⚠ 生成《{video['title']}》失败：{exc}")
        return None
```

- [ ] **Step 4: Run the article tests**

Run:

```bash
python -m pytest tests/test_write_articles.py -v
```

Expected: four tests pass.

- [ ] **Step 5: Write failing batch-readiness tests**

Append to `tests/test_write_articles.py`:

```python
def test_batch_checks_readiness_once_and_generates_articles():
    client = client_returning("Article")
    readiness_check = Mock()
    result = write_articles.write_articles_for_videos(
        [video(), video("Second description")],
        article_client=client,
        config=CONFIG,
        readiness_check=readiness_check,
    )
    readiness_check.assert_called_once_with(CONFIG)
    assert len(result) == 2


def test_batch_stops_with_actionable_setup_error(capsys):
    readiness_check = Mock(
        side_effect=OllamaSetupError(
            "未安装模型 qwen3.5:4b，请运行：ollama pull qwen3.5:4b"
        )
    )
    result = write_articles.write_articles_for_videos(
        [video()],
        article_client=client_returning("unused"),
        config=CONFIG,
        readiness_check=readiness_check,
    )
    assert result == []
    assert "ollama pull qwen3.5:4b" in capsys.readouterr().out
```

- [ ] **Step 6: Run the batch tests and confirm they fail**

Run:

```bash
python -m pytest tests/test_write_articles.py -v
```

Expected: the new tests fail because readiness injection is not implemented.

- [ ] **Step 7: Implement one readiness check per batch**

Replace the batch function with:

```python
def write_articles_for_videos(
    videos,
    *,
    article_client=None,
    config=None,
    readiness_check=ensure_ollama_ready,
):
    config = config or DEFAULT_CONFIG
    article_client = article_client or DEFAULT_CLIENT
    print(f"\n正在使用本地 Ollama 模型 {config.model} 生成文章...\n")
    try:
        readiness_check(config)
    except OllamaSetupError as exc:
        print(f"  ⚠ {exc}")
        return []

    print("=" * 60)
    articles = []

    for video in videos:
        print(f"Writing article: {video['title'][:50]}...")
        article = write_article(
            video,
            article_client=article_client,
            config=config,
        )
        if article:
            articles.append({
                "title": video["title"],
                "channel": video["channel"],
                "url": video["url"],
                "article": article,
            })
            print("  ✓ Article generated!\n")
        else:
            print("  ✗ Failed to generate article\n")

    print("=" * 60)
    print(f"Generated {len(articles)} articles")
    return articles
```

- [ ] **Step 8: Replace main-program provider wording**

Change `main.py:50-52` to:

```python
    # Step 3: Generate articles using local AI
    print("\n✍️ STEP 3: Writing articles with local Ollama...\n")
    articles = write_articles_for_videos(videos_with_transcripts)
```

- [ ] **Step 9: Run all focused tests and compile the project**

Run:

```bash
python -m pytest tests/test_ollama_client.py tests/test_write_articles.py -v
python -m compileall -q .
```

Expected: all tests pass and compilation exits with status 0.

- [ ] **Step 10: Commit article integration**

```bash
git add write_articles.py main.py tests/test_write_articles.py
git commit -m "feat: generate articles with local Ollama"
```

---

### Task 3: Align configuration, documentation, UI copy, and licensing

**Files:**
- Modify: `.env.example:1-15`
- Modify: `requirements.txt:1-7`
- Modify: `README.md:1-126`
- Modify: `SKILL.md:1-171`
- Modify: `dashboard.py:724,890`
- Create: `LICENSE`
- Create: `tests/test_env_example.py`

**Interfaces:**
- Consumes: configuration keys and defaults from `ollama_client.py`.
- Produces: a Chinese-first installation path using `YOUTUBE_API_KEY`, `SUPADATA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and optional Gmail values.

- [ ] **Step 1: Write the failing example-configuration behavior test**

Create `tests/test_env_example.py`:

```python
from pathlib import Path

from dotenv import dotenv_values

from ollama_client import load_ollama_config


def test_example_environment_drives_the_supported_local_defaults():
    example = dotenv_values(
        Path(__file__).resolve().parents[1] / ".env.example"
    )
    config = load_ollama_config(example)

    assert config.base_url == "http://localhost:11434"
    assert config.model == "qwen3.5:4b"
    assert example["YOUTUBE_API_KEY"]
    assert example["SUPADATA_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in example
```

- [ ] **Step 2: Run the example-configuration test and confirm it fails**

Run:

```bash
python -m pytest tests/test_env_example.py -v
```

Expected: the test fails because `.env.example` lacks `SUPADATA_API_KEY` and still carries the unsupported Anthropic key.

- [ ] **Step 3: Replace `.env.example` with the active configuration**

Use this exact structure, keeping credentials as examples only:

```dotenv
# YouTube 视频列表
YOUTUBE_API_KEY=your_youtube_api_key_here

# Supadata 字幕服务
SUPADATA_API_KEY=your_supadata_api_key_here

# 本地 Ollama，不需要付费 API Key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b

# Gmail 邮件发送，可选
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password_here
```

- [ ] **Step 4: Synchronize runtime and development dependencies**

Remove the unused `youtube-transcript-api` line from `requirements.txt`. Keep:

```text
google-api-python-client
python-dotenv
anthropic
markdown
ebooklib
requests
```

- [ ] **Step 5: Rewrite the README as a Chinese-first quick start**

Replace `README.md` with this complete content:

````markdown
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

- Python 3.8 或更高版本
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

完整的 `main.py` 流程会在生成 EPUB 后尝试发送邮件。需要邮件发送时，在 Google 账号中创建应用专用密码，然后填写：

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

本地 Ollama 只能在自己的电脑上访问，因此电子书生成应通过 macOS `launchd` 在本机运行。先根据实际 Python 和项目路径修改 `com.youtube.newsletter.plist`，然后执行：

```bash
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
````

- [ ] **Step 6: Update the skill documentation and visible provider copy**

Apply these exact documentation replacements in `SKILL.md`:

```markdown
3. Transforms transcripts into polished articles using a local Ollama model

## Requirements

- Python 3.8+
- Ollama with `qwen3.5:4b` or another configured local model
- YouTube Data API key
- Supadata API key for transcript retrieval
```

Replace the obsolete “Transcript API Syntax” and “Rate Limiting on Transcripts” sections with:

```markdown
### 3. Transcript Retrieval

**Problem**: Direct YouTube transcript libraries can be blocked or change their API.

**Solution**: Configure `SUPADATA_API_KEY` in `.env`. The project sends the video URL to Supadata and reads the returned text transcript.

### 4. Supadata Errors

**Problem**: Transcript requests may fail because the key is missing, a video has no transcript, or the service rate limit is reached.

**Solution**: Check the status message printed by `get_transcripts.py`. HTTP 401 means the key is invalid, 404 means no transcript is available, and 429 means the request should be retried later.
```

Replace the transcript-accuracy sentence with:

```markdown
**Solution**: Include the video title and description in the local model context—these usually contain the correct spellings.
```

Replace the workflow diagram's provider row with:

```text
│ (YouTube API)│    │  (Supadata)  │    │(Ollama Local) │    │ (ebooklib) │
```

Keep the existing Gmail section and change its introductory sentence to `Add Gmail credentials to .env only when you want email delivery:`.

In `dashboard.py`, replace line 724 with `Customize how your local AI writes articles.` and line 890 with `The Digest • Powered by local Ollama`.

- [ ] **Step 7: Add the MIT license file**

Create the standard MIT license text beginning with:

```text
MIT License

Copyright (c) 2026 zarazhangrui
Copyright (c) 2026 rachelhomeland

Permission is hereby granted, free of charge, to any person obtaining a copy
```

Include the complete standard MIT grant, copyright notice condition, and warranty disclaimer.

- [ ] **Step 8: Run the configuration behavior test and manual documentation scans**

Run:

```bash
python -m pytest tests/test_env_example.py -v
rg -n "ANTHROPIC_API_KEY|claude-sonnet|Claude AI|Powered by Claude" . \
  -g '!docs/superpowers/**' -g '!tests/**' -g '!.git/**'
rg -n "rachelhomeland/youtube-to-ebook|zarazhangrui/youtube-to-ebook|Copyright \(c\) 2026" README.md LICENSE
```

Expected: the configuration behavior test passes; the provider scan has no matches; the attribution scan shows both repository names in README and both copyright lines in LICENSE. The lower-level `anthropic` package name may remain in `requirements.txt` and `ollama_client.py` because it is used only as Ollama's compatible transport.

- [ ] **Step 9: Run the complete local suite**

Run:

```bash
python -m pytest -v
python -m compileall -q .
git diff --check
```

Expected: all tests pass, compilation succeeds, and the diff check produces no output.

- [ ] **Step 10: Commit documentation and branding**

```bash
git add .env.example requirements.txt README.md SKILL.md dashboard.py LICENSE tests/test_env_example.py
git commit -m "docs: rebrand fork for local Ollama"
```

---

### Task 4: Replace cloud generation with credential-free validation

**Files:**
- Delete: `.github/workflows/newsletter.yml`
- Create: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: `requirements-dev.txt` and the test suite from Tasks 1–3.
- Produces: GitHub Actions validation for pushes and pull requests without secrets or external model calls.

- [ ] **Step 1: Replace the newsletter workflow**

Delete `.github/workflows/newsletter.yml` and create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements-dev.txt

      - name: Run tests
        run: python -m pytest -v

      - name: Compile Python files
        run: python -m compileall -q .
```

- [ ] **Step 2: Verify the workflow contains no generation secrets**

Run:

```bash
rg -n "secrets\.|YOUTUBE_API_KEY|SUPADATA_API_KEY|GMAIL_APP_PASSWORD|ANTHROPIC_API_KEY" .github/workflows
```

Expected: no matches.

- [ ] **Step 3: Run final pre-publication verification**

Run:

```bash
python -m pytest -v
python -m compileall -q .
git diff --check
git status --short
```

Expected: all tests pass; compilation and diff checks succeed; status shows only the intended workflow replacement before commit.

- [ ] **Step 4: Run the optional live Ollama smoke test when available**

Run:

```bash
if command -v ollama >/dev/null 2>&1 && ollama list | awk 'NR > 1 {print $1}' | grep -qx 'qwen3.5:4b'; then
  python write_articles.py
else
  echo "Skipped live Ollama smoke test: qwen3.5:4b is not installed"
fi
```

Expected when the model is installed: the standalone script prints a non-empty generated article. Otherwise, it prints the explicit skip message; mocked automated coverage remains mandatory.

- [ ] **Step 5: Commit CI validation**

```bash
git add .github/workflows/tests.yml
git rm .github/workflows/newsletter.yml
git commit -m "ci: validate the local Ollama fork"
```

---

### Task 5: Create and publish the GitHub fork

**Files:**
- No source-file changes.
- Remote state: create `rachelhomeland/youtube-to-ebook`, publish `feat/ollama-local`, then merge to `main` after checks pass.

**Interfaces:**
- Consumes: verified local commits on `feat/ollama-local` and authenticated GitHub account `rachelhomeland`.
- Produces: public fork `https://github.com/rachelhomeland/youtube-to-ebook` with `origin` pointing to the fork and `upstream` pointing to `zarazhangrui/youtube-to-ebook`.

- [ ] **Step 1: Confirm the local branch and clean state**

Run:

```bash
git branch --show-current
git status --short
git log --oneline --decorate -6
```

Expected: branch is `feat/ollama-local`, the worktree is clean, and the design plus implementation commits are visible.

- [ ] **Step 2: Create the fork under the authenticated account**

Using the authenticated GitHub browser session, open `https://github.com/zarazhangrui/youtube-to-ebook/fork`, select owner `rachelhomeland`, keep repository name `youtube-to-ebook`, keep “Copy the main branch only” enabled, and create the fork.

Verify the resulting URL is exactly:

```text
https://github.com/rachelhomeland/youtube-to-ebook
```

- [ ] **Step 3: Correct local remote ownership**

Run:

```bash
git remote rename origin upstream
git remote add origin https://github.com/rachelhomeland/youtube-to-ebook.git
git remote -v
```

Expected: `origin` is the `rachelhomeland` fork and `upstream` is the `zarazhangrui` repository for both fetch and push.

- [ ] **Step 4: Publish the feature branch**

Run:

```bash
git push -u origin feat/ollama-local
```

Expected: GitHub reports a new branch at `rachelhomeland/youtube-to-ebook`.

- [ ] **Step 5: Open and merge the fork-local pull request**

Create a pull request in `rachelhomeland/youtube-to-ebook` from `feat/ollama-local` into `main` with:

```text
Title: Replace Anthropic API with local Ollama

Body:
## Summary
- generate articles with configurable local Ollama
- add actionable local setup checks and tests
- update Chinese-first documentation and attribution
- replace cloud generation with credential-free CI

## Verification
- python -m pytest -v
- python -m compileall -q .
- git diff --check
```

Wait for the `Tests` workflow to pass, then merge the pull request without deleting the branch until the local checkout has been synchronized.

- [ ] **Step 6: Synchronize and verify the published default branch**

Run:

```bash
git switch main
git pull --ff-only origin main
git branch -d feat/ollama-local
git status --short --branch
git log -1 --oneline
```

Expected: local `main` tracks the fork's merged commit, the feature branch is deleted locally, and the worktree is clean.

- [ ] **Step 7: Verify the public repository contents**

Confirm on GitHub that:

- the repository is identified as a fork of `zarazhangrui/youtube-to-ebook`
- README installation uses `rachelhomeland/youtube-to-ebook`
- `.env.example` contains Ollama and Supadata settings but no Anthropic key
- `LICENSE` credits upstream and fork maintainers
- the latest `Tests` workflow is green
