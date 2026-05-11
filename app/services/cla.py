import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from github import Github

from app.core.config import settings
from app.services.github import github_service

logger = logging.getLogger(__name__)


class CLAService:
    """Service implementing CLA Assistant logic for the GitHub App.

    Behaviour is inspired by contributor-assistant/github-action:
    - tracks contributors who have signed the CLA in a JSON file
    - checks all contributors on a PR
    - posts a status check and PR comments
    - can lock the PR once merged and everyone has signed
    """

    STATUS_CONTEXT = "cla/a1y"
    STATUS_COMMENT_MARKER = "<!-- a1y-cla-status -->"

    async def check_pr_cla(self, client: Github, payload: Dict) -> None:
        """Check CLA status for a PR on open/synchronize or manual recheck."""
        if not self._is_enabled():
            return

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})

        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        pr_number = pr.get("number")

        if not (owner and name and pr_number):
            logger.error("Missing owner/name/pr_number in payload for CLA check")
            return

        installation_id = payload.get("installation", {}).get("id")
        if not installation_id:
            logger.error("No installation ID in payload for CLA check")
            return

        logger.info("Running CLA check for PR #%s in %s/%s", pr_number, owner, name)

        # Collect contributors from PR commits
        contributors = await self._get_pr_contributors(client, owner, name, pr_number)

        # Compute who has / hasn't signed
        signatures_repo = settings.CLA_SIGNATURES_REPO or f"{owner}/{name}"
        signatures_data, signed_users = await self._load_signatures(
            client, signatures_repo
        )

        unsigned = sorted(self._get_unsigned(contributors, signed_users))

        # Update status check on the head commit
        head_sha = await github_service.get_pr_head_sha(client, owner, name, pr_number)

        if unsigned:
            description = "CLA missing for: " + ", ".join(f"@{u}" for u in unsigned)
            state = "failure"
        else:
            description = "All contributors have signed the CLA."
            state = "success"

        await github_service.create_commit_status(
            client,
            owner,
            name,
            head_sha,
            state=state,
            description=description[:140],
            context=self.STATUS_CONTEXT,
            target_url=settings.CLA_DOCUMENT_URL,
        )

        # Post a comment summarising the state
        await self._comment_pr_status(
            client,
            owner,
            name,
            pr_number,
            unsigned=unsigned,
        )

        # Persist signatures_data unchanged – this method does not modify it
        # (signatures are added only when a contributor explicitly comments).

    async def handle_sign_comment(self, client: Github, payload: Dict) -> None:
        """Handle a comment that may sign the CLA or request recheck."""
        if not self._is_enabled():
            return

        comment = payload.get("comment", {})
        body: str = comment.get("body") or ""
        body_lower = body.lower()

        repo = payload.get("repository", {})
        issue = payload.get("issue", {})
        sender = payload.get("sender", {})

        # Work only on PR comments
        if "pull_request" not in issue:
            return

        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        pr_number = issue.get("number")
        commenter = sender.get("login")

        if not (owner and name and pr_number and commenter):
            logger.error("Missing data in payload for CLA comment handler")
            return

        installation_id = payload.get("installation", {}).get("id")
        if not installation_id:
            logger.error("No installation ID in payload for CLA comment handler")
            return

        sign_phrase = (settings.CLA_SIGN_PHRASE or "").lower()
        recheck_phrase = (settings.CLA_RECHECK_PHRASE or "").lower()

        wants_sign = sign_phrase and sign_phrase in body_lower
        wants_recheck = recheck_phrase and recheck_phrase in body_lower

        if not wants_sign and not wants_recheck:
            return

        logger.info(
            "Processing CLA comment on PR #%s in %s/%s by @%s " "(sign=%s, recheck=%s)",
            pr_number,
            owner,
            name,
            commenter,
            wants_sign,
            wants_recheck,
        )

        signatures_repo = settings.CLA_SIGNATURES_REPO or f"{owner}/{name}"

        signatures_data, signed_users = await self._load_signatures(
            client, signatures_repo
        )

        updated = False

        if wants_sign:
            if commenter in signed_users:
                logger.info("User @%s already signed CLA, skipping update", commenter)
            else:
                signatures_data = self._append_signature(
                    signatures_data,
                    commenter,
                    pr_number,
                    user_id=sender.get("id"),
                    comment_id=comment.get("id"),
                    created_at=comment.get("created_at"),
                    repo_id=repo.get("id"),
                )
                commit_message = (
                    f"@{commenter} has signed the CLA in " f"{owner}/{name}#{pr_number}"
                )
                await self._save_signatures(
                    client,
                    signatures_repo,
                    signatures_data,
                    commit_message,
                )
                updated = True

        if wants_recheck or updated:
            # Re-run the full check to refresh status + comments
            await self.check_pr_cla(client, self._build_pr_payload_stub(payload))

    async def handle_pr_merged(self, client: Github, payload: Dict) -> None:
        """Lock PR after merge if everyone has signed and config allows it."""
        if not self._is_enabled() or not settings.CLA_LOCK_AFTER_MERGE:
            return

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})

        if not pr.get("merged"):
            return

        owner = repo.get("owner", {}).get("login")
        name = repo.get("name")
        pr_number = pr.get("number")

        if not (owner and name and pr_number):
            logger.error("Missing owner/name/pr_number in payload for CLA merge hook")
            return

        installation_id = payload.get("installation", {}).get("id")
        if not installation_id:
            logger.error("No installation ID in payload for CLA merge hook")
            return

        logger.info(
            "Handling CLA post-merge for PR #%s in %s/%s", pr_number, owner, name
        )

        contributors = await self._get_pr_contributors(client, owner, name, pr_number)
        signatures_repo = settings.CLA_SIGNATURES_REPO or f"{owner}/{name}"
        _, signed_users = await self._load_signatures(client, signatures_repo)

        unsigned = self._get_unsigned(contributors, signed_users)
        if unsigned:
            logger.info(
                "Not locking PR #%s because these users have not signed: %s",
                pr_number,
                ", ".join(unsigned),
            )
            return

        # Everyone has signed – lock the PR conversation
        await github_service.lock_issue(
            client,
            owner,
            name,
            pr_number,
            reason="resolved",
        )

    def _is_enabled(self) -> bool:
        if not settings.CLA_ENABLED:
            return False
        if not settings.CLA_DOCUMENT_URL:
            logger.warning("CLA_DOCUMENT_URL is not set – disabling CLA checks")
            return False
        return True

    def _get_allowlist(self) -> Set[str]:
        raw = settings.CLA_ALLOWLIST or ""
        return {item.strip() for item in raw.split(",") if item.strip()}

    def _get_ai_agent_allowlist(self) -> Set[str]:
        raw = settings.CLA_AI_AGENT_ALLOWLIST or ""
        return {item.strip() for item in raw.split(",") if item.strip()}

    async def _get_pr_contributors(
        self,
        client: Github,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> Set[str]:
        allowlist = self._get_allowlist() | self._get_ai_agent_allowlist()
        commits = await github_service.get_pr_commits(client, owner, repo, pr_number)

        contributors: Set[str] = set()
        for commit in commits:
            author = getattr(commit, "author", None)
            committer = getattr(commit, "committer", None)

            for user in (author, committer):
                if not user:
                    continue
                login = getattr(user, "login", None)
                if not login:
                    continue
                if login in allowlist:
                    continue
                if getattr(user, "type", None) == "Bot":
                    continue
                contributors.add(login)

        return contributors

    async def _load_signatures(
        self,
        client: Github,
        signatures_repo: str,
    ) -> Tuple[Dict, Set[str]]:
        path = settings.CLA_SIGNATURES_PATH
        branch = settings.CLA_SIGNATURES_BRANCH

        content, _sha = await github_service.get_file_content(
            client,
            signatures_repo,
            path,
            branch,
        )

        if not content:
            logger.info(
                "No CLA signatures file found at %s@%s:%s – starting fresh",
                signatures_repo,
                branch,
                path,
            )
            data: Dict = {}
        else:
            try:
                data = json.loads(content)
                if not isinstance(data, dict):
                    logger.warning(
                        "Unexpected CLA signatures format (not a JSON object); "
                        "resetting to empty dict for new writes."
                    )
                    data = {}
            except json.JSONDecodeError:
                logger.exception(
                    "Failed to parse CLA signatures JSON; using empty dict"
                )
                data = {}

        signed_users = self._extract_signed_users(data)
        return data, signed_users

    async def _save_signatures(
        self,
        client: Github,
        signatures_repo: str,
        data: Dict,
        commit_message: str,
    ) -> None:
        path = settings.CLA_SIGNATURES_PATH
        branch = settings.CLA_SIGNATURES_BRANCH

        content = json.dumps(data, indent=2, sort_keys=True)

        await github_service.upsert_file(
            client,
            signatures_repo,
            path,
            content,
            commit_message,
            branch,
        )

    def _extract_signed_users(self, data: Dict) -> Set[str]:
        """Extract the set of GitHub usernames who have signed the CLA.

        Supports both this app's native format and the classic
        CLA Assistant format with `signedContributors`.
        """
        signed: Set[str] = set()

        # 1) Native "signatures" format used by this app
        entries = data.get("signatures")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                user = (
                    entry.get("user")
                    or entry.get("name")
                    or entry.get("githubId")
                    or entry.get("github_id")
                )
                if user:
                    signed.add(str(user))

        # 2) Classic CLA Assistant format: "signedContributors"
        value = data.get("signedContributors")
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    signed.add(item)
                elif isinstance(item, dict):
                    user = (
                        item.get("name")
                        or item.get("user")
                        or item.get("githubId")
                        or item.get("github_id")
                    )
                    if user:
                        signed.add(str(user))

        # 3) Generic "users": ["login1", "login2", ...]
        users_value = data.get("users")
        if isinstance(users_value, list):
            for item in users_value:
                if isinstance(item, str):
                    signed.add(item)

        return signed

    def _append_signature(
        self,
        data: Dict,
        username: str,
        pr_number: int,
        *,
        user_id: Optional[int] = None,
        comment_id: Optional[int] = None,
        created_at: Optional[str] = None,
        repo_id: Optional[int] = None,
    ) -> Dict:
        if not isinstance(data, dict):
            data = {}

        entries = data.get("signedContributors")
        if not isinstance(entries, list):
            entries = []

        # Avoid duplicate entries for the same user
        if any(
            (isinstance(entry, dict) and entry.get("name") == username)
            or entry == username
            for entry in entries
        ):
            data["signedContributors"] = entries
            return data

        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "name": username,
            "id": user_id or 0,
            "comment_id": comment_id or 0,
            "created_at": created_at or now,
            "repoId": repo_id or 0,
            "pullRequestNo": pr_number,
        }

        entries.append(entry)
        data["signedContributors"] = entries
        return data

    def _get_unsigned(
        self,
        contributors: Set[str],
        signed_users: Set[str],
    ) -> Set[str]:
        return set(contributors) - set(signed_users)

    async def _comment_pr_status(
        self,
        client: Github,
        owner: str,
        repo: str,
        pr_number: int,
        unsigned: List[str],
    ) -> None:
        # Locate existing CLA status comment (if any) via hidden marker
        repo_obj = client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(pr_number)

        existing_status_comment = None
        try:
            for comment in issue.get_comments():
                body: str = getattr(comment, "body", "") or ""
                if self.STATUS_COMMENT_MARKER in body:
                    existing_status_comment = comment
                    break
        except Exception:  # pragma: no cover - defensive around API quirks
            existing_status_comment = None

        if unsigned:
            users_str = ", ".join(f"@{u}" for u in unsigned)
            core_body = (
                "Thank you for your contribution! Before we can merge this pull "
                "request, all contributors need to sign our Contributor License "
                f"Agreement (CLA).\n\n"
                f"Users pending signature: {users_str}\n\n"
                f"Please read the CLA document here: {settings.CLA_DOCUMENT_URL}\n\n"
                f"To sign, comment the following phrase exactly:\n\n"
                f"> {settings.CLA_SIGN_PHRASE}\n\n"
                f"If you've already signed or after signing, you can comment "
                f"`{settings.CLA_RECHECK_PHRASE}` to trigger a re-check."
            )
            body = f"{self.STATUS_COMMENT_MARKER}\n\n{core_body}"

            if existing_status_comment:
                existing_status_comment.edit(body)
            else:
                issue.create_comment(body)
        else:
            # Everyone has signed. If we previously posted a status comment,
            # update it to a simple thank-you message. Do not create a new
            # comment if none existed.
            if not existing_status_comment:
                return

            core_body = (
                "All contributors have signed the CLA. Thank you! ✅\n\n"
                f"Reference: {settings.CLA_DOCUMENT_URL}"
            )
            body = f"{self.STATUS_COMMENT_MARKER}\n\n{core_body}"
            existing_status_comment.edit(body)

    def _build_pr_payload_stub(self, original_payload: Dict) -> Dict:
        """Build a minimal PR-like payload for re-use in check_pr_cla."""
        repo = original_payload.get("repository", {})
        issue = original_payload.get("issue", {})
        installation = original_payload.get("installation", {})

        pr_stub = {
            "number": issue.get("number"),
            "head": {
                # head SHA will be resolved again by check_pr_cla
            },
        }

        return {
            "pull_request": pr_stub,
            "repository": repo,
            "installation": installation,
        }


cla_service = CLAService()
