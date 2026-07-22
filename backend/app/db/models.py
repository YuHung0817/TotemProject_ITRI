from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_expiry() -> datetime:
    return utc_now() + timedelta(minutes=get_settings().data_retention_minutes)


def new_id() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chatrooms: Mapped[list[Chatroom]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    image_records: Mapped[list[ImageRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    collections: Mapped[list[Collection]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Chatroom(Base):
    __tablename__ = "chatrooms"
    __table_args__ = (Index("ix_chatrooms_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_expiry, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="chatrooms")
    messages: Mapped[list[Message]] = relationship(
        back_populates="chatroom", cascade="all, delete-orphan"
    )
    image_records: Mapped[list[ImageRecord]] = relationship(back_populates="chatroom")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_expires_at", "expires_at"),
        UniqueConstraint(
            "chatroom_id",
            "client_exchange_id",
            "role",
            name="uq_messages_chat_exchange_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    chatroom_id: Mapped[str] = mapped_column(
        ForeignKey("chatrooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="generation")
    client_exchange_id: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_expiry, nullable=False
    )

    chatroom: Mapped[Chatroom] = relationship(back_populates="messages")
    image_records: Mapped[list[ImageRecord]] = relationship(back_populates="message")


class ImageRecord(Base):
    __tablename__ = "image_records"
    __table_args__ = (Index("ix_image_records_expires_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chatroom_id: Mapped[str | None] = mapped_column(
        ForeignKey("chatrooms.id", ondelete="SET NULL"), index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), index=True
    )
    parent_image_id: Mapped[str | None] = mapped_column(
        ForeignKey("image_records.id", ondelete="SET NULL"), index=True
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    compiled_prompt: Mapped[str | None] = mapped_column(Text)
    generation_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_expiry, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="image_records")
    chatroom: Mapped[Chatroom | None] = relationship(back_populates="image_records")
    message: Mapped[Message | None] = relationship(back_populates="image_records")
    parent: Mapped[ImageRecord | None] = relationship(remote_side=[id])
    assets: Mapped[list[ImageAsset]] = relationship(
        back_populates="image_record", cascade="all, delete-orphan"
    )


class ImageAsset(Base):
    __tablename__ = "image_assets"
    __table_args__ = (
        UniqueConstraint("image_record_id", "asset_type", name="uq_image_assets_record_type"),
        Index("ix_image_assets_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    image_record_id: Mapped[str] = mapped_column(
        ForeignKey("image_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="image/png")
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    is_saved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deletion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_expiry, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    image_record: Mapped[ImageRecord] = relationship(back_populates="assets")
    collection_links: Mapped[list[CollectionAsset]] = relationship(
        back_populates="image_asset", cascade="all, delete-orphan"
    )


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collections_user_name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    # Collection folders persist. Their image links disappear when expired
    # image assets are deleted through the foreign-key cascade.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="collections")
    asset_links: Mapped[list[CollectionAsset]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionAsset(Base):
    __tablename__ = "collection_assets"

    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    image_asset_id: Mapped[str] = mapped_column(
        ForeignKey("image_assets.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    collection: Mapped[Collection] = relationship(back_populates="asset_links")
    image_asset: Mapped[ImageAsset] = relationship(back_populates="collection_links")


class ApiUsage(Base):
    __tablename__ = "api_usage"
    __table_args__ = (Index("ix_api_usage_created_at", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(200))
    usage_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index(
            "uq_generation_jobs_one_active_user",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    request_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("image_records.id", ondelete="SET NULL")
    )
    result_record_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=default_expiry, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
