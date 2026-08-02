import os
import urllib.parse
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import pandas as pd
import requests
from keep_alive import keep_alive

# 환경 변수 로드 및 서버 유지 실행
load_dotenv()
keep_alive()

# ---------------------------------------------------------
# 1. 나무위키/웹 이미지 검색 함수 (차단 방지용)
# ---------------------------------------------------------
def get_namu_image(char_name: str):
    try:
        clean_name = char_name.replace("S.", "").strip()
        encoded_name = urllib.parse.quote(f"젠레스 존 제로 {clean_name}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_name}+site:namu.wiki"
        res = requests.get(search_url, headers=headers, timeout=3)
        return f"https://raw.githubusercontent.com/site-images/zzz/{clean_name}.png"
    except:
        return None

# ---------------------------------------------------------
# 2. CSV 데이터 로드
# ---------------------------------------------------------
def load_data():
    df = pd.read_csv("build_data.csv", header=1)
    df.columns = df.columns.str.strip()
    
    if "캐릭명" in df.columns:
        df["캐릭명"] = df["캐릭명"].ffill()
    if "진영" in df.columns:
        df["진영"] = df["진영"].ffill()
        
    return df

# ---------------------------------------------------------
# 3. 캐릭터 선택 드롭다운 (2단계)
# ---------------------------------------------------------
class CharacterSelect(discord.ui.Select):
    def __init__(self, characters_df):
        options = []
        for _, row in characters_df.iterrows():
            c_name = str(row["캐릭명"]).strip()
            faction = str(row["진영"]).strip() if pd.notna(row["진영"]) else ""
            options.append(
                discord.SelectOption(
                    label=c_name,
                    description=f"{faction}" if faction else "세팅 정보 보기",
                    value=c_name
                )
            )
        
        super().__init__(
            placeholder="캐릭터를 선택해줘!",
            min_values=1,
            max_values=1,
            options=options[:25]  # 디스코드 제한: 최대 25개
        )
        self.characters_df = characters_df

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        selected_char = self.values[0]
        row = self.characters_df[self.characters_df["캐릭명"] == selected_char].iloc[0]

        def get_val(col_name):
            val = row.get(col_name)
            if pd.isna(val) or str(val).strip() == "":
                return "-"
            return str(val).strip()

        c_name = get_val("캐릭명")
        faction = get_val("진영")
        trait = get_val("특성")
        skill_lvl = get_val("스킬 레벨\n(평,회,지,특,궁)") if "스킬 레벨\n(평,회,지,특,궁)" in row else get_val("스킬 레벨")
        position = get_val("포지션")
        w_engine = get_val("W-엔진")
        set_4 = get_val("4세트")
        set_2 = get_val("2세트")
        breakthrough = get_val("핵심돌파")
        sub_stats = get_val("유효 부옵션")
        main_stat = get_val("주옵")
        crit_stat = get_val("치명타")
        etc = get_val("기타")

        disc_main_cols = [c for c in row.index if "디스크 주옵션" in c or "주옵션" in c]
        disc_mains = [get_val(c) for c in disc_main_cols if get_val(c) != "-"]
        disc_main_text = " / ".join(disc_mains) if disc_mains else "-"

        # 임베드 생성
        embed = discord.Embed(
            title=f"🎮 {c_name} ({faction}) 세팅 가이드",
            description=f"**특성:** {trait} | **포지션:** {position}\n**핵심 돌파:** {breakthrough}",
            color=0x00FF7F
        )

        # 썸네일 이미지 링크 세팅
        clean_char = c_name.replace("S.", "").strip()
        embed.set_thumbnail(url=f"https://act-webstatic.hoyoverse.com/game_record/zzz/role_square_avatar/{clean_char}.png")

        embed.add_field(name="🗡️ 추천 W-엔진", value=f"```{w_engine}```", inline=False)
        embed.add_field(name="💿 추천 디스크 세트", value=f"```4세트: {set_4}\n2세트: {set_2}```", inline=False)
        embed.add_field(name="📊 디스크 주옵션 (4/5/6번)", value=f"```{disc_main_text}```", inline=True)
        embed.add_field(name="🔍 유효 부옵션", value=f"```{sub_stats}```", inline=True)
        
        target_info = []
        if main_stat != "-": target_info.append(f"주옵: {main_stat}")
        if crit_stat != "-": target_info.append(f"치명타: {crit_stat}")
        target_text = " | ".join(target_info) if target_info else "-"
        
        embed.add_field(name="🎯 목표 스탯", value=f"```{target_text}```", inline=False)

        if etc != "-":
            embed.add_field(name="📝 참고 사항 / 계산법", value=f"```{etc}```", inline=False)

        if skill_lvl != "-":
            embed.set_footer(text=f"스킬 레벨 우선순위: {skill_lvl}")

        await interaction.followup.send(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)

# ---------------------------------------------------------
# 4. 카테고리 선택 드롭다운 (1단계)
# ---------------------------------------------------------
class CategorySelect(discord.ui.Select):
    def __init__(self, df):
        self.df = df
        options = [
            discord.SelectOption(label="강공", description="강공 포지션 캐릭터", emoji="⚔️"),
            discord.SelectOption(label="격파", description="격파 포지션 캐릭터", emoji="💥"),
            discord.SelectOption(label="이상", description="이상 포지션 캐릭터", emoji="🌀"),
            discord.SelectOption(label="지원", description="지원 포지션 캐릭터", emoji="🪄"),
            discord.SelectOption(label="방어", description="방어 포지션 캐릭터", emoji="🛡️"),
            discord.SelectOption(label="명파", description="명파 포지션 캐릭터", emoji="✨"),
        ]
        super().__init__(placeholder="카테고리를 고르고 세팅을 확인해봐!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        
        filtered_df = self.df[
            (self.df["포지션"].astype(str).str.contains(selected_category, na=False)) |
            (self.df["특성"].astype(str).str.contains(selected_category, na=False))
        ]

        if filtered_df.empty:
            await interaction.response.send_message(f"❌ **{selected_category}** 카테고리에 속한 캐릭터 데이터가 없어!", ephemeral=True)
            return

        char_view = discord.ui.View()
        char_view.add_item(CharacterSelect(filtered_df))
        
        await interaction.response.edit_message(
            content=f"📌 **{selected_category}** 카테고리를 선택했어! 세팅을 볼 캐릭터를 골라줘.",
            view=char_view
        )

class CategoryView(discord.ui.View):
    def __init__(self, df):
        super().__init__()
        self.add_item(CategorySelect(df))

# ---------------------------------------------------------
# 5. 봇 및 슬래시 명령어 설정
# ---------------------------------------------------------
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="세팅", description="젠존제 캐릭터 세팅 정보를 카테고리별로 검색해!")
async def setting_slash(interaction: discord.Interaction):
    try:
        df = load_data()
        view = CategoryView(df)
        await interaction.response.send_message("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}", ephemeral=True)

# ---------------------------------------------------------
# 6. 토큰 로드 및 실행
# ---------------------------------------------------------
token = os.getenv("DISCORD_TOKEN")

if not token:
    raise ValueError("⚠️ DISCORD_TOKEN 환경 변수가 설정되지 않았어! Render 대시보드를 확인해줘.")

bot.run(token)
