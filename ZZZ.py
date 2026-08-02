import os
import urllib.parse
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
# 1. zzz_data.csv 전용 데이터 로드 함수
# ---------------------------------------------------------
def load_data():
    csv_file = "zzz_data.csv"
    
    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig", header=1)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", header=1)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding="cp949", header=1)

    # 헤더명 공백 및 줄바꿈 정리
    df.columns = [str(col).replace("\n", "").replace(" ", "").strip() for col in df.columns]

    # 3행 1세트 데이터 묶어주기
    if "캐릭명" in df.columns:
        df["캐릭명"] = df["캐릭명"].bfill()

    if "진영" in df.columns:
        df["진영"] = df["진영"].bfill().ffill()

    fill_targets = ["특성", "포지션", "W-엔진", "4세트", "2세트", "디스크주옵션", "유효부옵션", "핵심돌파", "주옵", "치명타", "기타"]
    for target in fill_targets:
        if target in df.columns:
            df[target] = df[target].ffill()

    skill_col = [c for c in df.columns if "스킬" in c]
    if skill_col:
        df.rename(columns={skill_col[0]: "스킬레벨"}, inplace=True)

    # 디스크 4, 5, 6번 주옵션 통합
    unnamed_cols = [c for c in df.columns if "Unnamed" in c]
    for idx, row in df.iterrows():
        mains = []
        if pd.notna(row.get("디스크주옵션")):
            mains.append(str(row["디스크주옵션"]).replace("\n", " ").strip())
        for u_col in unnamed_cols:
            if pd.notna(row.get(u_col)):
                mains.append(str(row[u_col]).replace("\n", " ").strip())
        df.at[idx, "통합디스크주옵션"] = " / ".join(mains) if mains else "-"

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    return df

# ---------------------------------------------------------
# 2. 임베드 생성 함수 (썸네일 URL 안전 처리 및 세로 박스 배치)
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

    # 💡 썸네일 URL 인코딩 및 예외 처리
    try:
        clean_char = c_name.replace("S.", "").strip()
        encoded_char = urllib.parse.quote(clean_char)
        img_url = f"https://act-webstatic.hoyoverse.com/game_record/zzz/role_square_avatar/{encoded_char}.png"
        embed.set_thumbnail(url=img_url)
    except Exception:
        pass

    # 위에서 아래로 단일 열 세로 배치 & 값 전체 코드 블록(```) 처리
    embed.add_field(name="🏛️ 진영", value=f"```{faction}```", inline=False)
    embed.add_field(name="⚡ 특성", value=f"```{trait}```", inline=False)
    embed.add_field(name="🎯 포지션", value=f"```{position}```", inline=False)
    embed.add_field(name="🗡️ W-엔진", value=f"```{w_engine}```", inline=False)
    embed.add_field(name="💿 4세트", value=f"```{set_4}```", inline=False)
    embed.add_field(name="💿 2세트", value=f"```{set_2}```", inline=False)
    embed.add_field(name="📊 디스크 주옵션", value=f"```{disc_main_text}```", inline=False)
    embed.add_field(name="🔍 유효 부옵션", value=f"```{sub_stats}```", inline=False)
    embed.add_field(name="🔓 핵심 돌파", value=f"```{breakthrough}```", inline=False)
    embed.add_field(name="📈 주옵 (목표 스탯)", value=f"```{main_stat}```", inline=False)
    embed.add_field(name="💥 치명타", value=f"```{crit_stat}```", inline=False)

    if etc != "-":
        embed.add_field(name="📝 기타 / 계산법", value=f"```{etc}
