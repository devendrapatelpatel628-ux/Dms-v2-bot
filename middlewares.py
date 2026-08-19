# ============================================================
#         ZENKAI DMS FORWARDING BOT - MIDDLEWARES
# ============================================================

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import (
    Message,
    CallbackQuery,
    TelegramObject,
)
from config import OWNER_ID, OWNER_USERNAME
from database import (
    get_user,
    create_user,
    update_last_active,
    get_force_channels,
    get_config,
    get_referral_by_referred,
    complete_referral,
    create_referral,
    add_log,
)
from keyboards import (
    force_sub_keyboard,
    not_configured_keyboard,
    main_menu_keyboard,
    owner_main_menu_keyboard,
)

logger = logging.getLogger(__name__)


async def _safe_edit(
    message,
    text: str = None,
    reply_markup=None,
):
    """
    Safely edit a message, ignoring
    'message is not modified' errors.
    """
    try:
        if text is not None:
            await message.edit_text(
                text,
                reply_markup=reply_markup,
            )
        else:
            await message.edit_reply_markup(
                reply_markup=reply_markup
            )
    except Exception as e:
        # Silently ignore "not modified" errors
        err_str = str(e).lower()
        if "not modified" in err_str:
            return
        # Log other errors but don't crash
        logger.debug(f"edit failed: {e}")

# ============================================================
# USER REGISTRATION MIDDLEWARE
# Registers new users and updates last active
# ============================================================

class UserRegistrationMiddleware(BaseMiddleware):
    """
    Runs on every update.
    Creates user in DB if not exists.
    Updates last active timestamp.
    Handles referral tracking.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        # Extract user from event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        user_id = user.id

        # Get or create user in DB
        db_user = await get_user(user_id)

        if not db_user:
            # Check for referral in start payload
            referred_by = None
            if isinstance(event, Message):
                text = event.text or ""
                if text.startswith("/start ref_"):
                    try:
                        referrer_id = int(
                            text.split("ref_")[1].strip()
                        )
                        # Prevent self-referral
                        if referrer_id != user_id:
                            referred_by = referrer_id
                    except (ValueError, IndexError):
                        pass

            # Create new user
            db_user = await create_user(
                tg_id=user_id,
                username=user.username or "",
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                referred_by=referred_by,
            )

            # Create pending referral if referred
            if referred_by:
                await create_referral(
                    referrer_id=referred_by,
                    referred_id=user_id,
                )

            await add_log(
                user_id,
                "user_registered",
                f"New user: @{user.username}"
            )

        else:
            # Update last active
            await update_last_active(user_id)

        # Inject db_user into handler data
        data["db_user"] = db_user

        return await handler(event, data)


# ============================================================
# BAN CHECK MIDDLEWARE
# Blocks banned users from using the bot
# ============================================================

class BanCheckMiddleware(BaseMiddleware):
    """
    Runs after UserRegistrationMiddleware.
    Silently blocks banned users.
    Owner is never blocked.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        # Owner is never banned
        if user.id == OWNER_ID:
            return await handler(event, data)

        db_user = data.get("db_user") or await get_user(user.id)

        if db_user and db_user.get("is_banned"):
            # Send ban message once
            ban_text = (
                "🚫 <b>You Are Banned</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "You have been banned from\n"
                "using this bot.\n\n"
                "Contact support if you think\n"
                "this is a mistake."
            )
            try:
                if isinstance(event, Message):
                    await event.answer(ban_text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "🚫 You are banned.",
                        show_alert=True
                    )
            except Exception:
                pass
            return  # Block handler

        return await handler(event, data)


# ============================================================
# FORCE SUBSCRIBE MIDDLEWARE
# Checks if user has joined all required channels
# ============================================================

