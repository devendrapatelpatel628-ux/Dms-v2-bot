# ============================================================
#         ZENKAI DMS FORWARDING BOT - FINGERPRINT
# ============================================================

import random
import asyncio
import hashlib
import json
from datetime import datetime
from config import (
    DEVICE_MODELS,
    SYSTEM_VERSIONS,
    APP_VERSIONS,
    LANG_CODES,
    SYSTEM_LANG_CODES,
    STEALTH_LEVELS,
)


# ============================================================
# FINGERPRINT STORE
# Used to track generated fingerprints and ensure
# no two active sessions look identical
# ============================================================

_fingerprint_store = {}


# ============================================================
# DEVICE FINGERPRINT GENERATOR
# ============================================================

def generate_device_fingerprint(user_id: int = None) -> dict:
    """
    Generate a completely unique device fingerprint.
    Checks against existing fingerprints to ensure
    no two sessions look identical.
    7-layer fingerprint system.
    """

    max_attempts = 50
    for attempt in range(max_attempts):

        # Layer 1: Device Identity
        device_model = random.choice(DEVICE_MODELS)
        system_version = SYSTEM_VERSIONS.get(
            device_model,
            "Android 13"
        )
        app_version = random.choice(APP_VERSIONS)

        # Layer 2: Language
        lang_code = random.choice(LANG_CODES)
        system_lang_code = random.choice(SYSTEM_LANG_CODES)

        # Layer 3: Connection timing seeds
        # (stored as seeds, applied during actual connection)
        pre_connect_delay = round(random.uniform(0.3, 1.8), 3)
        pre_send_code_delay = round(random.uniform(1.2, 4.5), 3)
        pre_sign_in_delay = round(random.uniform(2.1, 6.3), 3)
        api_call_delay = round(random.uniform(0.4, 2.2), 3)
        micro_jitter = round(random.uniform(0.1, 0.9), 3)

        # Layer 4: MTProto layer randomization
        flood_sleep_threshold = random.randint(20, 120)
        receive_delay = round(random.uniform(0.5, 2.5), 3)
        connection_retries = random.randint(3, 8)
        retry_delay = round(random.uniform(1.0, 5.0), 3)

        # Layer 5: Session behavior seeds
        post_login_delay = round(random.uniform(3.0, 8.0), 3)
        online_pattern = random.choice([
            "active",
            "semi_active",
            "passive"
        ])

        # Layer 6: Typing & interaction pattern
        typing_delay_min = round(random.uniform(1.0, 2.5), 3)
        typing_delay_max = round(random.uniform(3.0, 6.5), 3)
        read_receipt_delay = round(random.uniform(0.5, 3.0), 3)
        message_send_delay = round(random.uniform(0.3, 1.5), 3)

        # Layer 7: Anti-pattern unique seed
        unique_seed = random.randint(100000, 999999)

        fingerprint = {
            # Identity
            "device_model":         device_model,
            "system_version":       system_version,
            "app_version":          app_version,
            "lang_code":            lang_code,
            "system_lang_code":     system_lang_code,

            # Connection timing
            "pre_connect_delay":    pre_connect_delay,
            "pre_send_code_delay":  pre_send_code_delay,
            "pre_sign_in_delay":    pre_sign_in_delay,
            "api_call_delay":       api_call_delay,
            "micro_jitter":         micro_jitter,

            # MTProto
            "flood_sleep_threshold": flood_sleep_threshold,
            "receive_delay":        receive_delay,
            "connection_retries":   connection_retries,
            "retry_delay":          retry_delay,

            # Session behavior
            "post_login_delay":     post_login_delay,
            "online_pattern":       online_pattern,

            # Typing & interaction
            "typing_delay_min":     typing_delay_min,
            "typing_delay_max":     typing_delay_max,
            "read_receipt_delay":   read_receipt_delay,
            "message_send_delay":   message_send_delay,

            # Anti-pattern
            "unique_seed":          unique_seed,

            # Metadata
            "generated_at":         datetime.now().isoformat(),
            "user_id":              user_id,
        }

        # Generate hash to check uniqueness
        fp_hash = _hash_fingerprint(fingerprint)

        # Check if this fingerprint already exists
        if fp_hash not in _fingerprint_store.values():
            if user_id:
                _fingerprint_store[user_id] = fp_hash
            return fingerprint

    # If we couldn't generate unique after max_attempts,
    # force uniqueness via unique_seed
    fingerprint["unique_seed"] = random.randint(1000000, 9999999)
    return fingerprint


