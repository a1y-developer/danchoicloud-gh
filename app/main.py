from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router
from app.api.settings import router as settings_router
from app.api.webhook import router as webhook_router
from app.core.config import settings
from app.db.session import init_db
from app.services.notifications.manager import notification_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize resources on startup
    init_db()
    yield
    # Cleanup resources on shutdown
    await notification_manager.close()


app = FastAPI(title="Danchoicloud GitHub App", lifespan=lifespan)

allowed_origins = [settings.WEB_BASE_URL]
if settings.EXTRA_CORS_ORIGINS:
    allowed_origins.extend(
        [
            origin.strip()
            for origin in settings.EXTRA_CORS_ORIGINS.split(",")
            if origin.strip()
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Hello from Danchoicloud GitHub App"}
