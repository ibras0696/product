from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile, status

from common.exceptions import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from common.schemas import ApiResponse
from config import get_settings
from infrastructure.database import session_factory
from modules.media.public import (
    IdempotencyConflictError,
    ImageValidator,
    LocalMediaStorage,
    MediaUploadService,
    MediaValidationError,
    SqlMediaRepository,
    StorageError,
    SubmissionMedia,
    SubmissionMediaLimitError,
    SubmissionMediaMetadata,
    SubmissionMediaPatch,
    SubmissionMediaService,
    UploadMetadata,
    UploadTooLargeError,
)
from modules.submissions.capabilities import draft_cookie_name
from modules.submissions.routes import ServiceDependency, _require_same_origin

router = APIRouter(prefix="/submissions/{submission_id}/media", tags=["submission-media"])


class PayloadTooLargeError(ApplicationError):
    code = "payload_too_large"
    status_code = 413


class UnsupportedMediaTypeError(ApplicationError):
    code = "unsupported_media_type"
    status_code = 415


class MediaIdempotencyError(ConflictError):
    code = "idempotency_conflict"


def _storage() -> LocalMediaStorage:
    return LocalMediaStorage(get_settings().media_storage_root)


def _repository(submission_id: UUID) -> SqlMediaRepository:
    return SqlMediaRepository(session_factory, submission_id)


@dataclass(frozen=True, slots=True)
class MediaUploadInput:
    idempotency_key: UUID
    file: UploadFile
    metadata: SubmissionMediaMetadata


def _metadata_input(
    caption: Annotated[str, Form(max_length=2_000)],
    author: Annotated[str, Form(max_length=300)],
    source_description: Annotated[str, Form(max_length=5_000)],
    approximate_date: Annotated[str | None, Form(max_length=120)] = None,
    related_entity_id: Annotated[UUID | None, Form()] = None,
) -> SubmissionMediaMetadata:
    return SubmissionMediaMetadata(
        caption=caption,
        author=author,
        source_description=source_description,
        approximate_date=approximate_date,
        related_entity_id=related_entity_id,
    )


def _upload_input(
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    file: Annotated[UploadFile, File()],
    metadata: Annotated[SubmissionMediaMetadata, Depends(_metadata_input)],
) -> MediaUploadInput:
    return MediaUploadInput(idempotency_key, file, metadata)


@router.post("", response_model=ApiResponse[SubmissionMedia], status_code=status.HTTP_201_CREATED)
async def upload_submission_media(
    submission_id: UUID,
    request: Request,
    submission_service: ServiceDependency,
    upload_input: Annotated[MediaUploadInput, Depends(_upload_input)],
) -> ApiResponse[SubmissionMedia]:
    _require_same_origin(request)
    cookie = request.cookies.get(draft_cookie_name(submission_id))
    await submission_service.authorize_owner(submission_id, cookie, editable=True)
    file = upload_input.file
    upload = MediaUploadService(_repository(submission_id), _storage(), ImageValidator())
    try:
        record = await upload.upload(
            idempotency_key=upload_input.idempotency_key,
            chunks=_chunks(file),
            metadata=UploadMetadata(
                submission_id=submission_id,
                original_name=Path(file.filename or "upload").name[:500],
                **upload_input.metadata.model_dump(),
            ),
        )
    except IdempotencyConflictError as exc:
        raise MediaIdempotencyError(str(exc)) from exc
    except SubmissionMediaLimitError as exc:
        raise ConflictError(str(exc)) from exc
    except UploadTooLargeError as exc:
        raise PayloadTooLargeError(str(exc)) from exc
    except MediaValidationError as exc:
        raise UnsupportedMediaTypeError(str(exc)) from exc
    except StorageError as exc:
        raise ServiceUnavailableError("Media storage is temporarily unavailable") from exc
    finally:
        await file.close()
    result = SubmissionMedia.from_record(record)
    return ApiResponse[SubmissionMedia].success(result, request.state.request_id)


@router.get("", response_model=ApiResponse[list[SubmissionMedia]])
async def list_submission_media(
    submission_id: UUID, request: Request, submission_service: ServiceDependency
) -> ApiResponse[list[SubmissionMedia]]:
    cookie = request.cookies.get(draft_cookie_name(submission_id))
    await submission_service.authorize_owner(submission_id, cookie, editable=False)
    records = await SubmissionMediaService(_repository(submission_id), _storage()).list(
        submission_id
    )
    result = [SubmissionMedia.from_record(record) for record in records]
    return ApiResponse[list[SubmissionMedia]].success(result, request.state.request_id)


@router.patch("/{media_id}", response_model=ApiResponse[SubmissionMedia])
async def patch_submission_media(
    submission_id: UUID,
    media_id: UUID,
    payload: SubmissionMediaPatch,
    request: Request,
    submission_service: ServiceDependency,
) -> ApiResponse[SubmissionMedia]:
    _require_same_origin(request)
    cookie = request.cookies.get(draft_cookie_name(submission_id))
    await submission_service.authorize_owner(submission_id, cookie, editable=True)
    record = await SubmissionMediaService(_repository(submission_id), _storage()).update(
        submission_id, media_id, payload.changes()
    )
    if record is None:
        raise NotFoundError("Submission media not found")
    return ApiResponse[SubmissionMedia].success(
        SubmissionMedia.from_record(record), request.state.request_id
    )


@router.delete("/{media_id}", response_model=ApiResponse[None])
async def delete_submission_media(
    submission_id: UUID,
    media_id: UUID,
    request: Request,
    submission_service: ServiceDependency,
) -> ApiResponse[None]:
    _require_same_origin(request)
    cookie = request.cookies.get(draft_cookie_name(submission_id))
    await submission_service.authorize_owner(submission_id, cookie, editable=True)
    deleted = await SubmissionMediaService(_repository(submission_id), _storage()).delete(
        submission_id, media_id
    )
    if not deleted:
        raise NotFoundError("Submission media not found")
    return ApiResponse[None].success(None, request.state.request_id)


async def _chunks(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(64 * 1024):
        yield chunk
