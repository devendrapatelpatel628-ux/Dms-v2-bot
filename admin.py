# ============================================================
#         ZENKAI DMS FORWARDING BOT - ADMIN PANEL
# ============================================================

import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID, OWNER_USERNAME, BOT_NAME, BOT_VERSION
from filters import OwnerFilter
from database import (
    get_user,
    get_all_users,
    get_total_users,
    update_user,
    ban_user,
    unban_user,
    grant_vip,
    revoke_vip,
    add_credits,
    deduct_credits,
    search_user,
    get_all_keys,
    create_key,
    delete_key,
    get_key_by_name,
    get_key_redeemers,
    get_force_channels,
    add_force_channel,
    delete_force_channel,
    get_proxy_sources,
    get_proxy_count,
    add_proxy_source,
    delete_proxy_source,
    clear_proxies,
    get_config,
    set_config,
    get_all_config,
    get_bot_stats,
    get_recent_logs,
    get_user_logs,
    get_top_referrers,
    get_referrals_today,
    get_dms_sent_today,
    add_log,
)
from keyboards import (
    admin_panel_keyboard,
    admin_users_keyboard,
    admin_keys_keyboard,
    admin_forcesub_keyboard,
    admin_proxy_keyboard,
    admin_settings_keyboard,
    admin_stats_keyboard,
    admin_refer_settings_keyboard,
    active_tasks_keyboard,
    stealth_level_keyboard,
    view_keys_keyboard,
    view_channels_keyboard,
    view_sources_keyboard,
    channel_type_keyboard,
    confirm_cancel_keyboard,
    back_to_main_inline,
)
from engine import (
    get_task_registry,
    kill_task,
    kill_all_tasks,
    force_hunt_now,
    refresh_semaphore,
    scrape_members,
    scrape_join_requests,
    register_task,
    format_progress_bar,
    format_eta,
)
from fingerprint import micro_jitter

logger = logging.getLogger(__name__)
admin_router = Router()
admin_router.message.filter(OwnerFilter())
admin_router.callback_query.filter(OwnerFilter())


# ============================================================
# FSM STATES - ADMIN
# ============================================================

class AdminUserStates(StatesGroup):
    awaiting_user_id        = State()
    awaiting_ban_id         = State()
    awaiting_unban_id       = State()
    awaiting_vip_id         = State()
    awaiting_credits_id     = State()
    awaiting_credits_amount = State()
    awaiting_broadcast      = State()


class AdminKeyStates(StatesGroup):
    awaiting_key_name       = State()
    awaiting_key_credits    = State()
    awaiting_key_redeems    = State()
    awaiting_delete_key     = State()
    awaiting_redeemer_key   = State()


class AdminForceSubStates(StatesGroup):
    awaiting_channel_link   = State()
    awaiting_invite_link    = State()
    awaiting_channel_id     = State()
    awaiting_remove_id      = State()


class AdminProxyStates(StatesGroup):
    awaiting_proxy_source   = State()


class AdminSettingsStates(StatesGroup):
    awaiting_api_id         = State()
    awaiting_api_hash       = State()
    awaiting_concurrency    = State()
    awaiting_dm_delay       = State()
    awaiting_reply_delay    = State()
    awaiting_free_credits   = State()
    awaiting_max_accounts   = State()
    awaiting_progress_interval = State()
    awaiting_referral_credits  = State()
    awaiting_new_user_bonus    = State()


class AdminScrapeStates(StatesGroup):
    awaiting_session_id     = State()
    awaiting_target         = State()
    awaiting_scrape_type    = State()


# ============================================================
# HELPERS
# ============================================================

def admin_back_keyboard():
    """Back to admin panel inline button."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.enums import ButtonStyle
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔙 Back to Admin Panel",
            callback_data="admin_panel",
            style=ButtonStyle.PRIMARY,
        )
    ]])


# ============================================================
# ADMIN PANEL ENTRY
# ============================================================

@admin_router.message(F.text == "⚙️ Admin Panel")
@admin_router.callback_query(F.data == "admin_panel")
async def admin_panel_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    """Show main admin panel."""
    await state.clear()

    stats = await get_bot_stats()
    proxy_count = await get_proxy_count()
    tasks = get_task_registry()

    text = (
        f"⚙️ <b>𝗔𝗱𝗺𝗶𝗻 𝗣𝗮𝗻𝗲𝗹</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 <b>Bot:</b> {BOT_NAME}\n"
        f"📦 <b>Version:</b> {BOT_VERSION}\n\n"
        f"👥 <b>Total Users:</b> "
        f"{stats['total_users']:,}\n"
        f"🆕 <b>New Today:</b> "
        f"{stats['new_users_today']:,}\n"
        f"🚫 <b>Banned:</b> "
        f"{stats['banned_users']:,}\n"
        f"💎 <b>VIP Users:</b> "
        f"{stats['vip_users']:,}\n"
        f"📱 <b>Active Sessions:</b> "
        f"{stats['active_sessions']:,}\n"
        f"🌐 <b>Proxies in Pool:</b> "
        f"{proxy_count:,}\n"
        f"⚡ <b>Active Tasks:</b> "
        f"{len(tasks)}\n"
        f"📨 <b>DMs Today:</b> "
        f"{stats['dms_today']:,}\n"
        f"🎯 <b>Referrals Today:</b> "
        f"{stats['referrals_today']:,}"
    )

    kb = admin_panel_keyboard()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        try:
            await event.message.edit_text(
                text, reply_markup=kb
            )
        except Exception:
            await event.message.answer(
                text, reply_markup=kb
            )
        await event.answer()


# ============================================================
# USER MANAGEMENT
# ============================================================

@admin_router.callback_query(F.data == "admin_users")
async def admin_users_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show user management panel."""
    await state.clear()
    total = await get_total_users()

    await callback.message.edit_text(
        f"👥 <b>User Management</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Total registered users: <b>{total:,}</b>\n\n"
        f"Select an action:",
        reply_markup=admin_users_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_search_user")
async def admin_search_user(
    callback: CallbackQuery,
    state: FSMContext
):
    """Ask for user to search."""
    await state.set_state(AdminUserStates.awaiting_user_id)
    await callback.message.edit_text(
        "🔍 <b>Search User</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the user's:\n"
        "• Telegram ID (e.g. 123456789)\n"
        "• Username (e.g. @username)"
    )
    await callback.answer()


@admin_router.message(AdminUserStates.awaiting_user_id)
async def process_search_user(
    message: Message,
    state: FSMContext
):
    """Process user search."""
    await state.clear()
    query = message.text.strip()

    user = await search_user(query)

    if not user:
        await message.answer(
            "❌ <b>User not found.</b>",
            reply_markup=admin_back_keyboard(),
        )
        return

    from database import count_user_sessions
    sessions = await count_user_sessions(user["tg_id"])

    text = (
        f"👤 <b>User Info</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{user['tg_id']}</code>\n"
        f"👤 <b>Name:</b> {user['first_name']} "
        f"{user.get('last_name', '')}\n"
        f"📛 <b>Username:</b> "
        f"@{user['username'] or 'None'}\n"
        f"💎 <b>Credits:</b> {user['credits']:,}\n"
        f"💎 <b>VIP:</b> "
        f"{'✅' if user['is_vip'] else '❌'}\n"
        f"🚫 <b>Banned:</b> "
        f"{'✅' if user['is_banned'] else '❌'}\n"
        f"📱 <b>Sessions:</b> {sessions}\n"
        f"👥 <b>Referred:</b> "
        f"{user['total_referred']}\n"
        f"📅 <b>Joined:</b> {user['joined_at'][:10]}\n"
        f"🕐 <b>Last Active:</b> "
        f"{user['last_active'][:10]}"
    )

    from aiogram.types import InlineKeyboardMarkup
    from aiogram.types import InlineKeyboardButton
    from aiogram.enums import ButtonStyle

    uid = user["tg_id"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚫 Ban" if not user["is_banned"]
                else "✅ Unban",
                callback_data=f"toggle_ban_{uid}",
                style=ButtonStyle.DANGER
                if not user["is_banned"]
                else ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text="💎 Grant VIP"
                if not user["is_vip"]
                else "❌ Revoke VIP",
                callback_data=f"toggle_vip_{uid}",
                style=ButtonStyle.SUCCESS
                if not user["is_vip"]
                else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text="💰 Add Credits",
                callback_data=f"add_credits_{uid}",
                style=ButtonStyle.SUCCESS,
            ),
            InlineKeyboardButton(
                text="📋 View Logs",
                callback_data=f"view_user_logs_{uid}",
                style=ButtonStyle.PRIMARY,
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Back",
                callback_data="admin_users",
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ])

    await message.answer(text, reply_markup=kb)


