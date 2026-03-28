# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

An AI-powered code review tool that receives GitHub pull request webhooks, analyzes code changes using the Claude API, and posts context-aware review comments back to GitHub automatically.

**Stack:** Python + FastAPI (backend), PostgreSQL (database), GitHub Webhooks + GitHub API (integration), Anthropic Claude API (AI), React (dashboard frontend).

## Build Status

- [ ] Environment setup
- [ ] Project scaffold
- [ ] GitHub webhook receiver
- [ ] LLM integration
- [ ] Database setup
- [ ] Dashboard frontend
- [ ] Deployment

## Commands

<!-- Fill in as the project is built. Expected shape:
- Run server: `uvicorn main:app --reload`
- Run tests: `pytest` or `pytest tests/test_foo.py`
- Lint: `ruff check .` or `flake8`
- Install deps: `pip install -r requirements.txt`
-->

## Architecture

<!-- Fill in as the project is built. -->

## Working with this User

The user is an intermediate Python developer with no prior web/systems architecture experience, learning top-down (why before how). Follow these rules strictly:

- Explain **why** a concept exists before writing any code for it.
- Never introduce code the user hasn't first understood conceptually.
- Use real-world analogies when explaining what something does.
- Flag foundational concepts and offer to drill deeper.
- If the user appears to be copy-pasting without understanding, stop and ask questions to verify comprehension before continuing.
