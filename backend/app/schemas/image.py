from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str = Field(default="", description="想表達的圖騰需求。")
    elements: list[str] = Field(default_factory=list, description="布農圖騰元素。")
    palette_instruction: str = Field(default="", exclude=True)
    excluded_elements: list[str] = Field(default_factory=list, exclude=True)


class ProductPreviewRequest(BaseModel):
    product: str = Field(default="托特包")
    placement: str = Field(default="AI自動決定位置")
    display_style: str = Field(default="白色商品＋白底")
    preview_prompt: str = Field(default="", exclude=True)
    preview_size: str = Field(default="1024x1024")
    preview_quality: str = Field(default="medium")


class RegenerateRequest(BaseModel):
    instruction: str = Field(min_length=1)
    mode: Literal["elements", "palette", "same"] = "same"


class MotifRevisionResolution(BaseModel):
    """Design-only fields that the text model may change during a revision."""

    model_config = ConfigDict(extra="forbid")

    final_elements: list[str] = Field(default_factory=list, max_length=30)
    added_elements: list[str] = Field(default_factory=list, max_length=20)
    removed_elements: list[str] = Field(default_factory=list, max_length=20)
    excluded_elements: list[str] = Field(default_factory=list, max_length=20)
    changes_palette: bool = False
    palette_instruction: str = Field(default="", max_length=500)
    revision_summary: str = Field(min_length=1, max_length=500)


class ImageAsset(BaseModel):
    type: Literal["motif", "preview", "chart"]
    filename: str | None = None
    url: str | None = None
    saved: bool = False
    favorite: bool = False
    collection_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] | None = None
    width: int | None = None
    height: int | None = None


class ImageRecord(BaseModel):
    id: str
    filename: str
    url: str
    original_filename: str | None = None
    original_url: str | None = None
    created_at: str
    expires_at: str
    prompt: str
    revised_prompt: str | None = None
    request: dict[str, Any]
    palette_name: str | None = None
    totem_url: str | None = None
    totem_prompt: str | None = None
    score: float | None = None
    score_reason: str | None = None
    files: dict[str, Any] | None = None
    generation: dict[str, Any] | None = None
    palette: dict[str, Any] | None = None
    design_spec: dict[str, Any] | None = None
    assets: dict[str, ImageAsset] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    images: list[ImageRecord]


class GalleryAsset(BaseModel):
    record_id: str
    asset_type: Literal["motif", "preview", "chart"]
    url: str
    saved: bool = False
    favorite: bool = False
    collection_ids: list[str] = Field(default_factory=list)
    created_at: str
    expires_at: str
    elements: list[str] = Field(default_factory=list)
    width: int | None = None
    height: int | None = None


class AssetStateRequest(BaseModel):
    saved: bool | None = None
    favorite: bool | None = None
    parameters: dict[str, Any] | None = None


class CollectionRecord(BaseModel):
    id: str
    name: str
    system: bool = False
    image_count: int = 0
    preview_url: str | None = None
    preview_urls: list[str] = Field(default_factory=list)


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class AssetCollectionsRequest(BaseModel):
    collection_ids: list[str] = Field(default_factory=list)
