# 🎮 젠존제 캐릭터 세팅 가이드 봇 (ZZZ Setting Guide Bot)

Discord.js v14 기반으로 동작하는 **젠레스 존 제로(Zenless Zone Zero)** 캐릭터 세팅 정보 안내 디스코드 봇입니다.  
구글 시트(Google Sheets) 데이터를 기반으로 최신 세팅 정보를 가져오며, 인터랙티브 드롭다운 메뉴 및 슬래시 명령어를 통해 간편하게 가이드를 조회할 수 있습니다.

---

## 📌 주요 기능

- **📊 구글 시트 연동 및 자동 캐싱**:
  - 구글 시트 CSV 데이터를 실시간으로 파싱하여 최신 캐릭터 세팅 가이드를 제공합니다.
  - 5분 간격의 데이터 캐싱(Cache)을 통해 불필요한 네트워크 요청을 줄이고 속도를 최적화했습니다.
- **🎮 상세 캐릭터 세팅 가이드**:
  - 진영, 특성, 포지션, 추천 W-엔진, 디스크(4세트/2세트/주옵션), 유효 부옵션, 스킬 레벨, 핵심 돌파, 치명타 정보, 기타 팁 제공.
  - `char_images.json` 파일과 연동하여 캐릭터 썸네일 이미지를 출력합니다.
- **🎛️ 인터랙티브 드롭다운 메뉴**:
  - 캐릭터 이름을 직접 검색하지 않아도 전체, 진영별, 특성별, 포지션별 카테고리 메뉴를 통해 쉽게 탐색할 수 있습니다.

---

## 🛠️ 기술 스택

- **Runtime**: Node.js
- **Framework & Libraries**:
  - `discord.js` v14
  - `axios` (구글 시트 HTTP 요청)
  - `papaparse` (CSV 파싱)
  - `http` & `fs` & `path`

---

## 📂 프로젝트 구조

```text
.
├── data/
│   └── char_images.json      # 캐릭터별 썸네일 이미지 URL 매핑 파일
├── index.js                  # 봇 메인 로직 (Keep-Alive 서버, 구글 시트 파싱, 슬래시 명령어, 드롭다운 이벤트)
├── package.json              # 프로젝트 의존성 라이브러리 목록
└── README.md                 # 프로젝트 설명 문서

---

# 출처
https://zzz.akademiya.app/en/characters
https://docs.google.com/spreadsheets/d/1C3ZpKCTQJXFwUBgZKZRdLOvGqDGlVijb/htmlview#gid=2007866856
