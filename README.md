# 젠존제(ZZZ) 디스코드 봇

시트 데이터 조회 + 트위터/유튜브 새 글·영상 알림 기능이 있는 디스코드 봇입니다.

## 폴더 구조

```
zzz-bot/
├── bot.py                 # 실행 파일
├── config.py               # 환경변수 로딩
├── database.py              # SQLite DB 관리
├── requirements.txt
├── .env.example             # 이걸 복사해서 .env 로 만들고 값 채우기
├── cogs/
│   ├── zzz_data.py          # /데이터, /데이터목록, /데이터검색
│   └── notifications.py      # /알림채널, /트위터알림, /유튜브알림
├── utils/
│   ├── twitter_checker.py
│   └── youtube_checker.py
├── data/
│   └── zzz_data.json        # 시트 데이터 (지금은 예시만 들어있음, 교체 필요!)
└── scripts/
    └── csv_to_json.py        # CSV → zzz_data.json 변환 스크립트
```

## 1. 설치

```bash
cd zzz-bot
python -m venv venv
source venv/bin/activate      # Windows는 venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. 디스코드 봇 만들기

1. https://discord.com/developers/applications 접속 → **New Application**
2. 왼쪽 메뉴 **Bot** → **Reset Token**으로 토큰 발급 → `.env`의 `DISCORD_TOKEN`에 붙여넣기
3. 같은 Bot 페이지에서 **Privileged Gateway Intents**는 기본값(꺼짐)으로 둬도 됩니다 (메시지 내용 읽기 기능은 안 씀)
4. 왼쪽 메뉴 **OAuth2 → URL Generator**
   - SCOPES: `bot`, `applications.commands`
   - BOT PERMISSIONS: `Send Messages`, `Embed Links`, `Use Slash Commands`
   - 생성된 URL로 봇을 원하는 서버에 초대
5. (선택) 테스트용으로 명령어를 즉시 반영하고 싶으면, 서버에서 우클릭 → ID 복사(개발자 모드 필요) 해서 `.env`의 `GUILD_ID`에 입력. 비워두면 전역 등록되며 반영까지 최대 1시간 걸릴 수 있어요.

## 3. 실행

```bash
python bot.py
```

## 4. 시트 데이터 채워넣기 (중요!)

`data/zzz_data.json`에는 지금 예시 데이터만 들어있어요. 실제 구글 시트 내용으로 바꾸는 방법:

1. 구글 시트 각 탭을 **파일 → 다운로드 → 쉼표로 구분된 값(.csv)**로 내보내기
2. 파일명을 탭 이름으로 저장 (예: `캐릭터.csv`, `무기.csv`, `드라이브디스크.csv`)
3. `zzz-bot/csv_input/` 폴더를 만들고 그 안에 CSV들을 넣기
4. 실행:
   ```bash
   python scripts/csv_to_json.py
   ```
5. `data/zzz_data.json`이 자동으로 생성됩니다. 봇이 켜져 있다면 디스코드에서 `/데이터새로고침` 명령어로 바로 반영 가능해요.

CSV의 첫 번째 열 이름은 `이름`으로 해주면 항목 이름으로 자동 인식됩니다 (없으면 첫 번째 컬럼을 이름으로 사용).

## 5. 명령어 목록

**시트 데이터**
- `/데이터목록` — 등록된 분류와 개수 확인
- `/데이터 분류:캐릭터 이름:○○` — 특정 항목 상세 조회 (자동완성 지원)
- `/데이터검색 키워드:○○` — 모든 분류에서 키워드로 검색
- `/데이터새로고침` — (관리자) json 파일 다시 불러오기

**알림 설정**
- `/알림채널 설정 종류:트위터|유튜브|둘다` — 현재 채널을 알림 채널로 지정 (관리자 전용)

**트위터 알림**
- `/트위터알림 추가 아이디:○○`
- `/트위터알림 삭제 아이디:○○`
- `/트위터알림 목록`

**유튜브 알림**
- `/유튜브알림 추가 채널:URL 또는 @핸들`
- `/유튜브알림 삭제 채널id:UCxxxx`
- `/유튜브알림 목록`

봇은 기본적으로 5분(`CHECK_INTERVAL_SECONDS`, `.env`에서 조절 가능)마다 새 트윗/영상을 확인합니다.

## 6. 트위터 알림 관련 중요 주의사항 ⚠️

이 봇은 X(트위터) 공식 API를 쓰지 않고, **Nitter(트위터 미러 서비스)의 RSS 피드**로 새 트윗을 감지합니다. API 키가 필요 없다는 장점이 있지만 대신:

- Nitter 공개 인스턴스들은 X 측의 차단으로 **수시로 다운되거나 막힙니다.** 그래서 이 봇은 `.env`의 `NITTER_INSTANCES`에 등록된 인스턴스를 순서대로 시도하고, 실패한 인스턴스는 자동으로 뒤로 밀려서 다음 확인부터는 우선순위가 낮아지도록 되어 있어요.
- 그래도 **등록된 인스턴스가 전부 죽어있으면 그 주기의 알림은 못 받습니다.** 이런 경우 `.env`의 `NITTER_INSTANCES`를 최신 살아있는 인스턴스로 바꿔주세요.
  - 살아있는 인스턴스 확인: https://status.d420.de/
- 계정이 비공개 계정이거나, Nitter 인스턴스가 특정 계정을 차단한 경우 해당 계정만 감지가 안 될 수 있어요.
- 100% 안정적인 방식은 아니라서, 정말 중요한 알림(예: 공식 계정 긴급 공지)은 사람이 직접 확인하는 것도 병행하는 걸 추천해요.

**직접 Nitter 인스턴스를 운영하는 방법도 있어요** (더 안정적이지만 별도 서버 필요). 필요하면 Docker로 셀프 호스팅하는 방법도 안내해드릴 수 있어요.

## 7. 유튜브 알림은 API 키 없이 동작합니다

유튜브 채널의 공개 RSS 피드(`https://www.youtube.com/feeds/videos.xml?channel_id=...`)를 사용하므로 별도 API 키 없이도 새 영상 알림이 동작합니다. `YOUTUBE_API_KEY`는 선택 사항입니다.

## 8. 봇을 24시간 켜두고 싶다면

로컬 PC를 계속 켜두거나, Raspberry Pi / 개인 서버 / VPS에서 `nohup python bot.py &` 또는 `systemd`, `pm2`, `tmux` 등으로 백그라운드 실행하는 걸 추천해요. (무료 클라우드 호스팅은 다음에 필요하시면 도와드릴게요.)
