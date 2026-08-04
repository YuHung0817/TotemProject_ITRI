from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from app.schemas.image import ColorTag, ImageRecord


class GenerationExchangeSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    createdAt: int | None = None
    prompt: str = ""
    elements: list[str] = Field(default_factory=list)
    colors: list[ColorTag] = Field(default_factory=list)
    carrier: str | None = Field(default=None, max_length=50)
    reply: str = ""
    images: list[ImageRecord] = Field(default_factory=list)
    pending: bool = False
    failed: bool = False
    expectedImageCount: int = Field(default=0, ge=0)
    missingImageCount: int = Field(default=0, ge=0)


class RevisionExchangeSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    createdAt: int | None = None
    user: str = ""
    sourceImage: str = ""
    reply: str = ""
    image: ImageRecord | None = None
    pending: bool = False
    failed: bool = False
    expectedImage: bool = False
    imageExpired: bool = False
    displayAsset: Literal["motif", "preview"] = "motif"


class ChatroomSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    title: str = Field(default="圖騰對話", min_length=1, max_length=200)
    expires_at: datetime | None = None
    revisionExchanges: list[RevisionExchangeSnapshot] = Field(default_factory=list)
    generationExchanges: list[GenerationExchangeSnapshot] = Field(default_factory=list)

    @field_serializer("expires_at", when_used="json")
    def serialize_expires_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        normalized = value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)
        return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


class ChatroomUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
