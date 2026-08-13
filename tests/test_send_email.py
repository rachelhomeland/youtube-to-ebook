from pathlib import Path

import send_email


def article():
    return {
        "title": "A useful talk",
        "channel": "Example Channel",
        "url": "https://youtube.com/watch?v=example",
        "article": "# Generated article",
    }


def test_missing_gmail_credentials_archives_epub_without_sending(
    monkeypatch, tmp_path, capsys
):
    epub_path = tmp_path / "digest.epub"
    epub_path.write_bytes(b"epub")
    archive_marker = tmp_path / "archived.txt"

    monkeypatch.setattr(send_email, "GMAIL_ADDRESS", None)
    monkeypatch.setattr(send_email, "GMAIL_APP_PASSWORD", None)
    monkeypatch.setattr(send_email, "create_epub", lambda articles: str(epub_path))
    monkeypatch.setattr(
        send_email,
        "create_newsletter_html",
        lambda articles: "<html>digest</html>",
    )

    def archive(html_content, generated_epub, articles):
        assert html_content == "<html>digest</html>"
        assert generated_epub == str(epub_path)
        archive_marker.write_text(articles[0]["title"])

    monkeypatch.setattr(send_email, "save_newsletter_archive", archive)

    class UnexpectedSMTP:
        def __init__(self, *args, **kwargs):
            raise AssertionError("SMTP must not be used without Gmail credentials")

    monkeypatch.setattr(send_email.smtplib, "SMTP_SSL", UnexpectedSMTP)

    assert send_email.send_newsletter([article()]) is True
    assert archive_marker.read_text() == "A useful talk"
    assert not epub_path.exists()
    assert "未配置 Gmail" in capsys.readouterr().out
