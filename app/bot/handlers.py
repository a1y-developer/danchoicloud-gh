import logging
from app.services.github import github_service
from app.services.ai import ai_service
from app.services.telegram import telegram_service
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_pr_opened_notification(payload: dict):
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    sender = payload.get("sender", {})

    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    # Notifications (To Group Chat)
    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) ✨ New PR Opened: [{pr.get('title')}]({pr.get('html_url')}) by @{sender.get('login')}",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_pr_opened_ai(payload: dict):
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})

    owner_name = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")
    pr_number = pr.get("number")

    logger.info(f"Processing AI for PR #{pr_number} in {owner_name}/{repo_name}")

    if not installation_id:
        logger.error("No installation ID found")
        return

    client = await github_service.get_client(installation_id)

    # AI Summary & Review
    try:
        diff = await github_service.get_pr_diff(
            client, owner_name, repo_name, pr_number
        )

        # Generate Summary
        summary = await ai_service.generate_pr_summary(diff)
        await github_service.post_comment(
            client, owner_name, repo_name, pr_number, f"## PR Summary\n\n{summary}"
        )

        # Generate Code Review

        # Generate Inline Suggestions (Simplified)

    except Exception as e:
        logger.error(f"Error in AI processing: {e}", exc_info=True)


async def handle_pr_review_requested(payload: dict):
    pr = payload.get("pull_request", {})
    requested_reviewer = payload.get("requested_reviewer", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) 🔍 Review Requested for @{requested_reviewer.get('login')} : [{pr.get('title')}]({pr.get('html_url')})",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_pr_assigned(payload: dict):
    pr = payload.get("pull_request", {})
    assignee = payload.get("assignee", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) 👤 @{assignee.get('login')} assigned to PR: [{pr.get('title')}]({pr.get('html_url')})",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_issue_opened(payload: dict):
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")
    sender = payload.get("sender", {})

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) 🚨 New Issue: [{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_issue_assigned(payload: dict):
    issue = payload.get("issue", {})
    assignee = payload.get("assignee", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) 🔨 @{assignee.get('login')} assigned to Issue: [{issue.get('title')}]({issue.get('html_url')})",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_issue_comment_created(payload: dict):
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    sender = payload.get("sender", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    # Check if it is a PR or Issue
    is_pr = "pull_request" in issue
    entity_type = "PR" if is_pr else "Issue"

    # Extract assignees
    assignees = issue.get("assignees", [])
    assignee_mentions = [
        f"@{a.get('login')}" for a in assignees if a.get("login") != sender.get("login")
    ]

    message = f"[{repo_full_name}]({repo_url}) 💬 New Comment on {entity_type}: [{issue.get('title')}]({comment.get('html_url')}) by @{sender.get('login')}"

    if assignee_mentions:
        message += f"\n\nCC: {', '.join(assignee_mentions)} please check!"

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            message,
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_pr_review_comment_created(payload: dict):
    pr = payload.get("pull_request", {})
    comment = payload.get("comment", {})
    sender = payload.get("sender", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    # Extract assignees
    assignees = pr.get("assignees", [])
    assignee_mentions = [
        f"@{a.get('login')}" for a in assignees if a.get("login") != sender.get("login")
    ]

    message = f"[{repo_full_name}]({repo_url}) 💬 New Code Review Comment on PR: [{pr.get('title')}]({comment.get('html_url')}) by @{sender.get('login')}"

    if assignee_mentions:
        message += f"\n\nCC: {', '.join(assignee_mentions)} please check!"

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            message,
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_pr_closed(payload: dict):
    pr = payload.get("pull_request", {})
    sender = payload.get("sender", {})
    merged = pr.get("merged", False)
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    if merged:
        action_text = "Merged"
        icon = "✅"
        user = pr.get("merged_by", {}).get("login", sender.get("login"))
    else:
        action_text = "Closed"
        icon = "❌"
        user = sender.get("login")

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) {icon} PR {action_text}: [{pr.get('title')}]({pr.get('html_url')}) by @{user}",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_issue_closed(payload: dict):
    issue = payload.get("issue", {})
    sender = payload.get("sender", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            f"[{repo_full_name}]({repo_url}) ✅ Issue Closed: [{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )
