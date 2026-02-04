"""
Luna Bot Database Layer
Handles all database operations using aiosqlite for async safety.
"""

import aiosqlite
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import (
    DATABASE_PATH,
    TABLE_GUILD_SETTINGS,
    TABLE_AI_SETTINGS,
    TABLE_HELPER_ROLE,
    TABLE_MUTE,
    TABLE_WARN,
    TABLE_BAN,
    TABLE_STAFF_FLAGS,
    TABLE_TAGS,
    TABLE_REMINDERS,
    TABLE_DM_LOGS,
    TABLE_BLACKLIST,
    TABLE_POLLS,
    TABLE_SHIFTS,
    TABLE_SHIFT_CONFIGS,
    TABLE_QUOTA_TRACKING,
    TABLE_AI_TARGETS,
    TABLE_ACTIVITY_LOGS,
    MAX_STAFF_FLAGS,
    SHIFT_GMT_OFFSET,
)

# Database lock for concurrent access
db_lock = asyncio.Lock()


async def get_db_connection() -> aiosqlite.Connection:
    """Get a database connection."""
    return await aiosqlite.connect(DATABASE_PATH)


async def init_database() -> None:
    """Initialize all database tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Guild Settings
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_GUILD_SETTINGS} (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT ',',
                modlog_channel_id INTEGER,
                join_leave_channel_id INTEGER,
                member_role_id INTEGER,
                staff_role_id INTEGER,
                admin_role_id INTEGER,
                mod_channel_id INTEGER,
                shift_channel_id INTEGER,
                helper_button_channel_id INTEGER,
                lock_categories TEXT DEFAULT '[]'
            )
        """)

        # AI Settings
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_AI_SETTINGS} (
                guild_id INTEGER PRIMARY KEY,
                ai_enabled INTEGER DEFAULT 1,
                moderation_enabled INTEGER DEFAULT 1,
                dm_response_enabled INTEGER DEFAULT 1,
                personality TEXT DEFAULT 'helpful'
            )
        """)

        # Helper Role
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_HELPER_ROLE} (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER NOT NULL
            )
        """)

        # Mutes
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_MUTE} (
                user_id INTEGER,
                guild_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                expires_at INTEGER,
                created_at INTEGER,
                active INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Warns
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_WARN} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at INTEGER
            )
        """)

        # Bans
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_BAN} (
                user_id INTEGER,
                guild_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at INTEGER
            )
        """)

        # Staff Flags
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_STAFF_FLAGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                flagger_id INTEGER,
                reason TEXT,
                created_at INTEGER,
                expires_at INTEGER,
                active INTEGER DEFAULT 1
            )
        """)

        # Tags
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_TAGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                creator_id INTEGER,
                created_at INTEGER,
                UNIQUE(guild_id, category, title)
            )
        """)

        # Reminders
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_REMINDERS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                reminder_text TEXT,
                expires_at INTEGER,
                created_at INTEGER
            )
        """)

        # DM Logs
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_DM_LOGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_id INTEGER,
                content TEXT,
                timestamp INTEGER,
                has_attachment INTEGER DEFAULT 0
            )
        """)

        # Blacklist
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_BLACKLIST} (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                created_at INTEGER
            )
        """)

        # Polls
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_POLLS} (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                channel_id INTEGER,
                author_id INTEGER,
                title TEXT,
                question TEXT,
                options TEXT,
                role_id INTEGER,
                active INTEGER DEFAULT 1
            )
        """)

        # Shifts
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SHIFTS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                shift_type TEXT,
                start_ts_utc INTEGER,
                start_ts_gmt8 INTEGER,
                end_ts_utc INTEGER,
                end_ts_gmt8 INTEGER,
                break_duration INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at INTEGER
            )
        """)

        # Shift Configs
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SHIFT_CONFIGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                role_id INTEGER,
                shift_type TEXT,
                afk_timeout INTEGER,
                weekly_quota INTEGER,
                UNIQUE(guild_id, role_id, shift_type)
            )
        """)

        # Quota Tracking
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_QUOTA_TRACKING} (
                user_id INTEGER,
                guild_id INTEGER,
                shift_type TEXT,
                week_gmt8 TEXT,
                hours_logged REAL DEFAULT 0,
                quota_met INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, shift_type, week_gmt8)
            )
        """)

        # AI Targets
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_AI_TARGETS} (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                targeted_by_id INTEGER,
                timestamp INTEGER,
                active INTEGER DEFAULT 1
            )
        """)

        # Activity Logs
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_ACTIVITY_LOGS} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                timestamp INTEGER
            )
        """)

        await db.commit()


async def get_guild_setting(guild_id: int, setting: str) -> Optional[Any]:
    """Get a specific guild setting."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT {setting} FROM {TABLE_GUILD_SETTINGS} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def set_guild_setting(guild_id: int, setting: str, value: Any) -> None:
    """Set a specific guild setting."""
    async with db_lock:
        async with await get_db_connection() as db:
            # Check if guild exists
            async with db.execute(
                f"SELECT guild_id FROM {TABLE_GUILD_SETTINGS} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()

            if exists:
                await db.execute(
                    f"UPDATE {TABLE_GUILD_SETTINGS} SET {setting} = ? WHERE guild_id = ?",
                    (value, guild_id)
                )
            else:
                await db.execute(
                    f"INSERT INTO {TABLE_GUILD_SETTINGS} (guild_id, {setting}) VALUES (?, ?)",
                    (guild_id, value)
                )
            await db.commit()


async def get_ai_setting(guild_id: int, setting: str) -> Optional[Any]:
    """Get a specific AI setting."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT {setting} FROM {TABLE_AI_SETTINGS} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def set_ai_setting(guild_id: int, setting: str, value: Any) -> None:
    """Set a specific AI setting."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT guild_id FROM {TABLE_AI_SETTINGS} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                exists = await cursor.fetchone()

            if exists:
                await db.execute(
                    f"UPDATE {TABLE_AI_SETTINGS} SET {setting} = ? WHERE guild_id = ?",
                    (value, guild_id)
                )
            else:
                await db.execute(
                    f"INSERT INTO {TABLE_AI_SETTINGS} (guild_id, {setting}) VALUES (?, ?)",
                    (guild_id, value)
                )
            await db.commit()


async def get_helper_role(guild_id: int) -> Optional[int]:
    """Get helper role ID for a guild."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT role_id FROM {TABLE_HELPER_ROLE} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def set_helper_role(guild_id: int, role_id: int) -> None:
    """Set helper role for a guild."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {TABLE_HELPER_ROLE} (guild_id, role_id) VALUES (?, ?)",
                (guild_id, role_id)
            )
            await db.commit()