@admin_router.callback_query(
    F.data.startswith("toggle_ban_")
)
async def toggle_ban_user(
    callback: CallbackQuery,
):
    """Toggle ban status for a user."""
    uid = int(callback.data.split("_")[-1])
    user = await get_user(uid)

    if not user:
        await callback.answer(
            "User not found.",
            show_alert=True
        )
        return

    if user["is_banned"]:
        await unban_user(uid)
        action = "Unbanned"
    else:
        await ban_user(uid)
        action = "Banned"

    await add_log(
        OWNER_ID,
        f"admin_{action.lower()}",
        f"User {uid}"
    )

    await callback.answer(
        f"✅ {action} user {uid}",
        show_alert=True
    )
    await callback.message.edit_text(
        f"✅ <b>User {action}</b>\n\n"
        f"User <code>{uid}</code> has been "
        f"{action.lower()}.",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data.startswith("toggle_vip_")
)
async def toggle_vip_user(callback: CallbackQuery):
    """Toggle VIP status for a user."""
    uid = int(callback.data.split("_")[-1])
    user = await get_user(uid)

    if not user:
        await callback.answer(
            "User not found.",
            show_alert=True
        )
        return

    if user["is_vip"]:
        await revoke_vip(uid)
        action = "VIP Revoked"
    else:
        await grant_vip(uid)
        action = "VIP Granted"

    await add_log(
        OWNER_ID,
        f"admin_{action.lower().replace(' ', '_')}",
        f"User {uid}"
    )

    await callback.answer(
        f"✅ {action} for user {uid}",
        show_alert=True
    )
    await callback.message.edit_text(
        f"✅ <b>{action}</b>\n\n"
        f"User <code>{uid}</code>.",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data.startswith("add_credits_")
)
async def admin_add_credits_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for credit amount to add."""
    uid = int(callback.data.split("_")[-1])
    await state.update_data(target_user_id=uid)
    await state.set_state(
        AdminUserStates.awaiting_credits_amount
    )

    await callback.message.edit_text(
        f"💰 <b>Add Credits</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Adding credits to user "
        f"<code>{uid}</code>\n\n"
        f"Send the amount to add:\n"
        f"<i>Example: 500</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminUserStates.awaiting_credits_amount
)
async def process_add_credits(
    message: Message,
    state: FSMContext
):
    """Process adding credits to user."""
    data = await state.get_data()
    uid = data.get("target_user_id")
    await state.clear()

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount. Please send a "
            "positive number.",
            reply_markup=admin_back_keyboard(),
        )
        return

    await add_credits(uid, amount)
    user = await get_user(uid)

    await add_log(
        OWNER_ID,
        "admin_add_credits",
        f"Added {amount} to user {uid}"
    )

    await message.answer(
        f"✅ <b>Credits Added</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"User: <code>{uid}</code>\n"
        f"Added: <b>+{amount:,}</b> credits\n"
        f"New Balance: <b>{user['credits']:,}</b>",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data.startswith("view_user_logs_")
)
async def view_user_logs(callback: CallbackQuery):
    """View logs for a specific user."""
    uid = int(callback.data.split("_")[-1])
    logs = await get_user_logs(uid, 15)

    if not logs:
        await callback.message.edit_text(
            f"📋 <b>No logs found for user "
            f"<code>{uid}</code></b>",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    log_text = ""
    for log in logs:
        log_text += (
            f"• <b>{log['action']}</b> — "
            f"{log['timestamp'][:16]}\n"
            f"  {log.get('detail', '')[:50]}\n\n"
        )

    await callback.message.edit_text(
        f"📋 <b>Logs for User "
        f"<code>{uid}</code></b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{log_text}",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_all_users")
async def admin_all_users(callback: CallbackQuery):
    """Show all users list."""
    users = await get_all_users()

    if not users:
        await callback.message.edit_text(
            "👥 <b>No users found.</b>",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    # Show first 20 users
    user_list = ""
    for user in users[:20]:
        status = ""
        if user["is_banned"]:
            status = "🚫"
        elif user["is_vip"]:
            status = "💎"
        else:
            status = "👤"

        name = user["first_name"] or "Unknown"
        username = (
            f"@{user['username']}"
            if user["username"]
            else "no username"
        )
        user_list += (
            f"{status} <code>{user['tg_id']}</code> "
            f"— {name} ({username})\n"
            f"   💎 {user['credits']:,} credits\n\n"
        )

    total = len(users)
    shown = min(20, total)

    await callback.message.edit_text(
        f"👥 <b>All Users</b> "
        f"(showing {shown}/{total})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{user_list}",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


# ============================================================
# BROADCAST
# ============================================================

@admin_router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for broadcast message."""
    await state.set_state(AdminUserStates.awaiting_broadcast)
    await callback.message.edit_text(
        "📣 <b>Broadcast Message</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the message to broadcast\n"
        "to ALL users.\n\n"
        "✨ Full formatting supported.\n\n"
        "⚠️ This will send to every user\n"
        "in the database."
    )
    await callback.answer()


@admin_router.message(AdminUserStates.awaiting_broadcast)
async def process_broadcast(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    """Execute broadcast to all users."""
    await state.clear()

    msg_text = message.text or message.caption or ""
    entities = message.entities or []

    users = await get_all_users()
    total = len(users)
    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"📣 <b>Broadcasting...</b>\n\n"
        f"Sending to {total:,} users...\n"
        f"Please wait."
    )

    for user in users:
        try:
            await bot.send_message(
                chat_id=user["tg_id"],
                text=msg_text,
                entities=entities,
            )
            sent += 1
            await micro_jitter(0.3)
        except Exception:
            failed += 1
            continue

        # Update progress every 50 users
        if sent % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"📣 <b>Broadcasting...</b>\n\n"
                    f"✅ Sent: {sent:,}\n"
                    f"❌ Failed: {failed:,}\n"
                    f"👥 Total: {total:,}"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Sent:</b> {sent:,}\n"
        f"❌ <b>Failed:</b> {failed:,}\n"
        f"👥 <b>Total:</b> {total:,}",
        reply_markup=admin_back_keyboard(),
    )

    await add_log(
        OWNER_ID,
        "broadcast",
        f"Sent: {sent}, Failed: {failed}"
    )


# ============================================================
# KEY MANAGEMENT
# ============================================================

@admin_router.callback_query(F.data == "admin_keys")
async def admin_keys_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show key management panel."""
    await state.clear()
    keys = await get_all_keys()
    active = sum(1 for k in keys if k["is_active"])

    await callback.message.edit_text(
        f"🔑 <b>Key Management</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Total keys: <b>{len(keys)}</b>\n"
        f"Active: <b>{active}</b>\n\n"
        f"Select an action:",
        reply_markup=admin_keys_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_create_key")
async def admin_create_key_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Start key creation flow."""
    await state.set_state(AdminKeyStates.awaiting_key_name)
    await callback.message.edit_text(
        "➕ <b>Create New Key</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1/3\n\n"
        "Send me the <b>key name</b>:\n\n"
        "<i>Example: PROMO2024, VIP100, TRIAL</i>"
    )
    await callback.answer()


