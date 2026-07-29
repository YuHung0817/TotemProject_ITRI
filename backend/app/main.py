from datetime import datetime, timezone

import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.errors import safe_error_detail
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.models import ImageAsset, ImageRecord
from app.db.session import get_db
from app.services.storage_service import image_path

settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(
    title=settings.app_name, docs_url="/docs" if settings.app_env != "production" else None
)


@app.exception_handler(StarletteHTTPException)
async def localized_http_error(_request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": safe_error_detail(exc.status_code, exc.detail)},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def localized_validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "invalid_request",
                "message": "輸入內容有誤，請檢查後再試。",
            }
        },
    )


@app.exception_handler(Exception)
async def localized_unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled request error path=%s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "code": "server_error",
                "message": "系統暫時無法完成操作，請稍後再試。",
            }
        },
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
            return JSONResponse(
                status_code=403,
                content={
                    "detail": {
                        "code": "invalid_request_origin",
                        "message": "無法驗證請求來源。",
                    }
                },
            )
    return await call_next(request)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/generated/images/{storage_key}", include_in_schema=False)
def protected_image(
    storage_key: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> FileResponse:
    now = datetime.now(timezone.utc)
    asset = db.scalar(
        select(ImageAsset)
        .join(ImageRecord, ImageRecord.id == ImageAsset.image_record_id)
        .where(
            ImageAsset.storage_key == storage_key,
            ImageAsset.deleted_at.is_(None),
            ImageAsset.deletion_status == "active",
            ImageRecord.user_id == user.id,
            ImageRecord.deleted_at.is_(None),
            ImageRecord.expires_at > now,
        )
    )
    if asset is None:
        raise HTTPException(404, "Image not found")
    path = image_path(storage_key)
    if not path.is_file():
        raise HTTPException(404, "Image file not found")
    return FileResponse(path, media_type=asset.mime_type, headers={"Cache-Control": "private"})


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
