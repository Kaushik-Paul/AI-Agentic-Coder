import os
from functools import lru_cache
from typing import Any

import requests
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENCODE_GO_OPENAI_BASE_URL = "https://opencode.ai/zen/go/v1"
OPENCODE_GO_ANTHROPIC_BASE_URL = "https://opencode.ai/zen/go"
OPENCODE_GO_MODELS_URL = "https://opencode.ai/zen/go/v1/models"

DEFAULT_OPENROUTER_MODEL = "moonshotai/kimi-k2:free"
DEFAULT_OPENCODE_GO_MODEL = "minimax-m2.7"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _opencode_model_id(model: str) -> str:
    return model.removeprefix("opencode-go/").strip()


def _openrouter_model_id(model: str) -> str:
    model = model.strip()
    if model.startswith("openrouter/"):
        return model
    return f"openrouter/{model}"


def _strings_from(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.lower()]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_strings_from(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_strings_from(item))
        return strings
    return []


@lru_cache(maxsize=32)
def _opencode_go_api_style(model: str, api_key: str) -> str:
    configured = os.getenv("OPENCODE_GO_API_STYLE", "auto").strip().lower()
    if configured in {"openai", "anthropic"}:
        return configured
    if configured != "auto":
        raise RuntimeError("OPENCODE_GO_API_STYLE must be auto, openai, or anthropic")

    model_id = _opencode_model_id(model)
    try:
        response = requests.get(
            OPENCODE_GO_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        models = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(models, list):
            for item in models:
                if not isinstance(item, dict):
                    continue
                ids = {
                    str(item.get("id", "")),
                    str(item.get("model", "")),
                    str(item.get("name", "")),
                }
                if model_id not in ids and f"opencode-go/{model_id}" not in ids:
                    continue
                details = " ".join(_strings_from(item))
                if "messages" in details or "anthropic" in details:
                    return "anthropic"
                if (
                    "chat/completions" in details
                    or "openai" in details
                    or "alibaba" in details
                ):
                    return "openai"
    except requests.RequestException:
        pass

    if model_id.startswith("minimax-"):
        return "anthropic"
    return "openai"


def create_llm() -> LLM:
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    timeout = int(os.getenv("LLM_TIMEOUT", "300"))

    if _env_bool("USE_OPENROUTER", default=False):
        return LLM(
            model=_openrouter_model_id(
                os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
            ),
            api_base=OPENROUTER_BASE_URL,
            api_key=_env_required("OPENROUTER_API_KEY"),
            temperature=temperature,
            timeout=timeout,
        )

    api_key = _env_required("OPENCODE_GO_API_KEY")
    model = _opencode_model_id(os.getenv("OPENCODE_GO_MODEL", DEFAULT_OPENCODE_GO_MODEL))
    api_style = _opencode_go_api_style(model, api_key)

    if api_style == "anthropic":
        return LLM(
            model=f"anthropic/{model}",
            api_base=OPENCODE_GO_ANTHROPIC_BASE_URL,
            api_key=api_key,
            temperature=temperature,
            timeout=timeout,
        )

    return LLM(
        model=f"openai/{model}",
        api_base=OPENCODE_GO_OPENAI_BASE_URL,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout,
    )