@admin_router.message(AdminKeyStates.awaiting_key_name)
async def process_key_name(
    message: Message,
    state: FSMContext
):
    """Receive key name."""
    key_name = message.text.strip().upper()

    # Check if key already exists
    existing = await get_key_by_name(key_name)
    if existing:
        await message.answer(
            f"❌ Key <b>{key_name}</b> already exists.\n"
            f"Please choose a different name."
        )
        return

    await state.update_data(key_name=key_name)
    await state.set_state(AdminKeyStates.awaiting_key_credits)

    await message.answer(
        f"✅ Key name: <b>{key_name}</b>\n\n"
        f"Step 2/3\n\n"
        f"Send me the <b>credits</b> this key\n"
        f"will give when redeemed:\n\n"
        f"<i>Example: 500, 1000, 5000</i>"
    )


@admin_router.message(AdminKeyStates.awaiting_key_credits)
async def process_key_credits(
    message: Message,
    state: FSMContext
):
    """Receive key credits amount."""
    try:
        credits = int(message.text.strip())
        if credits <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount. Send a positive number."
        )
        return

    await state.update_data(credits=credits)
    await state.set_state(AdminKeyStates.awaiting_key_redeems)

    await message.answer(
        f"✅ Credits: <b>{credits:,}</b>\n\n"
        f"Step 3/3\n\n"
        f"Send me the <b>maximum number of\n"
        f"times</b> this key can be redeemed:\n\n"
        f"<i>Example: 1 (single use), "
        f"50, 100, 999</i>"
    )


