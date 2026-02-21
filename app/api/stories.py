from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.core.auth import build_error, require_api_key
from app.core.config import get_settings
from app.schemas.story import (
    ErrorResponse,
    StoryCreateAcceptedResponse,
    StoryCreateRequest,
    StoryResultResponse,
    StoryStatusResponse,
)
from app.services.illustration_service import IllustrationService
from app.services.job_store import JobStore
from app.services.rate_limiter import post_stories_rate_limiter
from app.services.request_context import get_request_id, log_event
from app.services.storage import (
    build_story_result_payload,
    make_story_id,
    to_static_outputs_url,
    write_story_json,
)
from app.services.story_service import StoryService
from app.services.tts_service import TTSService

router = APIRouter(
    prefix="/api/stories",
    tags=["stories"],
    dependencies=[Depends(require_api_key)],
)
job_store = JobStore()


def _extract_generation_flags(request_payload: dict[str, Any]) -> tuple[bool, bool]:
    generation = request_payload.get("generation")
    if not isinstance(generation, dict):
        return False, False
    return bool(generation.get("enable_tts", False)), bool(
        generation.get("enable_illustration", False)
    )


def _extract_service_errors(job_payload: dict[str, Any]) -> dict[str, str | None]:
    result = job_payload.get("result")
    if not isinstance(result, dict):
        return {"tts": None, "illustrations": None}

    assets = result.get("assets")
    if not isinstance(assets, dict):
        return {"tts": None, "illustrations": None}

    tts = assets.get("tts")
    illustrations = assets.get("illustrations")
    tts_error = tts.get("service_error") if isinstance(tts, dict) else None
    illustration_error = (
        illustrations.get("service_error") if isinstance(illustrations, dict) else None
    )
    return {
        "tts": str(tts_error) if tts_error else None,
        "illustrations": str(illustration_error) if illustration_error else None,
    }


def _run_story_generation_job(
    story_id: str,
    request_payload: dict[str, Any],
    request_id: str | None = None,
) -> None:
    include_tts, include_illustration = _extract_generation_flags(request_payload)
    service_errors: dict[str, str | None] = {"tts": None, "illustrations": None}
    story_json_path = None

    log_event(
        event="story.job.start",
        request_id=request_id,
        story_id=story_id,
    )

    try:
        request = StoryCreateRequest.model_validate(request_payload)
        job_store.mark_running(story_id)
        story, story_model = StoryService.generate_story(request)
        story_json_path = write_story_json(
            story_id=story_id,
            story=story,
            story_model=story_model,
        )

        tts_result: dict[str, Any] | None = None
        if request.generation.enable_tts:
            try:
                tts_result = TTSService.generate_tts(
                    request=request,
                    story_id=story_id,
                    story=story,
                )
            except Exception as error:
                service_errors["tts"] = str(error)

        illustration_result: dict[str, Any] | None = None
        if request.generation.enable_illustration:
            try:
                illustration_result = IllustrationService.generate_illustrations(
                    request=request,
                    story_id=story_id,
                    story=story,
                )
            except Exception as error:
                service_errors["illustrations"] = str(error)

        result_payload = build_story_result_payload(
            story_id=story_id,
            include_tts=include_tts,
            include_illustration=include_illustration,
            job_status="completed",
            service_errors=service_errors,
        )
        result_summary = {
            "story_json_url": to_static_outputs_url(story_json_path),
            "page_count": result_payload["meta"]["page_count"],
            "assets": result_payload["assets"],
            "raw_service_results": {
                "tts": tts_result,
                "illustrations": illustration_result,
            },
        }
        job_store.mark_completed(story_id=story_id, result=result_summary)
        log_event(
            event="story.job.completed",
            request_id=request_id,
            story_id=story_id,
            status="completed",
            has_partial_failures=result_payload["assets"]["has_partial_failures"],
        )
    except Exception as error:
        failed_result: dict[str, Any] | None = None
        if story_json_path is not None:
            try:
                failed_payload = build_story_result_payload(
                    story_id=story_id,
                    include_tts=include_tts,
                    include_illustration=include_illustration,
                    job_status="failed",
                    service_errors=service_errors,
                )
                failed_result = {
                    "story_json_url": to_static_outputs_url(story_json_path),
                    "page_count": failed_payload["meta"]["page_count"],
                    "assets": failed_payload["assets"],
                }
            except Exception:
                failed_result = None

        job_store.mark_failed(
            story_id=story_id,
            error={
                "code": "GENERATION_FAILED",
                "message": "story generation job failed",
                "detail": {"reason": str(error)},
            },
            result=failed_result,
        )
        log_event(
            event="story.job.failed",
            request_id=request_id,
            story_id=story_id,
            status="failed",
            reason=str(error),
            level=logging.ERROR,
        )


