import os
import urllib.parse
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import pandas as pd
from keep_alive import keep_alive

# 환경 변수 및 서브 서버 유지
load_dotenv()
keep_alive()

# ---------------------------------------------------------
# 1. zzz_data.csv 전용 데이터 로드 함수 (3행 1세트 완전 매칭)
# ---------------------------------------------------------
def load_data():
    csv_file = "zzz_data.csv"
    
    # 인코딩 예외 처리 (utf-8-sig -> utf-8 -> cp949)
    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig", header=1)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", header=1)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding="cp949", header=1)

    # 1) 헤더명 공백 및 줄바꿈 정리
    df.columns = [str(col).replace("\n", "").replace(" ", "").strip() for col in df.columns]

    # 2) 3행으로 나뉜 데이터 묶어주기
    # 캐릭명은 3번째 행(아래)에 위치하므로 아래에서 위로 채우기 (bfill)
    if "캐릭명" in df.columns:
        df["캐릭명"] = df["캐릭명"].bfill()

    # 진영은 2번째 행(가운데)에 위치
    if "진영" in df.columns:
        df["진영"] = df["진영"].bfill().ffill()

    # 상단 1번째 행에 있는 특성, 포지션, 스킬 레벨 등 세팅 정보 위에서 아래로 채우기 (ffill)
    fill_targets = ["특성", "포지션", "W-엔진", "4세트", "2세트", "디스크주옵션", "유효부옵션", "핵심돌파", "주옵", "치명타", "기타"]
    for target in fill_targets:
        if target in df.columns:
            df[target] = df[target].ffill()

    # 3) '스킬 레벨' 컬럼명 매칭 정규화
    skill_col = [c for c in df.columns if "스킬" in c]
    if skill_col:
        df.rename(columns={skill_col[0]: "스킬레벨"}, inplace=True)

    # 4) 디스크 주옵션 3개 컬럼(4/5/6번) 병합 처리
    # Unnamed: 9, Unnamed: 10 컬럼에 있는 5번, 6번 주옵션 합치기
    unnamed_cols = [c for c in df.columns if "Unnamed" in c]
    for idx, row in df.iterrows():
        mains = []
        if pd.notna(row.get("디스크주옵션")):
            mains.append(str(row["디스크주옵션"]).replace("\n", " ").strip())
        for u_col in unnamed_cols:
            if pd.notna(row.get(u_col)):
                mains.append(str(row[u_col]).replace("\n", " ").strip())
        df.at[idx, "통합디스크주옵션"] = " / ".join(mains) if mains else "-"

    # 진영, 포지션, W-엔진 등 내부 줄바꿈(\n)을 띄어쓰기 또는 줄바꿈으로 깔끔하게 포맷팅
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    return df

# ---------------------------------------------------------
# 2. 임베드 생성 함수 (잘림 방지 뷰)
# ---------------------------------------------------------
def create_setting_embed(row):
    def get_val(col_name):
        val = row.get(col_name)
        if pd.isna(val) or str(val).strip() in ["", "nan", "None", "-"]:
            return "-"
        return str(val).strip()

    c_name = get_val("캐릭명")
    faction = get_val("진영").replace("\n", " ")
    trait = get_val("특성")
    skill_lvl = get_val("스킬레벨")
    position = get_val("포지션").replace("\n", " ")
    w_engine = get_val("W-엔진")
    set_4 = get_val("4세트")
    set_2 = get_val("2세트")
    disc_main_text = get_val("통합디스크주옵션")
    sub_stats = get_val("유효부옵션")
    breakthrough = get_val("핵심돌파")
    main_stat = get_val("주옵")
    crit_stat = get_val("치명타")
    etc = get_val("기타")

    embed = discord.Embed(
        title=f"🎮 {c_name} 세팅 가이드",
        color=0x00FF7F
    )

    clean_char = c_name.replace("S.", "").strip()
    embed.set_thumbnail(url=f"https://act-webstatic.hoyoverse.com/game_record/zzz/role_square_avatar/{clean_char}.png")

    # 기본 속성
    embed.add_field(name="🏛️ 진영", value=faction, inline=True)
    embed.add_field(name="⚡ 특성", value=trait, inline=True)
    embed.add_field(name="🎯 포지션", value=position, inline=True)

    # 추천 장비
    embed.add_field(name="🗡️ 추천 W-엔진", value=f"```{w_engine}```", inline=False)
    embed.add_field(name="💿 추천 디스크 세트", value=f"```4세트: {set_4}\n2세트:\n{set_2}```", inline=False)

    # 디스크 옵션
    embed.add_field(name="📊 디스크 주옵션 (4/5/6번)", value=f"```{disc_main_text}```", inline=True)
    embed.add_field(name="🔍 유효 부옵션", value=f"```{sub_stats}```", inline=True)

    # 목표 스탯 및 돌파
    embed.add_field(name="🔓 핵심 돌파", value=f"```{breakthrough}```", inline=True)
    embed.add_field(name="📈 목표 주옵", value=f"```{main_stat}```", inline=True)
    embed.add_field(name="💥 치명타 스탯", value=f"```{crit_stat}```", inline=True)

    # 참고 및 기타 계산법
    if etc != "-":
        embed.add_field(name="📝 기타 / 계산법", value=f"```{etc}```", inline=False)

    if skill_lvl != "-":
        embed.set_footer(text=f"스킬 레벨 우선순위: {skill_lvl}")

    return c_name, embed

