# ============================================================
#         ZENKAI DMS FORWARDING BOT - USERBOT MANAGER
# ============================================================

import asyncio
import logging
import random
from datetime import datetime
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
import socks

from config import OWNER_ID
from database import (
    add_session,
    get_user_sessions,
    get_session_by_id,
    delete_session,
    count_user_sessions,
    get_config,
    get_fresh_proxy,
    add_log,
)
from fingerprint import (
    generate_device_fingerprint,
    clear_fingerprint,
    pre_connect_simulation,
    pre_send_code_simulation,
    pre_sign_in_simulation,
    post_login_simulation,
    typing_simulation,
    read_receipt_simulation,
    micro_jitter,
    human_delay,
    serialize_fingerprint,
    deserialize_fingerprint,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONNECTION POOL
# Keeps clients connected and reuses them
# instead of reconnecting every time
# ============================================================

# Structure:
# {
#   session_id: {
#       "client":     TelegramClient,
#       "last_used":  datetime,
#       "in_use":     bool,
#   }
# }

_connection_pool: dict = {}
_pool_lock = asyncio.Lock()

# How long to keep idle connections alive (seconds)
POOL_IDLE_TIMEOUT = 300  # 5 minutes


async def _get_pooled_client(
    session_id: int
) -> TelegramClient:
    """
    Get a client from the pool if available and connected.
    Returns None if not in pool or disconnected.
    """
    async with _pool_lock:
        entry = _connection_pool.get(session_id)
        if not entry:
            return None

        client = entry["client"]

        # Check if still connected
        if not client.is_connected():
            # Remove dead connection
            _connection_pool.pop(session_id, None)
            return None

        entry["last_used"] = datetime.now()
        entry["in_use"]    = True
        return client


async def _add_to_pool(
    session_id: int,
    client: TelegramClient
):
    """Add a connected client to the pool."""
    async with _pool_lock:
        _connection_pool[session_id] = {
            "client":    client,
            "last_used": datetime.now(),
            "in_use":    True,
        }


async def _release_from_pool(session_id: int):
    """
    Mark a pooled client as no longer in use
    but keep it connected for reuse.
    """
    async with _pool_lock:
        entry = _connection_pool.get(session_id)
        if entry:
            entry["in_use"]    = False
            entry["last_used"] = datetime.now()


async def _remove_from_pool(session_id: int):
    """
    Fully disconnect and remove a client from pool.
    Used when session is deleted or invalid.
    """
    async with _pool_lock:
        entry = _connection_pool.pop(session_id, None)
        if entry:
            try:
                await entry["client"].disconnect()
            except Exception:
                pass


async def cleanup_idle_connections():
    """
    Background task that cleans up idle connections.
    Runs periodically to free resources.
    """
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute

            async with _pool_lock:
                now         = datetime.now()
                to_remove   = []

                for session_id, entry in (
                    _connection_pool.items()
                ):
                    idle_seconds = (
                        now - entry["last_used"]
                    ).total_seconds()

                    # Remove if idle too long
                    # and not currently in use
                    if (
                        idle_seconds > POOL_IDLE_TIMEOUT
                        and not entry["in_use"]
                    ):
                        to_remove.append(session_id)

                for session_id in to_remove:
                    entry = _connection_pool.pop(
                        session_id, None
                    )
                    if entry:
                        try:
                            await entry[
                                "client"
                            ].disconnect()
                        except Exception:
                            pass
                        logger.info(
                            f"Cleaned idle connection: "
                            f"session {session_id}"
                        )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(
                f"Connection pool cleanup error: {e}"
            )


# ============================================================
# LOGIN STATE MACHINE
# ============================================================

_login_states = {}


def get_login_state(user_id: int) -> dict:
    return _login_states.get(user_id)


def set_login_state(user_id: int, state: dict):
    _login_states[user_id] = state


def clear_login_state(user_id: int):
    _login_states.pop(user_id, None)


def is_in_login_flow(user_id: int) -> bool:
    return user_id in _login_states


# ============================================================
# PROXY BUILDER
# ============================================================

def build_proxy_tuple(proxy: dict):
    """
    Convert proxy dict to Telethon-compatible tuple.
    Returns None if proxy is invalid.
    """
    if not proxy:
        return None

    host = proxy.get("host")
    port = proxy.get("port")

    if not host or not port:
        return None

    try:
        proxy_type = socks.SOCKS5
        ptype = proxy.get("type", "SOCKS5").upper()
        if ptype == "SOCKS4":
            proxy_type = socks.SOCKS4
        elif ptype == "HTTP":
            proxy_type = socks.HTTP

        if proxy.get("username") and proxy.get("password"):
            return (
                proxy_type,
                host,
                int(port),
                True,
                proxy["username"],
                proxy["password"],
            )
        else:
            return (
                proxy_type,
                host,
                int(port),
            )
    except Exception:
        return None


# ============================================================
# CLIENT BUILDER
# ============================================================

async def build_client(
    fingerprint: dict,
    proxy: dict = None,
    session_string: str = None
) -> TelegramClient:
    """
    Build a TelegramClient with fingerprint.
    No timeout= param — not supported by Telethon.
    """
    api_id   = await get_config("api_id")
    api_hash = await get_config("api_hash")

    if not api_id or not api_hash:
        raise ValueError(
            "API credentials not configured. "
            "Please set them in Admin Panel."
        )

    proxy_tuple = None
    if proxy:
        proxy_tuple = build_proxy_tuple(proxy)

    session = (
        StringSession(session_string)
        if session_string
        else StringSession()
    )

    client = TelegramClient(
        session=session,
        api_id=int(api_id),
        api_hash=api_hash,
        device_model=fingerprint["device_model"],
        system_version=fingerprint["system_version"],
        app_version=fingerprint["app_version"],
        lang_code=fingerprint["lang_code"],
        system_lang_code=fingerprint["system_lang_code"],
        proxy=proxy_tuple,
        flood_sleep_threshold=fingerprint[
            "flood_sleep_threshold"
        ],
        receive_updates=True,
        connection_retries=fingerprint["connection_retries"],
        retry_delay=fingerprint["retry_delay"],
        auto_reconnect=True,
    )

    return client


# ============================================================
# CONNECT WITH FALLBACK
# Try proxy → fall back to direct if proxy fails
# ============================================================

async def connect_with_fallback(
    fingerprint: dict,
    session_string: str = None,
    use_proxy: bool = True,
) -> TelegramClient:
    """
    Try proxy connection first.
    If proxy fails → connect directly.
    This ensures connection ALWAYS works.
    """

    # ── Attempt 1: With proxy ────────────────────────────
    if use_proxy:
        proxy = await get_fresh_proxy()
        if proxy:
            try:
                client = await build_client(
                    fingerprint=fingerprint,
                    proxy=proxy,
                    session_string=session_string,
                )
                await asyncio.wait_for(
                    client.connect(),
                    timeout=15.0
                )
                logger.info(
                    "Connected with proxy."
                )
                return client

            except asyncio.TimeoutError:
                logger.warning(
                    "Proxy timed out. "
                    "Trying direct connection."
                )
                try:
                    await client.disconnect()
                except Exception:
                    pass

            except Exception as e:
                logger.warning(
                    f"Proxy failed: {e}. "
                    f"Trying direct connection."
                )
                try:
                    await client.disconnect()
                except Exception:
                    pass

    # ── Attempt 2: Direct connection ─────────────────────
    logger.info("Connecting directly (no proxy)...")

    client = await build_client(
        fingerprint=fingerprint,
        proxy=None,
        session_string=session_string,
    )

    await asyncio.wait_for(
        client.connect(),
        timeout=30.0
    )

    logger.info("Connected directly.")
    return client


# ============================================================
# SESSION LOADER — WITH POOL
# FIX: Reuses existing connection if available
# ============================================================

async def load_client(
    session_id: int,
    use_proxy: bool = True
) -> TelegramClient:
    """
    Load a session client.
    Reuses pooled connection if available and connected.
    Only creates new connection if needed.
    Much faster for repeated operations.
    """

    # ── Check pool first ─────────────────────────────────
    pooled = await _get_pooled_client(session_id)
    if pooled:
        logger.debug(
            f"Reusing pooled connection "
            f"for session {session_id}"
        )
        return pooled

    # ── Pool miss — create new connection ────────────────
    logger.info(
        f"Creating new connection "
        f"for session {session_id}"
    )

    session_data = await get_session_by_id(session_id)
    if not session_data:
        raise ValueError(
            f"Session {session_id} not found."
        )

    fingerprint = _build_fingerprint(session_data)

    client = await connect_with_fallback(
        fingerprint=fingerprint,
        session_string=session_data["session_string"],
        use_proxy=use_proxy,
    )

    # Verify session is still valid
    if not await client.is_user_authorized():
        await client.disconnect()
        raise ValueError(
            f"Session {session_id} is no longer "
            f"authorized. Please login again."
        )

    # Add to pool for reuse
    await _add_to_pool(session_id, client)

    return client


def _build_fingerprint(session_data: dict) -> dict:
    """Build fingerprint dict from session DB data."""
    return {
        "device_model":          session_data["device_model"],
        "system_version":        session_data["system_version"],
        "app_version":           session_data["app_version"],
        "lang_code":             session_data["lang_code"],
        "system_lang_code":      random.choice([
            "en-US", "en-GB", "hi-IN", "ru-RU"
        ]),
        "flood_sleep_threshold": random.randint(20, 120),
        "connection_retries":    random.randint(3, 8),
        "retry_delay":           round(
            random.uniform(1.0, 5.0), 3
        ),
        "pre_connect_delay":     round(
            random.uniform(0.3, 1.8), 3
        ),
        "pre_send_code_delay":   round(
            random.uniform(1.2, 4.5), 3
        ),
        "pre_sign_in_delay":     round(
            random.uniform(2.1, 6.3), 3
        ),
        "api_call_delay":        round(
            random.uniform(0.4, 2.2), 3
        ),
        "micro_jitter":          round(
            random.uniform(0.1, 0.9), 3
        ),
        "receive_delay":         round(
            random.uniform(0.5, 2.5), 3
        ),
        "post_login_delay":      round(
            random.uniform(3.0, 8.0), 3
        ),
        "online_pattern":        random.choice([
            "active", "semi_active", "passive"
        ]),
        "typing_delay_min":      round(
            random.uniform(1.0, 2.5), 3
        ),
        "typing_delay_max":      round(
            random.uniform(3.0, 6.5), 3
        ),
        "read_receipt_delay":    round(
            random.uniform(0.5, 3.0), 3
        ),
        "message_send_delay":    round(
            random.uniform(0.3, 1.5), 3
        ),
        "unique_seed":           random.randint(
            100000, 999999
        ),
        "generated_at":          datetime.now().isoformat(),
        "user_id":               None,
    }


# ============================================================
# RELEASE CLIENT (Instead of disconnect)
# ============================================================

async def release_client(
    session_id: int,
    client: TelegramClient
):
    """
    Release a client back to the pool.
    Call this INSTEAD of client.disconnect()
    so the connection stays alive for reuse.
    """
    await _release_from_pool(session_id)
    logger.debug(
        f"Released session {session_id} back to pool."
    )


# ============================================================
# LOGIN FLOW - STEP 1: INITIATE
# ============================================================

async def initiate_login(user_id: int) -> dict:
    """
    Step 1: Generate fingerprint, connect.
    Login uses a temporary client (not pooled).
    """
    try:
        fingerprint = generate_device_fingerprint(user_id)
        await pre_connect_simulation(fingerprint)

        client = await connect_with_fallback(
            fingerprint=fingerprint,
            session_string=None,
            use_proxy=True,
        )

        await micro_jitter(0.5)

        set_login_state(user_id, {
            "state":           "awaiting_phone",
            "phone":           None,
            "client":          client,
            "fingerprint":     fingerprint,
            "phone_code_hash": None,
        })

        await add_log(
            user_id,
            "login_initiated",
            "Login flow started"
        )

        return {
            "success": True,
            "message": "Connected. Send your phone number."
        }

    except asyncio.TimeoutError:
        clear_login_state(user_id)
        return {
            "success": False,
            "error": (
                "Connection timed out.\n"
                "Please try again."
            )
        }

    except Exception as e:
        logger.error(
            f"Login initiation failed for {user_id}: {e}"
        )
        clear_login_state(user_id)
        return {
            "success": False,
            "error":   str(e)
        }


# ============================================================
# LOGIN FLOW - STEP 2: PHONE NUMBER
# ============================================================

async def submit_phone(
    user_id: int,
    phone: str
) -> dict:
    state = get_login_state(user_id)
    if not state or state["state"] != "awaiting_phone":
        return {
            "success": False,
            "error":   "Invalid state. Please start again."
        }

    client      = state["client"]
    fingerprint = state["fingerprint"]

    try:
        await pre_send_code_simulation(fingerprint)
        await micro_jitter(0.4)

        phone = (
            phone.strip()
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        if not phone.startswith("+"):
            phone = "+" + phone

        result = await client.send_code_request(phone)
        await micro_jitter(0.6)

        state["phone"]           = phone
        state["phone_code_hash"] = result.phone_code_hash
        state["state"]           = "awaiting_code"
        set_login_state(user_id, state)

        await add_log(
            user_id,
            "phone_submitted",
            f"Phone: {phone}"
        )

        return {
            "success": True,
            "message": "Code sent!"
        }

    except errors.PhoneNumberInvalidError:
        return {
            "success": False,
            "error": (
                "Invalid phone number.\n"
                "Format: +919876543210"
            )
        }
    except errors.PhoneNumberBannedError:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error":   "This number is banned from Telegram."
        }
    except errors.FloodWaitError as e:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error":   f"Too many attempts. Wait {e.seconds}s."
        }
    except errors.ApiIdInvalidError:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error": (
                "Invalid API credentials.\n"
                "Owner must fix API ID and Hash\n"
                "in the Admin Panel."
            )
        }
    except Exception as e:
        await _cleanup_login(user_id)
        logger.error(
            f"Phone submission failed for {user_id}: {e}"
        )
        return {
            "success": False,
            "error":   f"Failed: {str(e)}"
        }


