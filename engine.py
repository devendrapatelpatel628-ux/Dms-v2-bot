# ============================================================
#         ZENKAI DMS FORWARDING BOT - ENGINE
# ============================================================

import asyncio
import logging
import random
import aiohttp
import json
import re
from datetime import datetime
from telethon import errors, functions, types
from telethon.tl.functions.channels import (
    GetParticipantsRequest,
    GetFullChannelRequest,
)
from telethon.tl.types import (
    ChannelParticipantsSearch,
    InputPeerUser,
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityUnderline,
    MessageEntityStrike,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityUrl,
    MessageEntityTextUrl,
    MessageEntityBlockquote,
    MessageEntitySpoiler,
)
# ============================================================
# SAFE IMPORT - JOIN REQUESTS API
# ============================================================
_log = logging.getLogger(__name__)

HAS_JOIN_REQUESTS = False
try:
    from telethon.tl.functions.messages import (
        GetChatInviteImportersRequest,
        ExportChatInviteRequest,
    )
    HAS_JOIN_REQUESTS = True
    _log.info("Pending fetch API loaded.")
except ImportError as _je:
    _log.warning(f"Pending fetch not available: {_je}")

try:
    from telethon.tl.functions.messages import (
        HideChatJoinRequestRequest as HideJoinRequestRequest,
    )
    _log.info("HideChatJoinRequestRequest loaded.")
except ImportError:
    try:
        from telethon.tl.functions.channels import (
            HideJoinRequestRequest,
        )
        _log.info("HideJoinRequestRequest loaded.")
    except ImportError:
        HideJoinRequestRequest = None
        _log.warning("Approve request API not available.")

from config import (
    PROXY_SOURCES,
    TELEGRAM_TEST_SERVERS,
    OWNER_ID,
)
from database import (
    add_proxy,
    get_fresh_proxy,
    get_proxy_count,
    get_proxy_sources,
    update_proxy_source,
    get_config,
    set_config,
    update_campaign,
    add_log,
    get_dm_message,
    deduct_credits,
    add_credits,
    update_user,
)
from fingerprint import (
    human_delay,
    micro_jitter,
    batch_delay,
    dm_send_delay,
    flood_wait_handler,
    human_dm_pattern,
    get_safe_batch_size,
    progress_update_delay,
    typing_simulation,
    read_receipt_simulation,
    irregular_batch_pattern,
    is_suspicious_pattern,
)
from userbot import load_client, release_client

logger = logging.getLogger(__name__)


# ============================================================
# TASK REGISTRY
# ============================================================

_task_registry = {}
_semaphore     = None


def get_task_registry() -> dict:
    return dict(_task_registry)


def get_user_task(user_id: int) -> dict:
    return _task_registry.get(user_id)


def register_task(
    user_id: int,
    task: asyncio.Task,
    task_type: str,
    total: int,
    campaign_id: int = None
):
    _task_registry[user_id] = {
        "task":        task,
        "type":        task_type,
        "progress":    0,
        "total":       total,
        "status":      "running",
        "started_at":  datetime.now(),
        "campaign_id": campaign_id,
    }


def update_task_progress(user_id: int, progress: int):
    if user_id in _task_registry:
        _task_registry[user_id]["progress"] = progress


def deregister_task(user_id: int):
    _task_registry.pop(user_id, None)


async def kill_task(user_id: int) -> bool:
    task_info = _task_registry.get(user_id)
    if not task_info:
        return False
    task = task_info["task"]
    if not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(
                asyncio.shield(task),
                timeout=5.0
            )
        except (
            asyncio.CancelledError,
            asyncio.TimeoutError
        ):
            pass
    deregister_task(user_id)
    return True


async def kill_all_tasks() -> int:
    user_ids = list(_task_registry.keys())
    count    = 0
    for user_id in user_ids:
        if await kill_task(user_id):
            count += 1
    return count


# ============================================================
# SEMAPHORE
# ============================================================

async def init_semaphore():
    global _semaphore
    concurrency = int(
        await get_config("concurrency") or 100
    )
    _semaphore = asyncio.Semaphore(concurrency)
    logger.info(
        f"Semaphore initialized: {concurrency} slots."
    )


async def refresh_semaphore():
    global _semaphore
    concurrency = int(
        await get_config("concurrency") or 100
    )
    _semaphore = asyncio.Semaphore(concurrency)
    logger.info(
        f"Semaphore refreshed: {concurrency} slots."
    )


# ============================================================
# ENTITY CONVERTER
# ============================================================

