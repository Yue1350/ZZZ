# 🎮 젠존제 세팅 정보 디스코드 봇 (ZZS Bot)

> **젠레스 존 제로(Zenless Zone Zero)** 에이전트들의 세팅 정보, 디스크 옵션, W-엔진 추천을
> 구글 시트 기반으로 실시간 제공하는 디스코드 봇입니다.

---

## ✨ 주요 기능

* **📊 구글 시트 연동**: 항상 최신 데이터로 업데이트되는 캐릭터 세팅 정보 파싱
* **🔍 슬래시 명령어 (`/세팅`)**: 
  * 캐릭터명을 직접 검색하여 빠르게 세팅 가이드 출력
  * 카테고리(진영, 특성, 포지션)별 드롭다운 탐색 가능
* **📜 전체 목록 조회 (`/목록`)**: 등록된 전체 캐릭터 리스트를 한눈에 확인
* **🖼️ 캐릭터 이미지 매핑**: `data/char_images.json` 파일 기반 임베드 썸네일 지원
  
---

## 🛠️ 기술 스택

| 분류 | 기술 스택 |
| --- | --- |
| **Language** | Node.js (v18+) |
| **Library** | `discord.js` v14, `@discordjs/voice` |
| **Data Processing** | `axios`, `papaparse` |
| **Server** | Node.js Built-in `http` Module |

---

## 📁 프로젝트 구조

```text
├── index.js                  # 메인 로직 및 디스코드 클라이언트 설정
├── package.json              # 의존성 패키지 관리
├── readme.md                 # 프로젝트 설명 및 사용법 문서
└── data/
    └── char_images.json      # 캐릭터별 이미지 URL 매핑 파일
