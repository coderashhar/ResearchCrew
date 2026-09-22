"""Runtime settings, read from environment variables in one place.

Entrypoints (CLI, FastAPI app) call ``load_env()`` once to pull in a local
``.env``; library code only calls ``get_settings()``, so tests control the
environment completely.
"""

import os
from dataclasses import dataclass
from typing import Mapping

REQUIRED_KEYS = ("MISTRAL_API_KEY", "TAVILY_API_KEY")


class MissingKeyError(RuntimeError):
    """A required environment variable is unset or empty."""

    def __init__(self, name: str):
        super().__init__(f"Missing required environment variable: {name}")
        self.name = name


class InvalidSettingError(ValueError):
    """An environment variable holds a value of the wrong type."""


@dataclass(frozen=True)
class Settings:
    mistral_api_key: str
    tavily_api_key: str
    database_url: str | None = None
    writer_model: str = "mistral-medium-3-5"
    critic_model: str = "mistral-large-latest"
    client_hash_salt: str = ""
    pass_score: int = 7
    max_revisions: int = 2
    time_budget_s: int = 220


def load_env() -> None:
    """Load a local .env file without overriding variables already set."""
    from dotenv import load_dotenv

    load_dotenv(override=False)


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise InvalidSettingError(f"{name} must be an integer, got {raw!r}") from None


def get_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env

    for name in REQUIRED_KEYS:
        if not env.get(name, "").strip():
            raise MissingKeyError(name)

    defaults = Settings(mistral_api_key="", tavily_api_key="")
    return Settings(
        mistral_api_key=env["MISTRAL_API_KEY"].strip(),
        tavily_api_key=env["TAVILY_API_KEY"].strip(),
        database_url=env.get("DATABASE_URL") or None,
        writer_model=env.get("WRITER_MODEL") or defaults.writer_model,
        critic_model=env.get("CRITIC_MODEL") or defaults.critic_model,
        client_hash_salt=env.get("CLIENT_HASH_SALT") or defaults.client_hash_salt,
        pass_score=_int(env, "PASS_SCORE", defaults.pass_score),
        max_revisions=_int(env, "MAX_REVISIONS", defaults.max_revisions),
        time_budget_s=_int(env, "TIME_BUDGET_S", defaults.time_budget_s),
    )
