"""Configuration and client construction for the DeepSeek API."""

from dataclasses import dataclass
import os
from urllib.parse import urlparse

import anthropic
from dotenv import load_dotenv


DEFAULT_BASE_URL = "https://api.deepseek.com/anthropic"
DEFAULT_MODEL = "deepseek-v4-flash"
PLACEHOLDER_API_KEYS = {
    "your_deepseek_api_key_here",
    "your-key",
    "你的_deepseek_api_key",
}


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str


class DeepSeekSetupError(RuntimeError):
    """Raised when DeepSeek configuration is missing or invalid."""


def load_deepseek_config(environ=None):
    load_dotenv()
    values = os.environ if environ is None else environ
    api_key = values.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key.casefold() in PLACEHOLDER_API_KEYS:
        raise DeepSeekSetupError(
            "请在 .env 中填写有效的 DEEPSEEK_API_KEY"
        )

    base_url = values.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = values.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip()
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise DeepSeekSetupError(
            "DEEPSEEK_BASE_URL 必须是有效的 http 或 https 地址"
        )
    if not model:
        raise DeepSeekSetupError("DEEPSEEK_MODEL 不能为空")

    return DeepSeekConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def create_deepseek_client(config):
    return anthropic.Anthropic(
        base_url=config.base_url,
        api_key=config.api_key,
    )
