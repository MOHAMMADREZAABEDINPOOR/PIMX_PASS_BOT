from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import re
from pathlib import Path
from typing import Sequence
import ssl
from urllib.parse import quote, unquote

import aiosqlite
from aiohttp import web

from .providers import DataProvider
from .db import (
    get_selected_servers_page,
    get_selected_servers_total,
)


@dataclass(slots=True)
class WebServer:
    host: str
    port: int
    dbs: Sequence[aiosqlite.Connection]
    provider: DataProvider
    default_per_page: int = 10
    public_base_url: str | None = None
    ssl_cert_path: str | None = None
    ssl_key_path: str | None = None
    skip_top_servers: int = 0

    _runner: web.AppRunner | None = None
    _site: web.TCPSite | None = None

    async def start(self) -> None:
        if self._runner:
            return

        app = web.Application()
        static_dir = Path(__file__).parent / "static"
        webapp_html = static_dir / "webapp.html"

        async def health(_: web.Request) -> web.Response:
            return web.json_response({"ok": True})

        async def config(request: web.Request) -> web.Response:
            raw_id = request.match_info.get("id", "")
            try:
                server_id = int(raw_id)
            except Exception:
                raise web.HTTPBadRequest(text="invalid id")

            cfg = await self.provider.get_server_config(server_id=server_id)
            if not cfg:
                raise web.HTTPNotFound(text="not found")
            cfg = _normalize_config_for_import(cfg, remark="PIMXPASS")
            return web.Response(
                text=cfg,
                content_type="text/plain",
                headers={"Cache-Control": "no-store"},
            )

        async def status(_: web.Request) -> web.Response:
            scan = await self.provider.get_scan_status()
            return web.json_response(
                {
                    "is_scanning": scan.is_scanning,
                    "progress": scan.progress,
                    "total": scan.total,
                    "tested": scan.tested,
                    "active": scan.active,
                    "message": scan.message,
                    "scan_completed_at": scan.scan_completed_at,
                    "next_scan_at": scan.next_scan_at,
                    "default_per_page": self.default_per_page,
                }
            )

        async def servers(request: web.Request) -> web.Response:
            try:
                page = max(0, int(request.query.get("page", "0")))
            except Exception:
                page = 0
            try:
                per_page = int(request.query.get("per_page", str(self.default_per_page)))
            except Exception:
                per_page = self.default_per_page
            # Keep website output focused: cap to 150 servers per request.
            per_page = max(1, min(per_page, 150))
            try:
                max_len_raw = request.query.get("max_len")
                max_config_len = int(max_len_raw) if max_len_raw is not None else None
            except Exception:
                max_config_len = None

            paged = await self.provider.get_servers_page(
                page=page, per_page=per_page, max_config_len=max_config_len
            )
            # If requested, skip the first N servers (fastest) in the website output.
            # This is a pragmatic workaround for providers that tend to produce flaky "too-good-to-be-true" servers.
            if int(self.skip_top_servers or 0) > 0 and self.dbs:
                skip = max(0, int(self.skip_top_servers))
                db = self.dbs[0]
                total_selected = await get_selected_servers_total(db, max_latency_ms=99999)
                eff_total = min(150, max(0, int(total_selected) - skip))
                offset = page * per_page + skip
                servers_list = await get_selected_servers_page(
                    db,
                    offset=offset,
                    limit=per_page,
                    max_config_len=max_config_len,
                    max_latency_ms=99999,
                )
                paged = type(paged)(servers=servers_list, total=eff_total)
            base = (self.public_base_url or "").rstrip("/")
            servers_payload = []
            for s in paged.servers:
                link = f"{base}/c/{s.id}" if base else None
                flag = _country_flag(getattr(s, "country", None))
                name = "PIMXPASS"
                clean_cfg = _normalize_config_for_import(s.config_string, remark=name)
                servers_payload.append(
                    {
                        "id": s.id,
                        "name": name,
                        "latency": s.latency,
                        "country": getattr(s, "country", None),
                        "config": clean_cfg,
                        "copy_url": link,
                    }
                )

            return web.json_response(
                {
                    "page": page,
                    "per_page": per_page,
                    "total": paged.total,
                    "servers": servers_payload,
                }
            )

        async def server_config(request: web.Request) -> web.Response:
            raw_id = request.match_info.get("id", "")
            try:
                server_id = int(raw_id)
            except Exception:
                raise web.HTTPBadRequest(text="invalid id")
            cfg = await self.provider.get_server_config(server_id=server_id)
            if not cfg:
                raise web.HTTPNotFound(text="not found")
            cfg = _normalize_config_for_import(cfg, remark="PIMXPASS")
            return web.json_response({"id": server_id, "config": cfg})

        async def webapp(_: web.Request) -> web.StreamResponse:
            if not webapp_html.exists():
                raise web.HTTPNotFound(text="webapp not found")
            data = webapp_html.read_text(encoding="utf-8")
            return web.Response(text=data, content_type="text/html", charset="utf-8")

        app.router.add_get("/health", health)
        app.router.add_get("/", webapp if webapp_html.exists() else health)
        app.router.add_get("/c/{id}", config)
        app.router.add_get("/api/status", status)
        app.router.add_get("/api/servers", servers)
        app.router.add_get("/api/servers/{id}/config", server_config)
        app.router.add_get("/webapp", webapp)
        app.router.add_get("/app", webapp)
        if static_dir.exists():
            app.router.add_static("/static/", static_dir)

        runner = web.AppRunner(app)
        await runner.setup()
        ssl_context = None
        if self.ssl_cert_path and self.ssl_key_path:
            cert_path = Path(self.ssl_cert_path)
            key_path = Path(self.ssl_key_path)
            if cert_path.exists() and key_path.exists():
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(str(cert_path), str(key_path))
        site = web.TCPSite(runner, host=self.host, port=self.port, ssl_context=ssl_context)
        await site.start()
        self._runner = runner
        self._site = site

    async def stop(self) -> None:
        if not self._runner:
            return
        await self._runner.cleanup()
        self._runner = None
        self._site = None



