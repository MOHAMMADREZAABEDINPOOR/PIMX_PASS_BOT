from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import ssl
import tempfile
import time
from dataclasses import dataclass
from typing import Any

from .parser import ParsedConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    latency_ms: int


_UNVERIFIED_SSL_CONTEXT = ssl.create_default_context()
_UNVERIFIED_SSL_CONTEXT.check_hostname = False
_UNVERIFIED_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def _normalize_path(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _tls_expected(config: ParsedConfig) -> bool:
    protocol = (config.protocol or "").strip().lower()
    tls = (config.tls or "").strip().lower()
    if tls in {"none", "plain", "0", "false", "off"}:
        return False
    # Trojan is inherently TLS-based; treat it as TLS unless explicitly disabled.
    if protocol == "trojan":
        return True
    if tls in {"tls", "reality", "xtls"}:
        return True
    if tls in {"", "auto"}:
        return int(config.port) == 443
    return int(config.port) == 443


def _trace_request_bytes() -> bytes:
    return (
        b"GET /cdn-cgi/trace HTTP/1.1\r\n"
        b"Host: one.one.one.one\r\n"
        b"Connection: close\r\n"
        b"User-Agent: curl/8\r\n"
        b"\r\n"
    )


def _trace_response_ok(data: bytes) -> bool:
    if not data:
        return False
    if b"HTTP/" not in data[:32]:
        return False
    # Cloudflare trace includes stable markers; require at least one to reduce false-positives.
    return (b"\nh=one.one.one.one\n" in data) or (b"\ncolo=" in data) or (b"\nwarp=" in data)


def _env_str(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    return value if value else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _core_test_mode() -> str:
    return _env_str("REAL_TEST_MODE", "auto").lower()


_CORE_PATH_CACHE: str | None = None


def _find_core_on_disk() -> str | None:
    candidates = ("xray.exe", "xray", "v2ray.exe", "v2ray")
    home = Path.home()
    roots: list[Path] = []
    for p in (
        Path.cwd(),
        Path.cwd().parent,
        Path(__file__).resolve().parents[2],
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
    ):
        if p.exists():
            roots.append(p)

    # Last resort: scan the drive root (very shallow) to catch portable installs like D:\v2rayN\.
    drive_root = Path(Path.cwd().anchor)
    if drive_root.exists():
        roots.append(drive_root)

    seen: set[str] = set()
    unique_roots: list[Path] = []
    for r in roots:
        key = str(r.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(r)

    timeout_s = max(0.5, _env_float("CORE_PATH_SEARCH_TIMEOUT_SECONDS", 6.0))
    deadline = time.perf_counter() + timeout_s

    def max_depth_for(root: Path) -> int:
        # Keep it fast: deeper for small folders, shallow for drive root.
        if root == drive_root:
            return 3
        name = root.name.lower()
        if name in {"downloads", "desktop", "documents"}:
            return 5
        return 4

    for root in unique_roots:
        depth_limit = max_depth_for(root)
        start_depth = len(root.resolve().parts)
        for dirpath, dirnames, filenames in os.walk(root):
            if time.perf_counter() > deadline:
                return None

            current_depth = len(Path(dirpath).parts) - start_depth
            if current_depth >= depth_limit:
                dirnames[:] = []
                continue

            # Prune common huge/irrelevant directories.
            pruned: list[str] = []
            for d in dirnames:
                dl = d.lower()
                if dl in {
                    ".git",
                    ".hg",
                    ".svn",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "node_modules",
                    "dist",
                    "build",
                    ".cache",
                }:
                    continue
                pruned.append(d)
            dirnames[:] = pruned

            for filename in filenames:
                if filename.lower() in candidates:
                    return str(Path(dirpath) / filename)

    return None


def _resolve_core_path(preferred: str | None = None) -> str | None:
    if preferred and os.path.exists(preferred):
        return preferred
    global _CORE_PATH_CACHE
    if _CORE_PATH_CACHE is not None:
        return _CORE_PATH_CACHE or None
    candidates = []
    for key in ("XRAY_PATH", "V2RAY_PATH", "V2RAY_CORE_PATH"):
        env_path = os.getenv(key)
        if env_path:
            candidates.append(env_path)
    for name in ("xray", "xray.exe", "v2ray", "v2ray.exe"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    for path in candidates:
        if path and os.path.exists(path):
            _CORE_PATH_CACHE = path
            return path

    found = _find_core_on_disk()
    if found and os.path.exists(found):
        _CORE_PATH_CACHE = found
        return found
    _CORE_PATH_CACHE = ""
    return None


def _split_alpn(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value:
        return []
    if "," in value:
        parts = [p.strip() for p in value.split(",") if p.strip()]
    else:
        parts = [p.strip() for p in value.split() if p.strip()]
    return parts


def _normalize_transport(raw: str) -> str:
    transport = (raw or "tcp").strip().lower()
    if transport in {"", "tcp"}:
        return "tcp"
    if transport in {"ws", "websocket"}:
        return "ws"
    if transport in {"grpc"}:
        return "grpc"
    if transport in {"h2", "http2", "http"}:
        return "http"
    return transport


def _normalize_service_name(path: str) -> str:
    value = (path or "").strip()
    if value.startswith("/"):
        value = value[1:]
    return value


def _build_stream_settings(config: ParsedConfig) -> dict[str, Any] | None:
    network = _normalize_transport(config.transport)
    stream: dict[str, Any] = {"network": network}

    tls = (config.tls or "").strip().lower()
    if tls and tls not in {"none", "plain", "0", "false", "off"}:
        if tls == "reality":
            pbk = (config.pbk or "").strip()
            sid = (config.sid or "").strip()
            if "," in sid:
                sid = sid.split(",", 1)[0].strip()
            if not (pbk and sid):
                return None
            reality: dict[str, Any] = {
                "publicKey": pbk,
                "shortId": sid,
            }
            server_name = (config.sni or config.host or config.add).strip()
            if server_name:
                reality["serverName"] = server_name
            fp = (config.fp or "").strip()
            if fp:
                reality["fingerprint"] = fp
            alpn = _split_alpn(config.alpn)
            if alpn:
                reality["alpn"] = alpn
            spx = (config.spx or "").strip()
            if spx:
                reality["spiderX"] = spx
            stream["security"] = "reality"
            stream["realitySettings"] = reality
        else:
            tls_settings: dict[str, Any] = {"allowInsecure": True}
            server_name = (config.sni or config.host or config.add).strip()
            if server_name:
                tls_settings["serverName"] = server_name
            alpn = _split_alpn(config.alpn)
            if alpn:
                tls_settings["alpn"] = alpn
            stream["security"] = "tls"
            stream["tlsSettings"] = tls_settings

    if network == "ws":
        ws_settings: dict[str, Any] = {"path": _normalize_path(config.path)}
        host_header = (config.host or config.sni or "").strip()
        if host_header:
            ws_settings["headers"] = {"Host": host_header}
        stream["wsSettings"] = ws_settings
    elif network == "grpc":
        grpc_settings: dict[str, Any] = {}
        service_name = _normalize_service_name(config.path)
        if service_name:
            grpc_settings["serviceName"] = service_name
        authority = (config.host or config.sni or "").strip()
        if authority:
            grpc_settings["authority"] = authority
        if grpc_settings:
            stream["grpcSettings"] = grpc_settings
    elif network == "http":
        http_settings: dict[str, Any] = {}
        path = _normalize_path(config.path)
        if path:
            http_settings["path"] = [path]
        host_header = (config.host or config.sni or "").strip()
        if host_header:
            http_settings["host"] = [host_header]
        if http_settings:
            stream["httpSettings"] = http_settings

    return stream


def _build_xray_outbound(config: ParsedConfig) -> dict[str, Any] | None:
    protocol = (config.protocol or "").strip().lower()
    if protocol not in {"vless", "trojan", "vmess"}:
        return None
    stream_settings = _build_stream_settings(config)
    if stream_settings is None:
        return None

    address = (config.add or "").strip()
    if not address:
        return None
    try:
        port = int(config.port)
    except Exception:
        return None

    if protocol == "vless":
        if not (config.user or "").strip():
            return None
        user: dict[str, Any] = {"id": config.user, "encryption": "none"}
        flow = (config.flow or "").strip()
        if flow:
            user["flow"] = flow
        return {
            "protocol": "vless",
            "tag": "proxy",
            "settings": {"vnext": [{"address": address, "port": port, "users": [user]}]},
            "streamSettings": stream_settings,
        }

    if protocol == "trojan":
        if not (config.user or "").strip():
            return None
        server: dict[str, Any] = {"address": address, "port": port, "password": config.user}
        flow = (config.flow or "").strip()
        if flow:
            server["flow"] = flow
        return {
            "protocol": "trojan",
            "tag": "proxy",
            "settings": {"servers": [server]},
            "streamSettings": stream_settings,
        }

    if protocol == "vmess":
        if not (config.user or "").strip():
            return None
        user: dict[str, Any] = {"id": config.user, "alterId": int(config.vmess_aid or 0)}
        security = (config.vmess_security or "").strip()
        user["security"] = security or "auto"
        return {
            "protocol": "vmess",
            "tag": "proxy",
            "settings": {"vnext": [{"address": address, "port": port, "users": [user]}]},
            "streamSettings": stream_settings,
        }

    return None


def _build_xray_config(*, outbound: dict[str, Any], inbound_port: int) -> dict[str, Any]:
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": inbound_port,
                "protocol": "socks",
                "settings": {"udp": False},
            }
        ],
        "outbounds": [outbound],
    }


_CORE_LAUNCH_TEMPLATE: tuple[str, ...] | None = None
_CORE_LAUNCH_LOCK: asyncio.Lock | None = None
_CORE_LAUNCH_TEMPLATES: tuple[tuple[str, ...], ...] = (
    ("run", "-config", "{config}"),
    ("run", "-c", "{config}"),
    ("-config", "{config}"),
    ("-c", "{config}"),
)

_CORE_TEST_SEMAPHORE: asyncio.Semaphore | None = None


def _core_semaphore() -> asyncio.Semaphore:
    global _CORE_TEST_SEMAPHORE
    if _CORE_TEST_SEMAPHORE is None:
        limit = max(1, _env_int("CORE_TEST_CONCURRENCY", 3))
        _CORE_TEST_SEMAPHORE = asyncio.Semaphore(limit)
    return _CORE_TEST_SEMAPHORE


def _core_launch_lock() -> asyncio.Lock:
    global _CORE_LAUNCH_LOCK
    if _CORE_LAUNCH_LOCK is None:
        _CORE_LAUNCH_LOCK = asyncio.Lock()
    return _CORE_LAUNCH_LOCK


def _render_core_args(template: tuple[str, ...], *, config_path: str) -> list[str]:
    return [arg.format(config=config_path) for arg in template]


async def _start_core_process(
    *,
    core_path: str,
    config_path: str,
    inbound_port: int,
    startup_timeout_s: float,
) -> asyncio.subprocess.Process | None:
    global _CORE_LAUNCH_TEMPLATE

    async def spawn(template: tuple[str, ...], *, capture_stderr: bool) -> asyncio.subprocess.Process:
        args = _render_core_args(template, config_path=config_path)
        return await asyncio.create_subprocess_exec(
            core_path,
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE if capture_stderr else asyncio.subprocess.DEVNULL,
        )

    async def try_template(template: tuple[str, ...], *, capture_stderr: bool) -> asyncio.subprocess.Process | None:
        proc = await spawn(template, capture_stderr=capture_stderr)
        ready = await _wait_for_port("127.0.0.1", inbound_port, startup_timeout_s)
        if ready:
            return proc
        if proc.stderr:
            with contextlib.suppress(Exception):
                preview = await asyncio.wait_for(proc.stderr.read(512), timeout=0.2)
                if preview:
                    logger.debug("Core launch failed (%s): %s", " ".join(_render_core_args(template, config_path=config_path)), preview.decode(errors="ignore"))
        await _terminate_process(proc)
        return None

    # Fast path: cached launch template.
    if _CORE_LAUNCH_TEMPLATE is not None:
        proc = await try_template(_CORE_LAUNCH_TEMPLATE, capture_stderr=False)
        if proc is not None:
            return proc
        _CORE_LAUNCH_TEMPLATE = None

    # Slow path: detect correct invocation once.
    async with _core_launch_lock():
        if _CORE_LAUNCH_TEMPLATE is not None:
            proc = await try_template(_CORE_LAUNCH_TEMPLATE, capture_stderr=False)
            if proc is not None:
                return proc
            _CORE_LAUNCH_TEMPLATE = None

        for template in _CORE_LAUNCH_TEMPLATES:
            proc = await try_template(template, capture_stderr=True)
            if proc is not None:
                _CORE_LAUNCH_TEMPLATE = template
                return proc

    return None


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


async def _wait_for_port(host: str, port: int, timeout_s: float) -> bool:
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            await asyncio.sleep(0.05)
    return False


def _socks5_connect_request(target_host: str, target_port: int) -> bytes:
    try:
        ip = ipaddress.ip_address(target_host)
        if ip.version == 4:
            addr = ip.packed
            atyp = b"\x01"
        else:
            addr = ip.packed
            atyp = b"\x04"
    except ValueError:
        host_bytes = target_host.encode("idna")
        atyp = b"\x03"
        addr = bytes([len(host_bytes)]) + host_bytes
    return b"\x05\x01\x00" + atyp + addr + int(target_port).to_bytes(2, "big")


async def _socks_http_probe(
    *,
    host: str,
    port: int,
    target_host: str,
    target_port: int,
    target_path: str,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    writer: asyncio.StreamWriter | None = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout_s)

        writer.write(b"\x05\x01\x00")
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        resp = await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)
        if resp != b"\x05\x00":
            return ProbeResult(ok=False, latency_ms=999)

        req = _socks5_connect_request(target_host, target_port)
        writer.write(req)
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        header = await asyncio.wait_for(reader.readexactly(4), timeout=timeout_s)
        if len(header) < 4 or header[1] != 0x00:
            return ProbeResult(ok=False, latency_ms=999)

        atyp = header[3]
        if atyp == 0x01:
            await asyncio.wait_for(reader.readexactly(4), timeout=timeout_s)
        elif atyp == 0x03:
            ln = await asyncio.wait_for(reader.readexactly(1), timeout=timeout_s)
            await asyncio.wait_for(reader.readexactly(ln[0]), timeout=timeout_s)
        elif atyp == 0x04:
            await asyncio.wait_for(reader.readexactly(16), timeout=timeout_s)
        await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)

        mode = _env_str("TEST_TARGET_MODE", "auto").strip().lower()
        if mode not in {"auto", "tcp", "http"}:
            mode = "auto"
        if mode == "auto":
            mode = "tcp" if int(target_port) in {443, 8443} else "http"
        if mode == "tcp":
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ProbeResult(ok=True, latency_ms=latency_ms)

        safe_host = target_host.encode("idna").decode("ascii", errors="ignore")
        safe_path = _normalize_path(target_path)
        request = (
            f"HEAD {safe_path} HTTP/1.1\r\nHost: {safe_host}\r\nConnection: close\r\n\r\n"
        )
        writer.write(request.encode("ascii", errors="ignore"))
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        ok = line.startswith(b"HTTP/")
        latency_ms = int((time.perf_counter() - start) * 1000) if ok else 999
        return ProbeResult(ok=ok, latency_ms=latency_ms)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


