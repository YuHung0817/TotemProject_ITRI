from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event, select
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


def test_using_chatroom_refreshes_expiry_but_listing_does_not() -> None:
    engine = sqlite_engine()
    with Session(engine) as db:
        db.add(User(id=USER_ID, username="store"))
        room = Chatroom(
            id="chat-1",
            user_id=USER_ID,
            title="test",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
        db.add(room)
        db.commit()

        original_expiry = room.expires_at
        list_chatrooms(db, USER_ID)
        db.refresh(room)
        assert room.expires_at == original_expiry

        chatroom_snapshot(db, room.id, USER_ID, touch=True)
        db.refresh(room)
        assert room.expires_at > original_expiry + timedelta(days=13)