# ============================================================
# LOGIN FLOW - STEP 3: VERIFICATION CODE
# ============================================================

async def submit_code(
    user_id: int,
    code: str
) -> dict:
    state = get_login_state(user_id)
    if not state or state["state"] != "awaiting_code":
        return {
            "success": False,
            "error":   "Invalid state. Please start again."
        }

    client          = state["client"]
    fingerprint     = state["fingerprint"]
    phone           = state["phone"]
    phone_code_hash = state["phone_code_hash"]

    try:
        await pre_sign_in_simulation(fingerprint)
        await micro_jitter(0.5)

        code = (
            code.strip()
            .replace(" ", "")
            .replace("-", "")
            .replace(".", "")
        )

        await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=phone_code_hash,
        )

        await micro_jitter(0.7)
        await post_login_simulation(fingerprint)

        session_id = await _save_session(
            user_id, client, fingerprint, phone
        )

        # Add to pool after successful login
        await _add_to_pool(session_id, client)

        clear_login_state(user_id)

        await add_log(
            user_id,
            "login_success",
            f"Phone: {phone}"
        )

        return {
            "success":    True,
            "needs_2fa":  False,
            "session_id": session_id,
            "phone":      phone,
        }

    except errors.SessionPasswordNeededError:
        state["state"] = "awaiting_2fa"
        set_login_state(user_id, state)
        return {
            "success":   True,
            "needs_2fa": True,
        }

    except errors.PhoneCodeInvalidError:
        return {
            "success": False,
            "error":   "Invalid code. Please try again."
        }

    except errors.PhoneCodeExpiredError:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error":   "Code expired. Please start again."
        }

    except errors.FloodWaitError as e:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error":   f"Too many attempts. Wait {e.seconds}s."
        }

    except Exception as e:
        await _cleanup_login(user_id)
        logger.error(
            f"Code submission failed for {user_id}: {e}"
        )
        return {
            "success": False,
            "error":   f"Sign in failed: {str(e)}"
        }


