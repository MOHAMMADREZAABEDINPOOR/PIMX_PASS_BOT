from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


@dataclass(frozen=True, slots=True)
class ParsedConfig:
    original_string: str
    protocol: str
    transport: str
    tls: str
    ps: str
    add: str
    port: int
    host: str
    path: str
    user: str = ""
    source_id: int | None = None
    sni: str = ""
    alpn: str = ""
    fp: str = ""
    pbk: str = ""
    sid: str = ""
    spx: str = ""
    flow: str = ""
    vmess_aid: int = 0
    vmess_security: str = ""


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


def _qs_first(qs: dict[str, list[str]], key: str) -> str:
    values = qs.get(key)
    if not values:
        return ""
    return str(values[0] or "")


def parse_server_configs(content: str, *, source_id: int | None = None) -> list[ParsedConfig]:
    raw = (content or "").strip()
    if not raw:
        return []

    # Many subscription URLs return base64 of newline-separated configs.
    if "://" not in raw:
        decoded = _safe_b64decode_to_text(raw)
        if decoded and "://" in decoded:
            raw = decoded

    configs: list[ParsedConfig] = []
    for token in raw.split():
        line = token.strip()
        if not line:
            continue

        if line.startswith("vmess://"):
            decoded_json = _safe_b64decode_to_text(line[len("vmess://") :])
            if not decoded_json:
                continue
            try:
                data: dict[str, Any] = json.loads(decoded_json)
            except Exception:
                continue

            add = str(data.get("add") or "").strip()
            if not add or add.lower() == "unknown":
                continue

            try:
                port = int(data.get("port") or 0)
            except Exception:
                continue
            if port <= 0:
                continue

            configs.append(
                ParsedConfig(
                    original_string=line,
                    protocol="vmess",
                    transport=str(data.get("net") or "tcp"),
                    tls=str(data.get("tls") or ""),
                    ps=str(data.get("ps") or "vmess-node"),
                    add=add,
                    port=port,
                    host=str(data.get("host") or ""),
                    path=str(data.get("path") or ""),
                    user=str(data.get("id") or ""),
                    sni=str(data.get("sni") or ""),
                    alpn=",".join(str(v) for v in (data.get("alpn") or []) if v)
                    if isinstance(data.get("alpn"), list)
                    else str(data.get("alpn") or ""),
                    vmess_aid=int(data.get("aid") or data.get("alterId") or 0)
                    if str(data.get("aid") or data.get("alterId") or "0").isdigit()
                    else 0,
                    vmess_security=str(data.get("scy") or data.get("security") or ""),
                    source_id=source_id,
                )
            )
            continue

        if line.startswith("vless://") or line.startswith("trojan://"):
            try:
                parsed = urlparse(line)
            except Exception:
                continue

            add = (parsed.hostname or "").strip()
            if not add or add.lower() == "unknown":
                continue

            try:
                port = int(parsed.port or 443)
            except Exception:
                port = 443

            qs = parse_qs(parsed.query or "", keep_blank_values=True)
            transport = _qs_first(qs, "type") or _qs_first(qs, "net") or "tcp"
            user = (parsed.username or "").strip()
            # VLESS/Trojan links without user-id/password are not importable in clients like v2rayN.
            if not user:
                continue
            ps = unquote(parsed.fragment[1:] if parsed.fragment.startswith("#") else parsed.fragment) if parsed.fragment else ""
            if not ps:
                ps = "vless-node" if line.startswith("vless://") else "trojan-node"

            host = _qs_first(qs, "host")
            sni = _qs_first(qs, "sni") or host
            path = _qs_first(qs, "path") or _qs_first(qs, "serviceName")
            tls = _qs_first(qs, "security")
            alpn = _qs_first(qs, "alpn")
            fp = _qs_first(qs, "fp")
            pbk = _qs_first(qs, "pbk") or _qs_first(qs, "publicKey")
            sid = _qs_first(qs, "sid") or _qs_first(qs, "shortId")
            spx = _qs_first(qs, "spx") or _qs_first(qs, "spiderX")
            flow = _qs_first(qs, "flow")

            configs.append(
                ParsedConfig(
                    original_string=line,
                    protocol="vless" if line.startswith("vless://") else "trojan",
                    transport=transport,
                    tls=tls,
                    ps=ps,
                    add=add,
                    port=port,
                    host=host,
                    path=path,
                    user=user,
                    sni=sni,
                    alpn=alpn,
                    fp=fp,
                    pbk=pbk,
                    sid=sid,
                    spx=spx,
                    flow=flow,
                    source_id=source_id,
                )
            )
            continue

    return configs
