"""
title: GitHub Reader
author: AI Lab
version: 1.0.0
description: Read-only access to allowlisted GitHub repositories.
"""

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        github_token: str = Field(
            default="",
            description="Optional read-only fine-grained GitHub token for private repositories.",
        )
        allowed_repositories: str = Field(
            default="",
            description=(
                "Comma-separated owner/repository allowlist. Empty denies all repositories."
            ),
        )
        timeout_seconds: int = Field(default=20, ge=2, le=120)

    def __init__(self):
        self.valves = self.Valves()

    def _allowed(self, owner: str, repository: str) -> str:
        target = f"{owner.strip()}/{repository.strip()}".lower()
        allowed = {
            item.strip().lower()
            for item in self.valves.allowed_repositories.split(",")
            if item.strip()
        }
        if target not in allowed:
            raise ValueError(f"Repository {target} is not in the GitHub Reader allowlist.")
        return target

    def _get(self, path: str, parameters: dict | None = None):
        url = f"https://api.github.com{path}"
        if parameters:
            url = f"{url}?{urlencode(parameters)}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "openwebui-github-reader/1.0",
        }
        if self.valves.github_token:
            headers["Authorization"] = f"Bearer {self.valves.github_token}"
        try:
            with urlopen(  # noqa: S310
                Request(url, headers=headers), timeout=self.valves.timeout_seconds
            ) as response:
                return json.load(response)
        except HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise RuntimeError("The GitHub read-only API is unavailable.") from error

    def repository_overview(self, owner: str, repository: str) -> str:
        """Read an allowlisted repository's description, visibility, default branch, and activity.

        :param owner: GitHub account or organization.
        :param repository: Repository name.
        """
        target = self._allowed(owner, repository)
        data = self._get(f"/repos/{target}")
        selected = {
            key: data.get(key)
            for key in (
                "full_name",
                "description",
                "private",
                "html_url",
                "default_branch",
                "language",
                "topics",
                "open_issues_count",
                "pushed_at",
                "updated_at",
                "archived",
            )
        }
        return json.dumps(selected, indent=2)

    def list_repository_path(
        self, owner: str, repository: str, path: str = "", ref: str = ""
    ) -> str:
        """List files and directories at an allowlisted repository path.

        :param owner: GitHub account or organization.
        :param repository: Repository name.
        :param path: Repository-relative directory path.
        :param ref: Optional branch, tag, or commit SHA.
        """
        target = self._allowed(owner, repository)
        safe_path = quote(path.strip("/"), safe="/")
        parameters = {"ref": ref} if ref else None
        data = self._get(f"/repos/{target}/contents/{safe_path}", parameters)
        if not isinstance(data, list):
            data = [data]
        selected = [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "type": item.get("type"),
                "size": item.get("size"),
                "sha": item.get("sha"),
                "html_url": item.get("html_url"),
            }
            for item in data[:200]
        ]
        return json.dumps(selected, indent=2)

    def read_repository_file(self, owner: str, repository: str, path: str, ref: str = "") -> str:
        """Read a text file from an allowlisted repository, capped at 100,000 characters.

        :param owner: GitHub account or organization.
        :param repository: Repository name.
        :param path: Exact repository-relative file path.
        :param ref: Optional branch, tag, or commit SHA.
        """
        target = self._allowed(owner, repository)
        safe_path = quote(path.strip("/"), safe="/")
        parameters = {"ref": ref} if ref else None
        data = self._get(f"/repos/{target}/contents/{safe_path}", parameters)
        if data.get("type") != "file" or not data.get("content"):
            raise ValueError("The requested GitHub path is not a readable file.")
        content = base64.b64decode(data["content"], validate=False).decode(
            "utf-8", errors="replace"
        )
        return json.dumps(
            {
                "repository": target,
                "path": data.get("path"),
                "sha": data.get("sha"),
                "content": content[:100_000],
                "truncated": len(content) > 100_000,
            },
            indent=2,
        )

    def list_issues_and_pull_requests(
        self, owner: str, repository: str, state: str = "open", limit: int = 20
    ) -> str:
        """List recent issues and pull requests from an allowlisted repository.

        :param owner: GitHub account or organization.
        :param repository: Repository name.
        :param state: open, closed, or all.
        :param limit: Maximum results from 1 to 50.
        """
        target = self._allowed(owner, repository)
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be open, closed, or all")
        data = self._get(
            f"/repos/{target}/issues",
            {"state": state, "per_page": max(1, min(limit, 50)), "sort": "updated"},
        )
        selected = [
            {
                "number": item.get("number"),
                "type": "pull_request" if item.get("pull_request") else "issue",
                "title": item.get("title"),
                "state": item.get("state"),
                "user": (item.get("user") or {}).get("login"),
                "labels": [label.get("name") for label in item.get("labels", [])],
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
            }
            for item in data
        ]
        return json.dumps(selected, indent=2)
