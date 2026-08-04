import os, io, json, ssl, urllib.request, discord, pandas as pd
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive

keep_alive()

# ---------------------------------------------------------
# 봇 기본 설정
# ---------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------
# 캐릭터 이미지 JSON 로드 함수
# ---------------------------------------------------------
def load_char_images():
    if os.path.exists("char_images.json"):
        try:
            with open("char_images.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return {str(k).strip(): str(v).strip() for k, v in data.items()}
        except Exception as e:
            print(f"JSON 로드 중 오류 발생: {e}")
    return {}

# ---------------------------------------------------------
# 1. 온라인 구글 시트 데이터 로드 함수 (4행 1세트 전용 로직)
# ---------------------------------------------------------
def load_data():
    sheet_id = "1C3ZpKCTQJXFwUBgZKZRdLOvGqDGlVijb"
    gid = "2007866856"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    column_names = [
        "캐릭명", "진영", "특성", "스킬레벨", "포지션", "W-엔진", "4세트", "2세트",
        "disc_4", "disc_5", "disc_6", "유효부옵션", "핵심돌파", "주옵", "치명타", "기타"
    ]

    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            csv_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, context=context) as response:
            content = response.read()
            
        raw_df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", header=None)
        print(f"📊 [디버그] CSV 전체 행 수: {len(raw_df)}")
    except Exception as e:
        print(f"❌ 구글 시트 로드 중 오류 발생: {e}")
        return pd.DataFrame(columns=column_names + ["통합디스크주옵션"])

    raw_df = raw_df.iloc[:, :len(column_names)]
    raw_df.columns = column_names

    processed_rows = []
    total_rows = len(raw_df)

    # 1. 실제 데이터가 시작하는 첫 번째 행 인덱스 자동 탐색
    start_row = 0
    for idx in range(total_rows):
        val = str(raw_df.iloc[idx, 0]).strip()
        # 헤더 명칭이 아니고 내용이 있는 첫 행 찾기
        if val and val not in ["nan", "None", "-", "NaN", "캐릭명", "캐릭터", "이름"]:
            start_row = idx
            print(f"📍 [디버그] 데이터 시작 행 탐색 성공: 인덱스 {start_row} (캐릭터명: {val})")
            break

    # 2. 찾은 시작점부터 4행씩 처리
    for start_idx in range(start_row, total_rows, 4):
        chunk = raw_df.iloc[start_idx : start_idx + 4].copy()
        if chunk.empty:
            continue

        first_val = chunk.iloc[0, 0]
        if pd.isna(first_val):
            continue
            
        char_name = str(first_val).strip()
        if not char_name or char_name in ["캐릭명", "캐릭터", "nan", "None", "-", "이름"]:
            continue

        row_data = {}
        for col in column_names:
            valid_vals = chunk[col].dropna().astype(str).str.strip()
            valid_vals = [v for v in valid_vals if v not in ["", "nan", "None", "-", "NaN"]]
            
            if col in ["disc_4", "disc_5", "disc_6"]:
                row_data[col] = valid_vals[0] if valid_vals else "-"
            elif col in ["W-엔진", "기타", "유효부옵션"]:
                row_data[col] = "\n".join(valid_vals) if valid_vals else "-"
            else:
                row_data[col] = valid_vals[0] if valid_vals else "-"

        mains = [row_data["disc_4"], row_data["disc_5"], row_data["disc_6"]]
        mains = [m for m in mains if m != "-"]
        row_data["통합디스크주옵션"] = " / ".join(mains) if mains else "-"
        
        row_data["캐릭명"] = char_name
        processed_rows.append(row_data)

    if not processed_rows:
        print("⚠️ [디버그] 데이터 처리 결과가 비어있습니다.")
        return pd.DataFrame(columns=column_names + ["통합디스크주옵션"])

    final_df = pd.DataFrame(processed_rows)
    print(f"✅ [디버그] 파싱 완료된 캐릭터 수: {len(final_df)}명")
    return final_df
    
# ---------------------------------------------------------
# 2. 임베드 생성 함수
# ---------------------------------------------------------
def create_setting_embed(row):
    char_name = str(row["캐릭명"]).strip()
    
    char_images = load_char_images()
    image_url = char_images.get(char_name, None)

    embed = discord.Embed(
        title=f"🎮 {char_name} 세팅 가이드",
        color=0x00ff00
    )

    if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
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
            if "캐릭명" in self.df.columns and not self.df.empty:
                char_list = sorted(self.df["캐릭명"].tolist())
                text_list = ", ".join(char_list)
            else:
                text_list = "등록된 캐릭터가 없어!"
                
            embed = discord.Embed(title="📜 전체 캐릭터 목록", description=text_list, color=0x3498db)
            await interaction.response.edit_message(content="검색 가능한 전체 캐릭터 목록이야!", embed=embed, view=None)
            
        elif selected in ["진영", "특성", "포지션"]:
            view = SubCategoryView(self.df, selected)
            await interaction.response.edit_message(content=f"원하는 **{selected}**을(를) 선택해 줘!", view=view)

