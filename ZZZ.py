import discord
from discord.ext import commands
from discord import app_commands
import pandas as pd
import io
import urllib.request
import json
import os

# ---------------------------------------------------------
# 봇 기본 설정
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 접근 권한

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 캐릭터 이미지 JSON 로드 함수
# ---------------------------------------------------------
def load_char_images():
    if os.path.exists("char_images.json"):
        try:
            with open("char_images.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON 로드 중 오류 발생: {e}")
    return {}

# ---------------------------------------------------------
# 1. 온라인 구글 시트 데이터 로드 함수 (A열 기준 캐릭명 감지)
# ---------------------------------------------------------
def load_data():
    sheet_id = "1C3ZpKCTQJXFwUBgZKZRdLOvGqDGlVijb"
    gid = "2007866856"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    try:
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read()
            
        raw_df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", header=None)
    except Exception as e:
        print(f"구글 시트 로드 중 오류 발생: {e}")
        return pd.DataFrame()

    # 1~5행(인덱스 0~4) 제거하고 6행(인덱스 5)부터 데이터로 사용
    data_df = raw_df.iloc[5:].reset_index(drop=True)

    column_names = [
        "캐릭명",       # A (0)
        "진영",         # B (1)
        "특성",         # C (2)
        "스킬레벨",     # D (3)
        "포지션",       # E (4)
        "W-엔진",       # F (5)
        "4세트",        # G (6)
        "2세트",        # H (7)
        "disc_4",       # I (8)
        "disc_5",       # J (9)
        "disc_6",       # K (10)
        "유효부옵션",   # L (11)
        "핵심돌파",     # M (12)
        "주옵",         # N (13)
        "치명타",       # O (14)
        "기타"          # P (15)
    ]
    
    data_df = data_df.iloc[:, :len(column_names)]
    data_df.columns = column_names

    # A열(인덱스 0)에서만 캐릭명이 존재하는 행 번호 추출
    char_indices = []
    for idx, val in enumerate(data_df.iloc[:, 0]):  # A열만 순회
        if pd.notna(val) and str(val).strip() not in ["", "nan", "None", "-"]:
            char_indices.append(idx)

    processed_rows = []
    
    # A열에서 찾은 캐릭명 시작 행을 기준으로 캐릭터 단위 분할
    for i, start_idx in enumerate(char_indices):
        end_idx = char_indices[i+1] if i + 1 < len(char_indices) else start_idx + 4
        chunk = data_df.iloc[start_idx:end_idx].copy()
        
        # A열 첫 번째 값으로 캐릭명 지정
        char_name = str(chunk.iloc[0, 0]).strip()

        row_data = {}
        for col in column_names:
            valid_vals = chunk[col].dropna().astype(str).str.strip()
            valid_vals = [v for v in valid_vals if v not in ["", "nan", "None", "-"]]
            
            if col in ["disc_4", "disc_5", "disc_6"]:
                row_data[col] = valid_vals[0] if valid_vals else "-"
            elif col in ["W-엔진", "기타", "유효부옵션"]:
                row_data[col] = "\n".join(valid_vals) if valid_vals else "-"
            else:
                row_data[col] = valid_vals[0] if valid_vals else "-"

        # 디스크 4/5/6번 주옵션 하나로 합치기
        mains = [row_data["disc_4"], row_data["disc_5"], row_data["disc_6"]]
        mains = [m for m in mains if m != "-"]
        row_data["통합디스크주옵션"] = " / ".join(mains) if mains else "-"
        
        row_data["캐릭명"] = char_name
        processed_rows.append(row_data)

    final_df = pd.DataFrame(processed_rows)
    return final_df

