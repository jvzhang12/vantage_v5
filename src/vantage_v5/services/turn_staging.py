from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


MIN_STAGE_ATTEMPTS = 1
MAX_STAGE_ATTEMPTS = 3

FORBIDDEN_PROGRESS_TEXT = (
    "chain-of-thought",
    "scratchpad",
    "system prompt",
    "developer message",
    "raw provider",
    "stack trace",
    "traceback",
    "json schema",
    "openai",
    "gpt-",
)
_HIDDEN_KEYS = {
    "chain_of_thought",
    "debug",
    "developer",
    "messages",
    "model",
    "prompt",
    "provider",
    "raw",
    "reasoning",
    "schema",
    "system",
    "trace",
}


@dataclass(frozen=True, slots=True)
class TurnStage:
    stage_id: str
    task_kind: str
    contract: str | dict[str, Any]
    max_attempts: int = 1
    public_summary: str = ""
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self) -> None:
        bounded_attempts = _bounded_attempts(self.max_attempts)
        object.__setattr__(self, "max_attempts", bounded_attempts)
        object.__setattr__(self, "stage_id", _slug_text(self.stage_id) or "turn_stage")
        object.__setattr__(self, "task_kind", _slug_text(self.task_kind) or "chat")
        object.__setattr__(self, "contract", sanitize_public_value(self.contract) if isinstance(self.contract, dict) else _slug_text(self.contract))
        public_summary = self.public_summary or self.reason
        object.__setattr__(self, "public_summary", sanitize_stage_text(public_summary, limit=180))
        object.__setattr__(self, "reason", sanitize_stage_text(self.reason or public_summary, limit=180))
        object.__setattr__(self, "metadata", sanitize_public_value(self.metadata) or {})

    def to_dict(self) -> dict[str, Any]:
        label = _stage_label(self)
        return {
            "stage_id": self.stage_id,
            "key": self.stage_id,
            "label": label,
            "status": "staged",
            "message": self.public_summary,
            "task_kind": self.task_kind,
            "contract": self.contract,
            "max_attempts": self.max_attempts,
            "public_summary": self.public_summary,
            "retryable": self.retryable,
            "metadata": dict(self.metadata),
            "reason": self.reason,
        }

    def to_payload(self) -> dict[str, Any]:
        label = _stage_label(self)
        return {
            "stage_id": self.stage_id,
            "key": self.stage_id,
            "label": label,
            "status": "staged",
            "message": self.public_summary,
            "task_kind": self.task_kind,
            "contract": self.contract,
            "max_attempts": self.max_attempts,
            "reason": self.reason or self.public_summary,
        }


