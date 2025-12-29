from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import aiohttp
import aiosqlite

from .db import (
    ListedServer,
    get_scan_times,
    get_selected_servers_page,
    get_selected_servers_total,
    get_selected_servers_total_with_max_len,
    get_server_config_string,
)
from .scanner import ScanStatus, Scanner


@dataclass(frozen=True, slots=True)
class PagedServers:
    servers: list[ListedServer]
    total: int


class DataProvider(Protocol):
    async def get_scan_status(self) -> ScanStatus: ...

    async def get_servers_page(
        self, *, page: int, per_page: int, max_config_len: int | None = None
    ) -> PagedServers: ...

    async def get_server_config(self, *, server_id: int) -> str | None: ...


class DbProvider:
    def __init__(self, *, dbs: list[aiosqlite.Connection], scanner: Scanner):
        self._dbs = dbs
        self._scanner = scanner
        self._idx = 0

    async def get_scan_status(self) -> ScanStatus:
        current = self._scanner.status
        status = ScanStatus(
            is_scanning=current.is_scanning,
            progress=current.progress,
            total=current.total,
            tested=current.tested,
            active=current.active,
            message=current.message,
            scan_completed_at=current.scan_completed_at,
            next_scan_at=current.next_scan_at,
        )
        db = self._pick_db()
        completed_at, next_at = await get_scan_times(db)
        if status.scan_completed_at is None:
            status.scan_completed_at = completed_at
        if status.next_scan_at is None:
            status.next_scan_at = next_at
        return status

    def _pick_db(self) -> aiosqlite.Connection:
        if not self._dbs:
            raise RuntimeError("No DB connections available")
        self._idx = (self._idx + 1) % len(self._dbs)
        return self._dbs[self._idx]

    async def get_servers_page(
        self, *, page: int, per_page: int, max_config_len: int | None = None
    ) -> PagedServers:
        db = self._pick_db()
        if max_config_len is None:
            total = await get_selected_servers_total(db)
        else:
            total = await get_selected_servers_total_with_max_len(db, max_config_len=max_config_len)
        if total <= 0:
            return PagedServers(servers=[], total=0)

        max_page = max(0, (total - 1) // per_page)
        page = max(0, min(page, max_page))
        offset = page * per_page
        servers = await get_selected_servers_page(
            db, offset=offset, limit=per_page, max_config_len=max_config_len
        )
        return PagedServers(servers=servers, total=total)

    async def get_server_config(self, *, server_id: int) -> str | None:
        db = self._pick_db()
        return await get_server_config_string(db, server_id)


class ApiProvider:
    def __init__(self, *, api_base_url: str):
        self._base = api_base_url.rstrip("/")

    async def get_scan_status(self) -> ScanStatus:
        url = f"{self._base}/scan-status"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    data = await resp.json()
        except Exception:
            return ScanStatus(is_scanning=False, message="unknown")

        # supports both camelCase and snake_case
        is_scanning = bool(data.get("isScanning") or data.get("is_scanning") or False)
        tested = int(data.get("tested") or 0)
        total = int(data.get("total") or 0)
        active = int(data.get("active") or 0)
        progress = int(data.get("progress") or 0)
        message = str(data.get("message") or "scan-status")
        return ScanStatus(
            is_scanning=is_scanning,
            tested=tested,
            total=total,
            active=active,
            progress=progress,
            message=message,
            scan_completed_at=data.get("scanCompletedAt") or data.get("scan_completed_at"),
            next_scan_at=data.get("nextScanAt") or data.get("next_scan_at"),
        )

    async def get_servers_page(
        self, *, page: int, per_page: int, max_config_len: int | None = None
    ) -> PagedServers:
        url = f"{self._base}/servers"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                data = await resp.json()

        servers_list = data.get("servers") if isinstance(data, dict) else data
        if not isinstance(servers_list, list):
            servers_list = []

        listed: list[ListedServer] = []
        for s in servers_list:
            try:
                listed.append(
                        ListedServer(
                            id=int(s.get("id")),
                            name=str(s.get("name") or s.get("ps") or "Server"),
                            latency=int(s.get("latency")) if s.get("latency") is not None else None,
                            country=(
                                str(s.get("country") or s.get("countryCode") or s.get("cc") or "").strip() or None
                            ),
                            config_string=str(
                                s.get("config_string") or s.get("config") or s.get("originalString") or ""
                            ),
                        )
                )
            except Exception:
                continue

        if max_config_len is not None:
            listed = [s for s in listed if len(s.config_string or "") <= int(max_config_len)]

        total = len(listed)
        if total <= 0:
            return PagedServers(servers=[], total=0)

        max_page = max(0, (total - 1) // per_page)
        page = max(0, min(page, max_page))
        start = page * per_page
        end = start + per_page
        return PagedServers(servers=listed[start:end], total=total)

    async def get_server_config(self, *, server_id: int) -> str | None:
        # API mode only has list endpoint in the reference project; we fetch the list and find it.
        url = f"{self._base}/servers"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                data = await resp.json()

        servers_list = data.get("servers") if isinstance(data, dict) else data
        if not isinstance(servers_list, list):
            return None

        for s in servers_list:
            try:
                if int(s.get("id")) == server_id:
                    return str(s.get("config_string") or s.get("config") or s.get("originalString") or "")
            except Exception:
                continue
        return None
