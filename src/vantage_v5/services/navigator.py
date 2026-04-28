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
    preserve_pinned_context: bool | None = None
    pinned_context_reason: str | None = None
    preserve_selected_record: bool | None = None
    selected_record_reason: str | None = None
    control_panel: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        preserve_pinned_context = self.preserve_pinned_context
        if preserve_pinned_context is None:
            preserve_pinned_context = self.preserve_selected_record
        pinned_context_reason = self.pinned_context_reason
        if pinned_context_reason is None:
            pinned_context_reason = self.selected_record_reason
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "reason": self.reason,
            "comparison_question": self.comparison_question,
            "branch_count": self.branch_count,
            "branch_labels": list(self.branch_labels),
            "whiteboard_mode": self.whiteboard_mode,
            "preserve_pinned_context": preserve_pinned_context,
            "pinned_context_reason": pinned_context_reason,
            "preserve_selected_record": preserve_pinned_context,
            "selected_record_reason": pinned_context_reason,
            "control_panel": _normalize_control_panel(self.control_panel),
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
        pinned_context_id: str | None = None,
        pinned_context: dict[str, object] | None = None,
        selected_record_id: str | None = None,
        selected_record: dict[str, object] | None = None,
        pending_workspace_update: dict[str, object] | None = None,
        continuity_context: dict[str, object] | None = None,
    ) -> NavigationDecision:
        if not self.client:
            return self._fallback_decision("OpenAI mode is unavailable, so the turn stays in normal chat.")
        try:
            return self._openai_route(
                user_message=user_message,
                history=history,
                workspace=workspace,
                requested_whiteboard_mode=requested_whiteboard_mode,
                pinned_context_id=pinned_context_id,
                pinned_context=pinned_context,
                selected_record_id=selected_record_id,
                selected_record=selected_record,
                pending_workspace_update=pending_workspace_update,
                continuity_context=continuity_context,
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
        pinned_context_id: str | None,
        pinned_context: dict[str, object] | None,
        selected_record_id: str | None,
        selected_record: dict[str, object] | None,
        pending_workspace_update: dict[str, object] | None,
        continuity_context: dict[str, object] | None,
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
            "pinned_context_id": pinned_context_id or selected_record_id,
            "pinned_context": pinned_context or selected_record,
            "pending_workspace_update": pending_workspace_update,
            "continuity_context": continuity_context,
            "allowed_modes": ["chat", "scenario_lab"],
            "allowed_whiteboard_modes": ["chat", "offer", "draft", "auto"],
            "available_control_panel_actions": [
                "respond",
                "recall",
                "open_whiteboard",
                "draft_whiteboard",
                "open_scenario_lab",
                "apply_protocol",
                "inspect_context",
                "save_whiteboard",
                "publish_artifact",
                "manage_experiment",
                "ask_clarification",
            ],
            "available_protocol_kinds": ["email", "research_paper", "scenario_lab"],
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are the Vantage V5 turn interpreter. "
                "Decide whether the turn should stay in normal chat or enter Scenario Lab, whether the pinned context should be preserved as continuity context for this turn, and whether normal chat should stay in chat, invite whiteboard collaboration, or draft directly into the whiteboard. "
                "Also return a control_panel object that describes the product controls you would press. "
                "Think of the control panel as the canonical plan: actions are button presses, working_memory_queries are context you want the system to retrieve or keep active, and response_call describes whether another LLM response should be generated after context is assembled. "
                "Only choose actions from available_control_panel_actions. "
                "For every control_panel action, include protocol_kind as null unless the action type is apply_protocol. "
                "When action type is apply_protocol, protocol_kind is required and must be one of email, research_paper, or scenario_lab. "
                "For Scenario Lab comparisons, apply the scenario_lab protocol so first-principles, counterfactual, causal, tradeoff, and assumption-surfacing guidance can enter working memory. "
                "For email drafting, apply the email protocol when a reusable email protocol should guide the draft. "
                "For research-paper drafting or revision, apply the research_paper protocol when that reusable protocol should guide the work. "
                "Do not ask deterministic code to infer user intent later; put the interpretation into the control_panel. "
                "Scenario Lab is for structured comparison across alternative futures, plans, or options that should become durable scenario branches and a comparison artifact. "
                "Use scenario_lab only when the user is clearly asking for comparative what-if reasoning, option analysis, or branchable alternatives. "
                "The workspace payload may include scenario metadata when the currently open workspace is already a saved scenario branch. "
                "Treat that as explicit metadata about the open workspace, not as a second hidden continuity system. "
                "A branch workspace being open does not by itself mean the user wants a fresh Scenario Lab rerun. "
                "If a pinned context is already in focus, preserve it when the current turn is best understood as a follow-up, clarification, recommendation request, branch-specific elaboration, rule application, or other continuity question about that pinned item. "
                "If a pinned context is already in focus, especially a saved comparison or scenario artifact, prefer chat for follow-up questions like recommendations, clarifications, risk explanation, or branch-specific elaboration. "
                "If the open workspace or pinned context already refers to an existing scenario branch or comparison artifact, prefer chat for revisit, continuation, or branch-specific follow-up unless the user explicitly asks for new branches, a rerun, or a new comparison set. "
                "Only re-enter Scenario Lab when the user explicitly asks to create new branches, rerun the comparison, or compare a new option set. "
                "The payload may include pending_workspace_update from the immediately previous turn. "
                "When it exists, treat it as live context for a still-open whiteboard invitation or draft. "
                "If the current user message accepts, confirms, refines, or continues that pending whiteboard flow, choose whiteboard_mode='draft' rather than repeating the invitation. "
                "If the user both accepts the pending offer and states a future preference, still treat the current turn as acceptance unless they clearly decline the current work product. "
                "The payload may also include continuity_context with the current whiteboard, a very short recent-whiteboards list, the strongest last-turn referenced saved record, and a short last-turn recall shortlist. "
                "Use that continuity context to resolve deictic follow-ups like 'that one', 'the other email', or 'pull that up on the whiteboard' without overfitting to older history. "
                "Prefer the current whiteboard when the user is clearly continuing the active draft. "
                "Prefer last_turn_referenced_record over generic recent-whiteboard recency when the user is referring back to a recently surfaced saved item. "
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
                            "pinned_context_id": {"type": ["string", "null"]},
                            "pinned_context": {"type": ["object", "null"]},
                            "preserve_pinned_context": {"type": ["boolean", "null"]},
                            "pinned_context_reason": {"type": ["string", "null"]},
                            "control_panel": {
                                "type": ["object", "null"],
                                "additionalProperties": True,
                                "properties": {
                                    "actions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": True,
                                            "properties": {
                                                "type": {"type": "string"},
                                                "protocol_kind": {
                                                    "type": ["string", "null"],
                                                    "enum": ["email", "research_paper", "scenario_lab", None],
                                                },
                                                "reason": {"type": ["string", "null"]},
                                            },
                                            "required": ["type", "protocol_kind"],
                                        },
                                    },
                                    "working_memory_queries": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "response_call": {
                                        "type": ["object", "null"],
                                        "additionalProperties": True,
                                    },
                                },
                            },
                        },
                        "required": [
                            "mode",
                            "confidence",
                            "reason",
                            "comparison_question",
                            "branch_count",
                            "branch_labels",
                            "whiteboard_mode",
                            "pinned_context_id",
                            "pinned_context",
                            "preserve_pinned_context",
                            "pinned_context_reason",
                            "control_panel",
                        ],
                    },
                }
            },
        )
        result = json.loads(response.output_text)
        preserve_pinned_context = _normalize_preserve_pinned_context(
            result.get("preserve_pinned_context"),
            result.get("preserve_selected_record"),
        )
        pinned_context_reason = _normalize_reason(
            result.get("pinned_context_reason"),
            result.get("selected_record_reason"),
        )
        return NavigationDecision(
            mode=result.get("mode") or "chat",
            confidence=max(0.0, min(1.0, float(result.get("confidence", 0.0)))),
            reason=str(result.get("reason") or "No routing rationale returned."),
            comparison_question=(str(result["comparison_question"]).strip() if result.get("comparison_question") else None),
            branch_count=max(0, int(result.get("branch_count", 0))),
            branch_labels=[str(label).strip() for label in result.get("branch_labels", []) if str(label).strip()],
            whiteboard_mode=_normalize_whiteboard_mode_hint(result.get("whiteboard_mode")),
            preserve_pinned_context=preserve_pinned_context,
            pinned_context_reason=pinned_context_reason,
            preserve_selected_record=preserve_pinned_context,
            selected_record_reason=pinned_context_reason,
            control_panel=_normalize_control_panel(result.get("control_panel")),
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
            preserve_pinned_context=None,
            pinned_context_reason=None,
            preserve_selected_record=None,
            selected_record_reason=None,
            control_panel={
                "actions": [
                    {
                        "type": "respond",
                        "reason": "Fallback routing keeps the turn in chat without pressing other product controls.",
                    }
                ],
                "working_memory_queries": [],
                "response_call": {"type": "chat_response", "after_working_memory": True},
            },
        )