async def add_mute(user_id: int, guild_id: int, moderator_id: int, reason: str, expires_at: int) -> None:
    """Add a mute record."""
    created_at = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {TABLE_MUTE} (user_id, guild_id, moderator_id, reason, expires_at, created_at, active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (user_id, guild_id, moderator_id, reason, expires_at, created_at)
            )
            await db.commit()


async def get_active_mute(user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
    """Get active mute for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_MUTE} WHERE user_id = ? AND guild_id = ? AND active = 1",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None


async def remove_mute(user_id: int, guild_id: int) -> None:
    """Deactivate a mute."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"UPDATE {TABLE_MUTE} SET active = 0 WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            await db.commit()


async def add_warn(user_id: int, guild_id: int, moderator_id: int, reason: str) -> int:
    """Add a warn record and return the warn ID."""
    created_at = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"INSERT INTO {TABLE_WARN} (user_id, guild_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, moderator_id, reason, created_at)
            )
            await db.commit()
            return cursor.lastrowid


async def get_user_warns(user_id: int, guild_id: int) -> List[Dict[str, Any]]:
    """Get all warns for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_WARN} WHERE user_id = ? AND guild_id = ? ORDER BY created_at DESC",
                (user_id, guild_id)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def get_warn_count(user_id: int, guild_id: int) -> int:
    """Get warn count for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT COUNT(*) FROM {TABLE_WARN} WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0


async def add_staff_flag(user_id: int, guild_id: int, flagger_id: int, reason: str, expires_at: int) -> int:
    """Add a staff flag and return the flag ID."""
    created_at = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"INSERT INTO {TABLE_STAFF_FLAGS} (user_id, guild_id, flagger_id, reason, created_at, expires_at, active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (user_id, guild_id, flagger_id, reason, created_at, expires_at)
            )
            await db.commit()
            return cursor.lastrowid


async def get_active_flags(user_id: int, guild_id: int) -> int:
    """Get active flag count for a user."""
    now = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT COUNT(*) FROM {TABLE_STAFF_FLAGS} WHERE user_id = ? AND guild_id = ? AND active = 1 AND expires_at > ?",
                (user_id, guild_id, now)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0


async def get_all_staff_flags(guild_id: int) -> List[Dict[str, Any]]:
    """Get all staff with active flags."""
    now = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT user_id, COUNT(*) as flag_count FROM {TABLE_STAFF_FLAGS} WHERE guild_id = ? AND active = 1 AND expires_at > ? GROUP BY user_id",
                (guild_id, now)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def clear_staff_flags(user_id: int, guild_id: int) -> None:
    """Clear all active flags for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"UPDATE {TABLE_STAFF_FLAGS} SET active = 0 WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            await db.commit()


async def create_tag(guild_id: int, category: str, title: str, description: str, creator_id: int) -> int:
    """Create a tag and return its ID."""
    created_at = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"INSERT INTO {TABLE_TAGS} (guild_id, category, title, description, creator_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, category, title, description, creator_id, created_at)
            )
            await db.commit()
            return cursor.lastrowid


async def get_tag(guild_id: int, category: str, title: str) -> Optional[Dict[str, Any]]:
    """Get a specific tag."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_TAGS} WHERE guild_id = ? AND category = ? AND title = ?",
                (guild_id, category, title)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None


