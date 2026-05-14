# `src/vantage_v5/webapp_react/src/api.ts`

Typed API client for the React frontend.

## Purpose

- Wrap existing FastAPI endpoints without changing backend payload contracts.
- Normalize `/api/chat` responses into the React turn model.

## Coverage

- Health, login, account creation with optional access code, logout, workspace load/save, workspace promotion, calendar week fetches, and chat submission.
- Sends `history`, workspace context scope/content, and `visible_artifacts` to preserve Vantage context behavior.
