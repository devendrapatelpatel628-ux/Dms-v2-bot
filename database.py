# ============================================================
#         ZENKAI DMS FORWARDING BOT - DATABASE
# ============================================================

import aiosqlite
import asyncio
import logging
from datetime import datetime
from config import DATABASE_NAME, DEFAULT_FREE_CREDITS

logger = logging.getLogger(__name__)

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def init_db():
    """Initialize all database tables."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.executescript("""

            -- ------------------------------------------------
            -- USERS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id           INTEGER UNIQUE NOT NULL,
                username        TEXT,
                first_name      TEXT,
                last_name       TEXT,
                credits         INTEGER DEFAULT 100,
                is_banned       INTEGER DEFAULT 0,
                is_vip          INTEGER DEFAULT 0,
                referred_by     INTEGER DEFAULT NULL,
                total_referred  INTEGER DEFAULT 0,
                total_scraped   INTEGER DEFAULT 0,
                total_dms_sent  INTEGER DEFAULT 0,
                joined_at       TEXT DEFAULT (datetime('now')),
                last_active     TEXT DEFAULT (datetime('now'))
            );

            -- ------------------------------------------------
            -- SESSIONS TABLE (Userbot Accounts)
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                phone           TEXT NOT NULL,
                session_string  TEXT NOT NULL,
                device_model    TEXT,
                system_version  TEXT,
                app_version     TEXT,
                lang_code       TEXT,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            -- ------------------------------------------------
            -- PROXIES TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS proxies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                host        TEXT NOT NULL,
                port        INTEGER NOT NULL,
                username    TEXT DEFAULT NULL,
                password    TEXT DEFAULT NULL,
                type        TEXT DEFAULT 'SOCKS5',
                source      TEXT,
                added_at    TEXT DEFAULT (datetime('now'))
            );

            -- ------------------------------------------------
            -- PROXY SOURCES TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS proxy_sources (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT UNIQUE NOT NULL,
                is_active       INTEGER DEFAULT 1,
                last_checked    TEXT DEFAULT NULL,
                proxies_found   INTEGER DEFAULT 0
            );

            -- ------------------------------------------------
            -- KEYS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS keys (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name        TEXT UNIQUE NOT NULL,
                credits         INTEGER NOT NULL,
                max_redeems     INTEGER NOT NULL,
                redeemed_count  INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- ------------------------------------------------
            -- KEY REDEEMS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS key_redeems (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id      INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                redeemed_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (key_id) REFERENCES keys(id),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            -- ------------------------------------------------
            -- FORCE CHANNELS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS force_channels (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      INTEGER UNIQUE NOT NULL,
                channel_name    TEXT,
                channel_link    TEXT NOT NULL,
                invite_link     TEXT DEFAULT NULL,
                is_public       INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,
                added_at        TEXT DEFAULT (datetime('now'))
            );

            -- ------------------------------------------------
            -- DM MESSAGES TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS dm_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                message_text    TEXT NOT NULL,
                message_entities TEXT DEFAULT NULL,
                type            TEXT DEFAULT 'initial',
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            );

            -- ------------------------------------------------
            -- CAMPAIGNS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS campaigns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                session_id  INTEGER NOT NULL,
                type        TEXT NOT NULL,
                status      TEXT DEFAULT 'running',
                total       INTEGER DEFAULT 0,
                sent        INTEGER DEFAULT 0,
                failed      INTEGER DEFAULT 0,
                started_at  TEXT DEFAULT (datetime('now')),
                finished_at TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(tg_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            -- ------------------------------------------------
            -- REFERRALS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS referrals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id     INTEGER NOT NULL,
                referred_id     INTEGER NOT NULL UNIQUE,
                status          TEXT DEFAULT 'pending',
                credits_awarded INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                completed_at    TEXT DEFAULT NULL,
                FOREIGN KEY (referrer_id) REFERENCES users(tg_id),
                FOREIGN KEY (referred_id) REFERENCES users(tg_id)
            );

            -- ------------------------------------------------
            -- LOGS TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                action      TEXT NOT NULL,
                detail      TEXT,
                timestamp   TEXT DEFAULT (datetime('now'))
            );

            -- ------------------------------------------------
            -- CONFIG TABLE
            -- ------------------------------------------------
            CREATE TABLE IF NOT EXISTS config (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );

        """)
        await db.commit()
        logger.info("Database initialized successfully.")
        await _insert_default_config(db)


async def _insert_default_config(db):
    """Insert default config values if not already set."""
    defaults = {
        "api_id":                   "",
        "api_hash":                 "",
        "free_credits":             "100",
        "referral_credits":         "10",
        "new_user_bonus":           "25",
        "concurrency":              "100",
        "max_accounts_per_user":    "3",
        "dm_delay_min":             "15",
        "dm_delay_max":             "55",
        "reply_delay_min":          "6",
        "reply_delay_max":          "18",
        "human_delay_min":          "0.4",
        "human_delay_max":          "2.1",
        "typing_delay_min":         "1.2",
        "typing_delay_max":         "5.8",
        "stealth_level":            "3",
        "progress_interval":        "8",
        "batch_size_min":           "80",
        "batch_size_max":           "180",
        "proxy_timeout":            "10",
        "hunter_interval":          "300",
        "force_sub_enabled":        "1",
        "refer_system_enabled":     "1",
        "auto_reply_enabled":       "1",
        "typing_sim_enabled":       "1",
        "hunter_enabled":           "1",
    }
    for key, value in defaults.items():
        await db.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
    await db.commit()


# ============================================================
# CONFIG QUERIES
# ============================================================

async def get_config(key: str) -> str:
    """Get a config value by key."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_config(key: str, value: str):
    """Set a config value by key."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        await db.commit()


async def get_all_config() -> dict:
    """Get all config values as a dictionary."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT key, value FROM config") as cursor:
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# ============================================================
# USER QUERIES
# ============================================================

