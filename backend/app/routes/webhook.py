import hashlib
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.models import ReviewRun
from app.services.github import format_pr_diff, get_pr_files, post_review_comment
from app.services.reviewer import review_code


router = APIRouter()
HANDLED_ACTIONS = {"opened", "reopened", "synchronize", "ready_for_review"}


def verify_github_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_hub_signature_256: Annotated[str | None, Header(alias="x-hub-signature-256")] = None,
    x_github_event: Annotated[str | None, Header(alias="x-github-event")] = None,
    x_github_delivery: Annotated[str | None, Header(alias="x-github-delivery")] = None,
):
    raw_body = await request.body()
    if not verify_github_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid or missing GitHub signature")

    if x_github_delivery:
        existing = db.scalar(select(ReviewRun).where(ReviewRun.delivery_id == x_github_delivery))
        if existing:
            return {"status": "duplicate", "review_id": existing.id}

    if x_github_event == "ping":
        return {"status": "ok", "event": "ping"}
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event '{x_github_event}' is not handled"}

    payload = await request.json()
    action = payload.get("action", "unknown")
    pr = payload.get("pull_request") or {}
    repo = payload.get("repository") or {}
    pr_number = pr.get("number")
    repo_name = repo.get("full_name")

    if not isinstance(pr_number, int) or not repo_name:
        raise HTTPException(status_code=400, detail="Malformed pull_request payload")

    run = ReviewRun(
        delivery_id=x_github_delivery,
        repo_name=repo_name,
        pr_number=pr_number,
        pr_action=action,
        status="started",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if action not in HANDLED_ACTIONS:
        run.status = "ignored"
        run.error = f"Pull request action '{action}' is not reviewable"
        db.commit()
        return {"status": "ignored", "reason": run.error, "review_id": run.id}

    try:
        files = await get_pr_files(repo_name, pr_number)
        if not files:
            run.status = "skipped"
            run.error = "No reviewable text patches found"
            db.commit()
            return {"status": "skipped", "reason": run.error, "review_id": run.id}

        diff = format_pr_diff(files)
        review = await review_code(diff, repo_name, pr_number)
        await post_review_comment(repo_name, pr_number, review)

        run.status = "posted"
        run.review_body = review
        db.commit()
        return {"status": "review posted", "review_id": run.id, "repo": repo_name, "pr_number": pr_number}
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        db.commit()
        raise


@router.get("/reviews")
def list_reviews(db: Annotated[Session, Depends(get_db)], limit: int = 25):
    limit = max(1, min(limit, 100))
    rows = db.scalars(select(ReviewRun).order_by(ReviewRun.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": row.id,
            "repo_name": row.repo_name,
            "pr_number": row.pr_number,
            "action": row.pr_action,
            "status": row.status,
            "created_at": row.created_at,
            "error": row.error,
        }
        for row in rows
    ]


@router.get("/reviews/{review_id}")
def get_review(review_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(ReviewRun, review_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "id": row.id,
        "repo_name": row.repo_name,
        "pr_number": row.pr_number,
        "action": row.pr_action,
        "status": row.status,
        "review_body": row.review_body,
        "error": row.error,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: Annotated[Session, Depends(get_db)]):
    rows = db.scalars(select(ReviewRun).order_by(ReviewRun.created_at.desc()).limit(50)).all()
    items = "\n".join(
        f"<tr><td>{row.id}</td><td>{row.repo_name}</td><td>#{row.pr_number}</td>"
        f"<td>{row.pr_action}</td><td>{row.status}</td><td>{row.created_at}</td></tr>"
        for row in rows
    )
    return f"""
    <!doctype html>
    <html>
      <head>
        <title>AI Code Reviewer</title>
        <style>
          body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #172033; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border-bottom: 1px solid #d8dee9; padding: .65rem; text-align: left; }}
          th {{ background: #f6f8fb; }}
          code {{ background: #f6f8fb; padding: .1rem .25rem; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <h1>AI Code Reviewer</h1>
        <p>Recent webhook review runs. JSON API: <code>/reviews</code>.</p>
        <table>
          <thead><tr><th>ID</th><th>Repo</th><th>PR</th><th>Action</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>{items or "<tr><td colspan='6'>No reviews yet.</td></tr>"}</tbody>
        </table>
      </body>
    </html>
    """
