import json
import logging
from app.bot import handlers

logger = logging.getLogger(__name__)


async def handle_event(event_name: str, payload_bytes: bytes):
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.error("Failed to decode webhook payload")
        return

    logger.info(f"Received event: {event_name}, action: {payload.get('action')}")

    if event_name == "ping":
        logger.info("Ping event received")
        return

    if event_name == "pull_request":
        action = payload.get("action")
        if action == "opened":
            await handlers.handle_pr_opened_notification(payload)
            await handlers.handle_pr_opened_ai(payload)
            await handlers.handle_pr_opened_label_ai(payload)
            await handlers.handle_pr_cla_check(payload)
        elif action == "synchronize":
            await handlers.handle_pr_cla_check(payload)
        elif action == "review_requested":
            await handlers.handle_pr_review_requested(payload)
        elif action == "assigned":
            await handlers.handle_pr_assigned(payload)
        elif action == "closed":
            await handlers.handle_pr_closed(payload)
            await handlers.handle_pr_closed_cla(payload)

    elif event_name == "issues":
        action = payload.get("action")
        if action == "opened":
            await handlers.handle_issue_opened(payload)
            await handlers.handle_issue_opened_ai(payload)
        elif action == "assigned":
            await handlers.handle_issue_assigned(payload)
        elif action == "closed":
            await handlers.handle_issue_closed(payload)

    elif event_name == "issue_comment":
        action = payload.get("action")
        if action == "created":
            await handlers.handle_issue_comment_created(payload)
            await handlers.handle_issue_comment_cla(payload)

    elif event_name == "pull_request_review":
        action = payload.get("action")
        if action == "submitted":
            await handlers.handle_pr_review_submitted(payload)

    elif event_name == "workflow_run":
        action = payload.get("action")
        if action == "completed":
            await handlers.handle_workflow_run(payload)
