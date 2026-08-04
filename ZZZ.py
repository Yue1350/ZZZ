import io
import json
import os
import urllib.parse
import urllib.request
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import pandas as pd
from keep_alive import keep_alive

# 환경 변수 및 서버 유지
load_dotenv()
keep_alive()

# ---------------------------------------------------------
# 📸 외부 JSON 파일에서 캐릭터 이미지 사전 불러오기
# ---------------------------------------------------------
CHARACTER_IMAGES = {}
try:
    with open("character_images.json", "r", encoding="utf-8") as f:
        CHARACTER_IMAGES = json.load(f)
except FileNotFoundError:
    print("⚠️ character_images.json 파일을 찾을 수 없어 기본 이미지를 사용합니다.")
except Exception as e:
    print(f"⚠️ JSON 파일 로드 실패: {e}")

# ---------------------------------------------------------
# 1. 온라인 구글 시트 데이터 로드 함수 (3행 1세트 데이터 및 빈 칸 보정)
# ---------------------------------------------------------
def load_data():
    sheet_id = "1C3ZpKCTQJXFwUBgZKZRdLOvGqDGlVijb"
    gid = "2007866856"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read()
            
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", header=1)
    except Exception as e:
        print(f"구글 시트 로드 중 오류 발생: {e}")
        return pd.DataFrame()

    # 컬럼명 공백 및 줄바꿈 제거
    df.columns = [str(col).replace("\n", "").replace(" ", "").strip() for col in df.columns]

    # 캐릭명/진영 채우기 (빈 행을 위 캐릭터 이름으로 채움)
    if "캐릭명" in df.columns:
        df["캐릭명"] = df["캐릭명"].ffill()

    if "진영" in df.columns:
        df["진영"] = df["진영"].ffill()

    # 다른 캐릭터의 값이 빈 칸으로 넘어가 채워지는 현상을 방지하기 위해 
    # 캐릭터별 그룹(groupby)을 지정하여 ffill을 수행
    fill_targets = ["특성", "포지션", "W-엔진", "4세트", "2세트", "디스크주옵션", "유효부옵션", "핵심돌파", "주옵", "치명타", "기타"]
    for target in fill_targets:
        if target in df.columns:
            df[target] = df.groupby("캐릭명")[target].ffill()

    skill_col = [c for c in df.columns if "스킬" in c]
    if skill_col:
        df.rename(columns={skill_col[0]: "스킬레벨"}, inplace=True)

    # 디스크 4, 5, 6번 주옵션 통합
    unnamed_cols = [c for c in df.columns if "Unnamed" in c]
    for idx, row in df.iterrows():
        mains = []
        if pd.notna(row.get("디스크주옵션")) and str(row.get("디스크주옵션")).strip() not in ["", "nan", "None"]:
            mains.append(str(row["디스크주옵션"]).replace("\n", " ").strip())
        for u_col in unnamed_cols:
            if pd.notna(row.get(u_col)) and str(row.get(u_col)).strip() not in ["", "nan", "None"]:
                mains.append(str(row[u_col]).replace("\n", " ").strip())
        df.at[idx, "통합디스크주옵션"] = " / ".join(mains) if mains else "-"

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    return df

# ---------------------------------------------------------
# 2. 임베드 생성 함수 (커스텀 이미지 적용)
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
    skill_lvl = get_val("스킬레벨")

    embed = discord.Embed(
        title=f"🎮 {c_name} 세팅 가이드",
        color=0x2B2D31
    )

    # CHARACTER_IMAGES에 직접 지정한 이미지 URL이 있으면 우측 상단 썸네일로 사용
    if c_name in CHARACTER_IMAGES:
        embed.set_thumbnail(url=CHARACTER_IMAGES[c_name])
    else:
        try:
            clean_char = c_name.replace("S.", "").strip()
            encoded_char = urllib.parse.quote(clean_char)
            img_url = f"https://act-webstatic.hoyoverse.com/game_record/zzz/role_square_avatar/{encoded_char}.png"
            embed.set_thumbnail(url=img_url)
        except Exception:
            pass

    # [1] 기본 정보
    embed.add_field(name="🏛️ 진영", value=f"```{faction}```", inline=True)
    embed.add_field(name="⚡ 특성", value=f"```{trait}```", inline=True)
    embed.add_field(name="🎯 포지션", value=f"```{position}```", inline=True)

    # [2] 스킬 및 장비
    embed.add_field(name="🔝 스킬 레벨 우선순위 (평,회,지,특,궁)", value=f"```{skill_lvl}```", inline=False)
    embed.add_field(name="🗡️ W-엔진", value=f"```{w_engine}```", inline=False)
    
    # [3] 디스크 세트
    embed.add_field(name="💿 4세트", value=f"```{set_4}```", inline=True)
    embed.add_field(name="💿 2세트", value=f"```{set_2}```", inline=True)

    # [4] 디스크 옵션
    embed.add_field(name="📊 디스크 주옵션 (4/5/6번)", value=f"```{disc_main_text}```", inline=False)
    embed.add_field(name="🔍 유효 부옵션", value=f"```{sub_stats}```", inline=False)

    # [5] 스탯 및 돌파 정보
    embed.add_field(name="🔓 핵심 돌파", value=f"```{breakthrough}```", inline=True)
    embed.add_field(name="📈 주옵 스탯", value=f"```{main_stat}```", inline=True)
    embed.add_field(name="💥 치명타", value=f"```{crit_stat}```", inline=True)

    # [6] 기타 / 계산법
    if etc != "-":
        embed.add_field(name="📝 기타 / 계산법", value=f"```{etc}```", inline=False)

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
# 4. 봇 및 슬래시/일반 명령어 설정
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
# 5. 토큰 로드 및 봇 실행
# ---------------------------------------------------------
token = os.getenv("DISCORD_TOKEN")

if not token:
    raise ValueError("⚠️ DISCORD_TOKEN 환경 변수가 설정되지 않았어!")

bot.run(token)
