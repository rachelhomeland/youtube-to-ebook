# YouTube to Ebook Ollama Fork Design

> Historical document: this Ollama design was superseded by the DeepSeek API migration on 2026-08-29. See the current `README.md`, `.env.example`, and `deepseek_client.py` for the supported setup.

## Goal

Create a maintained fork of `zarazhangrui/youtube-to-ebook` under the GitHub account `rachelhomeland`. Keep the existing `youtube-to-ebook` name and end-to-end workflow, while replacing the paid Anthropic dependency with a local Ollama model. The first release targets personal use on a Mac and should be understandable to a Chinese-speaking user following the README.

## Repository and Attribution

- Fork `zarazhangrui/youtube-to-ebook` into `rachelhomeland/youtube-to-ebook`.
- Use the user's fork as the `origin` remote and keep the original repository as `upstream` for future updates.
- Preserve the MIT license and original copyright notice.
- Add a short attribution section in the README that links to the upstream project and describes the local-Ollama changes.
- Develop the change on `feat/ollama-local`, then merge it into the fork's default branch after verification.

## Scope

### Included

- Replace the remote Claude model call with an Ollama-backed call that remains compatible with the current article-writing interface.
- Default to `qwen3.5:4b`, with the model and Ollama server URL configurable through `.env`.
- Remove the requirement for a real Anthropic API key.
- Validate Ollama configuration before article generation and provide actionable messages when Ollama is not running or the selected model is not installed.
- Replace user-facing Claude and Anthropic wording in the command-line flow, dashboard, skill documentation, and README.
- Correct configuration documentation for the current Supadata-based transcript implementation.
- Provide Chinese-first setup instructions, while keeping enough English naming to make commands and file names easy to recognize.
- Add automated tests for configuration, successful generation, and common failure cases without requiring a live Ollama server.

### Excluded from the first release

- Supporting multiple AI providers.
- Replacing YouTube Data API, Supadata, or Gmail delivery.
- Redesigning the Streamlit dashboard.
- Hosting the application as a public web service.
- Running ebook generation in GitHub Actions. The default Ollama backend runs on the user's Mac and is not reachable from a hosted GitHub runner.

## Architecture

The video, transcript, ebook, email, dashboard, and tracking modules remain intact. Only the article-generation boundary changes.

`write_articles.py` will expose the existing `write_article(video)` and `write_articles_for_videos(videos)` functions so callers do not need to change. It will construct an Anthropic-compatible client pointed at Ollama's local endpoint. Ollama officially supports the Anthropic Messages API, so the project can retain the installed `anthropic` Python package while replacing the base URL, placeholder key, and model name.

Configuration will use:

- `OLLAMA_BASE_URL`, default `http://localhost:11434`
- `OLLAMA_MODEL`, default `qwen3.5:4b`
- a local placeholder API key supplied internally because the compatible client requires a value but Ollama does not validate it

The existing prompt and response parsing remain unchanged unless verification reveals a compatibility issue.

## Data Flow

1. `get_videos.py` retrieves recent videos through the YouTube Data API.
2. `get_transcripts.py` retrieves transcript text through Supadata.
3. `write_articles.py` sends the title, channel, URL, description, and transcript to local Ollama.
4. The generated Markdown is passed to `send_email.py` for EPUB creation and optional Gmail delivery.
5. Successfully delivered videos are recorded by `video_tracker.py`.

The `.env.example` file will document every active configuration value in this flow, including the currently missing `SUPADATA_API_KEY` entry.

## Error Handling

Before the first generation request, the article module will distinguish these cases:

- Ollama server unavailable: explain that Ollama must be installed and opened, and show the expected local address.
- Model unavailable: name the configured model and show the corresponding `ollama pull` command.
- Request timeout or generation error: identify the affected video and return `None`, preserving the current per-video failure behavior.
- Empty model response: treat it as a failed article instead of creating an empty ebook entry.

Configuration messages must never print secrets. YouTube, Supadata, and Gmail behavior remains unchanged apart from clearer documentation.

## Documentation and User Interface

- Rewrite the README quick start around `rachelhomeland/youtube-to-ebook` and local Ollama.
- Explain the three remaining integrations accurately: YouTube API, Supadata, and optional Gmail.
- Include model choices for lower- and higher-memory Macs, with `qwen3.5:4b` as the supported default.
- Replace visible “Claude AI” and “Powered by Claude AI” text with provider-neutral or Ollama-specific wording.
- Update `SKILL.md` so its requirements and workflow diagram match the implementation.
- Keep the current product label “The Digest” in the dashboard; this release changes the AI provider, not the product identity.

## GitHub Actions

The existing newsletter workflow will be replaced with a lightweight validation workflow that installs dependencies and runs the automated test suite. It will not fetch videos, call external services, generate ebooks, or require repository secrets. Local scheduling through macOS `launchd` remains the supported automation path.

## Verification

Automated verification will cover:

- default and environment-overridden Ollama configuration
- client construction with the local base URL and placeholder key
- successful article text extraction from a mocked compatible response
- server-unavailable, missing-model, empty-response, and generic request failures
- existing Python files compiling successfully

Manual verification will cover:

- README commands matching actual file names and configuration keys
- no remaining user-facing requirement for an Anthropic API key
- dashboard and command-line wording referring to Ollama or local AI
- an optional live smoke test when Ollama and `qwen3.5:4b` are installed on the machine

Tests must not require YouTube, Supadata, Gmail, or Ollama credentials.

## Success Criteria

- The fork exists at `rachelhomeland/youtube-to-ebook` and links back to the upstream repository.
- A new user can follow the README to install Ollama, configure the required non-LLM services, and start the project without an Anthropic account.
- Article generation uses the configured local Ollama model.
- Common Ollama setup failures produce clear recovery instructions.
- Automated tests and Python compilation checks pass.
- No credentials, personal email addresses, or generated newsletters are committed.
