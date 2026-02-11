# Branching Strategy

This repository uses one integrated branch and `feat/*` work branches.

## Branch Types

- `main`
  - Integrated baseline (story + tts).
  - Release and deployment reference.

- `feat/story-core`
  - Story-focused long-lived workstream (optional).
  - Preferred scope:
    - `generators/story_generator.py`
    - `models/`
    - `prompts/`
    - story-related tests/docs

- `feat/tts-core`
  - TTS-focused long-lived workstream (optional).
  - Preferred scope:
    - `generators/tts_*`
    - TTS integration area in `main.py`
    - tts-related tests/docs

## Workflow

1. Start from the latest `main` and create a `feat/*` branch.
2. Implement changes in that branch.
3. Open PR into `main`.
4. Require CI success before merge.
5. Keep `main` as the single integrated source of truth.

## Sync policy

- Periodically sync `main` back into long-lived `feat/*` branches:
  - At least monthly, or before each release cycle.
- For shared files (`README.md`, CI configs, env docs):
  - Update in the branch where the change originates.
  - Then propagate via merge or cherry-pick.

## Suggested labels

- `area:story`
- `area:tts`
- `area:docs`
- `area:shared`

## Notes

- Branch protection is recommended on `main` (PR-required, no direct push, CI-required).
