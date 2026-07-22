from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ApiUsage, Chatroom, GenerationJob, ImageRecord as ImageRecordModel, Message
from app.schemas.generation_job import GenerationJobResponse
from app.schemas.image import ImageRecord
from app.services.database_catalog_service import find_record

ACTIVE_STATUSES = ("pending", "running")


def _chat_result_message(job: GenerationJob) -> str:
    operation = (job.request_data or {}).get("operation")
    if job.status == "failed":
        return job.error_message or "圖片生成失敗"
    if operation in {"product_preview", "random_product_preview", "product_preview_variant"}:
        return "新的商品圖已完成；圖騰本身保持不變。"
    if operation == "regenerate":
        return "已依照你的要求產生新的圖騰；原圖與商品預覽都已保留。"
    count = len(job.result_record_ids or [])
    return f"完成了！這是相同圖案的 {count} 組配色。"


def sync_generation_job_to_chat(db: Session, job: GenerationJob) -> bool:
    context = job.request_data or {}
    chatroom_id = context.get("chatroom_id")
    exchange_id = context.get("client_exchange_id")
    if not chatroom_id or not exchange_id or job.status not in {"succeeded", "failed"}:
        return False
    room = db.scalar(
        select(Chatroom).where(
            Chatroom.id == chatroom_id,
            Chatroom.user_id == job.user_id,
            Chatroom.deleted_at.is_(None),
        )
    )
    if room is None:
        return False
    assistant = db.scalar(
        select(Message).where(
            Message.chatroom_id == room.id,
            Message.client_exchange_id == exchange_id,
            Message.role == "assistant",
        )
    )
    if assistant is None:
        return False
    reply = _chat_result_message(job)
    data = dict(assistant.content_data or {})
    data.update({"reply": reply, "pending": False})
    assistant.content = reply
    assistant.content_data = data
    if job.status == "succeeded":
        record_ids = list(job.result_record_ids or [])
        if not record_ids and job.result_record_id:
            record_ids = [job.result_record_id]
        records = db.scalars(
            select(ImageRecordModel).where(
                ImageRecordModel.id.in_(record_ids),
                ImageRecordModel.user_id == job.user_id,
                ImageRecordModel.deleted_at.is_(None),
            )
        ).all()
        for record in records:
            record.chatroom_id = room.id
            record.message_id = assistant.id
    room.updated_at = utc_now()
    return True


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_stale_jobs(db: Session, user_id: str) -> None:
    cutoff = utc_now() - timedelta(minutes=get_settings().generation_stale_minutes)
    db.execute(
        update(GenerationJob)
        .execution_options(synchronize_session=False)
        .where(
            GenerationJob.user_id == user_id,
            GenerationJob.status.in_(ACTIVE_STATUSES),
            GenerationJob.updated_at < cutoff,
        )
        .values(
            status="failed",
            error_message="Generation was interrupted or timed out",
            finished_at=utc_now(),
            updated_at=utc_now(),
        )
    )
    db.commit()


def existing_job(db: Session, idempotency_key: str, user_id: str) -> GenerationJob | None:
    return db.scalar(
        select(GenerationJob).where(
            GenerationJob.user_id == user_id,
            GenerationJob.idempotency_key == idempotency_key,
        )
    )


def _raise_for_existing(job: GenerationJob) -> None:
    if job.status in ACTIVE_STATUSES:
        raise HTTPException(
            409,
            {
                "code": "generation_in_progress",
                "message": "This generation is already in progress",
                "job_id": job.id,
            },
        )
    if job.status == "failed":
        raise HTTPException(
            409,
            {
                "code": "generation_failed",
                "message": "This generation attempt failed; submit a new request to retry",
                "job_id": job.id,
            },
        )