@admin_router.message(AdminKeyStates.awaiting_key_redeems)
async def process_key_redeems(
    message: Message,
    state: FSMContext
):
    """Receive max redeems and create key."""
    try:
        max_redeems = int(message.text.strip())
        if max_redeems <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid number. Send a positive number."
        )
        return

    data = await state.get_data()
    await state.clear()

    key_name = data["key_name"]
    credits = data["credits"]

    # Create the key
    key = await create_key(key_name, credits, max_redeems)

    await add_log(
        OWNER_ID,
        "admin_create_key",
        f"Key: {key_name}, Credits: {credits}, "
        f"Max: {max_redeems}"
    )

    await message.answer(
        f"✅ <b>Key Created Successfully!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 <b>Key:</b> <code>{key_name}</code>\n"
        f"💎 <b>Credits:</b> {credits:,}\n"
        f"👥 <b>Max Redeems:</b> {max_redeems}\n"
        f"📅 <b>Created:</b> "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Share this key with your users! 🚀",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(F.data == "admin_view_keys")
async def admin_view_keys(callback: CallbackQuery):
    """Show all keys."""
    keys = await get_all_keys()

    if not keys:
        await callback.message.edit_text(
            "🔑 <b>No keys found.</b>\n\n"
            "Create one first!",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🔑 <b>All Keys</b> ({len(keys)} total)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tap a key to see details:",
        reply_markup=view_keys_keyboard(keys),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("admin_key_detail_")
)
async def admin_key_detail(callback: CallbackQuery):
    """Show key details."""
    key_id = int(callback.data.split("_")[-1])

    keys = await get_all_keys()
    key = next((k for k in keys if k["id"] == key_id), None)

    if not key:
        await callback.answer(
            "Key not found.",
            show_alert=True
        )
        return

    redeemers = await get_key_redeemers(key_id)
    remaining = key["max_redeems"] - key["redeemed_count"]

    redeemer_list = ""
    for r in redeemers[:5]:
        name = r.get("first_name", "Unknown")
        username = r.get("username", "")
        display = f"@{username}" if username else name
        date = r["redeemed_at"][:10]
        redeemer_list += f"• {display} — {date}\n"

    from aiogram.types import InlineKeyboardMarkup
    from aiogram.types import InlineKeyboardButton
    from aiogram.enums import ButtonStyle

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🗑️ Delete Key",
                callback_data=f"confirm_delete_key_{key_id}",
                style=ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Back",
                callback_data="admin_view_keys",
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ])

    await callback.message.edit_text(
        f"🔑 <b>Key Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>Name:</b> "
        f"<code>{key['key_name']}</code>\n"
        f"💎 <b>Credits:</b> {key['credits']:,}\n"
        f"👥 <b>Max Redeems:</b> "
        f"{key['max_redeems']}\n"
        f"✅ <b>Redeemed:</b> "
        f"{key['redeemed_count']}\n"
        f"🔢 <b>Remaining:</b> {remaining}\n"
        f"📅 <b>Created:</b> "
        f"{key['created_at'][:10]}\n\n"
        f"👥 <b>Recent Redeemers:</b>\n"
        f"{redeemer_list or 'None yet'}",
        reply_markup=kb,
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("confirm_delete_key_")
)
async def confirm_delete_key(callback: CallbackQuery):
    """Confirm key deletion."""
    key_id = int(callback.data.split("_")[-1])

    await callback.message.edit_text(
        "⚠️ <b>Confirm Delete</b>\n\n"
        "Are you sure you want to\n"
        "delete this key?",
        reply_markup=confirm_cancel_keyboard(
            confirm_data=f"execute_delete_key_{key_id}",
            cancel_data="admin_view_keys",
            confirm_text="🗑️ Yes, Delete",
            cancel_text="❌ Cancel",
        ),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("execute_delete_key_")
)
async def execute_delete_key(callback: CallbackQuery):
    """Delete a key."""
    key_id = int(callback.data.split("_")[-1])
    await delete_key(key_id)

    await add_log(
        OWNER_ID,
        "admin_delete_key",
        f"Key ID: {key_id}"
    )

    await callback.message.edit_text(
        "✅ <b>Key Deleted Successfully</b>",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer("Key deleted ✅")


@admin_router.callback_query(
    F.data == "admin_key_redeemers"
)
async def admin_key_redeemers_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for key name to see redeemers."""
    await state.set_state(
        AdminKeyStates.awaiting_redeemer_key
    )
    await callback.message.edit_text(
        "👥 <b>Who Redeemed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the <b>key name</b> to see\n"
        "who has redeemed it:"
    )
    await callback.answer()


@admin_router.message(
    AdminKeyStates.awaiting_redeemer_key
)
async def process_key_redeemers(
    message: Message,
    state: FSMContext
):
    """Show redeemers for a key."""
    await state.clear()
    key_name = message.text.strip().upper()

    key = await get_key_by_name(key_name)
    if not key:
        await message.answer(
            f"❌ Key <b>{key_name}</b> not found.",
            reply_markup=admin_back_keyboard(),
        )
        return

    redeemers = await get_key_redeemers(key["id"])

    if not redeemers:
        await message.answer(
            f"👥 <b>No redeemers yet</b> for "
            f"key <code>{key_name}</code>.",
            reply_markup=admin_back_keyboard(),
        )
        return

    redeemer_text = ""
    for i, r in enumerate(redeemers, 1):
        name = r.get("first_name", "Unknown")
        username = r.get("username", "")
        display = f"@{username}" if username else name
        uid = r["tg_id"]
        date = r["redeemed_at"][:10]
        redeemer_text += (
            f"{i}. {display} "
            f"(<code>{uid}</code>) — {date}\n"
        )

    await message.answer(
        f"👥 <b>Redeemers for "
        f"<code>{key_name}</code></b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{redeemer_text}",
        reply_markup=admin_back_keyboard(),
    )


# ============================================================
# FORCE SUBSCRIBE MANAGEMENT
# ============================================================

@admin_router.callback_query(F.data == "admin_forcesub")
async def admin_forcesub_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show force sub management panel."""
    await state.clear()
    channels = await get_force_channels()
    enabled = await get_config("force_sub_enabled")

    status = "✅ ON" if enabled == "1" else "❌ OFF"

    await callback.message.edit_text(
        f"📢 <b>Force Subscribe</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Status: <b>{status}</b>\n"
        f"Channels: <b>{len(channels)}</b>\n\n"
        f"Select an action:",
        reply_markup=admin_forcesub_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_toggle_forcesub"
)
async def toggle_force_sub(callback: CallbackQuery):
    """Toggle force subscribe on/off."""
    current = await get_config("force_sub_enabled")
    new_val = "0" if current == "1" else "1"
    await set_config("force_sub_enabled", new_val)

    status = "✅ ON" if new_val == "1" else "❌ OFF"
    await callback.answer(
        f"Force Sub is now {status}",
        show_alert=True
    )
    await admin_forcesub_handler(callback, None)


@admin_router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Ask if channel is public or private."""
    await callback.message.edit_text(
        "➕ <b>Add Force Subscribe Channel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Is this channel public or private?",
        reply_markup=channel_type_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "channel_public")
async def add_public_channel(
    callback: CallbackQuery,
    state: FSMContext
):
    """Add public channel flow."""
    await state.update_data(channel_type="public")
    await state.set_state(
        AdminForceSubStates.awaiting_channel_link
    )

    await callback.message.edit_text(
        "🌐 <b>Add Public Channel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the channel username:\n\n"
        "<i>Example: @yourchannel</i>"
    )
    await callback.answer()


@admin_router.callback_query(F.data == "channel_private")
async def add_private_channel(
    callback: CallbackQuery,
    state: FSMContext
):
    """Add private channel flow."""
    await state.update_data(channel_type="private")
    await state.set_state(
        AdminForceSubStates.awaiting_invite_link
    )

    await callback.message.edit_text(
        "🔒 <b>Add Private Channel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1/2\n\n"
        "Send me the <b>invite link</b>:\n\n"
        "<i>Example: https://t.me/+abc123xyz</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminForceSubStates.awaiting_invite_link
)
async def process_invite_link(
    message: Message,
    state: FSMContext
):
    """Receive invite link for private channel."""
    invite_link = message.text.strip()
    await state.update_data(invite_link=invite_link)
    await state.set_state(
        AdminForceSubStates.awaiting_channel_id
    )

    await message.answer(
        f"✅ Invite link saved.\n\n"
        f"Step 2/2\n\n"
        f"Send me the channel's <b>numeric ID</b>:\n\n"
        f"<i>Example: -1001234567890\n\n"
        f"To get the ID, forward a message\n"
        f"from the channel to @userinfobot</i>"
    )


@admin_router.message(
    AdminForceSubStates.awaiting_channel_id
)
async def process_channel_id(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    """Receive channel ID and save private channel."""
    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Invalid ID. Send the numeric ID.\n"
            "<i>Example: -1001234567890</i>"
        )
        return

    data = await state.get_data()
    await state.clear()

    invite_link = data.get("invite_link")

    # Try to get channel name
    channel_name = "Private Channel"
    try:
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title or "Private Channel"
    except Exception:
        pass

    await add_force_channel(
        channel_id=channel_id,
        channel_name=channel_name,
        channel_link=invite_link,
        invite_link=invite_link,
        is_public=False,
    )

    await add_log(
        OWNER_ID,
        "admin_add_channel",
        f"Private: {channel_id}"
    )

    await message.answer(
        f"✅ <b>Private Channel Added!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>Name:</b> {channel_name}\n"
        f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
        f"🔗 <b>Link:</b> {invite_link}",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.message(
    AdminForceSubStates.awaiting_channel_link
)
async def process_public_channel_link(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    """Receive and save public channel."""
    await state.clear()

    channel_link = message.text.strip()
    username = channel_link.lstrip("@").replace(
        "https://t.me/", ""
    )

    # Get channel info
    channel_name = username
    channel_id = None

    try:
        chat = await bot.get_chat(f"@{username}")
        channel_name = chat.title or username
        channel_id = chat.id
    except Exception as e:
        await message.answer(
            f"❌ Could not find channel.\n"
            f"Error: {str(e)}\n\n"
            f"Make sure the bot is in the channel.",
            reply_markup=admin_back_keyboard(),
        )
        return

    await add_force_channel(
        channel_id=channel_id,
        channel_name=channel_name,
        channel_link=f"https://t.me/{username}",
        invite_link=None,
        is_public=True,
    )

    await add_log(
        OWNER_ID,
        "admin_add_channel",
        f"Public: @{username}"
    )

    await message.answer(
        f"✅ <b>Public Channel Added!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>Name:</b> {channel_name}\n"
        f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
        f"🔗 <b>Link:</b> t.me/{username}",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_view_channels"
)
async def admin_view_channels(callback: CallbackQuery):
    """Show all force channels."""
    channels = await get_force_channels()

    if not channels:
        await callback.message.edit_text(
            "📢 <b>No channels added yet.</b>",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📢 <b>Force Channels</b> "
        f"({len(channels)} total)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tap to manage:",
        reply_markup=view_channels_keyboard(channels),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("admin_ch_detail_")
)
async def admin_channel_detail(callback: CallbackQuery):
    """Show channel details with remove option."""
    channel_id = int(callback.data.split("_")[-1])
    channels = await get_force_channels()
    ch = next(
        (c for c in channels
         if c["channel_id"] == channel_id),
        None
    )

    if not ch:
        await callback.answer(
            "Channel not found.",
            show_alert=True
        )
        return

    ch_type = "🌐 Public" if ch["is_public"] else "🔒 Private"

    await callback.message.edit_text(
        f"📢 <b>Channel Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>Name:</b> "
        f"{ch['channel_name'] or 'Unknown'}\n"
        f"🆔 <b>ID:</b> "
        f"<code>{ch['channel_id']}</code>\n"
        f"🔗 <b>Link:</b> {ch['channel_link']}\n"
        f"📋 <b>Type:</b> {ch_type}\n"
        f"📅 <b>Added:</b> {ch['added_at'][:10]}",
        reply_markup=confirm_cancel_keyboard(
            confirm_data=f"remove_channel_{channel_id}",
            cancel_data="admin_view_channels",
            confirm_text="🗑️ Remove Channel",
            cancel_text="🔙 Back",
        ),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("remove_channel_")
)
async def remove_force_channel(callback: CallbackQuery):
    """Remove a force channel."""
    channel_id = int(callback.data.split("_")[-1])
    await delete_force_channel(channel_id)

    await add_log(
        OWNER_ID,
        "admin_remove_channel",
        f"Channel ID: {channel_id}"
    )

    await callback.message.edit_text(
        "✅ <b>Channel Removed Successfully</b>",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer("Channel removed ✅")


# ============================================================
# PROXY ENGINE CONTROL
# ============================================================

@admin_router.callback_query(F.data == "admin_proxy")
async def admin_proxy_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show proxy engine panel."""
    await state.clear()
    proxy_count = await get_proxy_count()
    sources = await get_proxy_sources()
    hunter_enabled = await get_config("hunter_enabled")
    hunter_status = (
        "✅ Running"
        if hunter_enabled == "1"
        else "❌ Stopped"
    )

    await callback.message.edit_text(
        f"🌐 <b>Proxy Engine</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 <b>Hunter:</b> {hunter_status}\n"
        f"🌐 <b>Proxies in Pool:</b> {proxy_count:,}\n"
        f"📋 <b>Sources:</b> {len(sources)}\n\n"
        f"Select an action:",
        reply_markup=admin_proxy_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_proxy_stats"
)
async def admin_proxy_stats(callback: CallbackQuery):
    """Show detailed proxy stats."""
    count = await get_proxy_count()
    sources = await get_proxy_sources()
    hunter = await get_config("hunter_enabled")
    interval = await get_config("hunter_interval")
    timeout = await get_config("proxy_timeout")

    source_list = ""
    for s in sources[:5]:
        status = "✅" if s["is_active"] else "❌"
        last = s.get(
            "last_checked",
            "Never"
        )
        if last and last != "Never":
            last = last[:16]
        found = s.get("proxies_found", 0)
        source_list += (
            f"{status} Source #{s['id']} "
            f"— {found} found — {last}\n"
        )

    await callback.message.edit_text(
        f"📊 <b>Proxy Engine Stats</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 <b>Pool Size:</b> {count:,}\n"
        f"🔄 <b>Hunter:</b> "
        f"{'✅ ON' if hunter == '1' else '❌ OFF'}\n"
        f"⏱ <b>Hunt Interval:</b> {interval}s\n"
        f"⏰ <b>Proxy Timeout:</b> {timeout}s\n\n"
        f"📋 <b>Recent Sources:</b>\n"
        f"{source_list or 'No sources'}",
        reply_markup=admin_proxy_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_toggle_hunter"
)
async def toggle_hunter(callback: CallbackQuery):
    """Toggle proxy hunter on/off."""
    current = await get_config("hunter_enabled")
    new_val = "0" if current == "1" else "1"
    await set_config("hunter_enabled", new_val)

    status = "✅ ON" if new_val == "1" else "❌ OFF"
    await callback.answer(
        f"Hunter is now {status}",
        show_alert=True
    )
    await admin_proxy_handler(callback, None)


@admin_router.callback_query(
    F.data == "admin_force_hunt"
)
async def admin_force_hunt(callback: CallbackQuery):
    """Manually trigger proxy hunt."""
    await callback.message.edit_text(
        "⚡ <b>Force Hunt Started...</b>\n\n"
        "Hunting for fresh proxies.\n"
        "This may take a few minutes ⏳"
    )
    await callback.answer("Hunt started! ⚡")

    # Run hunt in background
    async def run_hunt():
        found = await force_hunt_now()
        try:
            count = await get_proxy_count()
            await callback.message.edit_text(
                f"✅ <b>Hunt Complete!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🌐 <b>New proxies found:</b> {found}\n"
                f"📦 <b>Total in pool:</b> {count:,}",
                reply_markup=admin_proxy_keyboard(),
            )
        except Exception:
            pass

    asyncio.create_task(run_hunt())


@admin_router.callback_query(
    F.data == "admin_clear_proxies"
)
async def admin_clear_proxies_confirm(
    callback: CallbackQuery
):
    """Confirm clear all proxies."""
    await callback.message.edit_text(
        "⚠️ <b>Clear All Proxies?</b>\n\n"
        "This will delete ALL proxies\n"
        "from the pool permanently.",
        reply_markup=confirm_cancel_keyboard(
            confirm_data="execute_clear_proxies",
            cancel_data="admin_proxy",
            confirm_text="🗑️ Yes, Clear All",
            cancel_text="❌ Cancel",
        ),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "execute_clear_proxies"
)
async def execute_clear_proxies(callback: CallbackQuery):
    """Execute clear all proxies."""
    await clear_proxies()

    await add_log(
        OWNER_ID,
        "admin_clear_proxies",
        "Cleared all proxies"
    )

    await callback.message.edit_text(
        "✅ <b>All Proxies Cleared</b>\n\n"
        "The proxy pool is now empty.\n"
        "Hunter will refill it automatically.",
        reply_markup=admin_proxy_keyboard(),
    )
    await callback.answer("Proxies cleared ✅")


@admin_router.callback_query(
    F.data == "admin_add_proxy_source"
)
async def admin_add_proxy_source_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Ask for new proxy source URL."""
    await state.set_state(
        AdminProxyStates.awaiting_proxy_source
    )
    await callback.message.edit_text(
        "➕ <b>Add Proxy Source</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me the URL of the proxy\n"
        "source to add:\n\n"
        "<i>Must return a plain text list\n"
        "of IP:PORT proxies or JSON.</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminProxyStates.awaiting_proxy_source
)
async def process_add_proxy_source(
    message: Message,
    state: FSMContext
):
    """Save new proxy source."""
    await state.clear()
    url = message.text.strip()

    await add_proxy_source(url)

    await add_log(
        OWNER_ID,
        "admin_add_proxy_source",
        url
    )

    await message.answer(
        f"✅ <b>Proxy Source Added!</b>\n\n"
        f"URL: <code>{url}</code>\n\n"
        f"The hunter will use this source\n"
        f"in the next cycle.",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_view_sources"
)
async def admin_view_sources(callback: CallbackQuery):
    """Show all proxy sources."""
    sources = await get_proxy_sources()

    if not sources:
        await callback.message.edit_text(
            "📋 <b>No custom sources added.</b>\n\n"
            "Default sources from config are active.",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📋 <b>Proxy Sources</b> "
        f"({len(sources)} custom)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Tap to manage:",
        reply_markup=view_sources_keyboard(sources),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("admin_source_detail_")
)
async def admin_source_detail(callback: CallbackQuery):
    """Show source details with delete option."""
    source_id = int(callback.data.split("_")[-1])
    sources = await get_proxy_sources()
    source = next(
        (s for s in sources if s["id"] == source_id),
        None
    )

    if not source:
        await callback.answer(
            "Source not found.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"📋 <b>Source Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> {source['id']}\n"
        f"🔗 <b>URL:</b>\n"
        f"<code>{source['url']}</code>\n\n"
        f"🌐 <b>Found:</b> "
        f"{source.get('proxies_found', 0)} proxies\n"
        f"🕐 <b>Last Check:</b> "
        f"{source.get('last_checked', 'Never')}",
        reply_markup=confirm_cancel_keyboard(
            confirm_data=f"delete_source_{source_id}",
            cancel_data="admin_view_sources",
            confirm_text="🗑️ Delete Source",
            cancel_text="🔙 Back",
        ),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("delete_source_")
)
async def delete_source(callback: CallbackQuery):
    """Delete a proxy source."""
    source_id = int(callback.data.split("_")[-1])
    await delete_proxy_source(source_id)

    await callback.message.edit_text(
        "✅ <b>Source Deleted</b>",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer("Source deleted ✅")


# ============================================================
# BOT SETTINGS
# ============================================================

@admin_router.callback_query(F.data == "admin_settings")
async def admin_settings_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show bot settings panel."""
    await state.clear()
    config = await get_all_config()

    api_status = (
        "✅ Set"
        if config.get("api_id")
        else "❌ Not Set"
    )

    await callback.message.edit_text(
        f"⚙️ <b>Bot Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 <b>API Credentials:</b> {api_status}\n"
        f"⚡ <b>Concurrency:</b> "
        f"{config.get('concurrency', 100)}\n"
        f"⏱ <b>DM Delay:</b> "
        f"{config.get('dm_delay_min')}–"
        f"{config.get('dm_delay_max')}s\n"
        f"💬 <b>Reply Delay:</b> "
        f"{config.get('reply_delay_min')}–"
        f"{config.get('reply_delay_max')}s\n"
        f"🕵️ <b>Stealth Level:</b> "
        f"{config.get('stealth_level', 3)}\n"
        f"🎁 <b>Free Credits:</b> "
        f"{config.get('free_credits', 100)}\n"
        f"📱 <b>Max Accounts:</b> "
        f"{config.get('max_accounts_per_user', 3)}\n"
        f"🔄 <b>Auto Reply:</b> "
        f"{'✅' if config.get('auto_reply_enabled') == '1' else '❌'}\n"
        f"⌨️ <b>Typing Sim:</b> "
        f"{'✅' if config.get('typing_sim_enabled') == '1' else '❌'}\n"
        f"🎯 <b>Refer System:</b> "
        f"{'✅' if config.get('refer_system_enabled') == '1' else '❌'}",
        reply_markup=admin_settings_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_set_api")
async def admin_set_api_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Start API credentials setup."""
    await state.set_state(
        AdminSettingsStates.awaiting_api_id
    )
    await callback.message.edit_text(
        "🔑 <b>Set API Credentials</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Step 1/2\n\n"
        "Send me the <b>API ID</b>:\n\n"
        "<i>Get it from my.telegram.org</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_api_id
)
async def process_api_id(
    message: Message,
    state: FSMContext
):
    """Receive API ID."""
    api_id = message.text.strip()

    try:
        int(api_id)
    except ValueError:
        await message.answer(
            "❌ Invalid API ID. Must be a number."
        )
        return

    await state.update_data(api_id=api_id)
    await state.set_state(
        AdminSettingsStates.awaiting_api_hash
    )

    await message.answer(
        f"✅ API ID saved.\n\n"
        f"Step 2/2\n\n"
        f"Send me the <b>API Hash</b>:"
    )


@admin_router.message(
    AdminSettingsStates.awaiting_api_hash
)
async def process_api_hash(
    message: Message,
    state: FSMContext
):
    """Receive API Hash and save both."""
    data = await state.get_data()
    await state.clear()

    api_id = data.get("api_id")
    api_hash = message.text.strip()

    await set_config("api_id", api_id)
    await set_config("api_hash", api_hash)

    await add_log(
        OWNER_ID,
        "admin_set_api",
        "API credentials updated"
    )

    await message.answer(
        "✅ <b>API Credentials Set!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔑 <b>API ID:</b> ✅ Saved\n"
        "🔒 <b>API Hash:</b> ✅ Saved\n\n"
        "All new user logins will use\n"
        "these credentials.",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_concurrency"
)
async def set_concurrency_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for concurrency value."""
    await state.set_state(
        AdminSettingsStates.awaiting_concurrency
    )
    current = await get_config("concurrency")
    await callback.message.edit_text(
        f"🔢 <b>Set Concurrency</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}</b>\n\n"
        f"Send the new concurrency limit:\n\n"
        f"<i>No limit. You can set any value.\n"
        f"Higher = faster but needs more resources.\n"
        f"Recommended: 100–500 for VPS</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_concurrency
)
async def process_concurrency(
    message: Message,
    state: FSMContext
):
    """Save new concurrency."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid value. Send a positive number."
        )
        return

    await set_config("concurrency", str(val))
    await refresh_semaphore()

    await message.answer(
        f"✅ <b>Concurrency Updated!</b>\n\n"
        f"New value: <b>{val}</b>\n\n"
        f"Applied immediately ⚡",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_dm_delay"
)
async def set_dm_delay_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for DM delay range."""
    await state.set_state(
        AdminSettingsStates.awaiting_dm_delay
    )
    min_d = await get_config("dm_delay_min")
    max_d = await get_config("dm_delay_max")

    await callback.message.edit_text(
        f"⏱ <b>Set DM Delay</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{min_d}–{max_d}s</b>\n\n"
        f"Send min and max delay in seconds:\n\n"
        f"<i>Format: MIN MAX\n"
        f"Example: 15 55</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_dm_delay
)
async def process_dm_delay(
    message: Message,
    state: FSMContext
):
    """Save DM delay range."""
    await state.clear()
    try:
        parts = message.text.strip().split()
        min_d = float(parts[0])
        max_d = float(parts[1])
        if min_d < 0 or max_d <= min_d:
            raise ValueError
    except (ValueError, IndexError):
        await message.answer(
            "❌ Invalid format.\n"
            "Send: <b>MIN MAX</b>\n"
            "Example: 15 55"
        )
        return

    await set_config("dm_delay_min", str(min_d))
    await set_config("dm_delay_max", str(max_d))

    await message.answer(
        f"✅ <b>DM Delay Updated!</b>\n\n"
        f"New range: <b>{min_d}–{max_d}s</b>",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_reply_delay"
)
async def set_reply_delay_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for reply delay range."""
    await state.set_state(
        AdminSettingsStates.awaiting_reply_delay
    )
    min_d = await get_config("reply_delay_min")
    max_d = await get_config("reply_delay_max")

    await callback.message.edit_text(
        f"💬 <b>Set Reply Delay</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{min_d}–{max_d}s</b>\n\n"
        f"Send min and max delay in seconds:\n\n"
        f"<i>Format: MIN MAX\n"
        f"Example: 6 18</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_reply_delay
)
async def process_reply_delay(
    message: Message,
    state: FSMContext
):
    """Save reply delay range."""
    await state.clear()
    try:
        parts = message.text.strip().split()
        min_d = float(parts[0])
        max_d = float(parts[1])
        if min_d < 0 or max_d <= min_d:
            raise ValueError
    except (ValueError, IndexError):
        await message.answer(
            "❌ Invalid format.\n"
            "Send: <b>MIN MAX</b>\n"
            "Example: 6 18"
        )
        return

    await set_config("reply_delay_min", str(min_d))
    await set_config("reply_delay_max", str(max_d))

    await message.answer(
        f"✅ <b>Reply Delay Updated!</b>\n\n"
        f"New range: <b>{min_d}–{max_d}s</b>",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_stealth"
)
async def set_stealth_prompt(callback: CallbackQuery):
    """Show stealth level selector."""
    current = await get_config("stealth_level")
    await callback.message.edit_text(
        f"🕵️ <b>Set Stealth Level</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>Level {current}</b>\n\n"
        f"Select new stealth level:",
        reply_markup=stealth_level_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("stealth_")
)
async def set_stealth_level(callback: CallbackQuery):
    """Save stealth level."""
    level = int(callback.data.split("_")[-1])
    await set_config("stealth_level", str(level))

    level_names = {
        1: "⚡ Level 1 - Fastest (Risky)",
        2: "🔥 Level 2 - Fast",
        3: "⚖️ Level 3 - Balanced",
        4: "🛡️ Level 4 - Safe",
        5: "🔒 Level 5 - Safest",
    }

    await callback.message.edit_text(
        f"✅ <b>Stealth Level Updated!</b>\n\n"
        f"New level: <b>{level_names[level]}</b>",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer(f"Stealth Level {level} set ✅")


@admin_router.callback_query(
    F.data == "admin_set_free_credits"
)
async def set_free_credits_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for free credits amount."""
    await state.set_state(
        AdminSettingsStates.awaiting_free_credits
    )
    current = await get_config("free_credits")
    await callback.message.edit_text(
        f"🎁 <b>Set Free Credits</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}</b> credits\n\n"
        f"Send new amount for new users:"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_free_credits
)
async def process_free_credits(
    message: Message,
    state: FSMContext
):
    """Save free credits setting."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid. Send a non-negative number."
        )
        return

    await set_config("free_credits", str(val))

    await message.answer(
        f"✅ <b>Free Credits Updated!</b>\n\n"
        f"New users will receive: <b>{val}</b> credits",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_max_accounts"
)
async def set_max_accounts_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for max accounts per user."""
    await state.set_state(
        AdminSettingsStates.awaiting_max_accounts
    )
    current = await get_config("max_accounts_per_user")
    await callback.message.edit_text(
        f"📱 <b>Set Max Accounts Per User</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}</b>\n"
        f"VIP gets: <b>{int(current)*2}</b>\n\n"
        f"Send new maximum:"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_max_accounts
)
async def process_max_accounts(
    message: Message,
    state: FSMContext
):
    """Save max accounts setting."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid. Send a positive number."
        )
        return

    await set_config("max_accounts_per_user", str(val))

    await message.answer(
        f"✅ <b>Max Accounts Updated!</b>\n\n"
        f"Normal users: <b>{val}</b>\n"
        f"VIP users: <b>{val*2}</b>",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_toggle_autoreply"
)
async def toggle_auto_reply(callback: CallbackQuery):
    """Toggle auto reply on/off."""
    current = await get_config("auto_reply_enabled")
    new_val = "0" if current == "1" else "1"
    await set_config("auto_reply_enabled", new_val)

    status = "✅ ON" if new_val == "1" else "❌ OFF"
    await callback.answer(
        f"Auto Reply is now {status}",
        show_alert=True
    )
    await admin_settings_handler(callback, None)


@admin_router.callback_query(
    F.data == "admin_toggle_typing"
)
async def toggle_typing_sim(callback: CallbackQuery):
    """Toggle typing simulation on/off."""
    current = await get_config("typing_sim_enabled")
    new_val = "0" if current == "1" else "1"
    await set_config("typing_sim_enabled", new_val)

    status = "✅ ON" if new_val == "1" else "❌ OFF"
    await callback.answer(
        f"Typing Simulation is now {status}",
        show_alert=True
    )
    await admin_settings_handler(callback, None)


@admin_router.callback_query(
    F.data == "admin_set_progress_interval"
)
async def set_progress_interval_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for progress update interval."""
    await state.set_state(
        AdminSettingsStates.awaiting_progress_interval
    )
    current = await get_config("progress_interval")
    await callback.message.edit_text(
        f"⏰ <b>Set Progress Interval</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}s</b>\n\n"
        f"How often to update the progress\n"
        f"message (in seconds):\n\n"
        f"<i>Recommended: 8–15 seconds</i>"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_progress_interval
)
async def process_progress_interval(
    message: Message,
    state: FSMContext
):
    """Save progress interval."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val < 1:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid. Send a positive number."
        )
        return

    await set_config("progress_interval", str(val))

    await message.answer(
        f"✅ <b>Progress Interval Updated!</b>\n\n"
        f"Updates every: <b>{val}s</b>",
        reply_markup=admin_back_keyboard(),
    )


# ============================================================
# REFER SETTINGS
# ============================================================

@admin_router.callback_query(
    F.data == "admin_refer_settings"
)
async def admin_refer_settings_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show refer system settings."""
    await state.clear()
    config = await get_all_config()

    refer_enabled = config.get(
        "refer_system_enabled", "1"
    )
    ref_credits = config.get("referral_credits", "10")
    bonus = config.get("new_user_bonus", "25")

    await callback.message.edit_text(
        f"🎯 <b>Refer & Earn Settings</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Status: "
        f"{'✅ ON' if refer_enabled == '1' else '❌ OFF'}\n"
        f"Credits/Referral: <b>{ref_credits}</b>\n"
        f"New User Bonus: <b>{bonus}</b>\n\n"
        f"Select action:",
        reply_markup=admin_refer_settings_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_toggle_refer"
)
async def toggle_refer_system(callback: CallbackQuery):
    """Toggle refer system on/off."""
    current = await get_config("refer_system_enabled")
    new_val = "0" if current == "1" else "1"
    await set_config("refer_system_enabled", new_val)

    status = "✅ ON" if new_val == "1" else "❌ OFF"
    await callback.answer(
        f"Refer System is now {status}",
        show_alert=True
    )
    await admin_refer_settings_handler(callback, None)


@admin_router.callback_query(
    F.data == "admin_set_referral_credits"
)
async def set_referral_credits_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for referral credits amount."""
    await state.set_state(
        AdminSettingsStates.awaiting_referral_credits
    )
    current = await get_config("referral_credits")
    await callback.message.edit_text(
        f"💎 <b>Set Credits Per Referral</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}</b> credits\n\n"
        f"Send new amount per referral:"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_referral_credits
)
async def process_referral_credits(
    message: Message,
    state: FSMContext
):
    """Save referral credits."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid. Send a non-negative number."
        )
        return

    await set_config("referral_credits", str(val))

    await message.answer(
        f"✅ <b>Referral Credits Updated!</b>\n\n"
        f"Each referral now gives: <b>{val}</b> credits",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_set_new_user_bonus"
)
async def set_new_user_bonus_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    """Prompt for new user bonus."""
    await state.set_state(
        AdminSettingsStates.awaiting_new_user_bonus
    )
    current = await get_config("new_user_bonus")
    await callback.message.edit_text(
        f"🎁 <b>Set New User Bonus</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <b>{current}</b> extra credits\n\n"
        f"Extra credits given when a user\n"
        f"joins via referral link:"
    )
    await callback.answer()


@admin_router.message(
    AdminSettingsStates.awaiting_new_user_bonus
)
async def process_new_user_bonus(
    message: Message,
    state: FSMContext
):
    """Save new user bonus."""
    await state.clear()
    try:
        val = int(message.text.strip())
        if val < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid. Send a non-negative number."
        )
        return

    await set_config("new_user_bonus", str(val))

    await message.answer(
        f"✅ <b>New User Bonus Updated!</b>\n\n"
        f"Referred users get extra: <b>{val}</b> credits",
        reply_markup=admin_back_keyboard(),
    )