async def _terminate_process(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    with contextlib.suppress(Exception):
        proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=2.0)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(proc.wait(), timeout=1.0)


async def _test_with_core(
    config: ParsedConfig,
    *,
    timeout_s: float,
    core_path: str,
    target_host: str,
    target_port: int,
    target_path: str,
) -> ProbeResult:
    outbound = _build_xray_outbound(config)
    if outbound is None:
        return ProbeResult(ok=False, latency_ms=999)

    async with _core_semaphore():
        port = _reserve_port()
        config_data = _build_xray_config(outbound=outbound, inbound_port=port)
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            with open(config_path, "w", encoding="utf-8") as handle:
                json.dump(config_data, handle, ensure_ascii=True)

            startup_timeout = max(0.5, _env_float("CORE_STARTUP_TIMEOUT_SECONDS", 1.5))
            proc = await _start_core_process(
                core_path=core_path,
                config_path=config_path,
                inbound_port=port,
                startup_timeout_s=startup_timeout,
            )
            if proc is None:
                return ProbeResult(ok=False, latency_ms=999)
            try:
                return await _socks_http_probe(
                    host="127.0.0.1",
                    port=port,
                    target_host=target_host,
                    target_port=target_port,
                    target_path=target_path,
                    timeout_s=timeout_s,
                )
            finally:
                await _terminate_process(proc)


