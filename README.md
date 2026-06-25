# AI Code Reviewer

AI Code Reviewer is a FastAPI service that receives GitHub pull request webhooks, fetches the changed files, asks Claude for a code review, posts the review back to the PR, and stores each review run for later inspection.

The app also works locally without real API keys: if `ANTHROPIC_API_KEY` is empty and `DRY_RUN_WITHOUT_AI=true`, it uses a deterministic heuristic reviewer so the webhook flow, database, dashboard, and tests can run end to end.

## Features

- GitHub webhook signature verification.
- Pull request event filtering and delivery deduplication.
- GitHub PR file fetching with pagination.
- Claude-powered review generation when configured.
- Local heuristic fallback for demos and tests.
- GitHub PR comment posting.
- SQLAlchemy persistence with SQLite by default and PostgreSQL support.
- Review history JSON endpoints.
- Minimal dashboard at `/dashboard`.
- Automated tests for health, signature verification, webhook behavior, and duplicate delivery handling.

## Quick Start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Health: `http://127.0.0.1:8000/health`

## Configuration

Local dry-run defaults are safe. For production, set:

```env
GITHUB_WEBHOOK_SECRET=the-secret-configured-in-your-github-webhook
GITHUB_TOKEN=github-token-with-repo-access
ANTHROPIC_API_KEY=your-anthropic-api-key
DATABASE_URL=postgresql://user:password@host:5432/ai_code_reviewer
DRY_RUN_WITHOUT_AI=false
```

## GitHub Webhook Setup

1. Deploy the FastAPI app somewhere reachable by GitHub.
2. In the GitHub repository, go to Settings -> Webhooks -> Add webhook.
3. Payload URL: `https://your-domain.com/webhook`
4. Content type: `application/json`
5. Secret: same value as `GITHUB_WEBHOOK_SECRET`.
6. Events: select pull request events.

The service reviews actions: `opened`, `reopened`, `synchronize`, and `ready_for_review`.

## Run Tests

```bash
cd backend
pytest
```

## Project Structure

```text
backend/
  app/
    config.py              # environment-driven settings
    main.py                # FastAPI application entrypoint
    routes/webhook.py      # webhook, history, dashboard routes
    services/github.py     # GitHub API integration
    services/reviewer.py   # Claude and local heuristic reviewers
    database/              # SQLAlchemy connection and models
  tests/
```

## Production Notes

- Use HTTPS for the webhook endpoint.
- Store secrets in your host or platform secret manager, not in `.env` committed to Git.
- Prefer a GitHub App installation token for production over a personal access token.
- Use PostgreSQL for shared or deployed environments.
- Add request logging and background jobs if reviews may take longer than your webhook timeout budget.
