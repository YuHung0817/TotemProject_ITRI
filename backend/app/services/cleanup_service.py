from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    ApiUsage,
    Chatroom,
    GenerationJob,
    ImageAsset,
    ImageRecord,
    UserSession,
)
from app.services.storage_service import delete_image


@dataclass
class CleanupReport:
    dry_run: bool
    image_records: int
    image_assets: int
    image_files: int
    chatrooms: int
    generation_jobs: int
    api_usage: int
    sessions: int

    def to_dict(self) -> dict[str, bool | int]:
        return asdict(self)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_expired_data(
    db: Session,
    *,
    dry_run: bool = True,
    now: datetime | None = None,
) -> CleanupReport:
    current = now or utc_now()
    usage_cutoff = current - timedelta(minutes=get_settings().data_retention_minutes)

    expired_record_ids = list(
        db.scalars(select(ImageRecord.id).where(ImageRecord.expires_at <= current)).all()
    )
    expired_assets = db.execute(
        select(ImageAsset.id, ImageAsset.storage_key).where(
            or_(
                ImageAsset.expires_at <= current,
                ImageAsset.image_record_id.in_(expired_record_ids),
            )
        )
    ).all()
    expired_asset_ids = [row.id for row in expired_assets]
    removable_keys = {
        row.storage_key
        for row in expired_assets
        if not db.scalar(
            select(func.count(ImageAsset.id)).where(
                ImageAsset.storage_key == row.storage_key,
                ImageAsset.id.not_in(expired_asset_ids),
            )
        )
    }
    counts = CleanupReport(
        dry_run=dry_run,
        image_records=len(expired_record_ids),
        image_assets=len(expired_asset_ids),
        image_files=len(removable_keys),
        chatrooms=db.scalar(
            select(func.count(Chatroom.id)).where(Chatroom.expires_at <= current)
        )
        or 0,
        generation_jobs=db.scalar(
            select(func.count(GenerationJob.id)).where(
                GenerationJob.expires_at <= current,
                GenerationJob.status.not_in(("pending", "running")),
            )
        )
        or 0,
        api_usage=db.scalar(
            select(func.count(ApiUsage.id)).where(ApiUsage.created_at <= usage_cutoff)
        )
        or 0,
        sessions=db.scalar(
            select(func.count(UserSession.id)).where(UserSession.expires_at <= current)
        )
        or 0,
    )
    if dry_run:
        return counts

    if expired_asset_ids:
        db.execute(
            update(ImageAsset)
            .where(ImageAsset.id.in_(expired_asset_ids))
            .values(deletion_status="deleting")
        )
        db.commit()

    # File deletion happens before database deletion. A crash is safe to retry:
    # missing files are accepted and database rows still identify unfinished work.
    for storage_key in removable_keys:
        delete_image(storage_key)

    if expired_record_ids:
        db.execute(delete(ImageRecord).where(ImageRecord.id.in_(expired_record_ids)))
    if expired_asset_ids:
        db.execute(delete(ImageAsset).where(ImageAsset.id.in_(expired_asset_ids)))
    db.execute(delete(Chatroom).where(Chatroom.expires_at <= current))
    db.execute(
        delete(GenerationJob).where(
            GenerationJob.expires_at <= current,
            GenerationJob.status.not_in(("pending", "running")),
        )
    )
    db.execute(delete(ApiUsage).where(ApiUsage.created_at <= usage_cutoff))
    db.execute(delete(UserSession).where(UserSession.expires_at <= current))
    db.commit()
    return counts
