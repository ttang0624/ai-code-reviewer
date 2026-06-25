import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.github import PullRequestFile


def signed_headers(payload: dict, delivery: str = "delivery-1", event: str = "pull_request"):
    raw = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).hexdigest()
    return raw, {
        "x-hub-signature-256": signature,
        "x-github-event": event,
        "x-github-delivery": delivery,
        "content-type": "application/json",
    }


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rejects_missing_signature(client):
    response = client.post("/webhook", json={})
    assert response.status_code == 401


def test_ping_event(client):
    raw, headers = signed_headers({"zen": "Keep it logically awesome."}, event="ping")
    response = client.post("/webhook", data=raw, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "event": "ping"}


def test_ignored_pull_request_action(client):
    payload = {
        "action": "closed",
        "pull_request": {"number": 7},
        "repository": {"full_name": "ttang0624/example"},
    }
    raw, headers = signed_headers(payload, delivery="ignored-action")
    response = client.post("/webhook", data=raw, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_duplicate_delivery(client):
    payload = {
        "action": "closed",
        "pull_request": {"number": 8},
        "repository": {"full_name": "ttang0624/example"},
    }
    raw, headers = signed_headers(payload, delivery="duplicate-action")
    first = client.post("/webhook", data=raw, headers=headers)
    second = client.post("/webhook", data=raw, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_opened_pull_request_review_flow(client, monkeypatch):
    posted = {}

    async def fake_get_pr_files(repo_name: str, pr_number: int):
        assert repo_name == "ttang0624/example"
        assert pr_number == 9
        return [
            PullRequestFile(
                filename="app.py",
                status="modified",
                patch="+print('hello')",
            )
        ]

    async def fake_review_code(diff: str, repo_name: str, pr_number: int):
        assert "app.py" in diff
        return "## Review\nLooks good.\n\n### Verdict\nCOMMENT"

    async def fake_post_review_comment(repo_name: str, pr_number: int, review: str):
        posted["repo_name"] = repo_name
        posted["pr_number"] = pr_number
        posted["review"] = review

    monkeypatch.setattr("app.routes.webhook.get_pr_files", fake_get_pr_files)
    monkeypatch.setattr("app.routes.webhook.review_code", fake_review_code)
    monkeypatch.setattr("app.routes.webhook.post_review_comment", fake_post_review_comment)

    payload = {
        "action": "opened",
        "pull_request": {"number": 9},
        "repository": {"full_name": "ttang0624/example"},
    }
    raw, headers = signed_headers(payload, delivery="happy-path")
    response = client.post("/webhook", data=raw, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "review posted"
    assert posted == {
        "repo_name": "ttang0624/example",
        "pr_number": 9,
        "review": "## Review\nLooks good.\n\n### Verdict\nCOMMENT",
    }
