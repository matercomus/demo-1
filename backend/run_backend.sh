#!/usr/bin/env bash

export $(grep '^OPENAI_API_KEY=' .env) &&
uv run uvicorn backend.main:app --reload --port 8000