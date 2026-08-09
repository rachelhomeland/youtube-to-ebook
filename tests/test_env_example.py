from pathlib import Path

from dotenv import dotenv_values

from ollama_client import load_ollama_config


def test_example_environment_drives_the_supported_local_defaults():
    example = dotenv_values(
        Path(__file__).resolve().parents[1] / ".env.example"
    )
    config = load_ollama_config(example)

    assert config.base_url == "http://localhost:11434"
    assert config.model == "qwen3.5:4b"
    assert example["YOUTUBE_API_KEY"]
    assert example["SUPADATA_API_KEY"]
    assert "ANTHROPIC_API_KEY" not in example
