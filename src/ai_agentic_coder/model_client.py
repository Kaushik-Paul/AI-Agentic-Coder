import os

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_llm() -> LLM:
    return LLM(
        model=_env_required("MODEL"),
        api_base=_env_required("BASE_URL"),
        api_key=_env_required("API_KEY"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        timeout=int(os.getenv("LLM_TIMEOUT", "300")),
    )
