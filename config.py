import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID") or None

_DEFAULT_NITTER_INSTANCES = [
    "nitter.net",
    "nitter.privacyredirect.com",
    "nitter.poast.org",
    "xcancel.com",
]
_nitter_env = os.getenv("NITTER_INSTANCES", "")
NITTER_INSTANCES = (
    [i.strip() for i in _nitter_env.split(",") if i.strip()]
    if _nitter_env
    else _DEFAULT_NITTER_INSTANCES
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or None

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

DB_PATH = os.path.join(os.path.dirname(__file__), "zzz_bot.db")
ZZZ_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "zzz_data.json")
