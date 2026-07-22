from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.image import ImageRecord


class GenerationJobResponse(BaseModel):
    id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    images: list[ImageRecord] = Field(default_factory=list)
    error_message: str | None = None
