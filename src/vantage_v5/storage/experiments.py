from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil

from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(frozen=True, slots=True)
class ExperimentSession:
    session_id: str
    root: Path
    concepts_dir: Path
    memories_dir: Path
    memory_trace_dir: Path
    artifacts_dir: Path
    workspaces_dir: Path
    state_path: Path
    traces_dir: Path


class ExperimentSessionManager:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.sessions_dir = state_dir / "experiments"
        self.active_session_path = state_dir / "active_experiment.json"

    def get_active_session(self) -> ExperimentSession | None:
        if not self.active_session_path.exists():
            return None
        payload = json.loads(self.active_session_path.read_text(encoding="utf-8"))
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
            return None
        session = self._build_session(session_id)
        if not session.root.exists():
            self.active_session_path.unlink(missing_ok=True)
            return None
        return session

    def start(self, *, seed_workspace: WorkspaceDocument | None = None) -> ExperimentSession:
        started_at = datetime.now(tz=UTC)
        session_id = f"experiment-{started_at.strftime('%Y%m%d-%H%M%S')}"
        session = self._build_session(session_id)
        session.concepts_dir.mkdir(parents=True, exist_ok=True)
        session.memories_dir.mkdir(parents=True, exist_ok=True)
        session.memory_trace_dir.mkdir(parents=True, exist_ok=True)
        session.artifacts_dir.mkdir(parents=True, exist_ok=True)
        session.workspaces_dir.mkdir(parents=True, exist_ok=True)
        session.traces_dir.mkdir(parents=True, exist_ok=True)
        workspace_text = (
            seed_workspace.content
            if seed_workspace
            else (
                "# Experiment Workspace\n\n"
                "This is a temporary sandbox. Notes and concepts created here stay inside this session.\n"
            )
        )
        workspace_id = "experiment-workspace"
        (session.workspaces_dir / f"{workspace_id}.md").write_text(workspace_text, encoding="utf-8")
        session.state_path.parent.mkdir(parents=True, exist_ok=True)
        session.state_path.write_text(
            json.dumps(
                {
                    "active_workspace_id": workspace_id,
                    "active_workspace_path": f"workspaces/{workspace_id}.md",
                    "status": "active",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.active_session_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_session_path.write_text(
            json.dumps(
                {
                    "active": True,
                    "session_id": session_id,
                    "started_at": started_at.isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return session

    def end(self) -> dict[str, str | bool] | None:
        session = self.get_active_session()
        if not session:
            return None
        payload = {
            "ended": True,
            "session_id": session.session_id,
        }
        self.active_session_path.unlink(missing_ok=True)
        shutil.rmtree(session.root, ignore_errors=True)
        return payload

    def _build_session(self, session_id: str) -> ExperimentSession:
        root = self.sessions_dir / session_id
        return ExperimentSession(
            session_id=session_id,
            root=root,
            concepts_dir=root / "concepts",
            memories_dir=root / "memories",
            memory_trace_dir=root / "memory_trace",
            artifacts_dir=root / "artifacts",
            workspaces_dir=root / "workspaces",
            state_path=root / "state" / "active_workspace.json",
            traces_dir=root / "traces",
        )
