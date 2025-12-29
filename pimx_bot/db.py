from __future__ import annotations

import json
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
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/refs/heads/main/configs/us/all.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/refs/heads/main/Sub25.txt",
    "https://raw.githubusercontent.com/Danialsamadi/v2go/refs/heads/main/Sub21.txt",
    "https://raw.githubusercontent.com/nyeinkokoaung404/V2ray-Configs/refs/heads/main/Sub1.txt",
    "https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/refs/heads/main/configs/ua/all.txt",

]


@dataclass(frozen=True, slots=True)
class ListedServer:
    id: int
    name: str
    latency: int | None
    country: str | None
    config_string: str


async def connect(db_path: str) -> aiosqlite.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
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

    for idx, url in enumerate(DEFAULT_SOURCES, start=1):
        await db.execute(
            "INSERT OR IGNORE INTO sources (url, name) VALUES (?, ?)",
            (url, f"Source {idx}"),
        )
    await db.commit()


async def get_active_sources(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    rows = await fetchall(db, "SELECT * FROM sources WHERE active = 1")
    return [dict(r) for r in rows]


async def upsert_server(db: aiosqlite.Connection, server: dict[str, Any]) -> None:
    await db.execute(
        """
        INSERT INTO servers (
          config_string, protocol, transport, tls, name, address, port, host, path, country,
          latency, status, operators, packet_loss, speed, quality_score, reachable, scanned, source_id,
          is_selected, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(config_string) DO UPDATE SET
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


async def get_selected_servers_page(
    db: aiosqlite.Connection, *, offset: int, limit: int, max_config_len: int | None = None
) -> list[ListedServer]:
    max_len_sql = ""
    params: tuple[object, ...]
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_config_len), limit, offset)
    else:
        params = (limit, offset)
    rows = await fetchall(
        db,
        f"""
        SELECT id, name, latency, country, config_string
        FROM servers
        WHERE status = "active"{max_len_sql}
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
        )
        for r in rows
    ]


async def get_selected_servers_total(db: aiosqlite.Connection) -> int:
    return await get_selected_servers_total_with_max_len(db, max_config_len=None)


async def get_selected_servers_total_with_max_len(
    db: aiosqlite.Connection, *, max_config_len: int | None
) -> int:
    max_len_sql = ""
    params: tuple[object, ...] = ()
    if max_config_len is not None:
        max_len_sql = " AND LENGTH(config_string) <= ?"
        params = (int(max_config_len),)
    row = await fetchone(
        db,
        f'SELECT COUNT(*) as cnt FROM servers WHERE status = "active"{max_len_sql}',
        params,
    )
    return int(row["cnt"] if row else 0)


async def get_server_config_string(db: aiosqlite.Connection, server_id: int) -> str | None:
    row = await fetchone(db, "SELECT config_string FROM servers WHERE id = ?", (server_id,))
    if not row:
        return None
    return str(row["config_string"])


async def manage_selected_servers(
    db: aiosqlite.Connection, *, min_selected: int, max_selected: int
) -> None:
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
        await db.execute(
            """
            UPDATE servers
            SET is_selected = 1
            WHERE id IN (
              SELECT id FROM servers
              WHERE is_selected = 0 AND status = "active" AND COALESCE(latency, 99999) < 250
              ORDER BY COALESCE(latency, 99999) ASC, dislikes ASC, updated_at DESC
              LIMIT ?
            )
            """,
            (to_add,),
        )
        await db.commit()


async def update_stats(
    db: aiosqlite.Connection, *, scan_completed_at: str | None, next_scan_at: str | None
) -> None:
    row = await fetchone(
        db,
        """
        SELECT
          COUNT(*) as total_scanned,
          SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as total_active,
          SUM(CASE WHEN is_selected = 1 THEN 1 ELSE 0 END) as total_selected,
          SUM(dislikes) as total_dislikes
        FROM servers
        """
    )
    if not row:
        return

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
            int(row["total_scanned"] or 0),
            int(row["total_active"] or 0),
            int(row["total_selected"] or 0),
            int(row["total_dislikes"] or 0),
            scan_completed_at,
            next_scan_at,
        ),
    )
    await db.commit()


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
