import discord
from discord import app_commands
from discord.ext import commands

from config import ZZZ_DATA_CSV_PATH
from utils.sheet_parser import parse_setting_csv

MAX_FIELD_LEN = 1000  # 디스코드 embed 필드 길이 제한 방지용


class ZZZData(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: dict[str, list[dict]] = {}
        self.reload_data()

    def reload_data(self):
        characters = parse_setting_csv(ZZZ_DATA_CSV_PATH)
        self.data = {"캐릭터": characters} if characters else {}

    def _all_categories(self):
        return list(self.data.keys())

    def _entries(self, category: str):
        return self.data.get(category, [])

    def _entry_name(self, entry: dict):
        for key in ("이름", "name", "Name"):
            if key in entry:
                return str(entry[key])
        if entry:
            return str(next(iter(entry.values())))
        return "이름없음"

    def _build_embed(self, category: str, entry: dict) -> discord.Embed:
        title = self._entry_name(entry)
        embed = discord.Embed(title=title, description=f"분류: {category}", color=0x8A2BE2)
        for key, value in entry.items():
            if key in ("이름", "name", "Name"):
                continue
            text = str(value) if value not in (None, "") else "-"
            embed.add_field(name=key, value=text[:MAX_FIELD_LEN], inline=len(text) < 40)
        return embed

    # ---------------- 명령어 ----------------

    @app_commands.command(name="데이터목록", description="봇에 등록된 시트 데이터 분류와 개수를 봅니다.")
    async def data_list(self, interaction: discord.Interaction):
        if not self.data:
            await interaction.response.send_message(
                "등록된 데이터가 없어요. data/zzz_data.csv 파일을 넣고 /데이터새로고침 해주세요.",
                ephemeral=True,
            )
            return
        lines = "\n".join(f"- **{cat}**: {len(entries)}개" for cat, entries in self.data.items())
        await interaction.response.send_message(f"**등록된 데이터 분류**\n{lines}")

    @app_commands.command(name="데이터", description="분류와 이름으로 시트 데이터를 조회합니다.")
    @app_commands.describe(분류="데이터 분류 선택", 이름="조회할 항목 이름")
    async def data_lookup(self, interaction: discord.Interaction, 분류: str, 이름: str):
        entries = self._entries(분류)
        match = next((e for e in entries if self._entry_name(e) == 이름), None)
        if not match:
            match = next((e for e in entries if 이름.lower() in self._entry_name(e).lower()), None)
        if not match:
            await interaction.response.send_message(f"`{분류}` 분류에서 `{이름}`을(를) 찾지 못했어요.", ephemeral=True)
            return
        await interaction.response.send_message(embed=self._build_embed(분류, match))

    @data_lookup.autocomplete("분류")
    async def category_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=cat, value=cat)
            for cat in self._all_categories() if current.lower() in cat.lower()
        ][:25]

    @data_lookup.autocomplete("이름")
    async def name_autocomplete(self, interaction: discord.Interaction, current: str):
        분류 = interaction.namespace.분류 or ""
        entries = self._entries(분류)
        names = [self._entry_name(e) for e in entries]
        return [
            app_commands.Choice(name=n, value=n)
            for n in names if current.lower() in n.lower()
        ][:25]

    @app_commands.command(name="데이터검색", description="모든 분류에서 키워드로 데이터를 검색합니다.")
    @app_commands.describe(키워드="검색할 키워드")
    async def data_search(self, interaction: discord.Interaction, 키워드: str):
        results = []
        for category, entries in self.data.items():
            for entry in entries:
                haystack = " ".join(str(v) for v in entry.values()).lower()
                if 키워드.lower() in haystack:
                    results.append((category, self._entry_name(entry)))
        if not results:
            await interaction.response.send_message(f"`{키워드}`에 대한 검색 결과가 없어요.", ephemeral=True)
            return
        lines = "\n".join(f"- [{cat}] {name}" for cat, name in results[:25])
        more = f"\n...외 {len(results) - 25}건" if len(results) > 25 else ""
        await interaction.response.send_message(f"**'{키워드}' 검색 결과**\n{lines}{more}")

    @app_commands.command(name="데이터새로고침", description="(관리자) data/zzz_data.csv 파일을 다시 불러옵니다.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def data_reload(self, interaction: discord.Interaction):
        self.reload_data()
        total = sum(len(v) for v in self.data.values())
        await interaction.response.send_message(f"🔄 CSV를 다시 불러왔어요. (총 {total}개 항목)", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ZZZData(bot))
