# Generators 구조 안내

`generators/`는 스토리 생성과 TTS 생성 로직을 담당합니다.

## 파일별 역할

- `story_generator.py`
  - Gemini 텍스트 모델을 호출해 동화 JSON(`Story`)를 생성합니다.
  - 입력 언어(`primary_lang`, `secondary_lang`)와 프롬프트를 조합해 모델 요청을 구성합니다.

- `tts_generator.py`
  - TTS 오케스트레이션 진입점입니다.
  - 외부(`main.py`)에서 직접 사용하는 클래스는 `TTSGenerator`입니다.
  - 페이지 루프/요청 실행은 하위 `tts_*` 모듈을 조합해 수행합니다.

- `tts_pipeline.py`
  - 페이지 단위 TTS 생성 파이프라인(반복 처리)을 담당합니다.
  - 스킵/성공/실패 상태 집계와 결과 딕셔너리 생성을 수행합니다.

- `tts_runtime.py`
  - 요청 간격 제어(rate limit)와 재시도(backoff) 로직을 담당합니다.

- `tts_stream.py`
  - Gemini TTS 스트리밍 응답에서 오디오 바이트를 모아 반환합니다.
  - 스트림 내 MIME 타입 일관성 검증을 수행합니다.

- `tts_audio.py`
  - 오디오 MIME 파싱 및 WAV 변환 유틸리티를 제공합니다.
  - PCM(raw) 오디오를 WAV 헤더와 결합해 저장 가능한 형태로 만듭니다.

- `tts_text.py`
  - TTS 프롬프트 문구 생성, 언어명 슬러그 생성 유틸리티를 제공합니다.

- `tts_manifest.py`
  - `audio/manifest.json` 엔트리 생성 및 파일 저장을 담당합니다.

## 호출 흐름

1. `main.py`가 `TTSGenerator.generate_book_audio(...)`를 호출
2. `tts_generator.py`가 설정/의존성을 준비
3. `tts_pipeline.py`가 페이지와 언어(Primary/Secondary)를 순회
4. 각 요청에서:
   - `tts_runtime.py`: 요청 간격/재시도 제어
   - `tts_stream.py`: 스트림 오디오 수집
   - `tts_audio.py`: WAV 저장용 바이트 변환
5. 완료 후 `tts_manifest.py`가 매니페스트 저장

## 유지보수 가이드

- 새로운 오디오 포맷 지원이 필요하면 `tts_audio.py`를 우선 수정합니다.
- 재시도 정책/요청 간격 변경은 `tts_runtime.py`에서 처리합니다.
- 파일 경로/상태 집계 형식 변경은 `tts_pipeline.py`와 `tts_manifest.py`를 함께 수정합니다.
- 외부 인터페이스(`TTSGenerator`)를 유지하면 `main.py` 수정 없이 내부 구조를 바꿀 수 있습니다.
