from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
import re

from vantage_v5.services.model_client import create_model_client
from vantage_v5.services.model_client import ModelClientConfig
from vantage_v5.services.visible_artifacts import visible_artifacts_prompt_payload
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
    "remember",
    "close_surface",
    "preserve_surface",
    "manage_experiment",
    "ask_clarification",
}
ALLOWED_PROTOCOL_KINDS = {"email", "research_paper", "scenario_lab"}
COMPLEX_WORK_PRODUCT_RE = re.compile(
    r"\b(?:draft|write|compose|plan|outline|create|build|prepare|develop|make|put together)\b.{0,140}\b(?:itinerary|travel plan|trip plan|road trip|plan|checklist|agenda|research paper|paper introduction|paper intro|academic paper|essay|report|brief|document|doc|outline|proposal|roadmap|strategy|playbook|schedule)\b"
    r"|\b(?:itinerary|research paper|paper introduction|paper intro|academic paper|essay|report|checklist)\b",
    re.IGNORECASE,
)
CHAT_ONLY_RE = re.compile(r"\b(?:chat only|in chat only|keep (?:it|the full draft|this) in chat|answer directly in chat)\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b(?:e-?mail|mail|message|memo|letter|subject[- ]line)\b", re.IGNORECASE)
SIMPLE_EMAIL_MESSAGE_DRAFT_RE = re.compile(
    r"\b(?:draft|write|compose|prepare|create|make|help me draft)\b.{0,90}\b(?:an?\s+|the\s+|a\s+short\s+|a\s+quick\s+)?(?:e-?mail|mail|message|memo|letter)\b",
    re.IGNORECASE,
)
SUBJECT_LINE_RE = re.compile(r"\bsubject[- ]line\b", re.IGNORECASE)
MULTI_OPTION_DOC_RE = re.compile(
    r"\b(?:(?:two|three|four|five|six|seven|eight|nine|ten|\d+|several|multiple|a few)\s+(?:options|versions|variants|alternatives|drafts|e-?mails|messages|memos|letters|subject[- ]lines)|(?:compare|comparison|contrast|tradeoffs?|pros and cons|versus|vs\.?))\b",
    re.IGNORECASE,
)
COMPLEX_EMAIL_FORMAT_RE = re.compile(r"\b(?:e-?mail|message|memo|letter)\s+(?:campaign|sequence|series|drip|template|templates)\b", re.IGNORECASE)
COMPOUND_WORK_PRODUCT_RE = re.compile(
    r"\b(?:e-?mail|message|memo|letter|subject[- ]line)\b.{0,50}\b(?:and|plus)\b.{0,50}\b(?:itinerary|plan|checklist|agenda|paper|essay|report|brief|document|outline|proposal|roadmap)\b"
    r"|\b(?:itinerary|plan|checklist|agenda|paper|essay|report|brief|document|outline|proposal|roadmap)\b.{0,50}\b(?:and|plus)\b.{0,50}\b(?:e-?mail|message|memo|letter|subject[- ]line)\b",
    re.IGNORECASE,
)
COMPLEX_PRODUCT_BEFORE_EMAIL_RE = re.compile(
    r"\b(?:draft|write|compose|plan|outline|create|build|prepare|develop|make|put together)\b.{0,90}\b(?:itinerary|plan|checklist|agenda|research paper|paper|essay|report|brief|document|outline|proposal|roadmap)\b.{0,90}\b(?:e-?mail|message|memo|letter|subject[- ]line)\b",
    re.IGNORECASE,
)
SAVE_PUBLISH_COLLAB_RE = re.compile(r"\b(?:save|publish|collaborat\w*|co-?edit|artifact)\b", re.IGNORECASE)
WORK_PRODUCT_CONTEXT_RE = re.compile(
    r"\b(?:draft|write|compose|plan|outline|create|build|prepare|develop|make|put together|e-?mail|message|memo|letter|subject[- ]line|itinerary|checklist|agenda|paper|essay|report|brief|document|outline|proposal|roadmap)\b",
    re.IGNORECASE,
)
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
SAVED_MATERIAL_OPEN_LOOKUP_RE = re.compile(
    r"\b(?:find|show|open|pull up|look at|go back(?: to)?|reopen|revisit)\b"
    r".{0,100}\b(?:saved|artifact|material|materials|study plan|plan|whiteboard|note|document|exam preparation)\b"
    r"|\b(?:saved|artifact|material|materials|study plan|plan|whiteboard|note|document|exam preparation)\b"
    r".{0,100}\b(?:find|show|open|pull up|look at|go back(?: to)?|reopen|revisit)\b",
    re.IGNORECASE,
)
PRESERVE_VISIBLE_SURFACE_RE = re.compile(
    r"\b(?:keep|leave)\b.{0,80}\b(?:whiteboard|workspace|artifact|item|document|draft|plan|study plan|material|content|calendar|today|agenda|schedule|tasks?|to[-\s]?dos?|todo|it|this|that)\b.{0,30}\bopen\b"
    r"|\b(?:don'?t|do not|please don'?t|please do not)\b.{0,40}\b(?:close|hide|dismiss|remove)\b.{0,100}\b(?:whiteboard|workspace|artifact|item|document|draft|plan|study plan|material|content|calendar|today|agenda|schedule|tasks?|to[-\s]?dos?|todo|it|this|that|from view|out of view)\b",
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
    attention_selection: dict[str, object] | None = None

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
            "attention_selection": _normalize_attention_selection(self.attention_selection),
        }


