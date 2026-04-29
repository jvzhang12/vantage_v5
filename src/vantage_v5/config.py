from __future__ import annotations

import os
from dataclasses import dataclass, field
import json
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class AppConfig:
    repo_root: Path
    openai_api_key: str | None
    model: str
    port: int
    active_workspace: str
    nexus_root: Path | None
    nexus_include_paths: list[str]
    nexus_exclude_paths: list[str]
    canonical_root: Path | None = None
    host: str = "127.0.0.1"
    auth_username: str = "vantage"
    auth_password: str | None = None
    auth_users: dict[str, str] = field(default_factory=dict)
    allowed_hosts: list[str] = field(default_factory=list)
    allowed_origins: list[str] = field(default_factory=list)
    cookie_secure: bool = False
    allow_unsafe_public_no_auth: bool = False

    @classmethod
    def from_env(cls) -> "AppConfig":
        default_repo_root = Path(__file__).resolve().parents[2]
        load_dotenv(default_repo_root / ".env", override=False)
        repo_root = _optional_path(os.getenv("VANTAGE_V5_REPO_ROOT")) or default_repo_root
        load_dotenv(repo_root / ".env", override=False)
        return cls(
            repo_root=repo_root,
            canonical_root=_optional_path(os.getenv("VANTAGE_V5_CANONICAL_ROOT")) or default_repo_root / "canonical",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("VANTAGE_V5_MODEL", "gpt-4.1"),
            host=os.getenv("VANTAGE_V5_HOST", "127.0.0.1"),
            port=int(os.getenv("VANTAGE_V5_PORT", "8005")),
            active_workspace=os.getenv(
                "VANTAGE_V5_ACTIVE_WORKSPACE",
                _default_active_workspace(repo_root),
            ),
            nexus_root=_optional_path(os.getenv("VANTAGE_V5_NEXUS_ROOT")),
            nexus_include_paths=_csv_env("VANTAGE_V5_NEXUS_INCLUDE"),
            nexus_exclude_paths=_csv_env("VANTAGE_V5_NEXUS_EXCLUDE"),
            auth_username=os.getenv("VANTAGE_V5_AUTH_USERNAME", "vantage"),
            auth_password=os.getenv("VANTAGE_V5_AUTH_PASSWORD") or None,
            auth_users=_auth_users_from_env(repo_root),
            allowed_hosts=_csv_env("VANTAGE_V5_ALLOWED_HOSTS"),
            allowed_origins=_csv_env("VANTAGE_V5_ALLOWED_ORIGINS"),
            cookie_secure=_bool_env("VANTAGE_V5_COOKIE_SECURE"),
            allow_unsafe_public_no_auth=_bool_env("VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH"),
        )


def _default_active_workspace(repo_root: Path) -> str:
    state_path = repo_root / "state" / "active_workspace.json"
    if state_path.exists():
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        workspace_id = payload.get("active_workspace_id")
        if workspace_id:
            return str(workspace_id)
    return "v5-milestone-1"


def _csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


def _auth_users_from_env(repo_root: Path) -> dict[str, str]:
    raw_json = os.getenv("VANTAGE_V5_AUTH_USERS_JSON", "").strip()
    users_file = _optional_path(os.getenv("VANTAGE_V5_AUTH_USERS_FILE"))
    if raw_json:
        payload = json.loads(raw_json)
    elif users_file:
        path = users_file if users_file.is_absolute() else repo_root / users_file
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("VANTAGE_V5_AUTH_USERS_JSON or VANTAGE_V5_AUTH_USERS_FILE must contain a JSON object.")
    users: dict[str, str] = {}
    for username, password in payload.items():
        normalized_username = str(username).strip()
        normalized_password = str(password)
        if normalized_username and normalized_password:
            users[normalized_username] = normalized_password
    return users
