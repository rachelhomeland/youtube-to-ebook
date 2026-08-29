from unittest.mock import Mock

import pytest

import deepseek_client


def test_load_config_requires_api_key():
    with pytest.raises(deepseek_client.DeepSeekSetupError) as error:
        deepseek_client.load_deepseek_config({})

    assert "DEEPSEEK_API_KEY" in str(error.value)


@pytest.mark.parametrize("placeholder", [
    "your_deepseek_api_key_here",
    "your-key",
    "你的_DeepSeek_API_Key",
])
def test_load_config_rejects_documented_api_key_placeholders(placeholder):
    with pytest.raises(deepseek_client.DeepSeekSetupError) as error:
        deepseek_client.load_deepseek_config({
            "DEEPSEEK_API_KEY": placeholder,
        })

    assert "DEEPSEEK_API_KEY" in str(error.value)


def test_load_config_uses_cloud_defaults():
    config = deepseek_client.load_deepseek_config({
        "DEEPSEEK_API_KEY": "sk-test-key",
    })

    assert config.api_key == "sk-test-key"
    assert config.base_url == "https://api.deepseek.com/anthropic"
    assert config.model == "deepseek-v4-flash"


def test_load_config_normalizes_environment_overrides():
    config = deepseek_client.load_deepseek_config({
        "DEEPSEEK_API_KEY": "  sk-custom-key  ",
        "DEEPSEEK_BASE_URL": "https://example.com/anthropic/",
        "DEEPSEEK_MODEL": "  custom-model  ",
    })

    assert config.api_key == "sk-custom-key"
    assert config.base_url == "https://example.com/anthropic"
    assert config.model == "custom-model"


def test_load_config_rejects_invalid_base_url():
    with pytest.raises(deepseek_client.DeepSeekSetupError) as error:
        deepseek_client.load_deepseek_config({
            "DEEPSEEK_API_KEY": "sk-test-key",
            "DEEPSEEK_BASE_URL": "not-a-url",
        })

    assert "DEEPSEEK_BASE_URL" in str(error.value)


def test_load_config_rejects_empty_model():
    with pytest.raises(deepseek_client.DeepSeekSetupError) as error:
        deepseek_client.load_deepseek_config({
            "DEEPSEEK_API_KEY": "sk-test-key",
            "DEEPSEEK_MODEL": "   ",
        })

    assert "DEEPSEEK_MODEL" in str(error.value)


def test_create_client_uses_deepseek_credentials(monkeypatch):
    factory = Mock(return_value=object())
    monkeypatch.setattr(deepseek_client.anthropic, "Anthropic", factory)
    config = deepseek_client.DeepSeekConfig(
        api_key="sk-test-key",
        base_url="https://api.deepseek.com/anthropic",
        model="deepseek-v4-flash",
    )

    client = deepseek_client.create_deepseek_client(config)

    assert client is factory.return_value
    factory.assert_called_once_with(
        base_url="https://api.deepseek.com/anthropic",
        api_key="sk-test-key",
    )