class NavigatorService:
    def __init__(
        self,
        *,
        model: str,
        openai_api_key: str | None,
        model_client_config: ModelClientConfig | None = None,
    ) -> None:
        self.model = model
        self.client = create_model_client(
            model_client_config or ModelClientConfig(openai_api_key=openai_api_key)
        )

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
        visible_artifacts: list[dict[str, object]] | None = None,
        attention_candidates: list[dict[str, object]] | None = None,
    ) -> NavigationDecision:
        if not self.client:
            return self._fallback_decision("The model provider is unavailable, so the turn stays in normal chat.")
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
                visible_artifacts=visible_artifacts,
                attention_candidates=attention_candidates,
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
        visible_artifacts: list[dict[str, object]] | None,
        attention_candidates: list[dict[str, object]] | None,
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
            "visible_artifacts": visible_artifacts_prompt_payload(visible_artifacts),
            "attention_candidates": attention_candidates or [],
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
                "remember",
                "close_surface",
                "preserve_surface",
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
                "The payload may include attention_candidates from deterministic query-key ranking; treat this shortlist as the primary context/resource selection layer for normal turns. "
                "Select only the few candidates that should actually enter the workspace/model context for this answer. "
                "Do not select candidates just because they are available; reject noisy or merely adjacent candidates. "
                "Selecting context is not the same as opening UI. Set attention_selection.surface_to_open only when the user is explicitly asking to open/show/find/look at material in an app surface, or when the control_panel would press an open surface action; otherwise leave it null even if a candidate has suggested_surface metadata. "
                "Only choose actions from available_control_panel_actions. "
                "For every control_panel action, include protocol_kind as null unless the action type is apply_protocol. "
                "When action type is apply_protocol, protocol_kind is required and must be one of email, research_paper, or scenario_lab. "
                "For Scenario Lab comparisons, apply the scenario_lab protocol so first-principles, counterfactual, causal, tradeoff, and assumption-surfacing guidance can enter working memory. "
                "For email drafting, apply the email protocol when a reusable email protocol should guide the draft. "
                "For research-paper drafting or revision, apply the research_paper protocol when that reusable protocol should guide the work. "
                "Do not ask deterministic code to infer user intent later; put the interpretation into the control_panel. "
                "When the user genuinely asks to close, hide, dismiss, or remove a visible surface from view, add a close_surface action with target set to whiteboard, artifact, calendar, today, task_focus, or current. "
                "A close_surface action only hides the client-side visible surface/context; it must not imply deleting, saving, editing, mutating calendar/tasks, or clearing pinned context. "
                "When the user asks to keep or leave a visible surface open, or explicitly says not to close/hide/remove it, add a preserve_surface action and do not add close_surface, open_whiteboard, draft_whiteboard, or attention_selection.surface_to_open. "
                "Examples include 'don't close the whiteboard', 'do not close this artifact', 'please don't remove today from view', 'keep the whiteboard open', and 'leave the calendar open'. "
                "If close/hide intent is ambiguous, prefer respond/chat and do not add close_surface. "
                "When the user explicitly asks Vantage to remember or save something as memory, add a remember action and keep the response in chat. "
                "Do not open calendar, task focus, or another operational surface merely because the content to remember mentions a day, task, focus, priority, or deadline. "
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
                "The payload may include visible_artifacts from the user's current view. Treat those artifacts as current turn context when routing follow-ups about the visible calendar, task list, whiteboard, plan, or surface. "
                "If the current user message accepts, confirms, refines, or continues that pending whiteboard flow, choose whiteboard_mode='draft' rather than repeating the invitation. "
                "If the user both accepts the pending offer and states a future preference, still treat the current turn as acceptance unless they clearly decline the current work product. "
                "The payload may also include continuity_context with the current whiteboard, a very short recent-whiteboards list, the strongest last-turn referenced saved record, and a short last-turn recall shortlist. "
                "Use that continuity context to resolve deictic follow-ups like 'that one', 'the other email', or 'pull that up on the whiteboard' without overfitting to older history. "
                "Prefer the current whiteboard when the user is clearly continuing the active draft. "
                "Prefer last_turn_referenced_record over generic recent-whiteboard recency when the user is referring back to a recently surfaced saved item. "
                "For ordinary chat turns, choose whiteboard_mode='chat' for simple one-off email, message, memo, letter, or subject-line drafts; still add apply_protocol for email when email guidance should shape that chat answer. "
                "Choose whiteboard_mode='offer' when the user is asking for a complex work product that should first invite whiteboard collaboration, including itineraries, research papers, essays, reports, checklists, plans, multi-option documents, or work the user wants saved, published, or collaboratively drafted. "
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
                                                "target": {
                                                    "type": ["string", "null"],
                                                    "enum": ["whiteboard", "artifact", "calendar", "today", "task_focus", "current", None],
                                                },
                                                "target_id": {"type": ["string", "null"]},
                                                "reason": {"type": ["string", "null"]},
                                                "confidence": {"type": ["number", "null"]},
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
                            "attention_selection": {
                                "type": ["object", "null"],
                                "additionalProperties": False,
                                "properties": {
                                    "selected_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "primary_resource_id": {"type": ["string", "null"]},
                                    "supporting_resource_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "rejected_candidate_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "surface_to_open": {
                                        "type": ["string", "null"],
                                        "enum": [
                                            "today_briefing",
                                            "calendar_day",
                                            "calendar_week",
                                            "task_focus",
                                            "whiteboard",
                                            None,
                                        ],
                                    },
                                    "reason": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": [
                                    "selected_ids",
                                    "primary_resource_id",
                                    "supporting_resource_ids",
                                    "rejected_candidate_ids",
                                    "surface_to_open",
                                    "reason",
                                    "confidence",
                                ],
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
                            "attention_selection",
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
            attention_selection=_normalize_attention_selection(result.get("attention_selection")),
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
            attention_selection=None,
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
            if action_type in {"close_surface", "preserve_surface"}:
                target = _normalize_surface_target(
                    action.get("target")
                    or action.get("surface")
                    or action.get("target_surface")
                )
                normalized_action["target"] = target or "current"
                target_id = _normalize_reason(action.get("target_id") or action.get("surface_id"))
                if target_id is not None:
                    normalized_action["target_id"] = target_id
                confidence = _normalize_confidence(action.get("confidence"))
                if confidence is not None:
                    normalized_action["confidence"] = confidence
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


def _normalize_attention_selection(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    raw_selected = value.get("selected_ids")
    selected_ids = [
        " ".join(str(item).strip().split())
        for item in (raw_selected if isinstance(raw_selected, list) else [])
        if str(item).strip()
    ]
    raw_supporting = value.get("supporting_resource_ids")
    supporting_resource_ids = [
        " ".join(str(item).strip().split())
        for item in (raw_supporting if isinstance(raw_supporting, list) else [])
        if str(item).strip()
    ]
    raw_rejected = value.get("rejected_candidate_ids")
    rejected_candidate_ids = [
        " ".join(str(item).strip().split())
        for item in (raw_rejected if isinstance(raw_rejected, list) else [])
        if str(item).strip()
    ]
    primary_resource_id = _normalize_reason(value.get("primary_resource_id"))
    surface_to_open = _normalize_reason(value.get("surface_to_open"))
    if surface_to_open not in {"today_briefing", "calendar_day", "calendar_week", "task_focus", "whiteboard"}:
        surface_to_open = None
    confidence_value = value.get("confidence")
    try:
        confidence = max(0.0, min(1.0, float(confidence_value)))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "selected_ids": selected_ids,
        "primary_resource_id": primary_resource_id,
        "supporting_resource_ids": supporting_resource_ids,
        "rejected_candidate_ids": rejected_candidate_ids,
        "surface_to_open": surface_to_open,
        "reason": _normalize_reason(value.get("reason")) or "",
        "confidence": confidence,
    }


def _normalize_surface_target(value: object) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "workspace": "whiteboard",
        "draft": "whiteboard",
        "document": "artifact",
        "item": "artifact",
        "study_plan": "artifact",
        "plan": "artifact",
        "schedule": "calendar",
        "agenda": "calendar",
        "day": "calendar",
        "week": "calendar",
        "today_briefing": "today",
        "today_surface": "today",
        "task": "task_focus",
        "tasks": "task_focus",
        "todo": "task_focus",
        "to_do": "task_focus",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {"whiteboard", "artifact", "calendar", "today", "task_focus", "current"}:
        return normalized
    return None


def _normalize_confidence(value: object) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


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
    elif _is_simple_email_or_message_draft_request(message):
        whiteboard_mode = "chat"
    elif _is_complex_work_product_request(message) and not _is_chat_only_request(message):
        whiteboard_mode = "offer"
    if whiteboard_mode != original_whiteboard_mode:
        if whiteboard_mode == "offer":
            stabilized_reason = "Canonical complex work-product policy invites whiteboard collaboration before drafting."
        elif whiteboard_mode == "draft":
            stabilized_reason = "Canonical whiteboard policy keeps accepted, explicit, or active-draft work in draft mode."
        elif whiteboard_mode == "chat":
            stabilized_reason = "Simple one-off email, message, and subject-line drafts stay in chat while email protocol guidance still applies."

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
        control_panel = _without_control_panel_actions(control_panel, {"open_whiteboard"})
        control_panel = _ensure_control_panel_action(
            control_panel,
            action_type="draft_whiteboard",
            reason="The turn is continuing or explicitly requesting a whiteboard draft.",
        )
    elif whiteboard_mode == "offer":
        control_panel = _without_control_panel_actions(control_panel, {"draft_whiteboard"})
        control_panel = _ensure_control_panel_action(
            control_panel,
            action_type="open_whiteboard",
            reason="The turn asks for a concrete work product that should first invite whiteboard collaboration.",
        )
    elif whiteboard_mode == "chat":
        control_panel = _without_control_panel_actions(control_panel, {"open_whiteboard", "draft_whiteboard"})
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
        attention_selection=decision.attention_selection,
    )


