# MoreTale-AI Server

MoreTale-AI의 FastAPI 마이크로서비스입니다.  
동화 생성 요청을 받아 비동기 작업으로 처리하고, 결과(JSON/TTS/일러스트)를 URL 기반으로 제공합니다.

CLI 사용 가이드는 `cli/README.md`를 참고하세요.

## 서버 범위

- `POST /api/stories/`: 스토리 생성 작업 시작 (`202`)
- `GET /api/stories/{story_id}`: 작업 상태 조회
- `GET /api/stories/{story_id}/result`: 결과 조회
- `GET /healthz`: 헬스체크
- `/static/outputs/...`: 로컬 산출물 정적 서빙

## 현재 구현 상태

- Phase 1: 서버 스캐폴딩, 비동기 job, 상태/결과 API
- Phase 2: TTS/일러스트 옵션 처리, 부분 실패 표현
- Phase 3-Lite: 운영 하드닝
  - `X-Request-ID` 응답 헤더
  - 인메모리 레이트리밋 (`POST /api/stories/`, API key 단위)
  - 모델/언어 allowlist 검증
  - 입력 길이 제한

## 프로젝트 구조

```text
app/
  main.py
  api/
    stories.py
  core/
    auth.py
    config.py
  schemas/
    story.py
  services/
    story_service.py
    tts_service.py
    illustration_service.py
    storage.py
    job_store.py
    rate_limiter.py
    request_context.py
```

## 빠른 시작 (서버)

### 1) 가상환경

```bash
source .moretale/bin/activate
```

없다면:

```bash
python3 -m venv .moretale
source .moretale/bin/activate
pip install -r requirements.txt
```

### 2) 환경변수

```env
# 인증 (콤마로 다중 키 지원)
MORETALE_API_KEY=key-a,key-b

# 선택: outputs 경로
# MORETALE_OUTPUTS_DIR=/absolute/path/to/outputs

# 생성기 키
GEMINI_STORY_API_KEY=YOUR_STORY_API_KEY
GEMINI_TTS_API_KEY=YOUR_TTS_API_KEY
NANO_BANANA_KEY=YOUR_ILLUSTRATION_API_KEY

# Phase 3-Lite 하드닝
MORETALE_RATE_LIMIT_POST_STORIES_PER_MIN=5
MORETALE_THEME_MAX_LEN=120
MORETALE_EXTRA_PROMPT_MAX_LEN=500
MORETALE_CHILD_NAME_MAX_LEN=40
MORETALE_ALLOWED_STORY_MODELS=gemini-2.5-flash
MORETALE_ALLOWED_TTS_MODELS=gemini-2.5-flash-preview-tts
MORETALE_ALLOWED_ILLUSTRATION_MODELS=gemini-2.5-flash-image
MORETALE_ALLOWED_LANGUAGES=Korean,English,Japanese,Chinese,Spanish,French,German
```

### 3) 실행

```bash
uvicorn app.main:app --reload
```

## API 예시

### 생성

```bash
curl -X POST http://127.0.0.1:8000/api/stories/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: key-a" \
  -d '{
    "child_name": "Mina",
    "child_age": 5,
    "primary_lang": "Korean",
    "secondary_lang": "English",
    "theme": "Friendship",
    "extra_prompt": "Include a dragon",
    "include_style_guide": true,
    "generation": {
      "story_model": "gemini-2.5-flash",
      "enable_tts": true,
      "enable_illustration": true
    }
  }'
```

### 상태 조회

```bash
curl -H "X-API-Key: key-a" \
  http://127.0.0.1:8000/api/stories/{story_id}
```

### 결과 조회

```bash
curl -H "X-API-Key: key-a" \
  http://127.0.0.1:8000/api/stories/{story_id}/result
```

## 응답/운영 규약

- 표준 에러 포맷:

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "human readable message",
    "detail": {}
  }
}
```

- 공통 응답 헤더:
  - `X-Request-ID`

- 주요 상태 코드:
  - `202`: 비동기 생성 시작
  - `200`: 조회 성공
  - `401`: API key 인증 실패
  - `409`: 결과 준비 전 상태 (`STORY_NOT_READY`)
  - `422`: 입력 검증 실패 (`VALIDATION_ERROR`)
  - `429`: 레이트리밋 초과 (`RATE_LIMIT_EXCEEDED`)

## 테스트

```bash
python -m unittest tests.test_fastapi_phase1 -v
python -m unittest tests.test_fastapi_phase2 -v
python -m unittest tests.test_fastapi_phase3_hardening -v
```

전체 테스트:

```bash
python -m unittest discover -s tests -v
```

## 문서 링크

- CLI 사용 가이드: `cli/README.md`
- 생성기 모듈 구조: `generators/README.md`
- FastAPI 구현 계획서: `docs/fastapi-ai-server-impl-plan.md`
