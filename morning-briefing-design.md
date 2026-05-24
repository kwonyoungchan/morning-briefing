# 설계 명세서: 매일 아침 뉴스/날씨 디스코드 알림 시스템

**버전**: 1.1  
**작성일**: 2026-05-24  
**상태**: 구현 완료

---

## 1. 프로젝트 개요

### 1.1 목적
매일 아침 지정된 시간에 사용자 관심사 기반 뉴스와 날씨 정보를 자동으로 수집하여 Discord 채널에 포맷된 메시지로 전송한다.

### 1.2 핵심 요구사항
| 항목 | 내용 |
|------|------|
| 실행 주기 | 매일 1회 (기본: 오전 7시 KST) |
| 알림 채널 | Discord Webhook |
| 뉴스 소스 | NewsAPI.org |
| 날씨 소스 | 기상청 단기예보 API (data.go.kr) |
| 실행 환경 | GitHub Actions (서버리스) |
| 구현 언어 | Python 3.11 |

### 1.3 범위 외 항목
- 사용자 인터랙션(명령어 응답 등) → Discord 봇 기능 불포함
- 뉴스 본문 전체 크롤링 → 제목 + 요약 + 링크만 제공
- 다중 사용자 지원 → 단일 Webhook 대상

---

## 2. 시스템 아키텍처

```
[GitHub Actions Cron]
        │
        ▼
┌───────────────────────────────┐
│        main.py (Orchestrator) │
│                               │
│  ┌──────────┐  ┌───────────┐  │
│  │ news.py  │  │weather.py │  │
│  └────┬─────┘  └─────┬─────┘  │
│       │              │        │
│  ┌────▼──────────────▼─────┐  │
│  │     formatter.py        │  │
│  └────────────┬────────────┘  │
│               │               │
│  ┌────────────▼────────────┐  │
│  │     notifier.py         │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
        │
        ▼
[Discord Webhook → Discord 채널]
```

---

## 3. 디렉토리 구조

```
morning-briefing/
├── .github/
│   └── workflows/
│       └── morning_briefing.yml   # GitHub Actions 워크플로우
├── src/
│   ├── main.py                    # 진입점 및 오케스트레이터
│   ├── news.py                    # 뉴스 수집 모듈
│   ├── weather.py                 # 날씨 수집 모듈
│   ├── formatter.py               # Discord 메시지 포맷 모듈
│   └── notifier.py                # Discord Webhook 전송 모듈
├── config/
│   └── settings.yaml              # 관심사 키워드, 지역 등 설정값
├── requirements.txt
└── README.md
```

---

## 4. 컴포넌트 상세 설계

### 4.1 GitHub Actions Workflow (`morning_briefing.yml`)

**역할**: 스케줄 트리거 및 실행 환경 제공

**트리거 조건**
```
cron: '0 22 * * *'   # UTC 22:00 = KST 07:00
```

**실행 순서**
1. Python 3.11 환경 셋업
2. `requirements.txt` 의존성 설치
3. GitHub Secrets에서 환경 변수 주입
4. `python src/main.py` 실행
5. 실패 시 Actions 로그에 에러 기록

**GitHub Secrets 목록**
| Secret 이름 | 설명 |
|-------------|------|
| `NEWS_API_KEY` | NewsAPI.org API 키 |
| `WEATHER_API_KEY` | 기상청 단기예보 API 키 (data.go.kr) |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL |

---

### 4.2 설정 파일 (`config/settings.yaml`)

**역할**: 코드 변경 없이 관심사/지역 수정 가능하게 분리

```yaml
news:
  keywords:
    - "AI"
    - "개발"
    - "테크"
  language: "ko"
  article_count: 5

weather:
  city: "서울"     # 표시 이름
  nx: 60           # 기상청 격자 X 좌표
  ny: 127          # 기상청 격자 Y 좌표

schedule:
  timezone: "Asia/Seoul"
```

**주요 도시 격자 좌표**
| 도시 | nx | ny |
|------|----|----- |
| 서울 | 60 | 127 |
| 부산 | 98 | 76 |
| 대구 | 89 | 90 |
| 인천 | 55 | 124 |
| 광주 | 58 | 74 |
| 대전 | 67 | 100 |
| 제주 | 52 | 38 |

---

### 4.3 뉴스 수집 모듈 (`news.py`)

**역할**: NewsAPI에서 관심사 기반 기사 목록 가져오기

**사용 API**: `GET https://newsapi.org/v2/everything`

