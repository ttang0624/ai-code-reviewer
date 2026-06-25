import re

import anthropic
from fastapi import HTTPException

from app.config import settings


SYSTEM_PROMPT = """\
You are a senior software engineer conducting a concise pull request review.

Prioritize bugs, security issues, data-loss risks, performance regressions, and missing tests.
Return markdown with:
- Summary
- Findings, ordered by severity
- Tests to add or run
- Verdict: APPROVE, COMMENT, or REQUEST CHANGES

Ground every finding in the supplied diff. Do not invent files or behavior that are not present.
"""


RISK_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(password|token|secret|api[_-]?key)\s*=", "Possible hard-coded secret or credential."),
    (r"(?i)subprocess\.(run|popen|call).*shell\s*=\s*True", "Use of shell=True can enable command injection."),
    (r"(?i)eval\(", "Use of eval can execute untrusted code."),
    (r"(?i)except\s*:", "Bare except can hide real errors."),
    (r"(?i)print\(", "Debug print statement may need structured logging or removal."),
    (r"(?i)todo|fixme", "TODO/FIXME left in changed code."),
]


def _heuristic_review(diff: str, repo_name: str, pr_number: int) -> str:
    findings: list[str] = []
    added_lines = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]

    for line in added_lines:
        for pattern, message in RISK_PATTERNS:
            if re.search(pattern, line):
                snippet = line[:160].replace("`", "'")
                findings.append(f"- **COMMENT** {message}\n  Changed line: `{snippet}`")
                break

    if not findings:
        findings.append("- No high-risk issues found by the local heuristic reviewer.")

    verdict = "COMMENT" if findings and "No high-risk" not in findings[0] else "APPROVE"
    return (
        f"## AI Code Review for `{repo_name}` PR #{pr_number}\n\n"
        "### Summary\n"
        "Local heuristic review completed because no Anthropic API key is configured.\n\n"
        "### Findings\n"
        + "\n".join(findings)
        + "\n\n### Tests\n"
        "- Run the project test suite and any checks relevant to the changed files.\n\n"
        f"### Verdict\n{verdict}"
    )


async def review_code(diff: str, repo_name: str, pr_number: int) -> str:
    if not settings.anthropic_api_key:
        if settings.dry_run_without_ai:
            return _heuristic_review(diff, repo_name, pr_number)
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured and dry-run fallback is disabled.",
        )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Review pull request #{pr_number} in `{repo_name}`.\n\n"
                        f"Diff:\n{diff}"
                    ),
                }
            ],
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=exc.status_code, detail=f"Claude API error: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach Claude API: {exc}") from exc

    text_blocks = [block.text for block in response.content if block.type == "text"]
    if not text_blocks:
        raise HTTPException(status_code=500, detail="Claude returned no text content.")
    return "\n".join(text_blocks)
