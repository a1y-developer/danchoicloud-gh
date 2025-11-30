from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize resources on startup
    yield
    # Cleanup resources on shutdown


app = FastAPI(title="Danchoicloud GitHub App", lifespan=lifespan)

app.include_router(webhook_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Hello from Danchoicloud GitHub App"}
