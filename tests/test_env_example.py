from pathlib import Path

from dotenv import dotenv_values

from deepseek_client import load_deepseek_config


def test_example_environment_drives_the_supported_deepseek_defaults():
    example = dotenv_values(
        Path(__file__).resolve().parents[1] / ".env.example"
    )
    configured = dict(example)
    configured["DEEPSEEK_API_KEY"] = "sk-test-key"
    config = load_deepseek_config(configured)

    assert example["DEEPSEEK_API_KEY"] == ""
    assert config.base_url == "https://api.deepseek.com/anthropic"
    assert config.model == "deepseek-v4-flash"
    assert example["YOUTUBE_API_KEY"]
    assert example["SUPADATA_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in example
    assert not any(key.startswith("OLLAMA_") for key in example)