# ============================================================
# LOGIN FLOW - STEP 4: 2FA PASSWORD
# ============================================================

async def submit_2fa(
    user_id: int,
    password: str
) -> dict:
    state = get_login_state(user_id)
    if not state or state["state"] != "awaiting_2fa":
        return {
            "success": False,
            "error":   "Invalid state. Please start again."
        }

    client      = state["client"]
    fingerprint = state["fingerprint"]
    phone       = state["phone"]

    try:
        await typing_simulation(fingerprint)
        await micro_jitter(0.6)

        await client.sign_in(password=password)
        await micro_jitter(0.8)
        await post_login_simulation(fingerprint)

        session_id = await _save_session(
            user_id, client, fingerprint, phone
        )

        # Add to pool after successful login
        await _add_to_pool(session_id, client)

        clear_login_state(user_id)

        await add_log(
            user_id,
            "login_2fa_success",
            f"Phone: {phone}"
        )

        return {
            "success":    True,
            "session_id": session_id,
            "phone":      phone,
        }

    except errors.PasswordHashInvalidError:
        return {
            "success": False,
            "error":   "Wrong password. Please try again."
        }

    except errors.FloodWaitError as e:
        await _cleanup_login(user_id)
        return {
            "success": False,
            "error":   f"Too many attempts. Wait {e.seconds}s."
        }

    except Exception as e:
        await _cleanup_login(user_id)
        logger.error(f"2FA failed for {user_id}: {e}")
        return {
            "success": False,
            "error":   f"2FA failed: {str(e)}"
        }


