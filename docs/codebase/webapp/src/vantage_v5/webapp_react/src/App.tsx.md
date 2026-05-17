# `src/vantage_v5/webapp_react/src/App.tsx`

Top-level React application container for the Vantage frontend migration.

## Purpose

- Bootstraps auth, health, and workspace state from the existing FastAPI API.
- Passes the account-creation access code through the login screen when the backend reports that hosted signup requires one.
- Renders the premium default chat UI, artifact host, Vantage/Inspect view, and whiteboard surface.
- Sends chat turns with hidden backend history and visible artifact context.
- Shows a generic pending assistant state while chat requests are in flight, then clears it on success or failure.

## Coverage

- Keeps the user prompt out of the visible transcript while retaining `history` for continuity.
- Opens returned calendar/task/today surfaces and whiteboard drafts automatically.
- Supports calendar week switching by fetching `/api/calendar/week` and replacing the active visible surface payload.
- Opens the Vantage inspection receipt from the top-left Vantage button and hides the composer while that latest-turn receipt is active.
- Keeps the latest assistant answer mounted while Whiteboard is foregrounded so mobile layout can expose the chat response without closing the draft.
- Renders `Vantage is thinking...` from local request state only; it does not expose chain-of-thought or depend on backend streaming.
