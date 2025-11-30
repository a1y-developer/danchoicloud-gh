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
            f"[`{repo_full_name}`]({repo_url}): ✨ New PR Opened: [{pr.get('title')}]({pr.get('html_url')}) by @{sender.get('login')}",
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
            f"[`{repo_full_name}`]({repo_url}): 🔍 Review Requested for @{requested_reviewer.get('login')} : [{pr.get('title')}]({pr.get('html_url')})",
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
            f"[`{repo_full_name}`]({repo_url}): 👤 @{assignee.get('login')} assigned to PR: [{pr.get('title')}]({pr.get('html_url')})",
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
            f"[`{repo_full_name}`]({repo_url}): 🚨 New Issue: [{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}",
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
            f"[`{repo_full_name}`]({repo_url}): 🔨 @{assignee.get('login')} assigned to Issue: [{issue.get('title')}]({issue.get('html_url')})",
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

    message = f"[`{repo_full_name}`]({repo_url}): 💬 New Comment on {entity_type}: [{issue.get('title')}]({comment.get('html_url')}) by @{sender.get('login')}"

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

    # Extract assignees
    assignees = pr.get("assignees", [])
    assignee_mentions = [
        f"@{a.get('login')}" for a in assignees if a.get("login") != user
    ]

    message = f"[`{repo_full_name}`]({repo_url}): {icon} PR {action_text}: [{pr.get('title')}]({pr.get('html_url')}) by @{user}"

    if assignee_mentions:
        message += f"\n\nCC: {', '.join(assignee_mentions)}"

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            message,
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
            f"[`{repo_full_name}`]({repo_url}): ✅ Issue Closed: [{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}",
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_pr_review_submitted(payload: dict):
    pr = payload.get("pull_request", {})
    review = payload.get("review", {})
    sender = payload.get("sender", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    state = review.get("state")

    if state == "approved":
        action_text = "Approved"
        icon = "✅"
    elif state == "changes_requested":
        action_text = "Changes Requested"
        icon = "🚫"
    elif state == "commented":
        action_text = "Commented"
        icon = "💬"
    else:
        return

    # Extract assignees
    assignees = pr.get("assignees", [])
    assignee_mentions = [
        f"@{a.get('login')}" for a in assignees if a.get("login") != sender.get("login")
    ]

    # Review body (optional)
    body = review.get("body")

    message = f"[`{repo_full_name}`]({repo_url}): {icon} PR {action_text}: [{pr.get('title')}]({review.get('html_url')}) by @{sender.get('login')}"

    if body:
        message += f'\n\n"{body}"'

    if assignee_mentions:
        message += f"\n\nCC: {', '.join(assignee_mentions)} please check!"

    if settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            settings.TELEGRAM_CHAT_ID,
            message,
            message_thread_id=settings.TELEGRAM_THREAD_ID,
        )


async def handle_workflow_run(payload: dict):
    workflow_run = payload.get("workflow_run", {})
    repo = payload.get("repository", {})
    installation_id = payload.get("installation", {}).get("id")

    conclusion = workflow_run.get("conclusion")
    if conclusion == "success":
        logger.info("Workflow run succeeded, skipping notification")
        return

    workflow_name = workflow_run.get("name")
    workflow_url = workflow_run.get("html_url")
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")
    run_id = workflow_run.get("id")
    owner_name = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")

    if not installation_id:
        logger.error("No installation ID found for workflow_run")
        return

    try:
        client = await github_service.get_client(installation_id)
        jobs = await github_service.get_workflow_jobs(
            client, owner_name, repo_name, run_id
        )

        message = f"[`{repo_full_name}`]({repo_url}): ❌ Workflow Failed: [{workflow_name}]({workflow_url})\n\n"

        message += "*Jobs:*\n"

        for job in jobs:
            job_name = job.name
            job_status = job.conclusion if job.conclusion else job.status
            job_url = job.html_url

            # Calculate duration
            duration = "N/A"
            if job.started_at and job.completed_at:
                delta = job.completed_at - job.started_at
                total_seconds = int(delta.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                duration_parts = []
                if hours > 0:
                    duration_parts.append(f"{hours}h")
                if minutes > 0:
                    duration_parts.append(f"{minutes}m")
                if seconds > 0 or not duration_parts:
                    duration_parts.append(f"{seconds}s")

                duration = " ".join(duration_parts)

            icon = (
                "✅"
                if job_status == "success"
                else "❌" if job_status == "failure" else "⚠️"
            )

            message += f"{icon} [{job_name}]({job_url}) - {job_status} ({duration})\n"

        if settings.TELEGRAM_CHAT_ID:
            await telegram_service.send_message(
                settings.TELEGRAM_CHAT_ID,
                message,
                message_thread_id=settings.TELEGRAM_THREAD_ID,
            )
    except Exception as e:
        logger.error(f"Error handling workflow run: {e}", exc_info=True)
