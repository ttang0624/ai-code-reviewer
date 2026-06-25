from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from app.config import settings


GITHUB_API_VERSION = "2022-11-28"


@dataclass(frozen=True)
class PullRequestFile:
    filename: str
    status: str
    patch: str


def _auth_headers() -> dict[str, str]:
    if not settings.github_token:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN is not configured; cannot call the GitHub API.",
        )
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "ai-code-reviewer",
    }


async def get_pr_files(repo_name: str, pr_number: int) -> list[PullRequestFile]:
    files: list[PullRequestFile] = []
    page = 1

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files"
            response = await client.get(
                url,
                headers=_auth_headers(),
                params={"per_page": 100, "page": page},
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API error fetching PR files: {response.text}",
                )

            batch = response.json()
            if not batch:
                break

            for item in batch:
                patch = item.get("patch") or ""
                if patch:
                    files.append(
                        PullRequestFile(
                            filename=item.get("filename", "unknown"),
                            status=item.get("status", "modified"),
                            patch=patch,
                        )
                    )

            if len(batch) < 100:
                break
            page += 1

    return files


def format_pr_diff(files: list[PullRequestFile], max_chars: int | None = None) -> str:
    limit = max_chars or settings.max_diff_chars
    diff_parts = [
        f"### {file.filename} ({file.status})\n```diff\n{file.patch}\n```"
        for file in files
    ]
    diff = "\n\n".join(diff_parts)
    if len(diff) <= limit:
        return diff
    return diff[:limit] + "\n\n[Diff truncated because it exceeded the configured size limit.]"


async def post_review_comment(repo_name: str, pr_number: int, review: str) -> None:
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
    body = {"body": review}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=_auth_headers(), json=body)

    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error posting review comment: {response.text}",
        )
