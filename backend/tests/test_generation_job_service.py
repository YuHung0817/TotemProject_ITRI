from datetime import timedelta
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.db.models import Chatroom, ImageAsset, ImageRecord, Message, User
from app.services import generation_job_service
from app.services.chat_service import chatroom_snapshot
from app.services.generation_job_service import (
    acquire_generation_job,
    complete_generation_job,
    utc_now,
)

USER_ID = "single-store"


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def limits(hourly: int = 10, daily: int = 30, stale: int = 10) -> SimpleNamespace:
    return SimpleNamespace(
        generation_hourly_limit=hourly,
        generation_daily_limit=daily,
        generation_stale_minutes=stale,
    )


def add_user(db: Session) -> None:
    db.add(User(id=USER_ID, username="store"))
    db.commit()


def test_idempotency_and_one_active_job(monkeypatch) -> None:
    monkeypatch.setattr(generation_job_service, "get_settings", lambda: limits())
    engine = sqlite_engine()
    with Session(engine) as db:
        add_user(db)
        first = acquire_generation_job(db, "request-key-0001", {"prompt": "山"}, USER_ID)
        with pytest.raises(HTTPException) as duplicate_error:
            acquire_generation_job(db, "request-key-0001", {"prompt": "山"}, USER_ID)
        assert duplicate_error.value.status_code == 409
        assert duplicate_error.value.detail["job_id"] == first.id

        with pytest.raises(HTTPException) as active_error:
            acquire_generation_job(db, "request-key-0002", {"prompt": "河"}, USER_ID)
        assert active_error.value.status_code == 429

        complete_generation_job(db, first, [])
        second = acquire_generation_job(db, "request-key-0002", {"prompt": "河"}, USER_ID)
        assert second.status == "running"
        completed_duplicate = acquire_generation_job(
            db, "request-key-0001", {"prompt": "山"}, USER_ID
        )
        assert completed_duplicate.id == first.id
        assert completed_duplicate.status == "succeeded"


def test_stale_job_is_failed_before_new_job_is_acquired(monkeypatch) -> None:
    monkeypatch.setattr(generation_job_service, "get_settings", lambda: limits(stale=10))
    engine = sqlite_engine()
    with Session(engine) as db:
        add_user(db)
        stale = acquire_generation_job(db, "request-key-0001", {}, USER_ID)
        stale.updated_at = utc_now() - timedelta(minutes=11)
        db.commit()
        replacement = acquire_generation_job(db, "request-key-0002", {}, USER_ID)
        db.refresh(stale)
        assert stale.status == "failed"
        assert replacement.status == "running"


def test_hourly_limit_is_enforced_before_provider_call(monkeypatch) -> None:
    monkeypatch.setattr(generation_job_service, "get_settings", lambda: limits(hourly=1))
    engine = sqlite_engine()
    with Session(engine) as db:
        add_user(db)
        first = acquire_generation_job(db, "request-key-0001", {}, USER_ID)
        complete_generation_job(db, first, [])
        with pytest.raises(HTTPException) as error:
            acquire_generation_job(db, "request-key-0002", {}, USER_ID)
        assert error.value.status_code == 429
        assert error.value.detail["code"] == "hourly_generation_limit"


def test_completed_job_reconciles_late_pending_chat_message(monkeypatch) -> None:
    monkeypatch.setattr(generation_job_service, "get_settings", lambda: limits())
    engine = sqlite_engine()
    with Session(engine) as db:
        add_user(db)
        job = acquire_generation_job(
            db,
            "request-key-chat-0001",
            {
                "operation": "regenerate",
                "chatroom_id": "room-1",
                "client_exchange_id": "exchange-1",
            },
            USER_ID,
        )
        image = ImageRecord(id="image-1", user_id="single-store", prompt="prompt")
        asset = ImageAsset(
            id="asset-1",
            image_record=image,
            asset_type="motif",
            storage_key="image-1.png",
        )
        db.add_all((image, asset))
        db.commit()

        # The provider finishes before the frontend's pending snapshot is saved.
        complete_generation_job(db, job, [image.id])
        room = Chatroom(id="room-1", user_id="single-store", title="chat")
        user_message = Message(
            id="message-user-1",
            chatroom_id=room.id,
            role="user",
            message_type="revision",
            client_exchange_id="exchange-1",
            content="change it",
            content_data={
                "createdAt": 1_753_092_000_000,
                "user": "change it",
                "sourceImage": "/generated/images/source.png",
            },
        )
        assistant = Message(
            id="message-1",
            chatroom_id=room.id,
            role="assistant",
            message_type="revision",
            client_exchange_id="exchange-1",
            content="正在生成",
            content_data={"reply": "正在生成", "pending": True},
        )
        db.add_all((room, user_message, assistant))
        db.commit()

        # Opening a chatroom reconciles a job that finished while the user was
        # viewing another page.
        snapshot = chatroom_snapshot(db, room.id, USER_ID)
        db.refresh(assistant)
        db.refresh(image)

        assert snapshot.revisionExchanges[0].pending is False
        assert snapshot.revisionExchanges[0].image is not None
        assert snapshot.revisionExchanges[0].image.id == image.id
        assert assistant.content_data["pending"] is False
        assert "已依照你的要求" in assistant.content
        assert image.chatroom_id == room.id
        assert image.message_id == assistant.id
