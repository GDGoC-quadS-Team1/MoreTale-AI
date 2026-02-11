# Branching Strategy

This repository uses one integrated branch and two long-lived workstream branches.

## Branch roles

- `main`
  - Integrated baseline (story + tts).
  - Release and deployment reference.

- `feature/story-core`
  - Story-focused workstream.
  - Preferred scope:
    - `generators/story_generator.py`
    - `models/`
    - `prompts/`
    - story-related tests/docs

- `feature/tts-core`
  - TTS-focused workstream.
  - Preferred scope:
    - `generators/tts_*`
    - TTS integration area in `main.py`
    - tts-related tests/docs

## Workflow

1. Implement changes in the appropriate workstream branch.
2. Open PR from workstream branch into `main`.
3. Require CI success before merge.
4. Keep `main` as the single integrated source of truth.

## Sync policy

- Periodically sync `main` back into both long-lived branches:
  - At least monthly, or before each release cycle.
- For shared files (`README.md`, CI configs, env docs):
  - Update in the branch where the change originates.
  - Then propagate via merge or cherry-pick.

## Suggested labels

- `area:story`
- `area:tts`
- `area:shared`

## Notes

- The current baseline commit used to initialize this model is `e00f128`.
- Branch protection is recommended on `main` (PR-required, no direct push, CI-required).
