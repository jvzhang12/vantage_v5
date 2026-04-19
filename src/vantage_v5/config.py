from __future__ import annotations

import os
from dataclasses import dataclass
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

    @classmethod
    def from_env(cls) -> "AppConfig":
        repo_root = Path(__file__).resolve().parents[2]
        load_dotenv(repo_root / ".env", override=False)
        return cls(
            repo_root=repo_root,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("VANTAGE_V5_MODEL", "gpt-4.1"),
            port=int(os.getenv("VANTAGE_V5_PORT", "8005")),
            active_workspace=os.getenv(
                "VANTAGE_V5_ACTIVE_WORKSPACE",
                _default_active_workspace(repo_root),
            ),
            nexus_root=_optional_path(os.getenv("VANTAGE_V5_NEXUS_ROOT")),
            nexus_include_paths=_csv_env("VANTAGE_V5_NEXUS_INCLUDE"),
            nexus_exclude_paths=_csv_env("VANTAGE_V5_NEXUS_EXCLUDE"),
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


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()