@admin_router.callback_query(
    F.data == "admin_full_leaderboard"
)
async def admin_full_leaderboard(callback: CallbackQuery):
    """Show full referral leaderboard."""
    top = await get_top_referrers(20)

    if not top:
        await callback.message.edit_text(
            "🏆 <b>No referrals yet.</b>",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    board = ""
    for i, user in enumerate(top, 1):
        username = user.get("username", "")
        name = user.get(
            "first_name",
            f"User {user['tg_id']}"
        )
        display = f"@{username}" if username else name
        refs = user.get("referral_count", 0)
        credits = user.get("total_credits", 0)
        board += (
            f"{i}. {display} — "
            f"{refs} refs — "
            f"{credits} credits\n"
        )

    today = await get_referrals_today()

    await callback.message.edit_text(
        f"🏆 <b>Full Leaderboard (Top 20)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{board}\n\n"
        f"📊 <b>Referrals Today:</b> {today}",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_referrals_today"
)
async def admin_referrals_today(callback: CallbackQuery):
    """Show today's referral stats."""
    today = await get_referrals_today()
    credits = int(
        await get_config("referral_credits") or 10
    )
    earned = today * credits

    await callback.answer(
        f"📊 Referrals Today: {today}\n"
        f"💎 Credits Awarded: {earned}",
        show_alert=True
    )


# ============================================================
# LIVE STATS & MONITORING
# ============================================================

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(
    callback: CallbackQuery,
    state: FSMContext
):
    """Show live stats panel."""
    await state.clear()

    stats = await get_bot_stats()
    tasks = get_task_registry()
    proxy_count = await get_proxy_count()

    await callback.message.edit_text(
        f"📊 <b>Live Stats</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> "
        f"{stats['total_users']:,}\n"
        f"🆕 <b>New Today:</b> "
        f"{stats['new_users_today']:,}\n"
        f"🚫 <b>Banned:</b> "
        f"{stats['banned_users']:,}\n"
        f"💎 <b>VIP:</b> "
        f"{stats['vip_users']:,}\n"
        f"📱 <b>Sessions:</b> "
        f"{stats['active_sessions']:,}\n"
        f"🌐 <b>Proxies:</b> {proxy_count:,}\n"
        f"⚡ <b>Active Tasks:</b> {len(tasks)}\n"
        f"📨 <b>DMs Today:</b> "
        f"{stats['dms_today']:,}\n"
        f"🔑 <b>Active Keys:</b> "
        f"{stats['active_keys']:,}\n"
        f"🎯 <b>Referrals Today:</b> "
        f"{stats['referrals_today']:,}\n\n"
        f"🕐 <b>Updated:</b> "
        f"{datetime.now().strftime('%H:%M:%S')}",
        reply_markup=admin_stats_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "admin_active_tasks"
)
async def admin_active_tasks(callback: CallbackQuery):
    """Show all active tasks."""
    tasks = get_task_registry()

    if not tasks:
        await callback.message.edit_text(
            "⚡ <b>No Active Tasks</b>\n\n"
            "No campaigns or tasks running.",
            reply_markup=admin_stats_keyboard(),
        )
        await callback.answer()
        return

    task_list = ""
    for uid, info in tasks.items():
        elapsed = (
            datetime.now() - info["started_at"]
        ).seconds // 60
        task_list += (
            f"👤 User: <code>{uid}</code>\n"
            f"📋 Type: {info['type']}\n"
            f"📊 Progress: "
            f"{info['progress']:,}/{info['total']:,}\n"
            f"⏱ Running: {elapsed}m\n\n"
        )

    await callback.message.edit_text(
        f"⚡ <b>Active Tasks</b> "
        f"({len(tasks)} running)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{task_list}",
        reply_markup=active_tasks_keyboard(tasks),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data.startswith("kill_task_")
)
async def admin_kill_task(callback: CallbackQuery):
    """Kill a specific user's task."""
    uid = int(callback.data.split("_")[-1])
    killed = await kill_task(uid)

    if killed:
        await add_log(
            OWNER_ID,
            "admin_kill_task",
            f"Killed task for user {uid}"
        )
        await callback.answer(
            f"✅ Task for user {uid} killed.",
            show_alert=True
        )
    else:
        await callback.answer(
            "Task not found or already done.",
            show_alert=True
        )

    await admin_active_tasks(callback)


@admin_router.callback_query(F.data == "admin_kill_all")
async def admin_kill_all_tasks(callback: CallbackQuery):
    """Confirm kill all tasks."""
    await callback.message.edit_text(
        "🔴 <b>Kill ALL Tasks?</b>\n\n"
        "This will immediately stop ALL\n"
        "running campaigns for ALL users.\n\n"
        "⚠️ This cannot be undone.",
        reply_markup=confirm_cancel_keyboard(
            confirm_data="execute_kill_all",
            cancel_data="admin_stats",
            confirm_text="🔴 Yes, Kill All",
            cancel_text="❌ Cancel",
        ),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "execute_kill_all"
)
async def execute_kill_all(callback: CallbackQuery):
    """Execute kill all tasks."""
    count = await kill_all_tasks()

    await add_log(
        OWNER_ID,
        "admin_kill_all",
        f"Killed {count} tasks"
    )

    await callback.message.edit_text(
        f"🔴 <b>All Tasks Killed!</b>\n\n"
        f"Stopped <b>{count}</b> running tasks.",
        reply_markup=admin_stats_keyboard(),
    )
    await callback.answer(
        f"Killed {count} tasks ✅",
        show_alert=True
    )


# ============================================================
# VIEW LOGS
# ============================================================

@admin_router.callback_query(F.data == "admin_logs")
async def admin_logs_handler(callback: CallbackQuery):
    """Show recent logs."""
    logs = await get_recent_logs(30)

    if not logs:
        await callback.message.edit_text(
            "📋 <b>No logs found.</b>",
            reply_markup=admin_back_keyboard(),
        )
        await callback.answer()
        return

    log_text = ""
    for log in logs[:25]:
        username = log.get("username", "")
        user_display = (
            f"@{username}"
            if username
            else f"ID:{log.get('user_id', 'N/A')}"
        )
        log_text += (
            f"• <b>{log['action']}</b> "
            f"— {user_display}\n"
            f"  {log['timestamp'][:16]}\n\n"
        )

    await callback.message.edit_text(
        f"📋 <b>Recent Logs</b> (last 25)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{log_text}",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


# ============================================================
# OWNER SCRAPER (Owner Only Feature)
# ============================================================

@admin_router.message(F.text == "📤 Scrape Members")
async def owner_scrape_handler(
    message: Message,
    state: FSMContext
):
    """Owner-only scrape members flow."""
    from database import get_user_sessions
    sessions = await get_user_sessions(OWNER_ID)

    if not sessions:
        await message.answer(
            "📱 <b>No Account Connected</b>\n\n"
            "Add an account first.",
            reply_markup=back_to_main_inline(),
        )
        return

    from keyboards import session_select_keyboard
    await message.answer(
        "📤 <b>Scrape Members</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select the account to use:",
        reply_markup=session_select_keyboard(
            sessions,
            "ownscrape"
        ),
    )


@admin_router.callback_query(
    F.data.startswith("ownscrape_session_")
)
async def owner_scrape_session_selected(
    callback: CallbackQuery,
    state: FSMContext
):
    """Session selected for owner scrape."""
    session_id = int(callback.data.split("_")[-1])
    await state.update_data(session_id=session_id)

    from keyboards import scrape_type_keyboard
    await callback.message.edit_text(
        "📤 <b>What to Scrape?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select scrape type:",
        reply_markup=scrape_type_keyboard(),
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "scrape_members"
)
async def owner_scrape_members(
    callback: CallbackQuery,
    state: FSMContext
):
    """Start scrape members flow."""
    await state.update_data(scrape_type="members")
    await state.set_state(
        AdminScrapeStates.awaiting_target
    )

    await callback.message.edit_text(
        "🔗 <b>Enter Target</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the group/channel link\n"
        "or username to scrape:\n\n"
        "<i>Example:\n"
        "@groupname\n"
        "https://t.me/groupname</i>"
    )
    await callback.answer()


@admin_router.callback_query(
    F.data == "scrape_pending"
)
async def owner_scrape_pending(
    callback: CallbackQuery,
    state: FSMContext
):
    """Start scrape pending requests flow."""
    await state.update_data(scrape_type="pending")
    await state.set_state(
        AdminScrapeStates.awaiting_target
    )

    await callback.message.edit_text(
        "🔗 <b>Enter Channel Link</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the channel link to scrape\n"
        "pending join requests from:\n\n"
        "⚠️ Account must be <b>admin</b>\n"
        "in that channel."
    )
    await callback.answer()


@admin_router.message(AdminScrapeStates.awaiting_target)
async def owner_scrape_target_received(
    message: Message,
    state: FSMContext
):
    """Execute owner scrape."""
    target = message.text.strip()
    data = await state.get_data()
    await state.clear()

    session_id = data.get("session_id")
    scrape_type = data.get("scrape_type", "members")

    campaign_id = await create_campaign(
        user_id=OWNER_ID,
        session_id=session_id,
        campaign_type=f"scrape_{scrape_type}",
        total=0,
    )

    progress_msg = await message.answer(
        f"📤 <b>Scraping {scrape_type.title()}...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Target: <code>{target}</code>\n"
        f"Please wait ⏳"
    )

    start_time = datetime.now()

    async def progress_callback(current, total):
        try:
            bar = format_progress_bar(current, total)
            elapsed = (
                datetime.now() - start_time
            ).total_seconds()
            eta = format_eta(current, total, elapsed)

            await progress_msg.edit_text(
                f"📤 <b>Scraping...</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{bar}\n\n"
                f"✅ <b>Extracted:</b> {current:,}\n"
                f"👥 <b>Total:</b> {total:,}\n"
                f"🕐 <b>ETA:</b> {eta}"
            )
        except Exception:
            pass

    if scrape_type == "members":
        task = asyncio.create_task(
            scrape_members(
                user_id=OWNER_ID,
                session_id=session_id,
                target=target,
                campaign_id=campaign_id,
                progress_callback=progress_callback,
            )
        )
    else:
        task = asyncio.create_task(
            scrape_join_requests(
                user_id=OWNER_ID,
                session_id=session_id,
                target=target,
                campaign_id=campaign_id,
                progress_callback=progress_callback,
            )
        )

    register_task(
        user_id=OWNER_ID,
        task=task,
        task_type=f"scrape_{scrape_type}",
        total=0,
        campaign_id=campaign_id,
    )

    async def on_done(t):
        try:
            result = t.result()
            if result and result.get("success"):
                file_path = result.get("file_path")
                scraped = result.get(
                    "scraped",
                    result.get("total", 0)
                )
                with_username = result.get(
                    "with_username", 0
                )

                await progress_msg.edit_text(
                    f"✅ <b>Scrape Complete!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"✅ <b>Extracted:</b> {scraped:,}\n"
                    f"👤 <b>With Username:</b> "
                    f"{with_username:,}\n\n"
                    f"📁 Sending file..."
                )

                # Send file
                if file_path and os.path.exists(file_path):
                    await message.answer_document(
                        document=FSInputFile(file_path),
                        caption=(
                            f"📤 <b>Scrape Results</b>\n\n"
                            f"Target: <code>{target}</code>\n"
                            f"Total: {scraped:,} users\n"
                            f"With username: {with_username:,}"
                        ),
                    )
                    # Clean up file
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
            else:
                error = result.get(
                    "error", "Unknown error"
                ) if result else "Task failed"
                await progress_msg.edit_text(
                    f"❌ <b>Scrape Failed</b>\n\n"
                    f"{error}",
                    reply_markup=admin_back_keyboard(),
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Scrape task error: {e}")

    task.add_done_callback(
        lambda t: asyncio.create_task(on_done(t))
    )

    await message.answer(
        "⚡ <b>Scraping started in background!</b>\n"
        "You will receive the file when done.",
        reply_markup=admin_back_keyboard(),
    )


# ============================================================
# EXPORT ADMIN ROUTER
# ============================================================

__all__ = ["admin_router"]