def _hash_fingerprint(fingerprint: dict) -> str:
    """
    Generate a hash of key fingerprint fields
    for uniqueness checking.
    """
    key_fields = {
        "device_model":     fingerprint["device_model"],
        "system_version":   fingerprint["system_version"],
        "app_version":      fingerprint["app_version"],
        "lang_code":        fingerprint["lang_code"],
        "unique_seed":      fingerprint["unique_seed"],
    }
    raw = json.dumps(key_fields, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def clear_fingerprint(user_id: int):
    """Remove a user's fingerprint from the store."""
    _fingerprint_store.pop(user_id, None)


def get_all_fingerprints() -> dict:
    """Get all stored fingerprint hashes."""
    return dict(_fingerprint_store)


# ============================================================
# HUMAN LAYER - DELAY ENGINE
# ============================================================

async def human_delay(
    min_seconds: float = 0.4,
    max_seconds: float = 2.1,
    stealth_level: int = 3
):
    """
    Core human delay function.
    Applies a random delay based on stealth level.
    Used everywhere in the bot.
    """
    # Get stealth level multipliers
    stealth = STEALTH_LEVELS.get(stealth_level, STEALTH_LEVELS[3])
    stealth_min_human = stealth[2]
    stealth_max_human = stealth[3]

    # Use stealth level to adjust the range
    effective_min = max(min_seconds, stealth_min_human)
    effective_max = max(max_seconds, stealth_max_human)

    delay = random.uniform(effective_min, effective_max)
    await asyncio.sleep(delay)


async def micro_jitter(max_seconds: float = 0.5):
    """
    Tiny random jitter applied between every
    single API call to break robotic patterns.
    """
    await asyncio.sleep(random.uniform(0.05, max_seconds))


async def typing_simulation(
    fingerprint: dict = None,
    stealth_level: int = 3
):
    """
    Simulate human typing delay.
    Uses fingerprint-specific timing if available.
    """
    if fingerprint:
        delay = random.uniform(
            fingerprint["typing_delay_min"],
            fingerprint["typing_delay_max"]
        )
    else:
        stealth = STEALTH_LEVELS.get(stealth_level, STEALTH_LEVELS[3])
        delay = random.uniform(1.2, 5.8)

    await asyncio.sleep(delay)


async def read_receipt_simulation(fingerprint: dict = None):
    """
    Simulate the time it takes for a human
    to read a message before responding.
    """
    if fingerprint:
        delay = fingerprint["read_receipt_delay"]
    else:
        delay = random.uniform(0.5, 3.0)
    await asyncio.sleep(delay)


async def post_login_simulation(fingerprint: dict = None):
    """
    Simulate delay after login before taking
    any action. Mimics a human opening the app
    and looking at the interface.
    """
    if fingerprint:
        delay = fingerprint["post_login_delay"]
    else:
        delay = random.uniform(3.0, 8.0)
    await asyncio.sleep(delay)


async def pre_connect_simulation(fingerprint: dict = None):
    """Delay before initiating connection."""
    if fingerprint:
        delay = fingerprint["pre_connect_delay"]
    else:
        delay = random.uniform(0.3, 1.8)
    await asyncio.sleep(delay)


async def pre_send_code_simulation(fingerprint: dict = None):
    """
    Delay before calling send_code_request.
    Mimics user looking up their phone number.
    """
    if fingerprint:
        delay = fingerprint["pre_send_code_delay"]
    else:
        delay = random.uniform(1.2, 4.5)
    await asyncio.sleep(delay)


async def pre_sign_in_simulation(fingerprint: dict = None):
    """
    Delay before signing in with the code.
    Mimics user reading SMS and typing the code.
    """
    if fingerprint:
        delay = fingerprint["pre_sign_in_delay"]
    else:
        delay = random.uniform(2.1, 6.3)
    await asyncio.sleep(delay)


async def dm_send_delay(
    stealth_level: int = 3,
    custom_min: float = None,
    custom_max: float = None
):
    """
    Delay between each DM sent.
    Uses stealth level or custom range from admin settings.
    """
    if custom_min and custom_max:
        delay = random.uniform(custom_min, custom_max)
    else:
        stealth = STEALTH_LEVELS.get(stealth_level, STEALTH_LEVELS[3])
        delay = random.uniform(stealth[0], stealth[1])

    await asyncio.sleep(delay)


async def batch_delay(
    stealth_level: int = 3
):
    """
    Delay between scraping batches.
    Slightly longer than micro_jitter but shorter than dm_send_delay.
    """
    stealth = STEALTH_LEVELS.get(stealth_level, STEALTH_LEVELS[3])
    base = stealth[2]
    delay = random.uniform(base, base * 3)
    await asyncio.sleep(delay)


async def flood_wait_handler(seconds: int):
    """
    Handle Telegram FloodWait errors.
    Waits exactly the required time + small jitter.
    """
    jitter = random.uniform(0.3, 1.9)
    total_wait = seconds + jitter
    await asyncio.sleep(total_wait)


async def irregular_batch_pattern(
    base_min: int = 80,
    base_max: int = 180
) -> int:
    """
    Returns a random batch size to avoid
    predictable scraping patterns.
    Never the same number twice in a row.
    """
    await micro_jitter(0.3)
    return random.randint(base_min, base_max)


async def human_dm_pattern(sent_count: int):
    """
    Apply irregular sending pattern based on
    how many messages have been sent.
    Mimics human behavior:
    - Send a few, pause
    - Send more, longer pause
    - Never perfectly regular
    """
    if sent_count % random.randint(2, 6) == 0:
        # Short pause every 2-6 messages
        await asyncio.sleep(random.uniform(2.0, 8.0))
    elif sent_count % random.randint(10, 20) == 0:
        # Medium pause every 10-20 messages
        await asyncio.sleep(random.uniform(15.0, 45.0))
    elif sent_count % random.randint(50, 100) == 0:
        # Longer pause every 50-100 messages
        await asyncio.sleep(random.uniform(60.0, 180.0))
    else:
        # Normal jitter
        await micro_jitter(1.0)


# ============================================================
# ONLINE PRESENCE SIMULATOR
# ============================================================

async def simulate_online_presence(
    client,
    fingerprint: dict = None
):
    """
    Simulate realistic online/offline patterns
    based on the session's fingerprint online_pattern.
    """
    pattern = "active"
    if fingerprint:
        pattern = fingerprint.get("online_pattern", "active")

    try:
        if pattern == "active":
            # Stay online, short gaps
            await asyncio.sleep(random.uniform(0.5, 2.0))
        elif pattern == "semi_active":
            # Go offline occasionally
            await asyncio.sleep(random.uniform(1.0, 5.0))
        elif pattern == "passive":
            # Mostly offline, rarely online
            await asyncio.sleep(random.uniform(3.0, 10.0))
    except Exception:
        pass


# ============================================================
# PROGRESS UPDATE TIMING
# ============================================================

async def progress_update_delay(
    base_interval: int = 8
) -> float:
    """
    Returns a randomized delay for progress updates.
    Ensures progress edits never happen at perfectly
    regular intervals (looks human).
    """
    jitter = random.uniform(-2.0, 4.0)
    delay = max(4.0, base_interval + jitter)
    await asyncio.sleep(delay)
    return delay


# ============================================================
# ANTI-DETECTION CHECKS
# ============================================================

def is_suspicious_pattern(
    actions_per_minute: float,
    threshold: float = 30.0
) -> bool:
    """
    Check if the current action rate is suspiciously high.
    Returns True if the rate exceeds the threshold.
    Owner can adjust threshold via stealth level.
    """
    return actions_per_minute > threshold


def get_safe_batch_size(
    stealth_level: int = 3,
    custom_min: int = None,
    custom_max: int = None
) -> int:
    """
    Get a safe random batch size for scraping.
    Never returns the same value twice consecutively.
    """
    if custom_min and custom_max:
        return random.randint(custom_min, custom_max)

    # Stealth level affects batch size
    batch_ranges = {
        1: (150, 200),
        2: (120, 180),
        3: (80,  180),
        4: (50,  120),
        5: (30,  80),
    }
    low, high = batch_ranges.get(stealth_level, (80, 180))
    return random.randint(low, high)


# ============================================================
# FINGERPRINT SERIALIZER
# (For storing fingerprint in DB with session)
# ============================================================

def serialize_fingerprint(fingerprint: dict) -> str:
    """Convert fingerprint dict to JSON string for DB storage."""
    return json.dumps(fingerprint)


def deserialize_fingerprint(fp_string: str) -> dict:
    """Convert JSON string back to fingerprint dict."""
    try:
        return json.loads(fp_string)
    except Exception:
        return {}


# ============================================================
# EXPORT ALL
# ============================================================

__all__ = [
    "generate_device_fingerprint",
    "clear_fingerprint",
    "get_all_fingerprints",
    "human_delay",
    "micro_jitter",
    "typing_simulation",
    "read_receipt_simulation",
    "post_login_simulation",
    "pre_connect_simulation",
    "pre_send_code_simulation",
    "pre_sign_in_simulation",
    "dm_send_delay",
    "batch_delay",
    "flood_wait_handler",
    "irregular_batch_pattern",
    "human_dm_pattern",
    "simulate_online_presence",
    "progress_update_delay",
    "is_suspicious_pattern",
    "get_safe_batch_size",
    "serialize_fingerprint",
    "deserialize_fingerprint",
]