from dataclasses import dataclass
import os

import anthropic
import requests
from dotenv import load_dotenv


DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:4b"


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    model: str


class OllamaSetupError(RuntimeError):
    """Raised when the local Ollama service is not ready."""


def load_ollama_config(environ=None):
    load_dotenv()
    values = os.environ if environ is None else environ
    base_url = values.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = values.get("OLLAMA_MODEL", DEFAULT_MODEL).strip()
    return OllamaConfig(base_url=base_url, model=model)


def create_ollama_client(config):
    return anthropic.Anthropic(
        base_url=config.base_url,
        api_key="ollama",
    )


def ensure_ollama_ready(config, http_get=requests.get):
    tags_url = f"{config.base_url}/api/tags"
    try:
        response = http_get(tags_url, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        if isinstance(exc, requests.ConnectionError):
            raise OllamaSetupError(
                f"无法连接 Ollama：请确认应用已经启动，地址为 {config.base_url}"
            ) from exc
        raise OllamaSetupError(f"检查 Ollama 状态失败：{exc}") from exc
    except ValueError as exc:
        raise OllamaSetupError("Ollama 返回了无法解析的状态信息") from exc

    installed = {
        item.get("name")
        for item in payload.get("models", [])
        if item.get("name")
    }
    if config.model not in installed:
        raise OllamaSetupError(
            f"未安装模型 {config.model}，请运行：ollama pull {config.model}"
        )