# ---------------------------------------------------------
# 2. 임베드 생성 함수
# ---------------------------------------------------------
def create_setting_embed(row):
    char_name = str(row["캐릭명"]).strip()
    
    # JSON 파일에서 이미지 URL 불러오기
    char_images = load_char_images()
    image_url = char_images.get(char_name, None)

    embed = discord.Embed(
        title=f"🎮 {char_name} 세팅 가이드",
        color=0x00ff00
    )

    # JSON에 이미지가 등록되어 있다면 임베드 썸네일로 추가
    if image_url:
        embed.set_thumbnail(url=image_url)

    embed.add_field(name="🏛️ 진영", value=row["진영"], inline=True)
    embed.add_field(name="⚡ 특성", value=row["특성"], inline=True)
    embed.add_field(name="🎯 포지션", value=row["포지션"], inline=True)

    embed.add_field(name="🗡️ W-엔진", value=row["W-엔진"], inline=False)
    embed.add_field(name="🔮 4세트", value=row["4세트"], inline=True)
    embed.add_field(name="💎 2세트", value=row["2세트"], inline=True)

    embed.add_field(name="📊 디스크 4 / 5 / 6번 주옵션", value=row["통합디스크주옵션"], inline=False)
    embed.add_field(name="✨ 유효 부옵션", value=row["유효부옵션"], inline=True)
    embed.add_field(name="💥 스킬 레벨", value=row["스킬레벨"], inline=True)

    embed.add_field(name="🚀 핵심 돌파", value=row["핵심돌파"], inline=True)
    embed.add_field(name="⚙️ 주요 옵션", value=row["주옵"], inline=True)
    embed.add_field(name="🎯 치명타 정보", value=row["치명타"], inline=True)

    if row["기타"] != "-":
        embed.add_field(name="📌 기타 팁", value=row["기타"], inline=False)

    embed.set_footer(text="젠존제 세팅 정보 봇")
    return char_name, embed

