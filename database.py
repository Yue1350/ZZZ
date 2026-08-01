import aiosqlite
from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notify_channels (
    guild_id INTEGER NOT NULL,
    kind TEXT NOT NULL,           -- 'twitter' or 'youtube'
    channel_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, kind)
);

CREATE TABLE IF NOT EXISTS twitter_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    username TEXT NOT NULL,       -- '@' 없이 저장
    last_tweet_id TEXT,
    UNIQUE(guild_id, username)
);

CREATE TABLE IF NOT EXISTS youtube_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id TEXT NOT NULL,     -- UC로 시작하는 유튜브 채널 ID
    channel_name TEXT,
    last_video_id TEXT,
    UNIQUE(guild_id, channel_id)
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


# ---------- 알림 채널 ----------

async def set_notify_channel(guild_id: int, kind: str, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO notify_channels (guild_id, kind, channel_id)
               VALUES (?, ?, ?)
               ON CONFLICT(guild_id, kind) DO UPDATE SET channel_id=excluded.channel_id""",
            (guild_id, kind, channel_id),
        )
        await db.commit()


async def get_notify_channel(guild_id: int, kind: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT channel_id FROM notify_channels WHERE guild_id=? AND kind=?",
            (guild_id, kind),
        )
        row = await cur.fetchone()
        return row[0] if row else None


# ---------- 트위터 감시 ----------

async def add_twitter_watch(guild_id: int, username: str):
    username = username.lstrip("@").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO twitter_watch (guild_id, username) VALUES (?, ?)",
                (guild_id, username),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_twitter_watch(guild_id: int, username: str):
    username = username.lstrip("@").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM twitter_watch WHERE guild_id=? AND username=?",
            (guild_id, username),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_twitter_watch(guild_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if guild_id is None:
            cur = await db.execute("SELECT id, guild_id, username, last_tweet_id FROM twitter_watch")
        else:
            cur = await db.execute(
                "SELECT id, guild_id, username, last_tweet_id FROM twitter_watch WHERE guild_id=?",
                (guild_id,),
            )
        return await cur.fetchall()


async def update_last_tweet_id(row_id: int, tweet_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE twitter_watch SET last_tweet_id=? WHERE id=?", (tweet_id, row_id)
        )
        await db.commit()


# ---------- 유튜브 감시 ----------

async def add_youtube_watch(guild_id: int, channel_id: str, channel_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO youtube_watch (guild_id, channel_id, channel_name) VALUES (?, ?, ?)",
                (guild_id, channel_id, channel_name),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_youtube_watch(guild_id: int, channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM youtube_watch WHERE guild_id=? AND channel_id=?",
            (guild_id, channel_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_youtube_watch(guild_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if guild_id is None:
            cur = await db.execute(
                "SELECT id, guild_id, channel_id, channel_name, last_video_id FROM youtube_watch"
            )
        else:
            cur = await db.execute(
                "SELECT id, guild_id, channel_id, channel_name, last_video_id FROM youtube_watch WHERE guild_id=?",
                (guild_id,),
            )
        return await cur.fetchall()


async def update_last_video_id(row_id: int, video_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE youtube_watch SET last_video_id=? WHERE id=?", (video_id, row_id)
        )
        await db.commit()
