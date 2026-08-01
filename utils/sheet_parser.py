"""
'이잘키' 형식 젠존제 세팅 시트(캐릭터당 3행: 진영/이름/세팅데이터) CSV를
바로 파싱해서 dict 리스트로 돌려주는 공용 모듈.

시트 구조:
    행0: 제목
    행1: 컬럼 헤더
    행2: (있을 수도 있음) 이름/진영 없이 데이터만 있는 예시 설명행
    이후 3행 반복: [진영행, 이름행, 세팅데이터행]
"""
import csv
import os

DATA_FIELD_NAMES = [
    "특성", "스킬 레벨(평,회,지,특,궁)", "포지션", "W-엔진", "4세트", "2세트",
    "디스크4 주옵션", "디스크5 주옵션", "디스크6 주옵션",
    "유효 부옵션", "핵심 돌파", "주옵", "치명타", "기타",
]
DATA_COLS = list(range(2, 16))  # csv 열 2~15


def _clean(v: str) -> str:
    return (v or "").strip()


def _parse_data_row(row) -> dict:
    d = {}
    for name, col in zip(DATA_FIELD_NAMES, DATA_COLS):
        val = _clean(row[col]) if col < len(row) else ""
        if val:
            d[name] = val
    return d


def parse_setting_csv(csv_path: str) -> list[dict]:
    """CSV 경로를 받아 캐릭터 dict 리스트를 반환. 파일이 없으면 빈 리스트."""
    if not os.path.exists(csv_path):
        return []

    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if len(rows) < 3:
        return []

    characters = []
    i = 2

    # 행2가 이름/진영 없이 데이터만 있으면 예시 설명행으로 처리
    if i < len(rows) and len(rows[i]) > 2 and _clean(rows[i][2]):
        example = _parse_data_row(rows[i])
        if example:
            example["이름"] = "(예시 설명행)"
            example["진영"] = ""
            example["메모"] = "시트 최상단의 예시/설명용 행입니다. 실제 캐릭터가 아닙니다."
            characters.append(example)
        i += 1

    while i < len(rows):
        faction_row = rows[i]
        faction = _clean(faction_row[1]).replace("\n", " ") if len(faction_row) > 1 else ""

        name = ""
        if i + 1 < len(rows):
            name = _clean(rows[i + 1][0])

        data = {}
        if i + 2 < len(rows):
            data = _parse_data_row(rows[i + 2])

        if name:
            entry = {"이름": name, "진영": faction}
            entry.update(data)
            if not data:
                entry["메모"] = "세팅 데이터가 아직 시트에 채워지지 않은 캐릭터입니다."
            characters.append(entry)

        i += 3

    return characters
