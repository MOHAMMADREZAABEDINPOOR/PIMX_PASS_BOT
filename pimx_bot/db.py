from __future__ import annotations

import json
import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


DEFAULT_SOURCES = [


    "https://raw.githubusercontent.com/MrAbolfazlNorouzi/iran-configs/refs/heads/main/configs/working-configs.txt",
    "https://raw.githubusercontent.com/Arianlavi/RebeldevConfig/refs/heads/main/RebelLink/trojan_subscriptions.txt",
    "https://raw.githubusercontent.com/nyeinkokoaung404/V2ray-Configs/refs/heads/main/Sub2.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no4.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no3.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no8.txt",
    "https://raw.githubusercontent.com/Arianlavi/RebeldevConfig/refs/heads/main/RebelLink/vless_subscriptions.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no1.txt",
    "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/V2RAY_SUB/refs/heads/main/v2ray_configs_no6.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/Sub25.txt",
    "https://raw.githubusercontent.com/Danialsamadi/v2go/refs/heads/main/Sub21.txt",
    "https://raw.githubusercontent.com/nyeinkokoaung404/V2ray-Configs/refs/heads/main/Sub1.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/refs/heads/main/configs/us/all.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/refs/heads/main/configs/ua/all.txt",
]


@dataclass(frozen=True, slots=True)
class ListedServer:
    id: int
    name: str
    latency: int | None
    country: str | None
    config_string: str
    copy_config: str | None = None


async def connect(db_path: str) -> aiosqlite.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA synchronous = NORMAL")
    await db.execute("PRAGMA busy_timeout = 5000")
    return db


async def fetchone(db: aiosqlite.Connection, query: str, params: tuple[object, ...] = ()) -> aiosqlite.Row | None:
    async with db.execute(query, params) as cursor:
        return await cursor.fetchone()


async def fetchall(db: aiosqlite.Connection, query: str, params: tuple[object, ...] = ()) -> list[aiosqlite.Row]:
    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        return list(rows)


