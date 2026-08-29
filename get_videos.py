"""
Part 1: Fetch Latest Videos from YouTube Channels
This script gets the most recent video from each of your favorite channels.
Filters out YouTube Shorts by checking the /shorts/ URL.
"""

import os
import re
import requests
from urllib.parse import parse_qs, urlparse
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load your secret API key from the .env file
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ========================================
# YOUR FAVORITE CHANNELS GO HERE
# Use the @ handle from the channel's YouTube page (most reliable)
# Example: youtube.com/@MrBeast → use "@MrBeast"
# ========================================
CHANNELS = [
    "@LatentSpacePod",
    "@ycombinator",
    "@a16z",
    "@RedpointAI",
    "@EveryInc",
    "@DataDrivenNYC",
    "@NoPriorsPodcast",
    "@DwarkeshPatel",
]

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(value):
    """Extract a YouTube video ID from a video ID or a common YouTube URL."""
    value = (value or "").strip()
    if VIDEO_ID_PATTERN.fullmatch(value):
        return value

    candidate_url = value
    if candidate_url.startswith((
        "youtube.com/",
        "www.youtube.com/",
        "m.youtube.com/",
        "music.youtube.com/",
        "youtu.be/",
        "youtube-nocookie.com/",
        "www.youtube-nocookie.com/",
    )):
        candidate_url = f"https://{candidate_url}"

    parsed = urlparse(candidate_url)
    host = (parsed.hostname or "").lower()
    video_id = None

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif host in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }:
        path_parts = [part for part in parsed.path.split("/") if part]
        if parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            video_id = path_parts[1]
    elif host in {"youtube-nocookie.com", "www.youtube-nocookie.com"}:
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "embed":
            video_id = path_parts[1]

    if not video_id or not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError(
            f"无法识别 YouTube 视频链接或视频 ID：{value or '(空值)'}"
        )
    return video_id


def get_videos_by_urls(video_urls, *, youtube=None):
    """Fetch metadata for explicitly selected YouTube videos."""
    video_ids = list(dict.fromkeys(extract_video_id(url) for url in video_urls))
    if not video_ids:
        return []

    if youtube is None:
        if not YOUTUBE_API_KEY:
            raise ValueError("未配置 YOUTUBE_API_KEY，无法查询 YouTube 视频信息。")
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    items_by_id = {}
    for offset in range(0, len(video_ids), 50):
        batch = video_ids[offset:offset + 50]
        response = youtube.videos().list(
            part="snippet",
            id=",".join(batch),
        ).execute()
        items_by_id.update(
            {item["id"]: item for item in response.get("items", [])}
        )

    videos = []
    for video_id in video_ids:
        item = items_by_id.get(video_id)
        if not item:
            print(f"  ✗ YouTube 未返回视频：{video_id}")
            continue
        snippet = item["snippet"]
        videos.append({
            "title": snippet["title"],
            "video_id": video_id,
            "description": snippet.get("description", ""),
            "channel": snippet["channelTitle"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    print(f"已获取 {len(videos)} 个指定视频。")
    return videos


def get_channel_info(youtube, channel_handle):
    """
    Given a channel handle (@username), find its channel ID and uploads playlist ID.
    The uploads playlist contains ALL videos in exact upload order (most reliable).
    """
    # Remove @ if present for the API call
    handle = channel_handle.lstrip("@")

    # Get channel info including the contentDetails (which has the uploads playlist)
    request = youtube.channels().list(
        part="snippet,contentDetails",
        forHandle=handle
    )
    response = request.execute()

    if response.get("items"):
        channel = response["items"][0]
        return {
            "channel_id": channel["id"],
            "channel_name": channel["snippet"]["title"],
            "uploads_playlist_id": channel["contentDetails"]["relatedPlaylists"]["uploads"]
        }

    return None


def is_youtube_short(video_id):
    """
    Check if a video is a YouTube Short by testing the /shorts/ URL.
    If youtube.com/shorts/VIDEO_ID works (doesn't redirect away), it's a Short.
    """
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"

    try:
        # Make a request and check if we stay on the /shorts/ URL
        response = requests.head(shorts_url, allow_redirects=True, timeout=5)
        final_url = response.url

        # If the final URL still contains /shorts/, it's a Short
        return "/shorts/" in final_url
    except:
        # If there's an error, assume it's not a Short
        return False


def get_latest_video(youtube, uploads_playlist_id, channel_name):
    """
    Get the most recent LONG-FORM video from a channel's uploads playlist.
    Uses the uploads playlist (not search) for accurate chronological order.
    Skips YouTube Shorts by checking the /shorts/ URL pattern.
    """
    # Get the 15 most recent videos from the uploads playlist
    # The uploads playlist is always in exact upload order (newest first)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=15
    )
    response = request.execute()

    for item in response.get("items", []):
        video_id = item["snippet"]["resourceId"]["videoId"]

        # Check if this video is a Short
        if is_youtube_short(video_id):
            continue  # Skip Shorts, check the next video

        # It's a long-form video!
        return {
            "title": item["snippet"]["title"],
            "video_id": video_id,
            "description": item["snippet"]["description"],
            "channel": channel_name,
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }

    return None


def main():
    """
    Main function - this runs when you execute the script.
    """
    # Create a connection to YouTube
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    print("Fetching latest LONG-FORM videos (skipping Shorts)...\n")
    print("=" * 60)

    videos = []

    for channel_handle in CHANNELS:
        print(f"Looking up: {channel_handle}")

        # Step 1: Get channel info (including uploads playlist)
        channel_info = get_channel_info(youtube, channel_handle)

        if channel_info:
            print(f"  Channel: {channel_info['channel_name']}")

            # Step 2: Get latest video from uploads playlist
            video = get_latest_video(
                youtube,
                channel_info["uploads_playlist_id"],
                channel_info["channel_name"]
            )

            if video:
                videos.append(video)
                print(f"  ✓ Found: {video['title']}")
                print(f"    URL: {video['url']}\n")
            else:
                print(f"  ✗ No long-form videos found\n")
        else:
            print(f"  ✗ Channel not found\n")

    print("=" * 60)
    print(f"Found {len(videos)} videos total!")

    return videos


# This runs the main function when you execute the script
if __name__ == "__main__":
    main()
