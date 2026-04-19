from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json

from openai import OpenAI

from vantage_v5.storage.workspaces import WorkspaceDocument


@dataclass(slots=True)
class NavigationDecision:
    mode: str
    confidence: float
    reason: str
    comparison_question: str | None = None
    branch_count: int = 0
    branch_labels: list[str] = field(default_factory=list)
    whiteboard_mode: str | None = None
    preserve_selected_record: bool | None = None
    selected_record_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "reason": self.reason,
            "comparison_question": self.comparison_question,
            "branch_count": self.branch_count,
            "branch_labels": list(self.branch_labels),
            "whiteboard_mode": self.whiteboard_mode,
            "preserve_selected_record": self.preserve_selected_record,
            "selected_record_reason": self.selected_record_reason,
        }


class NavigatorService:
    def __init__(self, *, model: str, openai_api_key: str | None) -> None:
        self.model = model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None

    def route_turn(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        workspace: WorkspaceDocument,
        requested_whiteboard_mode: str = "auto",
        selected_record_id: str | None = None,
        selected_record: dict[str, object] | None = None,
        pending_workspace_update: dict[str, object] | None = None,
    ) -> NavigationDecision:
        if not self.client:
            return self._fallback_decision("OpenAI mode is unavailable, so the turn stays in normal chat.")
        try:
            return self._openai_route(
                user_message=user_message,
                history=history,
                workspace=workspace,
                requested_whiteboard_mode=requested_whiteboard_mode,
                selected_record_id=selected_record_id,
                selected_record=selected_record,
                pending_workspace_update=pending_workspace_update,
            )
        except Exception:
            return self._fallback_decision("Navigator routing fell back to normal chat after an unavailable or invalid model response.")

    def _openai_route(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        workspace: WorkspaceDocument,
        requested_whiteboard_mode: str,
        selected_record_id: str | None,
        selected_record: dict[str, object] | None,
        pending_workspace_update: dict[str, object] | None,
    ) -> NavigationDecision:
        payload = {
            "user_message": user_message,
            "recent_chat": history[-6:],
            "workspace": {
                "workspace_id": workspace.workspace_id,
                "title": workspace.title,
                "content_excerpt": workspace.content[:1600],
                "scenario_kind": (workspace.scenario_metadata or {}).get("scenario_kind"),
                "scenario": workspace.scenario_metadata,
            },
            "requested_whiteboard_mode": requested_whiteboard_mode,
            "selected_record_id": selected_record_id,
            "selected_record": selected_record,
            "pending_workspace_update": pending_workspace_update,
            "allowed_modes": ["chat", "scenario_lab"],
            "allowed_whiteboard_modes": ["chat", "offer", "draft", "auto"],
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage V5 turn interpreter. "
                "Decide whether the turn should stay in normal chat or enter Scenario Lab, whether the selected record should be preserved as continuity context for this turn, and whether normal chat should stay in chat, invite whiteboard collaboration, or draft directly into the whiteboard. "
                "Scenario Lab is for structured comparison across alternative futures, plans, or options that should become durable scenario branches and a comparison artifact. "
                "Use scenario_lab only when the user is clearly asking for comparative what-if reasoning, option analysis, or branchable alternatives. "
                "The workspace payload may include scenario metadata when the currently open workspace is already a saved scenario branch. "
                "Treat that as explicit metadata about the open workspace, not as a second hidden continuity system. "
                "A branch workspace being open does not by itself mean the user wants a fresh Scenario Lab rerun. "
                "If a selected record is already in focus, preserve it when the current turn is best understood as a follow-up, clarification, recommendation request, branch-specific elaboration, rule application, or other continuity question about that selected item. "
                "If a selected record is already in focus, especially a saved comparison or scenario artifact, prefer chat for follow-up questions like recommendations, clarifications, risk explanation, or branch-specific elaboration. "
                "If the open workspace or selected record already refers to an existing scenario branch or comparison artifact, prefer chat for revisit, continuation, or branch-specific follow-up unless the user explicitly asks for new branches, a rerun, or a new comparison set. "
                "Only re-enter Scenario Lab when the user explicitly asks to create new branches, rerun the comparison, or compare a new option set. "
                "The payload may include pending_workspace_update from the immediately previous turn. "
                "When it exists, treat it as live context for a still-open whiteboard invitation or draft. "
                "If the current user message accepts, confirms, refines, or continues that pending whiteboard flow, choose whiteboard_mode='draft' rather than repeating the invitation. "
                "If the user both accepts the pending offer and states a future preference, still treat the current turn as acceptance unless they clearly decline the current work product. "
                "For ordinary chat turns, choose whiteboard_mode='offer' when the user is asking for a concrete work product that should first invite whiteboard collaboration. "
                "If the current whiteboard already contains a live draft and the user is revising, updating, refining, or continuing that draft, choose whiteboard_mode='draft' rather than reopening or reoffering the whiteboard. "
                "Choose whiteboard_mode='draft' when the user is clearly continuing or explicitly requesting whiteboard drafting now. "
                "Choose whiteboard_mode='chat' when the turn should stay in plain chat. "
                "Choose whiteboard_mode='auto' only when the whiteboard decision is genuinely ambiguous and the chat model should decide from context. "
                "Respect the requested_whiteboard_mode when it is not auto, because that reflects an explicit UI choice. "
                "Use chat for ordinary questions, brainstorming, explanation, editing, or ambiguous requests. "
                "Be conservative. If there is meaningful ambiguity, choose chat."
            ),
            input=json.dumps(payload),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "navigation_decision",
                    "strict": False,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "mode": {
                                "type": "string",
                                "enum": ["chat", "scenario_lab"],
                            },
                            "confidence": {"type": "number"},
                            "reason": {"type": "string"},
                            "comparison_question": {"type": ["string", "null"]},
                            "branch_count": {"type": "integer"},
                            "branch_labels": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "whiteboard_mode": {"type": ["string", "null"]},
                            "preserve_selected_record": {"type": ["boolean", "null"]},
                            "selected_record_reason": {"type": ["string", "null"]},
                        },
                        "required": [
                            "mode",
                            "confidence",
                            "reason",
                            "comparison_question",
                            "branch_count",
                            "branch_labels",
                            "whiteboard_mode",
                            "preserve_selected_record",
                            "selected_record_reason",
                        ],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        return NavigationDecision(
            mode=result.get("mode") or "chat",
            confidence=max(0.0, min(1.0, float(result.get("confidence", 0.0)))),
            reason=str(result.get("reason") or "No routing rationale returned."),
            comparison_question=(str(result["comparison_question"]).strip() if result.get("comparison_question") else None),
            branch_count=max(0, int(result.get("branch_count", 0))),
            branch_labels=[str(label).strip() for label in result.get("branch_labels", []) if str(label).strip()],
            whiteboard_mode=_normalize_whiteboard_mode_hint(result.get("whiteboard_mode")),
            preserve_selected_record=_normalize_preserve_selected_record(result.get("preserve_selected_record")),
            selected_record_reason=(str(result["selected_record_reason"]).strip() if result.get("selected_record_reason") else None),
        )

    @staticmethod
    def _fallback_decision(reason: str) -> NavigationDecision:
        return NavigationDecision(
            mode="chat",
            confidence=0.0,
            reason=reason,
            comparison_question=None,
            branch_count=0,
            branch_labels=[],
            whiteboard_mode=None,
            preserve_selected_record=None,
            selected_record_reason=None,
        )


def _normalize_whiteboard_mode_hint(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"chat", "offer", "draft", "auto"}:
        return normalized
    return None


def _normalize_preserve_selected_record(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None