class SubCategorySelect(discord.ui.Select):
    def __init__(self, df, category_type):
        self.df = df
        self.category_type = category_type
        
        unique_values = df[category_type].dropna().unique() if category_type in df.columns else []
        options = []
        for val in unique_values:
            val_str = str(val).strip()
            if val_str and val_str != "-":
                options.append(discord.SelectOption(label=val_str, value=val_str))

        if not options:
            options.append(discord.SelectOption(label="데이터 없음", value="none"))

        super().__init__(placeholder=f"{category_type} 선택...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        selected_val = self.values[0]
        if selected_val == "none":
            await interaction.response.send_message("해당 카테고리에 데이터가 없어!", ephemeral=True)
            return

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
    
    # 봇 상태 메세지 설정
    await bot.change_presence(activity=discord.Game(name="에이전트 관리 중"))
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ 동기화된 슬래시 명령어: {len(synced)}개")
    except Exception as e:
        print(f"❌ 슬래시 명령어 동기화 실패: {e}")

# 슬래시 명령어 (/목록)
@bot.tree.command(name="목록", description="세팅 정보가 등록된 전체 캐릭터 목록을 확인해!")
async def list_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    df = load_data()
    
    if df.empty or "캐릭명" not in df.columns:
        await interaction.followup.send("❌ 등록된 캐릭터 데이터를 불러올 수 없어!")
        return

    char_list = sorted(df["캐릭명"].unique().tolist())
    text_list = "\n".join([f"• {name}" for name in char_list])

    embed = discord.Embed(
        title="📜 등록된 캐릭터 목록",
        description=text_list,
        color=0x3498db
    )
    embed.set_footer(text=f"총 {len(char_list)}명의 캐릭터가 등록되어 있어!")
    await interaction.followup.send(embed=embed)

# 일반 명령어 (!목록)
@bot.command(name="목록")
async def list_prefix(ctx):
    df = load_data()
    
    if df.empty or "캐릭명" not in df.columns:
        await ctx.send("❌ 등록된 캐릭터 데이터를 불러올 수 없어!")
        return

    char_list = sorted(df["캐릭명"].unique().tolist())
    text_list = "\n".join([f"• {name}" for name in char_list])

    embed = discord.Embed(
        title="📜 등록된 캐릭터 목록",
        description=text_list,
        color=0x3498db
    )
    embed.set_footer(text=f"총 {len(char_list)}명의 캐릭터가 등록되어 있어!")
    await ctx.send(embed=embed)

# 슬래시 명령어 (/세팅 [캐릭터])
@bot.tree.command(name="세팅", description="젠존제 캐릭터 세팅 정보를 검색해!")
@app_commands.describe(캐릭터="검색할 캐릭터 이름을 입력해줘 (선택 사항)")
async def setting_slash(interaction: discord.Interaction, 캐릭터: str = None):
    await interaction.response.defer(ephemeral=(캐릭터 is None))
    
    try:
        df = load_data()
        
        if df.empty or "캐릭명" not in df.columns:
            await interaction.followup.send("❌ 캐릭터 데이터를 로드하지 못했어!", ephemeral=True)
            return

        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            
            if search_name == "배연우":
                await interaction.followup.send(f"{interaction.user.mention} 너 배연우")
                return

            if search_name == "베리나":
                images = load_char_images()
                img_url = images.get("베리나", "https://i.namu.wiki/i/eACVAos4WR6IB2Y1AlVn8qXnKlzxYWTsR6AULHvS9w-bbhphy1X4_iszgM8zdCRhSA0zfvvZpqNRIluNxNauxw.webp")
                await interaction.followup.send(f"{interaction.user.mention} 너 미래 남편\n{img_url}")
                return

            matched = df[df["캐릭명"].astype(str).str.replace(" ", "").str.lower().str.contains(search_name, na=False)]

            if matched.empty:
                await interaction.followup.send(f"❌ **{캐릭터}** 캐릭터 정보를 찾을 수 없어!", ephemeral=True)
                return

            row = matched.iloc[0]
            c_name, embed = create_setting_embed(row)
            await interaction.followup.send(content=f"**{c_name}** 세팅 정보를 가져왔어!", embed=embed)
        else:
            view = CategoryView(df)
            await interaction.followup.send("원하는 카테고리를 아래 드롭다운에서 골라줘!", view=view, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"⚠️ 데이터를 불러오는 중 오류가 발생했어: {e}", ephemeral=True)

# 일반 명령어 (!세팅 [캐릭터])
@bot.command(name="세팅")
async def setting_prefix(ctx, *, 캐릭터: str = None):
    try:
        df = load_data()
        
        if df.empty or "캐릭명" not in df.columns:
            await ctx.send("❌ 캐릭터 데이터를 로드하지 못했어!")
            return

        if 캐릭터:
            search_name = 캐릭터.replace(" ", "").lower()
            
            if search_name == "배연우":
                await ctx.send(f"{ctx.author.mention} 너 배연우")
                return

            if search_name == "베리나":
                images = load_char_images()
                img_url = images.get("베리나", "https://i.namu.wiki/i/eACVAos4WR6IB2Y1AlVn8qXnKlzxYWTsR6AULHvS9w-bbhphy1X4_iszgM8zdCRhSA0zfvvZpqNRIluNxNauxw.webp")
                await ctx.send(f"{ctx.author.mention} 너 미래 남편\n{img_url}")
                return

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
# 봇 실행
# ---------------------------------------------------------
TOKEN = os.environ.get("DISCORD_TOKEN")

bot.run(TOKEN)