def _should_use_core_for_config(config: ParsedConfig) -> bool:
    protocol = (config.protocol or "").strip().lower()
    # Prefer core-based testing whenever possible to match v2rayN behavior and
    # reduce false positives from lightweight handshakes.
    return protocol in {"vless", "trojan", "vmess"}


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


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: Pure TCP/TLS Connection Test
# ═══════════════════════════════════════════════════════════════════════════
async def _test1_tcp_connect(
    host: str, port: int, ssl_ctx: ssl.SSLContext | None, 
    server_hostname: str | None, timeout_s: float
) -> ProbeResult:
    """Test 1: Basic TCP/TLS handshake - just connect and disconnect"""
    start = time.perf_counter()
    writer = None
    try:
        reader, writer = await _open_stream(
            host, port, ssl_ctx=ssl_ctx, server_hostname=server_hostname, timeout_s=timeout_s
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(ok=True, latency_ms=latency_ms)
    except Exception as e:
        logger.debug(f"Test1 TCP failed for {host}:{port}: {e}")
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: HTTP HEAD Request (fast, minimal data)
# ═══════════════════════════════════════════════════════════════════════════
async def _test2_http_head(
    host: str, port: int, host_header: str,
    ssl_ctx: ssl.SSLContext | None, server_hostname: str | None, timeout_s: float
) -> ProbeResult:
    """Test 2: HTTP HEAD request - check if server responds to HTTP"""
    start = time.perf_counter()
    writer = None
    try:
        reader, writer = await _open_stream(
            host, port, ssl_ctx=ssl_ctx, server_hostname=server_hostname, timeout_s=timeout_s
        )
        req = f"HEAD / HTTP/1.1\r\nHost: {host_header}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode())
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
        ok = line.startswith(b"HTTP/")
        latency_ms = int((time.perf_counter() - start) * 1000) if ok else 999
        return ProbeResult(ok=ok, latency_ms=latency_ms)
    except Exception as e:
        logger.debug(f"Test2 HTTP HEAD failed for {host}:{port}: {e}")
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


def _ws_masked_frame(payload: bytes, *, opcode: int = 0x2) -> bytes:
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    first = 0x80 | (opcode & 0x0F)
    length = len(payload)
    if length < 126:
        header = bytes([first, 0x80 | length])
    elif length <= 0xFFFF:
        header = bytes([first, 0x80 | 126]) + length.to_bytes(2, "big")
    else:
        header = bytes([first, 0x80 | 127]) + length.to_bytes(8, "big")
    return header + mask + masked


async def _ws_read_frame(reader: asyncio.StreamReader, *, timeout_s: float) -> tuple[int, bytes] | None:
    head = await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)
    b1, b2 = head[0], head[1]
    opcode = b1 & 0x0F
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F
    if length == 126:
        ext = await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)
        length = int.from_bytes(ext, "big")
    elif length == 127:
        ext = await asyncio.wait_for(reader.readexactly(8), timeout=timeout_s)
        length = int.from_bytes(ext, "big")
    if masked:
        mask = await asyncio.wait_for(reader.readexactly(4), timeout=timeout_s)
        payload = await asyncio.wait_for(reader.readexactly(length), timeout=timeout_s)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload
    payload = await asyncio.wait_for(reader.readexactly(length), timeout=timeout_s) if length else b""
    return opcode, payload


