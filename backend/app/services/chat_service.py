from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import Chatroom, ImageAsset, ImageRecord, Message
from app.schemas.chat import ChatroomSnapshot
from app.services.database_catalog_service import record_to_dict


def timestamp(value: int | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def message_id(chatroom_id: str, exchange_id: str, role: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{chatroom_id}:{exchange_id}:{role}").hex


def touch_chatroom(room: Chatroom) -> None:
    """Move retention to the last time the chatroom was actually used."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=get_settings().data_retention_minutes)
    room.updated_at = now
    room.expires_at = expires_at
    for message in room.messages:
        message.expires_at = expires_at


def get_chatroom(db: Session, chatroom_id: str, user_id: str) -> Chatroom:
    room = db.scalar(
        select(Chatroom)
        .where(
            Chatroom.id == chatroom_id,
            Chatroom.user_id == user_id,
            Chatroom.deleted_at.is_(None),
        )
        .options(selectinload(Chatroom.messages))
    )
    if room is None:
        raise HTTPException(404, "Chatroom not found")
    return room


def upsert_message(
    db: Session,
    room: Chatroom,
    exchange_id: str,
    role: str,
    message_type: str,
    content: str,
    content_data: dict,
    created_at: datetime,
) -> Message:
    identity = message_id(room.id, exchange_id, role)
    message = db.get(Message, identity)
    if message is None:
        message = Message(
            id=identity,
            chatroom_id=room.id,
            role=role,
            client_exchange_id=exchange_id,
            created_at=created_at,
            expires_at=room.expires_at,
        )
        db.add(message)
    message.message_type = message_type
    message.content = content
    message.content_data = content_data
    return message


def link_images(
    db: Session,
    room: Chatroom,
    assistant: Message,
    image_ids: list[str],
    user_id: str,
) -> None:
    if not image_ids:
        return
    records = db.scalars(
        select(ImageRecord).where(
            ImageRecord.id.in_(image_ids),
            ImageRecord.user_id == user_id,
            ImageRecord.deleted_at.is_(None),
        )
    ).all()
    found_ids = {record.id for record in records}
    unknown_ids = set(image_ids) - found_ids
    if unknown_ids:
        raise HTTPException(422, f"Unknown image records: {sorted(unknown_ids)}")
    for record in records:
        record.chatroom_id = room.id
        record.message_id = assistant.id


def sync_chatroom(db: Session, snapshot: ChatroomSnapshot, user_id: str) -> ChatroomSnapshot:
    room = db.get(Chatroom, snapshot.id)
    if room is None:
        room = Chatroom(id=snapshot.id, user_id=user_id, title=snapshot.title)
        db.add(room)
        db.flush()
    elif room.user_id != user_id or room.deleted_at is not None:
        raise HTTPException(404, "Chatroom not found")
    room.title = snapshot.title.strip() or "圖騰對話"

    touch_chatroom(room)
    retained_ids: set[str] = set()
    for exchange in snapshot.generationExchanges:
        created_at = timestamp(exchange.createdAt)
        user_message = upsert_message(
            db,
            room,
            exchange.id,
            "user",
            "generation",
            exchange.prompt,
            {
                "createdAt": exchange.createdAt,
                "prompt": exchange.prompt,
                "elements": exchange.elements,
            },
            created_at,
        )
        assistant = upsert_message(
            db,
            room,
            exchange.id,
            "assistant",
            "generation",
            exchange.reply,
            {
                "createdAt": exchange.createdAt,
                "reply": exchange.reply,
                "pending": exchange.pending,
            },
            created_at,
        )
        retained_ids.update((user_message.id, assistant.id))
        link_images(db, room, assistant, [image.id for image in exchange.images], user_id)

    for exchange in snapshot.revisionExchanges:
        created_at = timestamp(exchange.createdAt)
        user_message = upsert_message(
            db,
            room,
            exchange.id,
            "user",
            "revision",
            exchange.user,
            {
                "createdAt": exchange.createdAt,
                "user": exchange.user,
                "sourceImage": exchange.sourceImage,
            },
            created_at,
        )
        assistant = upsert_message(
            db,
            room,
            exchange.id,
            "assistant",
            "revision",
            exchange.reply,
            {
                "createdAt": exchange.createdAt,
                "reply": exchange.reply,
                "pending": exchange.pending,
            },
            created_at,
        )
        retained_ids.update((user_message.id, assistant.id))
        link_images(
            db, room, assistant, [exchange.image.id] if exchange.image else [], user_id
        )

    for existing in list(room.messages):
        if existing.id not in retained_ids:
            db.delete(existing)
    # A very fast job may finish before the pending snapshot reaches SQLite.
    # Reconcile completed jobs after the messages exist so order cannot lose a result.
    from app.services.generation_job_service import reconcile_chatroom_generation_jobs

    db.flush()
    reconcile_chatroom_generation_jobs(db, room.id, user_id)
    db.commit()
    return chatroom_snapshot(db, room.id, user_id)


def chatroom_snapshot(
    db: Session, chatroom_id: str, user_id: str, *, touch: bool = False
) -> ChatroomSnapshot:
    room = get_chatroom(db, chatroom_id, user_id)
    if touch:
        touch_chatroom(room)
        db.commit()
    messages = sorted(room.messages, key=lambda item: (item.created_at, item.role))
    grouped: dict[tuple[str, str], dict[str, Message]] = {}
    for message in messages:
        grouped.setdefault((message.message_type, message.client_exchange_id), {})[
            message.role
        ] = message

    generation_exchanges = []
    revision_exchanges = []
    for (message_type, exchange_id), roles in grouped.items():
        user = roles.get("user")
        assistant = roles.get("assistant")
        if user is None or assistant is None:
            continue
        image_records = db.scalars(
            select(ImageRecord)
            .where(ImageRecord.message_id == assistant.id, ImageRecord.deleted_at.is_(None))
            .options(
                selectinload(ImageRecord.assets).selectinload(ImageAsset.collection_links)
            )
            .order_by(ImageRecord.created_at)
        ).all()
        images = [record_to_dict(record) for record in image_records]
        user_data = user.content_data or {}
        assistant_data = assistant.content_data or {}
        if message_type == "generation":
            generation_exchanges.append(
                {
                    "id": exchange_id,
                    "createdAt": user_data.get("createdAt"),
                    "prompt": user_data.get("prompt", user.content),
                    "elements": user_data.get("elements", []),
                    "reply": assistant_data.get("reply", assistant.content),
                    "images": images,
                    "pending": assistant_data.get("pending", False),
                }
            )
        else:
            revision_exchanges.append(
                {
                    "id": exchange_id,
                    "createdAt": user_data.get("createdAt"),
                    "user": user_data.get("user", user.content),
                    "sourceImage": user_data.get("sourceImage", ""),
                    "reply": assistant_data.get("reply", assistant.content),
                    "image": images[0] if images else None,
                    "pending": assistant_data.get("pending", False),
                }
            )
    return ChatroomSnapshot(
        id=room.id,
        title=room.title,
        revisionExchanges=revision_exchanges,
        generationExchanges=generation_exchanges,
    )


def list_chatrooms(db: Session, user_id: str) -> list[ChatroomSnapshot]:
    ids = db.scalars(
        select(Chatroom.id)
        .where(Chatroom.user_id == user_id, Chatroom.deleted_at.is_(None))
        .order_by(Chatroom.updated_at.desc())
        .limit(30)
    ).all()
    return [chatroom_snapshot(db, chatroom_id, user_id) for chatroom_id in ids]


def rename_chatroom(
    db: Session, chatroom_id: str, title: str, user_id: str
) -> ChatroomSnapshot:
    room = get_chatroom(db, chatroom_id, user_id)
    room.title = title.strip()
    touch_chatroom(room)
    db.commit()
    return chatroom_snapshot(db, room.id, user_id)


def delete_chatroom(db: Session, chatroom_id: str, user_id: str) -> None:
    room = get_chatroom(db, chatroom_id, user_id)
    room.deleted_at = datetime.now(timezone.utc)
    db.commit()