# ---------------------------------------------------------
# 3. 드롭다운 뷰 클래스
# ---------------------------------------------------------
class CharacterSelect(discord.ui.Select):
    def __init__(self, characters_df):
        options = []
        unique_chars = characters_df.drop_duplicates(subset=["캐릭명"])
        for _, row in unique_chars.iterrows():
            c_name = str(row["캐릭명"]).strip()
            faction = str(row["진영"]).replace("\n", " ").strip() if pd.notna(row["진영"]) else ""
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
            options=options[:25]
        )
        self.characters_df = characters_df

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_char = self.values[0]
        row = self.characters_df[self.characters_df["캐릭명"] == selected_char].iloc[0]

        c_name, embed = create_setting_embed(row)
        await interaction.followup.send(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)

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
# 4. 봇 및 명령어 설정
# ---------------------------------------------------------
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# 슬래시 명령어 (/세팅 [캐릭터])
@bot.tree.command(name="세팅", description="젠존제 캐릭터 세팅 정보를 검색해!")
@app_commands.describe(캐릭터="검색할 캐릭터 이름을 입력해줘 (선택 사항)")
async def setting_slash(interaction: discord.Interaction, 캐릭터: str = None):
    try:
        df = load_data()

        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            matched = df[df["캐릭명"].astype(str).str.replace(" ", "").str.lower().str.contains(search_name, na=False)]

            if matched.empty:
                await interaction.response.send_message(f"❌ **{캐릭터}** 캐릭터 정보를 찾을 수 없어!", ephemeral=True)
                return

            row = matched.iloc[0]
            c_name, embed = create_setting_embed(row)
            await interaction.response.send_message(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)
        else:
            view = CategoryView(df)
            await interaction.response.send_message("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}", ephemeral=True)

# 일반 명령어 (!세팅 [캐릭터])
@bot.command(name="세팅")
async def setting_prefix(ctx, *, 캐릭터: str = None):
    try:
        df = load_data()

        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            matched = df[df["캐릭명"].astype(str).str.replace(" ", "").str.lower().str.contains(search_name, na=False)]

            if matched.empty:
                await ctx.send(f"❌ **{캐릭터}** 캐릭터 정보를 찾을 수 없어!")
                return

            row = matched.iloc[0]
            c_name, embed = create_setting_embed(row)
            await ctx.send(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)
        else:
            view = CategoryView(df)
            await ctx.send("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view)

    except Exception as e:
        await ctx.send(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}")

# ---------------------------------------------------------
# 5. 토큰 로드 및 실행
# ---------------------------------------------------------
token = os.getenv("DISCORD_TOKEN")

if not token:
    raise ValueError("⚠️ DISCORD_TOKEN 환경 변수가 설정되지 않았어!")

bot.run(token)
