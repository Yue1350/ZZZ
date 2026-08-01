"""
구글 시트에서 각 탭을 CSV로 내보낸 파일들을 zzz_data.json 하나로 합쳐줍니다.

사용법:
    1. 구글 시트에서 각 탭(예: '캐릭터', '무기', '드라이브디스크')을
       파일 > 다운로드 > 쉼표로 구분된 값(.csv) 으로 각각 내보내기
    2. 파일 이름을 탭 이름으로 저장 (예: 캐릭터.csv, 무기.csv)
    3. 이 파일들을 zzz-bot/csv_input/ 폴더에 넣기
    4. python scripts/csv_to_json.py 실행
    5. data/zzz_data.json 이 자동으로 생성/갱신됨
"""
import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "csv_input")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "zzz_data.json")


def convert():
    if not os.path.isdir(INPUT_DIR):
        print(f"'{INPUT_DIR}' 폴더가 없어요. csv_input 폴더를 만들고 CSV 파일들을 넣어주세요.")
        return

    result = {}
    csv_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".csv")]

    if not csv_files:
        print(f"'{INPUT_DIR}' 폴더에 CSV 파일이 없어요.")
        return

    for filename in csv_files:
        category = os.path.splitext(filename)[0]
        path = os.path.join(INPUT_DIR, filename)

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [
                {k.strip(): v.strip() for k, v in row.items() if k}
                for row in reader
                if any(v.strip() for v in row.values())
            ]

        result[category] = rows
        print(f"  - {category}: {len(rows)}개 항목 변환")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n완료! -> {OUTPUT_PATH}")


if __name__ == "__main__":
    convert()
