# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

An AI-powered code review tool that receives GitHub pull request webhooks, analyzes code changes using the Claude API, and posts context-aware review comments back to GitHub automatically.

**Stack:** Python + FastAPI (backend), SQLite locally / PostgreSQL in production, GitHub Webhooks + GitHub API, Anthropic Claude API, minimal server-rendered dashboard.

## Build Status

- [x] Environment setup
- [x] Project scaffold
- [x] GitHub webhook receiver
- [x] LLM integration
- [x] Database setup
- [x] Minimal dashboard
- [ ] Deployment

## Commands

- Install deps: `cd backend && pip install -r requirements.txt`
- Run server: `cd backend && uvicorn app.main:app --reload`
- Run tests: `cd backend && pytest`

## Architecture

GitHub sends signed pull request webhooks to `/webhook`. The route verifies the HMAC signature, deduplicates delivery IDs, filters non-reviewable PR actions, fetches changed file patches via the GitHub API, asks Claude for a review when configured, posts the review as a PR comment, and stores a `ReviewRun` row for dashboard/history inspection.

If `ANTHROPIC_API_KEY` is absent and `DRY_RUN_WITHOUT_AI=true`, the service uses a deterministic local heuristic reviewer so the full app can be tested without paid API calls.

## Working with this User

The user is an intermediate Python developer with no prior web/systems architecture experience, learning top-down (why before how). Follow these rules strictly:

- Explain **why** a concept exists before writing any code for it.
- Never introduce code the user hasn't first understood conceptually.
- Use real-world analogies when explaining what something does.
- Flag foundational concepts and offer to drill deeper.
- If the user appears to be copy-pasting without understanding, stop and ask questions to verify comprehension before continuing.
