# MoreTale-AI

Gemini API를 사용해 **이중언어 동화(JSON)**를 생성하는 프로젝트입니다.  
아동 이름, 주 언어/보조 언어(그리고 선택적으로 테마)를 입력하면 24페이지 구조의 동화를 생성해 `outputs/`에 저장합니다.  
옵션으로 페이지 단위 이중언어 TTS 오디오북(WAV)도 생성할 수 있습니다.

## 구현된 기능

- Gemini 모델 기반 동화 생성 (`google-genai`)
- Gemini TTS 기반 오디오북 생성 (`google-genai`)
  - `--enable_tts` 활성화 시 페이지별 1/2 언어 분리 WAV 생성
  - 요청 간 고정 대기(`--tts_request_interval_sec`, 기본 10초)로 RPM 제한 대응
- 이중언어 페이지 구조 생성
  - `text_primary` / `text_secondary`
  - 페이지별 `illustration_prompt`, `sound_effects`
- 스키마 기반 검증 (`pydantic`)
  - 동화는 **정확히 24페이지**여야 함
- 프롬프트 로더
  - `prompts/system_instruction.txt`
  - `prompts/user_prompt.txt`
  - (선택) `prompts/style_guide.txt` (`--include_style_guide`)
  - 템플릿 placeholder 오류 감지
- 단위 테스트
  - 모델 검증 테스트
  - 프롬프트 로딩/포맷 테스트

## 프로젝트 구조

```text
MoreTale-AI/
├── main.py
├── generators/
│   └── story_generator.py
├── models/
│   └── story_model.py
├── prompts/
│   ├── story_prompts.py
│   ├── system_instruction.txt
│   ├── user_prompt.txt
│   ├── style_guide.txt
│   └── legacy/
├── tests/
│   ├── test_story_model.py
│   └── test_story_prompts.py
└── requirements.txt
```

## 빠른 시작 (팀원용)

### 1) 가상환경 활성화

이미 프로젝트 내 가상환경(`.moretale`)이 준비된 기준:

```bash
source .moretale/bin/activate
```

새로 만드는 경우:

```bash
python3 -m venv .moretale
source .moretale/bin/activate
pip install -r requirements.txt
```

### 2) 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들고 Gemini API 키를 설정합니다.

```env
GEMINI_STORY_API_KEY=YOUR_STORY_API_KEY
GEMINI_TTS_API_KEY=YOUR_TTS_API_KEY
```

### 3) 동화 생성 실행

```bash
python main.py \
  --child_name "Mina" \
  --child_age 5 \
  --primary_lang "Korean" \
  --secondary_lang "English" \
  --theme "Friendship" \
  --extra_prompt "Include a dragon" \
  --include_style_guide \
  --model_name "gemini-2.5-flash"
```

생성 결과는 아래 경로에 저장됩니다.

```text
outputs/{timestamp}_story_{slug}/story_{model_name}.json
```

### 4) 동화 + 오디오북(TTS) 함께 생성

```bash
python main.py \
  --child_name "Mina" \
  --primary_lang "Korean" \
  --secondary_lang "English" \
  --model_name "gemini-2.5-flash" \
  --enable_tts \
  --tts_model "gemini-2.5-flash-preview-tts" \
  --tts_voice "Achernar" \
  --tts_temperature 1.0 \
  --tts_request_interval_sec 10.0
```

TTS 출력은 아래처럼 생성됩니다.

```text
outputs/{timestamp}_story_{slug}/audio/01_korean/page_01_primary.wav
outputs/{timestamp}_story_{slug}/audio/02_english/page_01_secondary.wav
outputs/{timestamp}_story_{slug}/audio/manifest.json
```

24페이지 기준 요청 수는 총 48회(페이지당 2회: primary/secondary)입니다.
스토리 JSON과 TTS 결과는 항상 같은 `output_dir` 아래에 저장됩니다.

## CLI 옵션

- `--child_name` (필수): 아이 이름
- `--child_age` (선택): 아이 나이(권장)
- `--primary_lang` (필수): 주 언어
- `--secondary_lang` (필수): 보조 언어
- `--theme` (선택): 동화 테마 (생략 시 자동 생성)
- `--extra_prompt` (선택): 추가 요청사항
- `--include_style_guide` (선택): `prompts/style_guide.txt`를 system instruction에 포함
- `--model_name` (선택, 기본값 `gemini-2.5-flash`): 사용할 Gemini 모델
- `--enable_tts` (선택): 생성된 동화를 페이지 단위 TTS WAV로 변환
- `--tts_model` (선택, 기본값 `gemini-2.5-flash-preview-tts`): TTS 모델
- `--tts_voice` (선택, 기본값 `Achernar`): TTS 음성
- `--tts_temperature` (선택, 기본값 `1.0`): TTS temperature
- `--tts_request_interval_sec` (선택, 기본값 `10.0`): TTS 요청 간 대기 시간(초)

## 출력 JSON 개요

`Story` 스키마를 따릅니다.

- `title_primary`
- `title_secondary`
- `author_name`
- `image_style`
- `main_character_design`
- `primary_language`
- `secondary_language`
- `pages` (정확히 24개)
  - `page_number`
  - `text_primary`
  - `text_secondary`
  - `illustration_prompt`
  - `sound_effects`

## 테스트

가상환경 활성화 후 실행:

```bash
python -m unittest discover -s tests -v
```

## 트러블슈팅

- `GEMINI_API_KEY environment variable not set.`
  - `.env` 파일에 `GEMINI_STORY_API_KEY`가 있는지 확인
  - 실행 셸이 프로젝트 루트인지 확인
- `GEMINI_TTS_API_KEY environment variable not set.`
  - `--enable_tts` 사용 시 `.env` 파일에 `GEMINI_TTS_API_KEY` 설정
  - 실행 셸이 프로젝트 루트인지 확인
- `ModuleNotFoundError`
  - 가상환경 활성화 여부 확인
  - `pip install -r requirements.txt` 재실행
