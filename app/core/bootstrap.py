from sqlalchemy import select

from app.core.auth import hash_password
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User


def ensure_admin_user() -> None:
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        return
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == settings.admin_email))
        if user:
            if not user.is_admin:
                user.is_admin = True
                db.commit()
            return
        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            is_admin=True,
        )
        db.add(admin)
        db.commit()