def apply_control_panel_open_intent_fallback(
    decision: NavigationDecision,
    *,
    user_message: str,
    attention_candidates: list[dict[str, object]] | None,
) -> NavigationDecision:
    if decision.mode != "chat":
        return decision
    if _is_preserve_visible_surface_intent(user_message) or _has_control_panel_action(decision, {"preserve_surface"}):
        return _with_preserve_surface_intent(decision, user_message=user_message)
    if _is_explicit_memory_intent(user_message) or _has_control_panel_action(decision, {"remember"}):
        return _with_memory_intent(decision, user_message=user_message)
    if not _is_saved_material_open_lookup(user_message):
        return decision

    attention_selection = _normalize_attention_selection(decision.attention_selection) or {
        "selected_ids": [],
        "primary_resource_id": None,
        "supporting_resource_ids": [],
        "rejected_candidate_ids": [],
        "surface_to_open": None,
        "reason": "",
        "confidence": 0.0,
    }
    if attention_selection.get("surface_to_open"):
        return decision

    selected_ids = list(attention_selection.get("selected_ids") or [])
    candidate_by_id = _candidate_aliases(attention_candidates or [])
    selected_candidates = [
        candidate_by_id[item]
        for item in selected_ids
        if isinstance(item, str) and item in candidate_by_id
    ]
    openable = next(
        (candidate for candidate in selected_candidates if _is_openable_saved_material_candidate(candidate)),
        None,
    )
    if openable is None:
        openable = next(
            (
                candidate
                for candidate in (attention_candidates or [])
                if _is_openable_saved_material_candidate(candidate)
            ),
            None,
        )
    if openable is None:
        return decision

    openable_id = _candidate_resource_id(openable)
    if openable_id and openable_id not in selected_ids:
        selected_ids = [openable_id, *selected_ids]
    if not selected_ids:
        return decision

    primary_resource_id = attention_selection.get("primary_resource_id")
    if not primary_resource_id:
        primary_resource_id = openable_id
    reason = (
        str(attention_selection.get("reason") or "").strip()
        or "The user asked to open saved material, so Navigator is issuing an explicit Whiteboard open intent."
    )
    confidence = max(float(attention_selection.get("confidence") or 0.0), 0.72)
    control_panel = _ensure_control_panel_action(
        _normalize_control_panel(decision.control_panel),
        action_type="open_whiteboard",
        reason="Saved/open-material lookup should foreground the selected material without drafting or writing.",
    )
    return NavigationDecision(
        mode=decision.mode,
        confidence=max(decision.confidence, confidence),
        reason=decision.reason
        or "Saved/open-material lookup should foreground the selected material without drafting or writing.",
        comparison_question=decision.comparison_question,
        branch_count=decision.branch_count,
        branch_labels=list(decision.branch_labels),
        whiteboard_mode=decision.whiteboard_mode,
        preserve_pinned_context=decision.preserve_pinned_context,
        pinned_context_reason=decision.pinned_context_reason,
        preserve_selected_record=decision.preserve_selected_record,
        selected_record_reason=decision.selected_record_reason,
        control_panel=control_panel,
        attention_selection={
            **attention_selection,
            "selected_ids": selected_ids[:4],
            "primary_resource_id": primary_resource_id,
            "supporting_resource_ids": [
                item
                for item in selected_ids[:4]
                if item != primary_resource_id
            ],
            "surface_to_open": "whiteboard",
            "reason": reason,
            "confidence": confidence,
        },
    )


