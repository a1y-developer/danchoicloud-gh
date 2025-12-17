import logging

from app.services.ai import ai_service
from app.services.cla import cla_service
from app.services.github import github_service
from app.services.notifications.manager import notification_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_pr_opened_notification(payload: dict):
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    sender = payload.get("sender", {})

    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : ✨ New PR Opened: "
        f"[{pr.get('title')}]({pr.get('html_url')}) by @{sender.get('login')}"
    )

    await notification_manager.broadcast_message(markdown_text)


async def handle_pr_opened_label_ai(payload: dict):
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    sender = payload.get("sender", {})

    if sender.get("type") == "Bot":
        logger.info("PR opened by a bot, skipping AI labeling")
        return

    owner_name = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")
    pr_number = pr.get("number")
    title = pr.get("title", "")
    body = pr.get("body", "") or ""

    logger.info(
        f"Processing AI labeling for PR #{pr_number} in {owner_name}/{repo_name}"
    )

    if not installation_id:
        logger.error("No installation ID found")
        return

    client = await github_service.get_client(installation_id)

    try:
        available_labels = await github_service.get_repo_labels(
            client, owner_name, repo_name
        )
        suggested_labels = await ai_service.suggest_labels(
            title, body, available_labels
        )
        if suggested_labels:
            await github_service.add_labels(
                client, owner_name, repo_name, pr_number, suggested_labels
            )
            logger.info(f"Added labels to PR #{pr_number}: {suggested_labels}")
    except Exception as e:
        logger.error(f"Error suggesting labels: {e}")


async def handle_pr_opened_ai(payload: dict):
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    sender = payload.get("sender", {})

    if sender.get("type") == "Bot":
        logger.info("PR opened by a bot, skipping AI processing")
        return

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

        # Note: GitHub comments use standard Markdown, not Telegram's MarkdownV2
        await github_service.post_comment(
            client, owner_name, repo_name, pr_number, f"## PR Summary\n\n{summary}"
        )

        # Generate Code Review

        # Generate Inline Suggestions (Simplified)

    except Exception as e:
        logger.error(f"Error in AI processing: {e}", exc_info=True)


async def handle_pr_cla_check(payload: dict):
    """Run CLA check for PR on open/synchronize or manual triggers."""
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        logger.error("No installation ID found for CLA check")
        return

    client = await github_service.get_client(installation_id)
    try:
        await cla_service.check_pr_cla(client, payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error while running CLA check: %s", exc, exc_info=True)


async def handle_pr_review_requested(payload: dict):
    pr = payload.get("pull_request", {})
    requested_reviewer = payload.get("requested_reviewer", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : 🔍 Review Requested for "
        f"@{requested_reviewer.get('login')} : [{pr.get('title')}]({pr.get('html_url')})"
    )

    await notification_manager.broadcast_message(markdown_text)


async def handle_pr_assigned(payload: dict):
    pr = payload.get("pull_request", {})
    assignee = payload.get("assignee", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : 👤 @{assignee.get('login')} "
        f"assigned to PR: [{pr.get('title')}]({pr.get('html_url')})"
    )

    await notification_manager.broadcast_message(markdown_text)


async def handle_issue_opened(payload: dict):
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")
    sender = payload.get("sender", {})

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : 🚨 New Issue: "
        f"[{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}"
    )

    await notification_manager.broadcast_message(markdown_text)


async def handle_issue_opened_ai(payload: dict):
    installation_id = payload.get("installation", {}).get("id")
    repo = payload.get("repository", {})
    issue = payload.get("issue", {})
    sender = payload.get("sender", {})

    if sender.get("type") == "Bot":
        return

    owner_name = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")
    issue_number = issue.get("number")
    title = issue.get("title", "")
    body = issue.get("body", "") or ""

    logger.info(f"Processing AI for Issue #{issue_number} in {owner_name}/{repo_name}")

    if not installation_id:
        logger.error("No installation ID found")
        return

    client = await github_service.get_client(installation_id)

    try:
        available_labels = await github_service.get_repo_labels(
            client, owner_name, repo_name
        )
        suggested_labels = await ai_service.suggest_labels(
            title, body, available_labels
        )
        if suggested_labels:
            await github_service.add_labels(
                client, owner_name, repo_name, issue_number, suggested_labels
            )
            logger.info(f"Added labels to Issue #{issue_number}: {suggested_labels}")
    except Exception as e:
        logger.error(f"Error in AI processing for Issue: {e}", exc_info=True)