**요청 파라미터**
| 파라미터 | 값 |
|----------|----|  
| `q` | settings.yaml의 keywords 조합 (OR 연산) |
| `language` | settings.yaml의 language |
| `sortBy` | `publishedAt` |
| `pageSize` | settings.yaml의 article_count |
| `from` | 전날 날짜 (오늘 기준 -1일) |

**반환 데이터 구조**
```python
[
    {
        "title": "기사 제목",
        "description": "기사 요약 (최대 100자)",
        "url": "https://...",
        "source": "출처명",
        "published_at": "2026-05-24T07:00:00Z"
    },
    ...
]
```

**에러 처리**
- API 응답 200 외 → 빈 리스트 반환 + 에러 로그
- 네트워크 타임아웃: 10초
- 기사 0건 시: "오늘 관련 뉴스가 없습니다." 대체 텍스트 사용

---

### 4.4 날씨 수집 모듈 (`weather.py`)

**역할**: 기상청 단기예보 API에서 현재 날씨 및 오늘 예보 수집

**사용 API**
- 초단기실황: `GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst`
- 단기예보: `GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst`

**공통 요청 파라미터**
| 파라미터 | 값 |
|----------|----|  
| `serviceKey` | data.go.kr 발급 API 키 (URL 디코딩 적용) |
| `dataType` | `JSON` |
| `nx` | settings.yaml의 격자 X 좌표 |
| `ny` | settings.yaml의 격자 Y 좌표 |
| `base_date` | KST 기준 오늘 날짜 (YYYYMMDD) |
| `base_time` | 가장 최근 발표 시각 (10분 여유 적용) |

**API별 역할 분담**
| API | 수집 항목 |
|-----|----------|
| 초단기실황 (`getUltraSrtNcst`) | T1H(현재기온), REH(습도), PTY(강수형태) |
| 단기예보 (`getVilageFcst`) | TMN(최저기온), TMX(최고기온), POP(강수확률), SKY(하늘상태) |

**단기예보 발표 시각**: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300 (KST)

**반환 데이터 구조**
```python
{
    "city": "서울",
    "condition": "맑음",
    "temp_current": 18,
    "temp_min": 14,
    "temp_max": 23,
    "humidity": 60,
    "rain_probability": 10,
    "emoji": "☀️"
}
```

**날씨 상태 → 이모지 매핑**
| PTY(강수형태) | 상태 | 이모지 |
|---|---|---|
| 1 | 비 | 🌧️ |
| 2 | 비/눈 | 🌨️ |
| 3 | 눈 | ❄️ |
| 4 | 소나기 | 🌦️ |
| 0 + SKY 1 | 맑음 | ☀️ |
| 0 + SKY 3 | 구름많음 | ⛅ |
| 0 + SKY 4 | 흐림 | ☁️ |

**에러 처리**
- 초단기실황 실패 시 `None` 반환 → formatter에서 대체 텍스트 처리
- 단기예보 실패 시 빈 dict 반환 → 현재 기온으로 min/max 대체
- 타임아웃: 10초

---

### 4.5 메시지 포맷 모듈 (`formatter.py`)

**역할**: 수집 데이터를 Discord Embed 형식으로 변환

**Discord Webhook Payload 구조**
```json
{
  "username": "Morning Briefing Bot",
  "embeds": [
    {
      "title": "☀️ 2026년 5월 24일 토요일 모닝 브리핑",
      "color": 16776960,
      "fields": [
        {
          "name": "🌤️ 오늘의 날씨 — 서울",
          "value": "...",
          "inline": false
        },
        {
          "name": "📰 오늘의 뉴스",
          "value": "...",
          "inline": false
        }
      ],
      "footer": {
        "text": "NewsAPI · OpenWeatherMap | 매일 오전 7시 업데이트"
      },
      "timestamp": "2026-05-24T07:00:00Z"
    }
  ]
}
```

**날씨 필드 값 형식**
```
☀️ 맑음  |  현재 18°C  |  최저 14°C / 최고 23°C
💧 습도 60%  |  🌂 강수확률 10%
```

**뉴스 필드 값 형식** (기사당 1줄)
```
1. [기사 제목](링크) — 출처명
2. [기사 제목](링크) — 출처명
...
```

**Embed 색상 규칙**
| 강수확률 | 색상 | 색코드 |
|----------|------|--------|
| 0~30% | 노란색 (맑음) | `16776960` |
| 31~60% | 파란색 (흐림) | `3447003` |
| 61~100% | 회색 (비/눈) | `9807270` |

