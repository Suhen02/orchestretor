from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import JobRead


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[JobRead])
def list_all_jobs(db: Session = Depends(get_db), admin=Depends(get_current_admin)) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.created_at.desc())).all())
