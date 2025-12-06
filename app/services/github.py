import logging
import asyncio
from typing import List, Optional, Tuple

from github import Github, Auth, GithubIntegration
from github.GithubException import GithubException

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """Thin async wrapper around PyGithub.

    All heavy operations are executed in a thread pool via asyncio.to_thread.
    """

    async def get_client(self, installation_id: int) -> Github:
        return await asyncio.to_thread(self._get_client_sync, installation_id)

    def _get_client_sync(self, installation_id: int) -> Github:
        private_key = settings.GITHUB_PRIVATE_KEY.replace("\\n", "\n")

        auth = Auth.AppAuth(
            app_id=settings.GITHUB_APP_ID,
            private_key=private_key,
        )
        gi = GithubIntegration(auth=auth)
        return gi.get_github_for_installation(installation_id)

    async def get_repo(self, client: Github, full_name: str):
        return await asyncio.to_thread(self._get_repo_sync, client, full_name)

    def _get_repo_sync(self, client: Github, full_name: str):
        return client.get_repo(full_name)

    # ------------------------------------------------------------------
    # PR helpers
    # ------------------------------------------------------------------
    async def get_pr_diff(
        self, client: Github, owner: str, repo: str, pull_number: int
    ) -> str:
        return await asyncio.to_thread(
            self._get_diff_sync, client, owner, repo, pull_number
        )

    def _get_diff_sync(
        self, client: Github, owner: str, repo: str, pull_number: int
    ) -> str:
        repo_obj = client.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(pull_number)
        # Request the diff specifically
        headers = {"Accept": "application/vnd.github.v3.diff"}
        # Access internal requester to send custom headers with the existing auth
        # This avoids needing to manually handle tokens for a raw request
        status, headers, data = client._Github__requester.requestBlob(
            "GET", pr.url, headers=headers
        )

        logger.info(
            f"Diff retrieved for {owner}/{repo}#{pull_number}. Type: {type(data)}"
        )

        if isinstance(data, bytes):
            return data.decode("utf-8")
        return data

    async def get_pr_commits(
        self, client: Github, owner: str, repo: str, pull_number: int
    ):
        return await asyncio.to_thread(
            self._get_pr_commits_sync, client, owner, repo, pull_number
        )

    def _get_pr_commits_sync(
        self, client: Github, owner: str, repo: str, pull_number: int
    ):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(pull_number)
        return list(pr.get_commits())

    async def get_pr_head_sha(
        self, client: Github, owner: str, repo: str, pull_number: int
    ) -> str:
        return await asyncio.to_thread(
            self._get_pr_head_sha_sync, client, owner, repo, pull_number
        )

    def _get_pr_head_sha_sync(
        self, client: Github, owner: str, repo: str, pull_number: int
    ) -> str:
        repo_obj = client.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(pull_number)
        return pr.head.sha

    async def post_comment(
        self, client: Github, owner: str, repo: str, issue_number: int, body: str
    ):
        await asyncio.to_thread(
            self._post_comment_sync, client, owner, repo, issue_number, body
        )

    def _post_comment_sync(
        self, client: Github, owner: str, repo: str, issue_number: int, body: str
    ):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(issue_number)
        issue.create_comment(body)

    async def get_workflow_jobs(
        self, client: Github, owner: str, repo: str, run_id: int
    ):
        return await asyncio.to_thread(
            self._get_workflow_jobs_sync, client, owner, repo, run_id
        )

    def _get_workflow_jobs_sync(
        self, client: Github, owner: str, repo: str, run_id: int
    ):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        run = repo_obj.get_workflow_run(run_id)
        return list(run.jobs())

    async def add_labels(
        self,
        client: Github,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str],
    ):
        await asyncio.to_thread(
            self._add_labels_sync, client, owner, repo, issue_number, labels
        )

    def _add_labels_sync(
        self,
        client: Github,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str],
    ):
        if not labels:
            return
        repo_obj = client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(issue_number)
        issue.add_to_labels(*labels)

    async def get_repo_labels(self, client: Github, owner: str, repo: str) -> List[str]:
        return await asyncio.to_thread(self._get_repo_labels_sync, client, owner, repo)

    def _get_repo_labels_sync(self, client: Github, owner: str, repo: str) -> List[str]:
        repo_obj = client.get_repo(f"{owner}/{repo}")
        return [label.name for label in repo_obj.get_labels()]

    async def get_file_content(
        self,
        client: Github,
        repo_full_name: str,
        path: str,
        branch: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (content, sha) for a file or (None, None) if it does not exist."""
        return await asyncio.to_thread(
            self._get_file_content_sync,
            client,
            repo_full_name,
            path,
            branch,
        )

    def _get_file_content_sync(
        self,
        client: Github,
        repo_full_name: str,
        path: str,
        branch: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        # NOTE:
        # For GitHub Apps, a 404 here can also mean "no access to this repo",
        # not just "repo does not exist".
        try:
            repo = client.get_repo(repo_full_name)
        except GithubException as exc:  # type: ignore[no-untyped-call]
            # Treat "repo not found / not accessible" the same way as
            # "file not found" for callers that just want a yes/no answer.
            if exc.status == 404:
                logger.warning(
                    "GitHub repo not accessible: %s (404). Data: %s",
                    repo_full_name,
                    getattr(exc, "data", None),
                )
                return None, None

            # For anything else (401, 403, 500, ...), bubble up with context.
            logger.error(
                "Error loading GitHub repo %s: %s (status=%s, data=%s)",
                repo_full_name,
                exc,
                getattr(exc, "status", None),
                getattr(exc, "data", None),
            )
            raise

        try:
            file = repo.get_contents(path, ref=branch)
        except GithubException as exc:  # type: ignore[no-untyped-call]
            if exc.status == 404:
                return None, None
            raise

        try:
            content = file.decoded_content.decode("utf-8")
        except Exception:  # pragma: no cover - very unlikely
            content = file.decoded_content

        return content, file.sha

    async def upsert_file(
        self,
        client: Github,
        repo_full_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ):
        await asyncio.to_thread(
            self._upsert_file_sync,
            client,
            repo_full_name,
            path,
            content,
            message,
            branch,
        )

    def _upsert_file_sync(
        self,
        client: Github,
        repo_full_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ):
        repo = client.get_repo(repo_full_name)
        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(
                path,
                message,
                content,
                existing.sha,
                branch=branch,
            )
        except GithubException as exc:  # type: ignore[no-untyped-call]
            if exc.status != 404:
                raise
            repo.create_file(
                path,
                message,
                content,
                branch=branch,
            )

    async def create_commit_status(
        self,
        client: Github,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str,
        target_url: Optional[str] = None,
    ):
        await asyncio.to_thread(
            self._create_commit_status_sync,
            client,
            owner,
            repo,
            sha,
            state,
            description,
            context,
            target_url,
        )

    def _create_commit_status_sync(
        self,
        client: Github,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str,
        target_url: Optional[str] = None,
    ):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        commit = repo_obj.get_commit(sha)
        commit.create_status(
            state=state,
            target_url=target_url,
            description=description,
            context=context,
        )

    async def lock_issue(
        self,
        client: Github,
        owner: str,
        repo: str,
        issue_number: int,
        reason: Optional[str] = None,
    ):
        await asyncio.to_thread(
            self._lock_issue_sync,
            client,
            owner,
            repo,
            issue_number,
            reason,
        )

    def _lock_issue_sync(
        self,
        client: Github,
        owner: str,
        repo: str,
        issue_number: int,
        reason: Optional[str] = None,
    ):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(number=issue_number)
        try:
            lock_reason = reason or "resolved"
            issue.lock(lock_reason)
        except TypeError:
            issue.lock()


github_service = GitHubService()
