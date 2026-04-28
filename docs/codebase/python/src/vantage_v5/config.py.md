# `src/vantage_v5/config.py`

Environment-backed configuration layer for Vantage V5. It centralizes repo/data paths, API credentials, host/port selection, optional Basic Auth, optional multi-user credential maps, workspace defaults, and Nexus include/exclude controls.

## Purpose

- Load `.env` from the repository root.
- Build a frozen `AppConfig` object from environment variables.
- Provide defaults when explicit env vars are missing, including the active workspace ID.

## Key Classes / Functions

- `AppConfig`: frozen dataclass with:
  - `repo_root`
  - `openai_api_key`
  - `model`
  - `host`
  - `port`
  - `active_workspace`
  - `nexus_root`
  - `nexus_include_paths`
  - `nexus_exclude_paths`
  - `auth_username`
  - `auth_password`
  - `auth_users`
- `AppConfig.from_env()`: reads environment variables and constructs the config.
- `_default_active_workspace(repo_root)`: reads `state/active_workspace.json` if present, otherwise falls back to `v5-milestone-1`.
- `_csv_env(name)`: parses comma-separated env vars into trimmed string lists.
- `_optional_path(value)`: expands a path string into `Path | None`.
- `_auth_users_from_env(repo_root)`: loads an optional username/password map from `VANTAGE_V5_AUTH_USERS_JSON` or `VANTAGE_V5_AUTH_USERS_FILE`.

## Major Dependencies

- `os`
- `json`
- `pathlib.Path`
- `dataclasses.dataclass`
- `dotenv.load_dotenv`

## Notable Behavior

- Treats the repository root as two parents above this file, so path resolution is stable relative to the package layout.
- Loads `.env` without overriding already-set environment variables.
- Loads the package-root `.env` first, then an overridden `VANTAGE_V5_REPO_ROOT/.env` when `VANTAGE_V5_REPO_ROOT` points at a separate persistent data directory.
- Defaults `VANTAGE_V5_MODEL` to `gpt-4.1`, `VANTAGE_V5_HOST` to `127.0.0.1`, and `VANTAGE_V5_PORT` to `8005`.
- Reads `VANTAGE_V5_ACTIVE_WORKSPACE` first, but can infer it from `state/active_workspace.json` if unset.
- Enables single shared HTTP Basic Auth when `VANTAGE_V5_AUTH_PASSWORD` is set, or multi-user profile auth when `VANTAGE_V5_AUTH_USERS_JSON` / `VANTAGE_V5_AUTH_USERS_FILE` is set; local development remains unauthenticated by default.
- Parses `VANTAGE_V5_NEXUS_INCLUDE` and `VANTAGE_V5_NEXUS_EXCLUDE` as comma-separated allow/deny lists.
