# Defines the HTTP endpoint that GitHub will call when a pull request event occurs.
# Receives the raw webhook payload, verifies it came from GitHub, then hands off to services.

from fastapi import APIRouter

router = APIRouter()

@router.post("/webhook")
async def handle_webhook():
    # TODO: verify webhook signature
    # TODO: parse event type and PR data
    # TODO: call reviewer service
    pass