async def get_user(tg_id: int) -> dict:
    """Get a user by Telegram ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_user(
    tg_id: int,
    username: str,
    first_name: str,
    last_name: str,
    referred_by: int = None
) -> dict:
    """Create a new user."""
    free_credits = int(await get_config("free_credits") or 100)
    bonus = int(await get_config("new_user_bonus") or 25)
    credits = free_credits + (bonus if referred_by else 0)

    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users
            (tg_id, username, first_name, last_name, credits, referred_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tg_id, username, first_name, last_name, credits, referred_by)
        )
        await db.commit()
    return await get_user(tg_id)


async def update_user(tg_id: int, **kwargs):
    """Update user fields dynamically."""
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [tg_id]
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            f"UPDATE users SET {fields} WHERE tg_id = ?", values
        )
        await db.commit()


async def get_all_users() -> list:
    """Get all users."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_total_users() -> int:
    """Get total user count."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0]


async def deduct_credits(tg_id: int, amount: int) -> bool:
    """Deduct credits from a user. Returns False if insufficient."""
    user = await get_user(tg_id)
    if not user or user["credits"] < amount:
        return False
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET credits = credits - ? WHERE tg_id = ?",
            (amount, tg_id)
        )
        await db.commit()
    return True


async def add_credits(tg_id: int, amount: int):
    """Add credits to a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE users SET credits = credits + ? WHERE tg_id = ?",
            (amount, tg_id)
        )
        await db.commit()


async def ban_user(tg_id: int):
    """Ban a user."""
    await update_user(tg_id, is_banned=1)


async def unban_user(tg_id: int):
    """Unban a user."""
    await update_user(tg_id, is_banned=0)


async def grant_vip(tg_id: int):
    """Grant VIP to a user."""
    await update_user(tg_id, is_vip=1)


async def revoke_vip(tg_id: int):
    """Revoke VIP from a user."""
    await update_user(tg_id, is_vip=0)


async def update_last_active(tg_id: int):
    """Update user's last active timestamp."""
    await update_user(tg_id, last_active=datetime.now().isoformat())


async def search_user(query: str) -> dict:
    """Search user by username or tg_id."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        if query.isdigit():
            async with db.execute(
                "SELECT * FROM users WHERE tg_id = ?", (int(query),)
            ) as cursor:
                row = await cursor.fetchone()
        else:
            query = query.lstrip("@")
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (query,)
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None


# ============================================================
# SESSION QUERIES
# ============================================================

async def add_session(
    user_id: int,
    phone: str,
    session_string: str,
    device_model: str,
    system_version: str,
    app_version: str,
    lang_code: str
) -> int:
    """Add a new userbot session."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO sessions
            (user_id, phone, session_string, device_model,
             system_version, app_version, lang_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, phone, session_string, device_model,
             system_version, app_version, lang_code)
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_sessions(user_id: int) -> list:
    """Get all active sessions for a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM sessions
            WHERE user_id = ? AND is_active = 1
            """,
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_session_by_id(session_id: int) -> dict:
    """Get a session by its ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def delete_session(session_id: int):
    """Soft delete a session."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "UPDATE sessions SET is_active = 0 WHERE id = ?",
            (session_id,)
        )
        await db.commit()