async def init_db(db: aiosqlite.Connection) -> None:
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          url TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,
          active BOOLEAN DEFAULT 1,
          last_scan DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

	        CREATE TABLE IF NOT EXISTS servers (
	          id INTEGER PRIMARY KEY AUTOINCREMENT,
	          config_string TEXT UNIQUE NOT NULL,
	          copy_config TEXT,
	          protocol TEXT NOT NULL,
	          transport TEXT,
	          tls TEXT,
	          name TEXT NOT NULL,
	          address TEXT NOT NULL,
          port INTEGER NOT NULL,
          host TEXT,
          path TEXT,
          country TEXT,
          latency INTEGER,
          status TEXT DEFAULT 'pending',
          operators TEXT,
          packet_loss REAL,
          speed REAL,
          quality_score INTEGER DEFAULT 0,
          reachable BOOLEAN DEFAULT 0,
          scanned BOOLEAN DEFAULT 0,
          source_id INTEGER,
          is_selected BOOLEAN DEFAULT 0,
          dislikes INTEGER DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (source_id) REFERENCES sources (id)
        );

        CREATE INDEX IF NOT EXISTS idx_servers_selected_active
          ON servers(is_selected, status, latency);

        CREATE TABLE IF NOT EXISTS stats (
          id INTEGER PRIMARY KEY,
          total_scanned INTEGER DEFAULT 0,
          total_active INTEGER DEFAULT 0,
          total_selected INTEGER DEFAULT 0,
          total_dislikes INTEGER DEFAULT 0,
          last_scan DATETIME,
          scan_completed_at DATETIME,
          next_scan_at DATETIME,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
          user_id INTEGER PRIMARY KEY,
          chat_id INTEGER NOT NULL,
          username TEXT,
          first_name TEXT,
          last_name TEXT,
          language_code TEXT,
          is_premium BOOLEAN DEFAULT 0,
          is_bot BOOLEAN DEFAULT 0,
          bio TEXT,
          photo_file_id TEXT,
          first_seen_at INTEGER NOT NULL,
          last_seen_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bot_sessions (
          chat_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          message_id INTEGER NOT NULL,
          page INTEGER NOT NULL DEFAULT 0,
          last_hash TEXT,
          last_interaction_at INTEGER NOT NULL,
          PRIMARY KEY (chat_id, message_id)
        );
        """
    )
    await db.execute("INSERT OR IGNORE INTO stats (id) VALUES (1)")
    with contextlib.suppress(aiosqlite.OperationalError):
        await db.execute("ALTER TABLE users ADD COLUMN usage_count INTEGER DEFAULT 0")
    with contextlib.suppress(aiosqlite.OperationalError):
        await db.execute("ALTER TABLE stats ADD COLUMN last_cleanup_at DATETIME")
    with contextlib.suppress(aiosqlite.OperationalError):
        await db.execute("ALTER TABLE servers ADD COLUMN copy_config TEXT")

    for idx, url in enumerate(DEFAULT_SOURCES, start=1):
        await db.execute(
            "INSERT OR IGNORE INTO sources (url, name) VALUES (?, ?)",
            (url, f"Source {idx}"),
        )
    await db.commit()


async def get_known_config_strings(db: aiosqlite.Connection) -> set[str]:
    rows = await fetchall(db, "SELECT config_string FROM servers")
    return {str(r["config_string"]) for r in rows if r and r["config_string"]}


async def get_recent_config_strings(db: aiosqlite.Connection, *, window_seconds: int) -> set[str]:
    seconds = max(0, int(window_seconds))
    rows = await fetchall(
        db,
        "SELECT config_string FROM servers WHERE updated_at >= datetime('now', ?)",
        (f"-{seconds} seconds",),
    )
    return {str(r["config_string"]) for r in rows if r and r["config_string"]}


async def get_active_sources(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await fetchall(db, "SELECT * FROM sources WHERE active = 1")
    return [dict(r) for r in rows]


async def upsert_server(db: aiosqlite.Connection, server: dict[str, Any]) -> None:
    await db.execute(
        """
        INSERT INTO servers (
          config_string, copy_config, protocol, transport, tls, name, address, port, host, path, country,
          latency, status, operators, packet_loss, speed, quality_score, reachable, scanned, source_id,
          is_selected, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(config_string) DO UPDATE SET
          copy_config = excluded.copy_config,
          protocol = excluded.protocol,
          transport = excluded.transport,
          tls = excluded.tls,
          name = excluded.name,
          address = excluded.address,
          port = excluded.port,
          host = excluded.host,
          path = excluded.path,
          country = excluded.country,
          latency = excluded.latency,
          status = excluded.status,
          operators = excluded.operators,
          packet_loss = excluded.packet_loss,
          speed = excluded.speed,
          quality_score = excluded.quality_score,
          reachable = excluded.reachable,
          scanned = excluded.scanned,
          source_id = excluded.source_id,
          is_selected = excluded.is_selected,
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            server["config_string"],
            server.get("copy_config"),
            server["protocol"],
            server.get("transport") or "tcp",
            server.get("tls") or "",
            server.get("name") or "Unnamed",
            server["address"],
            int(server["port"]),
            server.get("host") or server["address"],
            server.get("path") or "/",
            server.get("country") or "Unknown",
            server.get("latency"),
            server.get("status") or "pending",
            json.dumps(server.get("operators") or {}),
            server.get("packet_loss") or 0,
            server.get("speed") or 0,
            int(server.get("quality_score") or 0),
            1 if server.get("reachable") else 0,
            1 if server.get("scanned") else 0,
            server.get("source_id"),
            1 if server.get("is_selected") else 0,
        ),
    )


async def upsert_user(db: aiosqlite.Connection, user: dict[str, Any]) -> None:
    await db.execute(
        """
        INSERT INTO users (
          user_id, chat_id, username, first_name, last_name, language_code, is_premium,
          is_bot, bio, photo_file_id, first_seen_at, last_seen_at, usage_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          chat_id = excluded.chat_id,
          username = excluded.username,
          first_name = excluded.first_name,
          last_name = excluded.last_name,
          language_code = excluded.language_code,
          is_premium = excluded.is_premium,
          is_bot = excluded.is_bot,
          bio = COALESCE(excluded.bio, users.bio),
          photo_file_id = COALESCE(excluded.photo_file_id, users.photo_file_id),
          last_seen_at = excluded.last_seen_at,
          usage_count = users.usage_count + 1
        """,
        (
            int(user["user_id"]),
            int(user["chat_id"]),
            user.get("username"),
            user.get("first_name"),
            user.get("last_name"),
            user.get("language_code"),
            1 if user.get("is_premium") else 0,
            1 if user.get("is_bot") else 0,
            user.get("bio"),
            user.get("photo_file_id"),
            int(user["first_seen_at"]),
            int(user["last_seen_at"]),
            1,
        ),
    )
    await db.commit()


