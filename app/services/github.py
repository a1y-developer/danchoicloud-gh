import logging
import asyncio
from typing import List
from github import Github, Auth, GithubIntegration
from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubService:
    async def get_client(self, installation_id: int) -> Github:
        return await asyncio.to_thread(self._get_client_sync, installation_id)

    def _get_client_sync(self, installation_id: int) -> Github:
        # Handle potentially escaped newlines in the private key from env vars
        private_key = settings.GITHUB_PRIVATE_KEY.replace('\\n', '\n')
        
        auth = Auth.AppAuth(
            app_id=settings.GITHUB_APP_ID,
            private_key=private_key,
        )
        gi = GithubIntegration(auth=auth)
        return gi.get_github_for_installation(installation_id)

    async def get_pr_diff(self, client: Github, owner: str, repo: str, pull_number: int) -> str:
        return await asyncio.to_thread(self._get_diff_sync, client, owner, repo, pull_number)

    def _get_diff_sync(self, client: Github, owner: str, repo: str, pull_number: int) -> str:
        repo_obj = client.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(pull_number)
        # Request the diff specifically
        headers = {"Accept": "application/vnd.github.v3.diff"}
        # Access internal requester to send custom headers with the existing auth
        # This avoids needing to manually handle tokens for a raw request
        status, headers, data = client._Github__requester.requestBlob(
            "GET", pr.url, headers=headers
        )
        
        logger.info(f"Diff retrieved for {owner}/{repo}#{pull_number}. Type: {type(data)}")
        
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return data

    async def post_comment(self, client: Github, owner: str, repo: str, issue_number: int, body: str):
        await asyncio.to_thread(self._post_comment_sync, client, owner, repo, issue_number, body)

    def _post_comment_sync(self, client: Github, owner: str, repo: str, issue_number: int, body: str):
        repo_obj = client.get_repo(f"{owner}/{repo}")
        issue = repo_obj.get_issue(issue_number)
        issue.create_comment(body)

github_service = GitHubService()