async def count_user_sessions(user_id: int) -> int:
    """Count active sessions for a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT COUNT(*) FROM sessions
            WHERE user_id = ? AND is_active = 1
            """,
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


# ============================================================
# PROXY QUERIES
# ============================================================

async def add_proxy(
    host: str,
    port: int,
    username: str = None,
    password: str = None,
    proxy_type: str = "SOCKS5",
    source: str = None
):
    """Add a new proxy to the pool."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO proxies
            (host, port, username, password, type, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (host, port, username, password, proxy_type, source)
        )
        await db.commit()


async def get_fresh_proxy() -> dict:
    """Get and immediately delete one proxy from the pool (burn policy)."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM proxies ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            proxy = dict(row)

        # Burn it immediately
        await db.execute(
            "DELETE FROM proxies WHERE id = ?", (proxy["id"],)
        )
        await db.commit()
        return proxy


async def delete_proxy(proxy_id: int):
    """Delete a proxy by ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM proxies WHERE id = ?", (proxy_id,)
        )
        await db.commit()


async def get_proxy_count() -> int:
    """Get total proxies in pool."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM proxies") as cursor:
            row = await cursor.fetchone()
            return row[0]


async def clear_proxies():
    """Delete all proxies from pool."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("DELETE FROM proxies")
        await db.commit()


async def get_proxy_sources() -> list:
    """Get all active proxy sources."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM proxy_sources WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def add_proxy_source(url: str):
    """Add a new proxy source URL."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO proxy_sources (url) VALUES (?)",
            (url,)
        )
        await db.commit()


async def update_proxy_source(url: str, proxies_found: int):
    """Update proxy source stats after a hunt."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            UPDATE proxy_sources
            SET last_checked = datetime('now'),
                proxies_found = ?
            WHERE url = ?
            """,
            (proxies_found, url)
        )
        await db.commit()


async def delete_proxy_source(source_id: int):
    """Delete a proxy source."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM proxy_sources WHERE id = ?", (source_id,)
        )
        await db.commit()


# ============================================================
# KEY QUERIES
# ============================================================

async def create_key(
    key_name: str,
    credits: int,
    max_redeems: int
) -> dict:
    """Create a new redemption key."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT INTO keys (key_name, credits, max_redeems)
            VALUES (?, ?, ?)
            """,
            (key_name, credits, max_redeems)
        )
        await db.commit()
    return await get_key_by_name(key_name)


async def get_key_by_name(key_name: str) -> dict:
    """Get a key by its name."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM keys WHERE key_name = ?", (key_name,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_keys() -> list:
    """Get all keys."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM keys ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def redeem_key(key_name: str, user_id: int) -> dict:
    """
    Redeem a key for a user.
    Returns dict with status and message.
    """
    key = await get_key_by_name(key_name)
    if not key:
        return {"success": False, "reason": "invalid"}
    if not key["is_active"]:
        return {"success": False, "reason": "inactive"}
    if key["redeemed_count"] >= key["max_redeems"]:
        return {"success": False, "reason": "exhausted"}

    # Check if user already redeemed this key
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT id FROM key_redeems
            WHERE key_id = ? AND user_id = ?
            """,
            (key["id"], user_id)
        ) as cursor:
            already = await cursor.fetchone()
            if already:
                return {"success": False, "reason": "already_redeemed"}

        # Record redemption
        await db.execute(
            """
            INSERT INTO key_redeems (key_id, user_id)
            VALUES (?, ?)
            """,
            (key["id"], user_id)
        )
        await db.execute(
            """
            UPDATE keys SET redeemed_count = redeemed_count + 1
            WHERE id = ?
            """,
            (key["id"],)
        )
        await db.commit()

    # Add credits to user
    await add_credits(user_id, key["credits"])
    return {"success": True, "credits": key["credits"], "key": key}


async def delete_key(key_id: int):
    """Delete a key."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("DELETE FROM keys WHERE id = ?", (key_id,))
        await db.commit()