def convert_entities(entities_data: list) -> list:
    """
    Convert entity dicts (from DB/JSON) back to
    proper Telethon MessageEntity objects.
    Skips unknown types safely.
    """
    if not entities_data:
        return []

    entity_map = {
        "bold":          MessageEntityBold,
        "italic":        MessageEntityItalic,
        "underline":     MessageEntityUnderline,
        "strikethrough": MessageEntityStrike,
        "code":          MessageEntityCode,
        "pre":           MessageEntityPre,
        "url":           MessageEntityUrl,
        "text_link":     MessageEntityTextUrl,
        "spoiler":       MessageEntitySpoiler,
        "blockquote":    MessageEntityBlockquote,
    }

    result = []
    for e in entities_data:
        try:
            entity_type = e.get("type", "")
            offset      = int(e.get("offset", 0))
            length      = int(e.get("length", 0))
            url         = e.get("url")

            if length == 0:
                continue

            cls = entity_map.get(entity_type)
            if not cls:
                continue

            if entity_type == "text_link" and url:
                result.append(
                    cls(
                        offset=offset,
                        length=length,
                        url=url
                    )
                )
            elif entity_type == "pre":
                result.append(
                    cls(
                        offset=offset,
                        length=length,
                        language=""
                    )
                )
            else:
                result.append(
                    cls(offset=offset, length=length)
                )

        except Exception as ex:
            logger.warning(
                f"Entity skip {e.get('type')}: {ex}"
            )
            continue

    return result


# ============================================================
# DELAY PRESETS
# ============================================================

DELAY_PRESETS = {
    "fast": {
        "dm_min": 1,
        "dm_max": 2,
        "label":  "⚡ Fast (1–2s)",
        "risk":   "Higher risk of limits",
    },
    "medium": {
        "dm_min": 3,
        "dm_max": 8,
        "label":  "⚖️ Medium (3–8s)",
        "risk":   "Balanced",
    },
    "slow": {
        "dm_min": 8,
        "dm_max": 20,
        "label":  "🐢 Slow (8–20s)",
        "risk":   "Safest",
    },
}


def get_delay_preset(preset: str) -> dict:
    return DELAY_PRESETS.get(
        preset,
        DELAY_PRESETS["medium"]
    )


# ============================================================
# PROXY HUNTER
# ============================================================

async def hunt_proxies():
    logger.info("Proxy hunter started.")

    while True:
        try:
            hunter_enabled = await get_config(
                "hunter_enabled"
            )
            if hunter_enabled != "1":
                await asyncio.sleep(60)
                continue

            db_sources = await get_proxy_sources()
            db_urls    = [s["url"] for s in db_sources]
            all_urls   = list(
                set(db_urls + PROXY_SOURCES)
            )

            for url in all_urls:
                try:
                    found = await _scrape_proxy_source(
                        url
                    )
                    await update_proxy_source(url, found)
                    await micro_jitter(1.0)
                except Exception as e:
                    logger.warning(
                        f"Source failed {url}: {e}"
                    )

            interval = int(
                await get_config(
                    "hunter_interval"
                ) or 300
            )
            jitter = random.uniform(-30, 60)
            await asyncio.sleep(interval + jitter)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Hunter error: {e}")
            await asyncio.sleep(60)


async def _scrape_proxy_source(url: str) -> int:
    working = 0
    timeout = aiohttp.ClientTimeout(total=15)

    try:
        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return 0
                text    = await response.text()
                proxies = _parse_proxy_list(text, url)

                for i in range(0, len(proxies), 20):
                    batch   = proxies[i:i + 20]
                    tasks   = [
                        _test_and_save_proxy(p)
                        for p in batch
                    ]
                    results = await asyncio.gather(
                        *tasks,
                        return_exceptions=True
                    )
                    working += sum(
                        1 for r in results
                        if r is True
                    )
                    await micro_jitter(0.5)

    except Exception as e:
        logger.warning(
            f"Scrape source error {url}: {e}"
        )

    return working


def _parse_proxy_list(
    text: str,
    source_url: str
) -> list:
    proxies = []
    lines   = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("{") or line.startswith("["):
            try:
                data = json.loads(text)
                if (
                    isinstance(data, dict)
                    and "data" in data
                ):
                    for item in data["data"]:
                        proxies.append({
                            "host":   item.get("ip"),
                            "port":   int(
                                item.get("port", 0)
                            ),
                            "source": source_url,
                        })
                break
            except Exception:
                continue

        match = re.match(
            r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r":(\d+)$",
            line
        )
        if match:
            proxies.append({
                "host":   match.group(1),
                "port":   int(match.group(2)),
                "source": source_url,
            })

    return proxies


async def _test_and_save_proxy(proxy: dict) -> bool:
    host   = proxy.get("host")
    port   = proxy.get("port")
    source = proxy.get("source", "")

    if not host or not port:
        return False

    timeout = int(
        await get_config("proxy_timeout") or 10
    )

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()

        await add_proxy(
            host=host,
            port=port,
            proxy_type="SOCKS5",
            source=source,
        )
        return True

    except Exception:
        return False


async def force_hunt_now() -> int:
    db_sources  = await get_proxy_sources()
    db_urls     = [s["url"] for s in db_sources]
    all_urls    = list(set(db_urls + PROXY_SOURCES))
    total_found = 0

    for url in all_urls:
        try:
            found        = await _scrape_proxy_source(url)
            total_found += found
            await micro_jitter(0.8)
        except Exception as e:
            logger.warning(
                f"Force hunt failed {url}: {e}"
            )

    return total_found

