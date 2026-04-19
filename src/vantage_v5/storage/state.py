from __future__ import annotations

import json
from pathlib import Path


class ActiveWorkspaceStateStore:
    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path

    def get_active_workspace_id(self, *, default_workspace_id: str) -> str:
        if not self.state_path.exists():
            return default_workspace_id
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return str(payload.get("active_workspace_id") or default_workspace_id)

    def set_active_workspace_id(self, workspace_id: str) -> dict:
        payload = {
            "active_workspace_id": workspace_id,
            "active_workspace_path": f"workspaces/{workspace_id}.md",
            "status": "active",
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
