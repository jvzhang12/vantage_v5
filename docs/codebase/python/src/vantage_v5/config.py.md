# `src/vantage_v5/config.py`

Environment-backed configuration layer for Vantage V5. It centralizes repo/data paths, canonical-default paths, model provider/auth settings, host/port selection, deployment safety controls, optional Basic Auth, optional multi-user credential maps, workspace defaults, and Nexus include/exclude controls.

## Purpose

- Load `.env` from the repository root.
- Build a frozen `AppConfig` object from environment variables.
- Provide defaults when explicit env vars are missing, including the active workspace ID.

## Key Classes / Functions

- `AppConfig`: frozen dataclass with:
  - `repo_root`
  - `openai_api_key`
  - `model`
  - `model_provider`
  - `codex_auth_path`
  - `codex_base_url`
  - `calendar_events_path`
  - `tasks_path`
  - `host`
  - `port`
  - `active_workspace`
  - `nexus_root`
  - `nexus_include_paths`
  - `nexus_exclude_paths`
  - `canonical_root`
  - `auth_username`
  - `auth_password`
  - `auth_users`
  - `account_creation_code`
  - `allowed_hosts`
  - `allowed_origins`
  - `cookie_secure`
  - `allow_unsafe_public_no_auth`
- `AppConfig.from_env()`: reads environment variables and constructs the config.
- `_default_active_workspace(repo_root)`: reads `state/active_workspace.json` if present, otherwise falls back to `v5-milestone-1`.
- `_csv_env(name)`: parses comma-separated env vars into trimmed string lists.
- `_optional_path(value)`: expands a path string into `Path | None`.
- `_auth_users_from_env(repo_root)`: loads an optional username/password map from `VANTAGE_V5_AUTH_USERS_JSON` or `VANTAGE_V5_AUTH_USERS_FILE`.
- `_bool_env(name)`: parses simple true-ish environment flags such as `VANTAGE_V5_COOKIE_SECURE`.

## Major Dependencies

- `os`
- `json`
- `pathlib.Path`
- `dataclasses.dataclass`
- `dotenv.load_dotenv`
- `vantage_v5.services.model_client`

## Notable Behavior

- Treats the repository root as two parents above this file, so path resolution is stable relative to the package layout.
- Loads `.env` without overriding already-set environment variables.
- Loads the package-root `.env` first, then an overridden `VANTAGE_V5_REPO_ROOT/.env` when `VANTAGE_V5_REPO_ROOT` points at a separate persistent data directory.
- Defaults `VANTAGE_V5_CANONICAL_ROOT` to the package/source checkout's `canonical/` directory so Docker can keep shipped defaults in the image while user data lives under `/data`.
- Defaults `VANTAGE_V5_MODEL_PROVIDER` to `codex_oauth`; the model default follows the provider (`gpt-5.5` for Codex OAuth, `gpt-4.1` for direct OpenAI API-key mode). Host and port still default to `127.0.0.1:8005`.
- Reads `VANTAGE_V5_CALENDAR_EVENTS_FILE` as an optional local JSON event source for the read-only calendar backend; when unset, the server defaults to `state/calendar/events.json` under the repo root.
- Reads `VANTAGE_V5_TASKS_FILE` as an optional local JSON task source for the read-only task focus backend; when unset, the server defaults to `state/tasks/tasks.json` under the repo root.
- Reads `VANTAGE_V5_ACTIVE_WORKSPACE` first, but can infer it from `state/active_workspace.json` if unset.
- Enables single shared HTTP Basic Auth when `VANTAGE_V5_AUTH_PASSWORD` is set, or multi-user profile auth when `VANTAGE_V5_AUTH_USERS_JSON` / `VANTAGE_V5_AUTH_USERS_FILE` is set; local development remains unauthenticated by default.
- Reads `VANTAGE_V5_ACCOUNT_CREATION_CODE` as an optional invite-style code for account creation in hosted/profile deployments.
- Reads deployment hardening settings for trusted hosts, allowed browser origins, secure cookies, and the explicit unsafe-public-no-auth override.
- Parses `VANTAGE_V5_NEXUS_INCLUDE` and `VANTAGE_V5_NEXUS_EXCLUDE` as comma-separated allow/deny lists.
