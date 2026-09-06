from __future__ import annotations

import os
from pathlib import Path
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
    active_confirmations: int

    servers_per_page: int
    list_update_interval_seconds: int
    session_ttl_seconds: int
    membership_check_interval_seconds: int

    read_db_pool_size: int
    web_host: str
    web_port: int | None
    web_ssl_cert: str | None
    web_ssl_key: str | None
    public_base_url: str | None
    web_skip_top_servers: int


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
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
    website_url = os.getenv("WEBSITE_URL", "").strip() or "https://pimxpass.site/PIMX/PASS/BOT"

    data_provider = (os.getenv("DATA_PROVIDER", "db").strip().lower() or "db")
    if data_provider not in ("db", "api"):
        raise RuntimeError("DATA_PROVIDER must be 'db' or 'api'")

    api_base_url = os.getenv("API_BASE_URL", "").strip() or None
    if data_provider == "api" and not api_base_url:
        raise RuntimeError("API_BASE_URL is required when DATA_PROVIDER=api")

    db_path_raw = os.getenv("DB_PATH", "./data/pimx_bot.db").strip() or "./data/pimx_bot.db"
    db_path = str((project_root / db_path_raw).resolve()) if not os.path.isabs(db_path_raw) else db_path_raw
    web_ssl_cert_raw = os.getenv("WEB_SSL_CERT", "").strip()
    web_ssl_key_raw = os.getenv("WEB_SSL_KEY", "").strip()
    web_ssl_cert = (
        str((project_root / web_ssl_cert_raw).resolve())
        if web_ssl_cert_raw and not os.path.isabs(web_ssl_cert_raw)
        else (web_ssl_cert_raw or None)
    )
    web_ssl_key = (
        str((project_root / web_ssl_key_raw).resolve())
        if web_ssl_key_raw and not os.path.isabs(web_ssl_key_raw)
        else (web_ssl_key_raw or None)
    )

    return Settings(
        bot_token=bot_token,
        channel_id=channel_id,
        channel_username=channel_username,
        channel_link=channel_link,
        website_url=website_url,
        data_provider=data_provider,  # type: ignore[arg-type]
        api_base_url=api_base_url,
        db_path=db_path,
        servers_to_test=max(0, _getenv_int("SERVERS_TO_TEST", 1000)),
        scan_interval_seconds=_getenv_int("SCAN_INTERVAL_SECONDS", 3600),
        min_selected_servers=_getenv_int("MIN_SELECTED_SERVERS", 100),
        max_selected_servers=_getenv_int("MAX_SELECTED_SERVERS", 150),
        source_fetch_timeout_seconds=_getenv_int("SOURCE_FETCH_TIMEOUT_SECONDS", 15),
        test_timeout_seconds=_getenv_float("TEST_TIMEOUT_SECONDS", 3.0),
        max_latency_ms=_getenv_int("MAX_LATENCY_MS", 250),
        max_concurrency=_getenv_int("MAX_CONCURRENCY", 80),
        active_confirmations=_getenv_int("ACTIVE_CONFIRMATIONS", 2),
        servers_per_page=_getenv_int("SERVERS_PER_PAGE", 10),
        list_update_interval_seconds=_getenv_int("LIST_UPDATE_INTERVAL_SECONDS", 3),
        session_ttl_seconds=_getenv_int("SESSION_TTL_SECONDS", 3600),
        membership_check_interval_seconds=_getenv_int("MEMBERSHIP_CHECK_INTERVAL_SECONDS", 120),
        read_db_pool_size=_getenv_int("READ_DB_POOL_SIZE", 4),
        web_host=os.getenv("WEB_HOST", "0.0.0.0").strip() or "0.0.0.0",
        web_port=(
            int(os.getenv("WEB_PORT"))
            if os.getenv("WEB_PORT")
            else (int(os.getenv("PORT")) if os.getenv("PORT") else 8080)
        ),
        web_ssl_cert=web_ssl_cert,
        web_ssl_key=web_ssl_key,
        public_base_url=os.getenv("PUBLIC_BASE_URL", "").strip() or "https://pimxpass.site",
        web_skip_top_servers=_getenv_int("WEB_SKIP_TOP_SERVERS", 0),
    )