def enforce_usage_limits(db: Session, user_id: str) -> None:
    settings = get_settings()
    now = utc_now()
    hour_count = db.scalar(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.user_id == user_id,
            GenerationJob.created_at >= now - timedelta(hours=1),
        )
    ) or 0
    if hour_count >= settings.generation_hourly_limit:
        raise HTTPException(
            429,
            {
                "code": "hourly_generation_limit",
                "message": "Hourly image generation limit reached",
            },
        )
    day_count = db.scalar(
        select(func.count(GenerationJob.id)).where(
            GenerationJob.user_id == user_id,
            GenerationJob.created_at >= now - timedelta(days=1),
        )
    ) or 0
    if day_count >= settings.generation_daily_limit:
        raise HTTPException(
            429,
            {
                "code": "daily_generation_limit",
                "message": "Daily image generation limit reached",
            },
        )


def acquire_generation_job(
    db: Session,
    idempotency_key: str,
    request_data: dict,
    user_id: str,
) -> GenerationJob:
    cleanup_stale_jobs(db, user_id)
    duplicate = existing_job(db, idempotency_key, user_id)
    if duplicate is not None:
        if duplicate.status == "succeeded":
            return duplicate
        _raise_for_existing(duplicate)

    enforce_usage_limits(db, user_id)
    job = GenerationJob(
        user_id=user_id,
        idempotency_key=idempotency_key,
        status="running",
        request_data=request_data,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = existing_job(db, idempotency_key, user_id)
        if duplicate is not None:
            if duplicate.status == "succeeded":
                return duplicate
            _raise_for_existing(duplicate)
        active = db.scalar(
            select(GenerationJob).where(
                GenerationJob.user_id == user_id,
                GenerationJob.status.in_(ACTIVE_STATUSES),
            )
        )
        raise HTTPException(
            429,
            {
                "code": "another_generation_in_progress",
                "message": "Another image generation is already in progress",
                "job_id": active.id if active else None,
            },
        ) from None
    db.refresh(job)
    return job


def complete_generation_job(db: Session, job: GenerationJob, record_ids: list[str]) -> None:
    now = utc_now()
    job.status = "succeeded"
    job.result_record_id = record_ids[0] if record_ids else None
    job.result_record_ids = record_ids
    job.finished_at = now
    job.updated_at = now
    db.add(
        ApiUsage(
            user_id=job.user_id,
            operation=(job.request_data or {}).get("operation", "image_generation"),
            status="succeeded",
            usage_data={"job_id": job.id, "image_count": len(record_ids)},
        )
    )
    sync_generation_job_to_chat(db, job)
    db.commit()


def fail_generation_job(db: Session, job_id: str, error: Exception) -> None:
    job = db.get(GenerationJob, job_id)
    if job is None:
        return
    now = utc_now()
    job.status = "failed"
    job.error_message = str(error)[:500]
    job.finished_at = now
    job.updated_at = now
    db.add(
        ApiUsage(
            user_id=job.user_id,
            operation=(job.request_data or {}).get("operation", "image_generation"),
            status="failed",
            usage_data={"job_id": job.id},
        )
    )
    sync_generation_job_to_chat(db, job)
    db.commit()


def reconcile_chatroom_generation_jobs(
    db: Session, chatroom_id: str, user_id: str
) -> None:
    jobs = db.scalars(
        select(GenerationJob).where(
            GenerationJob.user_id == user_id,
            GenerationJob.status.in_(("succeeded", "failed")),
        )
    ).all()
    for job in jobs:
        if (job.request_data or {}).get("chatroom_id") == chatroom_id:
            sync_generation_job_to_chat(db, job)


def job_images(db: Session, job: GenerationJob) -> list[ImageRecord]:
    ids = list(job.result_record_ids or [])
    if not ids and job.result_record_id:
        ids = [job.result_record_id]
    return [ImageRecord(**find_record(db, record_id, job.user_id)) for record_id in ids]


def generation_job_response(
    db: Session, job_id: str, user_id: str
) -> GenerationJobResponse:
    job = db.scalar(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.user_id == user_id,
        )
    )
    if job is None:
        raise HTTPException(404, "Generation job not found")
    cleanup_stale_jobs(db, user_id)
    db.refresh(job)
    return GenerationJobResponse(
        id=job.id,
        status=job.status,
        images=job_images(db, job) if job.status == "succeeded" else [],
        error_message=job.error_message if job.status == "failed" else None,
    )
