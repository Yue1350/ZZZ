"""
'이잘키' 형식 젠존제 세팅 시트(캐릭터당 3행: 진영/이름/세팅데이터) 전용 변환 스크립트.

일반적인 한 행 = 한 항목 구조가 아니라, 아래처럼 3행이 한 세트인 특수 포맷입니다:
    행1: [       , 진영, ...]
    행2: [이름   ,     , ...]
    행3: [       ,     , 특성, 스킬레벨, 포지션, W-엔진, 4세트, 2세트,
                        디스크4주옵, 디스크5주옵, 디스크6주옵,
                        유효부옵션, 핵심돌파, 주옵, 치명타, 기타]

사용법:
    python scripts/convert_setting_sheet.py <원본CSV경로>
    (결과: data/zzz_data.json 의 "캐릭터" 항목으로 저장/갱신됨)
"""
import csv
import json
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "zzz_data.json")

DATA_FIELD_NAMES = [
    "특성", "스킬 레벨(평,회,지,특,궁)", "포지션", "W-엔진", "4세트", "2세트",
    "디스크4 주옵션", "디스크5 주옵션", "디스크6 주옵션",
    "유효 부옵션", "핵심 돌파", "주옵", "치명타", "기타",
]
DATA_COLS = list(range(2, 16))  # csv 열 2~15


def clean(v: str) -> str:
    return (v or "").strip()


def parse_data_row(row) -> dict:
    d = {}
    for name, col in zip(DATA_FIELD_NAMES, DATA_COLS):
        val = clean(row[col]) if col < len(row) else ""
        if val:
            d[name] = val
    return d


def convert(csv_path: str):
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    characters = []

    # 헤더(행0=제목, 행1=컬럼헤더) 다음부터 시작
    i = 2

    # 행2는 이름/진영 없이 데이터만 있는 예시/설명 행인 경우가 많아 별도 처리
    if i < len(rows) and clean(rows[i][2]):
        example = parse_data_row(rows[i])
        if example:
            example["이름"] = "(예시 설명행)"
            example["진영"] = ""
            example["메모"] = "시트 최상단의 예시/설명용 행입니다. 실제 캐릭터가 아닙니다."
            characters.append(example)
        i += 1

    # 이후 3행(진영, 이름, 데이터) 단위로 반복
    while i < len(rows):
        faction_row = rows[i]
        faction = clean(faction_row[1]).replace("\n", " ") if len(faction_row) > 1 else ""

        name = ""
        if i + 1 < len(rows):
            name = clean(rows[i + 1][0])

        data = {}
        if i + 2 < len(rows):
            data = parse_data_row(rows[i + 2])

        if name:
            entry = {"이름": name, "진영": faction}
            entry.update(data)
            if not data:
                entry["메모"] = "세팅 데이터가 아직 시트에 채워지지 않은 캐릭터입니다."
            characters.append(entry)

        i += 3

    result = {"캐릭터": characters}

    # 기존 zzz_data.json이 있으면 다른 분류는 보존하고 '캐릭터'만 교체
    if os.path.exists(OUTPUT_PATH):
        try:
            with open(OUTPUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}

    existing["캐릭터"] = characters

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"캐릭터 {len(characters)}개 변환 완료 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python scripts/convert_setting_sheet.py <원본CSV경로>")
        sys.exit(1)
    convert(sys.argv[1])
