"""Transform video transcripts into magazine articles using local Ollama."""

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


# Test it standalone
if __name__ == "__main__":
    # Test with a mock video
    test_video = {
        "title": "Test Video",
        "channel": "Test Channel",
        "url": "https://youtube.com/watch?v=test",
        "transcript": "Hello everyone, today we're going to talk about something really exciting. I've been working on this project for months and I can't wait to share it with you. The main idea is simple but powerful..."
    }

    print("Testing article generation...")
    article = write_article(test_video)
    if article:
        print("\nGenerated article:\n")
        print(article)