# ============================================================
# SESSION SAVER
# ============================================================

async def _save_session(
    user_id: int,
    client: TelegramClient,
    fingerprint: dict,
    phone: str,
) -> int:
    session_string = client.session.save()

    session_id = await add_session(
        user_id=user_id,
        phone=phone,
        session_string=session_string,
        device_model=fingerprint["device_model"],
        system_version=fingerprint["system_version"],
        app_version=fingerprint["app_version"],
        lang_code=fingerprint["lang_code"],
    )

    return session_id


# ============================================================
# SESSION REMOVER
# ============================================================

async def remove_session(
    user_id: int,
    session_id: int
) -> dict:
    try:
        session_data = await get_session_by_id(session_id)
        if not session_data:
            return {
                "success": False,
                "error":   "Session not found."
            }

        if session_data["user_id"] != user_id:
            return {
                "success": False,
                "error":   "Unauthorized."
            }

        # Try graceful logout
        try:
            client = await load_client(
                session_id,
                use_proxy=False
            )
            await client.log_out()
        except Exception as e:
            logger.warning(
                f"Graceful logout failed: {e}. "
                f"Deleting from DB anyway."
            )

        # Remove from pool completely
        await _remove_from_pool(session_id)

        await delete_session(session_id)
        clear_fingerprint(user_id)

        await add_log(
            user_id,
            "session_removed",
            f"Session ID: {session_id}"
        )

        return {
            "success": True,
            "phone":   session_data["phone"]
        }

    except Exception as e:
        logger.error(f"Remove session failed: {e}")
        return {
            "success": False,
            "error":   str(e)
        }


