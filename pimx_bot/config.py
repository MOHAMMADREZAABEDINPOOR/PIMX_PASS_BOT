from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


DataProviderMode = Literal["db", "api"]


def _getenv_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _getenv_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str

    channel_id: int | None
    channel_username: str | None
    channel_link: str | None

    website_url: str | None

    data_provider: DataProviderMode
    api_base_url: str | None

    db_path: str

    servers_to_test: int
    scan_interval_seconds: int
    min_selected_servers: int
    max_selected_servers: int
    source_fetch_timeout_seconds: int

    test_timeout_seconds: float
    max_latency_ms: int
    max_concurrency: int

    servers_per_page: int
    list_update_interval_seconds: int
    session_ttl_seconds: int

    read_db_pool_size: int
    web_host: str
    web_port: int | None
    public_base_url: str | None


def load_settings() -> Settings:
    load_dotenv(override=False)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    channel_id_raw = os.getenv("CHANNEL_ID", "").strip()
    channel_id = int(channel_id_raw) if channel_id_raw else None

    channel_username = os.getenv("CHANNEL_USERNAME", "").strip() or None
    channel_link = os.getenv("CHANNEL_LINK", "").strip() or None
    if not channel_link:
        if channel_username:
            channel_link = f"https://t.me/{channel_username.lstrip('@')}"
        else:
            channel_link = "https://t.me/PIMX_PASS"
    website_url = os.getenv("WEBSITE_URL", "").strip() or None

    data_provider = (os.getenv("DATA_PROVIDER", "db").strip().lower() or "db")
    if data_provider not in ("db", "api"):
        raise RuntimeError("DATA_PROVIDER must be 'db' or 'api'")

    api_base_url = os.getenv("API_BASE_URL", "").strip() or None
    if data_provider == "api" and not api_base_url:
        raise RuntimeError("API_BASE_URL is required when DATA_PROVIDER=api")

    return Settings(
        bot_token=bot_token,
        channel_id=channel_id,
        channel_username=channel_username,
        channel_link=channel_link,
        website_url=website_url,
        data_provider=data_provider,  # type: ignore[arg-type]
        api_base_url=api_base_url,
        db_path=os.getenv("DB_PATH", "./data/pimx_bot.db").strip() or "./data/pimx_bot.db",
        servers_to_test=max(1000, _getenv_int("SERVERS_TO_TEST", 1000)),
        scan_interval_seconds=_getenv_int("SCAN_INTERVAL_SECONDS", 3600),
        min_selected_servers=_getenv_int("MIN_SELECTED_SERVERS", 100),
        max_selected_servers=_getenv_int("MAX_SELECTED_SERVERS", 150),
        source_fetch_timeout_seconds=_getenv_int("SOURCE_FETCH_TIMEOUT_SECONDS", 15),
        test_timeout_seconds=_getenv_float("TEST_TIMEOUT_SECONDS", 3.0),
        max_latency_ms=_getenv_int("MAX_LATENCY_MS", 2000),
        max_concurrency=_getenv_int("MAX_CONCURRENCY", 80),
        servers_per_page=_getenv_int("SERVERS_PER_PAGE", 10),
        list_update_interval_seconds=_getenv_int("LIST_UPDATE_INTERVAL_SECONDS", 3),
        session_ttl_seconds=_getenv_int("SESSION_TTL_SECONDS", 3600),
        read_db_pool_size=_getenv_int("READ_DB_POOL_SIZE", 4),
        web_host=os.getenv("WEB_HOST", "0.0.0.0").strip() or "0.0.0.0",
        web_port=(
            int(os.getenv("WEB_PORT"))
            if os.getenv("WEB_PORT")
            else (int(os.getenv("PORT")) if os.getenv("PORT") else None)
        ),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip() or None,
    )
