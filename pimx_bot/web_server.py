from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import aiosqlite
from aiohttp import web

from .providers import DataProvider


@dataclass(slots=True)
class WebServer:
    host: str
    port: int
    dbs: Sequence[aiosqlite.Connection]
    provider: DataProvider
    default_per_page: int = 10
    public_base_url: str | None = None

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
            per_page = max(1, min(per_page, 200))
            try:
                max_len_raw = request.query.get("max_len")
                max_config_len = int(max_len_raw) if max_len_raw is not None else None
            except Exception:
                max_config_len = None

            paged = await self.provider.get_servers_page(
                page=page, per_page=per_page, max_config_len=max_config_len
            )
            base = (self.public_base_url or "").rstrip("/")
            servers_payload = []
            for s in paged.servers:
                link = f"{base}/c/{s.id}" if base else None
                servers_payload.append(
                    {
                        "id": s.id,
                        "name": s.name,
                        "latency": s.latency,
                        "country": getattr(s, "country", None),
                        "config": s.config_string,
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
            return web.json_response({"id": server_id, "config": cfg})

        async def webapp(_: web.Request) -> web.StreamResponse:
            if not webapp_html.exists():
                raise web.HTTPNotFound(text="webapp not found")
            return web.FileResponse(webapp_html)

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
        site = web.TCPSite(runner, host=self.host, port=self.port)
        await site.start()
        self._runner = runner
        self._site = site

    async def stop(self) -> None:
        if not self._runner:
            return
        await self._runner.cleanup()
        self._runner = None
        self._site = None