def _vless_request_header(uuid_text: str, *, dest_host: str, dest_port: int) -> bytes:
    try:
        import uuid as _uuid_mod

        user_id = _uuid_mod.UUID(uuid_text.strip())
        user_bytes = user_id.bytes
    except Exception:
        return b""

    host = (dest_host or "").strip()
    if not host:
        return b""

    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        atyp = 1
        addr = bytes(int(p) for p in parts)
    else:
        atyp = 2
        raw = host.encode("utf-8", errors="ignore")
        addr = bytes([len(raw)]) + raw

    return (
        b"\x01"  # version
        + user_bytes
        + b"\x00"  # opt len
        + b"\x01"  # command TCP
        + int(dest_port).to_bytes(2, "big")
        + bytes([atyp])
        + addr
    )


def _trojan_handshake(password: str) -> bytes:
    pw = (password or "").strip().encode("utf-8", errors="ignore")
    if not pw:
        return b""
    return hashlib.sha224(pw).hexdigest().encode("ascii") + b"\r\n"


async def _proxy_http_over_vless_tcp(
    *,
    host: str,
    port: int,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    uuid_text: str,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    writer: asyncio.StreamWriter | None = None
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        header = _vless_request_header(uuid_text, dest_host="1.1.1.1", dest_port=80)
        if not header:
            return ProbeResult(ok=False, latency_ms=999)
        writer.write(header + _trace_request_bytes())
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        # VLESS response starts with: version (1 byte), opt_len (1 byte), opt (opt_len bytes), then payload.
        prefix = await asyncio.wait_for(reader.readexactly(2), timeout=timeout_s)
        opt_len = int(prefix[1])
        if opt_len:
            await asyncio.wait_for(reader.readexactly(opt_len), timeout=timeout_s)
        data = await asyncio.wait_for(reader.read(2048), timeout=timeout_s)
        ok = _trace_response_ok(data)
        latency_ms = int((time.perf_counter() - start) * 1000) if ok else 999
        return ProbeResult(ok=ok, latency_ms=latency_ms)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


async def _proxy_http_over_trojan_tcp(
    *,
    host: str,
    port: int,
    ssl_ctx: ssl.SSLContext | None,
    server_hostname: str | None,
    password: str,
    timeout_s: float,
) -> ProbeResult:
    start = time.perf_counter()
    writer: asyncio.StreamWriter | None = None
    try:
        reader, writer = await _open_stream(
            host,
            port,
            ssl_ctx=ssl_ctx,
            server_hostname=server_hostname,
            timeout_s=timeout_s,
        )
        hs = _trojan_handshake(password)
        if not hs:
            return ProbeResult(ok=False, latency_ms=999)
        req = (
            hs
            + b"\x01"  # CMD_CONNECT
            + b"\x01"  # ATYP IPv4
            + b"\x01\x01\x01\x01"  # 1.1.1.1
            + int(80).to_bytes(2, "big")
            + b"\r\n"
        )
        writer.write(req)
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        writer.write(_trace_request_bytes())
        await asyncio.wait_for(writer.drain(), timeout=timeout_s)
        data = await asyncio.wait_for(reader.read(2048), timeout=timeout_s)
        ok = _trace_response_ok(data)
        latency_ms = int((time.perf_counter() - start) * 1000) if ok else 999
        return ProbeResult(ok=ok, latency_ms=latency_ms)
    except Exception:
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: Protocol-Specific Test (WebSocket / gRPC / HTTP GET with path)
# ═══════════════════════════════════════════════════════════════════════════
async def _test3_protocol_specific(
    host: str,
    port: int,
    path: str,
    host_header: str,
    transport: str,
    protocol: str,
    user: str,
    ssl_ctx: ssl.SSLContext | None, server_hostname: str | None, timeout_s: float
) -> ProbeResult:
    """Test 3: Protocol-specific test based on transport type"""
    start = time.perf_counter()
    writer = None
    
    try:
        reader, writer = await _open_stream(
            host, port, ssl_ctx=ssl_ctx, server_hostname=server_hostname, timeout_s=timeout_s
        )
        
        if transport in {"ws", "websocket"}:
            # WebSocket handshake
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host_header}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            writer.write(req.encode())
            await asyncio.wait_for(writer.drain(), timeout=timeout_s)
            status_line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
            ok = False
            if status_line.startswith(b"HTTP/"):
                parts = status_line.split()
                if len(parts) >= 2:
                    with contextlib.suppress(Exception):
                        ok = int(parts[1]) == 101

            headers: dict[bytes, bytes] = {}
            if ok:
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout=timeout_s)
                    if line in (b"\r\n", b"\n", b""):
                        break
                    if b":" in line:
                        k, v = line.split(b":", 1)
                        headers[k.strip().lower()] = v.strip().lower()
                ok = headers.get(b"upgrade") == b"websocket" and b"upgrade" in headers.get(
                    b"connection", b""
                )

            # For VLESS over WS, do a real proxy HEAD request via VLESS header inside WS frames.
            if ok and protocol == "vless" and user:
                vless = _vless_request_header(user, dest_host="1.1.1.1", dest_port=80)
                if not vless:
                    ok = False
                else:
                    payload = vless + _trace_request_bytes()
                    writer.write(_ws_masked_frame(payload, opcode=0x2))
                    await asyncio.wait_for(writer.drain(), timeout=timeout_s)

                    deadline = time.perf_counter() + min(timeout_s, 2.0)
                    buf = b""
                    ok = False
                    while time.perf_counter() < deadline and len(buf) < 2048:
                        remaining = max(0.05, deadline - time.perf_counter())
                        frame = await _ws_read_frame(reader, timeout_s=remaining)
                        if frame is None:
                            break
                        opcode, data = frame
                        if opcode == 0x8:  # close
                            break
                        if opcode in (0x9, 0xA):  # ping/pong
                            continue
                        if opcode in (0x0, 0x1, 0x2):  # cont/text/binary
                            buf += data
                            if len(buf) >= 2:
                                opt_len = int(buf[1])
                                if len(buf) >= 2 + opt_len:
                                    body = buf[2 + opt_len :]
                                    if _trace_response_ok(body):
                                        ok = True
                                        break

            # For Trojan over WS, do a real proxy HEAD request via Trojan CONNECT inside WS frames.
            if ok and protocol == "trojan" and user:
                hs = _trojan_handshake(user)
                if not hs:
                    ok = False
                else:
                    connect = (
                        hs
                        + b"\x01"  # CMD_CONNECT
                        + b"\x01"  # ATYP IPv4
                        + b"\x01\x01\x01\x01"  # 1.1.1.1
                        + int(80).to_bytes(2, "big")
                        + b"\r\n"
                    )
                    payload = connect + _trace_request_bytes()
                    writer.write(_ws_masked_frame(payload, opcode=0x2))
                    await asyncio.wait_for(writer.drain(), timeout=timeout_s)

                    deadline = time.perf_counter() + min(timeout_s, 2.0)
                    buf = b""
                    ok = False
                    while time.perf_counter() < deadline and len(buf) < 2048:
                        remaining = max(0.05, deadline - time.perf_counter())
                        frame = await _ws_read_frame(reader, timeout_s=remaining)
                        if frame is None:
                            break
                        opcode, data = frame
                        if opcode == 0x8:  # close
                            break
                        if opcode in (0x9, 0xA):  # ping/pong
                            continue
                        if opcode in (0x0, 0x1, 0x2):  # cont/text/binary
                            buf += data
                            if _trace_response_ok(buf):
                                ok = True
                                break
             
        elif transport in {"grpc", "h2", "http2"}:
            # HTTP/2 preface
            h2_preface = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
            h2_settings = b"\x00\x00\x00\x04\x00\x00\x00\x00\x00"
            writer.write(h2_preface + h2_settings)
            await asyncio.wait_for(writer.drain(), timeout=timeout_s)
            header = await asyncio.wait_for(reader.readexactly(9), timeout=timeout_s)
            if header.startswith(b"HTTP/"):
                ok = False
            else:
                length = int.from_bytes(header[:3], "big")
                frame_type = header[3]
                stream_id = int.from_bytes(header[5:9], "big") & 0x7FFFFFFF
                ok = frame_type == 0x4 and stream_id == 0
                if ok and length:
                    await asyncio.wait_for(reader.readexactly(min(length, 1024)), timeout=timeout_s)
             
        else:
            # Plain TCP without protocol-level validation is too noisy; treat as failed.
            ok = False
         
        latency_ms = int((time.perf_counter() - start) * 1000) if ok else 999
        return ProbeResult(ok=ok, latency_ms=latency_ms)
        
    except Exception as e:
        logger.debug(f"Test3 Protocol failed for {host}:{port}: {e}")
        return ProbeResult(ok=False, latency_ms=999)
    finally:
        if writer:
            with contextlib.suppress(Exception):
                writer.close()
                await writer.wait_closed()


