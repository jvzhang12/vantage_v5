# `tests/test_model_client.py`

Tests the provider adapter that lets Vantage use Codex OAuth while preserving the old V5 model-client call shape.

## Purpose

- Verify local Codex CLI `auth.json` credentials are parsed into a usable `CodexOAuthCredential`.
- Confirm Codex OAuth status payloads are configured, masked, and token-safe.
- Check that Codex OAuth clients use the Codex Responses base URL.
- Lock in the adapter behavior that converts string input into Responses messages and forces Codex-required streaming with `store=False`.
- Ensure expired Codex OAuth credentials do not create a model client.

## Core Data Flow

- Tests write temporary fake Codex auth files with unsigned JWT-shaped access tokens.
- `load_codex_oauth_credential()` and `codex_oauth_status()` are exercised without touching the real user auth file.
- `OpenAI` is monkeypatched with a fake class so construction and request-shaping can be inspected without network calls.
- The adapter's `responses.create()` call is tested through the same surface the production services use.

## Key Assertions

- Parsed credentials preserve access token, refresh token, account id, expiry, and auth path.
- Status output masks account ids and does not contain the raw token.
- The Codex client uses `https://chatgpt.com/backend-api/codex`.
- Codex requests are sent as a message-list `input`, with `stream=True` and `store=False`.
- Expired tokens return `None` and never instantiate the SDK client.