async def count_users_since(db: aiosqlite.Connection, *, since_ts: int) -> int:
    row = await fetchone(
        db,
        "SELECT COUNT(*) as cnt FROM users WHERE last_seen_at >= ?",
        (int(since_ts),),
    )
    return int(row["cnt"] if row else 0)


async def count_users_total(db: aiosqlite.Connection) -> int:
    row = await fetchone(db, "SELECT COUNT(*) as cnt FROM users")
    return int(row["cnt"] if row else 0)


async def list_users(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await fetchall(
        db,
        """
        SELECT user_id, chat_id, username, first_name, last_name, language_code,
               is_premium, is_bot, bio, photo_file_id, first_seen_at, last_seen_at,
               usage_count
        FROM users
        ORDER BY last_seen_at DESC
        """,
    )
    return [dict(r) for r in rows]


async def count_selected_active(db: aiosqlite.Connection) -> int:
    row = await fetchone(
        db,
        'SELECT COUNT(*) as cnt FROM servers WHERE is_selected = 1 AND status = "active"'
    )
    return int(row["cnt"] if row else 0)


async def count_active(db: aiosqlite.Connection) -> int:
    row = await fetchone(db, 'SELECT COUNT(*) as cnt FROM servers WHERE status = "active"')
    return int(row["cnt"] if row else 0)


async def count_total(db: aiosqlite.Connection) -> int:
    row = await fetchone(db, "SELECT COUNT(*) as cnt FROM servers")
    return int(row["cnt"] if row else 0)

async def get_active_servers_page(
    db: aiosqlite.Connection,
    *,
    offset: int,
    limit: int,
    max_config_len: int | None = None,
    max_latency_ms: int = 250,
    ) -> list[ListedServer]:
    max_len_sql = ""
    params: tuple[object, ...]
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_latency_ms), int(max_config_len), limit, offset)    
    else:
        params = (int(max_latency_ms), limit, offset)
    rows = await fetchall(
        db,
        f"""
        SELECT id, name, latency, country, config_string, copy_config
        FROM servers
        WHERE status = "active"
          AND COALESCE(latency, 99999) <= ?{max_len_sql}
          AND COALESCE(copy_config, '') != ''
        ORDER BY COALESCE(latency, 99999) ASC, updated_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    return [
        ListedServer(
            id=int(r["id"]),
            name=str(r["name"]),
            latency=r["latency"],
            country=str(r["country"]) if r["country"] is not None else None,
            config_string=str(r["config_string"]),
            copy_config=str(r["copy_config"]) if r["copy_config"] is not None else None,
        )
        for r in rows
    ]


async def get_active_servers_total(db: aiosqlite.Connection, *, max_latency_ms: int = 250) -> int:
    return await get_active_servers_total_with_max_len(
        db, max_config_len=None, max_latency_ms=max_latency_ms
    )


async def get_active_servers_total_with_max_len(
    db: aiosqlite.Connection, *, max_config_len: int | None, max_latency_ms: int = 250
) -> int:
    max_len_sql = ""
    params: tuple[object, ...]
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_latency_ms), int(max_config_len))
    else:
        params = (int(max_latency_ms),)
    row = await fetchone(
        db,
        f'SELECT COUNT(*) as cnt FROM servers WHERE status = "active" AND COALESCE(latency, 99999) <= ?{max_len_sql} AND COALESCE(copy_config, \"\") != \"\"',
        params,
    )
    return int(row["cnt"] if row else 0)


async def get_selected_servers_page(
    db: aiosqlite.Connection,
    *,
    offset: int,
    limit: int,
    max_config_len: int | None = None,
    max_latency_ms: int = 250,
) -> list[ListedServer]:
    max_len_sql = ""
    params: tuple[object, ...]
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_latency_ms), int(max_config_len), limit, offset)
    else:
        params = (int(max_latency_ms), limit, offset)
    rows = await fetchall(
        db,
        f"""
        SELECT id, name, latency, country, config_string, copy_config
        FROM servers
        WHERE status = "active"
          AND is_selected = 1
          AND scanned = 1
          AND COALESCE(latency, 99999) <= ?{max_len_sql}
          AND COALESCE(copy_config, '') != ''
        ORDER BY COALESCE(latency, 99999) ASC, updated_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    return [
        ListedServer(
            id=int(r["id"]),
            name=str(r["name"]),
            latency=r["latency"],
            country=str(r["country"]) if r["country"] is not None else None,
            config_string=str(r["config_string"]),
            copy_config=str(r["copy_config"]) if r["copy_config"] is not None else None,
        )
        for r in rows
    ]


async def get_selected_servers_total(db: aiosqlite.Connection, *, max_latency_ms: int = 250) -> int:
    return await get_selected_servers_total_with_max_len(
        db, max_config_len=None, max_latency_ms=max_latency_ms
    )

async def get_selected_servers_total(db: aiosqlite.Connection, *, max_latency_ms: int = 250) -> int:
    return await get_selected_servers_total_with_max_len(
        db, max_config_len=None, max_latency_ms=max_latency_ms
    )

async def get_selected_servers_total_with_max_len(
    db: aiosqlite.Connection, *, max_config_len: int | None, max_latency_ms: int = 250
) -> int:
    max_len_sql = ""
    params: tuple[object, ...]
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_latency_ms), int(max_config_len))
    else:
        params = (int(max_latency_ms),)
    row = await fetchone(
        db,
        f'SELECT COUNT(*) as cnt FROM servers WHERE status = "active" AND is_selected = 1 AND scanned = 1 AND COALESCE(latency, 99999) <= ?{max_len_sql} AND COALESCE(copy_config, \"\") != \"\"',
        params,
    )
    return int(row["cnt"] if row else 0)


