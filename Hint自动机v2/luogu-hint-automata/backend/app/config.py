import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    cache_hours: int = int(os.getenv("CACHE_HOURS", "24"))
    luogu_timeout: int = int(os.getenv("LUOGU_TIMEOUT", "25"))
    max_solution_details: int = int(os.getenv("MAX_SOLUTION_DETAILS", "5"))
    hint_levels: list[str] = field(default_factory=lambda: _split_csv(os.getenv("HINT_LEVELS", "keyword,concept,approach,next_step")))

    llm_provider: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5:14b")
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "120"))

    luogu_enabled: bool = os.getenv("LUOGU_ENABLED", "true").lower() == "true"
    demo_api_key: str = os.getenv("DEMO_API_KEY", "")

    app_url: str = os.getenv("APP_URL", "")
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))


settings = Settings()