# ---------------------------------------------------------
# 3. 카테고리 드롭다운 UI 클래스
# ---------------------------------------------------------
class CategorySelect(discord.ui.Select):
    def __init__(self, df):
        self.df = df
        options = [
            discord.SelectOption(label="전체 보기", description="모든 캐릭터 보기", value="전체"),
            discord.SelectOption(label="진영별 보기", description="진영으로 캐릭터 찾아보기", value="진영"),
            discord.SelectOption(label="특성별 보기", description="속성/특성으로 캐릭터 찾아보기", value="특성"),
            discord.SelectOption(label="포지션별 보기", description="포지션(역할군)으로 캐릭터 찾아보기", value="포지션")
        ]
        super().__init__(placeholder="카테고리를 선택해 줘!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        
        if selected == "전체":
            char_list = self.df["캐릭명"].tolist()
            text_list = ", ".join(char_list)
            embed = discord.Embed(title="📜 전체 캐릭터 목록", description=text_list, color=0x3498db)
            await interaction.response.edit_message(content="검색 가능한 캐릭터 목록이야!", embed=embed, view=None)
            
        elif selected in ["진영", "특성", "포지션"]:
            view = SubCategoryView(self.df, selected)
            await interaction.response.edit_message(content=f"원하는 **{selected}**을(를) 선택해 줘!", view=view)

class SubCategorySelect(discord.ui.Select):
    def __init__(self, df, category_type):
        self.df = df
        self.category_type = category_type
        
        unique_values = df[category_type].dropna().unique()
        options = []
        for val in unique_values:
            val_str = str(val).strip()
            if val_str and val_str != "-":
                options.append(discord.SelectOption(label=val_str, value=val_str))

        super().__init__(placeholder=f"{category_type} 선택...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        selected_val = self.values[0]
        matched_df = self.df[self.df[self.category_type] == selected_val]
        
        view = CharacterSelectView(matched_df)
        await interaction.response.edit_message(content=f"**[{selected_val}]** 카테고리의 캐릭터를 선택해 줘!", view=view)

class CharacterSelect(discord.ui.Select):
    def __init__(self, matched_df):
        self.matched_df = matched_df
        options = []
        for _, row in matched_df.iterrows():
            c_name = str(row["캐릭명"]).strip()
            options.append(discord.SelectOption(label=c_name, value=c_name))

        super().__init__(placeholder="캐릭터를 선택해 줘!", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        selected_char = self.values[0]
        row = self.matched_df[self.matched_df["캐릭명"] == selected_char].iloc[0]
        
        c_name, embed = create_setting_embed(row)
        await interaction.response.edit_message(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed, view=None)

class CategoryView(discord.ui.View):
    def __init__(self, df):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(df))

class SubCategoryView(discord.ui.View):
    def __init__(self, df, category_type):
        super().__init__(timeout=60)
        self.add_item(SubCategorySelect(df, category_type))

class CharacterSelectView(discord.ui.View):
    def __init__(self, matched_df):
        super().__init__(timeout=60)
        self.add_item(CharacterSelect(matched_df))

# ---------------------------------------------------------
# 4. 디스코드 이벤트 및 명령어
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"🤖 봇 로그인 성공: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ 동기화된 슬래시 명령어: {len(synced)}개")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 실패: {e}")

# 슬래시 명령어 (/세팅 [캐릭터])
@bot.tree.command(name="세팅", description="젠존제 캐릭터 세팅 정보를 검색해!")
@app_commands.describe(캐릭터="검색할 캐릭터 이름을 입력해줘 (선택 사항)")
async def setting_slash(interaction: discord.Interaction, 캐릭터: str = None):
    try:
        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            
            # 예외 처리 1: '배연우'
            if search_name == "배연우":
                await interaction.response.send_message(f"{interaction.user.mention} 너 배연우")
                return

            # 예외 처리 2: '베리나'
            if search_name == "베리나":
                images = load_char_images()
                img_url = images.get("베리나", "https://i.namu.wiki/i/eACVAos4WR6IB2Y1AlVn8qXnKlzxYWTsR6AULHvS9w-bbhphy1X4_iszgM8zdCRhSA0zfvvZpqNRIluNxNauxw.webp")
                await interaction.response.send_message(f"{interaction.user.mention} 너 미래 남편\n{img_url}")
                return

            df = load_data()
            matched = df[df["캐릭명"].astype(str).str.replace(" ", "").str.lower().str.contains(search_name, na=False)]

            if matched.empty:
                await interaction.response.send_message(f"❌ **{캐릭터}** 캐릭터 정보를 찾을 수 없어!", ephemeral=True)
                return

            row = matched.iloc[0]
            c_name, embed = create_setting_embed(row)
            await interaction.response.send_message(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)
        else:
            df = load_data()
            view = CategoryView(df)
            await interaction.response.send_message("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}", ephemeral=True)

# 일반 명령어 (!세팅 [캐릭터])
@bot.command(name="세팅")
async def setting_prefix(ctx, *, 캐릭터: str = None):
    try:
        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            
            # 예외 처리 1: '배연우'
            if search_name == "배연우":
                await ctx.send(f"{ctx.author.mention} 너 배연우")
                return

            # 예외 처리 2: '베리나'
            if search_name == "베리나":
                images = load_char_images()
                img_url = images.get("베리나", "https://i.namu.wiki/i/eACVAos4WR6IB2Y1AlVn8qXnKlzxYWTsR6AULHvS9w-bbhphy1X4_iszgM8zdCRhSA0zfvvZpqNRIluNxNauxw.webp")
                await ctx.send(f"{ctx.author.mention} 너 미래 남편\n{img_url}")
                return

            df = load_data()
            matched = df[df["캐릭명"].astype(str).str.replace(" ", "").str.lower().str.contains(search_name, na=False)]

            if matched.empty:
                await ctx.send(f"❌ **{캐릭터}** 캐릭터 정보를 찾을 수 없어!")
                return

            row = matched.iloc[0]
            c_name, embed = create_setting_embed(row)
            await ctx.send(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)
        else:
            df = load_data()
            view = CategoryView(df)
            await ctx.send("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view)

    except Exception as e:
        await ctx.send(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}")

# ---------------------------------------------------------
# 봇 실행 (Render 환경 변수에서 토큰 로드)
# ---------------------------------------------------------
TOKEN = os.environ.get("DISCORD_TOKEN")

bot.run(TOKEN)