async def search_tags(guild_id: int, category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for tags with optional category and search filter."""
    async with db_lock:
        async with await get_db_connection() as db:
            query = f"SELECT * FROM {TABLE_TAGS} WHERE guild_id = ?"
            params = [guild_id]

            if category:
                query += " AND category = ?"
                params.append(category)

            if search:
                query += " AND (title LIKE ? OR description LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY category, title"

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def delete_tag(guild_id: int, category: str, title: str) -> bool:
    """Delete a tag. Returns True if deleted."""
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"DELETE FROM {TABLE_TAGS} WHERE guild_id = ? AND category = ? AND title = ?",
                (guild_id, category, title)
            )
            await db.commit()
            return cursor.rowcount > 0


async def edit_tag(guild_id: int, category: str, title: str, new_description: str) -> bool:
    """Edit a tag description. Returns True if updated."""
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"UPDATE {TABLE_TAGS} SET description = ? WHERE guild_id = ? AND category = ? AND title = ?",
                (new_description, guild_id, category, title)
            )
            await db.commit()
            return cursor.rowcount > 0


async def create_reminder(user_id: int, guild_id: int, reminder_text: str, expires_at: int) -> int:
    """Create a reminder and return its ID."""
    created_at = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"INSERT INTO {TABLE_REMINDERS} (user_id, guild_id, reminder_text, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, reminder_text, expires_at, created_at)
            )
            await db.commit()
            return cursor.lastrowid


async def get_user_reminders(user_id: int) -> List[Dict[str, Any]]:
    """Get all active reminders for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_REMINDERS} WHERE user_id = ? ORDER BY expires_at ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Delete a reminder. Returns True if deleted."""
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"DELETE FROM {TABLE_REMINDERS} WHERE id = ? AND user_id = ?",
                (reminder_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0


async def get_expired_reminders() -> List[Dict[str, Any]]:
    """Get all expired reminders."""
    now = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_REMINDERS} WHERE expires_at <= ?",
                (now,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def remove_reminder(reminder_id: int) -> None:
    """Remove a reminder after it's sent."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"DELETE FROM {TABLE_REMINDERS} WHERE id = ?",
                (reminder_id,)
            )
            await db.commit()


async def start_shift(user_id: int, guild_id: int, shift_type: str) -> int:
    """Start a shift and return its ID."""
    now_utc = int(datetime.utcnow().timestamp())
    # Convert to GMT+8
    gmt8_tz = ZoneInfo("Asia/Singapore")
    now_gmt8 = datetime.now(gmt8_tz)
    now_gmt8_ts = int(now_gmt8.timestamp())
    
    created_at = now_utc
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"INSERT INTO {TABLE_SHIFTS} (user_id, guild_id, shift_type, start_ts_utc, start_ts_gmt8, created_at, status) VALUES (?, ?, ?, ?, ?, ?, 'active')",
                (user_id, guild_id, shift_type, now_utc, now_gmt8_ts, created_at)
            )
            await db.commit()
            return cursor.lastrowid