@router.post(
    "/",
    response_model=StoryCreateAcceptedResponse,
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    status_code=status.HTTP_202_ACCEPTED,
)
def create_story(
    http_request: Request,
    request: StoryCreateRequest,
    background_tasks: BackgroundTasks,
) -> StoryCreateAcceptedResponse:
    api_key = (http_request.headers.get("X-API-Key") or "").strip()
    limit_per_min = get_settings().rate_limit_post_stories_per_min
    if not post_stories_rate_limiter.is_allowed(
        key=api_key,
        limit_per_min=limit_per_min,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=build_error(
                code="RATE_LIMIT_EXCEEDED",
                message="rate limit exceeded",
                detail={"limit_per_min": limit_per_min},
            ),
        )

    story_id = make_story_id(child_name=request.child_name, theme=request.theme)
    request_payload = request.model_dump(mode="json")
    job_store.initialize_job(story_id=story_id, request_payload=request_payload)
    request_id = get_request_id()

    background_tasks.add_task(
        _run_story_generation_job,
        story_id,
        request_payload,
        request_id,
    )

    log_event(
        event="story.job.queued",
        request_id=request_id,
        story_id=story_id,
        status="queued",
    )

    return StoryCreateAcceptedResponse(
        id=story_id,
        status="queued",
        status_url=f"/api/stories/{story_id}",
        result_url=f"/api/stories/{story_id}/result",
    )


@router.get(
    "/{story_id}",
    response_model=StoryStatusResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_story(story_id: str) -> StoryStatusResponse:
    job = job_store.load_job(story_id=story_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_error(
                code="STORY_NOT_FOUND",
                message="story not found",
                detail={"id": story_id},
            )
        )
    return StoryStatusResponse.model_validate(job)


@router.get(
    "/{story_id}/result",
    response_model=StoryResultResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_story_result(story_id: str) -> StoryResultResponse:
    job = job_store.load_job(story_id=story_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_error(
                code="STORY_NOT_FOUND",
                message="story not found",
                detail={"id": story_id},
            ),
        )

    job_status = str(job.get("status", ""))
    if job_status not in {"completed", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_error(
                code="STORY_NOT_READY",
                message="story result is not ready",
                detail={"id": story_id, "status": job_status},
            ),
        )

    request_payload = job.get("request")
    include_tts, include_illustration = _extract_generation_flags(
        request_payload if isinstance(request_payload, dict) else {}
    )
    service_errors = _extract_service_errors(job)

    try:
        payload = build_story_result_payload(
            story_id=story_id,
            include_tts=include_tts,
            include_illustration=include_illustration,
            job_status=job_status,
            service_errors=service_errors,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=build_error(
                code="STORY_RESULT_NOT_FOUND",
                message="story result not found",
                detail={"id": story_id},
            ),
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=build_error(
                code="STORY_RESULT_INVALID",
                message="story result is invalid",
                detail={"id": story_id, "reason": str(error)},
            ),
        ) from None

    return StoryResultResponse.model_validate(payload)