def _country_flag(country: str | None) -> str:
    code = (country or "").strip().upper()
    if not code or code == "UNKNOWN":
        return ""
    code = code.split("-")[0].split("_")[0]
    if len(code) == 2 and code.isalpha():
        base = 0x1F1E6
        return chr(base + (ord(code[0]) - ord("A"))) + chr(base + (ord(code[1]) - ord("A")))
    return ""


_QUERY_KEY_ALIASES: dict[str, str] = {
    "publicKey": "pbk",
    "shortId": "sid",
    "spiderX": "spx",
}
_TYPE_VALUE_ALIASES: dict[str, str] = {
    "websocket": "ws",
}


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


def _normalize_config_for_import(cfg: str, *, remark: str) -> str:
    base = str(cfg or "").strip()
    if not base:
        return ""
    base = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", base)
    base = re.sub(r"\s+", "", base)
    if "#" in base:
        base = base.split("#", 1)[0]

    base = _normalize_vmess_for_import(base, remark=remark)
    if "?" in base:
        head, query = base.split("?", 1)
        raw_parts = [p for p in query.split("&") if p]
        parts: list[str] = []
        type_parts: list[str] = []
        seen_single: set[str] = set()
        seen_exact: set[str] = set()
        for raw in raw_parts:
            key, eq, val = raw.partition("=")
            if eq:
                canonical_key = _QUERY_KEY_ALIASES.get(key, key)
                if canonical_key != key:
                    key = canonical_key
                if key == "type":
                    normalized_val = _TYPE_VALUE_ALIASES.get(val, val)
                    if normalized_val != val:
                        val = normalized_val

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
        base = head + (f"?{query2}" if query2 else "")

    normalized = base.strip()
    if normalized.startswith("vmess://"):
        return normalized
    return f"{normalized}#{(remark or 'PIMXPASS').strip()}"