@dataclass(frozen=True, slots=True)
class StageProgressEvent:
    event_id: str
    label: str
    status: str = "completed"
    message: str = ""
    attempt: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.event_id,
            "label": sanitize_stage_text(self.label, limit=60),
            "status": self.status if self.status in {"pending", "running", "completed", "retrying", "failed"} else "completed",
            "message": sanitize_stage_text(self.message, limit=180),
        }
        if self.attempt is not None:
            payload["attempt"] = self.attempt
        return payload

    def to_payload(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(frozen=True, slots=True)
class StageAuditResult:
    accepted: bool
    status: str
    issues: tuple[str, ...] = ()
    retry_instruction: str = ""

    @property
    def retryable(self) -> bool:
        return self.status == "retry"

    @property
    def terminal(self) -> bool:
        return self.status == "terminal"

    def to_dict(self) -> dict[str, Any]:
        summary = "Accepted" if self.accepted else ("Retrying" if self.retryable else "Needs attention")
        return {
            "accepted": self.accepted,
            "status": self.status,
            "summary": summary,
            "result": "retryable" if self.retryable else self.status,
            "retryable": self.retryable,
            "terminal": self.terminal,
            "issues": [sanitize_stage_text(issue, limit=120) for issue in self.issues],
            "retry_instruction": sanitize_stage_text(self.retry_instruction, limit=240),
        }

    def to_payload(self) -> dict[str, Any]:
        return self.to_dict()


def audit_stage_output(
    parsed_output: dict[str, Any] | None,
    stage: TurnStage,
    *,
    attempt: int = 1,
) -> StageAuditResult:
    issues = _audit_issues(parsed_output, stage)
    if not issues:
        return StageAuditResult(accepted=True, status="accepted")
    terminal = _bounded_attempts(attempt) >= stage.max_attempts
    return StageAuditResult(
        accepted=False,
        status="terminal" if terminal else "retry",
        issues=tuple(issues),
        retry_instruction="" if terminal else _retry_instruction(stage, issues),
    )


def payload_for_stage(value: TurnStage | dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(value, TurnStage):
        return value.to_payload()
    sanitized = sanitize_public_value(value)
    return sanitized if isinstance(sanitized, dict) else None


def payload_for_progress(value: StageProgressEvent | dict[str, Any] | list[dict[str, Any]] | None) -> Any:
    if isinstance(value, StageProgressEvent):
        return value.to_payload()
    sanitized = sanitize_public_value(value)
    return sanitized if isinstance(sanitized, dict | list) else None


def payload_for_audit(value: StageAuditResult | dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(value, StageAuditResult):
        return value.to_payload()
    sanitized = sanitize_public_value(value)
    return sanitized if isinstance(sanitized, dict) else None


def sanitize_public_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            public_key = _slug_text(key)
            if not public_key or public_key in _HIDDEN_KEYS:
                continue
            normalized = sanitize_public_value(item)
            if normalized in (None, "", [], {}):
                continue
            cleaned[public_key] = normalized
        return cleaned
    if isinstance(value, list):
        cleaned_list = [sanitize_public_value(item) for item in value]
        return [item for item in cleaned_list if item not in (None, "", [], {})]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return sanitize_stage_text(value, limit=500)


def build_turn_stage(
    *,
    navigation_mode: str,
    whiteboard_mode: str,
    public_summary: str = "",
) -> TurnStage:
    normalized_navigation = str(navigation_mode or "chat").strip().lower() or "chat"
    normalized_whiteboard = str(whiteboard_mode or "auto").strip().lower() or "auto"
    if normalized_navigation == "scenario_lab":
        return TurnStage(
            stage_id="scenario_lab:compare",
            task_kind="scenario_lab",
            contract="scenario_lab",
            max_attempts=1,
            public_summary=public_summary or "Preparing a scenario comparison.",
            retryable=False,
        )
    if normalized_whiteboard == "draft":
        return TurnStage(
            stage_id="chat:whiteboard_draft",
            task_kind="chat",
            contract="whiteboard_draft",
            max_attempts=2,
            public_summary=public_summary or "Preparing a whiteboard draft.",
            retryable=True,
        )
    if normalized_whiteboard == "offer":
        return TurnStage(
            stage_id="chat:whiteboard_offer",
            task_kind="chat",
            contract="whiteboard_offer",
            max_attempts=2,
            public_summary=public_summary or "Preparing a whiteboard invitation.",
            retryable=True,
        )
    return TurnStage(
        stage_id="chat:response",
        task_kind="chat",
        contract="chat_response",
        max_attempts=1,
        public_summary=public_summary or "Preparing a response.",
        retryable=False,
    )


def stage_progress_event(
    event_id: str,
    label: str,
    *,
    status: str = "completed",
    message: str = "",
    attempt: int | None = None,
) -> dict[str, Any]:
    return StageProgressEvent(
        event_id=event_id,
        label=label,
        status=status,
        message=message,
        attempt=attempt,
    ).to_dict()


def initial_stage_progress(stage: TurnStage) -> list[dict[str, Any]]:
    return [
        stage_progress_event(
            "stage_context",
            "Prepared context",
            message=stage.public_summary,
        )
    ]


def audit_stage_response(
    *,
    stage: TurnStage | None,
    assistant_message: str,
    has_workspace_draft: bool,
    has_workspace_offer: bool,
    attempt: int,
) -> StageAuditResult:
    if stage is None or stage.contract == "chat_response":
        return StageAuditResult(accepted=True, status="accepted")
    if stage.contract == "scenario_lab":
        return StageAuditResult(accepted=True, status="accepted")
    if _contains_forbidden_text(assistant_message):
        return StageAuditResult(
            accepted=False,
            status="terminal",
            issues=("internal_or_provider_text",),
            retry_instruction="",
        )
    if stage.contract == "whiteboard_draft" and not has_workspace_draft:
        return _contract_failure(
            stage=stage,
            attempt=attempt,
            issue="missing_whiteboard_draft",
            retry_instruction=(
                "Return a concise CHAT_RESPONSE plus a WHITEBOARD_DRAFT containing the complete Markdown draft. "
                "Do not only offer the whiteboard."
            ),
        )
    if stage.contract == "whiteboard_offer" and not has_workspace_offer:
        return _contract_failure(
            stage=stage,
            attempt=attempt,
            issue="missing_whiteboard_offer",
            retry_instruction=(
                "Return a concise CHAT_RESPONSE plus a WHITEBOARD_OFFER describing the draft that can be opened. "
                "Do not provide the full draft in chat."
            ),
        )
    return StageAuditResult(accepted=True, status="accepted")


def sanitize_stage_text(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    lowered = text.lower()
    if any(term in lowered for term in FORBIDDEN_PROGRESS_TEXT):
        text = "Checked the response against the turn contract."
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _audit_issues(parsed_output: dict[str, Any] | None, stage: TurnStage) -> list[str]:
    if not isinstance(parsed_output, dict):
        return ["Parsed output must be an object."]
    issues: list[str] = []
    contract = stage.contract if isinstance(stage.contract, dict) else {}
    workspace_update = parsed_output.get("workspace_update")
    expected_type = _expected_workspace_update_type(stage)
    workspace_type_matches = False
    expects_workspace_update = bool(contract.get("requires_workspace_update")) or expected_type is not None
    if expects_workspace_update and not isinstance(workspace_update, dict):
        issues.append("Missing workspace_update object.")

    if expected_type and isinstance(workspace_update, dict):
        actual_type = _slug_text(workspace_update.get("type"))
        workspace_type_matches = actual_type == expected_type
        if not workspace_type_matches:
            issues.append(f"workspace_update.type must be {expected_type}.")

    if expected_type == "draft_whiteboard" and isinstance(workspace_update, dict) and workspace_type_matches:
        title = str(workspace_update.get("title") or "").strip()
        content = str(workspace_update.get("content") or "").strip()
        min_content_chars = _positive_int(contract.get("min_content_chars"), default=1)
        if not title:
            issues.append("Draft whiteboard update needs a title.")
        if len(content) < min_content_chars:
            issues.append("Draft whiteboard update needs draft content.")

    if expected_type == "offer_whiteboard" and isinstance(workspace_update, dict) and workspace_type_matches:
        summary = str(workspace_update.get("summary") or "").strip()
        if not summary:
            issues.append("Offer whiteboard update needs a public summary.")

    for field_name in _string_list(contract.get("required_fields")):
        if parsed_output.get(field_name) in (None, "", [], {}):
            issues.append(f"Missing required field: {field_name}.")
    return issues


def _expected_workspace_update_type(stage: TurnStage) -> str | None:
    contract = stage.contract if isinstance(stage.contract, dict) else {}
    contract_type = _slug_text(contract.get("workspace_update_type"))
    if contract_type in {"draft_whiteboard", "offer_whiteboard"}:
        return contract_type
    if stage.contract == "whiteboard_draft" or stage.task_kind == "whiteboard_draft":
        return "draft_whiteboard"
    if stage.contract == "whiteboard_offer" or stage.task_kind == "whiteboard_offer":
        return "offer_whiteboard"
    return None


def _retry_instruction(stage: TurnStage, issues: list[str]) -> str:
    issue_text = "; ".join(issues)
    if _expected_workspace_update_type(stage) == "draft_whiteboard":
        return f"Return a draft_whiteboard workspace_update with title and content. Fix: {issue_text}"
    if _expected_workspace_update_type(stage) == "offer_whiteboard":
        return f"Return an offer_whiteboard workspace_update with a public summary. Fix: {issue_text}"
    return f"Repair the staged response contract. Fix: {issue_text}"


def _bounded_attempts(value: Any) -> int:
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        attempts = 1
    return min(MAX_STAGE_ATTEMPTS, max(MIN_STAGE_ATTEMPTS, attempts))


def _positive_int(value: Any, *, default: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, normalized)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_slug_text(item) for item in value if _slug_text(item)]


def _slug_text(value: Any) -> str:
    return "_".join(str(value or "").strip().lower().split())


def _contract_failure(
    *,
    stage: TurnStage,
    attempt: int,
    issue: str,
    retry_instruction: str,
) -> StageAuditResult:
    if stage.retryable and attempt < stage.max_attempts:
        return StageAuditResult(
            accepted=False,
            status="retry",
            issues=(issue,),
            retry_instruction=retry_instruction,
        )
    return StageAuditResult(
        accepted=False,
        status="terminal",
        issues=(issue,),
        retry_instruction="",
    )


def _contains_forbidden_text(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(term in lowered for term in FORBIDDEN_PROGRESS_TEXT)


def _stage_label(stage: TurnStage) -> str:
    contract = stage.contract if isinstance(stage.contract, str) else stage.task_kind
    return {
        "whiteboard_draft": "Whiteboard draft",
        "whiteboard_offer": "Whiteboard offer",
        "scenario_lab": "Scenario Lab",
        "chat_response": "Chat response",
    }.get(contract, str(contract or "Turn stage").replace("_", " ").title())
