# ============================================================
#         ZENKAI DMS FORWARDING BOT - HANDLERS
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
    BufferedInputFile,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import OWNER_ID, OWNER_USERNAME, BOT_NAME
from database import (
    get_user,
    get_user_sessions,
    count_user_sessions,
    get_dm_message,
    save_dm_message,
    get_config,
    deduct_credits,
    add_credits,
    redeem_key,
    get_user_referrals,
    get_top_referrers,
    get_user_referral_rank,
    get_user_campaigns,
    create_campaign,
    update_campaign,
    add_log,
)
from keyboards import (
    main_menu_keyboard,
    owner_main_menu_keyboard,
    force_sub_keyboard,
    confirm_cancel_keyboard,
    session_select_keyboard,
    remove_account_keyboard,
    campaign_source_keyboard,
    campaign_start_keyboard,
    campaign_running_keyboard,
    scrape_type_keyboard,
    how_to_use_keyboard,
    support_keyboard,
    create_own_bot_keyboard,
    vip_keyboard,
    refer_earn_keyboard,
    leaderboard_keyboard,
    referral_history_keyboard,
    my_stats_keyboard,
    my_account_keyboard,
    no_credits_keyboard,
    not_configured_keyboard,
    no_session_keyboard,
    accept_pending_keyboard,
    preview_message_keyboard,
    back_to_main_inline,
    delay_select_keyboard,
)
from userbot import (
    initiate_login,
    submit_phone,
    submit_code,
    submit_2fa,
    is_in_login_flow,
    get_login_state,
    clear_login_state,
    remove_session,
    get_sessions_info,
    load_client,
    release_client,
)
from engine import (
    run_mass_dm,
    run_join_request_dm,
    accept_pending_requests,
    register_task,
    get_user_task,
    kill_task,
    format_progress_bar,
    format_eta,
    get_dm_contacts,
    scrape_members,
    DELAY_PRESETS,
    get_pending_requesters,
)
from fingerprint import human_delay, micro_jitter

logger = logging.getLogger(__name__)
router = Router()


# ============================================================
# FSM STATES
# ============================================================

class LoginStates(StatesGroup):
    awaiting_phone = State()
    awaiting_code  = State()
    awaiting_2fa   = State()


class DMStates(StatesGroup):
    awaiting_dm_message    = State()
    awaiting_reply_message = State()


class CampaignStates(StatesGroup):
    awaiting_target      = State()
    awaiting_custom_list = State()
    awaiting_confirm     = State()
    awaiting_delay       = State()


class AcceptStates(StatesGroup):
    awaiting_channel_link = State()
    awaiting_confirm      = State()


class RedeemStates(StatesGroup):
    awaiting_key = State()


class JoinRequestDMStates(StatesGroup):
    awaiting_channel_link = State()
    awaiting_confirm      = State()


# ============================================================
# HELPERS
# ============================================================

async def get_main_menu(user_id: int):
    if user_id == OWNER_ID:
        return owner_main_menu_keyboard()
    return main_menu_keyboard()


async def get_user_photo(bot: Bot, user_id: int):
    try:
        photos = await bot.get_user_profile_photos(
            user_id=user_id,
            limit=1
        )
        if photos.total_count > 0:
            photo      = photos.photos[0][-1]
            file       = await bot.get_file(
                photo.file_id
            )
            downloaded = await bot.download_file(
                file.file_path
            )
            return BufferedInputFile(
                downloaded.read(),
                filename="profile.jpg"
            )
    except Exception:
        pass
    return None


def build_welcome_text(user, db_user: dict) -> str:
    credits    = db_user.get("credits", 100)
    user_id    = user.id
    first_name = user.first_name or "Friend"

    return (
        f"⚡ <b>𝗭𝗲𝗻𝗸𝗮𝗶 𝗗𝗠𝘀 𝗙𝗼𝗿𝘄𝗮𝗿𝗱𝗶𝗻𝗴 𝗕𝗼𝘁</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Hey <b>{first_name}</b>! 👋\n\n"
        f"🔥 <b>The Ultimate Telegram DM Toolkit</b>\n\n"
        f"📤 <b>Scrape</b> — Extract all members\n\n"
        f"📨 <b>Mass DM</b> — Personalized messages\n\n"
        f"🔑 <b>Auto Reply</b> — Smart follow-up\n\n"
        f"✅ <b>Accept Pending</b> — Accept requests\n\n"
        f"🎯 <b>Refer & Earn</b> — 10 credits/invite\n\n"
        f"🎁 <b>Your Credits:</b> <b>{credits}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>Credits:</b> {credits} "
        f"| 🆔 <b>ID:</b> <code>{user_id}</code>"
    )


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def start_handler(
    message: Message,
    bot: Bot,
    db_user: dict,
    state: FSMContext
):
    await state.clear()
    user     = message.from_user
    await micro_jitter(0.5)

    welcome  = build_welcome_text(user, db_user)
    keyboard = await get_main_menu(user.id)
    photo    = await get_user_photo(bot, user.id)

    await micro_jitter(0.4)

    if photo:
        await message.answer_photo(
            photo=photo,
            caption=welcome,
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            text=welcome,
            reply_markup=keyboard,
        )

    await add_log(user.id, "start", "User started bot")


# ============================================================
# MAIN MENU CALLBACK
# ============================================================

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(
    callback: CallbackQuery,
    bot: Bot,
    db_user: dict,
    state: FSMContext
):
    await state.clear()
    user     = callback.from_user
    welcome  = build_welcome_text(user, db_user)
    keyboard = await get_main_menu(user.id)
    photo    = await get_user_photo(bot, user.id)

    await micro_jitter(0.3)

    try:
        await callback.message.delete()
    except Exception:
        pass

    if photo:
        await callback.message.answer_photo(
            photo=photo,
            caption=welcome,
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer(
            text=welcome,
            reply_markup=keyboard,
        )

    await callback.answer()


# ============================================================
# CANCEL ACTION
# ============================================================

@router.callback_query(F.data == "cancel_action")
async def cancel_action_callback(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Action Cancelled</b>\n\n"
        "Use the menu below to continue.",
        reply_markup=back_to_main_inline(),
    )
    await callback.answer("Cancelled.")


# ============================================================
# ADD ACCOUNT
# ============================================================

@router.message(F.text == "➕ Add Account")
@router.callback_query(F.data == "add_account")
async def add_account_handler(
    event: Message | CallbackQuery,
    bot: Bot,
    db_user: dict,
    state: FSMContext
):
    user_id = event.from_user.id

    if user_id != OWNER_ID:
        max_accounts = int(
            await get_config(
                "max_accounts_per_user"
            ) or 3
        )
        if db_user.get("is_vip"):
            max_accounts = max_accounts * 2

        current = await count_user_sessions(user_id)
        if current >= max_accounts:
            text = (
                f"⚠️ <b>Account Limit Reached</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"You can add max "
                f"<b>{max_accounts}</b> accounts.\n\n"
                f"Remove one first."
            )
            kb = back_to_main_inline()
            if isinstance(event, Message):
                await event.answer(
                    text, reply_markup=kb
                )
            else:
                await event.message.edit_text(
                    text, reply_markup=kb
                )
                await event.answer()
            return

    api_id   = await get_config("api_id")
    api_hash = await get_config("api_hash")

    if not api_id or not api_hash:
        text = (
            "⚠️ <b>Bot Not Configured Yet</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Owner has not set API credentials.\n"
            "Please contact the owner."
        )
        kb = not_configured_keyboard(OWNER_USERNAME)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb)
        else:
            await event.message.edit_text(
                text, reply_markup=kb
            )
            await event.answer()
        return

    await micro_jitter(0.5)
    text = (
        "🔑 <b>Add Your Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Connecting to Telegram...\n"
        "Please wait ⏳"
    )

    if isinstance(event, Message):
        sent = await event.answer(text)
    else:
        await event.message.edit_text(text)
        sent = event.message
        await event.answer()

    result = await initiate_login(user_id)

    if not result["success"]:
        await sent.edit_text(
            f"❌ <b>Connection Failed</b>\n\n"
            f"{result['error']}\n\n"
            f"Please try again.",
            reply_markup=back_to_main_inline(),
        )
        return

    await state.set_state(LoginStates.awaiting_phone)

    await sent.edit_text(
        "✅ <b>Connected!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 Send your <b>phone number</b>\n"
        "with country code.\n\n"
        "<i>Example: +919876543210</i>"
    )


