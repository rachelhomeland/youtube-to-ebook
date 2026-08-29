from pathlib import Path
import subprocess
import sys

import pytest

import main


VIDEO_URL_1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
VIDEO_URL_2 = "https://youtu.be/9bZkp7q19f0"


def video():
    return {
        "title": "Selected video",
        "video_id": "dQw4w9WgXcQ",
        "description": "Description",
        "channel": "Selected channel",
        "url": VIDEO_URL_1,
    }


def article():
    return {
        "title": "Selected video",
        "video_id": "dQw4w9WgXcQ",
        "channel": "Selected channel",
        "url": VIDEO_URL_1,
        "article": "# Generated article",
    }


def test_parse_args_accepts_repeated_video_urls_and_no_email():
    args = main.parse_args(
        ["--url", VIDEO_URL_1, "--url", VIDEO_URL_2, "--no-email"]
    )

    assert args.video_urls == [VIDEO_URL_1, VIDEO_URL_2]
    assert args.no_email is True


def test_manual_urls_bypass_channel_scan_and_always_save_locally(monkeypatch):
    selected_video = video()
    transcript_video = {**selected_video, "transcript": "Transcript"}
    generated_article = article()
    events = []

    monkeypatch.setattr(main, "get_processed_count", lambda: 0)
    monkeypatch.setattr(
        main,
        "fetch_videos_by_urls",
        lambda urls: events.append(("fetch_urls", urls)) or [selected_video],
    )
    monkeypatch.setattr(
        main,
        "fetch_videos",
        lambda: (_ for _ in ()).throw(AssertionError("channel scan must be skipped")),
    )
    monkeypatch.setattr(
        main,
        "filter_new_videos",
        lambda videos: (_ for _ in ()).throw(
            AssertionError("manual videos must be reprocessable")
        ),
    )
    monkeypatch.setattr(
        main,
        "get_transcripts_for_videos",
        lambda videos: [transcript_video],
    )
    monkeypatch.setattr(
        main,
        "write_articles_for_videos",
        lambda videos: [generated_article],
    )

    def deliver(articles, *, email_enabled):
        events.append(("deliver", email_enabled, articles))
        return True

    monkeypatch.setattr(main, "send_newsletter", deliver)
    monkeypatch.setattr(
        main,
        "mark_videos_processed",
        lambda videos: events.append(("marked", videos)),
    )

    result = main.run(video_urls=[VIDEO_URL_1])

    assert result == [generated_article]
    assert events == [
        ("fetch_urls", [VIDEO_URL_1]),
        ("deliver", False, [generated_article]),
        ("marked", [transcript_video]),
    ]


def test_no_email_flag_disables_email_in_channel_mode(monkeypatch):
    selected_video = video()
    transcript_video = {**selected_video, "transcript": "Transcript"}
    generated_article = article()
    delivery = []

    monkeypatch.setattr(main, "get_processed_count", lambda: 0)
    monkeypatch.setattr(main, "fetch_videos", lambda: [selected_video])
    monkeypatch.setattr(main, "filter_new_videos", lambda videos: videos)
    monkeypatch.setattr(
        main, "get_transcripts_for_videos", lambda videos: [transcript_video]
    )
    monkeypatch.setattr(
        main, "write_articles_for_videos", lambda videos: [generated_article]
    )
    monkeypatch.setattr(
        main,
        "send_newsletter",
        lambda articles, *, email_enabled: delivery.append(email_enabled) or True,
    )
    monkeypatch.setattr(main, "mark_videos_processed", lambda videos: None)

    assert main.run(no_email=True) == [generated_article]
    assert delivery == [False]


def test_default_channel_mode_keeps_email_enabled(monkeypatch):
    selected_video = video()
    transcript_video = {**selected_video, "transcript": "Transcript"}
    delivery = []

    monkeypatch.setattr(main, "get_processed_count", lambda: 0)
    monkeypatch.setattr(main, "fetch_videos", lambda: [selected_video])
    monkeypatch.setattr(main, "filter_new_videos", lambda videos: videos)
    monkeypatch.setattr(
        main, "get_transcripts_for_videos", lambda videos: [transcript_video]
    )
    monkeypatch.setattr(main, "write_articles_for_videos", lambda videos: [article()])
    monkeypatch.setattr(
        main,
        "send_newsletter",
        lambda articles, *, email_enabled: delivery.append(email_enabled) or True,
    )
    monkeypatch.setattr(main, "mark_videos_processed", lambda videos: None)

    main.run()

    assert delivery == [True]


def test_only_successfully_generated_videos_are_marked_processed(monkeypatch):
    first = {**video(), "transcript": "First transcript"}
    second = {
        **video(),
        "title": "Second video",
        "video_id": "9bZkp7q19f0",
        "url": VIDEO_URL_2,
        "transcript": "Second transcript",
    }
    marked = []

    monkeypatch.setattr(main, "get_processed_count", lambda: 0)
    monkeypatch.setattr(main, "fetch_videos_by_urls", lambda urls: [first, second])
    monkeypatch.setattr(
        main, "get_transcripts_for_videos", lambda videos: [first, second]
    )
    monkeypatch.setattr(main, "write_articles_for_videos", lambda videos: [article()])
    monkeypatch.setattr(
        main,
        "send_newsletter",
        lambda articles, *, email_enabled: True,
    )
    monkeypatch.setattr(
        main, "mark_videos_processed", lambda videos: marked.extend(videos)
    )

    main.run(video_urls=[VIDEO_URL_1, VIDEO_URL_2])

    assert marked == [first]


def test_invalid_manual_url_stops_with_actionable_message(monkeypatch, capsys):
    monkeypatch.setattr(main, "get_processed_count", lambda: 0)
    monkeypatch.setattr(
        main,
        "fetch_videos_by_urls",
        lambda urls: (_ for _ in ()).throw(ValueError("无法识别 YouTube 视频链接")),
    )

    with pytest.raises(ValueError, match="无法识别 YouTube 视频链接"):
        main.run(video_urls=["bad-url"])


def test_cli_invalid_manual_url_returns_nonzero_exit_status():
    result = subprocess.run(
        [sys.executable, str(Path(main.__file__)), "--url", "bad-url"],
        cwd=Path(main.__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "无法识别 YouTube 视频链接" in result.stderr