# ============================================================
# PENDING JOIN REQUESTS HELPER
# FIX: Uses input_peer, extracts link properly,
#      handles all None cases
# ============================================================

# ============================================================
# PENDING JOIN REQUESTS HELPER
# FIX: Use empty link string to get ALL pending
#      requests across all invite links
# ============================================================

async def get_pending_requesters(
    client,
    entity,
    limit: int = 100,
) -> list:
    """
    Fetch all pending join request users from a channel.
    Uses empty link to get requests across ALL invite links.
    Returns list of Telethon user objects.
    """
    from telethon.tl.types import InputUserEmpty

    if entity is None:
        raise ValueError(
            "Channel entity is None."
        )

    # Convert to proper InputPeer
    try:
        input_peer = await client.get_input_entity(entity)
    except Exception as e:
        logger.error(f"input_entity failed: {e}")
        raise ValueError(
            f"Cannot resolve channel: {e}"
        )

    all_users   = []
    seen_ids    = set()
    offset_user = InputUserEmpty()
    offset_date = 0

    # ── Paginate through ALL pending requests ────────────
    # link="" (empty string) = all invite links combined
    while True:
        await asyncio.sleep(0)

        try:
            result = await client(
                GetChatInviteImportersRequest(
                    peer=input_peer,
                    link="",           # ← empty = ALL links
                    requested=True,
                    q="",              # ← empty search
                    offset_date=offset_date,
                    offset_user=offset_user,
                    limit=limit,
                )
            )
        except errors.ChatAdminRequiredError:
            raise
        except errors.FloodWaitError as e:
            await flood_wait_handler(e.seconds)
            continue
        except TypeError:
            # Older Telethon versions don't accept
            # link="" — try without link parameter
            try:
                result = await client(
                    GetChatInviteImportersRequest(
                        peer=input_peer,
                        requested=True,
                        q="",
                        offset_date=offset_date,
                        offset_user=offset_user,
                        limit=limit,
                    )
                )
            except Exception as e2:
                logger.error(
                    f"get_pending fallback failed: {e2}"
                )
                break
        except Exception as e:
            logger.error(
                f"get_pending_requesters error: {e}"
            )
            break

        if not result.importers:
            logger.info(
                f"No more importers. "
                f"Total collected: {len(all_users)}"
            )
            break

        for importer in result.importers:
            user = next(
                (
                    u for u in result.users
                    if u.id == importer.user_id
                ),
                None
            )
            if user and user.id not in seen_ids:
                seen_ids.add(user.id)
                all_users.append(user)

        logger.info(
            f"Fetched {len(result.importers)} in batch. "
            f"Total: {len(all_users)}"
        )

        if len(result.importers) < limit:
            break

        # Advance pagination
        last        = result.importers[-1]
        offset_date = last.date
        try:
            offset_user = await client.get_input_entity(
                last.user_id
            )
        except Exception as e:
            logger.warning(
                f"Pagination cursor failed: {e}"
            )
            break

        await micro_jitter(0.5)

    logger.info(
        f"Found {len(all_users)} total pending requesters"
    )
    return all_users

# ============================================================
# DM CONTACTS FETCHER
# ============================================================

async def get_dm_contacts(session_id: int) -> list:
    client = None
    try:
        client   = await load_client(session_id)
        await micro_jitter(0.6)

        contacts = []
        seen_ids = set()
        me       = await client.get_me()
        my_id    = me.id

        async for dialog in client.iter_dialogs(
            limit=None
        ):
            await asyncio.sleep(0)

            if not dialog.is_user:
                continue

            user = dialog.entity

            if user.id == my_id:
                continue
            if user.id in seen_ids:
                continue
            if getattr(user, "bot", False):
                continue
            if getattr(user, "deleted", False):
                continue

            seen_ids.add(user.id)
            contacts.append({
                "user_id":    user.id,
                "username":   getattr(
                    user, "username", ""
                ) or "",
                "first_name": getattr(
                    user, "first_name", ""
                ) or "",
                "last_name":  getattr(
                    user, "last_name", ""
                ) or "",
            })

        logger.info(
            f"DM contacts: {len(contacts)} found"
        )

        await release_client(session_id, client)
        return contacts

    except Exception as e:
        logger.error(f"get_dm_contacts failed: {e}")
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        return []


# ============================================================
# SCRAPE MEMBERS
# ============================================================

