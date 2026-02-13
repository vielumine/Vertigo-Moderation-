"""SQLite database layer for Luna.

The database is the source of truth for all moderation actions, guild-specific
settings, tags, shifts, reminders, and stats. All methods are designed to be 
safe to call concurrently from cogs.
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
    promotion_channel_id: int | None


@dataclass(slots=True)
class AISettings:
    guild_id: int
    ai_enabled: bool
    ai_personality: str
    respond_to_mentions: bool
    respond_to_dms: bool
    help_moderation: bool


@dataclass(slots=True)
class AITarget:
    user_id: int
    guild_id: int
    target_by: int
    timestamp: str
    notes: str | None


@dataclass(slots=True)
class BotBlacklist:
    user_id: int
    blacklisted_by: int
    reason: str
    timestamp: str


@dataclass(slots=True)
class TimeoutSettings:
    guild_id: int
    phrases: str
    alert_role_id: int | None
    alert_channel_id: int | None
    timeout_duration: int
    enabled: bool


@dataclass(slots=True)
class DMNotificationSettings:
    guild_id: int
    enabled: bool
    notify_warns: bool
    notify_mutes: bool
    notify_kicks: bool
    notify_bans: bool
    notify_flags: bool


@dataclass(slots=True)
class PromotionSuggestion:
    id: int
    guild_id: int
    user_id: int
    suggestion_type: str
    current_role: str | None
    suggested_role: str | None
    confidence: float
    reason: str | None
    metrics: str | None
    timestamp: str
    status: str
    reviewed_by: int | None
    reviewed_at: str | None


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
                lock_categories         TEXT DEFAULT '',
                promotion_channel_id    INTEGER
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
                ai_personality TEXT DEFAULT 'professional',
                respond_to_mentions BOOLEAN DEFAULT TRUE,
                respond_to_dms BOOLEAN DEFAULT FALSE,
                help_moderation BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS ai_targets (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                target_by INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS bot_blacklist (
                user_id INTEGER PRIMARY KEY,
                blacklisted_by INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timeout_settings (
                guild_id INTEGER PRIMARY KEY,
                phrases TEXT DEFAULT '',
                alert_role_id INTEGER,
                alert_channel_id INTEGER,
                timeout_duration INTEGER DEFAULT 86400,
                enabled BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS staff_hierarchy (
                guild_id        INTEGER PRIMARY KEY,
                role_ids        TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS mod_stats (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                action_type     TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                UNIQUE(guild_id, user_id, action_type, timestamp)
            );

            CREATE TABLE IF NOT EXISTS afk (
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                reason          TEXT,
                timestamp       TEXT NOT NULL,
                pings           TEXT DEFAULT '',
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS trial_mod_roles (
                guild_id        INTEGER PRIMARY KEY,
                role_ids        TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS tags (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                category        TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT NOT NULL,
                creator_id      INTEGER NOT NULL,
                created_at      TEXT NOT NULL,
                UNIQUE(guild_id, category, title)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER,
                text            TEXT NOT NULL,
                expiration_ts   TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                shift_type      TEXT NOT NULL,
                start_ts_utc    TEXT NOT NULL,
                start_ts_gmt8   TEXT NOT NULL,
                end_ts_utc      TEXT,
                end_ts_gmt8     TEXT,
                break_duration  INTEGER DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS shift_configs (
                guild_id        INTEGER NOT NULL,
                role_id         INTEGER NOT NULL,
                shift_type      TEXT NOT NULL,
                afk_timeout     INTEGER DEFAULT 300,
                weekly_quota    INTEGER DEFAULT 10,
                PRIMARY KEY (guild_id, role_id, shift_type)
            );

            CREATE TABLE IF NOT EXISTS quota_tracking (
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                shift_type      TEXT NOT NULL,
                week_gmt8       TEXT NOT NULL,
                hours_logged    REAL DEFAULT 0,
                quota_met       INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, shift_type, week_gmt8)
            );

            CREATE TABLE IF NOT EXISTS stats (
                key             TEXT PRIMARY KEY,
                value           INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS dm_notification_settings (
                guild_id        INTEGER PRIMARY KEY,
                enabled         INTEGER NOT NULL DEFAULT 1,
                notify_warns    INTEGER NOT NULL DEFAULT 1,
                notify_mutes    INTEGER NOT NULL DEFAULT 1,
                notify_kicks    INTEGER NOT NULL DEFAULT 1,
                notify_bans     INTEGER NOT NULL DEFAULT 1,
                notify_flags    INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS dm_notification_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                action_type     TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                success         INTEGER NOT NULL,
                reason          TEXT
            );

            CREATE TABLE IF NOT EXISTS staff_performance_metrics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                period_start    TEXT NOT NULL,
                period_end      TEXT NOT NULL,
                warns_count     INTEGER DEFAULT 0,
                mutes_count     INTEGER DEFAULT 0,
                kicks_count     INTEGER DEFAULT 0,
                bans_count      INTEGER DEFAULT 0,
                total_actions   INTEGER DEFAULT 0,
                activity_score  REAL DEFAULT 0,
                UNIQUE(guild_id, user_id, period_start)
            );

            CREATE TABLE IF NOT EXISTS promotion_suggestions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                suggestion_type TEXT NOT NULL,
                current_role    TEXT,
                suggested_role  TEXT,
                confidence      REAL DEFAULT 0,
                reason          TEXT,
                metrics         TEXT,
                timestamp       TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                reviewed_by     INTEGER,
                reviewed_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS dm_preferences (
                user_id         INTEGER NOT NULL,
                guild_id        INTEGER NOT NULL,
                receive_dms     INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
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
            promotion_channel_id=row["promotion_channel_id"],
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
            ORDER BY id ASC
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

    # ---------------------------------------------------------------------
    # AI Targets
    # ---------------------------------------------------------------------

    async def add_ai_target(self, *, user_id: int, guild_id: int, target_by: int, notes: str | None = None) -> None:
        """Add a user to AI targeting list."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO ai_targets (user_id, guild_id, target_by, timestamp, notes) VALUES (?, ?, ?, ?, ?)",
            (user_id, guild_id, target_by, utcnow().isoformat(), notes),
        )
        await self.conn.commit()

    async def remove_ai_target(self, *, user_id: int, guild_id: int) -> None:
        """Remove a user from AI targeting list."""
        await self.conn.execute("DELETE FROM ai_targets WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        await self.conn.commit()

    async def get_ai_target(self, *, user_id: int, guild_id: int) -> AITarget | None:
        """Get AI target information."""
        async with self.conn.execute("SELECT * FROM ai_targets WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return AITarget(
            user_id=row["user_id"],
            guild_id=row["guild_id"],
            target_by=row["target_by"],
            timestamp=row["timestamp"],
            notes=row["notes"],
        )

    async def get_all_ai_targets(self, *, guild_id: int) -> list[AITarget]:
        """Get all AI targets for a guild."""
        async with self.conn.execute("SELECT * FROM ai_targets WHERE guild_id = ?", (guild_id,)) as cur:
            rows = await cur.fetchall()
        return [
            AITarget(
                user_id=row["user_id"],
                guild_id=row["guild_id"],
                target_by=row["target_by"],
                timestamp=row["timestamp"],
                notes=row["notes"],
            )
            for row in rows
        ]

    # ---------------------------------------------------------------------
    # Bot Blacklist
    # ---------------------------------------------------------------------

    async def add_to_blacklist(self, *, user_id: int, blacklisted_by: int, reason: str) -> None:
        """Add user to bot blacklist."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO bot_blacklist (user_id, blacklisted_by, reason, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, blacklisted_by, reason, utcnow().isoformat()),
        )
        await self.conn.commit()

    async def remove_from_blacklist(self, *, user_id: int) -> None:
        """Remove user from bot blacklist."""
        await self.conn.execute("DELETE FROM bot_blacklist WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def is_blacklisted(self, *, user_id: int) -> bool:
        """Check if user is blacklisted."""
        async with self.conn.execute("SELECT 1 FROM bot_blacklist WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone() is not None

    async def get_blacklist_entry(self, *, user_id: int) -> BotBlacklist | None:
        """Get blacklist entry."""
        async with self.conn.execute("SELECT * FROM bot_blacklist WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return BotBlacklist(
            user_id=row["user_id"],
            blacklisted_by=row["blacklisted_by"],
            reason=row["reason"],
            timestamp=row["timestamp"],
        )

    async def get_all_blacklisted(self) -> list[BotBlacklist]:
        """Get all blacklisted users."""
        async with self.conn.execute("SELECT * FROM bot_blacklist ORDER BY timestamp DESC") as cur:
            rows = await cur.fetchall()
        return [
            BotBlacklist(
                user_id=row["user_id"],
                blacklisted_by=row["blacklisted_by"],
                reason=row["reason"],
                timestamp=row["timestamp"],
            )
            for row in rows
        ]

    # ---------------------------------------------------------------------
    # Timeout Settings
    # ---------------------------------------------------------------------

    async def get_timeout_settings(self, guild_id: int) -> TimeoutSettings:
        """Get timeout settings for guild."""
        async with self.conn.execute("SELECT * FROM timeout_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            # Create default settings
            await self.conn.execute(
                "INSERT OR IGNORE INTO timeout_settings (guild_id) VALUES (?)",
                (guild_id,),
            )
            await self.conn.commit()
            async with self.conn.execute("SELECT * FROM timeout_settings WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
        
        assert row is not None
        return TimeoutSettings(
            guild_id=row["guild_id"],
            phrases=row["phrases"] or "",
            alert_role_id=row["alert_role_id"],
            alert_channel_id=row["alert_channel_id"],
            timeout_duration=int(row["timeout_duration"] or 86400),
            enabled=bool(row["enabled"]),
        )

    async def update_timeout_settings(self, guild_id: int, **kwargs: Any) -> None:
        """Update timeout settings."""
        if not kwargs:
            return
        
        normalized: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key == "phrases":
                normalized[key] = str(value)
            elif key in {"alert_role_id", "alert_channel_id"}:
                normalized[key] = value
            elif key == "timeout_duration":
                normalized[key] = int(value)
            elif key == "enabled":
                normalized[key] = bool(value)
        
        fields = ", ".join(f"{k} = ?" for k in normalized)
        params = list(normalized.values()) + [guild_id]
        await self.conn.execute(f"UPDATE timeout_settings SET {fields} WHERE guild_id = ?", params)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # AI Settings
    # ---------------------------------------------------------------------

    async def get_ai_settings(self, guild_id: int) -> AISettings:
        """Get AI settings for guild."""
        async with self.conn.execute("SELECT * FROM ai_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            # Create default settings
            await self.conn.execute(
                "INSERT OR IGNORE INTO ai_settings (guild_id, ai_enabled, ai_personality, respond_to_mentions, respond_to_dms, help_moderation) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, 1 if config.AI_ENABLED_BY_DEFAULT else 0, "professional", 1, 0, 0),
            )
            await self.conn.commit()
            async with self.conn.execute("SELECT * FROM ai_settings WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()

        assert row is not None
        return AISettings(
            guild_id=row["guild_id"],
            ai_enabled=bool(row["ai_enabled"]),
            ai_personality=row["ai_personality"] or "professional",
            respond_to_mentions=bool(row["respond_to_mentions"]),
            respond_to_dms=bool(row["respond_to_dms"]),
            help_moderation=bool(row["help_moderation"]),
        )

    async def update_ai_settings(self, guild_id: int, **kwargs: Any) -> None:
        """Update AI settings."""
        if not kwargs:
            return

        normalized: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key == "ai_enabled":
                normalized[key] = bool(value)
            elif key == "ai_personality":
                normalized[key] = str(value)
            elif key in {"respond_to_mentions", "respond_to_dms", "help_moderation"}:
                normalized[key] = bool(value)

        fields = ", ".join(f"{k} = ?" for k in normalized)
        params = list(normalized.values()) + [guild_id]
        await self.conn.execute(f"UPDATE ai_settings SET {fields} WHERE guild_id = ?", params)
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Staff Hierarchy
    # ---------------------------------------------------------------------

    async def get_staff_hierarchy(self, guild_id: int) -> list[int]:
        """Get staff hierarchy role IDs for a guild (highest to lowest)."""
        async with self.conn.execute("SELECT role_ids FROM staff_hierarchy WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return []
        return _csv_to_int_list(row["role_ids"])

    async def set_staff_hierarchy(self, guild_id: int, role_ids: list[int]) -> None:
        """Set staff hierarchy role IDs for a guild."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO staff_hierarchy (guild_id, role_ids) VALUES (?, ?)",
            (guild_id, _int_list_to_csv(role_ids)),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Mod Stats
    # ---------------------------------------------------------------------

    async def track_mod_action(self, *, guild_id: int, user_id: int, action_type: str) -> None:
        """Track a moderation action for statistics."""
        ts = utcnow().isoformat()
        try:
            await self.conn.execute(
                "INSERT OR IGNORE INTO mod_stats (guild_id, user_id, action_type, timestamp) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, action_type, ts),
            )
            await self.conn.commit()
        except Exception:
            logger.exception("Failed to track mod action")

    async def get_mod_stats(self, guild_id: int, user_id: int) -> dict:
        """Get mod stats for a user."""
        now = utcnow()
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        fourteen_days_ago = (now - timedelta(days=14)).isoformat()
        thirty_days_ago = (now - timedelta(days=30)).isoformat()

        stats = {
            'warns_7d': 0, 'warns_14d': 0, 'warns_30d': 0, 'warns_total': 0,
            'mutes_7d': 0, 'mutes_14d': 0, 'mutes_30d': 0, 'mutes_total': 0,
            'kicks_7d': 0, 'kicks_14d': 0, 'kicks_30d': 0, 'kicks_total': 0,
            'bans_7d': 0, 'bans_14d': 0, 'bans_30d': 0, 'bans_total': 0,
        }

        for action in ['warns', 'mutes', 'kicks', 'bans']:
            # Total
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ?",
                (guild_id, user_id, action)
            ) as cur:
                row = await cur.fetchone()
                stats[f'{action}_total'] = row['count'] if row else 0

            # Past 30 days
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp >= ?",
                (guild_id, user_id, action, thirty_days_ago)
            ) as cur:
                row = await cur.fetchone()
                stats[f'{action}_30d'] = row['count'] if row else 0

            # Past 14 days
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp >= ?",
                (guild_id, user_id, action, fourteen_days_ago)
            ) as cur:
                row = await cur.fetchone()
                stats[f'{action}_14d'] = row['count'] if row else 0

            # Past 7 days
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp >= ?",
                (guild_id, user_id, action, seven_days_ago)
            ) as cur:
                row = await cur.fetchone()
                stats[f'{action}_7d'] = row['count'] if row else 0

        return stats

    async def get_all_staff_rankings(self, guild_id: int) -> list[dict]:
        """Get all staff ranked by total mod actions."""
        async with self.conn.execute(
            """
            SELECT user_id, COUNT(*) as total 
            FROM mod_stats 
            WHERE guild_id = ? 
            GROUP BY user_id 
            ORDER BY total DESC
            """,
            (guild_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [{'user_id': row['user_id'], 'total': row['total']} for row in rows]

    async def set_mod_stat(self, *, guild_id: int, user_id: int, action_type: str, period: str, value: int) -> None:
        """Manually set a mod stat value."""
        # This is a simplified version - we'll just add/remove entries to match the desired count
        # First, get current count for the period
        now = utcnow()
        
        if period == 'total':
            # Count all entries
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ?",
                (guild_id, user_id, action_type)
            ) as cur:
                row = await cur.fetchone()
                current = row['count'] if row else 0
        else:
            # Count entries within period
            days = int(period.rstrip('d'))
            cutoff = (now - timedelta(days=days)).isoformat()
            async with self.conn.execute(
                "SELECT COUNT(*) as count FROM mod_stats WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp >= ?",
                (guild_id, user_id, action_type, cutoff)
            ) as cur:
                row = await cur.fetchone()
                current = row['count'] if row else 0

        diff = value - current
        
        if diff > 0:
            # Add entries
            for _ in range(diff):
                ts = utcnow().isoformat()
                await self.conn.execute(
                    "INSERT INTO mod_stats (guild_id, user_id, action_type, timestamp) VALUES (?, ?, ?, ?)",
                    (guild_id, user_id, action_type, ts)
                )
        elif diff < 0:
            # Remove entries
            if period == 'total':
                await self.conn.execute(
                    """
                    DELETE FROM mod_stats 
                    WHERE id IN (
                        SELECT id FROM mod_stats 
                        WHERE guild_id = ? AND user_id = ? AND action_type = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    )
                    """,
                    (guild_id, user_id, action_type, abs(diff))
                )
            else:
                days = int(period.rstrip('d'))
                cutoff = (now - timedelta(days=days)).isoformat()
                await self.conn.execute(
                    """
                    DELETE FROM mod_stats 
                    WHERE id IN (
                        SELECT id FROM mod_stats 
                        WHERE guild_id = ? AND user_id = ? AND action_type = ? AND timestamp >= ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    )
                    """,
                    (guild_id, user_id, action_type, cutoff, abs(diff))
                )
        
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # AFK System
    # ---------------------------------------------------------------------

    async def set_afk(self, *, user_id: int, guild_id: int, reason: str | None = None) -> None:
        """Set a user as AFK."""
        ts = utcnow().isoformat()
        await self.conn.execute(
            "INSERT OR REPLACE INTO afk (user_id, guild_id, reason, timestamp, pings) VALUES (?, ?, ?, ?, '')",
            (user_id, guild_id, reason or "AFK", ts),
        )
        await self.conn.commit()

    async def remove_afk(self, *, user_id: int, guild_id: int) -> tuple[str, list[str]] | None:
        """Remove AFK status and return reason + pings."""
        async with self.conn.execute(
            "SELECT reason, pings FROM afk WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
        
        if row is None:
            return None
        
        reason = row['reason']
        pings_str = row['pings'] or ''
        pings = [p for p in pings_str.split('|||') if p.strip()]
        
        await self.conn.execute("DELETE FROM afk WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        await self.conn.commit()
        
        return reason, pings

    async def get_afk(self, *, user_id: int, guild_id: int) -> tuple[str, str] | None:
        """Get AFK status for a user."""
        async with self.conn.execute(
            "SELECT reason, timestamp FROM afk WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
        
        if row is None:
            return None
        
        return row['reason'], row['timestamp']

    async def add_afk_ping(self, *, user_id: int, guild_id: int, ping_info: str) -> None:
        """Add a ping to AFK user's record."""
        async with self.conn.execute(
            "SELECT pings FROM afk WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
        
        if row is None:
            return
        
        current_pings = row['pings'] or ''
        new_pings = f"{current_pings}|||{ping_info}" if current_pings else ping_info
        
        await self.conn.execute(
            "UPDATE afk SET pings = ? WHERE user_id = ? AND guild_id = ?",
            (new_pings, user_id, guild_id)
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Trial Mod Roles
    # ---------------------------------------------------------------------

    async def get_trial_mod_roles(self, guild_id: int) -> list[int]:
        """Get trial moderator role IDs for a guild."""
        async with self.conn.execute("SELECT role_ids FROM trial_mod_roles WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            return []
        return _csv_to_int_list(row["role_ids"])

    async def set_trial_mod_roles(self, guild_id: int, role_ids: list[int]) -> None:
        """Set trial moderator role IDs for a guild."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO trial_mod_roles (guild_id, role_ids) VALUES (?, ?)",
            (guild_id, _int_list_to_csv(role_ids)),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Tags System
    # ---------------------------------------------------------------------

    async def create_tag(self, *, guild_id: int, category: str, title: str, description: str, creator_id: int) -> int:
        """Create a new tag."""
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            "INSERT INTO tags (guild_id, category, title, description, creator_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, category, title, description, creator_id, ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_tag(self, *, guild_id: int, category: str, title: str) -> aiosqlite.Row | None:
        """Get a specific tag."""
        async with self.conn.execute(
            "SELECT * FROM tags WHERE guild_id = ? AND category = ? AND title = ?",
            (guild_id, category, title),
        ) as cur:
            return await cur.fetchone()

    async def get_all_tags(self, guild_id: int) -> list[aiosqlite.Row]:
        """Get all tags for a guild."""
        async with self.conn.execute(
            "SELECT * FROM tags WHERE guild_id = ? ORDER BY category, title",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def get_tags_by_category(self, guild_id: int, category: str) -> list[aiosqlite.Row]:
        """Get tags by category."""
        async with self.conn.execute(
            "SELECT * FROM tags WHERE guild_id = ? AND category = ? ORDER BY title",
            (guild_id, category),
        ) as cur:
            return await cur.fetchall()

    async def update_tag(self, *, guild_id: int, category: str, title: str, description: str) -> None:
        """Update a tag's description."""
        await self.conn.execute(
            "UPDATE tags SET description = ? WHERE guild_id = ? AND category = ? AND title = ?",
            (description, guild_id, category, title),
        )
        await self.conn.commit()

    async def delete_tag(self, *, guild_id: int, category: str, title: str) -> None:
        """Delete a tag."""
        await self.conn.execute(
            "DELETE FROM tags WHERE guild_id = ? AND category = ? AND title = ?",
            (guild_id, category, title),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Reminders
    # ---------------------------------------------------------------------

    async def add_reminder(self, *, user_id: int, guild_id: int | None, text: str, expiration_ts: str) -> int:
        """Add a reminder."""
        cur = await self.conn.execute(
            "INSERT INTO reminders (user_id, guild_id, text, expiration_ts, is_active) VALUES (?, ?, ?, ?, 1)",
            (user_id, guild_id, text, expiration_ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_active_reminders(self, user_id: int) -> list[aiosqlite.Row]:
        """Get active reminders for a user."""
        async with self.conn.execute(
            "SELECT * FROM reminders WHERE user_id = ? AND is_active = 1 ORDER BY expiration_ts",
            (user_id,),
        ) as cur:
            return await cur.fetchall()

    async def get_expired_reminders(self) -> list[aiosqlite.Row]:
        """Get expired reminders."""
        now = utcnow().isoformat()
        async with self.conn.execute(
            "SELECT * FROM reminders WHERE is_active = 1 AND expiration_ts <= ? ORDER BY expiration_ts",
            (now,),
        ) as cur:
            return await cur.fetchall()

    async def deactivate_reminder(self, reminder_id: int) -> None:
        """Deactivate a reminder."""
        await self.conn.execute(
            "UPDATE reminders SET is_active = 0 WHERE id = ?",
            (reminder_id,),
        )
        await self.conn.commit()

    async def delete_reminder(self, reminder_id: int, user_id: int) -> bool:
        """Delete a reminder. Returns True if deleted."""
        async with self.conn.execute(
            "SELECT id FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        ) as cur:
            row = await cur.fetchone()
        
        if row is None:
            return False
        
        await self.conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await self.conn.commit()
        return True

    # ---------------------------------------------------------------------
    # Shifts System
    # ---------------------------------------------------------------------

    async def start_shift(self, *, user_id: int, guild_id: int, shift_type: str, start_ts_utc: str, start_ts_gmt8: str) -> int:
        """Start a new shift."""
        cur = await self.conn.execute(
            "INSERT INTO shifts (user_id, guild_id, shift_type, start_ts_utc, start_ts_gmt8, status) VALUES (?, ?, ?, ?, ?, 'active')",
            (user_id, guild_id, shift_type, start_ts_utc, start_ts_gmt8),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def end_shift(self, *, shift_id: int, end_ts_utc: str, end_ts_gmt8: str, break_duration: int = 0) -> None:
        """End a shift."""
        await self.conn.execute(
            "UPDATE shifts SET end_ts_utc = ?, end_ts_gmt8 = ?, break_duration = ?, status = 'completed' WHERE id = ?",
            (end_ts_utc, end_ts_gmt8, break_duration, shift_id),
        )
        await self.conn.commit()

    async def get_active_shift(self, user_id: int, guild_id: int) -> aiosqlite.Row | None:
        """Get active shift for a user."""
        async with self.conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND guild_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (user_id, guild_id),
        ) as cur:
            return await cur.fetchone()

    async def get_user_shifts(self, user_id: int, guild_id: int, limit: int = 50) -> list[aiosqlite.Row]:
        """Get shifts for a user."""
        async with self.conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND guild_id = ? ORDER BY start_ts_utc DESC LIMIT ?",
            (user_id, guild_id, limit),
        ) as cur:
            return await cur.fetchall()

    async def set_shift_config(self, *, guild_id: int, role_id: int, shift_type: str, afk_timeout: int, weekly_quota: int) -> None:
        """Set shift configuration."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO shift_configs (guild_id, role_id, shift_type, afk_timeout, weekly_quota) VALUES (?, ?, ?, ?, ?)",
            (guild_id, role_id, shift_type, afk_timeout, weekly_quota),
        )
        await self.conn.commit()

    async def get_shift_config(self, guild_id: int, role_id: int, shift_type: str) -> aiosqlite.Row | None:
        """Get shift configuration."""
        async with self.conn.execute(
            "SELECT * FROM shift_configs WHERE guild_id = ? AND role_id = ? AND shift_type = ?",
            (guild_id, role_id, shift_type),
        ) as cur:
            return await cur.fetchone()

    async def update_quota_tracking(self, *, user_id: int, guild_id: int, shift_type: str, week_gmt8: str, hours_logged: float, quota_met: bool) -> None:
        """Update quota tracking."""
        await self.conn.execute(
            """
            INSERT INTO quota_tracking (user_id, guild_id, shift_type, week_gmt8, hours_logged, quota_met)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id, shift_type, week_gmt8) 
            DO UPDATE SET hours_logged = ?, quota_met = ?
            """,
            (user_id, guild_id, shift_type, week_gmt8, hours_logged, int(quota_met), hours_logged, int(quota_met)),
        )
        await self.conn.commit()

    async def get_quota_tracking(self, user_id: int, guild_id: int, shift_type: str, week_gmt8: str) -> aiosqlite.Row | None:
        """Get quota tracking."""
        async with self.conn.execute(
            "SELECT * FROM quota_tracking WHERE user_id = ? AND guild_id = ? AND shift_type = ? AND week_gmt8 = ?",
            (user_id, guild_id, shift_type, week_gmt8),
        ) as cur:
            return await cur.fetchone()

    # ---------------------------------------------------------------------
    # Stats Dashboard
    # ---------------------------------------------------------------------

    async def stats_get(self, key: str, default: int = 0) -> int:
        """Get a stats value."""
        async with self.conn.execute("SELECT value FROM stats WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
        return int(row["value"]) if row else default

    async def stats_set(self, key: str, value: int) -> None:
        """Set a stats value."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO stats (key, value) VALUES (?, ?)",
            (key, value),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # DM Notification Settings
    # ---------------------------------------------------------------------

    async def get_dm_notification_settings(self, guild_id: int) -> DMNotificationSettings:
        """Get DM notification settings for a guild."""
        async with self.conn.execute("SELECT * FROM dm_notification_settings WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
        
        if row is None:
            # Create default settings
            await self.conn.execute(
                "INSERT OR IGNORE INTO dm_notification_settings (guild_id) VALUES (?)",
                (guild_id,),
            )
            await self.conn.commit()
            async with self.conn.execute("SELECT * FROM dm_notification_settings WHERE guild_id = ?", (guild_id,)) as cur:
                row = await cur.fetchone()
        
        assert row is not None
        return DMNotificationSettings(
            guild_id=row["guild_id"],
            enabled=bool(row["enabled"]),
            notify_warns=bool(row["notify_warns"]),
            notify_mutes=bool(row["notify_mutes"]),
            notify_kicks=bool(row["notify_kicks"]),
            notify_bans=bool(row["notify_bans"]),
            notify_flags=bool(row["notify_flags"]),
        )

    async def update_dm_notification_settings(self, guild_id: int, **kwargs: Any) -> None:
        """Update DM notification settings."""
        if not kwargs:
            return
        
        normalized: dict[str, Any] = {}
        for key, value in kwargs.items():
            if key in {"enabled", "notify_warns", "notify_mutes", "notify_kicks", "notify_bans", "notify_flags"}:
                normalized[key] = int(bool(value))
        
        fields = ", ".join(f"{k} = ?" for k in normalized)
        params = list(normalized.values()) + [guild_id]
        await self.conn.execute(f"UPDATE dm_notification_settings SET {fields} WHERE guild_id = ?", params)
        await self.conn.commit()

    async def log_dm_notification(self, *, guild_id: int, user_id: int, action_type: str, success: bool, reason: str | None = None) -> None:
        """Log a DM notification attempt."""
        ts = utcnow().isoformat()
        await self.conn.execute(
            "INSERT INTO dm_notification_log (guild_id, user_id, action_type, timestamp, success, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, action_type, ts, int(success), reason),
        )
        await self.conn.commit()

    async def get_dm_preference(self, user_id: int, guild_id: int) -> bool:
        """Check if user wants to receive DMs."""
        async with self.conn.execute(
            "SELECT receive_dms FROM dm_preferences WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
        
        if row is None:
            return True  # Default to enabled
        
        return bool(row["receive_dms"])

    async def set_dm_preference(self, user_id: int, guild_id: int, receive_dms: bool) -> None:
        """Set user's DM preference."""
        await self.conn.execute(
            "INSERT OR REPLACE INTO dm_preferences (user_id, guild_id, receive_dms) VALUES (?, ?, ?)",
            (user_id, guild_id, int(receive_dms)),
        )
        await self.conn.commit()

    # ---------------------------------------------------------------------
    # Staff Performance Metrics
    # ---------------------------------------------------------------------

    async def record_performance_metrics(
        self,
        *,
        guild_id: int,
        user_id: int,
        period_start: str,
        period_end: str,
        warns_count: int = 0,
        mutes_count: int = 0,
        kicks_count: int = 0,
        bans_count: int = 0,
        activity_score: float = 0.0
    ) -> None:
        """Record staff performance metrics for a period."""
        total_actions = warns_count + mutes_count + kicks_count + bans_count
        await self.conn.execute(
            """
            INSERT OR REPLACE INTO staff_performance_metrics 
            (guild_id, user_id, period_start, period_end, warns_count, mutes_count, kicks_count, bans_count, total_actions, activity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, period_start, period_end, warns_count, mutes_count, kicks_count, bans_count, total_actions, activity_score),
        )
        await self.conn.commit()

    async def get_performance_metrics(self, guild_id: int, user_id: int, period_start: str) -> aiosqlite.Row | None:
        """Get performance metrics for a specific period."""
        async with self.conn.execute(
            "SELECT * FROM staff_performance_metrics WHERE guild_id = ? AND user_id = ? AND period_start = ?",
            (guild_id, user_id, period_start),
        ) as cur:
            return await cur.fetchone()

    async def get_all_staff_performance(self, guild_id: int, period_start: str) -> list[aiosqlite.Row]:
        """Get all staff performance for a specific period."""
        async with self.conn.execute(
            "SELECT * FROM staff_performance_metrics WHERE guild_id = ? AND period_start = ? ORDER BY total_actions DESC",
            (guild_id, period_start),
        ) as cur:
            return await cur.fetchall()

    # ---------------------------------------------------------------------
    # Promotion Suggestions
    # ---------------------------------------------------------------------

    async def add_promotion_suggestion(
        self,
        *,
        guild_id: int,
        user_id: int,
        suggestion_type: str,
        current_role: str | None,
        suggested_role: str | None,
        confidence: float,
        reason: str | None,
        metrics: str | None
    ) -> int:
        """Add a promotion suggestion."""
        ts = utcnow().isoformat()
        cur = await self.conn.execute(
            """
            INSERT INTO promotion_suggestions 
            (guild_id, user_id, suggestion_type, current_role, suggested_role, confidence, reason, metrics, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (guild_id, user_id, suggestion_type, current_role, suggested_role, confidence, reason, metrics, ts),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_pending_suggestions(self, guild_id: int) -> list[aiosqlite.Row]:
        """Get all pending promotion suggestions."""
        async with self.conn.execute(
            "SELECT * FROM promotion_suggestions WHERE guild_id = ? AND status = 'pending' ORDER BY timestamp DESC",
            (guild_id,),
        ) as cur:
            return await cur.fetchall()

    async def get_suggestion(self, suggestion_id: int) -> aiosqlite.Row | None:
        """Get a specific promotion suggestion."""
        async with self.conn.execute(
            "SELECT * FROM promotion_suggestions WHERE id = ?",
            (suggestion_id,),
        ) as cur:
            return await cur.fetchone()

    async def review_suggestion(self, suggestion_id: int, reviewed_by: int, status: str) -> None:
        """Review a promotion suggestion."""
        ts = utcnow().isoformat()
        await self.conn.execute(
            "UPDATE promotion_suggestions SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
            (status, reviewed_by, ts, suggestion_id),
        )
        await self.conn.commit()

    async def get_user_suggestions(self, guild_id: int, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        """Get promotion suggestions for a specific user."""
        async with self.conn.execute(
            "SELECT * FROM promotion_suggestions WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (guild_id, user_id, limit),
        ) as cur:
            return await cur.fetchall()
