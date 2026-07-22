from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.models import ImageAsset, ImageRecord
from app.db.session import get_db
from app.services.storage_service import image_path

settings = get_settings()
app = FastAPI(
    title=settings.app_name, docs_url="/docs" if settings.app_env != "production" else None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def validate_mutation_origin(request: Request, call_next):
    if (
        settings.app_env == "production"
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path.startswith(settings.api_v1_prefix)
    ):
        origin = request.headers.get("origin")
        if origin not in settings.cors_origin_list:
            return JSONResponse(status_code=403, content={"detail": "Invalid request origin"})
    return await call_next(request)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/generated/images/{storage_key}", include_in_schema=False)
def protected_image(
    storage_key: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> FileResponse:
    asset = db.scalar(
        select(ImageAsset)
        .join(ImageRecord, ImageRecord.id == ImageAsset.image_record_id)
        .where(
            ImageAsset.storage_key == storage_key,
            ImageAsset.deleted_at.is_(None),
            ImageAsset.deletion_status == "active",
            ImageRecord.user_id == user.id,
            ImageRecord.deleted_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    if asset is None:
        raise HTTPException(404, "Image not found")
    expiry = asset.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise HTTPException(404, "Image not found")
    path = image_path(storage_key)
    if not path.is_file():
        raise HTTPException(404, "Image file not found")
    return FileResponse(path, media_type=asset.mime_type, headers={"Cache-Control": "private"})


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
