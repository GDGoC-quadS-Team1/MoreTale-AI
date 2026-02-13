# Generators 구조 안내

`generators/`는 도메인별 하위 디렉토리로 구성됩니다.

## 디렉토리 구성

- `story/`
  - `story_generator.py`: Gemini 텍스트 모델을 호출해 동화 JSON(`Story`)를 생성합니다.
  - `story_model.py`: `Story`, `Page` Pydantic 모델의 canonical 정의입니다.
  - `story_prompts.py`: 스토리 프롬프트 로더/템플릿 처리(`StoryPrompt`)입니다.
    - 텍스트 리소스는 루트 `prompts/*.txt`를 읽습니다.

- `tts/`
  - `tts_generator.py`: TTS 오케스트레이션 진입점(`TTSGenerator`)
  - `tts_pipeline.py`: 페이지/언어 반복 처리와 상태 집계
  - `tts_runtime.py`: rate limit + retry(backoff)
  - `tts_stream.py`: 스트리밍 응답에서 오디오 바이트 수집
  - `tts_audio.py`: MIME 파싱 및 WAV 변환
  - `tts_text.py`: TTS 프롬프트/언어 슬러그 유틸
  - `tts_manifest.py`: `audio/manifest.json` 저장

- `illustration/`
  - `illustration_generator.py`: 동화 JSON(`illustration_prompt` + `illustration_scene_prompt`)를 사용해 페이지별 이미지를 생성합니다.
  - `illustration_prompt_utils.py`: 일러스트 prefix/scene 분리 유틸의 canonical 정의입니다.
    - 기본 API 키: `.env`의 `NANO_BANANA_KEY`
    - 출력: `illustrations/page_XX.*`, `illustrations/manifest.json`

## Import 호환성

- 내부 구현의 canonical import는 `generators/*`를 사용합니다.
- 하위 호환을 위해 `prompts/story_prompts.py`,
  `prompts/illustration_prompt_utils.py`는 re-export shim으로 유지됩니다.
- 모델 스키마는 `generators.story.story_model` 경로만 지원합니다.

## 호출 흐름 (TTS)

1. `main.py`가 `TTSGenerator.generate_book_audio(...)` 호출
2. `generators/tts/tts_generator.py`가 설정/의존성 준비
3. `generators/tts/tts_pipeline.py`가 페이지와 언어를 순회
4. 요청 단위로 `tts_runtime.py`, `tts_stream.py`, `tts_audio.py`를 조합
5. 완료 후 `tts_manifest.py`가 매니페스트 저장

## 유지보수 가이드

- 오디오 포맷 확장은 `generators/tts/tts_audio.py`를 먼저 수정합니다.
- 재시도/요청 간격 정책은 `generators/tts/tts_runtime.py`에서 처리합니다.
- 결과 경로/집계 포맷 변경은 `generators/tts/tts_pipeline.py`와 `generators/tts/tts_manifest.py`를 함께 수정합니다.
