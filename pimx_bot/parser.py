from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


def _safe_b64decode(value: str) -> str:
    try:
        value = value.strip()
        value += "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value.encode("utf-8")).decode("utf-8", errors="ignore")
    except Exception:
        return ""


@dataclass(slots=True)
class ParsedConfig:
    original_string: str
    protocol: str
    transport: str
    ps: str
    add: str
    port: int
    host: str
    path: str
    tls: str
    source_id: int | None = None


def parse_server_configs(content: str, *, source_id: int | None = None) -> list[ParsedConfig]:
    raw = (content or "").strip()
    if not raw:
        return []

    if "://" not in raw:
        decoded = _safe_b64decode(raw)
        if decoded and "://" in decoded:
            raw = decoded

    lines = raw.split()
    configs: list[ParsedConfig] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("vmess://"):
            parsed = _parse_vmess(line, source_id=source_id)
            if parsed:
                configs.append(parsed)
            continue

        if line.startswith("vless://"):
            parsed = _parse_url_config(line, protocol="vless", default_port=443, source_id=source_id)
            if parsed:
                configs.append(parsed)
            continue

        if line.startswith("trojan://"):
            parsed = _parse_url_config(line, protocol="trojan", default_port=443, source_id=source_id)
            if parsed:
                configs.append(parsed)
            continue

    unique: dict[str, ParsedConfig] = {}
    for c in configs:
        unique.setdefault(c.original_string, c)
    return list(unique.values())


def _parse_vmess(line: str, *, source_id: int | None) -> ParsedConfig | None:
    b64 = line[len("vmess://") :]
    payload = _safe_b64decode(b64)
    if not payload:
        return None
    try:
        data: dict[str, Any] = json.loads(payload)
    except Exception:
        return None

    add = str(data.get("add") or "").strip()
    port = int(str(data.get("port") or "0") or "0")
    if not add or add == "unknown" or port <= 0 or port >= 65536:
        return None

    return ParsedConfig(
        original_string=line,
        protocol="vmess",
        transport=str(data.get("net") or "tcp"),
        ps=str(data.get("ps") or "vmess-node"),
        add=add,
        port=port,
        host=str(data.get("host") or ""),
        path=str(data.get("path") or ""),
        tls=str(data.get("tls") or ""),
        source_id=source_id,
    )


def _parse_url_config(
    line: str, *, protocol: str, default_port: int, source_id: int | None
) -> ParsedConfig | None:
    try:
        parsed = urlparse(line)
    except Exception:
        return None

    hostname = (parsed.hostname or "").strip()
    if not hostname or hostname == "unknown":
        return None

    port = parsed.port or default_port
    qs = parse_qs(parsed.query)

    transport = (qs.get("type", [None])[0] or qs.get("net", [None])[0] or "tcp").strip()
    tls = (qs.get("security", [None])[0] or "").strip()
    host = (qs.get("host", [None])[0] or qs.get("sni", [None])[0] or "").strip()
    path = (qs.get("path", [None])[0] or qs.get("serviceName", [None])[0] or "").strip()

    name = ""
    if parsed.fragment:
        try:
            name = unquote(parsed.fragment)
        except Exception:
            name = parsed.fragment
    if not name:
        name = f"{protocol}-node"

    return ParsedConfig(
        original_string=line,
        protocol=protocol,
        transport=transport,
        ps=name,
        add=hostname,
        port=int(port),
        host=host,
        path=path,
        tls=tls,
        source_id=source_id,
    )
