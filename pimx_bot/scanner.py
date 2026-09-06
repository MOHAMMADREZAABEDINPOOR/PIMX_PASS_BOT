from __future__ import annotations

import asyncio
import logging
import hashlib
import random
from dataclasses import dataclass
import re
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
import aiosqlite
from urllib.parse import quote, unquote

from . import db as db_mod
from .parser import ParsedConfig, parse_server_configs
from .server_tester import test_server

logger = logging.getLogger(__name__)

_QUERY_VALUE_SAFE = "-._~:/?@!$'()*+,;="


def _safe_b64decode_to_text(data: str) -> str:
    s = (data or "").strip()
    if not s:
        return ""
    s = s.replace("-", "+").replace("_", "/")
    padding = (-len(s)) % 4
    if padding:
        s = s + ("=" * padding)
    try:
        raw = base64.b64decode(s.encode("ascii", errors="ignore"))
    except Exception:
        return ""
    try:
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _compact_query_value(val: str) -> str:
    value = str(val or "")
    if not value or "%" not in value:
        return value
    try:
        decoded = unquote(value)
    except Exception:
        return value
    return quote(decoded, safe=_QUERY_VALUE_SAFE)


def _normalize_vmess_for_import(cfg: str, *, remark: str) -> str:
    base = str(cfg or "").strip()
    if not base.startswith("vmess://"):
        return base
    payload = base[len("vmess://") :]
    decoded_json = _safe_b64decode_to_text(payload)
    if not decoded_json:
        return base
    try:
        data = json.loads(decoded_json)
    except Exception:
        return base
    if not isinstance(data, dict):
        return base
    data["ps"] = (remark or "PIMXPASS").strip()
    encoded = base64.urlsafe_b64encode(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    encoded = encoded.rstrip("=")
    return f"vmess://{encoded}"


def _normalize_for_copy(cfg: str, *, remark: str, drop_exact: set[str] | None = None) -> str:
    base_text = str(cfg or "").strip()
    if not base_text:
        return ""
    base_text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", base_text)
    base_text = re.sub(r"\s+", "", base_text)
    if "#" in base_text:
        base_text = base_text.split("#", 1)[0]

    base_text = _normalize_vmess_for_import(base_text, remark=remark)
    if base_text.startswith("vmess://"):
        return base_text

    if "?" in base_text:
        head, query = base_text.split("?", 1)
        raw_parts = [p for p in query.split("&") if p]
        parts: list[str] = []
        type_parts: list[str] = []
        seen_single: set[str] = set()
        seen_exact: set[str] = set()
        for raw in raw_parts:
            if drop_exact and raw in drop_exact:
                continue
            key, eq, val = raw.partition("=")
            if eq:
                if key == "publicKey":
                    key = "pbk"
                elif key == "shortId":
                    key = "sid"
                elif key == "spiderX":
                    key = "spx"
                if key == "type" and val == "websocket":
                    val = "ws"
                val = _compact_query_value(val)
                if val == "":
                    continue
                raw = f"{key}={val}"
                if key in {"pbk", "sid", "spx", "type"}:
                    if key in seen_single:
                        continue
                    seen_single.add(key)
            if raw in seen_exact:
                continue
            seen_exact.add(raw)
            if raw.startswith("type="):
                type_parts.append(raw)
            else:
                parts.append(raw)
        if type_parts:
            parts.extend(type_parts[:1])
        query2 = "&".join(parts)
        base_text = head + (f"?{query2}" if query2 else "")

    return f"{base_text.strip()}#{(remark or 'PIMXPASS').strip()}"


def _copy_config(cfg: str, *, remark: str = "PIMXPASS", max_len: int = 256) -> str | None:
    drop_sets: list[set[str] | None] = [
        None,
        {"headerType=none"},
        {"headerType=none", "encryption=none"},
        {"headerType=none", "encryption=none", "type=tcp"},
    ]
    for drop in drop_sets:
        candidate = _normalize_for_copy(cfg, remark=remark, drop_exact=drop)
        if candidate and len(candidate) <= max_len:
            return candidate
    return None


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

    def _required_active_confirmations(self) -> int:
        # Some servers pass lightweight probes but fail in real clients (false-positives).
        # Require multiple consecutive "active" results to reduce flaky/incorrect actives.
        raw = getattr(self._settings, "active_confirmations", None)
        try:
            value = int(raw) if raw is not None else 2
        except Exception:
            value = 2
        return max(1, min(5, value))

    @staticmethod
    def _seed_for_scan(scan_started_at: str) -> int:
        # Deterministic per scan invocation (helps spread sampling and makes logs repeatable).
        digest = hashlib.sha256(scan_started_at.encode("utf-8", errors="ignore")).hexdigest()
        return int(digest[:8], 16)

    @property
    def status(self) -> ScanStatus:
        return self._status

    async def scan_once(self) -> None:
        if self._lock.locked():
            return

        async with self._lock:
            self._status.is_scanning = True
            self._status.progress = 0
            self._status.total = 0
            self._status.tested = 0
            self._status.active = 0
            self._status.message = "در حال شروع اسکن..."
            self._status.scan_completed_at = None
            self._status.next_scan_at = None

            try:
                await self._run_scan()
            except Exception as e:
                logger.error(f"Scan error: {e}")
                self._status.message = f"خطا در اسکن: {e}"
            finally:
                self._status.is_scanning = False

    async def _run_scan(self) -> None:
        scan_started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        scan_seed = self._seed_for_scan(scan_started_at)
        rng = random.Random(scan_seed)
        if await db_mod.maybe_purge_runtime_data(self._db, interval_days=3):
            logger.info("Purged runtime DB data (3-day maintenance)")
        sources = await db_mod.get_active_sources(self._db)
        if not sources:
            self._status.message = "هیچ سورسی فعال نیست."
            return

        # Don't re-display servers from the previous scan.
        # We also reset `scanned` so list endpoints can show only servers discovered in this scan.
        await self._db.execute("UPDATE servers SET is_selected = 0, scanned = 0")
        await self._db.commit()

        source_country_map = {
            int(src["id"]): _infer_country_code(str(src["url"])) for src in sources if src.get("id") is not None
        }

        min_selected = int(self._settings.min_selected_servers)  # 100
        max_selected = int(self._settings.max_selected_servers)  # 150
        max_latency_ms = int(self._settings.max_latency_ms)  # 250
        servers_to_test = int(self._settings.servers_to_test)  # 1000
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Fetch configs from sources (max 1000 initially)
        # ═══════════════════════════════════════════════════════════════════
        self._status.message = "در حال دریافت کانفیگ‌ها..."
        logger.info("Fetching configs from sources...")
        
        unique: dict[str, ParsedConfig] = {}
        timeout = aiohttp.ClientTimeout(total=int(self._settings.source_fetch_timeout_seconds))
        
        # Spread sampling across sources so one bad source doesn't dominate the pool.
        per_source_quota = max(1, (servers_to_test + len(sources) - 1) // max(1, len(sources)))
        parsed_by_source_id: dict[int, list[ParsedConfig]] = {}
        recent_window_s = max(3600, int(getattr(self._settings, "scan_interval_seconds", 3600) or 3600))
        recently_tested = await db_mod.get_recent_config_strings(self._db, window_seconds=recent_window_s)
        def should_test(cfg: ParsedConfig) -> bool:
            # Skip configs that won't import/connect reliably.
            if cfg.protocol in {"vless", "trojan"} and not (cfg.user or "").strip():
                return False
            # Avoid re-testing the same config within the scan window.
            if cfg.original_string in recently_tested:
                return False
            return True

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for source in sources:
                try:
                    async with session.get(
                        str(source["url"]),
                        headers={"User-Agent": "Mozilla/5.0"},
                    ) as resp:
                        text = await resp.text(errors="ignore")
                        source_id = int(source["id"])
                        parsed = parse_server_configs(text, source_id=source_id)
                        parsed_by_source_id[source_id] = parsed
                        if parsed:
                            # Many sources have "dead first, good later" ordering; sample across the list.
                            stride = max(1, len(parsed) // max(1, per_source_quota))
                            offset = (scan_seed ^ source_id) % stride
                            added_for_source = 0
                            for idx in range(offset, len(parsed), stride):
                                if len(unique) >= servers_to_test:
                                    break
                                cfg = parsed[idx]
                                if not should_test(cfg):
                                    continue
                                if cfg.original_string in unique:
                                    continue
                                unique[cfg.original_string] = cfg
                                added_for_source += 1
                                if added_for_source >= per_source_quota:
                                    break
                except Exception as e:
                    logger.warning(f"Failed to fetch from source {source['url']}: {e}")
                    continue

                await self._db.execute(
                    "UPDATE sources SET last_scan = CURRENT_TIMESTAMP WHERE id = ?",
                    (int(source["id"]),),
                )
                await self._db.commit()

        # Top up from any remaining configs (2nd pass) to reach the requested cap.
        if len(unique) < servers_to_test:
            for source in sources:
                if len(unique) >= servers_to_test:
                    break
                source_id = int(source["id"])
                for cfg in parsed_by_source_id.get(source_id, []):
                    if len(unique) >= servers_to_test:
                        break
                    if not should_test(cfg):
                        continue
                    if cfg.original_string in unique:
                        continue
                    unique[cfg.original_string] = cfg

        if not unique:
            self._status.message = "هیچ کانفیگی پیدا نشد."
            return

        # Shuffle so early batches don't look "all dead" (more stable progress + better UX).
        configs = list(unique.values())
        rng.shuffle(configs)
        configs = configs[:servers_to_test]  # Limit to servers_to_test
        total_configs = len(configs)
        self._status.total = total_configs
        logger.info(f"Found {total_configs} unique configs to test")

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: Test servers in batches of 10
        # ═══════════════════════════════════════════════════════════════════
        # Higher batch size = higher parallelism (bounded by MAX_CONCURRENCY).
        # Protocol-level validation is heavier, so keep a sensible cap.
        BATCH_SIZE = max(1, min(int(getattr(self._settings, "max_concurrency", 50) or 50), 50))
        processed = 0
        active_found = 0
        geo_cache: dict[str, str | None] = {}
        
        self._status.message = f"در حال تست {total_configs} سرور..."
        logger.info(f"Starting to test {total_configs} servers in batches of {BATCH_SIZE}")

        # Geo lookup is best-effort; keep it short so it doesn't slow scans.
        geo_timeout = aiohttp.ClientTimeout(total=3)
        test_timeout = float(self._settings.test_timeout_seconds)
        active_confirmations = self._required_active_confirmations()

        async def test_one(
            cfg: ParsedConfig, geo_sess: aiohttp.ClientSession
        ) -> tuple[dict[str, Any] | None, bool]:
            try:
                result = await test_server(cfg, timeout_s=test_timeout, max_latency_ms=max_latency_ms)
                is_active = result.get("status") == "active"
                test_mode = result.get("test_mode")

                # Confirm "active" multiple times to reduce false positives.
                if is_active and active_confirmations > 1 and test_mode != "core":
                    for _ in range(active_confirmations - 1):
                        await asyncio.sleep(0.05)
                        confirm = await test_server(cfg, timeout_s=test_timeout, max_latency_ms=max_latency_ms)
                        if confirm.get("status") != "active":
                            is_active = False
                            # Keep last confirm result so the stored latency/status reflects failure.
                            result = confirm
                            break
                        # Prefer best latency among successful confirmations.
                        try:
                            best_latency = min(
                                int(result.get("latency") or 999),
                                int(confirm.get("latency") or 999),
                            )
                            result["latency"] = best_latency
                        except Exception:
                            pass

                copy_cfg = _copy_config(cfg.original_string, remark="PIMXPASS")
                if is_active and not copy_cfg:
                    # Not eligible for Telegram's 1-tap copy button; treat as inactive so it won't be listed.
                    is_active = False
                    result["status"] = "timeout"

                country_code = source_country_map.get(cfg.source_id)
                if country_code is None and is_active:
                    host_for_geo = (cfg.host or cfg.sni or cfg.add or "").strip()
                    country_code = await _geo_country_code(host_for_geo, geo_sess, geo_cache)

                server_row = {
                    "config_string": cfg.original_string,
                    "copy_config": copy_cfg,
                    "protocol": cfg.protocol,
                    "transport": cfg.transport,
                    "tls": cfg.tls,
                    "name": cfg.ps,
                    "address": cfg.add,
                    "port": cfg.port,
                    "host": cfg.host or cfg.sni or cfg.add,
                    "path": cfg.path or "/",
                    "country": country_code,
                    "latency": result.get("latency"),
                    "status": result.get("status"),
                    "reachable": result.get("reachable"),
                    "scanned": True,
                    "source_id": cfg.source_id,
                    # Mark as selected when active so the list can update during scanning.
                    "is_selected": is_active,
                    "quality_score": 100 - (result.get("latency") or 999) // 10 if is_active else 0,
                }
                return server_row, is_active
            except Exception as e:
                logger.debug(f"Test error for {cfg.add}: {e}")
                return None, False
        
        async with aiohttp.ClientSession(timeout=geo_timeout) as geo_session:
            for batch_start in range(0, total_configs, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_configs)
                batch = configs[batch_start:batch_end]
                
                logger.debug(f"Testing batch {batch_start//BATCH_SIZE + 1}: servers {batch_start+1}-{batch_end}")
                
                # Run batch tests concurrently
                tasks = [test_one(cfg, geo_session) for cfg in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                batch_rows: list[dict[str, Any]] = []
                batch_active_count = 0
                for result in results:
                    processed += 1
                    
                    if isinstance(result, Exception):
                        logger.debug(f"Batch test exception: {result}")
                        continue
                    
                    if result is None or result[0] is None:
                        continue
                    
                    row, is_active = result
                    
                    if is_active:
                        active_found += 1
                        batch_active_count += 1

                    batch_rows.append(row)

                # Save servers from this batch (active + inactive) to support de-duplication across scans.
                if batch_rows:
                    for row in batch_rows:
                        await db_mod.upsert_server(self._db, row)
                    await self._db.commit()
                    logger.info(f"Batch saved: {batch_active_count} active, {len(batch_rows)} total")

                selected_count = 0
                if batch_active_count:
                    selected_count = await db_mod.reselect_top_servers(
                        self._db,
                        max_selected=max_selected,
                        updated_since=scan_started_at,
                        only_updated_since=True,
                    )

                # Update progress
                self._status.tested = processed
                display_active = (
                    min(int(selected_count or 0), max_selected)
                    if batch_active_count
                    else min(active_found, max_selected)
                )
                # The number of active servers found can be higher than the list cap (150).
                self._status.active = active_found
                self._status.progress = int((processed / total_configs) * 100) if total_configs else 0
                self._status.message = (
                    f"{processed}/{total_configs} تست شد (فعال پیدا شده: {active_found} | نمایش: {display_active} از سریع‌ترین‌ها)"
                )

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: If < min_selected active after the first 1000 tests, test 500 more.
        # ═══════════════════════════════════════════════════════════════════
        max_test_budget = max(servers_to_test + 500, 5000)
        tested_set = {c.original_string for c in configs}
        while (
            (active_found < min_selected) or (active_found < max_selected)
        ) and processed < max_test_budget and len(unique) < 3000:
            remaining = max_test_budget - processed
            take = min(500, remaining)

            if active_found < min_selected:
                self._status.message = f"کمتر از {min_selected} فعال - در حال بررسی {take} سرور بیشتر..."
            else:
                self._status.message = f"در حال تکمیل لیست ۱۵۰تایی - بررسی {take} سرور بیشتر..."

            # Fetch more from sources to expand pool.
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for source in sources:
                    if len(unique) >= 3000:
                        break
                    try:
                        async with session.get(
                            str(source["url"]),
                            headers={"User-Agent": "Mozilla/5.0"},
                        ) as resp:
                            text = await resp.text(errors="ignore")
                            parsed = parse_server_configs(text, source_id=int(source["id"]))
                            for cfg in parsed:
                                if not should_test(cfg):
                                    continue
                                if cfg.original_string not in unique:
                                    unique[cfg.original_string] = cfg
                    except Exception:
                        continue

            new_configs = [c for c in unique.values() if c.original_string not in tested_set]
            if not new_configs:
                break

            rng.shuffle(new_configs)
            new_configs = new_configs[:take]
            total_target = processed + len(new_configs)
            self._status.total = max(self._status.total, total_target)
            logger.info(f"Testing {len(new_configs)} additional configs")

            async with aiohttp.ClientSession(timeout=geo_timeout) as geo_session2:
                for batch_start in range(0, len(new_configs), BATCH_SIZE):
                    if processed >= total_target:
                        break

                    batch = new_configs[batch_start:batch_start + BATCH_SIZE]
                    tasks = [test_one(cfg, geo_session2) for cfg in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    batch_rows: list[dict[str, Any]] = []
                    batch_active_count = 0
                    for cfg, result in zip(batch, results, strict=False):
                        if processed >= total_target:
                            break
                        tested_set.add(cfg.original_string)
                        processed += 1
                        if isinstance(result, Exception) or result is None or result[0] is None:
                            continue
                        row, is_active = result
                        if is_active:
                            active_found += 1
                            batch_active_count += 1
                        batch_rows.append(row)

                    if batch_rows:
                        for row in batch_rows:
                            await db_mod.upsert_server(self._db, row)
                        await self._db.commit()

                    selected_count = 0
                    if batch_active_count:
                        selected_count = await db_mod.reselect_top_servers(
                            self._db,
                            max_selected=max_selected,
                            updated_since=scan_started_at,
                            only_updated_since=True,
                        )

                    self._status.tested = processed
                    display_active = (
                        min(int(selected_count or 0), max_selected)
                        if batch_active_count
                        else min(active_found, max_selected)
                    )
                    self._status.active = active_found
                    self._status.progress = int((processed / self._status.total) * 100) if self._status.total else 0
                    self._status.message = (
                        f"تست اضافی: فعال پیدا شده {active_found} | نمایش {display_active} از سریع‌ترین‌ها"
                    )

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 4: Cleanup and finalize
        # ═══════════════════════════════════════════════════════════════════
        selected_total = await db_mod.reselect_top_servers(
            self._db,
            max_selected=max_selected,
            updated_since=scan_started_at,
            only_updated_since=True,
        )

        completed_at = datetime.now(timezone.utc)
        next_at = completed_at + timedelta(seconds=int(self._settings.scan_interval_seconds))
        self._status.scan_completed_at = completed_at.isoformat()
        self._status.next_scan_at = next_at.isoformat()
        self._status.progress = 100

        display_active = min(int(selected_total or 0), max_selected)
        self._status.active = active_found
        self._status.message = (
            f"اسکن تمام شد - فعال پیدا شده: {active_found} | نمایش: {display_active} (۱۵۰ تا از سریع‌ترین‌ها)"
        )
        logger.info(f"Scan completed: active_found={active_found} selected={selected_total}")

        await db_mod.update_stats(
            self._db,
            total_scanned=int(processed),
            total_active=int(active_found),
            total_selected=int(selected_total),
            scan_completed_at=self._status.scan_completed_at,
            next_scan_at=self._status.next_scan_at,
        )


def _infer_country_code(source_url: str) -> str | None:
    url = (source_url or "").lower()
    path_matches = re.findall(r"/([a-z]{2})/", url)
    if path_matches:
        return path_matches[-1].upper()
    file_match = re.search(r"[-_/]([a-z]{2})\.txt", url)
    if file_match:
        return file_match.group(1).upper()
    return None


async def _geo_country_code(
    host: str, session: aiohttp.ClientSession, cache: dict[str, str | None]
) -> str | None:
    key = (host or "").strip().lower()
    if not key:
        return None
    if key in cache:
        return cache[key]

    code = None
    try:
        async with session.get(f"http://ip-api.com/json/{key}?fields=status,countryCode") as resp:
            data = await resp.json()
            if data.get("status") == "success":
                code = str(data.get("countryCode") or "").upper() or None
    except Exception:
        pass

    cache[key] = code
    return code
