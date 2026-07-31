from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import Session

from app.db import Base
from app.db.models import Chatroom, ImageRecord, Message, User
from app.schemas.chat import ChatroomSnapshot
from app.services.chat_service import (
    chatroom_snapshot,
    delete_chatroom,
    list_chatrooms,
    sync_chatroom,
)
from app.services.database_catalog_service import save_record

USER_ID = "single-store"


def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def image_payload(image_id: str) -> dict:
    return {
        "id": image_id,
        "filename": f"{image_id}.png",
        "url": f"/generated/images/{image_id}.png",
        "created_at": "2026-07-21T10:00:00+00:00",
        "prompt": "山與河流",
        "request": {"prompt": "山與河流", "elements": ["山", "河流"]},
        "assets": {
            "motif": {
                "type": "motif",
                "filename": f"{image_id}.png",
                "url": f"/generated/images/{image_id}.png",
            }
        },
    }


def test_chatroom_expiry_json_marks_naive_database_time_as_utc() -> None:
    snapshot = ChatroomSnapshot(
        id="chat-timezone",
        title="Timezone",
        expires_at=datetime(2026, 7, 30, 3, 26),
    )

    assert snapshot.model_dump(mode="json")["expires_at"] == "2026-07-30T03:26:00Z"


def test_sync_chatroom_splits_exchanges_and_links_images() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        db.commit()
        image = save_record(db, image_payload("image-1"), USER_ID)
        snapshot = ChatroomSnapshot.model_validate(
            {
                "id": "chat-1",
                "title": "山與河流",
                "generationExchanges": [
                    {
                        "id": "generation-1",
                        "createdAt": 1_753_092_000_000,
                        "prompt": "山與河流",
                        "elements": ["山", "河流"],
                        "reply": "完成了！",
                        "images": [image],
                        "pending": False,
                    }
                ],
                "revisionExchanges": [],
            }
        )
        result = sync_chatroom(db, snapshot, USER_ID)
        assert result.generationExchanges[0].images[0].id == "image-1"
        assert len(db.scalars(select(Message)).all()) == 2
        record = db.get(ImageRecord, "image-1")
        assert record is not None
        assert record.chatroom_id == "chat-1"
        assert record.message_id is not None

        sync_chatroom(db, snapshot, USER_ID)
        assert len(db.scalars(select(Message)).all()) == 2
        assert list_chatrooms(db, USER_ID)[0].title == "山與河流"

        delete_chatroom(db, "chat-1", USER_ID)
        room = db.get(Chatroom, "chat-1")
        assert room is not None and room.deleted_at is not None
        assert list_chatrooms(db, USER_ID) == []


def test_reading_chatroom_does_not_refresh_expiry_or_sort_order() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        older_room = Chatroom(
            id="chat-1",
            user_id=USER_ID,
            title="older",
            updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        newer_room = Chatroom(
            id="chat-2",
            user_id=USER_ID,
            title="newer",
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.add_all((older_room, newer_room))
        db.commit()

        original_expiry = older_room.expires_at
        original_updated_at = older_room.updated_at
        assert [room.id for room in list_chatrooms(db, USER_ID)] == ["chat-2", "chat-1"]

        chatroom_snapshot(db, older_room.id, USER_ID)
        db.refresh(older_room)
        assert older_room.expires_at == original_expiry
        assert older_room.updated_at == original_updated_at
        assert [room.id for room in list_chatrooms(db, USER_ID)] == ["chat-2", "chat-1"]


def test_expired_chatrooms_are_hidden_before_cleanup_runs() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        db.add_all(
            [
                Chatroom(
                    id="expired-chat",
                    user_id=USER_ID,
                    title="expired",
                    expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                ),
                Chatroom(
                    id="active-chat",
                    user_id=USER_ID,
                    title="active",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1),
                ),
            ]
        )
        db.commit()

        assert [room.id for room in list_chatrooms(db, USER_ID)] == ["active-chat"]


def test_chatroom_marks_missing_generated_images_as_expired() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        db.commit()
        image = save_record(db, image_payload("image-expiring"), USER_ID)
        snapshot = ChatroomSnapshot.model_validate(
            {
                "id": "chat-expiring",
                "title": "即將過期",
                "generationExchanges": [
                    {
                        "id": "generation-expiring",
                        "prompt": "山豬",
                        "reply": "完成了！",
                        "images": [image],
                        "pending": False,
                    }
                ],
            }
        )
        synced = sync_chatroom(db, snapshot, USER_ID)
        assert synced.generationExchanges[0].expectedImageCount == 1
        assert synced.generationExchanges[0].missingImageCount == 0

        db.execute(delete(ImageRecord).where(ImageRecord.id == "image-expiring"))
        db.commit()

        expired = chatroom_snapshot(db, "chat-expiring", USER_ID)
        exchange = expired.generationExchanges[0]
        assert exchange.images == []
        assert exchange.expectedImageCount == 1
        assert exchange.missingImageCount == 1


def test_revision_display_asset_is_persisted() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        db.commit()
        snapshot = ChatroomSnapshot.model_validate(
            {
                "id": "chat-product-preview",
                "title": "更換商品圖",
                "revisionExchanges": [
                    {
                        "id": "revision-product-preview",
                        "user": "更換商品圖：換成綠色",
                        "sourceImage": "/generated/images/source.png",
                        "reply": "新的商品圖已完成。",
                        "displayAsset": "preview",
                    }
                ],
            }
        )

        saved = sync_chatroom(db, snapshot, USER_ID)

        assert saved.revisionExchanges[0].displayAsset == "preview"
        assert (
            chatroom_snapshot(db, "chat-product-preview", USER_ID)
            .revisionExchanges[0]
            .displayAsset
            == "preview"
        )
