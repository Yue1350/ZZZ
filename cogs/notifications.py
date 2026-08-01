import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp

import database as db
from config import CHECK_INTERVAL_SECONDS
from utils import twitter_checker, youtube_checker


class Notifications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.check_loop.change_interval(seconds=CHECK_INTERVAL_SECONDS)

    async def cog_load(self):
        self.session = aiohttp.ClientSession()
        self.check_loop.start()

    async def cog_unload(self):
        self.check_loop.cancel()
        if self.session:
            await self.session.close()

    # ---------------- 알림 채널 설정 ----------------

    notify_group = app_commands.Group(name="알림채널", description="트위터/유튜브 알림을 보낼 채널을 설정합니다.")

    @notify_group.command(name="설정", description="이 채널을 트위터/유튜브 알림 채널로 지정합니다.")
    @app_commands.describe(종류="어떤 알림을 이 채널로 보낼지 선택하세요")
    @app_commands.choices(종류=[
        app_commands.Choice(name="트위터", value="twitter"),
        app_commands.Choice(name="유튜브", value="youtube"),
        app_commands.Choice(name="둘 다", value="both"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, 종류: app_commands.Choice[str]):
        kinds = ["twitter", "youtube"] if 종류.value == "both" else [종류.value]
        for k in kinds:
            await db.set_notify_channel(interaction.guild_id, k, interaction.channel_id)
        await interaction.response.send_message(
            f"✅ 이 채널을 {종류.name} 알림 채널로 설정했어요.", ephemeral=True
        )

    # ---------------- 트위터 관리 ----------------

    twitter_group = app_commands.Group(name="트위터알림", description="감시할 트위터 계정을 관리합니다.")

    @twitter_group.command(name="추가", description="새 글 알림을 받을 트위터 계정을 추가합니다.")
    @app_commands.describe(아이디="@ 없이 트위터(X) 아이디만 입력하세요")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def twitter_add(self, interaction: discord.Interaction, 아이디: str):
        if not twitter_checker.is_configured():
            await interaction.response.send_message(
                "⚠️ 사용 가능한 Nitter 인스턴스가 없어요. .env의 NITTER_INSTANCES를 확인해주세요.",
                ephemeral=True,
            )
            return

        ok = await db.add_twitter_watch(interaction.guild_id, 아이디)
        if ok:
            await interaction.response.send_message(f"✅ `@{아이디.lstrip('@')}` 알림 등록 완료!", ephemeral=True)
        else:
            await interaction.response.send_message(f"이미 등록되어 있는 계정이에요.", ephemeral=True)

    @twitter_group.command(name="삭제", description="감시 중인 트위터 계정을 삭제합니다.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def twitter_remove(self, interaction: discord.Interaction, 아이디: str):
        ok = await db.remove_twitter_watch(interaction.guild_id, 아이디)
        msg = f"🗑️ `@{아이디.lstrip('@')}` 삭제했어요." if ok else "등록되어 있지 않은 계정이에요."
        await interaction.response.send_message(msg, ephemeral=True)

    @twitter_group.command(name="목록", description="현재 감시 중인 트위터 계정 목록을 봅니다.")
    async def twitter_list(self, interaction: discord.Interaction):
        rows = await db.list_twitter_watch(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("등록된 트위터 계정이 없어요.", ephemeral=True)
            return
        lines = "\n".join(f"- @{r[2]}" for r in rows)
        await interaction.response.send_message(f"**감시 중인 트위터 계정**\n{lines}", ephemeral=True)

    # ---------------- 유튜브 관리 ----------------

    youtube_group = app_commands.Group(name="유튜브알림", description="감시할 유튜브 채널을 관리합니다.")

    @youtube_group.command(name="추가", description="새 영상 알림을 받을 유튜브 채널을 추가합니다.")
    @app_commands.describe(채널="채널 URL, @핸들, 또는 채널ID(UC로 시작)를 입력하세요")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def youtube_add(self, interaction: discord.Interaction, 채널: str):
        await interaction.response.defer(ephemeral=True)
        channel_id = await youtube_checker.resolve_channel_id_from_handle(self.session, 채널)
        if not channel_id:
            await interaction.followup.send(
                "❌ 채널을 찾지 못했어요. 채널 URL이나 정확한 @핸들을 입력해주세요.", ephemeral=True
            )
            return

        info = await youtube_checker.fetch_latest_video(self.session, channel_id)
        channel_name = info["channel_name"] if info else 채널

        ok = await db.add_youtube_watch(interaction.guild_id, channel_id, channel_name)
        if ok:
            await interaction.followup.send(f"✅ `{channel_name}` 채널 알림 등록 완료!", ephemeral=True)
        else:
            await interaction.followup.send("이미 등록되어 있는 채널이에요.", ephemeral=True)

    @youtube_group.command(name="삭제", description="감시 중인 유튜브 채널을 삭제합니다.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def youtube_remove(self, interaction: discord.Interaction, 채널id: str):
        ok = await db.remove_youtube_watch(interaction.guild_id, 채널id)
        msg = "🗑️ 삭제했어요." if ok else "등록되어 있지 않은 채널이에요."
        await interaction.response.send_message(msg, ephemeral=True)

    @youtube_group.command(name="목록", description="현재 감시 중인 유튜브 채널 목록을 봅니다.")
    async def youtube_list(self, interaction: discord.Interaction):
        rows = await db.list_youtube_watch(interaction.guild_id)
        if not rows:
            await interaction.response.send_message("등록된 유튜브 채널이 없어요.", ephemeral=True)
            return
        lines = "\n".join(f"- {r[3]} (`{r[2]}`)" for r in rows)
        await interaction.response.send_message(f"**감시 중인 유튜브 채널**\n{lines}", ephemeral=True)

    # ---------------- 백그라운드 체크 루프 ----------------

    @tasks.loop(seconds=300)
    async def check_loop(self):
        await self._check_twitter()
        await self._check_youtube()

    @check_loop.before_loop
    async def before_check_loop(self):
        await self.bot.wait_until_ready()

    async def _check_twitter(self):
        if not twitter_checker.is_configured():
            return
        rows = await db.list_twitter_watch()
        for row_id, guild_id, username, last_tweet_id in rows:
            latest = await twitter_checker.fetch_latest_tweet(self.session, username)
            if not latest:
                continue
            if last_tweet_id is None:
                # 최초 등록 시에는 알림 없이 기준점만 저장
                await db.update_last_tweet_id(row_id, latest["tweet_id"])
                continue
            if latest["tweet_id"] != last_tweet_id:
                await db.update_last_tweet_id(row_id, latest["tweet_id"])
                await self._send_twitter_alert(guild_id, username, latest)

    async def _check_youtube(self):
        rows = await db.list_youtube_watch()
        for row_id, guild_id, channel_id, channel_name, last_video_id in rows:
            latest = await youtube_checker.fetch_latest_video(self.session, channel_id)
            if not latest:
                continue
            if last_video_id is None:
                await db.update_last_video_id(row_id, latest["video_id"])
                continue
            if latest["video_id"] != last_video_id:
                await db.update_last_video_id(row_id, latest["video_id"])
                await self._send_youtube_alert(guild_id, latest)

    async def _send_twitter_alert(self, guild_id, username, tweet):
        channel_id = await db.get_notify_channel(guild_id, "twitter")
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title=f"🐦 @{username} 새 트윗",
            description=tweet["text"],
            url=tweet["url"],
            color=0x1DA1F2,
        )
        await channel.send(embed=embed)

    async def _send_youtube_alert(self, guild_id, video):
        channel_id = await db.get_notify_channel(guild_id, "youtube")
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title=f"▶️ {video['channel_name']} 새 영상",
            description=video["title"],
            url=video["url"],
            color=0xFF0000,
        )
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Notifications(bot))
