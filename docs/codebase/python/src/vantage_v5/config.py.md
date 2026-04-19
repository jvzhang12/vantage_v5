# `src/vantage_v5/config.py`

Environment-backed configuration layer for Vantage V5. It centralizes repo paths, API credentials, model/port selection, workspace defaults, and Nexus include/exclude controls.

## Purpose

- Load `.env` from the repository root.
- Build a frozen `AppConfig` object from environment variables.
- Provide defaults when explicit env vars are missing, including the active workspace ID.

## Key Classes / Functions

- `AppConfig`: frozen dataclass with:
  - `repo_root`
  - `openai_api_key`
  - `model`
  - `port`
  - `active_workspace`
  - `nexus_root`
  - `nexus_include_paths`
  - `nexus_exclude_paths`
- `AppConfig.from_env()`: reads environment variables and constructs the config.
- `_default_active_workspace(repo_root)`: reads `state/active_workspace.json` if present, otherwise falls back to `v5-milestone-1`.
- `_csv_env(name)`: parses comma-separated env vars into trimmed string lists.
- `_optional_path(value)`: expands a path string into `Path | None`.

## Major Dependencies

- `os`
- `json`
- `pathlib.Path`
- `dataclasses.dataclass`
- `dotenv.load_dotenv`

## Notable Behavior

- Treats the repository root as two parents above this file, so path resolution is stable relative to the package layout.
- Loads `.env` without overriding already-set environment variables.
- Defaults `VANTAGE_V5_MODEL` to `gpt-4.1` and `VANTAGE_V5_PORT` to `8005`.
- Reads `VANTAGE_V5_ACTIVE_WORKSPACE` first, but can infer it from `state/active_workspace.json` if unset.
- Parses `VANTAGE_V5_NEXUS_INCLUDE` and `VANTAGE_V5_NEXUS_EXCLUDE` as comma-separated allow/deny lists.
