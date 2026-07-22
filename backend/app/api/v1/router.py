from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.chatrooms import router as chatrooms_router
from app.api.v1.routes.generation_jobs import router as generation_jobs_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.images import router as images_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(chatrooms_router, tags=["chatrooms"])
api_router.include_router(generation_jobs_router, tags=["generation-jobs"])
api_router.include_router(images_router, tags=["images"])
