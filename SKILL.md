---
name: youtube-to-ebook
description: Transform YouTube videos into beautifully formatted ebook articles with transcripts
---

# YouTube to Ebook

Transform YouTube videos from your favorite channels into well-written magazine-style articles, delivered as an EPUB ebook.

## What This Skill Does

1. Fetches latest videos from YouTube channels (filtering out Shorts)
2. Extracts transcripts from those videos
3. Transforms transcripts into polished articles using a local Ollama model
4. Packages articles into an EPUB ebook for reading on any device

## Quick Start

Ask: "Set up YouTube to ebook for me"

I'll guide you through:
1. Creating a project folder
2. Setting up YouTube API access
3. Configuring your favorite channels
4. Generating your first ebook

## Requirements

- Python 3.8+
- Ollama with `qwen3.5:4b` or another configured local model
- YouTube Data API key
- Supadata API key for transcript retrieval

## Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Generate ebook from latest videos |
| `python -m streamlit run dashboard.py` | Launch web dashboard |

To configure channels, edit the `CHANNELS` list in `get_videos.py` before running the full pipeline.

## Key Files

```
project-root/
├── get_videos.py      # Fetch latest videos and configure CHANNELS
├── get_transcripts.py # Extract transcripts
├── write_articles.py  # Transform to articles
├── send_email.py      # Create EPUB & send
├── main.py            # Run full pipeline
├── dashboard.py       # Streamlit dashboard
├── run_newsletter.sh  # launchd runner
├── com.youtube.newsletter.plist # launchd configuration
└── .env               # API keys
```

## Known Pitfalls & Solutions

### 1. YouTube Shorts Detection
**Problem**: Filtering by duration doesn't work—some Shorts are longer than 60 seconds.

**Solution**: Check if the `/shorts/` URL resolves:
```python
def is_youtube_short(video_id):
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
    response = requests.head(shorts_url, allow_redirects=True, timeout=5)
    return "/shorts/" in response.url
```

### 2. Videos Not in Chronological Order
**Problem**: YouTube Search API doesn't return truly chronological results.

**Solution**: Use the channel's uploads playlist via `playlistItems` API:
```python
# Get uploads playlist ID from channel
channel_info = youtube.channels().list(
    part="contentDetails",
    forHandle=handle
).execute()
uploads_playlist_id = channel_info["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# Fetch from uploads playlist (always chronological)
youtube.playlistItems().list(
    part="snippet",
    playlistId=uploads_playlist_id,
    maxResults=15
).execute()
```

### 3. Transcript Retrieval

**Problem**: Direct YouTube transcript libraries can be blocked or change their API.

**Solution**: Configure `SUPADATA_API_KEY` in `.env`. The project sends the video URL to Supadata and reads the returned text transcript.

### 4. Supadata Errors

**Problem**: Transcript requests may fail because the key is missing, a video has no transcript, or the service rate limit is reached.

**Solution**: Check the status message printed by `get_transcripts.py`. HTTP 401 means the key is invalid, 404 means no transcript is available, and 429 means the request should be retried later.

### 5. Transcript Accuracy (Names, Terms)
**Problem**: Auto-transcripts misspell names and technical terms.

**Solution**: Include the video title and description in the local model context—these usually contain the correct spellings.

### 6. Cloud Automation Blocked
**Problem**: GitHub Actions and cloud servers are blocked by YouTube for transcript fetching.

**Solution**: Run automation locally on your Mac using `launchd`:
```xml
<!-- ~/Library/LaunchAgents/com.youtube.ebook.plist -->
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youtube.ebook</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/main.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>3</integer>
        <key>Hour</key>
        <integer>7</integer>
    </dict>
</dict>
</plist>
```

## Customization

### Writing Style
Edit the prompt in `write_articles.py` to change article tone:
- Magazine style (default)
- Academic summary
- Casual blog post
- Technical documentation

### Email Delivery (Optional)
Add Gmail credentials to .env only when you want email delivery:
```
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

## Workflow

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌────────────┐
│ Fetch Videos│───▶│Get Transcripts│───▶│Write Articles │───▶│Create EPUB │
│ (YouTube API)│    │  (Supadata)  │    │(Ollama Local) │    │ (ebooklib) │
└─────────────┘    └──────────────┘    └───────────────┘    └────────────┘
```

## Example Output

The generated EPUB contains:
- Table of contents with all articles
- Clean, readable formatting
- Original video links for reference
- Mobile-friendly styling
