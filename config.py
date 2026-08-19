# ============================================================
#         ZENKAI DMS FORWARDING BOT - CONFIG
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CORE SETTINGS
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME")
DATABASE_NAME = os.getenv("DATABASE_NAME", "zenkai.db")
BOT_NAME = os.getenv("BOT_NAME", "Zenkai DMs Forwarding Bot")
BOT_VERSION = os.getenv("BOT_VERSION", "1.0.0")

# ============================================================
# DEFAULT BOT SETTINGS (Overridable via Admin Panel)
# ============================================================

# Credits
DEFAULT_FREE_CREDITS = 100
DEFAULT_REFERRAL_CREDITS = 10
DEFAULT_NEW_USER_BONUS = 25

# Concurrency
DEFAULT_CONCURRENCY = 100
MAX_CONCURRENCY = 99999  # No real cap, owner decides

# Accounts
DEFAULT_MAX_ACCOUNTS_PER_USER = 3

# DM Delays (seconds)
DEFAULT_DM_DELAY_MIN = 5
DEFAULT_DM_DELAY_MAX = 15
DEFAULT_REPLY_DELAY_MIN = 6
DEFAULT_REPLY_DELAY_MAX = 18

# Human Layer Delays (seconds)
DEFAULT_HUMAN_DELAY_MIN = 0.4
DEFAULT_HUMAN_DELAY_MAX = 2.1
DEFAULT_TYPING_DELAY_MIN = 1.2
DEFAULT_TYPING_DELAY_MAX = 5.8

# Stealth Level (1-5)
DEFAULT_STEALTH_LEVEL = 3

# Progress Update Interval (seconds)
DEFAULT_PROGRESS_INTERVAL = 2

# Scraping
DEFAULT_BATCH_SIZE_MIN = 80
DEFAULT_BATCH_SIZE_MAX = 180

# Proxy Hunter
DEFAULT_PROXY_TIMEOUT = 10
DEFAULT_PROXY_TEST_RETRIES = 0
DEFAULT_HUNTER_INTERVAL = 300  # seconds between hunt cycles

# Referral
DEFAULT_REFER_SYSTEM = True

# ============================================================
# STEALTH LEVEL DELAY RANGES
# (Min DM delay, Max DM delay, Min human delay, Max human delay)
# ============================================================
STEALTH_LEVELS = {
    1: (5,  15,  0.2, 0.8),   # Fastest, riskiest
    2: (10, 25,  0.3, 1.2),   # Fast, moderate risk
    3: (15, 55,  0.4, 2.1),   # Balanced (default)
    4: (30, 90,  0.6, 3.0),   # Safe, slower
    5: (60, 180, 1.0, 5.0),   # Safest, slowest
}

# ============================================================
# FINGERPRINT - REAL DEVICE POOL
# ============================================================
DEVICE_MODELS = [
    "Samsung Galaxy S23 Ultra",
    "Samsung Galaxy S22",
    "Samsung Galaxy S21 FE",
    "Samsung Galaxy A54",
    "Samsung Galaxy A34",
    "iPhone 14 Pro Max",
    "iPhone 14 Pro",
    "iPhone 13",
    "iPhone 12 Pro",
    "iPhone 11",
    "Google Pixel 7 Pro",
    "Google Pixel 7",
    "Google Pixel 6a",
    "OnePlus 11",
    "OnePlus 10 Pro",
    "Xiaomi 13 Pro",
    "Xiaomi 12T",
    "Redmi Note 12 Pro",
    "Redmi Note 11",
    "Realme GT3",
    "Realme 10 Pro",
    "OPPO Find X6",
    "OPPO Reno 10",
    "Vivo X90 Pro",
    "Huawei P50 Pro",
    "Nokia G60",
    "Motorola Edge 40",
    "Sony Xperia 1 V",
]

