import hashlib
import hmac
import logging
from fastapi import APIRouter, Request, BackgroundTasks, Header, HTTPException
from app.core.config import settings
from app.bot.dispatcher import handle_event

router = APIRouter()
logger = logging.getLogger(__name__)

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not signature.startswith("sha256="):
        logger.error("Signature does not start with sha256=")
        return False
    
    if not secret:
        logger.error("GITHUB_WEBHOOK_SECRET is not set")
        return False

    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    expected_signature = f"sha256={mac.hexdigest()}"
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.error(f"Signature mismatch. Expected: {expected_signature}, Got: {signature}")
        return False
        
    return True

@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(...)
):
    payload = await request.body()
    
    if not verify_signature(payload, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    background_tasks.add_task(handle_event, x_github_event, payload)
    return {"status": "ok"}