# ============================================================
# LOGIN - PHONE
# ============================================================

@router.message(LoginStates.awaiting_phone)
async def login_phone_handler(
    message: Message,
    state: FSMContext
):
    user_id = message.from_user.id
    phone   = message.text.strip()

    await micro_jitter(0.6)

    processing = await message.answer(
        "⏳ <b>Sending verification code...</b>"
    )

    result = await submit_phone(user_id, phone)

    if not result["success"]:
        await processing.edit_text(
            f"❌ <b>Failed</b>\n\n"
            f"{result['error']}\n\n"
            f"Please try again.",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()
        return

    await state.set_state(LoginStates.awaiting_code)

    await processing.edit_text(
        "📨 <b>Code Sent!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the <b>verification code</b>\n"
        "from your Telegram.\n\n"
        "<i>Example: 12345</i>"
    )


# ============================================================
# LOGIN - CODE
# ============================================================

@router.message(LoginStates.awaiting_code)
async def login_code_handler(
    message: Message,
    state: FSMContext
):
    user_id = message.from_user.id
    code    = message.text.strip()

    await micro_jitter(0.7)

    processing = await message.answer(
        "⏳ <b>Verifying code...</b>"
    )

    result = await submit_code(user_id, code)

    if not result["success"]:
        await processing.edit_text(
            f"❌ <b>Verification Failed</b>\n\n"
            f"{result['error']}\n\n"
            f"Please try again.",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()
        return

    if result.get("needs_2fa"):
        await state.set_state(LoginStates.awaiting_2fa)
        await processing.edit_text(
            "🔐 <b>2FA Required</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Send your <b>2FA password</b>:"
        )
        return

    await state.clear()
    phone = result.get("phone", "Unknown")

    await processing.edit_text(
        f"✅ <b>Account Added!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Phone:</b> <code>{phone}</code>\n\n"
        f"Ready to use! 🚀",
        reply_markup=back_to_main_inline(),
    )


# ============================================================
# LOGIN - 2FA
# ============================================================

@router.message(LoginStates.awaiting_2fa)
async def login_2fa_handler(
    message: Message,
    state: FSMContext
):
    user_id  = message.from_user.id
    password = message.text.strip()

    await micro_jitter(0.8)

    processing = await message.answer(
        "⏳ <b>Verifying 2FA password...</b>"
    )

    result = await submit_2fa(user_id, password)

    if not result["success"]:
        await processing.edit_text(
            f"❌ <b>2FA Failed</b>\n\n"
            f"{result['error']}\n\n"
            f"Please try again.",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()
        return

    await state.clear()
    phone = result.get("phone", "Unknown")

    await processing.edit_text(
        f"✅ <b>Account Added!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>Phone:</b> <code>{phone}</code>\n"
        f"🔐 <b>2FA:</b> ✅ Verified\n\n"
        f"Ready to use! 🚀",
        reply_markup=back_to_main_inline(),
    )


# ============================================================
# REMOVE ACCOUNT
# ============================================================

@router.message(F.text == "➖ Remove Account")
@router.callback_query(F.data == "remove_account")
async def remove_account_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    user_id  = event.from_user.id
    await state.clear()

    sessions = await get_sessions_info(user_id)

    if not sessions:
        text = (
            "📱 <b>No Accounts Found</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You have no accounts connected."
        )
        kb = no_session_keyboard()
        if isinstance(event, Message):
            await event.answer(text, reply_markup=kb)
        else:
            await event.message.edit_text(
                text, reply_markup=kb
            )
            await event.answer()
        return

    text = (
        "➖ <b>Remove Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select account to remove:\n\n"
        "⚠️ Cannot be undone."
    )
    kb = remove_account_keyboard(sessions)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(
            text, reply_markup=kb
        )
        await event.answer()


@router.callback_query(
    F.data.startswith("remove_session_")
)
async def confirm_remove_session(
    callback: CallbackQuery,
    state: FSMContext
):
    session_id = int(callback.data.split("_")[-1])
    await state.update_data(session_id=session_id)

    await callback.message.edit_text(
        "⚠️ <b>Confirm Removal</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Remove this account?",
        reply_markup=confirm_cancel_keyboard(
            confirm_data=f"confirm_remove_{session_id}",
            cancel_data="cancel_action",
            confirm_text="✅ Yes, Remove",
            cancel_text="❌ Cancel",
        ),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("confirm_remove_")
)
async def execute_remove_session(
    callback: CallbackQuery,
    state: FSMContext
):
    session_id = int(callback.data.split("_")[-1])
    user_id    = callback.from_user.id

    await callback.message.edit_text(
        "⏳ <b>Removing account...</b>"
    )

    result = await remove_session(user_id, session_id)

    if result["success"]:
        await callback.message.edit_text(
            f"✅ <b>Account Removed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 {result['phone']} removed.",
            reply_markup=back_to_main_inline(),
        )
    else:
        await callback.message.edit_text(
            f"❌ <b>Removal Failed</b>\n\n"
            f"{result['error']}",
            reply_markup=back_to_main_inline(),
        )
    await callback.answer()


# ============================================================
# MY ACCOUNT
# ============================================================

@router.message(F.text == "👤 My Account")
@router.callback_query(F.data == "my_account")
async def my_account_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    user_id  = event.from_user.id
    sessions = await get_sessions_info(user_id)

    if not sessions:
        text = (
            "👤 <b>My Account</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No accounts connected.\n\n"
            "Tap <b>Add Account</b> to start."
        )
    else:
        session_list = ""
        for s in sessions:
            session_list += (
                f"📱 <code>{s['phone']}</code>\n"
                f"   📟 {s['device']}\n"
                f"   📅 {s['created_at'][:10]}\n\n"
            )

        text = (
            f"👤 <b>My Accounts</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{session_list}"
            f"Total: <b>{len(sessions)}</b>"
        )

    kb = my_account_keyboard()
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(
            text, reply_markup=kb
        )
        await event.answer()


# ============================================================
# SET DM MESSAGE
# ============================================================

@router.message(F.text == "✉️ Set DM Message")
@router.callback_query(F.data == "edit_dm_message")
async def set_dm_message_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    await state.set_state(DMStates.awaiting_dm_message)

    text = (
        "✉️ <b>Set Mass DM Message</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send me your campaign message.\n\n"
        "✨ Full formatting supported:\n"
        "Bold, Italic, Links, Emojis!\n\n"
        "Preserved <b>100% exactly</b>."
    )

    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.edit_text(text)
        await event.answer()


@router.message(DMStates.awaiting_dm_message)
async def receive_dm_message(
    message: Message,
    state: FSMContext
):
    user_id  = message.from_user.id
    msg_text = message.text or message.caption or ""
    entities = (
        message.entities
        or message.caption_entities
        or []
    )

    entities_data = []
    for entity in entities:
        entities_data.append({
            "type":   entity.type.value,
            "offset": entity.offset,
            "length": entity.length,
            "url":    getattr(entity, "url", None),
        })

    entities_json = json.dumps(
        entities_data,
        ensure_ascii=False
    )

    await save_dm_message(
        user_id=user_id,
        message_text=msg_text,
        message_entities=entities_json,
        msg_type="initial",
    )

    await state.clear()

    await message.answer(
        "✅ <b>DM Message Saved!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "All formatting preserved ✨",
        reply_markup=preview_message_keyboard(),
    )


# ============================================================
# SET AUTO REPLY
# ============================================================

@router.message(F.text == "💬 Set Auto Reply")
@router.callback_query(F.data == "edit_auto_reply")
async def set_auto_reply_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    await state.set_state(DMStates.awaiting_reply_message)

    text = (
        "💬 <b>Set Auto Reply Message</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the follow-up message sent\n"
        "when someone replies to your DM.\n\n"
        "✨ Full formatting supported!"
    )

    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.message.edit_text(text)
        await event.answer()


@router.message(DMStates.awaiting_reply_message)
async def receive_reply_message(
    message: Message,
    state: FSMContext
):
    user_id  = message.from_user.id
    msg_text = message.text or message.caption or ""
    entities = (
        message.entities
        or message.caption_entities
        or []
    )

    entities_data = []
    for entity in entities:
        entities_data.append({
            "type":   entity.type.value,
            "offset": entity.offset,
            "length": entity.length,
            "url":    getattr(entity, "url", None),
        })

    entities_json = json.dumps(
        entities_data,
        ensure_ascii=False
    )

    await save_dm_message(
        user_id=user_id,
        message_text=msg_text,
        message_entities=entities_json,
        msg_type="reply",
    )

    await state.clear()

    await message.answer(
        "✅ <b>Auto Reply Saved!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Saved with all formatting ✨",
        reply_markup=preview_message_keyboard(),
    )


# ============================================================
# PREVIEW MESSAGE
# ============================================================

@router.message(F.text == "👁️ Preview Message")
@router.callback_query(F.data == "preview_message")
async def preview_message_handler(
    event: Message | CallbackQuery,
    state: FSMContext
):
    user_id = event.from_user.id

    dm_msg    = await get_dm_message(user_id, "initial")
    reply_msg = await get_dm_message(user_id, "reply")

    if isinstance(event, Message):
        target = event
    else:
        target = event.message
        await event.answer()

    await target.answer(
        "👁️ <b>Message Preview</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📨 <b>Your Mass DM Message:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    if dm_msg:
        await target.answer(dm_msg["message_text"])
    else:
        await target.answer(
            "❌ <i>No DM message set yet.</i>"
        )

    await target.answer(
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💬 <b>Your Auto Reply Message:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    if reply_msg:
        await target.answer(reply_msg["message_text"])
    else:
        await target.answer(
            "❌ <i>No auto-reply set yet.</i>"
        )

    await target.answer(
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=preview_message_keyboard(),
    )


# ============================================================
# START MASS DM CAMPAIGN
# ============================================================

@router.message(F.text == "🚀 Start Mass DM Campaign")
async def start_campaign_handler(
    message: Message,
    db_user: dict,
    state: FSMContext
):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        if (
            db_user["credits"] <= 0
            and not db_user["is_vip"]
        ):
            await message.answer(
                "💎 <b>No Credits Remaining</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "You have <b>0 credits</b> left.\n\n"
                "🎫 Redeem a key\n"
                "🎯 Refer friends\n"
                "💎 Go VIP for unlimited",
                reply_markup=no_credits_keyboard(),
            )
            return

    sessions = await get_sessions_info(user_id)
    if not sessions:
        await message.answer(
            "📱 <b>No Account Connected</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Connect an account first.",
            reply_markup=no_session_keyboard(),
        )
        return

    dm_msg = await get_dm_message(user_id, "initial")
    if not dm_msg:
        await message.answer(
            "✉️ <b>No DM Message Set</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Set your DM message first.",
            reply_markup=back_to_main_inline(),
        )
        return

    existing_task = get_user_task(user_id)
    if existing_task:
        await message.answer(
            "⚠️ <b>Campaign Already Running</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Type: {existing_task['type']}\n"
            f"Progress: "
            f"{existing_task['progress']}/"
            f"{existing_task['total']}",
            reply_markup=campaign_running_keyboard(
                existing_task.get("campaign_id", 0)
            ),
        )
        return

    await message.answer(
        "🚀 <b>Start Mass DM Campaign</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select the account to use:",
        reply_markup=session_select_keyboard(
            sessions, "campaign"
        ),
    )


@router.callback_query(
    F.data.startswith("campaign_session_")
)
async def campaign_session_selected(
    callback: CallbackQuery,
    state: FSMContext
):
    session_id = int(callback.data.split("_")[-1])
    await state.update_data(session_id=session_id)

    await callback.message.edit_text(
        "📋 <b>Select Target List</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Where to send messages?",
        reply_markup=campaign_source_keyboard(),
    )
    await callback.answer()


# ============================================================
# SOURCE: DM CONTACTS
# ============================================================

@router.callback_query(F.data == "source_dm_contacts")
async def campaign_dm_contacts_source(
    callback: CallbackQuery,
    state: FSMContext,
    db_user: dict
):
    user_id    = callback.from_user.id
    data       = await state.get_data()
    session_id = data.get("session_id")

    await callback.message.edit_text(
        "💬 <b>Fetching DM Contacts...</b>\n\n"
        "Reading conversations. Please wait ⏳"
    )
    await callback.answer()

    contacts = await get_dm_contacts(session_id)

    if not contacts:
        await callback.message.edit_text(
            "❌ <b>No DM Contacts Found</b>\n\n"
            "No existing DM conversations.",
            reply_markup=back_to_main_inline(),
        )
        return

    seen            = set()
    unique_contacts = []
    for c in contacts:
        if c["user_id"] not in seen:
            seen.add(c["user_id"])
            unique_contacts.append(c)

    total      = len(unique_contacts)
    target_ids = [c["user_id"] for c in unique_contacts]

    await state.update_data(
        targets=target_ids,
        source="dm_contacts",
        total=total,
    )

    is_owner     = user_id == OWNER_ID
    is_vip       = db_user["is_vip"]
    user_credits = db_user["credits"]

    credit_line = ""
    if not is_owner and not is_vip:
        credit_line = (
            f"💎 <b>Credits needed:</b> {total:,}\n"
            f"💰 <b>Your credits:</b> {user_credits:,}\n\n"
        )
        if user_credits < total:
            await callback.message.edit_text(
                f"❌ <b>Insufficient Credits</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Need <b>{total:,}</b> but have "
                f"<b>{user_credits:,}</b>.",
                reply_markup=no_credits_keyboard(),
            )
            await state.clear()
            return

    dm_msg    = await get_dm_message(user_id, "initial")
    reply_msg = await get_dm_message(user_id, "reply")

    await state.set_state(CampaignStates.awaiting_delay)
    await callback.message.edit_text(
        f"✅ <b>Analysis Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 <b>DM Contacts:</b> {total:,}\n"
        f"{credit_line}"
        f"✉️ <b>DM Message:</b> "
        f"{'✅ Set' if dm_msg else '❌ Not Set'}\n"
        f"💬 <b>Auto Reply:</b> "
        f"{'✅ Set' if reply_msg else '❌ Not Set'}\n\n"
        f"⚡ <b>Select sending speed:</b>",
        reply_markup=delay_select_keyboard(),
    )


# ============================================================
# SOURCE: CUSTOM LIST
# ============================================================

@router.callback_query(F.data == "source_custom")
async def campaign_custom_list(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(
        CampaignStates.awaiting_custom_list
    )
    await callback.message.edit_text(
        "📋 <b>Upload Target List</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send a <b>.txt file</b> with one\n"
        "username or user_id per line.\n\n"
        "<i>@username1\n"
        "123456789</i>"
    )
    await callback.answer()


@router.message(CampaignStates.awaiting_custom_list)
async def receive_custom_list(
    message: Message,
    state: FSMContext,
    db_user: dict
):
    user_id = message.from_user.id

    if not message.document:
        await message.answer(
            "❌ Please send a <b>.txt file</b>."
        )
        return

    bot        = message.bot
    file       = await bot.get_file(
        message.document.file_id
    )
    downloaded = await bot.download_file(file.file_path)
    content    = downloaded.read().decode(
        "utf-8", errors="ignore"
    )

    targets = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if line:
            targets.append(line.lstrip("@"))

    targets = list(set(targets))

    if not targets:
        await message.answer(
            "❌ <b>No valid targets found.</b>"
        )
        return

    await state.update_data(
        targets=targets,
        source="custom",
        total=len(targets),
    )

    credits_needed = len(targets)
    user_credits   = db_user["credits"]
    is_vip         = db_user["is_vip"]
    is_owner       = user_id == OWNER_ID

    credit_line = ""
    if not is_owner and not is_vip:
        credit_line = (
            f"💎 <b>Credits needed:</b> {credits_needed}\n"
            f"💰 <b>Your credits:</b> {user_credits}\n\n"
        )
        if user_credits < credits_needed:
            await message.answer(
                f"❌ <b>Insufficient Credits</b>\n\n"
                f"Need <b>{credits_needed}</b> but "
                f"have <b>{user_credits}</b>.",
                reply_markup=no_credits_keyboard(),
            )
            await state.clear()
            return

    await state.set_state(CampaignStates.awaiting_delay)
    await message.answer(
        f"✅ <b>Analysis Complete</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Targets:</b> {len(targets)}\n"
        f"{credit_line}"
        f"⚡ <b>Select sending speed:</b>",
        reply_markup=delay_select_keyboard(),
    )


# ============================================================
# SOURCE: SCRAPED GROUP
# ============================================================

@router.callback_query(F.data == "source_scraped")
async def campaign_scraped_source(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(CampaignStates.awaiting_target)
    await state.update_data(source="scraped")
    await callback.message.edit_text(
        "🔗 <b>Enter Target</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the group or channel link\n"
        "to scrape and DM members.\n\n"
        "<i>@groupname or t.me/link</i>"
    )
    await callback.answer()


@router.callback_query(F.data == "source_join_request")
async def campaign_join_request_source(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(
        JoinRequestDMStates.awaiting_channel_link
    )
    await callback.message.edit_text(
        "🔗 <b>Enter Channel Link</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send channel link to DM pending users.\n\n"
        "⚠️ Account must be <b>admin</b>."
    )
    await callback.answer()


@router.message(CampaignStates.awaiting_target)
async def campaign_target_received(
    message: Message,
    state: FSMContext,
    db_user: dict
):
    user_id    = message.from_user.id
    target     = message.text.strip()
    data       = await state.get_data()
    session_id = data.get("session_id")

    processing = await message.answer(
        "🔍 <b>Analyzing target...</b>\n"
        "Counting members ⏳"
    )

    try:
        from telethon.tl.functions.channels import (
            GetFullChannelRequest
        )

        client = await load_client(session_id)
        entity = await client.get_entity(target)
        full   = await client(
            GetFullChannelRequest(channel=entity)
        )
        total  = full.full_chat.participants_count
        await release_client(session_id, client)

        await state.update_data(
            target=target,
            total=total,
            source="scraped"
        )

        is_owner     = user_id == OWNER_ID
        is_vip       = db_user["is_vip"]
        user_credits = db_user["credits"]

        credit_line = ""
        if not is_owner and not is_vip:
            credit_line = (
                f"💎 <b>Credits needed:</b> {total}\n"
                f"💰 <b>Your credits:</b> {user_credits}\n\n"
            )
            if user_credits < total:
                await processing.edit_text(
                    f"❌ <b>Insufficient Credits</b>\n\n"
                    f"Need <b>{total}</b> but "
                    f"have <b>{user_credits}</b>.",
                    reply_markup=no_credits_keyboard(),
                )
                await state.clear()
                return

        await state.set_state(
            CampaignStates.awaiting_delay
        )
        await processing.edit_text(
            f"✅ <b>Analysis Complete</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 <b>Total members:</b> {total:,}\n"
            f"{credit_line}"
            f"⚡ <b>Select sending speed:</b>",
            reply_markup=delay_select_keyboard(),
        )

    except Exception as e:
        await processing.edit_text(
            f"❌ <b>Failed to analyze</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"• Check the link\n"
            f"• Make sure account is a member",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()


# ============================================================
# DELAY SELECTION
# ============================================================

@router.callback_query(F.data.startswith("delay_"))
async def delay_selected(
    callback: CallbackQuery,
    state: FSMContext
):
    preset = callback.data.split("_")[1]

    await state.update_data(delay_preset=preset)

    labels = {
        "fast":   "⚡ Fast (5–15s)",
        "medium": "⚖️ Medium (15–45s)",
        "slow":   "🐢 Slow (45–120s)",
    }

    await callback.message.edit_text(
        f"✅ <b>Speed Selected:</b> "
        f"{labels.get(preset, 'Medium')}\n\n"
        f"Ready to start campaign?",
        reply_markup=campaign_start_keyboard(),
    )
    await callback.answer(
        f"Speed: {labels.get(preset, preset)}"
    )


# ============================================================
# EXECUTE CAMPAIGN
# ============================================================

@router.callback_query(F.data == "start_campaign")
async def execute_campaign(
    callback: CallbackQuery,
    state: FSMContext,
    db_user: dict
):
    user_id = callback.from_user.id
    data    = await state.get_data()
    await state.clear()

    # ── DEBUG LOG ────────────────────────────────
    logger.info(
        f"===> execute_campaign STARTED "
        f"user={user_id} "
        f"source={data.get('source')} "
        f"target={data.get('target')} "
        f"targets_count={len(data.get('targets', []))} "
        f"total={data.get('total')} "
        f"delay={data.get('delay_preset')} "
        f"session_id={data.get('session_id')}"
    )

    session_id   = data.get("session_id")
    source       = data.get("source")
    target       = data.get("target")
    targets      = data.get("targets", [])
    total        = data.get("total", len(targets))
    delay_preset = data.get("delay_preset", "medium")

    dm_msg    = await get_dm_message(user_id, "initial")
    reply_msg = await get_dm_message(user_id, "reply")

    if not dm_msg:
        await callback.message.edit_text(
            "❌ <b>No DM Message Set</b>\n\n"
            "Set your DM message first.",
            reply_markup=back_to_main_inline(),
        )
        await callback.answer()
        return

    msg_entities   = json.loads(
        dm_msg["message_entities"] or "[]"
    )
    reply_entities = json.loads(
        reply_msg["message_entities"]
        if reply_msg else "[]"
    )

    campaign_id = await create_campaign(
        user_id=user_id,
        session_id=session_id,
        campaign_type=source,
        total=total,
    )

    preset_labels = {
        "fast":   "⚡ Fast",
        "medium": "⚖️ Medium",
        "slow":   "🐢 Slow",
    }

    progress_msg = await callback.message.edit_text(
        f"🚀 <b>Campaign Started!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{format_progress_bar(0, total)}\n\n"
        f"📨 <b>Sent:</b> 0\n"
        f"❌ <b>Failed:</b> 0\n"
        f"👥 <b>Total:</b> {total:,}\n"
        f"⚡ <b>Speed:</b> "
        f"{preset_labels.get(delay_preset, 'Medium')}\n"
        f"⏳ <b>Status:</b> Starting...",
        reply_markup=campaign_running_keyboard(
            campaign_id
        ),
    )

    await callback.answer("Campaign started! 🚀")

    start_time = datetime.now()

    async def progress_callback(
        sent, total_count,
        failed=0, peer_flood=False
    ):
        try:
            elapsed = (
                datetime.now() - start_time
            ).total_seconds()
            eta     = format_eta(
                sent, total_count, elapsed
            )
            bar     = format_progress_bar(
                sent, total_count
            )
            speed   = (
                int(sent / elapsed * 60)
                if elapsed > 0 else 0
            )
            status  = "Running 🟢"
            if peer_flood:
                status = "⚠️ PeerFlood!"

            await progress_msg.edit_text(
                f"🚀 <b>Campaign Running</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{bar}\n\n"
                f"📨 <b>Sent:</b> {sent:,}\n"
                f"❌ <b>Failed:</b> {failed:,}\n"
                f"👥 <b>Total:</b> {total_count:,}\n"
                f"⚡ <b>Speed:</b> "
                f"{preset_labels.get(delay_preset, 'Medium')}\n"
                f"🏃 <b>Rate:</b> ~{speed}/min\n"
                f"🕐 <b>ETA:</b> {eta}\n"
                f"📊 <b>Status:</b> {status}",
                reply_markup=campaign_running_keyboard(
                    campaign_id
                ),
            )
        except Exception:
            pass

    # ── SCRAPED SOURCE ────────────────────────────
    if source == "scraped" and target:
        logger.info(
            f"===> Creating scrape_and_dm task"
        )

        async def scrape_and_dm():
            scrape_result = await scrape_members(
                user_id=user_id,
                session_id=session_id,
                target=target,
                campaign_id=campaign_id,
                progress_callback=None,
            )

            if not scrape_result.get("success"):
                try:
                    await progress_msg.edit_text(
                        f"❌ <b>Scrape Failed</b>\n\n"
                        f"{scrape_result.get('error', 'Unknown')}",
                        reply_markup=back_to_main_inline(),
                    )
                except Exception:
                    pass
                return

            scraped_members = scrape_result.get(
                "members", []
            )
            scraped_targets = [
                m["username"]
                if m.get("username")
                else m["user_id"]
                for m in scraped_members
                if not m.get("is_bot", False)
            ]

            if not scraped_targets:
                try:
                    await progress_msg.edit_text(
                        "❌ <b>No valid targets</b>\n\n"
                        "All members are bots.",
                        reply_markup=back_to_main_inline(),
                    )
                except Exception:
                    pass
                return

            actual_total = len(scraped_targets)
            await update_campaign(
                campaign_id, total=actual_total
            )

            result = await run_mass_dm(
                user_id=user_id,
                session_id=session_id,
                targets=scraped_targets,
                campaign_id=campaign_id,
                message_text=dm_msg["message_text"],
                message_entities=msg_entities,
                auto_reply_text=reply_msg[
                    "message_text"
                ] if reply_msg else None,
                auto_reply_entities=reply_entities,
                progress_callback=progress_callback,
                delay_preset=delay_preset,
            )

            try:
                if result and result.get("success"):
                    await progress_msg.edit_text(
                        f"✅ <b>Campaign Complete!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📨 <b>Sent:</b> "
                        f"{result.get('sent', 0):,}\n"
                        f"❌ <b>Failed:</b> "
                        f"{result.get('failed', 0):,}\n"
                        f"👥 <b>Total:</b> "
                        f"{actual_total:,}\n\n"
                        f"{'⚠️ PeerFlood hit' if result.get('peer_flood') else ''}",
                        reply_markup=back_to_main_inline(),
                    )
            except Exception:
                pass

        task = asyncio.create_task(scrape_and_dm())

    # ── CUSTOM / DM CONTACTS ─────────────────────
    elif source in ("custom", "dm_contacts") and targets:
        logger.info(
            f"===> Creating run_mass_dm task "
            f"targets={len(targets)}"
        )

        task = asyncio.create_task(
            run_mass_dm(
                user_id=user_id,
                session_id=session_id,
                targets=targets,
                campaign_id=campaign_id,
                message_text=dm_msg["message_text"],
                message_entities=msg_entities,
                auto_reply_text=reply_msg[
                    "message_text"
                ] if reply_msg else None,
                auto_reply_entities=reply_entities,
                progress_callback=progress_callback,
                delay_preset=delay_preset,
            )
        )

        async def on_task_done(t):
            try:
                result = t.result()
                if result and result.get("success"):
                    await progress_msg.edit_text(
                        f"✅ <b>Campaign Complete!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📨 <b>Sent:</b> "
                        f"{result.get('sent', 0):,}\n"
                        f"❌ <b>Failed:</b> "
                        f"{result.get('failed', 0):,}\n"
                        f"👥 <b>Total:</b> {total:,}\n\n"
                        f"{'⚠️ PeerFlood hit' if result.get('peer_flood') else ''}",
                        reply_markup=back_to_main_inline(),
                    )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task done error: {e}")

        task.add_done_callback(
            lambda t: asyncio.create_task(
                on_task_done(t)
            )
        )

    # ── JOIN REQUEST DM ───────────────────────────
    else:
        logger.info(
            f"===> Creating run_join_request_dm task "
            f"target={target} source={source}"
        )

        task = asyncio.create_task(
            run_join_request_dm(
                user_id=user_id,
                session_id=session_id,
                target=target,
                campaign_id=campaign_id,
                message_text=dm_msg["message_text"],
                message_entities=msg_entities,
                auto_reply_text=reply_msg[
                    "message_text"
                ] if reply_msg else None,
                auto_reply_entities=reply_entities,
                progress_callback=progress_callback,
                delay_preset=delay_preset,
            )
        )

        async def on_jr_done(t):
            try:
                result = t.result()
                logger.info(
                    f"===> JR DM task done. "
                    f"result={result}"
                )
                if result and result.get("success"):
                    await progress_msg.edit_text(
                        f"✅ <b>Campaign Complete!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📨 <b>Sent:</b> "
                        f"{result.get('sent', 0):,}\n"
                        f"❌ <b>Failed:</b> "
                        f"{result.get('failed', 0):,}\n"
                        f"👥 <b>Total:</b> "
                        f"{result.get('total', 0):,}",
                        reply_markup=back_to_main_inline(),
                    )
                elif result and not result.get("success"):
                    await progress_msg.edit_text(
                        f"❌ <b>Campaign Failed</b>\n\n"
                        f"{result.get('error', 'Unknown')}",
                        reply_markup=back_to_main_inline(),
                    )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"JR task done error: {e}")

        task.add_done_callback(
            lambda t: asyncio.create_task(
                on_jr_done(t)
            )
        )

    register_task(
        user_id=user_id,
        task=task,
        task_type=source,
        total=total,
        campaign_id=campaign_id,
    )

# ============================================================
# STOP / REFRESH CAMPAIGN
# ============================================================

@router.callback_query(
    F.data.startswith("stop_campaign_")
)
async def stop_campaign(
    callback: CallbackQuery,
    state: FSMContext
):
    user_id = callback.from_user.id
    killed  = await kill_task(user_id)

    if killed:
        await callback.message.edit_text(
            "🔴 <b>Campaign Stopped</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Campaign stopped. Progress saved.",
            reply_markup=back_to_main_inline(),
        )
    else:
        await callback.message.edit_text(
            "⚠️ No active campaign found.",
            reply_markup=back_to_main_inline(),
        )
    await callback.answer("Stopped.")


@router.callback_query(
    F.data.startswith("refresh_campaign_")
)
async def refresh_campaign(callback: CallbackQuery):
    user_id   = callback.from_user.id
    task_info = get_user_task(user_id)

    if not task_info:
        await callback.answer(
            "No active campaign.",
            show_alert=True
        )
        return

    bar = format_progress_bar(
        task_info["progress"],
        task_info["total"]
    )

    await callback.message.edit_text(
        f"🚀 <b>Campaign Running</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{bar}\n\n"
        f"📨 <b>Progress:</b> "
        f"{task_info['progress']:,} / "
        f"{task_info['total']:,}\n"
        f"📊 <b>Status:</b> {task_info['status']}",
        reply_markup=campaign_running_keyboard(
            task_info.get("campaign_id", 0)
        ),
    )
    await callback.answer("Refreshed ✅")


# ============================================================
# JOIN REQUEST DM
# ============================================================

@router.message(F.text == "📨 Join Request DM")
async def join_request_dm_handler(
    message: Message,
    db_user: dict,
    state: FSMContext
):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        if (
            db_user["credits"] <= 0
            and not db_user["is_vip"]
        ):
            await message.answer(
                "💎 <b>No Credits</b>\n\n"
                "You have no credits left.",
                reply_markup=no_credits_keyboard(),
            )
            return

    sessions = await get_sessions_info(user_id)
    if not sessions:
        await message.answer(
            "📱 <b>No Account Connected</b>\n\n"
            "Add an account first.",
            reply_markup=no_session_keyboard(),
        )
        return

    dm_msg = await get_dm_message(user_id, "initial")
    if not dm_msg:
        await message.answer(
            "✉️ <b>No DM Message Set</b>\n\n"
            "Set your DM message first.",
            reply_markup=back_to_main_inline(),
        )
        return

    await message.answer(
        "📨 <b>Join Request DM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select account to use:\n\n"
        "⚠️ Must be <b>admin</b> in channel.",
        reply_markup=session_select_keyboard(
            sessions, "jrdm"
        ),
    )


@router.callback_query(
    F.data.startswith("jrdm_session_")
)
async def jrdm_session_selected(
    callback: CallbackQuery,
    state: FSMContext
):
    session_id = int(callback.data.split("_")[-1])
    await state.update_data(session_id=session_id)
    await state.set_state(
        JoinRequestDMStates.awaiting_channel_link
    )

    await callback.message.edit_text(
        "🔗 <b>Enter Channel Link</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the channel link.\n\n"
        "⚠️ Must be <b>admin</b>."
    )
    await callback.answer()


@router.message(
    JoinRequestDMStates.awaiting_channel_link
)
async def jrdm_channel_received(
    message: Message,
    state: FSMContext,
    db_user: dict
):
    user_id    = message.from_user.id
    target     = message.text.strip()
    data       = await state.get_data()
    session_id = data.get("session_id")

    processing = await message.answer(
        "🔍 <b>Counting pending requests...</b>\n"
        "Please wait ⏳"
    )

    try:
        from telethon import errors as telethon_errors

        client = await load_client(session_id)
        entity = await client.get_entity(target)

        try:
            pending_users = await get_pending_requesters(
                client, entity
            )
            count = len(pending_users)
        except telethon_errors.ChatAdminRequiredError:
            await release_client(session_id, client)
            await processing.edit_text(
                "❌ <b>Admin Required</b>\n\n"
                "Your account must be admin\n"
                "in this channel.",
                reply_markup=back_to_main_inline(),
            )
            await state.clear()
            return

        await release_client(session_id, client)

        await state.update_data(
            target=target,
            total=count,
            source="join_request",
        )

        is_owner     = user_id == OWNER_ID
        is_vip       = db_user["is_vip"]
        user_credits = db_user["credits"]

        credit_line = ""
        if not is_owner and not is_vip:
            credit_line = (
                f"💎 <b>Credits needed:</b> {count}\n"
                f"💰 <b>Your credits:</b> {user_credits}\n\n"
            )
            if user_credits < count:
                await processing.edit_text(
                    f"❌ <b>Insufficient Credits</b>\n\n"
                    f"Need <b>{count}</b> but "
                    f"have <b>{user_credits}</b>.",
                    reply_markup=no_credits_keyboard(),
                )
                await state.clear()
                return

        dm_msg    = await get_dm_message(
            user_id, "initial"
        )
        reply_msg = await get_dm_message(
            user_id, "reply"
        )

        await state.set_state(
            CampaignStates.awaiting_delay
        )
        await processing.edit_text(
            f"✅ <b>Analysis Complete</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 <b>Pending requests:</b> {count:,}\n"
            f"{credit_line}"
            f"📨 <b>DM Message:</b> "
            f"{'✅ Set' if dm_msg else '❌ Not Set'}\n"
            f"💬 <b>Auto Reply:</b> "
            f"{'✅ Set' if reply_msg else '❌ Not Set'}\n\n"
            f"⚠️ Requests will <b>NOT</b> be approved.\n\n"
            f"⚡ <b>Select sending speed:</b>",
            reply_markup=delay_select_keyboard(),
        )

    except Exception as e:
        await processing.edit_text(
            f"❌ <b>Failed</b>\n\n{str(e)}\n\n"
            f"Make sure account is admin.",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()


# ============================================================
# ACCEPT PENDING
# ============================================================

@router.message(F.text == "✅ Accept Pending")
async def accept_pending_handler(
    message: Message,
    state: FSMContext
):
    user_id  = message.from_user.id
    sessions = await get_sessions_info(user_id)

    if not sessions:
        await message.answer(
            "📱 <b>No Account Connected</b>\n\n"
            "Add an account first.",
            reply_markup=no_session_keyboard(),
        )
        return

    await message.answer(
        "✅ <b>Accept Pending Requests</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select account to use:\n\n"
        "⚠️ Must be <b>admin</b>.",
        reply_markup=session_select_keyboard(
            sessions, "accept"
        ),
    )


@router.callback_query(
    F.data.startswith("accept_session_")
)
async def accept_session_selected(
    callback: CallbackQuery,
    state: FSMContext
):
    session_id = int(callback.data.split("_")[-1])
    await state.update_data(session_id=session_id)
    await state.set_state(
        AcceptStates.awaiting_channel_link
    )

    await callback.message.edit_text(
        "🔗 <b>Enter Your Channel Link</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send channel link to accept all\n"
        "pending join requests.\n\n"
        "⚠️ Must be <b>admin</b>."
    )
    await callback.answer()


@router.message(AcceptStates.awaiting_channel_link)
async def accept_channel_received(
    message: Message,
    state: FSMContext
):
    target     = message.text.strip()
    data       = await state.get_data()
    session_id = data.get("session_id")

    processing = await message.answer(
        "🔍 <b>Counting pending requests...</b>"
    )

    try:
        from telethon import errors as telethon_errors

        client = await load_client(session_id)
        entity = await client.get_entity(target)

        try:
            pending_users = await get_pending_requesters(
                client, entity
            )
            count = len(pending_users)
        except telethon_errors.ChatAdminRequiredError:
            await release_client(session_id, client)
            await processing.edit_text(
                "❌ <b>Admin Required</b>\n\n"
                "Your account must be admin\n"
                "in this channel.",
                reply_markup=back_to_main_inline(),
            )
            await state.clear()
            return

        await release_client(session_id, client)

        await state.update_data(
            target=target,
            total=count,
        )
        await state.set_state(
            AcceptStates.awaiting_confirm
        )

        await processing.edit_text(
            f"📋 <b>Found {count:,} Pending Requests</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"This will <b>ACCEPT ALL</b> "
            f"{count:,} requests.\n\n"
            f"⚠️ Cannot be undone.\n\n"
            f"Are you sure?",
            reply_markup=accept_pending_keyboard(),
        )

    except Exception as e:
        await processing.edit_text(
            f"❌ <b>Failed</b>\n\n{str(e)}",
            reply_markup=back_to_main_inline(),
        )
        await state.clear()


@router.callback_query(
    F.data == "confirm_accept_pending"
)
async def execute_accept_pending(
    callback: CallbackQuery,
    state: FSMContext
):
    user_id    = callback.from_user.id
    data       = await state.get_data()
    await state.clear()

    session_id = data.get("session_id")
    target     = data.get("target")
    total      = data.get("total", 0)

    campaign_id = await create_campaign(
        user_id=user_id,
        session_id=session_id,
        campaign_type="accept_pending",
        total=total,
    )

    progress_msg = await callback.message.edit_text(
        f"✅ <b>Accepting Requests...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{format_progress_bar(0, total)}\n\n"
        f"✅ <b>Accepted:</b> 0\n"
        f"👥 <b>Total:</b> {total:,}",
        reply_markup=campaign_running_keyboard(
            campaign_id
        ),
    )

    await callback.answer("Accepting... ✅")

    start_time = datetime.now()

    async def progress_callback(
        accepted, total_count
    ):
        try:
            elapsed = (
                datetime.now() - start_time
            ).total_seconds()
            eta = format_eta(
                accepted, total_count, elapsed
            )
            bar = format_progress_bar(
                accepted, total_count
            )

            await progress_msg.edit_text(
                f"✅ <b>Accepting Requests...</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{bar}\n\n"
                f"✅ <b>Accepted:</b> {accepted:,}\n"
                f"👥 <b>Total:</b> {total_count:,}\n"
                f"🕐 <b>ETA:</b> {eta}",
                reply_markup=campaign_running_keyboard(
                    campaign_id
                ),
            )
        except Exception:
            pass

    task = asyncio.create_task(
        accept_pending_requests(
            user_id=user_id,
            session_id=session_id,
            target=target,
            campaign_id=campaign_id,
            progress_callback=progress_callback,
        )
    )

    register_task(
        user_id=user_id,
        task=task,
        task_type="accept_pending",
        total=total,
        campaign_id=campaign_id,
    )

    async def on_done(t):
        try:
            result = t.result()
            if result and result.get("success"):
                await progress_msg.edit_text(
                    f"✅ <b>All Done!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"✅ <b>Accepted:</b> "
                    f"{result['accepted']:,}\n"
                    f"❌ <b>Failed:</b> "
                    f"{result['failed']:,}\n"
                    f"👥 <b>Total:</b> "
                    f"{result['total']:,}",
                    reply_markup=back_to_main_inline(),
                )
            else:
                await progress_msg.edit_text(
                    f"❌ <b>Failed</b>\n\n"
                    f"{result.get('error', 'Unknown')}",
                    reply_markup=back_to_main_inline(),
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Accept task error: {e}")

    task.add_done_callback(
        lambda t: asyncio.create_task(on_done(t))
    )


# ============================================================
# MY STATS
# ============================================================

@router.message(F.text == "📊 My Stats")
async def my_stats_handler(
    message: Message,
    db_user: dict
):
    user_id   = message.from_user.id
    rank      = await get_user_referral_rank(user_id)
    campaigns = await get_user_campaigns(user_id)

    total_sent      = sum(
        c.get("sent", 0) for c in campaigns
    )
    total_campaigns = len(campaigns)

    text = (
        f"📊 <b>Your Stats</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Credits:</b> {db_user['credits']:,}\n"
        f"📨 <b>Total DMs Sent:</b> {total_sent:,}\n"
        f"🚀 <b>Campaigns Run:</b> {total_campaigns}\n"
        f"👥 <b>Total Referred:</b> "
        f"{db_user['total_referred']}\n"
        f"🏆 <b>Referral Rank:</b> #{rank}\n"
        f"💎 <b>VIP:</b> "
        f"{'✅ Active' if db_user['is_vip'] else '❌ None'}\n"
        f"📅 <b>Member Since:</b> "
        f"{db_user['joined_at'][:10]}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>"
    )

    await message.answer(
        text,
        reply_markup=my_stats_keyboard(),
    )


# ============================================================
# REDEEM CODE
# ============================================================

@router.message(F.text == "🎫 Redeem Code")
async def redeem_code_handler(
    message: Message,
    state: FSMContext
):
    await state.set_state(RedeemStates.awaiting_key)

    await message.answer(
        "🎫 <b>Redeem Key</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send your redemption key 🔑\n\n"
        "<i>Example: PROMO2024</i>"
    )


@router.message(RedeemStates.awaiting_key)
async def process_redeem_key(
    message: Message,
    state: FSMContext,
    db_user: dict
):
    user_id  = message.from_user.id
    key_name = message.text.strip()

    await state.clear()
    await micro_jitter(0.5)

    result = await redeem_key(key_name, user_id)

    if result["success"]:
        key         = result["key"]
        new_balance = db_user["credits"] + result["credits"]
        await message.answer(
            f"✅ <b>Key Redeemed!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 <b>Key:</b> {key['key_name']}\n"
            f"💎 <b>Added:</b> +{result['credits']:,}\n"
            f"💰 <b>Balance:</b> {new_balance:,}\n\n"
            f"Happy DMing! 🚀",
            reply_markup=back_to_main_inline(),
        )
    else:
        reason      = result["reason"]
        reason_text = {
            "invalid":
                "❌ Invalid key.",
            "inactive":
                "❌ Key is no longer active.",
            "exhausted":
                "❌ Key fully redeemed.",
            "already_redeemed":
                "❌ You already redeemed this key.",
        }.get(reason, "❌ Redemption failed.")

        await message.answer(
            f"❌ <b>Redemption Failed</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{reason_text}",
            reply_markup=back_to_main_inline(),
        )


# ============================================================
# REFER & EARN
# ============================================================

@router.message(F.text == "🎯 Refer & Earn")
@router.callback_query(F.data == "refer_earn")
async def refer_earn_handler(
    event: Message | CallbackQuery,
    bot: Bot,
    db_user: dict
):
    user_id          = event.from_user.id
    bot_info         = await bot.get_me()
    bot_username     = bot_info.username
    rank             = await get_user_referral_rank(
        user_id
    )
    referral_credits = (
        await get_config("referral_credits") or 10
    )

    text = (
        f"🎯 <b>Refer & Earn</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 Earn <b>{referral_credits} credits</b> "
        f"per invite!\n\n"
        f"🔗 <b>Your Link:</b>\n"
        f"<code>https://t.me/{bot_username}"
        f"?start=ref_{user_id}</code>\n\n"
        f"👥 <b>Total Referred:</b> "
        f"{db_user['total_referred']}\n"
        f"💎 <b>Credits Earned:</b> "
        f"{db_user['total_referred'] * int(referral_credits)}\n"
        f"🏆 <b>Your Rank:</b> #{rank}"
    )

    kb = refer_earn_keyboard(bot_username, user_id)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(
            text, reply_markup=kb
        )
        await event.answer()


@router.callback_query(F.data == "referral_history")
async def referral_history_handler(
    callback: CallbackQuery,
    db_user: dict
):
    user_id   = callback.from_user.id
    referrals = await get_user_referrals(user_id)

    if not referrals:
        text = (
            "📋 <b>Referral History</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No referrals yet. Share your link! 🎯"
        )
    else:
        history = ""
        for i, ref in enumerate(referrals[:20], 1):
            status   = (
                "✅" if ref["status"] == "completed"
                else "⏳"
            )
            name     = ref.get(
                "first_name",
                f"User {ref['referred_id']}"
            )
            username = ref.get("username", "")
            display  = (
                f"@{username}" if username else name
            )
            date     = ref["created_at"][:10]
            history += (
                f"{i}. {display} {status} — {date}\n"
            )

        text = (
            f"📋 <b>Referral History</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{history}\n\n"
            f"✅ = Credited | ⏳ = Pending"
        )

    await callback.message.edit_text(
        text,
        reply_markup=referral_history_keyboard(),
    )
    await callback.answer()


# ============================================================
# LEADERBOARD
# ============================================================

@router.message(F.text == "🏆 Leaderboard")
@router.callback_query(F.data == "leaderboard")
async def leaderboard_handler(
    event: Message | CallbackQuery,
    db_user: dict
):
    user_id = event.from_user.id
    top     = await get_top_referrers(10)
    rank    = await get_user_referral_rank(user_id)

    medals = ["🥇", "🥈", "🥉"]
    board  = ""

    for i, user in enumerate(top):
        medal    = medals[i] if i < 3 else f"{i+1}."
        username = user.get("username", "")
        name     = user.get(
            "first_name",
            f"User {user['tg_id']}"
        )
        display  = (
            f"@{username}" if username else name
        )
        refs     = user.get("referral_count", 0)
        credits  = user.get("total_credits", 0)
        board   += (
            f"{medal} {display} — "
            f"{refs} refs — "
            f"{credits} credits\n"
        )

    if not board:
        board = "No referrals yet. Be first! 🚀"

    my_refs          = db_user.get("total_referred", 0)
    referral_credits = int(
        await get_config("referral_credits") or 10
    )

    text = (
        f"🏆 <b>Top Referrers</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{board}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Your Rank:</b> #{rank}\n"
        f"👥 <b>Your Refs:</b> {my_refs}\n"
        f"💎 <b>Earned:</b> "
        f"{my_refs * referral_credits} credits"
    )

    kb = leaderboard_keyboard()

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(
            text, reply_markup=kb
        )
        await event.answer()


# ============================================================
# GO VIP
# ============================================================

@router.message(F.text == "💎 Go VIP Premium")
async def go_vip_handler(message: Message):
    await message.answer(
        "💎 <b>VIP Premium</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Unlock unlimited credits!\n\n"
        "✅ <b>VIP Benefits:</b>\n"
        "• Unlimited DM credits\n"
        "• Higher account limits\n"
        "• Priority support\n\n"
        "Contact owner to purchase 👇",
        reply_markup=vip_keyboard(OWNER_USERNAME),
    )


# ============================================================
# HOW TO USE
# ============================================================

@router.message(F.text == "❓ How To Use")
async def how_to_use_handler(message: Message):
    await message.answer(
        "❓ <b>How To Use</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select a topic:",
        reply_markup=how_to_use_keyboard(),
    )


@router.callback_query(F.data == "howto_api")
async def howto_api(callback: CallbackQuery):
    await callback.message.edit_text(
        "1️⃣ <b>Getting API Credentials</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Go to https://my.telegram.org\n"
        "2. Login with your phone\n"
        "3. Click API Development Tools\n"
        "4. Create a new app\n"
        "5. Copy API ID and API Hash",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_account")
async def howto_account(callback: CallbackQuery):
    await callback.message.edit_text(
        "2️⃣ <b>Adding Your Account</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Tap ➕ Add Account\n"
        "2. Send phone number\n"
        "3. Send the code\n"
        "4. Enter 2FA if needed",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_scrape")
async def howto_scrape(callback: CallbackQuery):
    await callback.message.edit_text(
        "3️⃣ <b>Scraping Members</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Admin only feature.\n\n"
        "1. Tap Scrape Members\n"
        "2. Select account\n"
        "3. Enter group link\n"
        "4. Receive .txt file",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_massdm")
async def howto_massdm(callback: CallbackQuery):
    await callback.message.edit_text(
        "4️⃣ <b>Setting Up Mass DM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Tap ✉️ Set DM Message\n"
        "2. Send your message\n"
        "3. Tap 💬 Set Auto Reply\n"
        "4. Send follow-up\n"
        "5. Use 👁️ Preview to check",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_campaign")
async def howto_campaign(callback: CallbackQuery):
    await callback.message.edit_text(
        "5️⃣ <b>Starting a Campaign</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Tap 🚀 Start Mass DM\n"
        "2. Select account\n"
        "3. Choose source\n"
        "4. Select speed\n"
        "5. Tap START",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_credits")
async def howto_credits(callback: CallbackQuery):
    free_credits = (
        await get_config("free_credits") or 100
    )
    await callback.message.edit_text(
        "6️⃣ <b>Understanding Credits</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Start with <b>{free_credits}</b> free\n\n"
        "💎 <b>1 credit = 1 DM sent</b>\n\n"
        "Earn more:\n"
        "• Redeem keys\n"
        "• Refer friends\n"
        "• Go VIP",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "howto_keys")
async def howto_keys(callback: CallbackQuery):
    await callback.message.edit_text(
        "7️⃣ <b>Redeeming Keys</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. Get key from owner\n"
        "2. Tap 🎫 Redeem Code\n"
        "3. Send the key\n"
        "4. Credits added instantly!",
        reply_markup=how_to_use_keyboard(),
    )
    await callback.answer()


# ============================================================
# SUPPORT
# ============================================================

@router.message(F.text == "📞 Support")
async def support_handler(message: Message):
    await message.answer(
        "📞 <b>Support</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Contact our team 👇",
        reply_markup=support_keyboard(OWNER_USERNAME),
    )


# ============================================================
# CREATE YOUR OWN BOT
# ============================================================

@router.message(F.text == "🤖 Create Your Own Bot")
async def create_own_bot_handler(message: Message):
    await message.answer(
        "🤖 <b>Create Your Own Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Want your own version?\n\n"
        "Contact Zenkai 👇",
        reply_markup=create_own_bot_keyboard(
            OWNER_USERNAME
        ),
    )


# ============================================================
# VERIFY MEMBERSHIP
# ============================================================

@router.callback_query(F.data == "verify_membership")
async def verify_membership_handler(
    callback: CallbackQuery,
    bot: Bot,
    db_user: dict
):
    user_id = callback.from_user.id

    from database import get_force_channels
    channels = await get_force_channels()

    if not channels:
        await callback.answer(
            "✅ No channels required.",
            show_alert=True
        )
        return

    user_joined = {}
    all_joined  = True

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=channel["channel_id"],
                user_id=user_id,
            )
            is_member = member.status in [
                "member",
                "administrator",
                "creator",
                "restricted",
            ]
            user_joined[
                channel["channel_id"]
            ] = is_member
            if not is_member:
                all_joined = False
        except Exception:
            user_joined[channel["channel_id"]] = True

    if all_joined:
        await callback.answer(
            "✅ Verified! Access granted.",
            show_alert=True
        )
        welcome  = build_welcome_text(
            callback.from_user, db_user
        )
        keyboard = await get_main_menu(user_id)
        photo    = await get_user_photo(
            bot, user_id
        )

        try:
            await callback.message.delete()
        except Exception:
            pass

        if photo:
            await callback.message.answer_photo(
                photo=photo,
                caption=welcome,
                reply_markup=keyboard,
            )
        else:
            await callback.message.answer(
                text=welcome,
                reply_markup=keyboard,
            )
    else:
        channel_status = ""
        for channel in channels:
            joined = user_joined.get(
                channel["channel_id"], False
            )
            name   = (
                channel["channel_name"] or "Channel"
            )
            status = "✅" if joined else "❌"
            channel_status += f"{status} {name}\n"
        # Safe edit — ignore 'not modified' errors
        try:
            await callback.message.edit_text(
                "🔒 <b>Access Denied</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Join ALL channels:\n\n"
                f"{channel_status}\n"
                "Then tap Verify again 👇",
                reply_markup=force_sub_keyboard(
                    channels, user_joined
                ),
            )
        except Exception as e:
            if "not modified" not in str(e).lower():
                logger.warning(
                    f"edit failed: {e}"
                )
        await callback.answer(
            "❌ Join all channels first.",
            show_alert=True
        )


# ============================================================
# EXPORT
# ============================================================

__all__ = ["router"]