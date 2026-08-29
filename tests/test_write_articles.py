from types import SimpleNamespace
from unittest.mock import Mock

from deepseek_client import DeepSeekConfig, DeepSeekSetupError
import write_articles


CONFIG = DeepSeekConfig(
    api_key="sk-test-key",
    base_url="https://api.deepseek.com/anthropic",
    model="deepseek-v4-flash",
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


def client_returning_blocks(blocks):
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(content=blocks)
    return client


def test_write_article_uses_configured_model_and_returns_trimmed_text():
    client = client_returning("  # Generated article  ")
    result = write_articles.write_article(
        video(), article_client=client, config=CONFIG
    )
    assert result == "# Generated article"
    request = client.messages.create.call_args.kwargs
    assert request["model"] == "deepseek-v4-flash"
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


def test_write_article_ignores_thinking_blocks_before_text():
    client = client_returning_blocks([
        SimpleNamespace(type="thinking", thinking="internal reasoning"),
        SimpleNamespace(type="text", text="  # Generated article  "),
    ])

    result = write_articles.write_article(
        video(), article_client=client, config=CONFIG
    )

    assert result == "# Generated article"


def test_write_article_rejects_response_without_text_blocks(capsys):
    client = client_returning_blocks([
        SimpleNamespace(type="thinking", thinking="internal reasoning"),
    ])

    result = write_articles.write_article(
        video(), article_client=client, config=CONFIG
    )

    assert result is None
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


def test_batch_generates_all_articles_without_local_readiness_check():
    client = client_returning("Article")
    result = write_articles.write_articles_for_videos(
        [video(), video("Second description")],
        article_client=client,
        config=CONFIG,
    )
    assert len(result) == 2


def test_batch_stops_with_actionable_missing_key_error(capsys):
    def missing_config():
        raise DeepSeekSetupError("请在 .env 中填写有效的 DEEPSEEK_API_KEY")

    result = write_articles.write_articles_for_videos(
        [video()],
        config_loader=missing_config,
    )
    assert result == []
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().out


def test_batch_builds_client_after_loading_config():
    client = client_returning("Article")
    client_factory = Mock(return_value=client)

    result = write_articles.write_articles_for_videos(
        [video()],
        config_loader=lambda: CONFIG,
        client_factory=client_factory,
    )

    assert len(result) == 1
    client_factory.assert_called_once_with(CONFIG)
