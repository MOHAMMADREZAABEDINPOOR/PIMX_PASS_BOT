from __future__ import annotations

import asyncio
import base64
import contextlib
import os
import ssl
import time
from dataclasses import dataclass

from .parser import ParsedConfig


@dataclass(frozen=True, slots=True)
class TestResult:
    latency_ms: int
    status: str  # "active" | "timeout" | "error"
    reachable: bool


_UNVERIFIED_SSL_CONTEXT = ssl.create_default_context()
_UNVERIFIED_SSL_CONTEXT.check_hostname = False
_UNVERIFIED_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    latency_ms: int


def _normalize_path(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _tls_expected(config: ParsedConfig) -> bool:
    tls = (config.tls or "").strip().lower()
    if tls in {"tls", "reality"}:
        return True
    if tls in {"", "none"}:
        return int(config.port) == 443
    return int(config.port) == 443


async def _open_stream(
    host: str,
    port: int,
    *,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    timeout_s: float,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    coro = asyncio.open_connection(
        host=host,
        port=port,
        ssl=ssl_ctx,
        server_hostname=server_hostname,
    )
    return await asyncio.wait_for(coro, timeout=timeout_s)


async def _probe_http1(
    *,
    host: str,
    port: int,
    path: str,
    host_header: str,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        writer.write(req.encode("utf-8", errors="ignore"))
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        ok = line.startswith(b"HTTP/")
        return ProbeResult(ok=ok, latency_ms=int((time.perf_counter() - start) * 1000) if ok else 999)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        with contextlib.suppress(Exception):
            writer.close()  # type: ignore[has-type]
            await writer.wait_closed()  # type: ignore[has-type]


async def _probe_ws(
    *,
    host: str,
    port: int,
    path: str,
    host_header: str,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "\r\n"
        )
        writer.write(req.encode("utf-8", errors="ignore"))
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        ok = b" 101 " in line or line.startswith(b"HTTP/1.1 101") or line.startswith(b"HTTP/1.0 101")
        return ProbeResult(ok=ok, latency_ms=int((time.perf_counter() - start) * 1000) if ok else 999)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        with contextlib.suppress(Exception):
            writer.close()  # type: ignore[has-type]
            await writer.wait_closed()  # type: ignore[has-type]


_H2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
_H2_SETTINGS_EMPTY = b"\x00\x00\x00\x04\x00\x00\x00\x00\x00"


async def _probe_http2(
    *,
    host: str,
    port: int,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        writer.write(_H2_PREFACE + _H2_SETTINGS_EMPTY)
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        data = await asyncio.wait_for(reader.read(9), timeout=timeout_s)
        ok = bool(data)
        return ProbeResult(ok=ok, latency_ms=int((time.perf_counter() - start) * 1000) if ok else 999)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        with contextlib.suppress(Exception):
            writer.close()  # type: ignore[has-type]
            await writer.wait_closed()  # type: ignore[has-type]


async def _probe_tcp(
    *,
    host: str,
    port: int,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    timeout_s: float,
) -> ProbeResult:
    """Basic TCP connection test for raw TCP transports."""
    start = time.perf_counter()
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        # If we can establish a connection, consider it reachable
        # Measure latency based on connection time
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(ok=True, latency_ms=latency_ms)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        with contextlib.suppress(Exception):
            writer.close()  # type: ignore[has-type]
            await writer.wait_closed()  # type: ignore[has-type]


async def _probe_best_of_two(probe: callable) -> ProbeResult:
    first: ProbeResult = await probe()
    if first.ok:
        return first
    second: ProbeResult = await probe()
    return second


async def test_server(
    config: ParsedConfig, *, timeout_s: float, max_latency_ms: int
) -> dict[str, object]:
    host = config.add
    port = int(config.port)
    transport = (config.transport or "tcp").strip().lower()
    use_ssl = _tls_expected(config)
    ssl_ctx = _UNVERIFIED_SSL_CONTEXT if use_ssl else None
    host_header = (config.host or config.add).strip() or config.add
    server_hostname = host_header if use_ssl else None

    path = _normalize_path(config.path)
    paths = [path, "/", "/favicon.ico", "/robots.txt"]
    unique_paths: list[str] = []
    for p in paths:
        p2 = _normalize_path(p)
        if p2 not in unique_paths:
            unique_paths.append(p2)

    async def do_probe() -> ProbeResult:
        if transport in {"ws", "websocket"}:
            return await _probe_ws(
                host=host,
                port=port,
                path=path,
                host_header=host_header,
                ssl_ctx=ssl_ctx,
                server_hostname=server_hostname,
                timeout_s=timeout_s,
            )
        if transport in {"grpc", "h2", "http2"}:
            return await _probe_http2(
                host=host,
                port=port,
                ssl_ctx=ssl_ctx,
                server_hostname=server_hostname,
                timeout_s=timeout_s,
            )
        # For raw TCP transports, do a basic connection test
        # This checks if the port is open and measures connection latency
        return await _probe_tcp(
            host=host,
            port=port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )

    result = await _probe_best_of_two(do_probe)
    if not result.ok or result.latency_ms > max_latency_ms:
        return {
            "latency": result.latency_ms,
            "status": "timeout",
            "scanned": True,
            "reachable": False,
        }

    return {
        "latency": result.latency_ms,
        "status": "active",
        "scanned": True,
        "reachable": True,
    }