async def get_server_config_string(db: aiosqlite.Connection, server_id: int) -> str | None:
    row = await fetchone(db, "SELECT config_string FROM servers WHERE id = ?", (server_id,))
    if not row:
        return None
    return str(row["config_string"])

async def cleanup_invalid_selected_servers(db: aiosqlite.Connection, *, max_latency_ms: int = 250) -> None:
    """Remove is_selected flag from servers that don't meet criteria.

    Note: latency is not a hard rule for selection; selection is based on fastest servers available.
    """
    await db.execute(
        """
        UPDATE servers
        SET is_selected = 0
        WHERE is_selected = 1 AND (
        status != "active" OR COALESCE(copy_config, '') = ''
        )
        """,
    )
    await db.commit()

async def manage_selected_servers(
    db: aiosqlite.Connection,
    *,
    min_selected: int,
    max_selected: int,
    max_latency_ms: int = 250,
) -> None:
    preferred_latency_ms = min(180, int(max_latency_ms))
    await cleanup_invalid_selected_servers(db, max_latency_ms=max_latency_ms)
    current_selected = await count_selected_active(db)
    if current_selected > max_selected:
        to_remove = current_selected - max_selected
        await db.execute(
            """
            UPDATE servers
            SET is_selected = 0
            WHERE id IN (
              SELECT id FROM servers
              WHERE is_selected = 1 AND status = "active"
              ORDER BY COALESCE(latency, 99999) DESC, dislikes DESC, updated_at ASC
              LIMIT ?
            )
            """,
            (to_remove,),
        )
        await db.commit()
        return

    if current_selected < min_selected:
        to_add = min_selected - current_selected

        # Prefer very low latency servers first to improve quality.
        await db.execute(
            """
            UPDATE servers
            SET is_selected = 1
            WHERE id IN (
              SELECT id FROM servers
              WHERE is_selected = 0 AND status = "active" AND COALESCE(latency, 99999) <= ?
              ORDER BY COALESCE(latency, 99999) ASC, dislikes ASC, updated_at DESC
              LIMIT ?
            )
            """,
            (preferred_latency_ms, to_add),
        )
        await db.commit()

        current_selected = await count_selected_active(db)
        if current_selected < min_selected:
            to_add = min_selected - current_selected
            await db.execute(
                """
                UPDATE servers
                SET is_selected = 1
                WHERE id IN (
                  SELECT id FROM servers
                  WHERE is_selected = 0 AND status = "active" AND COALESCE(latency, 99999) <= ?
                  ORDER BY COALESCE(latency, 99999) ASC, dislikes ASC, updated_at DESC
                  LIMIT ?
                )
                """,
                (int(max_latency_ms), to_add),
            )
            await db.commit()