async def test_server(
    config: ParsedConfig, *, timeout_s: float, max_latency_ms: int
) -> dict[str, object]:
    """
    Test a server with protocol-aware probes to balance speed and accuracy.

    - WS/GRPC/H2: protocol-specific handshake
    - VLESS/Trojan TCP: proxy HTTP via protocol header
    - Fallback TCP: TCP connect + HTTP HEAD
    """
    host = config.add
    port = int(config.port)
    transport = (config.transport or "tcp").strip().lower()
    protocol = (config.protocol or "").strip().lower()
    if transport == "websocket":
        transport = "ws"

    core_mode = _core_test_mode()
    core_path = _resolve_core_path()
    # Prefer a highly reachable endpoint for Iran and global networks.
    target_host = _env_str("TEST_TARGET_HOST", "one.one.one.one")
    target_port = _env_int("TEST_TARGET_PORT", 80)
    target_path = _env_str("TEST_TARGET_PATH", "/")

    use_core = False
    if core_path and core_mode != "light":
        if core_mode == "core":
            use_core = True
        else:
            use_core = _should_use_core_for_config(config)

    if use_core:
        core_result = await _test_with_core(
            config,
            timeout_s=timeout_s,
            core_path=core_path,
            target_host=target_host,
            target_port=target_port,
            target_path=target_path,
        )
        best_latency = int(core_result.latency_ms or 999)
        is_active = bool(core_result.ok)
        if is_active:
            return {
                "latency": best_latency,
                "status": "active",
                "scanned": True,
                "reachable": True,
                "test_mode": "core",
            }
        return {
            "latency": best_latency,
            "status": "timeout",
            "scanned": True,
            "reachable": core_result.ok,
            "test_mode": "core",
        }

    use_ssl = _tls_expected(config)
    ssl_ctx = _UNVERIFIED_SSL_CONTEXT if use_ssl else None
    host_header = (config.host or config.sni or config.add).strip() or config.add
    server_hostname = (config.sni or config.host or config.add).strip() if use_ssl else None
    path = _normalize_path(config.path)
    user = (getattr(config, "user", "") or "").strip()

    is_tcp = transport in {"", "tcp"}
    is_ws = transport in {"ws"}
    is_h2 = transport in {"grpc", "h2", "http2"}

    async def run_tcp():
        try:
            return await _test1_tcp_connect(host, port, ssl_ctx, server_hostname, timeout_s)
        except Exception:
            return ProbeResult(ok=False, latency_ms=999)

    async def run_http():
        # HTTP HEAD creates false-positives for TCP VLESS/Trojan and is redundant for WS/GRPC.
        if is_ws or is_h2:
            return ProbeResult(ok=False, latency_ms=999)
        if protocol in {"vless", "trojan"} and is_tcp:
            return ProbeResult(ok=False, latency_ms=999)
        try:
            return await _test2_http_head(host, port, host_header, ssl_ctx, server_hostname, timeout_s)
        except Exception:
            return ProbeResult(ok=False, latency_ms=999)

    async def run_protocol():
        # For TCP VLESS/Trojan, do a real proxy check instead of generic test3.
        if protocol in {"vless", "trojan"} and is_tcp and not user:
            return ProbeResult(ok=False, latency_ms=999)
        if protocol == "vless" and is_tcp and user:
            return await _proxy_http_over_vless_tcp(
                host=host,
                port=port,
                ssl_ctx=ssl_ctx,
                server_hostname=server_hostname,
                uuid_text=user,
                timeout_s=timeout_s,
            )
        if protocol == "trojan" and is_tcp and user:
            return await _proxy_http_over_trojan_tcp(
                host=host,
                port=port,
                ssl_ctx=ssl_ctx,
                server_hostname=server_hostname,
                password=user,
                timeout_s=timeout_s,
            )
        # In light-mode, VMess over WS is too noisy (handshake-only false positives).
        # Keep it disabled unless core mode is available.
        if is_ws and protocol == "vmess":
            return ProbeResult(ok=False, latency_ms=999)
        if is_h2:
            return ProbeResult(ok=False, latency_ms=999)
        try:
            return await _test3_protocol_specific(
                host,
                port,
                path,
                host_header,
                transport,
                protocol,
                user,
                ssl_ctx,
                server_hostname,
                timeout_s,
            )
        except Exception:
            return ProbeResult(ok=False, latency_ms=999)

    # Choose minimal probe set for speed while keeping accuracy.
    if (protocol in {"vless", "trojan"} and is_tcp) or is_ws or is_h2:
        probes = [run_protocol]
        require_all = True
    elif protocol == "vmess" and is_tcp:
        probes = [run_tcp]
        require_all = True
    else:
        probes = [run_tcp, run_http]
        require_all = False

    results = await asyncio.gather(*(p() for p in probes), return_exceptions=True)

    def get_result(res):
        if isinstance(res, ProbeResult):
            return res
        return ProbeResult(ok=False, latency_ms=999)

    probe_results = [get_result(r) for r in results]
    ok_results = [r for r in probe_results if r.ok]
    best_latency = min((r.latency_ms for r in ok_results), default=999)

    if require_all:
        is_active = bool(probe_results) and all(r.ok for r in probe_results)
    else:
        is_active = bool(ok_results)

    if is_active:
        return {
            "latency": best_latency,
            "status": "active",
            "scanned": True,
            "reachable": True,
            "test_mode": "light",
        }
    else:
        return {
            "latency": best_latency,
            "status": "timeout",
            "scanned": True,
            "reachable": any(r.ok for r in probe_results),
            "test_mode": "light",
        }