async def handle_issue_assigned(payload: dict):
    issue = payload.get("issue", {})
    assignee = payload.get("assignee", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : 🔨 @{assignee.get('login')} "
        f"assigned to Issue: [{issue.get('title')}]({issue.get('html_url')})"
    )

    await notification_manager.broadcast_message(markdown_text)


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

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : 💬 New Comment on {entity_type}: "
        f"[{issue.get('title')}]({comment.get('html_url')}) by @{sender.get('login')}"
    )

    if assignee_mentions:
        markdown_text += f"\n\ncc: {', '.join(assignee_mentions)}"

    await notification_manager.broadcast_message(markdown_text)


async def handle_issue_comment_cla(payload: dict):
    """Handle CLA-related commands in issue/PR comments."""
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        logger.error("No installation ID found for CLA comment handler")
        return

    client = await github_service.get_client(installation_id)
    try:
        await cla_service.handle_sign_comment(client, payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Error while handling CLA sign/recheck comment: %s", exc, exc_info=True
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

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : {icon} PR {action_text}: "
        f"[{pr.get('title')}]({pr.get('html_url')}) by @{user}"
    )

    if assignee_mentions:
        markdown_text += f"\n\ncc: {', '.join(assignee_mentions)}"

    await notification_manager.broadcast_message(markdown_text)


async def handle_issue_closed(payload: dict):
    issue = payload.get("issue", {})
    sender = payload.get("sender", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name")
    repo_url = repo.get("html_url")

    assignees = issue.get("assignees", [])
    assignee_mentions = [
        f"@{a.get('login')}" for a in assignees if a.get("login") != sender.get("login")
    ]

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : ✅ Issue Closed: "
        f"[{issue.get('title')}]({issue.get('html_url')}) by @{sender.get('login')}"
    )

    if assignee_mentions:
        markdown_text += f"\n\ncc: {', '.join(assignee_mentions)}"

    await notification_manager.broadcast_message(markdown_text)


async def handle_pr_closed_cla(payload: dict):
    """Lock PR after merge if CLA is satisfied and locking is enabled."""
    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        logger.error("No installation ID found for CLA merge handler")
        return

    client = await github_service.get_client(installation_id)
    try:
        await cla_service.handle_pr_merged(client, payload)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Error while handling CLA post-merge hook: %s", exc, exc_info=True)


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

    markdown_text = (
        f"**[{repo_full_name}]({repo_url})** : {icon} PR {action_text}: "
        f"[{pr.get('title')}]({review.get('html_url')}) by @{sender.get('login')}"
    )

    if body:
        markdown_text += f'\n\n"{body}"'

    if assignee_mentions:
        markdown_text += f"\n\ncc: {', '.join(assignee_mentions)}"

    await notification_manager.broadcast_message(markdown_text)


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
    actor = workflow_run.get("actor", {})
    actor_login = actor.get("login", "Unknown")
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

        markdown_text = (
            f"**[{repo_full_name}]({repo_url})** : ❌ Workflow Failed: "
            f"[{workflow_name}]({workflow_url})\n\n"
        )

        markdown_text += "**Jobs:**\n"

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

            markdown_text += (
                f"{icon} [{job_name}]({job_url}) - {job_status} ({duration})\n"
            )

            if actor_login != "Unknown":
                markdown_text += f"cc: @{actor_login} please check this job!\n"

        await notification_manager.broadcast_message(markdown_text)
    except Exception as e:
        logger.error(f"Error handling workflow run: {e}", exc_info=True)