async def reselect_top_servers(
    db: aiosqlite.Connection,
    *,
    max_selected: int,
    updated_since: str | None = None,
    only_updated_since: bool = False,
) -> int:
    """Rebuild the selected set (max 150) prioritizing recency, protocol, and latency.

    Ordering:
    1) Servers updated since `updated_since` (current scan) first (when provided)
    2) Protocol quality priority: vless > vmess > trojan (but keep a small mix when available)
    3) Lower latency, fewer dislikes, newer updated_at
    """
    await cleanup_invalid_selected_servers(db, max_latency_ms=99999)
    await db.execute("UPDATE servers SET is_selected = 0")

    max_selected = max(0, int(max_selected))
    if max_selected <= 0:
        await db.commit()
        return 0

    base_where = 'status = "active" AND COALESCE(copy_config, \'\') != \'\''
    base_params: list[object] = []
    if only_updated_since and updated_since:
        base_where += " AND updated_at >= ?"
        base_params.append(str(updated_since))
        base_where += " AND scanned = 1"

    # Keep a mix when possible so the list isn't "only vless" if vless count is very high.
    # Defaults: vless ~70%, vmess ~20%, trojan ~10%.
    vmess_cap = max(0, (max_selected * 20) // 100)
    trojan_cap = max(0, (max_selected * 10) // 100)
    vless_cap = max(0, max_selected - vmess_cap - trojan_cap)

    async def _select_ids_for_protocol(protocol: str, limit_n: int) -> list[int]:
        if limit_n <= 0:
            return []
        rows = await fetchall(
            db,
            f"""
            SELECT id
            FROM servers
            WHERE {base_where} AND protocol = ?
            ORDER BY
              COALESCE(latency, 99999) ASC,
              dislikes ASC,
              updated_at DESC
            LIMIT ?
            """,
            (*base_params, str(protocol), int(limit_n)),
        )
        return [int(r["id"]) for r in rows if r and r.get("id") is not None]

    selected_ids: list[int] = []
    selected_set: set[int] = set()

    for protocol, cap in (("vless", vless_cap), ("vmess", vmess_cap), ("trojan", trojan_cap)):
        for sid in await _select_ids_for_protocol(protocol, cap):
            if sid in selected_set:
                continue
            selected_set.add(sid)
            selected_ids.append(sid)

    remaining = max_selected - len(selected_ids)
    if remaining > 0:
        # Fill the rest with best available, keeping vless/vmess preferred over trojan.
        exclude_sql = ""
        params: list[object] = list(base_params)
        if selected_ids:
            placeholders = ",".join(["?"] * len(selected_ids))
            exclude_sql = f" AND id NOT IN ({placeholders})"
            params.extend(selected_ids)
        params.append(int(remaining))

        rows = await fetchall(
            db,
            f"""
            SELECT id
            FROM servers
            WHERE {base_where}{exclude_sql}
            ORDER BY
              CASE protocol
                WHEN 'vless' THEN 0
                WHEN 'vmess' THEN 1
                WHEN 'trojan' THEN 2
                ELSE 9
              END ASC,
              COALESCE(latency, 99999) ASC,
              dislikes ASC,
              updated_at DESC
            LIMIT ?
            """,
            tuple(params),
        )
        for r in rows:
            sid = int(r["id"])
            if sid in selected_set:
                continue
            selected_set.add(sid)
            selected_ids.append(sid)

    if not selected_ids:
        await db.commit()
        return 0

    placeholders = ",".join(["?"] * len(selected_ids))
    await db.execute(
        f"UPDATE servers SET is_selected = 1 WHERE id IN ({placeholders})",
        tuple(selected_ids),
    )

    await db.commit()
    return await count_selected_active(db)
async def trim_selected_servers(db: aiosqlite.Connection, *, max_selected: int) -> int:
    row = await fetchone(
        db,
        'SELECT COUNT(*) as cnt FROM servers WHERE is_selected = 1 AND status = "active"',
    )
    current = int(row["cnt"] if row else 0)
    if current <= max_selected:
        return 0

    to_remove = current - int(max_selected)
    await db.execute(
        """
        UPDATE servers
        SET is_selected = 0
        WHERE id IN (
          SELECT id FROM servers
          WHERE is_selected = 1 AND status = "active"
          ORDER BY COALESCE(latency, 99999) DESC, dislikes DESC, updated_at ASC
          LIMIT ?
        )
        """,
        (to_remove,),
    )
    await db.commit()
    return to_remove



async def update_stats(
    db: aiosqlite.Connection,
    *,
    total_scanned: int,
    total_active: int,
    total_selected: int | None = None,
    scan_completed_at: str | None,
    next_scan_at: str | None,
) -> None:
    if total_selected is None:
        total_selected = int(total_active)

    row = await fetchone(db, "SELECT SUM(dislikes) as total_dislikes FROM servers")
    total_dislikes = int(row["total_dislikes"] or 0) if row else 0

    await db.execute(
        """
        UPDATE stats SET
          total_scanned = ?,
          total_active = ?,
          total_selected = ?,
          total_dislikes = ?,
          last_scan = CURRENT_TIMESTAMP,
          scan_completed_at = ?,
          next_scan_at = ?,
          updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """,
        (
            int(total_scanned),
            int(total_active),
            int(total_selected),
            total_dislikes,
            scan_completed_at,
            next_scan_at,
        ),
    )
    await db.commit()


async def maybe_purge_runtime_data(db: aiosqlite.Connection, *, interval_days: int = 3) -> bool:
    row = await fetchone(
        db,
        "SELECT last_cleanup_at, scan_completed_at, next_scan_at FROM stats WHERE id = 1",
    )
    if not row:
        return False

    last_cleanup_at = row["last_cleanup_at"]
    if last_cleanup_at is None:
        await db.execute("UPDATE stats SET last_cleanup_at = CURRENT_TIMESTAMP WHERE id = 1")
        await db.commit()
        return False

    due = await fetchone(
        db,
        "SELECT 1 as due FROM stats WHERE id = 1 AND last_cleanup_at <= datetime('now', ?)",
        (f"-{int(interval_days)} days",),
    )
    if not due:
        return False

    scan_completed_at = str(row["scan_completed_at"]) if row["scan_completed_at"] is not None else None
    next_scan_at = str(row["next_scan_at"]) if row["next_scan_at"] is not None else None

    await db.execute("DELETE FROM servers")
    await db.execute("DELETE FROM bot_sessions")
    await db.execute(
        """
        UPDATE stats SET
          total_scanned = 0,
          total_active = 0,
          total_selected = 0,
          total_dislikes = 0,
          last_scan = NULL,
          scan_completed_at = ?,
          next_scan_at = ?,
          last_cleanup_at = CURRENT_TIMESTAMP,
          updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """,
        (scan_completed_at, next_scan_at),
    )
    await db.commit()
    return True


async def delete_servers_before(db: aiosqlite.Connection, *, before_ts: str) -> None:
    await db.execute(
        "DELETE FROM servers WHERE updated_at < ?",
        (before_ts,),
    )
    await db.commit()


async def get_scan_times(db: aiosqlite.Connection) -> tuple[str | None, str | None]:
    row = await fetchone(
        db,
        "SELECT scan_completed_at, next_scan_at FROM stats WHERE id = 1",
    )
    if not row:
        return None, None
    return (
        str(row["scan_completed_at"]) if row["scan_completed_at"] is not None else None,
        str(row["next_scan_at"]) if row["next_scan_at"] is not None else None,
    )


async def get_stats(db: aiosqlite.Connection) -> dict[str, int | str | None]:
    row = await fetchone(
        db,
        """
        SELECT total_scanned, total_active, total_selected, total_dislikes,
               scan_completed_at, next_scan_at
        FROM stats
        WHERE id = 1
        """,
    )
    if not row:
        return {
            "total_scanned": 0,
            "total_active": 0,
            "total_selected": 0,
            "total_dislikes": 0,
            "scan_completed_at": None,
            "next_scan_at": None,
        }
    return {
        "total_scanned": int(row["total_scanned"] or 0),
        "total_active": int(row["total_active"] or 0),
        "total_selected": int(row["total_selected"] or 0),
        "total_dislikes": int(row["total_dislikes"] or 0),
        "scan_completed_at": str(row["scan_completed_at"]) if row["scan_completed_at"] is not None else None,
        "next_scan_at": str(row["next_scan_at"]) if row["next_scan_at"] is not None else None,
    }
