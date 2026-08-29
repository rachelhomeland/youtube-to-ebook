"""
YouTube Newsletter Generator - Main Script
Ties together all the pieces: fetch videos → get transcripts → write articles → send email
Tracks processed videos to avoid sending duplicates.
"""

import argparse
import sys

from get_videos import get_videos_by_urls as fetch_videos_by_urls
from get_videos import main as fetch_videos
from get_transcripts import get_transcripts_for_videos
from write_articles import write_articles_for_videos
from send_email import send_newsletter
from video_tracker import filter_new_videos, mark_videos_processed, get_processed_count


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="把频道最新视频或指定的 YouTube 视频转换成电子书。"
    )
    parser.add_argument(
        "-u",
        "--url",
        action="append",
        dest="video_urls",
        metavar="YOUTUBE_URL",
        help="处理指定视频；可重复使用该参数来处理多个视频。",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="只在 newsletters/ 保存 HTML 和 EPUB，不发送邮件。",
    )
    return parser.parse_args(argv)


def run(video_urls=None, no_email=False):
    """
    Run the full newsletter pipeline.
    """
    print("=" * 60)
    print("  YOUTUBE NEWSLETTER GENERATOR")
    print("=" * 60)
    print(f"  Previously processed: {get_processed_count()} videos")

    manual_mode = bool(video_urls)

    # Step 1: Fetch either explicitly selected videos or channel updates
    if manual_mode:
        print("\n📺 STEP 1: Fetching selected videos...\n")
        videos = fetch_videos_by_urls(video_urls)
    else:
        print("\n📺 STEP 1: Fetching latest videos...\n")
        videos = fetch_videos()

    if not videos:
        if manual_mode:
            print("No selected videos found. Check the supplied YouTube URLs.")
        else:
            print("No videos found. Check your channel list.")
        return

    if manual_mode:
        # Explicitly selected videos may be regenerated even if processed before.
        new_videos = videos
    else:
        # Step 1b: Filter out already-processed videos
        print("\n🔍 Checking for new videos...\n")
        new_videos = filter_new_videos(videos)

    if not manual_mode and not new_videos:
        print("No new videos to process. All videos have been sent before.")
        print("=" * 60)
        return

    print(f"\n  → {len(new_videos)} new video(s) to process\n")

    # Step 2: Get transcripts for those videos
    print("\n📝 STEP 2: Extracting transcripts...\n")
    videos_with_transcripts = get_transcripts_for_videos(new_videos)

    if not videos_with_transcripts:
        print("No transcripts available for any videos.")
        return

    # Step 3: Generate articles using DeepSeek
    print("\n✍️ STEP 3: Writing articles with DeepSeek...\n")
    articles = write_articles_for_videos(videos_with_transcripts)

    if not articles:
        print("No articles generated.")
        return

    # Manual mode is local-only by default; --no-email also applies to channel mode.
    email_enabled = not manual_mode and not no_email
    print("\n📚 STEP 4: Creating newsletter...\n")
    success = send_newsletter(articles, email_enabled=email_enabled)

    # Step 5: Mark only videos whose articles were successfully delivered.
    if success:
        successful_video_ids = {article.get("video_id") for article in articles}
        processed_videos = [
            video
            for video in videos_with_transcripts
            if video["video_id"] in successful_video_ids
        ]
        mark_videos_processed(processed_videos)
        print(f"\n  ✓ Marked {len(processed_videos)} video(s) as processed")

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)

    return articles


def main(argv=None):
    args = parse_args(argv)
    try:
        run(video_urls=args.video_urls, no_email=args.no_email)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