async def get_active_shift(user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
    """Get active shift for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_SHIFTS} WHERE user_id = ? AND guild_id = ? AND status = 'active'",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None


async def pause_shift(user_id: int, guild_id: int) -> bool:
    """Pause a shift (break). Returns True if updated."""
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"UPDATE {TABLE_SHIFTS} SET status = 'break' WHERE user_id = ? AND guild_id = ? AND status = 'active'",
                (user_id, guild_id)
            )
            await db.commit()
            return cursor.rowcount > 0


async def resume_shift(user_id: int, guild_id: int, break_duration: int) -> bool:
    """Resume a shift from break. Returns True if updated."""
    async with db_lock:
        async with await get_db_connection() as db:
            cursor = await db.execute(
                f"UPDATE {TABLE_SHIFTS} SET status = 'active', break_duration = break_duration + COALESCE(break_duration, 0) WHERE user_id = ? AND guild_id = ? AND status = 'break'",
                (user_id, guild_id)
            )
            await db.commit()
            return cursor.rowcount > 0


async def end_shift(user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
    """End a shift and return the record with calculated duration."""
    shift = await get_active_shift(user_id, guild_id)
    if not shift:
        return None
    
    now_utc = int(datetime.utcnow().timestamp())
    gmt8_tz = ZoneInfo("Asia/Singapore")
    now_gmt8_ts = int(datetime.now(gmt8_tz).timestamp())
    
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"UPDATE {TABLE_SHIFTS} SET status = 'ended', end_ts_utc = ?, end_ts_gmt8 = ? WHERE id = ?",
                (now_utc, now_gmt8_ts, shift['id'])
            )
            await db.commit()
            
            # Get the updated shift
            async with db.execute(
                f"SELECT * FROM {TABLE_SHIFTS} WHERE id = ?",
                (shift['id'],)
            ) as cursor:
                row = await cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))


async def get_shift_history(user_id: int, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get shift history for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_SHIFTS} WHERE user_id = ? AND guild_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, guild_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def get_weekly_leaderboard(guild_id: int, shift_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get weekly leaderboard for shifts."""
    gmt8_tz = ZoneInfo("Asia/Singapore")
    now = datetime.now(gmt8_tz)
    week_start = now - timedelta(days=now.weekday())  # Monday
    week_start_ts = int(week_start.timestamp())
    
    async with db_lock:
        async with await get_db_connection() as db:
            query = f"""
                SELECT user_id, 
                       SUM(CASE 
                           WHEN end_ts_gmt8 IS NULL 
                           THEN ? - start_ts_gmt8 
                           ELSE end_ts_gmt8 - start_ts_gmt8 
                       END - COALESCE(break_duration, 0) as total_seconds
                FROM {TABLE_SHIFTS} 
                WHERE guild_id = ? AND status != 'active' AND created_at >= ?
            """
            params = [int(now.timestamp()), guild_id, week_start_ts]
            
            if shift_type:
                query += " AND shift_type = ?"
                params.append(shift_type)
            
            query += " GROUP BY user_id ORDER BY total_seconds DESC"
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def get_shift_config(guild_id: int, role_id: int, shift_type: str) -> Optional[Dict[str, Any]]:
    """Get shift config for a role and shift type."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_SHIFT_CONFIGS} WHERE guild_id = ? AND role_id = ? AND shift_type = ?",
                (guild_id, role_id, shift_type)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None


async def set_shift_config(guild_id: int, role_id: int, shift_type: str, afk_timeout: int, weekly_quota: int) -> None:
    """Set shift config for a role and shift type."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {TABLE_SHIFT_CONFIGS} (guild_id, role_id, shift_type, afk_timeout, weekly_quota) VALUES (?, ?, ?, ?, ?)",
                (guild_id, role_id, shift_type, afk_timeout, weekly_quota)
            )
            await db.commit()


async def get_all_shift_configs(guild_id: int) -> List[Dict[str, Any]]:
    """Get all shift configs for a guild."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_SHIFT_CONFIGS} WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def add_ai_target(user_id: int, guild_id: int, targeted_by_id: int) -> None:
    """Add or update an AI target."""
    timestamp = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"INSERT OR REPLACE INTO {TABLE_AI_TARGETS} (user_id, guild_id, targeted_by_id, timestamp, active) VALUES (?, ?, ?, ?, 1)",
                (user_id, guild_id, targeted_by_id, timestamp)
            )
            await db.commit()


async def remove_ai_target(user_id: int, guild_id: int) -> None:
    """Remove an AI target."""
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"UPDATE {TABLE_AI_TARGETS} SET active = 0 WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            await db.commit()


async def get_active_ai_targets(guild_id: int) -> List[Dict[str, Any]]:
    """Get all active AI targets."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT * FROM {TABLE_AI_TARGETS} WHERE guild_id = ? AND active = 1",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]


async def log_activity(user_id: int, guild_id: int, channel_id: int) -> None:
    """Log user activity for AFK tracking."""
    timestamp = int(datetime.utcnow().timestamp())
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"INSERT INTO {TABLE_ACTIVITY_LOGS} (user_id, guild_id, channel_id, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, channel_id, timestamp)
            )
            await db.commit()


async def get_last_activity(user_id: int, guild_id: int) -> Optional[int]:
    """Get last activity timestamp for a user."""
    async with db_lock:
        async with await get_db_connection() as db:
            async with db.execute(
                f"SELECT timestamp FROM {TABLE_ACTIVITY_LOGS} WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC LIMIT 1",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def cleanup_old_activity(older_than: int) -> None:
    """Clean up activity logs older than specified seconds."""
    cutoff = int(datetime.utcnow().timestamp()) - older_than
    async with db_lock:
        async with await get_db_connection() as db:
            await db.execute(
                f"DELETE FROM {TABLE_ACTIVITY_LOGS} WHERE timestamp < ?",
                (cutoff,)
            )
            await db.commit()