async def get_key_redeemers(key_id: int) -> list:
    """Get all users who redeemed a specific key."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT kr.redeemed_at, u.tg_id, u.username, u.first_name
            FROM key_redeems kr
            JOIN users u ON kr.user_id = u.tg_id
            WHERE kr.key_id = ?
            ORDER BY kr.redeemed_at DESC
            """,
            (key_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ============================================================
# FORCE CHANNEL QUERIES
# ============================================================

async def add_force_channel(
    channel_id: int,
    channel_name: str,
    channel_link: str,
    invite_link: str = None,
    is_public: bool = True
):
    """Add a force subscribe channel."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO force_channels
            (channel_id, channel_name, channel_link, invite_link, is_public)
            VALUES (?, ?, ?, ?, ?)
            """,
            (channel_id, channel_name, channel_link,
             invite_link, 1 if is_public else 0)
        )
        await db.commit()


async def get_force_channels() -> list:
    """Get all active force channels."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM force_channels WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def delete_force_channel(channel_id: int):
    """Remove a force channel."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM force_channels WHERE channel_id = ?",
            (channel_id,)
        )
        await db.commit()


# ============================================================
# DM MESSAGE QUERIES
# ============================================================

async def save_dm_message(
    user_id: int,
    message_text: str,
    message_entities: str,
    msg_type: str = "initial"
):
    """Save or update a DM message for a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM dm_messages WHERE user_id = ? AND type = ?",
            (user_id, msg_type)
        )
        await db.execute(
            """
            INSERT INTO dm_messages
            (user_id, message_text, message_entities, type)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, message_text, message_entities, msg_type)
        )
        await db.commit()


async def get_dm_message(user_id: int, msg_type: str = "initial") -> dict:
    """Get a user's DM message."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM dm_messages
            WHERE user_id = ? AND type = ?
            """,
            (user_id, msg_type)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ============================================================
# CAMPAIGN QUERIES
# ============================================================

async def create_campaign(
    user_id: int,
    session_id: int,
    campaign_type: str,
    total: int
) -> int:
    """Create a new campaign and return its ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO campaigns
            (user_id, session_id, type, total)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, session_id, campaign_type, total)
        )
        await db.commit()
        return cursor.lastrowid


async def update_campaign(campaign_id: int, **kwargs):
    """Update campaign fields."""
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [campaign_id]
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            f"UPDATE campaigns SET {fields} WHERE id = ?", values
        )
        await db.commit()


async def get_campaign(campaign_id: int) -> dict:
    """Get a campaign by ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_campaigns(user_id: int) -> list:
    """Get all campaigns for a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM campaigns
            WHERE user_id = ?
            ORDER BY started_at DESC
            """,
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_dms_sent_today() -> int:
    """Get total DMs sent today across all users."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT COALESCE(SUM(sent), 0) FROM campaigns
            WHERE DATE(started_at) = DATE('now')
            """
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


# ============================================================
# REFERRAL QUERIES
# ============================================================

async def create_referral(referrer_id: int, referred_id: int):
    """Create a pending referral."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO referrals
            (referrer_id, referred_id, status)
            VALUES (?, ?, 'pending')
            """,
            (referrer_id, referred_id)
        )
        await db.commit()


