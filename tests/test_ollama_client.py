from unittest.mock import Mock

import pytest
import requests

import ollama_client


def test_load_config_uses_local_defaults():
    config = ollama_client.load_ollama_config({})
    assert config.base_url == "http://localhost:11434"
    assert config.model == "qwen3.5:4b"


def test_load_config_uses_environment_overrides():
    config = ollama_client.load_ollama_config({
        "OLLAMA_BASE_URL": "http://127.0.0.1:11435/",
        "OLLAMA_MODEL": "qwen3.5:9b",
    })
    assert config.base_url == "http://127.0.0.1:11435"
    assert config.model == "qwen3.5:9b"


def test_create_client_targets_ollama(monkeypatch):
    factory = Mock(return_value=object())
    monkeypatch.setattr(ollama_client.anthropic, "Anthropic", factory)
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    client = ollama_client.create_ollama_client(config)
    assert client is factory.return_value
    factory.assert_called_once_with(
        base_url="http://localhost:11434",
        api_key="ollama",
    )


class FakeResponse:
    def __init__(self, models, status_code=200):
        self._models = models
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return {"models": [{"name": name} for name in self._models]}


def test_readiness_accepts_installed_model():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse(["qwen3.5:4b"]))
    ollama_client.ensure_ollama_ready(config, http_get=http_get)
    http_get.assert_called_once_with(
        "http://localhost:11434/api/tags",
        timeout=5,
    )


def test_readiness_explains_unavailable_server():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(side_effect=requests.ConnectionError("refused"))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "无法连接 Ollama" in str(error.value)
    assert "http://localhost:11434" in str(error.value)


def test_readiness_explains_missing_model():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse(["qwen3.5:9b"]))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "qwen3.5:4b" in str(error.value)
    assert "ollama pull qwen3.5:4b" in str(error.value)


def test_readiness_explains_http_failure():
    config = ollama_client.OllamaConfig(
        base_url="http://localhost:11434",
        model="qwen3.5:4b",
    )
    http_get = Mock(return_value=FakeResponse([], status_code=500))
    with pytest.raises(ollama_client.OllamaSetupError) as error:
        ollama_client.ensure_ollama_ready(config, http_get=http_get)
    assert "检查 Ollama 状态失败" in str(error.value)
