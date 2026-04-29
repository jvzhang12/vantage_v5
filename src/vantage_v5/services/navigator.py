from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
import re

from openai import OpenAI

from vantage_v5.storage.workspaces import WorkspaceDocument


ALLOWED_CONTROL_PANEL_ACTIONS = {
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
}
ALLOWED_PROTOCOL_KINDS = {"email", "research_paper", "scenario_lab"}
WORK_PRODUCT_RE = re.compile(
    r"\b(?:draft|write|compose|plan|outline|create|build)\b.{0,120}\b(?:email|mail|message|memo|letter|itinerary|plan|checklist|agenda|paper|essay|introduction|intro|report|brief|document|draft)\b"
    r"|\b(?:email|memo|letter|itinerary|checklist|agenda|research paper|paper introduction|report|brief)\b",
    re.IGNORECASE,
)
CHAT_ONLY_RE = re.compile(r"\b(?:chat only|in chat only|keep (?:it|the full draft|this) in chat|answer directly in chat)\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b(?:email|mail|message|memo|letter)\b", re.IGNORECASE)
RESEARCH_PAPER_RE = re.compile(r"\b(?:research paper|paper introduction|paper intro|academic paper)\b", re.IGNORECASE)
EXPLICIT_WHITEBOARD_DRAFT_RE = re.compile(
    r"\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b"
    r"|\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:(?:a|the)\s+)?(?:(?:fresh|new|blank|empty|shared)\s+)?whiteboard\b",
    re.IGNORECASE,
)
REVISION_RE = re.compile(
    r"\b(?:revise|edit|rewrite|refine|polish|tighten|update|change|adjust|add|remove|include|incorporate|make|mention|say|note|emphasize|clarify|soften|replace|apply|use)\b",
    re.IGNORECASE,
)
REVISION_TARGET_RE = re.compile(r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|tone|it|this|that)\b", re.IGNORECASE)
PENDING_ACCEPT_RE = re.compile(
    r"^\s*(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|sounds good|let'?s do that|that works|open it|use it)\b",
    re.IGNORECASE,
)


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
        decision = NavigationDecision(
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
        return _stabilize_decision(
            decision,
            user_message=user_message,
            requested_whiteboard_mode=requested_whiteboard_mode,
            workspace=workspace,
            pending_workspace_update=pending_workspace_update,
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
                        "protocol_kind": None,
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
            action_type = str(action.get("type") or "").strip().lower()
            if action_type not in ALLOWED_CONTROL_PANEL_ACTIONS:
                continue
            normalized_action = dict(action)
            normalized_action["type"] = action_type
            normalized_action.pop("kind", None)
            protocol_kind = str(
                action.get("protocol_kind")
                or action.get("kind")
                or ""
            ).strip().lower()
            if action_type == "apply_protocol":
                if protocol_kind not in ALLOWED_PROTOCOL_KINDS:
                    continue
                normalized_action["protocol_kind"] = protocol_kind
            else:
                normalized_action["protocol_kind"] = None
            reason = _normalize_reason(action.get("reason"))
            if reason is not None:
                normalized_action["reason"] = reason
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


def _stabilize_decision(
    decision: NavigationDecision,
    *,
    user_message: str,
    requested_whiteboard_mode: str,
    workspace: WorkspaceDocument,
    pending_workspace_update: dict[str, object] | None,
) -> NavigationDecision:
    if decision.mode != "chat":
        return decision
    normalized_requested = str(requested_whiteboard_mode or "auto").strip().lower()
    message = str(user_message or "")
    whiteboard_mode = decision.whiteboard_mode
    original_whiteboard_mode = whiteboard_mode
    stabilized_reason = decision.reason
    if normalized_requested == "chat":
        whiteboard_mode = "chat"
    elif _is_pending_whiteboard_acceptance(message, pending_workspace_update):
        whiteboard_mode = "draft"
    elif normalized_requested in {"offer", "draft"}:
        whiteboard_mode = normalized_requested
    elif _is_explicit_whiteboard_draft_request(message):
        whiteboard_mode = "draft"
    elif _is_active_draft_revision(message, workspace):
        whiteboard_mode = "draft"
    elif _is_work_product_request(message) and not _is_chat_only_request(message):
        whiteboard_mode = "offer"
    if whiteboard_mode != original_whiteboard_mode:
        if whiteboard_mode == "offer":
            stabilized_reason = "Canonical work-product policy invites whiteboard collaboration before drafting."
        elif whiteboard_mode == "draft":
            stabilized_reason = "Canonical whiteboard policy keeps accepted, explicit, or active-draft work in draft mode."
        elif whiteboard_mode == "chat":
            stabilized_reason = "The user or UI explicitly requested plain chat, so whiteboard drafting stays off."

    control_panel = _normalize_control_panel(decision.control_panel)
    protocol_kind = _infer_protocol_kind(
        message,
        workspace=workspace,
        pending_workspace_update=pending_workspace_update,
    )
    if protocol_kind:
        control_panel = _ensure_control_panel_action(
            control_panel,
            action_type="apply_protocol",
            protocol_kind=protocol_kind,
            reason=f"Use the reusable {protocol_kind.replace('_', ' ')} protocol for this work type.",
        )
    if whiteboard_mode == "draft":
        control_panel = _ensure_control_panel_action(
            control_panel,
            action_type="draft_whiteboard",
            reason="The turn is continuing or explicitly requesting a whiteboard draft.",
        )
    elif whiteboard_mode == "offer":
        control_panel = _ensure_control_panel_action(
            control_panel,
            action_type="open_whiteboard",
            reason="The turn asks for a concrete work product that should first invite whiteboard collaboration.",
        )
    return NavigationDecision(
        mode=decision.mode,
        confidence=decision.confidence,
        reason=stabilized_reason,
        comparison_question=decision.comparison_question,
        branch_count=decision.branch_count,
        branch_labels=list(decision.branch_labels),
        whiteboard_mode=whiteboard_mode,
        preserve_pinned_context=decision.preserve_pinned_context,
        pinned_context_reason=decision.pinned_context_reason,
        preserve_selected_record=decision.preserve_selected_record,
        selected_record_reason=decision.selected_record_reason,
        control_panel=control_panel,
    )


def _is_work_product_request(message: str) -> bool:
    return bool(WORK_PRODUCT_RE.search(message))


def _is_chat_only_request(message: str) -> bool:
    return bool(CHAT_ONLY_RE.search(message))


def _is_explicit_whiteboard_draft_request(message: str) -> bool:
    return bool(EXPLICIT_WHITEBOARD_DRAFT_RE.search(message))


def _is_active_draft_revision(message: str, workspace: WorkspaceDocument) -> bool:
    if not getattr(workspace, "content", "").strip():
        return False
    return bool(REVISION_RE.search(message) and REVISION_TARGET_RE.search(message))


def _is_pending_whiteboard_acceptance(message: str, pending_workspace_update: dict[str, object] | None) -> bool:
    if not isinstance(pending_workspace_update, dict):
        return False
    if pending_workspace_update.get("type") not in {"offer_whiteboard", "draft_whiteboard"}:
        return False
    if pending_workspace_update.get("status") not in {"offered", "draft_ready"}:
        return False
    return bool(PENDING_ACCEPT_RE.search(message))


def _infer_protocol_kind(
    message: str,
    *,
    workspace: WorkspaceDocument,
    pending_workspace_update: dict[str, object] | None,
) -> str | None:
    context = " ".join(
        part
        for part in [
            message,
            getattr(workspace, "title", ""),
            getattr(workspace, "content", "")[:500],
            str((pending_workspace_update or {}).get("summary") or ""),
            str((pending_workspace_update or {}).get("origin_user_message") or ""),
        ]
        if part
    )
    if RESEARCH_PAPER_RE.search(context):
        return "research_paper"
    if EMAIL_RE.search(context) or _looks_like_email_draft(context):
        return "email"
    return None


def _looks_like_email_draft(text: str) -> bool:
    return bool(
        re.search(r"\b(?:dear|hi|hello)\s+[A-Z][A-Za-z]+\b", text)
        and re.search(r"\b(?:best|regards|sincerely),?\b", text, re.IGNORECASE)
    )


def _ensure_control_panel_action(
    control_panel: dict[str, object],
    *,
    action_type: str,
    reason: str,
    protocol_kind: str | None = None,
) -> dict[str, object]:
    actions = list(control_panel.get("actions") if isinstance(control_panel.get("actions"), list) else [])
    for action in actions:
        if isinstance(action, dict) and action.get("type") == action_type and action.get("protocol_kind") == protocol_kind:
            return control_panel
    actions.append({"type": action_type, "protocol_kind": protocol_kind, "reason": reason})
    return _normalize_control_panel(
        {
            **control_panel,
            "actions": actions,
            "working_memory_queries": control_panel.get("working_memory_queries", []),
            "response_call": control_panel.get("response_call") or {"type": "chat_response", "after_working_memory": True},
        }
    )
