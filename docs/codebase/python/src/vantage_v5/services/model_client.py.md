# `src/vantage_v5/services/model_client.py`

Centralizes model-provider client construction for Vantage V5. It keeps the existing OpenAI API-key path working while adding a Codex OAuth provider that reads the local Codex CLI `auth.json`, builds a Responses client pointed at the Codex backend, and adapts Codex's streaming-only contract back into the `response.output_text` shape expected by the rest of the V5 services.

## Purpose

- Normalize model provider names such as `openai`, `codex`, and `codex_oauth`.
- Choose default model ids per provider, with Codex OAuth defaulting to `gpt-5.5`.
- Load local Codex OAuth credentials from `CODEX_HOME/auth.json` or `~/.codex/auth.json`.
- Reject missing or expired Codex OAuth tokens before service code tries to call the model.
- Create OpenAI SDK clients for direct OpenAI API-key mode or Codex OAuth mode.
- Hide Codex transport differences behind the same `client.responses.create(...).output_text` interface used by chat, navigator, meta, protocol, vetting, and Scenario Lab services.

## Core Data Flow

- `AppConfig.from_env()` resolves the provider/model and passes a `ModelClientConfig` into server-created services.
- `create_model_client()` builds a normal OpenAI SDK client for `openai` mode when an API key is available.
- In `codex_oauth` mode, it reads the Codex CLI credential, checks token expiry, points the SDK at `https://chatgpt.com/backend-api/codex`, and wraps the SDK client in `_CodexOAuthClientAdapter`.
- `_CodexOAuthResponsesAdapter.create()` converts string input into a Responses message list, forces `store=False`, forces `stream=True`, consumes the stream, and returns `CollectedResponse(output_text=...)`.
- `codex_oauth_status()` returns a secret-safe status payload for health/UI calls, including masked account id and expiry information without exposing tokens.

## Key Classes / Functions

- `ModelClientConfig`: provider/auth/base-url options for constructing a model client.
- `CodexOAuthCredential`: parsed local Codex CLI OAuth credential plus expiry helper.
- `CollectedResponse`: minimal response object preserving the existing `output_text` contract.
- `normalize_model_provider()`: maps aliases to canonical provider ids.
- `default_model_for_provider()`: selects conservative defaults for OpenAI API-key mode and Codex OAuth mode.
- `create_model_client()`: single entrypoint for service client construction.
- `load_codex_oauth_credential()`: reads and parses local Codex CLI auth state.
- `codex_oauth_status()`: builds safe product-facing provider status.
- `_collect_codex_response_stream()`: drains Codex's streamed Responses events into one text string.

## Notable Edge Cases

- Codex OAuth access tokens are never returned from status payloads; account ids are masked.
- Expired Codex OAuth credentials return `None` from `create_model_client()`, allowing existing deterministic fallback paths to stay in control.
- Codex Responses rejects plain string input and non-streamed calls, so the adapter normalizes both before the request leaves the app.
- Direct OpenAI API-key mode is left behavior-compatible with the old V5 service constructors and tests.
