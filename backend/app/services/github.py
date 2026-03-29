# Handles all communication with the GitHub API.
# Responsibilities: fetching PR diffs, posting review comments back to GitHub.

# httpx is an async-capable HTTP client library. We use it instead of the built-in `requests`
# library because `requests` is synchronous — it would block the entire server while waiting
# for GitHub to respond. httpx with `async/await` lets FastAPI handle other requests in the meantime.
import httpx

# HTTPException lets us abort request handling and return a specific HTTP error code to the caller.
# We raise it here (inside a service) so the route handler doesn't need to know GitHub's error details.
from fastapi import HTTPException

# We import the shared settings object to read GITHUB_TOKEN without hardcoding credentials.
from app.config import settings


# This is an async function — the `async` keyword means it can pause (with `await`) while waiting
# for network I/O, freeing the event loop to process other work during that wait.
async def get_pr_files(repo_name: str, pr_number: int) -> str:
    # Construct the GitHub REST API URL for listing files changed in a pull request.
    # The URL shape is documented at: https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
    # repo_name is the "owner/repo" string (e.g. "octocat/hello-world") extracted from the webhook payload.
    # pr_number is the integer PR number (e.g. 42) extracted from the same payload.
    url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files"

    # Build the HTTP headers that every GitHub API request requires.
    headers = {
        # Authorization tells GitHub who we are. "Bearer <token>" is the standard format for
        # token-based auth — GitHub checks this token to confirm we have access to the repo.
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        # Accept tells GitHub which version of its API response format we want.
        # "application/vnd.github+json" is the current recommended media type for the GitHub REST API.
        "Accept": "application/vnd.github+json",
        # X-GitHub-Api-Version pins us to a specific API version so future GitHub changes
        # don't silently break our integration.
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # `async with` creates an httpx client and guarantees it is closed when the block exits,
    # even if an exception is raised. This prevents connection leaks.
    async with httpx.AsyncClient() as client:
        # `await` pauses this function until GitHub responds, without blocking the server.
        # client.get() sends an HTTP GET request to the URL with the headers above.
        response = await client.get(url, headers=headers)

    # response.status_code is the HTTP status GitHub returned (200 = OK, 404 = not found, etc.).
    # Any status other than 200 means something went wrong and we should not try to parse the body.
    if response.status_code != 200:
        # Raise an HTTPException so FastAPI returns an error response to whoever called the webhook.
        # We forward GitHub's status code directly so the caller knows whether it was a 401, 404, etc.
        # We embed the raw response text in the detail so the error is diagnosable without extra logging.
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error fetching PR files: {response.text}",
        )

    # response.json() parses the JSON response body into a Python list of dicts.
    # Each dict represents one changed file and contains fields like `filename` and `patch`.
    files = response.json()

    # We'll accumulate the formatted diff sections in this list, then join them at the end.
    # Using a list and joining once is more efficient than concatenating strings in a loop.
    diff_parts = []

    # Iterate over every changed file GitHub returned.
    for file in files:
        # `filename` is the path of the changed file relative to the repo root (e.g. "src/main.py").
        filename = file.get("filename", "unknown file")

        # `patch` is the unified diff for this file — the actual added/removed lines.
        # Not every file entry has a patch: binary files and files that only moved have no patch.
        # We default to an empty string so we still include a header for those files.
        patch = file.get("patch", "")

        # Build a labelled block for this file so the LLM can tell which diff belongs to which file.
        # The format mirrors a standard unified diff header, which the model is trained to understand.
        diff_parts.append(f"### {filename}\n{patch}")

    # Join all file blocks with a blank line between them for readability.
    # This single string is what we'll pass to the Claude API as the code to review.
    return "\n\n".join(diff_parts)