---

### 4.6 Discord 전송 모듈 (`notifier.py`)

**역할**: 포맷된 payload를 Discord Webhook으로 HTTP POST

**재시도 전략**
- 최대 재시도 횟수: 3회
- 재시도 간격: 5초
- 429 (Rate Limit) 응답 시: `retry_after` 헤더값 대기 후 재시도
- 3회 실패 시: 에러 로그 출력 후 워크플로우 종료 (exit code 1)

---

### 4.7 오케스트레이터 (`main.py`)

**역할**: 전체 흐름 제어 및 에러 총괄

**부분 실패 정책**
- 뉴스 수집 실패 → 날씨만으로 메시지 전송 (계속 진행)
- 날씨 수집 실패 → 뉴스만으로 메시지 전송 (계속 진행)
- Discord 전송 실패 → exit code 1 (Actions 실패로 기록)

---

## 5. 외부 API 명세 요약

| API | 무료 플랜 한도 | 사용 횟수/일 |
|-----|--------------|------------|
| NewsAPI.org | 100건/일 | 1건 |
| 기상청 단기예보 (data.go.kr) | 10,000건/일 | 2건 (초단기실황 + 단기예보) |
| Discord Webhook | 제한 없음 (Rate limit: 30건/분) | 1건 |

---

## 6. 에러 처리 전략 총괄

| 상황 | 처리 방법 |
|------|----------|
| API 키 미설정 | 즉시 종료 + 명확한 에러 메시지 |
| 뉴스 API 실패 | 대체 텍스트로 메시지 전송 |
| 날씨 API 실패 | 대체 텍스트로 메시지 전송 |
| Discord 전송 실패 | 3회 재시도 후 Actions 실패 처리 |
| 기사 0건 | "관련 뉴스 없음" 안내 텍스트 표시 |
| 네트워크 타임아웃 | 10초 후 타임아웃, 대체 처리 |

---

## 7. 메시지 미리보기 (예시)

```
☀️ 2026년 5월 24일 토요일 모닝 브리핑
━━━━━━━━━━━━━━━━━━━━━━━━

🌤️ 오늘의 날씨 — 서울
☀️ 맑음  |  현재 18°C  |  최저 14°C / 최고 23°C
💧 습도 60%  |  🌂 강수확률 10%

📰 오늘의 뉴스
1. [OpenAI, GPT-5 공개 발표](https://...) — TechCrunch
2. [국내 AI 스타트업 투자 현황](https://...) — 매일경제
3. [GitHub Copilot 새 기능 출시](https://...) — GitHub Blog
4. [애플 WWDC 2026 주요 발표](https://...) — The Verge
5. [클라우드 서비스 시장 전망](https://...) — ZDNet Korea

━━━━━━━━━━━━━━━━━━━━━━━━
NewsAPI · 기상청 단기예보 | 매일 오전 7시 업데이트
```

---

## 8. 확장 포인트 (현재 범위 외, 추후 고려)

- **Claude API 연동**: 뉴스 요약 품질 향상
- **다중 키워드 채널 분리**: 키워드별 Discord 채널로 분류 전송
- **주간 요약**: 매주 월요일에 지난주 주요 뉴스 요약 전송
- **사용자 설정 UI**: settings.yaml 대신 웹 인터페이스로 관심사 변경

---

## 9. 초기 형상 GitHub PR

### 9.1 목적

구현 시작 전, 프로젝트 골격(디렉토리 구조 + 플레이스홀더 파일)을 GitHub에 PR로 등록하여 형상관리 기준점을 확보한다.

### 9.2 대상 리포지토리

| 항목 | 값 |
|------|-----|
| GitHub 계정 | `kwonyoungchan` |
| 리포지토리명 | `morning-briefing` |
| 기본 브랜치 | `main` |
| PR 브랜치 | `feat/initial-structure` |

### 9.3 플레이스홀더 작성 규칙

각 `.py` 파일은 함수 시그니처 + docstring + `raise NotImplementedError` 패턴을 따른다.

---

## 10. 구현 우선순위

| 우선순위 | 항목 |
|----------|------|
| P0 | GitHub Actions Workflow 기본 구조 |
| P0 | weather.py + notifier.py (핵심 기능) |
| P1 | news.py + formatter.py |
| P1 | 에러 처리 및 부분 실패 대응 |
| P2 | settings.yaml 설정 분리 |
| P2 | Embed 색상 동적 변경 |
