# `src/vantage_v5/webapp/auth_state.mjs`

Small pure helpers for client-side authentication state decisions.

## Purpose

- Normalize request paths before checking API response behavior.
- Decide when a `401` from a protected API route should be treated as an expired Vantage session.
- Keep ordinary `/api/login` failures separate so the login form can show normal invalid-credential feedback.
- Produce the user-facing expired-session message used by the app shell.

## Why It Matters

- The FastAPI server stores login sessions in memory, so a server restart can invalidate a browser cookie while the already-loaded UI still looks signed in.
- These helpers let `app.js` centrally convert protected-route `401` responses into a clean return to the sign-in gate instead of leaving stale chat or draft controls active.