class ForceSubscribeMiddleware(BaseMiddleware):
    """
    Runs after BanCheckMiddleware.
    Checks if user is in ALL required channels.
    Allows if member OR in pending join requests.
    Completes referral credit after force sub passes.
    Owner bypasses force sub.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user = None
        bot = data.get("bot")

        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        # Owner bypasses force sub
        if user.id == OWNER_ID:
            return await handler(event, data)

        # Check if force sub is enabled
        force_sub_enabled = await get_config("force_sub_enabled")
        if force_sub_enabled != "1":
            return await handler(event, data)

        # Allow verify callback through always
        if isinstance(event, CallbackQuery):
            if event.data == "verify_membership":
                return await handler(event, data)

        # Get all force channels
        channels = await get_force_channels()
        if not channels:
            return await handler(event, data)

        # Check membership for each channel
        user_joined = {}
        all_joined = True

        for channel in channels:
            is_member = await self._check_membership(
                bot,
                user.id,
                channel["channel_id"]
            )
            user_joined[channel["channel_id"]] = is_member
            if not is_member:
                all_joined = False

        if all_joined:
            # Complete referral if pending
            refer_enabled = await get_config("refer_system_enabled")
            if refer_enabled == "1":
                referral = await get_referral_by_referred(user.id)
                if referral and referral["status"] == "pending":
                    completed = await complete_referral(user.id)
                    if completed and bot:
                        # Notify referrer
                        await self._notify_referrer(
                            bot,
                            completed["referrer_id"],
                        )

            return await handler(event, data)

        # User hasn't joined all channels
        # Build status text
        channel_status = ""
        join_buttons_channels = []

        for channel in channels:
            joined = user_joined.get(channel["channel_id"], False)
            name = channel["channel_name"] or "Channel"
            if joined:
                channel_status += f"✅ {name} — Joined\n"
            else:
                channel_status += f"❌ {name} — Not Joined\n"
                join_buttons_channels.append(channel)

        force_sub_text = (
            "🔒 <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "You must join <b>ALL</b> channels\n"
            "below to use this bot 👇\n\n"
            f"{channel_status}\n"
            "Join the remaining channels\n"
            "and tap <b>Verify</b> below 👇"
        )

        keyboard = force_sub_keyboard(channels, user_joined)
        try:
            if isinstance(event, Message):
                await event.answer(
                    force_sub_text,
                    reply_markup=keyboard,
                )
            elif isinstance(event, CallbackQuery):
                await _safe_edit(
                    event.message,
                    text=force_sub_text,
                    reply_markup=keyboard,
                )
                await event.answer()
        except Exception as e:
            logger.warning(
                f"Force sub message failed: {e}"
            )

        return  # Block handler

    async def _check_membership(
        self,
        bot,
        user_id: int,
        channel_id: int
    ) -> bool:
        """
        Check if user is a member OR has a
        pending join request. True if either.
        """
        from database import (
            has_pending_request,
            remove_pending_request,
        )

        logger.info(
            f"===> CHECK user={user_id} "
            f"channel={channel_id}"
        )

        try:
            member = await bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id,
            )
            logger.info(
                f"===> status = {member.status}"
            )

            if member.status in (
                "member",
                "administrator",
                "creator",
                "restricted",
            ):
                await remove_pending_request(
                    user_id, channel_id
                )
                logger.info("===> ALLOWED (member)")
                return True

            has_pending = await has_pending_request(
                user_id, channel_id
            )
            logger.info(
                f"===> has_pending = {has_pending}"
            )

            if has_pending:
                logger.info("===> ALLOWED (pending)")
                return True

            logger.info("===> BLOCKED")
            return False

        except Exception as e:
            logger.warning(
                f"===> EXCEPTION: {e} — allowing"
            )
            return True

    async def _notify_referrer(
        self,
        bot,
        referrer_id: int,
    ):
        """
        Notify the referrer that they earned credits.
        """
        try:
            from database import get_user
            referrer = await get_user(referrer_id)
            if not referrer:
                return

            referral_credits = int(
                await get_config("referral_credits") or 10
            )
            new_balance = referrer["credits"]

            notify_text = (
                "🎉 <b>New Referral!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Someone joined via your referral link!\n\n"
                f"💎 <b>+{referral_credits} credits</b> "
                f"added to your account\n"
                f"💰 <b>New Balance:</b> {new_balance} credits\n\n"
                "Keep sharing to earn more! 🚀"
            )

            await bot.send_message(
                chat_id=referrer_id,
                text=notify_text,
            )

        except Exception as e:
            logger.warning(f"Referrer notification failed: {e}")


# ============================================================
# PRIVATE CHAT MIDDLEWARE
# Ensures bot only works in private chats
# ============================================================

class PrivateChatMiddleware(BaseMiddleware):
    """
    Blocks all interactions that are not
    from a private chat (DM).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        if isinstance(event, Message):
            if event.chat.type != "private":
                return  # Silently ignore group messages
        elif isinstance(event, CallbackQuery):
            if event.message.chat.type != "private":
                return

        return await handler(event, data)


# ============================================================
# API CONFIGURED MIDDLEWARE
# Checks if owner has set API credentials
# Blocks login attempts if not configured
# ============================================================

class APIConfiguredMiddleware(BaseMiddleware):
    """
    Checks if API ID and Hash are configured.
    Only blocks login-related actions.
    Owner bypasses this check.
    """

    # Actions that require API to be configured
    REQUIRES_API = [
        "add_account",
        "login_flow",
    ]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        # Owner bypasses
        if user.id == OWNER_ID:
            return await handler(event, data)

        # Check if this is an API-required action
        needs_check = False
        if isinstance(event, CallbackQuery):
            if event.data in self.REQUIRES_API:
                needs_check = True
        elif isinstance(event, Message):
            text = event.text or ""
            if text in ["➕ Add Account"]:
                needs_check = True

        if not needs_check:
            return await handler(event, data)

        # Check API credentials
        api_id = await get_config("api_id")
        api_hash = await get_config("api_hash")

        if not api_id or not api_hash:
            not_configured_text = (
                "⚠️ <b>Bot Not Configured Yet</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "The owner has not set up the\n"
                "API credentials yet.\n\n"
                "Please contact the owner."
            )
            keyboard = not_configured_keyboard(OWNER_USERNAME)

            try:
                if isinstance(event, Message):
                    await event.answer(
                        not_configured_text,
                        reply_markup=keyboard,
                    )
                elif isinstance(event, CallbackQuery):
                    await event.message.edit_text(
                        not_configured_text,
                        reply_markup=keyboard,
                    )
                    await event.answer()
            except Exception:
                pass
            return

        return await handler(event, data)


# ============================================================
# LOGGING MIDDLEWARE
# Logs all user interactions
# ============================================================

class LoggingMiddleware(BaseMiddleware):
    """
    Logs every message and callback to the DB.
    Lightweight - only logs action type, not content.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user_id = None
        action = None
        detail = None

        if isinstance(event, Message):
            user_id = event.from_user.id
            text = event.text or ""
            # Only log button presses and commands
            if text.startswith("/") or len(text) < 50:
                action = "message"
                detail = text[:100]

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            action = "callback"
            detail = event.data

        if user_id and action:
            try:
                await add_log(user_id, action, detail)
            except Exception:
                pass

        return await handler(event, data)


# ============================================================
# EXPORT ALL
# ============================================================

__all__ = [
    "UserRegistrationMiddleware",
    "BanCheckMiddleware",
    "ForceSubscribeMiddleware",
    "PrivateChatMiddleware",
    "APIConfiguredMiddleware",
    "LoggingMiddleware",
]