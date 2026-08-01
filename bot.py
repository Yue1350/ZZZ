import asyncio
import logging

import discord
from discord.ext import commands

import database as db
from config import DISCORD_TOKEN, GUILD_ID

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("zzz-bot")

INTENTS = discord.Intents.default()
# 메시지 내용이 필요하면 아래 줄 활성화 + 디스코드 개발자 포털에서도 Message Content Intent 켜기
# INTENTS.message_content = True

EXTENSIONS = [
    "cogs.zzz_data",
    "cogs.notifications",
]


class ZZZBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        await db.init_db()

        for ext in EXTENSIONS:
            await self.load_extension(ext)
            log.info(f"Cog 로드 완료: {ext}")

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info(f"슬래시 커맨드 {len(synced)}개를 서버({GUILD_ID})에 즉시 동기화했어요.")
        else:
            synced = await self.tree.sync()
            log.info(f"슬래시 커맨드 {len(synced)}개를 전역으로 동기화했어요. (반영까지 최대 1시간 소요될 수 있음)")

    async def on_ready(self):
        log.info(f"로그인 완료: {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Game(name="젠존제 | /데이터목록"))


async def main():
    if not DISCORD_TOKEN:
        raise SystemExit(
            "❌ DISCORD_TOKEN이 설정되지 않았어요. .env 파일을 만들고 토큰을 입력해주세요. "
            "(.env.example 파일 참고)"
        )

    bot = ZZZBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
