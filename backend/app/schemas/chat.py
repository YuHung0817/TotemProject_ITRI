from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.image import ImageRecord


class GenerationExchangeSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    createdAt: int | None = None
    prompt: str = ""
    elements: list[str] = Field(default_factory=list)
    reply: str = ""
    images: list[ImageRecord] = Field(default_factory=list)
    pending: bool = False


class RevisionExchangeSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    createdAt: int | None = None
    user: str = ""
    sourceImage: str = ""
    reply: str = ""
    image: ImageRecord | None = None
    pending: bool = False


class ChatroomSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    title: str = Field(default="圖騰對話", min_length=1, max_length=200)
    revisionExchanges: list[RevisionExchangeSnapshot] = Field(default_factory=list)
    generationExchanges: list[GenerationExchangeSnapshot] = Field(default_factory=list)


class ChatroomUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