def _is_saved_material_open_lookup(message: str) -> bool:
    return bool(SAVED_MATERIAL_OPEN_LOOKUP_RE.search(str(message or "")))


def _is_preserve_visible_surface_intent(message: str) -> bool:
    return bool(PRESERVE_VISIBLE_SURFACE_RE.search(str(message or "")))


def _is_explicit_memory_intent(message: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:please\s+)?remember\s+that\b|\b(?:save|store)\s+this\s+as\s+(?:a\s+)?memory\b",
            str(message or ""),
            re.IGNORECASE,
        )
    )


def _with_memory_intent(decision: NavigationDecision, *, user_message: str) -> NavigationDecision:
    attention_selection = _normalize_attention_selection(decision.attention_selection)
    if attention_selection is not None:
        attention_selection = {
            **attention_selection,
            "surface_to_open": None,
            "reason": attention_selection.get("reason")
            or "The user asked Vantage to remember information, not to open an operational surface.",
        }
    control_panel = _without_control_panel_actions(
        _normalize_control_panel(decision.control_panel),
        {"open_whiteboard", "draft_whiteboard"},
    )
    control_panel = _ensure_control_panel_action(
        control_panel,
        action_type="remember",
        reason="The user explicitly asked Vantage to remember information.",
    )
    return NavigationDecision(
        mode=decision.mode,
        confidence=max(decision.confidence, 0.74),
        reason=decision.reason or "The turn has explicit memory-write intent and should stay in chat.",
        comparison_question=decision.comparison_question,
        branch_count=decision.branch_count,
        branch_labels=list(decision.branch_labels),
        whiteboard_mode="chat",
        preserve_pinned_context=decision.preserve_pinned_context,
        pinned_context_reason=decision.pinned_context_reason,
        preserve_selected_record=decision.preserve_selected_record,
        selected_record_reason=decision.selected_record_reason,
        control_panel=control_panel,
        attention_selection=attention_selection,
    )


