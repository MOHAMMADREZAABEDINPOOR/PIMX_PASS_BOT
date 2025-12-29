from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import aiosqlite

from . import db as db_mod
from .parser import ParsedConfig, parse_server_configs
from .server_tester import test_server


@dataclass(slots=True)
class ScanStatus:
    is_scanning: bool = False
    progress: int = 0
    total: int = 0
    tested: int = 0
    active: int = 0
    message: str = "idle"
    scan_completed_at: str | None = None
    next_scan_at: str | None = None


class Scanner:
    def __init__(self, *, db: aiosqlite.Connection, settings: Any):
        self._db = db
        self._settings = settings
        self._status = ScanStatus()
        self._lock = asyncio.Lock()

    @property
    def status(self) -> ScanStatus:
        return self._status

    async def scan_once(self) -> None:
        if self._lock.locked():
            return

        async with self._lock:
            self._status.is_scanning = True
            self._status.progress = 0
            self._status.total = int(self._settings.servers_to_test)
            self._status.tested = 0
            self._status.active = 0
            self._status.message = "در حال تست سرورها..."
            self._status.scan_completed_at = None
            self._status.next_scan_at = None

            try:
                await self._run_scan()
            finally:
                self._status.is_scanning = False

    async def _run_scan(self) -> None:
        scan_started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sources = await db_mod.get_active_sources(self._db)
        if not sources:
            self._status.message = "هیچ سورسی فعال نیست."
            return

        source_country_map = {
            int(src["id"]): _infer_country_code(str(src["url"])) for src in sources if src.get("id") is not None
        }

        servers_needed = int(self._settings.servers_to_test)
        unique: dict[str, ParsedConfig] = {}

        timeout = aiohttp.ClientTimeout(total=int(self._settings.source_fetch_timeout_seconds))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for source in sources:
                if len(unique) >= servers_needed:
                    break
                try:
                    async with session.get(
                        str(source["url"]),
                        headers={"User-Agent": "Mozilla/5.0"},
                    ) as resp:
                        text = await resp.text(errors="ignore")
                except Exception:
                    continue

                parsed = parse_server_configs(text, source_id=int(source["id"]))
                for cfg in parsed:
                    if cfg.original_string not in unique:
                        unique[cfg.original_string] = cfg

                await self._db.execute(
                    "UPDATE sources SET last_scan = CURRENT_TIMESTAMP WHERE id = ?",
                    (int(source["id"]),),
                )
                await self._db.commit()

        if not unique:
            self._status.message = "هیچ کانفیگی پیدا نشد."
            return

        configs = list(unique.values())[:servers_needed]
        total_to_test = len(configs)
        if total_to_test == 0:
            self._status.message = "هیچ کانفیگی پیدا نشد."
            return

        # Only show servers verified in the current scan.
        await self._db.execute("UPDATE servers SET is_selected = 0")
        await self._db.commit()

        self._status.total = total_to_test
        self._status.message = f"در حال تست {total_to_test} سرور..."

        batch_size = 10
        max_concurrency = int(self._settings.max_concurrency)
        semaphore = asyncio.Semaphore(min(batch_size, max_concurrency))
        processed = 0
        active = 0
        cleared_old = False
        counter_lock = asyncio.Lock()
        write_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        geo_cache: dict[str, str | None] = {}
        geo_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6))
        geo_semaphore = asyncio.Semaphore(10)

        async def writer() -> None:
            while True:
                item = await write_queue.get()
                try:
                    if item is None:
                        break
                    await db_mod.upsert_server(self._db, item)
                    await self._db.commit()
                finally:
                    write_queue.task_done()
            await self._db.commit()

        writer_task = asyncio.create_task(writer())

        async def worker(cfg: ParsedConfig) -> None:
            nonlocal processed, active
            async with semaphore:
                result = await test_server(
                    cfg,
                    timeout_s=float(self._settings.test_timeout_seconds),
                    max_latency_ms=int(self._settings.max_latency_ms),
                )
            host_for_geo = (cfg.host or cfg.add or "").strip()
            country_code = source_country_map.get(cfg.source_id) or await _geo_country_code(
                host_for_geo, geo_session, geo_cache, geo_semaphore
            )

            server_row: dict[str, Any] = {
                "config_string": cfg.original_string,
                "protocol": cfg.protocol,
                "transport": cfg.transport,
                "tls": cfg.tls,
                "name": cfg.ps,
                "address": cfg.add,
                "port": cfg.port,
                "host": cfg.host or cfg.add,
                "path": cfg.path or "/",
                "country": country_code,
                "latency": result.get("latency"),
                "status": result.get("status"),
                "reachable": result.get("reachable"),
                "scanned": result.get("scanned"),
                "source_id": cfg.source_id,
                "is_selected": True if result.get("status") == "active" else False,
                "quality_score": 85 if result.get("status") == "active" else 0,
            }
            await write_queue.put(server_row)

            async with counter_lock:
                processed += 1
                if result.get("status") == "active":
                    active += 1
                    if not cleared_old:
                        cleared_old = True
                        await db_mod.delete_servers_before(self._db, before_ts=scan_started_at)

        try:
            for start in range(0, len(configs), batch_size):
                batch = configs[start : start + batch_size]
                tasks = [asyncio.create_task(worker(cfg)) for cfg in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await write_queue.join()
                async with counter_lock:
                    current_processed = processed
                    current_active = active
                self._status.tested = current_processed
                self._status.active = current_active
                self._status.progress = (
                    int((current_processed / total_to_test) * 100) if total_to_test else 0
                )
                self._status.message = (
                    f"{current_processed}/{total_to_test} تست شد ({current_active} فعال)"
                )
            await write_queue.put(None)
            await write_queue.join()
            await writer_task
        finally:
            await geo_session.close()

        await db_mod.manage_selected_servers(
            self._db,
            min_selected=int(self._settings.min_selected_servers),
            max_selected=int(self._settings.max_selected_servers),
        )

        completed_at = datetime.now(timezone.utc)
        next_at = completed_at + timedelta(seconds=int(self._settings.scan_interval_seconds))
        self._status.scan_completed_at = completed_at.isoformat()
        self._status.next_scan_at = next_at.isoformat()
        self._status.progress = 100
        self._status.message = f"اسکن تمام شد - {active} سرور فعال"

        await db_mod.update_stats(
            self._db,
            scan_completed_at=self._status.scan_completed_at,
            next_scan_at=self._status.next_scan_at,
        )


def _infer_country_code(source_url: str) -> str | None:
    url = (source_url or "").lower()
    # Look for the last /xx/ in the path (e.g. .../configs/us/all.txt)
    path_matches = re.findall(r"/([a-z]{2})/", url)
    if path_matches:
        return path_matches[-1].upper()
    # Look for -xx.txt or _xx.txt at the end
    file_match = re.search(r"[-_/]([a-z]{2})\\.txt", url)
    if file_match:
        return file_match.group(1).upper()
    return None


async def _geo_country_code(
    host: str,
    session: aiohttp.ClientSession,
    cache: dict[str, str | None],
    semaphore: asyncio.Semaphore,
) -> str | None:
    key = (host or "").strip().lower()
    if not key:
        return None
    if key in cache:
        return cache[key]

    code: str | None = None
    url = f"http://ip-api.com/json/{key}?fields=status,countryCode"
    try:
        async with semaphore:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    raw = str(data.get("countryCode") or "").upper()
                    if raw:
                        code = raw
    except Exception:
        code = None

    cache[key] = code
    return code
