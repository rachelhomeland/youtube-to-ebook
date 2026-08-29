"""Transform video transcripts into magazine articles using DeepSeek."""

from deepseek_client import (
    DeepSeekSetupError,
    create_deepseek_client,
    load_deepseek_config,
)


def write_article(video, *, article_client=None, config=None):
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
        config = config or load_deepseek_config()
        article_client = article_client or create_deepseek_client(config)
        message = article_client.messages.create(
            model=config.model,
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "\n\n".join(
            block.text.strip()
            for block in message.content
            if (
                getattr(block, "type", None) == "text"
                and getattr(block, "text", "").strip()
            )
        ).strip()
        if not text:
            print(f"  ⚠ DeepSeek 为《{video['title']}》返回了空内容")
            return None
        return text
    except DeepSeekSetupError as exc:
        print(f"  ⚠ {exc}")
        return None
    except Exception as exc:
        print(f"  ⚠ 生成《{video['title']}》失败：{exc}")
        return None


def write_articles_for_videos(
    videos,
    *,
    article_client=None,
    config=None,
    config_loader=load_deepseek_config,
    client_factory=create_deepseek_client,
):
    try:
        config = config or config_loader()
        article_client = article_client or client_factory(config)
    except DeepSeekSetupError as exc:
        print(f"  ⚠ {exc}")
        return []

    print(f"\n正在使用 DeepSeek 模型 {config.model} 生成文章...\n")

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
