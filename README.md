# MoreTale-AI

Gemini API를 사용해 **이중언어 동화(JSON)**를 생성하고, 선택적으로 **페이지 단위 TTS 오디오북(WAV)**, **일러스트 이미지**까지 만드는 프로젝트입니다.

## 핵심 동작

- 동화는 `Story` 스키마로 생성되며 **정확히 24페이지**를 강제합니다.
- 언어 입력은 `--primary_lang`, `--secondary_lang` 2개를 사용합니다.
- `--enable_tts` 활성화 시 같은 출력 폴더에서 오디오를 생성합니다.
- `--enable_illustration` 활성화 시 같은 출력 폴더에서 페이지별 일러스트를 생성합니다.
- TTS 요청 간 기본 간격은 `10.0`초입니다.

## 프로젝트 구조

```text
MoreTale-AI/
├── main.py
├── generators/
│   ├── README.md
│   ├── story/
│   │   ├── story_generator.py
│   │   ├── story_model.py
│   │   └── story_prompts.py
│   ├── tts/
│   │   ├── tts_generator.py
│   │   ├── tts_pipeline.py
│   │   ├── tts_runtime.py
│   │   ├── tts_stream.py
│   │   ├── tts_audio.py
│   │   ├── tts_text.py
│   │   └── tts_manifest.py
│   └── illustration/
│       ├── illustration_generator.py
│       └── illustration_prompt_utils.py
├── prompts/
│   ├── system_instruction.txt
│   ├── user_prompt.txt
│   └── style_guide.txt
├── tests/
│   ├── test_import_compat.py
│   ├── test_main_illustration.py
│   ├── test_story_model.py
│   ├── test_story_prompts.py
│   ├── test_tts_generator.py
│   └── test_main_tts.py
└── requirements.txt
```

`generators/` 내부 상세 역할은 `generators/README.md`를 참고하세요.
브랜치 운영 정책은 `BRANCHING.md`를 참고하세요.

## Import 호환 정책

- canonical 모듈은 `generators/*` 경로입니다.
- `prompts/`는 텍스트 리소스(`*.txt`) 전용 디렉토리입니다.
- 모델 스키마는 `generators.story.story_model` 경로만 지원합니다.

마이그레이션:

```python
# before
from prompts.story_prompts import StoryPrompt
from prompts.illustration_prompt_utils import split_scene_prompt

# after
from generators.story.story_prompts import StoryPrompt
from generators.illustration.illustration_prompt_utils import split_scene_prompt
```

예시:

```python
from generators.story.story_model import Story  # canonical
```

## 빠른 시작

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

프로젝트 루트 `.env`:

```env
GEMINI_STORY_API_KEY=YOUR_STORY_API_KEY
GEMINI_TTS_API_KEY=YOUR_TTS_API_KEY
NANO_BANANA_KEY=YOUR_ILLUSTRATION_API_KEY
```

### 3) 동화 생성

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

출력:

```text
outputs/{timestamp}_story_{slug}/story_{model_name}.json
```

### 4) 동화 + TTS 생성

```bash
python main.py \
  --child_name "Mina" \
  --primary_lang "Korean" \
  --secondary_lang "English" \
  --enable_tts \
  --tts_model "gemini-2.5-flash-preview-tts" \
  --tts_voice "Achernar" \
  --tts_temperature 1.0 \
  --tts_request_interval_sec 10.0
```

TTS 출력(언어 이름은 입력값으로 동적 생성):

```text
outputs/{timestamp}_story_{slug}/audio/01_<primary-lang-slug>/page_01_primary.wav
outputs/{timestamp}_story_{slug}/audio/02_<secondary-lang-slug>/page_01_secondary.wav
outputs/{timestamp}_story_{slug}/audio/manifest.json
```

24페이지 기준 요청 수는 `48`회(페이지당 `primary/secondary` 2회)입니다.

### 5) 동화 + 일러스트 일괄 생성

```bash
python main.py \
  --child_name "Mina" \
  --primary_lang "Korean" \
  --secondary_lang "English" \
  --enable_illustration \
  --illustration_model "gemini-2.5-flash-image" \
  --illustration_aspect_ratio "16:9" \
  --illustration_request_interval_sec 1.0 \
  --illustration_skip_existing
```

`--enable_tts`와 `--enable_illustration`은 함께 사용할 수 있습니다.

### 6) (선택) 기존 동화 JSON으로만 일러스트 생성

```bash
python generators/illustration/illustration_generator.py \
  --story_json outputs/{timestamp}_story_{slug}/story_gemini-2.5-flash.json \
  --skip_existing
```

일러스트 출력:

```text
outputs/{timestamp}_story_{slug}/illustrations/page_01.png
outputs/{timestamp}_story_{slug}/illustrations/manifest.json
```

## CLI 옵션

- `--child_name` (필수): 아이 이름
- `--child_age` (선택): 아이 나이
- `--primary_lang` (필수): 주 언어
- `--secondary_lang` (필수): 보조 언어
- `--theme` (선택): 테마 (생략 시 자동 생성)
- `--extra_prompt` (선택): 추가 요청사항
- `--include_style_guide` (선택): `prompts/style_guide.txt` 포함
- `--model_name` (선택, 기본 `gemini-2.5-flash`): 스토리 모델
- `--enable_tts` (선택): TTS 생성 활성화
- `--tts_model` (선택, 기본 `gemini-2.5-flash-preview-tts`): TTS 모델
- `--tts_voice` (선택, 기본 `Achernar`): TTS voice
- `--tts_temperature` (선택, 기본 `1.0`): TTS temperature
- `--tts_request_interval_sec` (선택, 기본 `10.0`): 요청 간 대기(초)
- `--enable_illustration` (선택): 일러스트 생성 활성화
- `--illustration_model` (선택, 기본 `gemini-2.5-flash-image`): 일러스트 모델
- `--illustration_aspect_ratio` (선택, 기본 `16:9`): 이미지 비율
- `--illustration_request_interval_sec` (선택, 기본 `1.0`): 요청 간 대기(초)
- `--illustration_skip_existing` (선택): 기존 `page_XX.*` 파일이 있으면 스킵

## 출력 JSON 스키마(요약)

- `title_primary`
- `title_secondary`
- `author_name`
- `primary_language`
- `secondary_language`
- `image_style`
- `main_character_design`
- `illustration_prefix` (선택): `{image_style}, {main_character_design}` 형태의 전역 prefix (코드에서 자동 채움)
- `pages` (정확히 24개)
  - `page_number`
  - `text_primary`
  - `text_secondary`
  - `illustration_prompt`
  - `illustration_scene_prompt` (선택): `illustration_prompt`에서 prefix/design를 제거한 페이지별 장면 묘사 (코드에서 자동 채움)

## 테스트

```bash
python -m unittest discover -s tests -v
```

## 트러블슈팅

- `GEMINI_TTS_API_KEY environment variable not set.`
  - `--enable_tts` 사용 시 `.env`에 `GEMINI_TTS_API_KEY` 설정 필요
- `GEMINI_STORY_API_KEY environment variable not set.`
  - 스토리 생성(`generators/story/story_generator.py`) 실행 시 `.env`에 `GEMINI_STORY_API_KEY` 설정 필요
- `NANO_BANANA_KEY environment variable not set.`
  - `--enable_illustration` 또는 `generators/illustration/illustration_generator.py` 실행 시 `.env`에 `NANO_BANANA_KEY` 설정 필요
- `ModuleNotFoundError`
  - 가상환경 활성화 확인
  - `pip install -r requirements.txt` 재실행
