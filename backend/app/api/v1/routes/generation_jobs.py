from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.generation_job import GenerationJobResponse
from app.services.generation_job_service import generation_job_response

router = APIRouter(prefix="/generation-jobs")


@router.get("/{job_id}", response_model=GenerationJobResponse)
def get_generation_job(
    job_id: str, user: CurrentUser, db: Session = Depends(get_db)
) -> GenerationJobResponse:
    return generation_job_response(db, job_id, user.id)
