# Defines the HTTP endpoint that GitHub will call when a pull request event occurs.
# Receives the raw webhook payload, verifies it came from GitHub, then hands off to services.

# hmac is a standard library module for computing Hash-based Message Authentication Codes.
# We use it to re-compute the expected signature and compare it against what GitHub sent.
import hmac

# hashlib gives us access to hash functions like SHA-256, which HMAC needs under the hood.
import hashlib

# APIRouter lets us define route handlers in a separate file and register them on the main app.
# Think of it as a mini-app that gets "mounted" onto the main FastAPI instance.
from fastapi import APIRouter, Request, HTTPException, Header

# Optional is a type hint that means the value might be None (i.e. the header might be missing).
from typing import Optional

# We import the shared settings object so we can read GITHUB_WEBHOOK_SECRET without hardcoding it.
from app.config import settings

# Creates the router instance. main.py calls app.include_router(router) to activate these routes.
router = APIRouter()


# @router.post("/webhook") registers this function as the handler for POST requests to /webhook.
# GitHub sends a POST every time a pull request event happens on a repo where the webhook is installed.
@router.post("/webhook")
async def handle_webhook(
    # Request gives us access to the raw HTTP request — headers, body bytes, etc.
    request: Request, #this specifies the type of the request parameter, which is an instance of FastAPI's Request class. This allows us to access the raw HTTP request data, including headers and body.
    # Header(...) tells FastAPI to extract the X-Hub-Signature-256 header from the incoming request.
    # GitHub sends this header on every webhook call; it contains the HMAC signature of the body.
    # The alias maps the Python variable name to the actual HTTP header name (hyphens → underscores).
    # Optional[str] means FastAPI won't error if the header is absent — we handle that case ourselves.
    x_hub_signature_256: Optional[str] = Header(None, alias="x-hub-signature-256"),
):
    # Read the raw request body as bytes. We need raw bytes (not parsed JSON) to recompute the HMAC.
    # HMAC is computed over the exact bytes GitHub sent — parsing first would change whitespace/ordering.
    if x_hub_signature_256 is None:
        raise HTTPException(status_code=401, detail="Missing signature header")
    raw_body = await request.body()


    # Encode the secret as bytes; hmac.new() requires bytes, not a plain string.
    # The secret must be exactly the same string both GitHub and we configured — any mismatch fails.
    secret_bytes = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")

    # Compute the expected HMAC-SHA256 signature using our secret and the raw request body.
    # hmac.new(key, msg, digestmod) creates the HMAC object; hexdigest() returns it as a hex string.
    expected_signature = "sha256=" + hmac.new(secret_bytes, raw_body, hashlib.sha256).hexdigest()

    # hmac.compare_digest does a constant-time comparison to prevent timing attacks.
    # A normal == comparison can leak information about how many characters matched via response time.
    signatures_match = hmac.compare_digest(expected_signature, x_hub_signature_256)

    # If the signatures don't match, the payload was not sent by our GitHub app — reject it.
    if not signatures_match:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the verified raw bytes as JSON now that we know the payload is authentic.
    # await request.json() decodes the bytes into a Python dict we can index into.
    payload = await request.json()

    # GitHub includes the event type in the X-GitHub-Event header (e.g. "pull_request", "push").
    # We read it here so we can ignore events that aren't pull request events.
    event_type = request.headers.get("x-github-event")

    # We only care about pull_request events. Anything else (push, star, etc.) we acknowledge
    # and ignore — returning 200 so GitHub doesn't mark the webhook delivery as failed.
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"event type '{event_type}' is not handled"}

    # The pull request number lives at payload["pull_request"]["number"].
    # GitHub always includes this for pull_request events; .get() returns None if somehow absent.
    pr_number = payload.get("pull_request", {}).get("number")

    # The repository's full name (e.g. "owner/repo") lives at payload["repository"]["full_name"].
    repo_name = payload.get("repository", {}).get("full_name")

    # Return a 200 with the extracted data so we can confirm parsing is correct during development.
    # In a later step this is where we'll call the reviewer service instead.

    if pr_number is None or repo_name is None:
        raise HTTPException(
            status_code=400,
            detail="Malformed pull_request payload"
        )
    
    return {
        "status": "received",
        "pr_number": pr_number,
        "repo": repo_name,
    }
