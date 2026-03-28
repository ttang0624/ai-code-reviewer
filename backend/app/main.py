# FastAPI is the web framework we use to define HTTP routes and run the server.
from fastapi import FastAPI

# We import the webhook router so we can register its routes on the app.
from app.routes import webhook

# This creates the FastAPI application instance — the central object that holds all routes and config.
app = FastAPI()

# This registers all routes defined in webhook.py under this app.
# Any @router decorator in webhook.py becomes a live endpoint after this line.
app.include_router(webhook.router)

# @app.get tells FastAPI: "when a GET request arrives at /health, call this function".
# Health check endpoints are standard practice — they let uptime monitors confirm the server is running.
@app.get("/health")
# The function name is just a label; FastAPI uses the decorator above to route requests to it.
def health_check():
    # We return a plain dict; FastAPI automatically converts it to a JSON response.
    return {"status": "ok"}
