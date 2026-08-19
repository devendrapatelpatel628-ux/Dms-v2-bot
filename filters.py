# ============================================================
#         ZENKAI DMS FORWARDING BOT - FILTERS
# ============================================================

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import OWNER_ID
from database import get_user, get_config


# ============================================================
# OWNER FILTER
# ============================================================

class OwnerFilter(BaseFilter):
    """
    Filter that passes only for the bot owner.
    Works on both Messages and CallbackQueries.
    """

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            return event.from_user.id == OWNER_ID
        elif isinstance(event, CallbackQuery):
            return event.from_user.id == OWNER_ID
        return False


# ============================================================
# BANNED FILTER
# ============================================================

class NotBannedFilter(BaseFilter):
    """
    Filter that passes only for non-banned users.
    Banned users are blocked silently.
    """

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        # Owner is never banned
        if user_id == OWNER_ID:
            return True

        user = await get_user(user_id)
        if not user:
            return True  # New user, not banned yet

        return user["is_banned"] == 0


# ============================================================
# VIP FILTER
# ============================================================

class VIPFilter(BaseFilter):
    """
    Filter that passes only for VIP users or owner.
    """

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        # Owner is always VIP
        if user_id == OWNER_ID:
            return True

        user = await get_user(user_id)
        if not user:
            return False

        return user["is_vip"] == 1


# ============================================================
# CREDITS FILTER
# ============================================================

class HasCreditsFilter(BaseFilter):
    """
    Filter that passes only if user has credits remaining.
    Owner and VIP users always pass.
    Accepts optional minimum credits required.
    """

    def __init__(self, min_credits: int = 1):
        self.min_credits = min_credits

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        # Owner always passes
        if user_id == OWNER_ID:
            return True

        user = await get_user(user_id)
        if not user:
            return False

        # VIP always passes
        if user["is_vip"] == 1:
            return True

        return user["credits"] >= self.min_credits


# ============================================================
# API CONFIGURED FILTER
# ============================================================

class APIConfiguredFilter(BaseFilter):
    """
    Filter that passes only if owner has set
    API ID and API Hash in the admin panel.
    """

    async def __call__(self, event) -> bool:
        api_id = await get_config("api_id")
        api_hash = await get_config("api_hash")
        return bool(api_id and api_hash)


# ============================================================
# FORCE SUB FILTER
# ============================================================

class ForceSubEnabledFilter(BaseFilter):
    """
    Filter that checks if force subscribe is enabled.
    Used to conditionally apply force sub logic.
    """

    async def __call__(self, event) -> bool:
        enabled = await get_config("force_sub_enabled")
        return enabled == "1"


# ============================================================
# OWNER ONLY FEATURES FILTER
# ============================================================

class OwnerFeatureFilter(BaseFilter):
    """
    Filter for features restricted to owner only.
    Like scraping members, viewing all users, etc.
    Sends a clean denial message if not owner.
    """

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        return user_id == OWNER_ID


# ============================================================
# ACTIVE SESSION FILTER
# ============================================================

class HasActiveSessionFilter(BaseFilter):
    """
    Filter that passes only if the user has
    at least one active userbot session.
    """

    async def __call__(self, event) -> bool:
        from database import count_user_sessions

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        # Owner always passes
        if user_id == OWNER_ID:
            return True

        count = await count_user_sessions(user_id)
        return count > 0


# ============================================================
# REFER SYSTEM ENABLED FILTER
# ============================================================

class ReferSystemFilter(BaseFilter):
    """
    Filter that passes only if refer system is enabled.
    """

    async def __call__(self, event) -> bool:
        enabled = await get_config("refer_system_enabled")
        return enabled == "1"


# ============================================================
# MAX ACCOUNTS FILTER
# ============================================================

class CanAddAccountFilter(BaseFilter):
    """
    Filter that checks if user can add more accounts.
    Compares current session count against owner's limit.
    Owner always passes.
    """

    async def __call__(self, event) -> bool:
        from database import count_user_sessions

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return False

        # Owner has no limit
        if user_id == OWNER_ID:
            return True

        user = await get_user(user_id)
        if not user:
            return False

        # VIP users get double the limit
        max_accounts = int(
            await get_config("max_accounts_per_user") or 3
        )
        if user["is_vip"] == 1:
            max_accounts = max_accounts * 2

        current = await count_user_sessions(user_id)
        return current < max_accounts


# ============================================================
# PRIVATE CHAT FILTER
# ============================================================

class PrivateChatFilter(BaseFilter):
    """
    Filter that passes only for private chats.
    Ensures bot commands only work in DMs.
    """

    async def __call__(self, event) -> bool:
        if isinstance(event, Message):
            return event.chat.type == "private"
        elif isinstance(event, CallbackQuery):
            return event.message.chat.type == "private"
        return False


# ============================================================
# EXPORT ALL FILTERS (Easy import in other files)
# ============================================================

__all__ = [
    "OwnerFilter",
    "NotBannedFilter",
    "VIPFilter",
    "HasCreditsFilter",
    "APIConfiguredFilter",
    "ForceSubEnabledFilter",
    "OwnerFeatureFilter",
    "HasActiveSessionFilter",
    "ReferSystemFilter",
    "CanAddAccountFilter",
    "PrivateChatFilter",
]