# ============================================================
# GET ME
# ============================================================

async def get_me(session_id: int) -> dict:
    try:
        client = await load_client(session_id)
        await micro_jitter(0.4)
        me     = await client.get_me()
        # FIX: release instead of disconnect
        await release_client(session_id, client)

        return {
            "success":    True,
            "id":         me.id,
            "first_name": me.first_name or "",
            "last_name":  me.last_name or "",
            "username":   me.username or "",
            "phone":      me.phone or "",
        }

    except Exception as e:
        logger.error(
            f"get_me failed for session {session_id}: {e}"
        )
        return {
            "success": False,
            "error":   str(e)
        }


# ============================================================
# RESOLVE ENTITY
# ============================================================

async def resolve_entity(
    session_id: int,
    target: str
) -> dict:
    try:
        client = await load_client(session_id)
        await micro_jitter(0.5)

        entity = await client.get_entity(target)
        await micro_jitter(0.4)

        result = {
            "success":  True,
            "id":       entity.id,
            "title":    getattr(entity, "title", ""),
            "username": getattr(entity, "username", ""),
            "type":     type(entity).__name__,
        }

        # FIX: release instead of disconnect
        await release_client(session_id, client)
        return result

    except errors.UsernameNotOccupiedError:
        return {
            "success": False,
            "error":   "Username not found."
        }
    except errors.ChannelPrivateError:
        return {
            "success": False,
            "error":   "Channel is private."
        }
    except Exception as e:
        logger.error(f"resolve_entity failed: {e}")
        return {
            "success": False,
            "error":   str(e)
        }