def _normalize_whiteboard_mode_hint(value: object) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"chat", "offer", "draft", "auto"}:
        return normalized
    return None


def _normalize_preserve_pinned_context(value: object, fallback: object | None = None) -> bool | None:
    if value is None:
        value = fallback
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


def _normalize_reason(value: object, fallback: object | None = None) -> str | None:
    candidate = value if value is not None else fallback
    if candidate is None:
        return None
    normalized = str(candidate).strip()
    return normalized or None


def _normalize_control_panel(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    raw_actions = value.get("actions")
    actions: list[dict[str, object]] = []
    if isinstance(raw_actions, list):
        for action in raw_actions:
            if not isinstance(action, dict):
                continue
            action_type = str(action.get("type") or "").strip()
            if not action_type:
                continue
            normalized_action = dict(action)
            normalized_action["type"] = action_type
            actions.append(normalized_action)
    raw_queries = value.get("working_memory_queries")
    working_memory_queries: list[str] = []
    if isinstance(raw_queries, list):
        working_memory_queries = [
            query
            for query in (" ".join(str(item).strip().split()) for item in raw_queries)
            if query
        ]
    response_call = value.get("response_call")
    return {
        "actions": actions,
        "working_memory_queries": working_memory_queries,
        "response_call": response_call if isinstance(response_call, dict) else None,
    }