def _with_preserve_surface_intent(decision: NavigationDecision, *, user_message: str) -> NavigationDecision:
    attention_selection = _normalize_attention_selection(decision.attention_selection)
    if attention_selection is not None:
        attention_selection = {
            **attention_selection,
            "surface_to_open": None,
            "reason": attention_selection.get("reason")
            or "The user asked to keep the current visible surface in place.",
        }
    control_panel = _without_control_panel_actions(
        _normalize_control_panel(decision.control_panel),
        {"open_whiteboard", "draft_whiteboard", "close_surface"},
    )
    control_panel = _ensure_control_panel_action(
        control_panel,
        action_type="preserve_surface",
        reason="The user asked to keep the current visible surface open, so no UI open or close action should run.",
        target=_preserve_surface_target(user_message),
    )
    return NavigationDecision(
        mode=decision.mode,
        confidence=decision.confidence,
        reason=decision.reason or "The current visible surface should stay open.",
        comparison_question=decision.comparison_question,
        branch_count=decision.branch_count,
        branch_labels=list(decision.branch_labels),
        whiteboard_mode=decision.whiteboard_mode,
        preserve_pinned_context=decision.preserve_pinned_context,
        pinned_context_reason=decision.pinned_context_reason,
        preserve_selected_record=decision.preserve_selected_record,
        selected_record_reason=decision.selected_record_reason,
        control_panel=control_panel,
        attention_selection=attention_selection,
    )


