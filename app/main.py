from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.api import admin, auth, jobs, metrics, queue
from app.core.bootstrap import ensure_admin_user
from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_admin_user()
    yield


limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(queue.router, prefix=settings.api_prefix)
app.include_router(metrics.router, prefix=settings.api_prefix)
