# Orchestrates the AI code review process.
# Takes a PR diff, sends it to Claude, and returns structured review comments.

# anthropic is the official Python SDK for calling the Claude API.
import anthropic

# HTTPException lets us abort request handling and return a specific HTTP error to the caller.
from fastapi import HTTPException

# We import settings to read ANTHROPIC_API_KEY without hardcoding credentials.
from app.config import settings

# The system prompt text is defined as a module-level constant so it never changes between calls.
# This is critical for prompt caching — the cache key is the exact bytes of the prefix,
# so any change to the system prompt, even whitespace, creates a cache miss.
SYSTEM_PROMPT = """\
You are a senior software engineer conducting a thorough pull request review.

Your job is to analyze the provided code diff and give clear, actionable feedback across four dimensions:

1. **Security** — Identify vulnerabilities such as injection flaws, insecure data handling, exposed secrets, broken authentication, or missing input validation.

2. **Performance** — Flag inefficient algorithms, unnecessary database calls, missing indexes, blocking I/O in async contexts, or memory issues.

3. **Readability** — Point out unclear naming, missing or misleading comments, overly complex logic, and violations of the language's idioms or style conventions.

4. **Architecture** — Highlight violations of separation of concerns, tight coupling, missing abstractions, or design decisions that will hinder future changes.

Format your review as follows:
- Lead with a one-sentence summary of the overall change.
- Group findings by dimension using the bold headers above.
- For each finding, state the filename and the specific concern, then give a concrete suggestion for improvement.
- If a dimension has no issues, write "No issues found."
- Close with a one-line verdict: APPROVE, REQUEST CHANGES, or COMMENT.\
"""


# This is an async function so it can be awaited inside the async webhook route handler.
# Making it async means FastAPI can handle other requests while Claude is generating a response.
async def review_code(diff: str, repo_name: str, pr_number: int) -> str:
    # AsyncAnthropic is the async variant of the SDK client.
    # It reads ANTHROPIC_API_KEY from the environment automatically, but we pass it explicitly
    # so it comes from our validated settings object rather than raw os.environ.
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # We wrap the API call in try/except to catch SDK-specific errors and convert them
    # into FastAPI HTTPExceptions that the route handler can return to the caller.
    try:
        # client.messages.create() sends a single request to the Claude API and waits for
        # the full response. We use `await` because this is an async client.
        response = await client.messages.create(
            # The model to use. Haiku is fast and cheap — well suited for high-volume webhook traffic.
            model="claude-haiku-4-5-20251001",
            # max_tokens caps how long Claude's response can be.
            # 1024 is enough for a focused review; raise this if reviews are being truncated.
            max_tokens=1024,
            # system accepts either a plain string or a list of content blocks.
            # We use a list here so we can attach cache_control to the block.
            system=[
                {
                    # type "text" is the standard system prompt block type.
                    "type": "text",
                    # The actual system prompt content defined above.
                    "text": SYSTEM_PROMPT,
                    # cache_control tells Claude to cache everything up to this block.
                    # "ephemeral" means the cache entry lives for 5 minutes (the default TTL).
                    # After the first request writes the cache, subsequent requests within 5 minutes
                    # read it at ~10% of the normal input token cost instead of paying full price.
                    # The system prompt is ~250 tokens — caching saves money at scale.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            # messages is the conversation history. We only have one turn: the user's request.
            messages=[
                {
                    # "user" is the role for the message we're sending to Claude.
                    "role": "user",
                    # The content is a plain string describing what to review and including the diff.
                    # We include the repo and PR number so the model has context for the review.
                    "content": (
                        f"Please review the following code diff from pull request #{pr_number} "
                        f"in the repository `{repo_name}`.\n\n"
                        f"{diff}"
                    ),
                }
            ],
        )

    # anthropic.APIStatusError is the base class for all HTTP error responses from the API.
    # status_code gives us the raw HTTP status (400, 401, 429, 500, etc.).
    # message gives us the human-readable error detail from Anthropic.
    except anthropic.APIStatusError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Claude API error: {e.message}",
        )

    # anthropic.APIConnectionError covers network-level failures — DNS, timeouts, dropped connections.
    # These are not HTTP errors, so there is no status_code to forward; we use 503 (service unavailable).
    except anthropic.APIConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach Claude API: {e}",
        )

    # response.content is a list of content blocks. We iterate to find the first text block
    # because Claude could theoretically return other block types (though not in this setup).
    for block in response.content:
        # block.type tells us what kind of content this block contains.
        if block.type == "text":
            # block.text is the raw string of Claude's review. Return it immediately.
            return block.text

    # If we exit the loop without finding a text block, something unexpected happened.
    # This should not occur in normal operation but we handle it defensively.
    raise HTTPException(
        status_code=500,
        detail="Claude returned a response with no text content.",
    )