def _preserve_surface_target(message: str) -> str:
    text = str(message or "")
    if re.search(r"\b(?:whiteboard|workspace)\b", text, re.IGNORECASE):
        return "whiteboard"
    if re.search(r"\b(?:calendar|today|agenda|schedule|day|week)\b", text, re.IGNORECASE):
        return "today"
    if re.search(r"\b(?:tasks?|to[-\s]?dos?|todo)\b", text, re.IGNORECASE):
        return "task_focus"
    if re.search(r"\b(?:artifact|item|document|draft|plan|study plan|material|content)\b", text, re.IGNORECASE):
        return "artifact"
    return "current"


def _candidate_aliases(candidates: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    aliases: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in ("id", "resource_id"):
            value = str(candidate.get(key) or "").strip()
            if value:
                aliases[value] = candidate
    return aliases


def _candidate_resource_id(candidate: dict[str, object]) -> str | None:
    value = str(candidate.get("resource_id") or "").strip()
    return value or None


def _is_openable_saved_material_candidate(candidate: dict[str, object]) -> bool:
    if not isinstance(candidate, dict):
        return False
    resource_id = str(candidate.get("resource_id") or "").strip().lower()
    if not resource_id.startswith("artifact:"):
        return False
    source = str(candidate.get("source") or "").strip().lower()
    if source and source != "artifact":
        return False
    surface = str(candidate.get("suggested_surface") or "").strip().lower()
    app = str(candidate.get("app") or "").strip().lower()
    kind = str(candidate.get("kind") or "").strip().lower()
    return surface == "whiteboard" or app == "whiteboard" or kind in {"artifact", "whiteboard"}


def _is_complex_work_product_request(message: str) -> bool:
    if MULTI_OPTION_DOC_RE.search(message) and WORK_PRODUCT_CONTEXT_RE.search(message):
        return True
    if SAVE_PUBLISH_COLLAB_RE.search(message) and WORK_PRODUCT_CONTEXT_RE.search(message):
        return True
    return bool(COMPLEX_WORK_PRODUCT_RE.search(message))


def _is_simple_email_or_message_draft_request(message: str) -> bool:
    has_email_message_target = bool(SIMPLE_EMAIL_MESSAGE_DRAFT_RE.search(message))
    has_subject_line_target = bool(SUBJECT_LINE_RE.search(message))
    if not has_email_message_target and not has_subject_line_target:
        return False
    if has_subject_line_target and not has_email_message_target and COMPLEX_WORK_PRODUCT_RE.search(message):
        return False
    if MULTI_OPTION_DOC_RE.search(message):
        return False
    if SAVE_PUBLISH_COLLAB_RE.search(message):
        return False
    if "whiteboard" in message.lower():
        return False
    if (
        COMPLEX_EMAIL_FORMAT_RE.search(message)
        or COMPOUND_WORK_PRODUCT_RE.search(message)
        or COMPLEX_PRODUCT_BEFORE_EMAIL_RE.search(message)
    ):
        return False
    return True


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
    target: str | None = None,
) -> dict[str, object]:
    actions = list(control_panel.get("actions") if isinstance(control_panel.get("actions"), list) else [])
    for action in actions:
        if isinstance(action, dict) and action.get("type") == action_type and action.get("protocol_kind") == protocol_kind:
            return control_panel
    action: dict[str, object] = {"type": action_type, "protocol_kind": protocol_kind, "reason": reason}
    if target:
        action["target"] = target
    actions.append(action)
    return _normalize_control_panel(
        {
            **control_panel,
            "actions": actions,
            "working_memory_queries": control_panel.get("working_memory_queries", []),
            "response_call": control_panel.get("response_call") or {"type": "chat_response", "after_working_memory": True},
        }
    )


def _has_control_panel_action(decision: NavigationDecision, action_types: set[str]) -> bool:
    control_panel = _normalize_control_panel(decision.control_panel)
    actions = control_panel.get("actions") if isinstance(control_panel.get("actions"), list) else []
    return any(
        isinstance(action, dict) and str(action.get("type") or "").strip().lower() in action_types
        for action in actions
    )


def _without_control_panel_actions(control_panel: dict[str, object], action_types: set[str]) -> dict[str, object]:
    actions = control_panel.get("actions") if isinstance(control_panel.get("actions"), list) else []
    filtered_actions = [
        action
        for action in actions
        if not (isinstance(action, dict) and str(action.get("type") or "").strip().lower() in action_types)
    ]
    if len(filtered_actions) == len(actions):
        return control_panel
    return _normalize_control_panel(
        {
            **control_panel,
            "actions": filtered_actions,
            "working_memory_queries": control_panel.get("working_memory_queries", []),
            "response_call": control_panel.get("response_call") or {"type": "chat_response", "after_working_memory": True},
        }
    )