# ============================================================
# CHECK ADMIN STATUS
# ============================================================

async def check_admin_status(
    session_id: int,
    channel_entity
) -> bool:
    try:
        client = await load_client(session_id)
        await micro_jitter(0.4)

        me = await client.get_me()
        await micro_jitter(0.3)

        is_admin = False
        async for admin in client.iter_participants(
            channel_entity,
            filter=types.ChannelParticipantsAdmins()
        ):
            if admin.id == me.id:
                is_admin = True
                break

        # FIX: release instead of disconnect
        await release_client(session_id, client)
        return is_admin

    except Exception as e:
        logger.error(f"check_admin_status failed: {e}")
        return False


# ============================================================
# CLEANUP HELPER
# ============================================================

async def _cleanup_login(user_id: int):
    """Clean up a failed login attempt."""
    state = get_login_state(user_id)
    if state and state.get("client"):
        try:
            await state["client"].disconnect()
        except Exception:
            pass
    clear_login_state(user_id)
    clear_fingerprint(user_id)


# ============================================================
# GET SESSIONS INFO
# ============================================================

async def get_sessions_info(user_id: int) -> list:
    sessions = await get_user_sessions(user_id)
    result   = []

    for session in sessions:
        result.append({
            "id":         session["id"],
            "phone":      session["phone"],
            "device":     session["device_model"],
            "created_at": session["created_at"],
            "is_active":  session["is_active"],
        })

    return result


# ============================================================
# POOL STATUS (for admin panel)
# ============================================================

def get_pool_status() -> dict:
    """Get current connection pool status."""
    total    = len(_connection_pool)
    in_use   = sum(
        1 for e in _connection_pool.values()
        if e["in_use"]
    )
    idle     = total - in_use

    return {
        "total":  total,
        "in_use": in_use,
        "idle":   idle,
    }


# ============================================================
# EXPORT ALL
# ============================================================

__all__ = [
    "get_login_state",
    "set_login_state",
    "clear_login_state",
    "is_in_login_flow",
    "build_proxy_tuple",
    "build_client",
    "connect_with_fallback",
    "load_client",
    "release_client",
    "cleanup_idle_connections",
    "get_pool_status",
    "initiate_login",
    "submit_phone",
    "submit_code",
    "submit_2fa",
    "remove_session",
    "get_me",
    "resolve_entity",
    "check_admin_status",
    "get_sessions_info",
]