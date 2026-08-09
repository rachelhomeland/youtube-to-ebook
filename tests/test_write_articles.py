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