async def complete_referral(referred_id: int) -> dict:
    """
    Complete a referral after force sub verification.
    Awards credits to referrer.
    Returns referral info.
    """
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM referrals
            WHERE referred_id = ? AND status = 'pending'
            """,
            (referred_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            referral = dict(row)

        credits = int(await get_config("referral_credits") or 10)

        await db.execute(
            """
            UPDATE referrals
            SET status = 'completed',
                credits_awarded = ?,
                completed_at = datetime('now')
            WHERE referred_id = ?
            """,
            (credits, referred_id)
        )
        await db.execute(
            """
            UPDATE users
            SET total_referred = total_referred + 1
            WHERE tg_id = ?
            """,
            (referral["referrer_id"],)
        )
        await db.commit()

    await add_credits(referral["referrer_id"], credits)
    return referral


async def get_referral_by_referred(referred_id: int) -> dict:
    """Get referral record by referred user ID."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM referrals WHERE referred_id = ?",
            (referred_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_referrals(referrer_id: int) -> list:
    """Get all referrals made by a user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT r.*, u.username, u.first_name
            FROM referrals r
            JOIN users u ON r.referred_id = u.tg_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
            """,
            (referrer_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_top_referrers(limit: int = 10) -> list:
    """Get top referrers leaderboard."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.tg_id, u.username, u.first_name,
                   u.total_referred,
                   COUNT(r.id) as referral_count,
                   COALESCE(SUM(r.credits_awarded), 0) as total_credits
            FROM users u
            LEFT JOIN referrals r ON u.tg_id = r.referrer_id
                AND r.status = 'completed'
            GROUP BY u.tg_id
            ORDER BY referral_count DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_referral_rank(tg_id: int) -> int:
    """Get a user's rank in the referral leaderboard."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT COUNT(*) + 1 FROM users
            WHERE total_referred > (
                SELECT total_referred FROM users WHERE tg_id = ?
            )
            """,
            (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


async def get_referrals_today() -> int:
    """Get total completed referrals today."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT COUNT(*) FROM referrals
            WHERE status = 'completed'
            AND DATE(completed_at) = DATE('now')
            """
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]


# ============================================================
# LOG QUERIES
# ============================================================

async def add_log(user_id: int, action: str, detail: str = None):
    """Add a log entry."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT INTO logs (user_id, action, detail)
            VALUES (?, ?, ?)
            """,
            (user_id, action, detail)
        )
        await db.commit()


async def get_recent_logs(limit: int = 50) -> list:
    """Get recent log entries."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT l.*, u.username FROM logs l
            LEFT JOIN users u ON l.user_id = u.tg_id
            ORDER BY l.timestamp DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_logs(user_id: int, limit: int = 20) -> list:
    """Get logs for a specific user."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM logs WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# ============================================================
# PENDING JOIN REQUESTS TRACKING
# ============================================================

async def add_pending_request(
    user_id: int,
    channel_id: int
):
    """Record a pending join request."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO pending_requests
            (user_id, channel_id)
            VALUES (?, ?)
            """,
            (user_id, channel_id)
        )
        await db.commit()


async def remove_pending_request(
    user_id: int,
    channel_id: int
):
    """Remove pending request (when approved)."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            DELETE FROM pending_requests
            WHERE user_id = ? AND channel_id = ?
            """,
            (user_id, channel_id)
        )
        await db.commit()


async def has_pending_request(
    user_id: int,
    channel_id: int
) -> bool:
    """Check if user has a pending request."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute(
            """
            SELECT 1 FROM pending_requests
            WHERE user_id = ? AND channel_id = ?
            """,
            (user_id, channel_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


# ============================================================
# STATS QUERIES
# ============================================================

async def get_bot_stats() -> dict:
    """Get overall bot statistics."""
    async with aiosqlite.connect(DATABASE_NAME) as db:
        stats = {}

        async with db.execute(
            "SELECT COUNT(*) FROM users"
        ) as cursor:
            stats["total_users"] = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_banned = 1"
        ) as cursor:
            stats["banned_users"] = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE is_vip = 1"
        ) as cursor:
            stats["vip_users"] = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM sessions WHERE is_active = 1"
        ) as cursor:
            stats["active_sessions"] = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM proxies"
        ) as cursor:
            stats["proxies_in_pool"] = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM keys WHERE is_active = 1"
        ) as cursor:
            stats["active_keys"] = (await cursor.fetchone())[0]

        async with db.execute(
            """
            SELECT COALESCE(SUM(sent), 0) FROM campaigns
            WHERE DATE(started_at) = DATE('now')
            """
        ) as cursor:
            stats["dms_today"] = (await cursor.fetchone())[0]

        async with db.execute(
            """
            SELECT COUNT(*) FROM referrals
            WHERE status = 'completed'
            AND DATE(completed_at) = DATE('now')
            """
        ) as cursor:
            stats["referrals_today"] = (await cursor.fetchone())[0]

        async with db.execute(
            """
            SELECT COUNT(*) FROM users
            WHERE DATE(joined_at) = DATE('now')
            """
        ) as cursor:
            stats["new_users_today"] = (await cursor.fetchone())[0]

        return stats