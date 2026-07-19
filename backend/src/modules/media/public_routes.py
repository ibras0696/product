import asyncio
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundError
from config import get_settings
from infrastructure.database import get_session
from modules.media.storage import LocalMediaStorage

router = APIRouter(prefix="/media", tags=["public-media"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/{media_id}/{variant}", response_class=FileResponse)
async def published_media_file(
    media_id: UUID,
    variant: Literal["original", "preview"],
    session: Session,
) -> FileResponse:
    row = (
        (
            await session.execute(
                text(
                    """SELECT storage_key,mime_type FROM media_assets
                WHERE id=:id AND status='published'"""
                ),
                {"id": media_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise NotFoundError("Published media not found")
    key = str(row["storage_key"])
    if variant == "preview":
        key = f"{key.rsplit('/', 1)[0]}/preview.webp"
    path = LocalMediaStorage(get_settings().media_storage_root).resolve_key(key)
    if not await asyncio.to_thread(path.is_file):
        raise NotFoundError("Published media not found")
    media_type = "image/webp" if variant == "preview" else str(row["mime_type"])
    return FileResponse(path, media_type=media_type)
