"""SQLite database layer for Vertigo.

The database is the source of truth for all moderation actions and guild-specific
settings. All methods are designed to be safe to call concurrently from cogs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """UTC aware now."""

    return datetime.now(timezone.utc)


@dataclass(slots=True)
class GuildSettings:
    guild_id: int
    prefix: str
    warn_duration: int
    modlog_channel_id: int | None
    commands_channel_id: int | None
    staff_role_ids: list[int]
    member_role_id: int | None
    head_mod_role_ids: list[int]
    senior_mod_role_ids: list[int]
    moderator_role_ids: list[int]
    flag_duration: int
    admin_role_ids: list[int]
    lock_categories: list[int]


@dataclass(slots=True)
class AISettings:
    guild_id: int
    ai_enabled: bool
    ai_personality: str
    respond_to_mentions: bool
    respond_to_dms: bool
    help_moderation: bool


def _csv_to_int_list(value: str | None) -> list[int]:
    if not value:
        return []
    out: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def _int_list_to_csv(value: list[int] | None) -> str:
    if not value:
        return ""
    return ",".join(str(v) for v in value)


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the SQLite connection and create schema."""

        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._init_schema()

    async def close(self) -> None:
        if self._conn is None:
            return
        await self._conn.close()
        self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected")
        return self._conn

    async def _init_schema(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id                INTEGER PRIMARY KEY,
                prefix                  TEXT DEFAULT '!',
                warn_duration           INTEGER DEFAULT 14,
                modlog_channel_id       INTEGER,
                commands_channel_id     INTEGER,
                staff_role_ids          TEXT DEFAULT '',
                member_role_id          INTEGER,
                head_mod_role_ids       TEXT DEFAULT '',
                senior_mod_role_ids     TEXT DEFAULT '',
                moderator_role_ids      TEXT DEFAULT '',
                flag_duration           INTEGER DEFAULT 30,
                admin_role_ids          TEXT DEFAULT '',
                lock_categories         TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                moderator_id    INTEGER NOT NULL,
                reason          TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                expires_at      TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS mutes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                moderator_id    INTEGER NOT NULL,
                reason          TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                duration        INTEGER NOT NULL,
                expires_at      TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bans (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                moderator_id    INTEGER NOT NULL,
                reason          TEXT NOT NULL,
                timestamp       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS staff_flags (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_user_id   INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                admin_id        INTEGER NOT NULL,
                reason          TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                expires_at      TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS temp_roles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                role_id         INTEGER NOT NULL,
                assigned_by     INTEGER NOT NULL,
                timestamp       TEXT NOT NULL,
                duration        INTEGER NOT NULL,
                expires_at      TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS persistent_roles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                role_id         INTEGER NOT NULL,
                assigned_by     INTEGER NOT NULL,
                timestamp       TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS modlogs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                action_type     TEXT NOT NULL,
                user_id         INTEGER,
                moderator_id    INTEGER,
                target_id       INTEGER,
                reason          TEXT,
                timestamp       TEXT NOT NULL,
                message_id      INTEGER
            );

            CREATE TABLE IF NOT EXISTS imprisonments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                moderator_id    INTEGER NOT NULL,
                roles_json      TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS blacklisted_guilds (
                guild_id        INTEGER PRIMARY KEY,
                reason          TEXT,
                timestamp       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ai_settings (
                guild_id INTEGER PRIMARY KEY,
                ai_enabled BOOLEAN DEFAULT TRUE,
                ai_personality TEXT DEFAULT 'genz',
                respond_to_mentions BOOLEAN DEFAULT TRUE,
                respond_to_dms BOOLEAN DEFAULT FALSE,
                help_moderation BOOLEAN DEFAULT TRUE
            );
            """
        )
        await self.conn.commit()

    async def ensure_guild_settings(self, guild_id: int, *, default_prefix: str = "!") -> None:
        """Create default settings for a guild if they do not exist."""

        await self.conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id, prefix) VALUES (?, ?)",
            (guild_id, default_prefix),
        )
        await self.conn.commit()

    async def get_guild_settings(self, guild_id: int, *, default_prefix: str = "!") -> GuildSettings:
        await self.ensure_guild_settings(guild_id, default_prefix=default_prefix)
        async with self.conn.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        assert row is not None
        return GuildSettings(
            guild_id=row["guild_id"],
            prefix=row["prefix"] or default_prefix,
            warn_duration=int(row["warn_duration"] or 14),
            modlog_channel_id=row["modlog_channel_id"],
            commands_channel_id=row["commands_channel_id"],
            staff_role_ids=_csv_to_int_list(row["staff_role_ids"]),
            member_role_id=row["member_role_id"],
            head_mod_role_ids=_csv_to_int_list(row["head_mod_role_ids"]),
            senior_mod_role_ids=_csv_to_int_list(row["senior_mod_role_ids"]),
            moderator_role_ids=_csv_to_int_list(row["moderator_role_ids"]),
            flag_duration=int(row["flag_duration"] or 30),
            admin_role_ids=_csv_to_int_list(row["admin_role_ids"]),
            lock_categories=_csv_to_int_list(row["lock_categories"]),
        )

    async def update_guild_settings(self, guild_id: int, **kwargs: Any) -> None:
        """Update guild settings with validated values."""

        if not kwargs:
            return

        normalized: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key.endswith("_role_ids") or key in {"staff_role_ids", "lock_categories", "admin_role_ids"}:
                if isinstance(value, list):
                    normalized[key] = _int_list_to_csv([int(v) for v in value])
                else:
                    normalized[key] = str(value)
            else:
                normalized[key] = value

        fields = ", ".join(f"{k} = ?" for k in normalized)
        params = list(normalized.values()) + [guild_id]
        await self.conn.execute(f"UPDATE guild_settings SET {fields} WHERE guild_id = ?", params)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Modlogs
    # ---------------------------------------------------------------------

    async def add_modlog(
        self,
        *,
        guild_id: int,
        action_type: str,
        user_id: int | None,
        moderator_id: int | None,
        target_id: int | None = None,
        reason: str | None = None,
        message_id: int | None = None,
    ) -> int:
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO modlogs (guild_id, action_type, user_id, moderator_id, target_id, reason, timestamp, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, action_type, user_id, moderator_id, target_id, reason, ts, message_id),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_modlogs_for_user(self, guild_id: int, user_id: int, *, limit: int = 100) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            "SELECT * FROM modlogs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, user_id, limit),
        ) as cur:
            return await cur.fetchall()

    async def get_modlogs_as_moderator(self, guild_id: int, moderator_id: int, *, limit: int = 50) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            "SELECT * FROM modlogs WHERE guild_id = ? AND moderator_id = ? ORDER BY id DESC LIMIT ?",
            (guild_id, moderator_id, limit),
        ) as cur:
            return await cur.fetchall()

    # ---------------------------------------------------------------------
    # Warnings
    # ---------------------------------------------------------------------

    async def add_warning(self, *, guild_id: int, user_id: int, moderator_id: int, reason: str, warn_days: int) -> int:
        ts = utcnow()
        expires = ts + timedelta(days=warn_days)
        cur = await self.conn.execute(
            """
            INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, moderator_id, reason, ts.isoformat(), expires.isoformat()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def deactivate_warning(self, *, warn_id: int, guild_id: int) -> None:
        await self.conn.execute(
            "UPDATE warnings SET is_active = 0 WHERE id = ? AND guild_id = ?",
            (warn_id, guild_id),
        )
        await self.conn.commit()

    async def get_active_warnings(self, *, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            """
            SELECT * FROM warnings
            WHERE guild_id = ? AND user_id = ? AND is_active = 1
            ORDER BY id DESC
            """,
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchall()

    async def get_expired_warnings(self, *, limit: int = 100) -> list[aiosqlite.Row]:
        now = utcnow().isoformat()
        async with self.conn.execute(
            "SELECT * FROM warnings WHERE is_active = 1 AND expires_at <= ? ORDER BY id ASC LIMIT ?",
            (now, limit),
        ) as cur:
            return await cur.fetchall()

    async def expire_warning_ids(self, warn_ids: list[int]) -> None:
        if not warn_ids:
            return
        placeholders = ",".join("?" for _ in warn_ids)
        await self.conn.execute(f"UPDATE warnings SET is_active = 0 WHERE id IN ({placeholders})", warn_ids)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Mutes
    # ---------------------------------------------------------------------

    async def add_mute(
        self,
        *,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        duration_seconds: int,
    ) -> int:
        ts = utcnow()
        expires = ts + timedelta(seconds=duration_seconds)
        cur = await self.conn.execute(
            """
            INSERT INTO mutes (user_id, guild_id, moderator_id, reason, timestamp, duration, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, moderator_id, reason, ts.isoformat(), duration_seconds, expires.isoformat()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def deactivate_active_mutes(self, *, guild_id: int, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE mutes SET is_active = 0 WHERE guild_id = ? AND user_id = ? AND is_active = 1",
            (guild_id, user_id),
        )
        await self.conn.commit()

    async def get_expired_mutes(self, *, limit: int = 100) -> list[aiosqlite.Row]:
        now = utcnow().isoformat()
        async with self.conn.execute(
            "SELECT * FROM mutes WHERE is_active = 1 AND expires_at <= ? ORDER BY id ASC LIMIT ?",
            (now, limit),
        ) as cur:
            return await cur.fetchall()

    async def expire_mute_ids(self, mute_ids: list[int]) -> None:
        if not mute_ids:
            return
        placeholders = ",".join("?" for _ in mute_ids)
        await self.conn.execute(f"UPDATE mutes SET is_active = 0 WHERE id IN ({placeholders})", mute_ids)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Bans
    # ---------------------------------------------------------------------

    async def add_ban(self, *, guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO bans (user_id, guild_id, moderator_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, guild_id, moderator_id, reason, ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_last_ban(self, *, guild_id: int, user_id: int) -> aiosqlite.Row | None:
        async with self.conn.execute(
            "SELECT * FROM bans WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 1",
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchone()

    # ---------------------------------------------------------------------
    # Staff flags
    # ---------------------------------------------------------------------

    async def add_staff_flag(
        self,
        *,
        guild_id: int,
        staff_user_id: int,
        admin_id: int,
        reason: str,
        duration_days: int,
    ) -> int:
        ts = utcnow()
        expires = ts + timedelta(days=duration_days)
        cur = await self.conn.execute(
            """
            INSERT INTO staff_flags (staff_user_id, guild_id, admin_id, reason, timestamp, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (staff_user_id, guild_id, admin_id, reason, ts.isoformat(), expires.isoformat()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def deactivate_staff_flag(self, *, guild_id: int, flag_id: int) -> None:
        await self.conn.execute(
            "UPDATE staff_flags SET is_active = 0 WHERE guild_id = ? AND id = ?",
            (guild_id, flag_id),
        )
        await self.conn.commit()

    async def get_active_staff_flags(self, *, guild_id: int, staff_user_id: int) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            """
            SELECT * FROM staff_flags
            WHERE guild_id = ? AND staff_user_id = ? AND is_active = 1
            ORDER BY id ASC
            """,
            (guild_id, staff_user_id),
        ) as cur:
            return await cur.fetchall()

    async def get_expired_staff_flags(self, *, limit: int = 100) -> list[aiosqlite.Row]:
        now = utcnow().isoformat()
        async with self.conn.execute(
            "SELECT * FROM staff_flags WHERE is_active = 1 AND expires_at <= ? ORDER BY id ASC LIMIT ?",
            (now, limit),
        ) as cur:
            return await cur.fetchall()

    async def expire_staff_flag_ids(self, flag_ids: list[int]) -> None:
        if not flag_ids:
            return
        placeholders = ",".join("?" for _ in flag_ids)
        await self.conn.execute(f"UPDATE staff_flags SET is_active = 0 WHERE id IN ({placeholders})", flag_ids)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Temp / persistent roles
    # ---------------------------------------------------------------------

    async def add_temp_role(
        self,
        *,
        guild_id: int,
        user_id: int,
        role_id: int,
        assigned_by: int,
        duration_seconds: int,
    ) -> int:
        ts = utcnow()
        expires = ts + timedelta(seconds=duration_seconds)
        cur = await self.conn.execute(
            """
            INSERT INTO temp_roles (user_id, guild_id, role_id, assigned_by, timestamp, duration, expires_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, role_id, assigned_by, ts.isoformat(), duration_seconds, expires.isoformat()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def deactivate_temp_role(self, *, guild_id: int, user_id: int, role_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE temp_roles
            SET is_active = 0
            WHERE guild_id = ? AND user_id = ? AND role_id = ? AND is_active = 1
            """,
            (guild_id, user_id, role_id),
        )
        await self.conn.commit()

    async def get_expired_temp_roles(self, *, limit: int = 100) -> list[aiosqlite.Row]:
        now = utcnow().isoformat()
        async with self.conn.execute(
            "SELECT * FROM temp_roles WHERE is_active = 1 AND expires_at <= ? ORDER BY id ASC LIMIT ?",
            (now, limit),
        ) as cur:
            return await cur.fetchall()

    async def expire_temp_role_ids(self, ids_: list[int]) -> None:
        if not ids_:
            return
        placeholders = ",".join("?" for _ in ids_)
        await self.conn.execute(f"UPDATE temp_roles SET is_active = 0 WHERE id IN ({placeholders})", ids_)
        await self.conn.commit()

    async def add_persistent_role(
        self,
        *,
        guild_id: int,
        user_id: int,
        role_id: int,
        assigned_by: int,
    ) -> int:
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO persistent_roles (user_id, guild_id, role_id, assigned_by, timestamp, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, role_id, assigned_by, ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def deactivate_persistent_role(self, *, guild_id: int, user_id: int, role_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE persistent_roles
            SET is_active = 0
            WHERE guild_id = ? AND user_id = ? AND role_id = ? AND is_active = 1
            """,
            (guild_id, user_id, role_id),
        )
        await self.conn.commit()

    async def get_active_persistent_roles(self) -> list[aiosqlite.Row]:
        async with self.conn.execute(
            "SELECT * FROM persistent_roles WHERE is_active = 1 ORDER BY id ASC"
        ) as cur:
            return await cur.fetchall()

    # ---------------------------------------------------------------------
    # Imprisonments
    # ---------------------------------------------------------------------

    async def add_imprisonment(
        self,
        *,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        role_ids: list[int],
    ) -> int:
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO imprisonments (user_id, guild_id, moderator_id, roles_json, timestamp, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (user_id, guild_id, moderator_id, json.dumps(role_ids), ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_active_imprisonment(self, *, guild_id: int, user_id: int) -> aiosqlite.Row | None:
        async with self.conn.execute(
            """
            SELECT * FROM imprisonments
            WHERE guild_id = ? AND user_id = ? AND is_active = 1
            ORDER BY id DESC
            LIMIT 1
            """,
            (guild_id, user_id),
        ) as cur:
            return await cur.fetchone()

    async def deactivate_imprisonment(self, *, imprison_id: int) -> None:
        await self.conn.execute(
            "UPDATE imprisonments SET is_active = 0 WHERE id = ?",
            (imprison_id,),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Guild blacklist (owner-only)
    # ---------------------------------------------------------------------

    async def blacklist_guild(self, *, guild_id: int, reason: str | None) -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO blacklisted_guilds (guild_id, reason, timestamp) VALUES (?, ?, ?)",
            (guild_id, reason, utcnow().isoformat()),
        )
        await self.conn.commit()

    async def unblacklist_guild(self, *, guild_id: int) -> None:
        await self.conn.execute("DELETE FROM blacklisted_guilds WHERE guild_id = ?", (guild_id,))
        await self.conn.commit()

    async def is_guild_blacklisted(self, *, guild_id: int) -> bool:
        async with self.conn.execute(
            "SELECT guild_id FROM blacklisted_guilds WHERE guild_id = ?", (guild_id,)
        ) as cur:
            return (await cur.fetchone()) is not None

    async def get_blacklisted_guilds(self) -> list[aiosqlite.Row]:
        async with self.conn.execute("SELECT * FROM blacklisted_guilds ORDER BY timestamp DESC") as cur:
            return await cur.fetchall()

    # ---------------------------------------------------------------------
    # AI Settings
    # ---------------------------------------------------------------------

    async def ensure_ai_settings(self, guild_id: int) -> None:
        """Create default AI settings for a guild if they do not exist."""
        await self.conn.execute(
            "INSERT OR IGNORE INTO ai_settings (guild_id) VALUES (?)",
            (guild_id,),
        )
        await self.conn.commit()

    async def get_ai_settings(self, guild_id: int) -> AISettings:
        await self.ensure_ai_settings(guild_id)
        async with self.conn.execute("SELECT * FROM ai_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        assert row is not None
        return AISettings(
            guild_id=row["guild_id"],
            ai_enabled=bool(row["ai_enabled"]),
            ai_personality=row["ai_personality"] or "genz",
            respond_to_mentions=bool(row["respond_to_mentions"]),
            respond_to_dms=bool(row["respond_to_dms"]),
            help_moderation=bool(row["help_moderation"]),
        )

    async def update_ai_settings(self, guild_id: int, **kwargs: Any) -> None:
        """Update AI settings with validated values."""
        if not kwargs:
            return
        
        normalized: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in {"ai_enabled", "respond_to_mentions", "respond_to_dms", "help_moderation"}:
                normalized[key] = bool(value)
            elif key == "ai_personality":
                normalized[key] = str(value)
        
        fields = ", ".join(f"{k} = ?" for k in normalized)
        params = list(normalized.values()) + [guild_id]
        await self.conn.execute(f"UPDATE ai_settings SET {fields} WHERE guild_id = ?", params)
        await self.conn.commit()
