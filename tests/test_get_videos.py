import pytest

from get_videos import extract_video_id, get_videos_by_urls


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=42", "dQw4w9WgXcQ"),
        ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_accepts_common_youtube_links(value, expected):
    assert extract_video_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch",
        "not a valid video",
    ],
)
def test_extract_video_id_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="YouTube"):
        extract_video_id(value)


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeVideosResource:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(kwargs)
        return FakeRequest(self.response)


class FakeYouTube:
    def __init__(self, response):
        self.resource = FakeVideosResource(response)

    def videos(self):
        return self.resource


def test_get_videos_by_urls_preserves_order_and_removes_duplicates(capsys):
    youtube = FakeYouTube(
        {
            "items": [
                {
                    "id": "9bZkp7q19f0",
                    "snippet": {
                        "title": "Second video",
                        "description": "Second description",
                        "channelTitle": "Second channel",
                    },
                },
                {
                    "id": "dQw4w9WgXcQ",
                    "snippet": {
                        "title": "First video",
                        "description": "First description",
                        "channelTitle": "First channel",
                    },
                },
            ]
        }
    )

    videos = get_videos_by_urls(
        [
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=9bZkp7q19f0",
            "dQw4w9WgXcQ",
        ],
        youtube=youtube,
    )

    assert [video["video_id"] for video in videos] == [
        "dQw4w9WgXcQ",
        "9bZkp7q19f0",
    ]
    assert videos[0] == {
        "title": "First video",
        "video_id": "dQw4w9WgXcQ",
        "description": "First description",
        "channel": "First channel",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    assert youtube.resource.calls == [
        {"part": "snippet", "id": "dQw4w9WgXcQ,9bZkp7q19f0"}
    ]
    assert "2" in capsys.readouterr().out


def test_get_videos_by_urls_reports_videos_not_returned_by_youtube(capsys):
    youtube = FakeYouTube({"items": []})

    assert get_videos_by_urls(["dQw4w9WgXcQ"], youtube=youtube) == []
    assert "dQw4w9WgXcQ" in capsys.readouterr().out


def test_get_videos_by_urls_fetches_metadata_in_batches_of_fifty():
    video_ids = [f"vid{i:08d}" for i in range(51)]
    youtube = FakeYouTube(
        {
            "items": [
                {
                    "id": video_id,
                    "snippet": {
                        "title": video_id,
                        "description": "",
                        "channelTitle": "Channel",
                    },
                }
                for video_id in video_ids
            ]
        }
    )

    videos = get_videos_by_urls(video_ids, youtube=youtube)

    assert [video["video_id"] for video in videos] == video_ids
    assert youtube.resource.calls == [
        {"part": "snippet", "id": ",".join(video_ids[:50])},
        {"part": "snippet", "id": video_ids[50]},
    ]