async def scrape_members(
    user_id: int,
    session_id: int,
    target: str,
    campaign_id: int,
    progress_callback=None,
) -> dict:
    global _semaphore

    if _semaphore is None:
        await init_semaphore()

    async with _semaphore:
        client = None
        try:
            client  = await load_client(session_id)
            await micro_jitter(0.6)

            stealth = int(
                await get_config("stealth_level") or 3
            )
            entity  = await client.get_entity(target)
            await micro_jitter(0.5)

            full    = await client(
                GetFullChannelRequest(channel=entity)
            )
            total   = full.full_chat.participants_count
            await micro_jitter(0.4)

            members     = []
            offset      = 0
            seen_ids    = set()
            last_update = datetime.now()

            while True:
                await asyncio.sleep(0)

                batch_size = get_safe_batch_size(
                    stealth_level=stealth
                )

                try:
                    participants = await client(
                        GetParticipantsRequest(
                            channel=entity,
                            filter=ChannelParticipantsSearch(
                                ""
                            ),
                            offset=offset,
                            limit=batch_size,
                            hash=0,
                        )
                    )
                except errors.FloodWaitError as e:
                    await flood_wait_handler(e.seconds)
                    continue
                except errors.ChatAdminRequiredError:
                    return {
                        "success": False,
                        "error":
                            "Admin access required."
                    }

                if not participants.users:
                    break

                for user in participants.users:
                    if user.id in seen_ids:
                        continue
                    seen_ids.add(user.id)
                    members.append({
                        "user_id":    user.id,
                        "username":   user.username or "",
                        "first_name": user.first_name or "",
                        "last_name":  user.last_name or "",
                        "phone":      getattr(
                            user, "phone", ""
                        ) or "",
                        "is_bot":     user.bot,
                    })

                offset += len(participants.users)
                update_task_progress(
                    user_id, len(members)
                )

                await update_campaign(
                    campaign_id,
                    sent=len(members)
                )

                now      = datetime.now()
                interval = int(
                    await get_config(
                        "progress_interval"
                    ) or 8
                )
                if (
                    now - last_update
                ).seconds >= interval \
                        and progress_callback:
                    await progress_callback(
                        len(members), total
                    )
                    last_update = now

                await batch_delay(stealth_level=stealth)

                if offset >= total:
                    break

                await micro_jitter(0.5)

            file_path = await _save_members_to_file(
                user_id, members
            )

            await update_campaign(
                campaign_id,
                status="completed",
                sent=len(members),
                total=total,
                finished_at=datetime.now().isoformat(),
            )

            await update_user(
                user_id,
                total_scraped=len(members)
            )

            await add_log(
                user_id,
                "scrape_complete",
                f"Scraped {len(members)} from {target}"
            )

            await release_client(session_id, client)

            return {
                "success":       True,
                "total":         total,
                "scraped":       len(members),
                "members":       members,
                "file_path":     file_path,
                "with_username": sum(
                    1 for m in members
                    if m["username"]
                ),
                "bots_found":    sum(
                    1 for m in members
                    if m["is_bot"]
                ),
            }

        except asyncio.CancelledError:
            await update_campaign(
                campaign_id,
                status="cancelled",
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.error(
                f"Scrape failed for {user_id}: {e}"
            )
            await update_campaign(
                campaign_id,
                status="failed",
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            return {
                "success": False,
                "error":   str(e)
            }

        finally:
            deregister_task(user_id)


# ============================================================
# SCRAPE JOIN REQUESTS
# ============================================================

async def scrape_join_requests(
    user_id: int,
    session_id: int,
    target: str,
    campaign_id: int,
    progress_callback=None,
) -> dict:
    global _semaphore

    if not HAS_JOIN_REQUESTS:
        return {
            "success": False,
            "error": (
                "Your Telethon version does not\n"
                "support join requests.\n"
                "Run: pip install --upgrade telethon"
            )
        }

    if _semaphore is None:
        await init_semaphore()

    async with _semaphore:
        client = None
        try:
            client  = await load_client(session_id)
            await micro_jitter(0.6)

            entity  = await client.get_entity(target)
            await micro_jitter(0.5)

            try:
                pending_users_raw = await get_pending_requesters(
                    client, entity
                )
            except errors.ChatAdminRequiredError:
                return {
                    "success": False,
                    "error": (
                        "Admin access required.\n"
                        "Account must be admin in "
                        "this channel."
                    )
                }

            pending_users = []
            for user in pending_users_raw:
                pending_users.append({
                    "user_id":    user.id,
                    "username":   user.username or "",
                    "first_name": user.first_name or "",
                    "last_name":  user.last_name or "",
                    "is_bot":     getattr(
                        user, "bot", False
                    ),
                })

            update_task_progress(
                user_id, len(pending_users)
            )

            if progress_callback:
                await progress_callback(
                    len(pending_users),
                    len(pending_users)
                )

            file_path = await _save_members_to_file(
                user_id,
                pending_users,
                prefix="pending"
            )

            await update_campaign(
                campaign_id,
                status="completed",
                sent=len(pending_users),
                total=len(pending_users),
                finished_at=datetime.now().isoformat(),
            )

            await add_log(
                user_id,
                "pending_scrape_complete",
                f"Scraped {len(pending_users)} "
                f"from {target}"
            )

            await release_client(session_id, client)

            return {
                "success":       True,
                "total":         len(pending_users),
                "members":       pending_users,
                "file_path":     file_path,
                "with_username": sum(
                    1 for u in pending_users
                    if u["username"]
                ),
            }

        except asyncio.CancelledError:
            await update_campaign(
                campaign_id,
                status="cancelled",
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.error(
                f"Pending scrape failed "
                f"for {user_id}: {e}"
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            return {
                "success": False,
                "error":   str(e)
            }

        finally:
            deregister_task(user_id)


# ============================================================
# ACCEPT PENDING REQUESTS
# ============================================================

async def accept_pending_requests(
    user_id: int,
    session_id: int,
    target: str,
    campaign_id: int,
    progress_callback=None,
) -> dict:
    global _semaphore

    if not HAS_JOIN_REQUESTS:
        return {
            "success": False,
            "error": (
                "Your Telethon version does not\n"
                "support join requests.\n"
                "Run: pip install --upgrade telethon"
            )
        }

    if _semaphore is None:
        await init_semaphore()

    async with _semaphore:
        client = None
        try:
            client  = await load_client(session_id)
            await micro_jitter(0.6)

            stealth = int(
                await get_config("stealth_level") or 3
            )
            entity  = await client.get_entity(target)
            await micro_jitter(0.5)

            try:
                pending_users = await get_pending_requesters(
                    client, entity
                )
            except errors.ChatAdminRequiredError:
                return {
                    "success": False,
                    "error": (
                        "Admin access required.\n"
                        "Account must be admin in "
                        "this channel."
                    )
                }

            accepted    = 0
            failed      = 0
            last_update = datetime.now()

            for user in pending_users:
                await asyncio.sleep(0)

                try:
                    await client(
                        HideJoinRequestRequest(
                            channel=entity,
                            user_id=user.id,
                            approved=True,
                        )
                    )
                    accepted += 1
                    await micro_jitter(0.8)

                except errors.FloodWaitError as e:
                    await flood_wait_handler(e.seconds)
                    try:
                        await client(
                            HideJoinRequestRequest(
                                channel=entity,
                                user_id=user.id,
                                approved=True,
                            )
                        )
                        accepted += 1
                    except Exception:
                        failed += 1

                except Exception:
                    failed += 1

                update_task_progress(user_id, accepted)

                now      = datetime.now()
                interval = int(
                    await get_config(
                        "progress_interval"
                    ) or 8
                )
                if (
                    now - last_update
                ).seconds >= interval \
                        and progress_callback:
                    await progress_callback(
                        accepted,
                        len(pending_users)
                    )
                    last_update = now

                await human_delay(
                    min_seconds=0.5,
                    max_seconds=2.5,
                    stealth_level=stealth,
                )

            await update_campaign(
                campaign_id,
                status="completed",
                sent=accepted,
                failed=failed,
                total=len(pending_users),
                finished_at=datetime.now().isoformat(),
            )

            await add_log(
                user_id,
                "accept_complete",
                f"Accepted {accepted} Failed {failed}"
            )

            await release_client(session_id, client)

            return {
                "success":  True,
                "accepted": accepted,
                "failed":   failed,
                "total":    len(pending_users),
            }

        except asyncio.CancelledError:
            await update_campaign(
                campaign_id,
                status="cancelled",
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.error(
                f"Accept pending failed "
                f"for {user_id}: {e}"
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            return {
                "success": False,
                "error":   str(e)
            }

        finally:
            deregister_task(user_id)

# ============================================================
# JOIN REQUEST DM ENGINE
# FIX: Uses InputPeerUser for strangers
# ============================================================

async def run_join_request_dm(
    user_id: int,
    session_id: int,
    target: str,
    campaign_id: int,
    message_text: str,
    message_entities: list,
    auto_reply_text: str = None,
    auto_reply_entities: list = None,
    progress_callback=None,
    delay_preset: str = "medium",
) -> dict:
    global _semaphore

    if not HAS_JOIN_REQUESTS:
        return {
            "success": False,
            "error": (
                "Telethon version too old.\n"
                "Run: pip install --upgrade telethon"
            )
        }

    if _semaphore is None:
        await init_semaphore()

    async with _semaphore:
        client      = None
        sent        = 0
        failed      = 0
        peer_flood  = False
        last_update = datetime.now()

        try:
            logger.info(
                f"JR DM: loading client "
                f"for user {user_id}"
            )
            client = await load_client(session_id)
            await micro_jitter(0.6)

            stealth = int(
                await get_config("stealth_level") or 3
            )

            logger.info(f"JR DM: resolving {target}")
            entity = await client.get_entity(target)
            await micro_jitter(0.5)

            logger.info(
                "JR DM: fetching pending users"
            )
            try:
                pending_users_raw = await get_pending_requesters(
                    client, entity
                )
            except errors.ChatAdminRequiredError:
                logger.error("JR DM: admin required")
                return {
                    "success": False,
                    "error": (
                        "Admin access required.\n"
                        "Account must be admin in "
                        "this channel."
                    )
                }

            # Deduplicate + filter bots
            seen_ids  = set()
            targets   = []
            for u in pending_users_raw:
                if u.id in seen_ids:
                    continue
                if getattr(u, "bot", False):
                    continue
                seen_ids.add(u.id)
                targets.append(u)

            total = len(targets)

            logger.info(
                f"JR DM: {total} targets after "
                f"filtering bots"
            )

            if total == 0:
                return {
                    "success": False,
                    "error": (
                        "No pending join requests "
                        "found (or all are bots)."
                    )
                }

            await update_campaign(
                campaign_id, total=total
            )

            # Initial progress ping
            if progress_callback:
                try:
                    await progress_callback(
                        0, total, 0, False
                    )
                except Exception as pe:
                    logger.warning(
                        f"initial cb: {pe}"
                    )

            auto_reply_enabled = (
                await get_config(
                    "auto_reply_enabled"
                ) == "1"
            )
            typing_enabled = (
                await get_config(
                    "typing_sim_enabled"
                ) == "1"
            )

            telethon_entities = convert_entities(
                message_entities
            )

            if auto_reply_enabled and auto_reply_text:
                telethon_reply_entities = convert_entities(
                    auto_reply_entities or []
                )
                _setup_auto_reply_listener(
                    client,
                    user_id,
                    auto_reply_text,
                    telethon_reply_entities,
                    stealth,
                )

            preset = get_delay_preset(delay_preset)
            dm_min = float(preset["dm_min"])
            dm_max = float(preset["dm_max"])

            logger.info(
                f"JR DM: sending {total} DMs "
                f"with {dm_min}-{dm_max}s delay"
            )

            # ── Send loop ────────────────────────────
            for i, target_user in enumerate(targets):
                await asyncio.sleep(0)
                target_id = target_user.id

                # Build InputPeerUser explicitly
                access_hash = getattr(
                    target_user, "access_hash", None
                )

                if access_hash is None:
                    logger.warning(
                        f"JR DM: [{i+1}] skip "
                        f"{target_id} (no access_hash)"
                    )
                    failed += 1
                    continue

                input_peer = InputPeerUser(
                    user_id=target_id,
                    access_hash=access_hash,
                )

                logger.info(
                    f"JR DM: [{i+1}/{total}] "
                    f"sending to {target_id}"
                )

                try:
                    await read_receipt_simulation()

                    if typing_enabled:
                        try:
                            async with client.action(
                                input_peer, "typing"
                            ):
                                await typing_simulation(
                                    stealth_level=stealth
                                )
                        except Exception as te:
                            logger.debug(
                                f"typing skip: {te}"
                            )
                            await typing_simulation(
                                stealth_level=stealth
                            )

                    await client.send_message(
                        entity=input_peer,
                        message=message_text,
                        formatting_entities=(
                            telethon_entities
                            if telethon_entities
                            else None
                        ),
                        link_preview=False,
                    )

                    sent += 1
                    update_task_progress(user_id, sent)
                    logger.info(
                        f"JR DM: [{i+1}] SENT "
                        f"to {target_id}"
                    )

                    if user_id != OWNER_ID:
                        await deduct_credits(user_id, 1)

                    await update_campaign(
                        campaign_id,
                        sent=sent,
                        failed=failed,
                    )

                    now      = datetime.now()
                    elapsed  = (
                        now - last_update
                    ).seconds
                    should_update = (
                        elapsed >= 5
                        or sent % 3 == 0
                    )

                    if should_update and progress_callback:
                        try:
                            await progress_callback(
                                sent,
                                total,
                                failed,
                                peer_flood
                            )
                            last_update = now
                        except Exception as pe:
                            logger.warning(
                                f"progress cb: {pe}"
                            )

                    await human_dm_pattern(sent)
                    await dm_send_delay(
                        stealth_level=stealth,
                        custom_min=dm_min,
                        custom_max=dm_max,
                    )

                except errors.PeerFloodError:
                    peer_flood = True
                    failed    += 1
                    logger.warning(
                        f"JR DM: PeerFlood at {sent}"
                    )
                    break

                except errors.FloodWaitError as e:
                    logger.warning(
                        f"JR DM: FloodWait {e.seconds}s"
                    )
                    await flood_wait_handler(e.seconds)
                    try:
                        await client.send_message(
                            entity=input_peer,
                            message=message_text,
                            formatting_entities=(
                                telethon_entities
                                if telethon_entities
                                else None
                            ),
                            link_preview=False,
                        )
                        sent += 1
                        if user_id != OWNER_ID:
                            await deduct_credits(
                                user_id, 1
                            )
                    except Exception:
                        failed += 1

                except (
                    errors.UserPrivacyRestrictedError,
                    errors.UserIsBlockedError,
                    errors.InputUserDeactivatedError,
                ) as e:
                    failed += 1
                    logger.debug(
                        f"JR DM: {target_id} skip "
                        f"({type(e).__name__})"
                    )
                    await micro_jitter(0.4)

                except Exception as e:
                    failed += 1
                    logger.error(
                        f"JR DM: [{i+1}] EXCEPTION "
                        f"{type(e).__name__}: {e}"
                    )
                    await micro_jitter(0.6)

            # Final progress update
            if progress_callback:
                try:
                    await progress_callback(
                        sent, total, failed, peer_flood
                    )
                except Exception:
                    pass

            status = (
                "peer_flood_stopped"
                if peer_flood
                else "completed"
            )

            await update_campaign(
                campaign_id,
                status=status,
                sent=sent,
                failed=failed,
                total=total,
                finished_at=datetime.now().isoformat(),
            )

            await add_log(
                user_id,
                "join_request_dm_complete",
                f"Sent:{sent} Failed:{failed}"
            )

            logger.info(
                f"JR DM: complete. "
                f"Sent:{sent} Failed:{failed}"
            )

            await release_client(session_id, client)

            return {
                "success":    True,
                "sent":       sent,
                "failed":     failed,
                "total":      total,
                "peer_flood": peer_flood,
            }

        except asyncio.CancelledError:
            await update_campaign(
                campaign_id,
                status="cancelled",
                sent=sent,
                failed=failed,
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.error(
                f"JR DM failed for {user_id}: {e}"
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            return {
                "success": False,
                "error":   str(e),
                "sent":    sent,
                "failed":  failed,
            }

        finally:
            deregister_task(user_id)

# ============================================================
# MASS DM ENGINE
# ============================================================

async def run_mass_dm(
    user_id: int,
    session_id: int,
    targets: list,
    campaign_id: int,
    message_text: str,
    message_entities: list,
    auto_reply_text: str = None,
    auto_reply_entities: list = None,
    progress_callback=None,
    delay_preset: str = "medium",
) -> dict:
    global _semaphore

    if _semaphore is None:
        await init_semaphore()

    async with _semaphore:
        client     = None
        sent       = 0
        failed     = 0
        peer_flood = False
        last_update = datetime.now()

        try:
            client  = await load_client(session_id)
            await micro_jitter(0.7)

            stealth = int(
                await get_config("stealth_level") or 3
            )
            auto_reply_enabled = (
                await get_config(
                    "auto_reply_enabled"
                ) == "1"
            )
            typing_enabled = (
                await get_config(
                    "typing_sim_enabled"
                ) == "1"
            )

            preset = get_delay_preset(delay_preset)
            dm_min = float(preset["dm_min"])
            dm_max = float(preset["dm_max"])

            telethon_entities = convert_entities(
                message_entities
            )

            if auto_reply_enabled and auto_reply_text:
                telethon_reply_entities = convert_entities(
                    auto_reply_entities or []
                )
                _setup_auto_reply_listener(
                    client,
                    user_id,
                    auto_reply_text,
                    telethon_reply_entities,
                    stealth,
                )

            for i, target in enumerate(targets):
                await asyncio.sleep(0)

                try:
                    await read_receipt_simulation()

                    if typing_enabled:
                        try:
                            async with client.action(
                                target, "typing"
                            ):
                                await typing_simulation(
                                    stealth_level=stealth
                                )
                        except Exception:
                            await typing_simulation(
                                stealth_level=stealth
                            )

                    await client.send_message(
                        entity=target,
                        message=message_text,
                        formatting_entities=(
                            telethon_entities
                            if telethon_entities
                            else None
                        ),
                        link_preview=False,
                    )

                    sent += 1
                    update_task_progress(user_id, sent)

                    if user_id != OWNER_ID:
                        await deduct_credits(user_id, 1)

                    await update_campaign(
                        campaign_id,
                        sent=sent,
                        failed=failed,
                    )

                    now      = datetime.now()
                    interval = int(
                        await get_config(
                            "progress_interval"
                        ) or 8
                    )
                    if (
                        now - last_update
                    ).seconds >= interval \
                            and progress_callback:
                        await progress_callback(
                            sent,
                            len(targets),
                            failed,
                            peer_flood
                        )
                        last_update = now

                    await human_dm_pattern(sent)
                    await dm_send_delay(
                        stealth_level=stealth,
                        custom_min=dm_min,
                        custom_max=dm_max,
                    )

                except errors.PeerFloodError:
                    peer_flood = True
                    failed    += 1
                    await add_log(
                        user_id,
                        "peer_flood",
                        f"After {sent} messages"
                    )
                    break

                except errors.FloodWaitError as e:
                    await flood_wait_handler(e.seconds)
                    try:
                        await client.send_message(
                            entity=target,
                            message=message_text,
                            formatting_entities=(
                                telethon_entities
                                if telethon_entities
                                else None
                            ),
                            link_preview=False,
                        )
                        sent += 1
                        if user_id != OWNER_ID:
                            await deduct_credits(
                                user_id, 1
                            )
                    except Exception:
                        failed += 1

                except errors.UserPrivacyRestrictedError:
                    failed += 1
                    await micro_jitter(0.5)

                except errors.UserIsBlockedError:
                    failed += 1
                    await micro_jitter(0.5)

                except errors.InputUserDeactivatedError:
                    failed += 1
                    await micro_jitter(0.3)

                except Exception as e:
                    failed += 1
                    logger.warning(
                        f"DM failed {target}: {e}"
                    )
                    await micro_jitter(0.8)

            status = (
                "peer_flood_stopped"
                if peer_flood
                else "completed"
            )

            await update_campaign(
                campaign_id,
                status=status,
                sent=sent,
                failed=failed,
                total=len(targets),
                finished_at=datetime.now().isoformat(),
            )

            await add_log(
                user_id,
                "mass_dm_complete",
                f"Sent:{sent} Failed:{failed} "
                f"Flood:{peer_flood}"
            )

            await release_client(session_id, client)

            return {
                "success":    True,
                "sent":       sent,
                "failed":     failed,
                "total":      len(targets),
                "peer_flood": peer_flood,
            }

        except asyncio.CancelledError:
            await update_campaign(
                campaign_id,
                status="cancelled",
                sent=sent,
                failed=failed,
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.error(
                f"Mass DM failed for {user_id}: {e}"
            )
            await update_campaign(
                campaign_id,
                status="failed",
                sent=sent,
                failed=failed,
                finished_at=datetime.now().isoformat(),
            )
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            return {
                "success": False,
                "error":   str(e),
                "sent":    sent,
                "failed":  failed,
            }

        finally:
            deregister_task(user_id)


# ============================================================
# AUTO REPLY LISTENER
# ============================================================

def _setup_auto_reply_listener(
    client,
    user_id: int,
    reply_text: str,
    reply_entities: list,
    stealth_level: int,
):
    from telethon import events

    replied_to = set()

    @client.on(events.NewMessage(incoming=True))
    async def auto_reply_handler(event):
        sender_id = event.sender_id
        if sender_id in replied_to:
            return

        replied_to.add(sender_id)

        try:
            await read_receipt_simulation()

            reply_min = float(
                await get_config(
                    "reply_delay_min"
                ) or 6
            )
            reply_max = float(
                await get_config(
                    "reply_delay_max"
                ) or 18
            )

            try:
                async with client.action(
                    sender_id, "typing"
                ):
                    await asyncio.sleep(
                        random.uniform(
                            reply_min, reply_max
                        )
                    )
            except Exception:
                await asyncio.sleep(
                    random.uniform(reply_min, reply_max)
                )

            await client.send_message(
                entity=sender_id,
                message=reply_text,
                formatting_entities=(
                    reply_entities
                    if reply_entities
                    else None
                ),
                link_preview=False,
            )

            await add_log(
                user_id,
                "auto_reply_sent",
                f"To {sender_id}"
            )

        except Exception as e:
            logger.warning(f"Auto-reply failed: {e}")


# ============================================================
# FILE SAVER
# ============================================================

async def _save_members_to_file(
    user_id: int,
    members: list,
    prefix: str = "members"
) -> str:
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    file_path = (
        f"scraped_{prefix}_{user_id}_{timestamp}.txt"
    )

    lines = [
        "=" * 60,
        f"Zenkai DMs Bot — Scraped {prefix.title()}",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total: {len(members)}",
        "=" * 60,
        "",
        f"{'ID':<15} {'Username':<25} "
        f"{'First Name':<20} {'Last Name':<20}",
        "-" * 80,
    ]

    for member in members:
        username = (
            f"@{member['username']}"
            if member.get("username")
            else "N/A"
        )
        lines.append(
            f"{member['user_id']:<15} "
            f"{username:<25} "
            f"{member.get('first_name', ''):<20} "
            f"{member.get('last_name', ''):<20}"
        )

    lines.append("")
    lines.append("=" * 60)
    lines.append(
        "Generated by Zenkai DMs Forwarding Bot"
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return file_path


# ============================================================
# PROGRESS FORMATTERS
# ============================================================

def format_progress_bar(
    current: int,
    total: int,
    width: int = 14
) -> str:
    if total == 0:
        return "[░░░░░░░░░░░░░░] 0%"

    percent = min(current / total, 1.0)
    filled  = int(width * percent)
    bar     = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {int(percent * 100)}%"


def format_eta(
    current: int,
    total: int,
    elapsed_seconds: float
) -> str:
    if current == 0 or elapsed_seconds == 0:
        return "Calculating..."

    rate = current / elapsed_seconds
    if rate == 0:
        return "Unknown"

    remaining   = total - current
    eta_seconds = remaining / rate

    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    elif eta_seconds < 3600:
        return (
            f"{int(eta_seconds // 60)}m "
            f"{int(eta_seconds % 60)}s"
        )
    else:
        hours = int(eta_seconds // 3600)
        mins  = int((eta_seconds % 3600) // 60)
        return f"{hours}h {mins}m"


# ============================================================
# EXPORT ALL
# ============================================================

__all__ = [
    "get_task_registry",
    "get_user_task",
    "register_task",
    "update_task_progress",
    "deregister_task",
    "kill_task",
    "kill_all_tasks",
    "init_semaphore",
    "refresh_semaphore",
    "convert_entities",
    "get_delay_preset",
    "DELAY_PRESETS",
    "hunt_proxies",
    "force_hunt_now",
    "get_dm_contacts",
    "get_pending_requesters",
    "scrape_members",
    "scrape_join_requests",
    "accept_pending_requests",
    "run_mass_dm",
    "run_join_request_dm",
    "format_progress_bar",
    "format_eta",
]