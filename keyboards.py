# ============================================================
#         ZENKAI DMS FORWARDING BOT - KEYBOARDS
# ============================================================

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import (
    ReplyKeyboardBuilder,
    InlineKeyboardBuilder,
)
from aiogram.enums import ButtonStyle


# ============================================================
# COLOR SCHEME REFERENCE
# ============================================================
# ButtonStyle.PRIMARY   → 🔵 Blue     (Info / Navigation)
# ButtonStyle.SUCCESS   → 🟢 Green    (Positive actions)
# ButtonStyle.DANGER    → 🔴 Red      (Destructive / Cancel)
# ============================================================


# ============================================================
# REMOVE KEYBOARD
# ============================================================

def remove_keyboard():
    return ReplyKeyboardRemove()


# ============================================================
# MAIN MENU — NORMAL USER
# ============================================================

def main_menu_keyboard():
    """Main menu for normal users with colorful buttons."""
    builder = ReplyKeyboardBuilder()

    # Big CTA button — full width — GREEN
    builder.row(
        KeyboardButton(
            text="🚀 Start Mass DM Campaign",
            style=ButtonStyle.SUCCESS,
        )
    )

    # Message setup — BLUE
    builder.row(
        KeyboardButton(
            text="✉️ Set DM Message",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="💬 Set Auto Reply",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Preview & Stats — BLUE
    builder.row(
        KeyboardButton(
            text="👁️ Preview Message",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="📊 My Stats",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Account + VIP — mixed
    builder.row(
        KeyboardButton(
            text="👤 My Account",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="💎 Go VIP Premium",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Positive actions — GREEN
    builder.row(
        KeyboardButton(
            text="🎫 Redeem Code",
            style=ButtonStyle.SUCCESS,
        ),
        KeyboardButton(
            text="➕ Add Account",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Remove (red) + Accept (green)
    builder.row(
        KeyboardButton(
            text="➖ Remove Account",
            style=ButtonStyle.DANGER,
        ),
        KeyboardButton(
            text="✅ Accept Pending",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # DM & Referral — GREEN
    builder.row(
        KeyboardButton(
            text="📨 Join Request DM",
            style=ButtonStyle.SUCCESS,
        ),
        KeyboardButton(
            text="🎯 Refer & Earn",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Info — BLUE
    builder.row(
        KeyboardButton(
            text="🏆 Leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="❓ How To Use",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Support + Custom bot — BLUE
    builder.row(
        KeyboardButton(
            text="📞 Support",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="🤖 Create Your Own Bot",
            style=ButtonStyle.PRIMARY,
        ),
    )

    return builder.as_markup(
        resize_keyboard=True,
        persistent=True,
    )


# ============================================================
# MAIN MENU — OWNER
# ============================================================

def owner_main_menu_keyboard():
    """Main menu for owner (extra Scrape + Admin buttons)."""
    builder = ReplyKeyboardBuilder()

    # Big CTA — GREEN
    builder.row(
        KeyboardButton(
            text="🚀 Start Mass DM Campaign",
            style=ButtonStyle.SUCCESS,
        )
    )

    # Message setup — BLUE
    builder.row(
        KeyboardButton(
            text="✉️ Set DM Message",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="💬 Set Auto Reply",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Preview & Stats — BLUE
    builder.row(
        KeyboardButton(
            text="👁️ Preview Message",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="📊 My Stats",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Account management
    builder.row(
        KeyboardButton(
            text="👤 My Account",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="➕ Add Account",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Remove + Accept
    builder.row(
        KeyboardButton(
            text="➖ Remove Account",
            style=ButtonStyle.DANGER,
        ),
        KeyboardButton(
            text="✅ Accept Pending",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Owner-only actions — GREEN
    builder.row(
        KeyboardButton(
            text="📤 Scrape Members",
            style=ButtonStyle.SUCCESS,
        ),
        KeyboardButton(
            text="📨 Join Request DM",
            style=ButtonStyle.SUCCESS,
        ),
    )

    # Info — BLUE
    builder.row(
        KeyboardButton(
            text="🏆 Leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="❓ How To Use",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Support & Custom
    builder.row(
        KeyboardButton(
            text="📞 Support",
            style=ButtonStyle.PRIMARY,
        ),
        KeyboardButton(
            text="🤖 Create Your Own Bot",
            style=ButtonStyle.PRIMARY,
        ),
    )

    # Admin Panel — full width — RED (owner power)
    builder.row(
        KeyboardButton(
            text="⚙️ Admin Panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup(
        resize_keyboard=True,
        persistent=True,
    )


# ============================================================
# FORCE SUBSCRIBE
# ============================================================

def force_sub_keyboard(channels: list, user_joined: dict):
    """Force sub — red for unjoined, green for joined."""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        joined = user_joined.get(
            channel["channel_id"], False
        )
        name = channel["channel_name"] or "Channel"

        if joined:
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ {name}",
                    callback_data=(
                        f"joined_{channel['channel_id']}"
                    ),
                    style=ButtonStyle.SUCCESS,
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"❌ Join {name}",
                    url=(
                        channel["invite_link"]
                        or channel["channel_link"]
                    ),
                    style=ButtonStyle.DANGER,
                )
            )

    # Verify — GREEN
    builder.row(
        InlineKeyboardButton(
            text="✅ Verify My Membership",
            callback_data="verify_membership",
            style=ButtonStyle.SUCCESS,
        )
    )

    return builder.as_markup()


# ============================================================
# BACK TO MAIN MENU
# ============================================================

def back_to_main_inline():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )
    return builder.as_markup()


# ============================================================
# CONFIRM / CANCEL
# ============================================================

def confirm_cancel_keyboard(
    confirm_data: str,
    cancel_data: str,
    confirm_text: str = "✅ Confirm",
    cancel_text: str = "❌ Cancel",
):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=confirm_text,
            callback_data=confirm_data,
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text=cancel_text,
            callback_data=cancel_data,
            style=ButtonStyle.DANGER,
        ),
    )
    return builder.as_markup()


# ============================================================
# SESSION SELECT
# ============================================================

def session_select_keyboard(sessions: list, action: str):
    """Session selection list."""
    builder = InlineKeyboardBuilder()

    for session in sessions:
        builder.row(
            InlineKeyboardButton(
                text=f"📱 {session['phone']}",
                callback_data=(
                    f"{action}_session_{session['id']}"
                ),
                style=ButtonStyle.PRIMARY,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# REMOVE ACCOUNT
# ============================================================

def remove_account_keyboard(sessions: list):
    builder = InlineKeyboardBuilder()

    for session in sessions:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑️ Remove {session['phone']}",
                callback_data=(
                    f"remove_session_{session['id']}"
                ),
                style=ButtonStyle.DANGER,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# CAMPAIGN SOURCE
# ============================================================

def campaign_source_keyboard():
    """Select target source for Mass DM."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💬 My DM Contacts (All Chats)",
            callback_data="source_dm_contacts",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Upload Custom List (.txt)",
            callback_data="source_custom",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Scrape Group Members",
            callback_data="source_scraped",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📨 Join Request Users",
            callback_data="source_join_request",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# CAMPAIGN START
# ============================================================

def campaign_start_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="▶️ START",
            callback_data="start_campaign",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="❌ CANCEL",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        ),
    )

    return builder.as_markup()


# ============================================================
# CAMPAIGN RUNNING
# ============================================================

def campaign_running_keyboard(campaign_id: int):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔴 Stop",
            callback_data=f"stop_campaign_{campaign_id}",
            style=ButtonStyle.DANGER,
        ),
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data=(
                f"refresh_campaign_{campaign_id}"
            ),
            style=ButtonStyle.PRIMARY,
        ),
    )

    return builder.as_markup()


# ============================================================
# DELAY SELECTOR
# ============================================================

def delay_select_keyboard():
    """Sending speed selector."""
    builder = InlineKeyboardBuilder()

    # Fast — RED (risky)
    builder.row(
        InlineKeyboardButton(
            text="⚡ Fast (5–15s) — Risky",
            callback_data="delay_fast",
            style=ButtonStyle.DANGER,
        )
    )
    # Medium — BLUE (balanced)
    builder.row(
        InlineKeyboardButton(
            text="⚖️ Medium (15–45s) — Balanced",
            callback_data="delay_medium",
            style=ButtonStyle.PRIMARY,
        )
    )
    # Slow — GREEN (safest)
    builder.row(
        InlineKeyboardButton(
            text="🐢 Slow (45–120s) — Safest",
            callback_data="delay_slow",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# SCRAPE TYPE
# ============================================================

def scrape_type_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="👥 All Members",
            callback_data="scrape_members",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Pending Join Requests",
            callback_data="scrape_pending",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# HOW TO USE
# ============================================================

def how_to_use_keyboard():
    builder = InlineKeyboardBuilder()

    steps = [
        ("1️⃣ Getting API Credentials", "howto_api"),
        ("2️⃣ Adding Your Account",     "howto_account"),
        ("3️⃣ Scraping Members",        "howto_scrape"),
        ("4️⃣ Setting Up Mass DM",      "howto_massdm"),
        ("5️⃣ Starting a Campaign",     "howto_campaign"),
        ("6️⃣ Understanding Credits",   "howto_credits"),
        ("7️⃣ Redeeming Keys",          "howto_keys"),
    ]

    for text, data in steps:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=data,
                style=ButtonStyle.PRIMARY,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.SUCCESS,
        )
    )

    return builder.as_markup()


# ============================================================
# SUPPORT
# ============================================================

def support_keyboard(owner_username: str):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💬 Contact Owner",
            url=f"https://t.me/{owner_username}",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# CREATE YOUR OWN BOT
# ============================================================

def create_own_bot_keyboard(owner_username: str):
    message = (
        "Zenkai sir I want to discuss "
        "the pricing of this bot's script"
    )
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💬 Chat with Zenkai",
            url=(
                f"https://t.me/{owner_username}"
                f"?text={message}"
            ),
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# VIP
# ============================================================

def vip_keyboard(owner_username: str):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💎 Contact Owner for VIP",
            url=f"https://t.me/{owner_username}",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# REFER & EARN
# ============================================================

def refer_earn_keyboard(bot_username: str, user_id: int):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📤 Share My Link",
            url=(
                f"https://t.me/share/url?"
                f"url=https://t.me/{bot_username}"
                f"?start=ref_{user_id}"
                f"&text=Join%20Zenkai%20DMs%20Bot"
                f"%20and%20get%20free%20credits!"
            ),
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 My Referral History",
            callback_data="referral_history",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🏆 Leaderboard",
            callback_data="leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# LEADERBOARD
# ============================================================

def leaderboard_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data="leaderboard",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        ),
    )

    return builder.as_markup()


# ============================================================
# REFERRAL HISTORY
# ============================================================

def referral_history_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🏆 Leaderboard",
            callback_data="leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        ),
    )

    return builder.as_markup()


# ============================================================
# MY STATS
# ============================================================

def my_stats_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎯 Refer & Earn",
            callback_data="refer_earn",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="🏆 Leaderboard",
            callback_data="leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# MY ACCOUNT
# ============================================================

def my_account_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Add Account",
            callback_data="add_account",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="➖ Remove Account",
            callback_data="remove_account",
            style=ButtonStyle.DANGER,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# NO CREDITS
# ============================================================

def no_credits_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎫 Redeem Key",
            callback_data="redeem_code",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎯 Refer & Earn",
            callback_data="refer_earn",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="💎 Go VIP",
            callback_data="go_vip",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# NOT CONFIGURED
# ============================================================

def not_configured_keyboard(owner_username: str):
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📞 Contact Owner",
            url=f"https://t.me/{owner_username}",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# NO SESSION
# ============================================================

def no_session_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Add Account",
            callback_data="add_account",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN PANEL MAIN
# ============================================================

def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="👥 Users",
            callback_data="admin_users",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🔑 Keys",
            callback_data="admin_keys",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Force Sub",
            callback_data="admin_forcesub",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🌐 Proxy",
            callback_data="admin_proxy",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Settings",
            callback_data="admin_settings",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="📊 Live Stats",
            callback_data="admin_stats",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📋 Logs",
            callback_data="admin_logs",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="📣 Broadcast",
            callback_data="admin_broadcast",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN USERS
# ============================================================

def admin_users_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔍 Search User",
            callback_data="admin_search_user",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="📋 All Users",
            callback_data="admin_all_users",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🚫 Ban",
            callback_data="admin_ban_user",
            style=ButtonStyle.DANGER,
        ),
        InlineKeyboardButton(
            text="✅ Unban",
            callback_data="admin_unban_user",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 Grant VIP",
            callback_data="admin_grant_vip",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="👤 Info",
            callback_data="admin_user_info",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📱 Max Accounts",
            callback_data="admin_max_accounts",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="💰 Add Credits",
            callback_data="admin_add_credits",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN KEYS
# ============================================================

def admin_keys_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Create Key",
            callback_data="admin_create_key",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="📋 View Keys",
            callback_data="admin_view_keys",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Delete Key",
            callback_data="admin_delete_key",
            style=ButtonStyle.DANGER,
        ),
        InlineKeyboardButton(
            text="📊 Stats",
            callback_data="admin_key_stats",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="👥 Who Redeemed",
            callback_data="admin_key_redeemers",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN FORCE SUB
# ============================================================

def admin_forcesub_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Add Channel",
            callback_data="admin_add_channel",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="📋 View Channels",
            callback_data="admin_view_channels",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Remove",
            callback_data="admin_remove_channel",
            style=ButtonStyle.DANGER,
        ),
        InlineKeyboardButton(
            text="🔄 Toggle ON/OFF",
            callback_data="admin_toggle_forcesub",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# CHANNEL TYPE (Public / Private)
# ============================================================

def channel_type_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🌐 Public",
            callback_data="channel_public",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="🔒 Private",
            callback_data="channel_private",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="admin_forcesub",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN PROXY
# ============================================================

def admin_proxy_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 Proxy Stats",
            callback_data="admin_proxy_stats",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="➕ Add Source",
            callback_data="admin_add_proxy_source",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Toggle Hunter",
            callback_data="admin_toggle_hunter",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="⚡ Force Hunt",
            callback_data="admin_force_hunt",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Clear Pool",
            callback_data="admin_clear_proxies",
            style=ButtonStyle.DANGER,
        ),
        InlineKeyboardButton(
            text="📋 Sources",
            callback_data="admin_view_sources",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN SETTINGS
# ============================================================

def admin_settings_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔑 Set API Credentials",
            callback_data="admin_set_api",
            style=ButtonStyle.SUCCESS,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔢 Concurrency",
            callback_data="admin_set_concurrency",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="⏱️ DM Delay",
            callback_data="admin_set_dm_delay",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="💬 Reply Delay",
            callback_data="admin_set_reply_delay",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🕵️ Stealth Level",
            callback_data="admin_set_stealth",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🎁 Free Credits",
            callback_data="admin_set_free_credits",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="📱 Max Accounts",
            callback_data="admin_set_max_accounts",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Auto Reply",
            callback_data="admin_toggle_autoreply",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="⌨️ Typing Sim",
            callback_data="admin_toggle_typing",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="⏰ Progress Interval",
            callback_data="admin_set_progress_interval",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🎯 Refer Settings",
            callback_data="admin_refer_settings",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN REFER SETTINGS
# ============================================================

def admin_refer_settings_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🔄 Toggle ON/OFF",
            callback_data="admin_toggle_refer",
            style=ButtonStyle.PRIMARY,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💎 Credits/Referral",
            callback_data="admin_set_referral_credits",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="🎁 New User Bonus",
            callback_data="admin_set_new_user_bonus",
            style=ButtonStyle.SUCCESS,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏆 Full Leaderboard",
            callback_data="admin_full_leaderboard",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="📊 Refs Today",
            callback_data="admin_referrals_today",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_settings",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ADMIN LIVE STATS
# ============================================================

def admin_stats_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⚡ Active Tasks",
            callback_data="admin_active_tasks",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="🌐 Proxy Pool",
            callback_data="admin_proxy_stats",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Refresh",
            callback_data="admin_stats",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="🔴 Kill ALL Tasks",
            callback_data="admin_kill_all",
            style=ButtonStyle.DANGER,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="💀 Kill Specific",
            callback_data="admin_kill_task",
            style=ButtonStyle.DANGER,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_panel",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# ACTIVE TASKS
# ============================================================

def active_tasks_keyboard(tasks: dict):
    builder = InlineKeyboardBuilder()

    for user_id, task_info in tasks.items():
        builder.row(
            InlineKeyboardButton(
                text=(
                    f"🔴 Kill "
                    f"{task_info['type'].upper()} "
                    f"| User {user_id} "
                    f"| {task_info['progress']}/"
                    f"{task_info['total']}"
                ),
                callback_data=f"kill_task_{user_id}",
                style=ButtonStyle.DANGER,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_stats",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# STEALTH LEVEL
# ============================================================

def stealth_level_keyboard():
    builder = InlineKeyboardBuilder()

    # Levels with color scaling
    # 1-2 → RED (risky) | 3 → BLUE (balanced) | 4-5 → GREEN (safe)
    levels = [
        ("⚡ Level 1 - Fastest (Risky)",  "stealth_1", ButtonStyle.DANGER),
        ("🔥 Level 2 - Fast",              "stealth_2", ButtonStyle.DANGER),
        ("⚖️ Level 3 - Balanced",          "stealth_3", ButtonStyle.PRIMARY),
        ("🛡️ Level 4 - Safe",              "stealth_4", ButtonStyle.SUCCESS),
        ("🔒 Level 5 - Safest (Slowest)", "stealth_5", ButtonStyle.SUCCESS),
    ]

    for text, data, style in levels:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=data,
                style=style,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_settings",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# VIEW KEYS
# ============================================================

def view_keys_keyboard(keys: list):
    builder = InlineKeyboardBuilder()

    for key in keys:
        status = "✅" if key["is_active"] else "❌"
        style  = (
            ButtonStyle.SUCCESS
            if key["is_active"]
            else ButtonStyle.DANGER
        )
        builder.row(
            InlineKeyboardButton(
                text=(
                    f"{status} {key['key_name']} | "
                    f"{key['credits']}c | "
                    f"{key['redeemed_count']}/"
                    f"{key['max_redeems']}"
                ),
                callback_data=(
                    f"admin_key_detail_{key['id']}"
                ),
                style=style,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_keys",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# VIEW CHANNELS
# ============================================================

def view_channels_keyboard(channels: list):
    builder = InlineKeyboardBuilder()

    for ch in channels:
        type_icon = "🌐" if ch["is_public"] else "🔒"
        builder.row(
            InlineKeyboardButton(
                text=(
                    f"{type_icon} "
                    f"{ch['channel_name'] or ch['channel_id']}"
                ),
                callback_data=(
                    f"admin_ch_detail_{ch['channel_id']}"
                ),
                style=ButtonStyle.PRIMARY,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_forcesub",
            style=ButtonStyle.DANGER,
        )
    )

    return builder.as_markup()


# ============================================================
# VIEW PROXY SOURCES
# ============================================================

def view_sources_keyboard(sources: list):
    builder = InlineKeyboardBuilder()

    for source in sources:
        status = "✅" if source["is_active"] else "❌"
        style  = (
            ButtonStyle.SUCCESS
            if source["is_active"]
            else ButtonStyle.DANGER
        )
        builder.row(
            InlineKeyboardButton(
                text=f"{status} Source #{source['id']}",
                callback_data=(
                    f"admin_source_detail_{source['id']}"
                ),
                style=style,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data="admin_proxy",
            style=ButtonStyle.PRIMARY,
        )
    )

    return builder.as_markup()


# ============================================================
# ACCEPT PENDING
# ============================================================

def accept_pending_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Accept All",
            callback_data="confirm_accept_pending",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data="cancel_action",
            style=ButtonStyle.DANGER,
        ),
    )

    return builder.as_markup()


# ============================================================
# PREVIEW MESSAGE
# ============================================================

def preview_message_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Edit DM",
            callback_data="edit_dm_message",
            style=ButtonStyle.PRIMARY,
        ),
        InlineKeyboardButton(
            text="✏️ Edit Reply",
            callback_data="edit_auto_reply",
            style=ButtonStyle.PRIMARY,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Main Menu",
            callback_data="main_menu",
            style=ButtonStyle.SUCCESS,
        )
    )

    return builder.as_markup()


# ============================================================
# EXPORT ALL
# ============================================================

__all__ = [
    "remove_keyboard",
    "main_menu_keyboard",
    "owner_main_menu_keyboard",
    "force_sub_keyboard",
    "back_to_main_inline",
    "confirm_cancel_keyboard",
    "session_select_keyboard",
    "remove_account_keyboard",
    "campaign_source_keyboard",
    "campaign_start_keyboard",
    "campaign_running_keyboard",
    "delay_select_keyboard",
    "scrape_type_keyboard",
    "how_to_use_keyboard",
    "support_keyboard",
    "create_own_bot_keyboard",
    "vip_keyboard",
    "refer_earn_keyboard",
    "leaderboard_keyboard",
    "referral_history_keyboard",
    "my_stats_keyboard",
    "my_account_keyboard",
    "no_credits_keyboard",
    "not_configured_keyboard",
    "no_session_keyboard",
    "admin_panel_keyboard",
    "admin_users_keyboard",
    "admin_keys_keyboard",
    "admin_forcesub_keyboard",
    "channel_type_keyboard",
    "admin_proxy_keyboard",
    "admin_settings_keyboard",
    "admin_refer_settings_keyboard",
    "admin_stats_keyboard",
    "active_tasks_keyboard",
    "stealth_level_keyboard",
    "view_keys_keyboard",
    "view_channels_keyboard",
    "view_sources_keyboard",
    "accept_pending_keyboard",
    "preview_message_keyboard",
]