SYSTEM_VERSIONS = {
    "Samsung Galaxy S23 Ultra": "Android 13",
    "Samsung Galaxy S22": "Android 13",
    "Samsung Galaxy S21 FE": "Android 13",
    "Samsung Galaxy A54": "Android 13",
    "Samsung Galaxy A34": "Android 13",
    "iPhone 14 Pro Max": "iOS 16.5",
    "iPhone 14 Pro": "iOS 16.4",
    "iPhone 13": "iOS 16.3",
    "iPhone 12 Pro": "iOS 16.2",
    "iPhone 11": "iOS 15.7",
    "Google Pixel 7 Pro": "Android 13",
    "Google Pixel 7": "Android 13",
    "Google Pixel 6a": "Android 13",
    "OnePlus 11": "Android 13",
    "OnePlus 10 Pro": "Android 13",
    "Xiaomi 13 Pro": "Android 13",
    "Xiaomi 12T": "Android 12",
    "Redmi Note 12 Pro": "Android 12",
    "Redmi Note 11": "Android 11",
    "Realme GT3": "Android 13",
    "Realme 10 Pro": "Android 13",
    "OPPO Find X6": "Android 13",
    "OPPO Reno 10": "Android 13",
    "Vivo X90 Pro": "Android 13",
    "Huawei P50 Pro": "Android 12",
    "Nokia G60": "Android 12",
    "Motorola Edge 40": "Android 13",
    "Sony Xperia 1 V": "Android 13",
}

APP_VERSIONS = [
    "9.6.3",
    "9.5.9",
    "9.5.3",
    "9.4.1",
    "9.3.3",
    "9.3.1",
    "9.2.1",
    "9.1.3",
    "9.0.1",
    "8.9.2",
]

LANG_CODES = [
    "en", "hi", "ar", "ru", "de",
    "fr", "tr", "es", "pt", "it",
    "id", "fa", "ur", "bn", "vi",
]

SYSTEM_LANG_CODES = [
    "en-US", "en-GB", "hi-IN", "ar-SA",
    "ru-RU", "de-DE", "fr-FR", "tr-TR",
    "es-ES", "pt-BR", "it-IT", "id-ID",
    "fa-IR", "ur-PK", "bn-BD", "vi-VN",
]

# ============================================================
# FREE PROXY SOURCES
# ============================================================
PROXY_SOURCES = [
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&simplified=true",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=socks5",
    "https://www.proxyscan.io/download?type=socks5",
]

# ============================================================
# TELEGRAM MTProto SERVERS (For proxy testing)
# ============================================================
TELEGRAM_TEST_SERVERS = [
    ("149.154.167.51", 443),
    ("149.154.167.92", 443),
    ("91.108.4.1", 443),
]

# ============================================================
# MESSAGES & UI TEXT
# ============================================================
WELCOME_TEXT = (
    "⚡ <b>𝗭𝗲𝗻𝗸𝗮𝗶 𝗗𝗠𝘀 𝗙𝗼𝗿𝘄𝗮𝗿𝗱𝗶𝗻𝗴 𝗕𝗼𝘁</b> ⚡\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Hey <b>{first_name}</b>! 👋\n\n"
    "🔥 <b>𝗧𝗵𝗲 𝗨𝗹𝘁𝗶𝗺𝗮𝘁𝗲 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗗𝗠 𝗧𝗼𝗼𝗹𝗸𝗶𝘁</b>\n\n"
    "📤 <b>Scrape</b> — Extract all members from any\n"
    "   group or channel instantly\n\n"
    "📨 <b>Mass DM</b> — Send personalized messages\n"
    "   to thousands with human-like patterns\n\n"
    "🔑 <b>Auto Reply</b> — Smart follow-up when\n"
    "   someone responds to your DM\n\n"
    "✅ <b>Accept Pending</b> — Accept all join\n"
    "   requests in your channel instantly\n\n"
    "🎯 <b>Refer & Earn</b> — Earn 10 credits for\n"
    "   every friend you invite!\n\n"
    "🎁 <b>Free Credits</b> — You get {credits} free\n"
    "   credits to start right away!\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "💎 <b>Credits:</b> {credits} | 🆔 <b>ID:</b> {user_id}"
)

FORCE_SUB_TEXT = (
    "🔒 <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "You must join <b>ALL</b> channels below\n"
    "to use this bot 👇\n\n"
    "{channel_status}\n\n"
    "Join the remaining channels and\n"
    "tap <b>Verify</b> below 👇"
)

NOT_CONFIGURED_TEXT = (
    "⚠️ <b>Bot Not Configured Yet</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "The owner has not set up the\n"
    "API credentials yet.\n\n"
    "Please contact the owner."
)

BANNED_TEXT = (
    "🚫 <b>You Are Banned</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "You have been banned from\n"
    "using this bot.\n\n"
    "Contact support if you think\n"
    "this is a mistake."
)

NO_CREDITS_TEXT = (
    "💎 <b>No Credits Remaining</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "You have <b>0 credits</b> left.\n\n"
    "🎫 Redeem a key to get more credits\n"
    "🎯 Refer friends to earn 10 credits each\n"
    "💎 Go VIP for unlimited access"
)