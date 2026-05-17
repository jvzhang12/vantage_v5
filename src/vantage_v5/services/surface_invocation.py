from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


SURFACE_CHAT = "chat"
SURFACE_WHITEBOARD = "whiteboard"
SURFACE_CALENDAR_DAY = "calendar_day"
SURFACE_CALENDAR_WEEK = "calendar_week"
SURFACE_TASK_FOCUS = "task_focus"
SURFACE_CODE_ARTIFACT = "code_artifact"

POLICY_VERSION = "surface-invocation-v1"

CHAT_ONLY_RE = re.compile(
    r"\b(?:chat[-\s]?only|in chat only|keep (?:it|this|the full draft|everything) in chat|"
    r"answer directly in chat|respond directly in chat|do not open|don't open|without (?:the )?whiteboard)\b",
    re.IGNORECASE,
)
SCHEDULE_LOOKUP_RE = re.compile(
    r"\b(?:calendar|schedule|agenda|availability|available|free|busy|planned|commitments?|events?|"
    r"appointments?|meetings?|week|weekly)\b|"
    r"\b(?:what(?:'s| is)?|tell me about|show me|walk me through)\b.{0,80}\b(?:today|tomorrow|my day)\b|"
    r"\b(?:day|today|tomorrow|week|this week|next week)\b.{0,80}\b(?:look like|planned|schedule|agenda)\b",
    re.IGNORECASE,
)
SCHEDULE_PLANNING_RE = re.compile(
    r"\b(?:plan|map out|time[-\s]?block|schedule|fit|slot|when should|find time|make time)\b"
    r".{0,100}\b(?:day|week|today|tomorrow|study|homework|workout|task|tasks|assignment|assignments|meeting|meetings)\b|"
    r"\b(?:plan my day|plan my week|map out my day|map out my week|time[-\s]?block my day|time[-\s]?block my week|when should i)\b",
    re.IGNORECASE,
)
WEEK_VIEW_RE = re.compile(r"\b(?:week|weekly|this week|next week|week view|weekly view)\b", re.IGNORECASE)
TRAVEL_PLAN_RE = re.compile(r"\b(?:road trip|travel plan|trip itinerary|sightseeing|touring route)\b", re.IGNORECASE)
TASK_FOCUS_RE = re.compile(
    r"\b(?:tasks?|to[-\s]?dos?|todo list|checklist|deadline|deadlines|assignment|assignments|homework|"
    r"priorit(?:y|ies|ize)|focus list|what should i do|what do i need to do|get done)\b",
    re.IGNORECASE,
)
EMAIL_DRAFT_RE = re.compile(
    r"\b(?:draft|write|compose|prepare|create|make|help me draft|reply to|respond to)\b"
    r".{0,100}\b(?:e-?mail|message|memo|letter)\b|"
    r"\b(?:e-?mail|message|memo|letter)\b.{0,80}\b(?:draft|reply|response)\b",
    re.IGNORECASE,
)
CODE_ARTIFACT_RE = re.compile(
    r"\b(?:code|implement|build|program|script|function|component|api|endpoint|bug|fix|refactor|"
    r"test|tests|class|module)\b",
    re.IGNORECASE,
)
DURABLE_WORK_PRODUCT_RE = re.compile(
    r"\b(?:draft|write|compose|plan|outline|create|build|prepare|develop|make|put together|design)\b"
    r".{0,140}\b(?:essay|paper|research paper|report|brief|document|doc|proposal|roadmap|strategy|"
    r"plan|study plan|project plan|launch plan|checklist|agenda|outline|playbook|itinerary|schedule|"
    r"list)\b|"
    r"\b(?:essay|research paper|paper introduction|report|proposal|itinerary|playbook)\b",
    re.IGNORECASE,
)
LIGHTWEIGHT_CHAT_RE = re.compile(
    r"^\s*(?:hi|hello|hey|thanks|thank you|ok(?:ay)?|what is|who is|define|explain briefly|"
    r"quick question)\b",
    re.IGNORECASE,
)
CURRENT_ARTIFACT_FOLLOWUP_RE = re.compile(
    r"\b(?:what should i do next|what should i focus on next|what next|what's next|what is next|"
    r"what should i do first|what should i focus on first|what should i start with|where should i start|"
    r"what comes first|what's first|what is first|now what|what am i looking at|what is this|what's this|"
    r"based on (?:this|the current view)|using (?:this|the current view)|"
    r"how should i use (?:this|the current view|this plan|the plan))\b",
    re.IGNORECASE,
)
VISIBLE_ARTIFACT_QNA_RE = re.compile(
    r"\b(?:summari[sz]e|explain|key points?|main points?|takeaways?|walk me through|tell me about|"
    r"what\s+(?:are|is|should|does|do|comes)|how\s+(?:should|do|does|can)|why|when|where|which)\b",
    re.IGNORECASE,
)
VISIBLE_ARTIFACT_REFERENCE_RE = re.compile(
    r"\b(?:this|that|current|visible|open|opened)\s+"
    r"(?:artifact|whiteboard|item|document|draft|plan|study plan|itinerary|outline|list|note|material|content)\b|"
    r"\b(?:this|the)\s+(?:study\s+)?plan\b|"
    r"\b(?:it|this|that)\b|"
    r"\b(?:current view|what i(?:'m| am) looking at)\b|"
    r"\b(?:from|in|on|about|using|based on)\s+(?:this|that|the current view)\b",
    re.IGNORECASE,
)
VISIBLE_ARTIFACT_WRITE_RE = re.compile(
    r"\b(?:draft|edit|update|revise|rewrite|write|create|make|build|turn|convert|save|publish)\b|"
    r"\b(?:open|pull up|bring up|show|use|start|resume)\s+"
    r"(?:(?:a|the)\s+)?(?:(?:fresh|new|blank|empty|shared)\s+)?whiteboard\b",
    re.IGNORECASE,
)
EXPLICIT_WHITEBOARD_DRAFT_RE = re.compile(
    r"\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|edit|update|revise|rewrite)\b"
    r".{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b|"
    r"\b(?:edit|update|revise|rewrite|refine|work on)\s+(?:the\s+)?whiteboard\b|"
    r"\b(?:open|pull up|bring up|show|use|start|resume)\s+"
    r"(?:(?:a|the)\s+)?(?:(?:fresh|new|blank|empty|shared)\s+)?whiteboard\b",
    re.IGNORECASE,
)
CLOSE_SURFACE_VERB_RE = re.compile(r"\b(?:close|hide|dismiss|remove)\b", re.IGNORECASE)
CLOSE_SURFACE_TARGET_RE = re.compile(
    r"\b(?:whiteboard|workspace|artifact|item|document|draft|plan|study plan|material|content|"
    r"calendar|today|agenda|schedule|day|week|tasks?|to[-\s]?dos?|todo|current view|"
    r"what i(?:'m| am) looking at|this|that|it)\b|"
    r"\b(?:from|out of)\s+(?:view|sight|the screen)\b",
    re.IGNORECASE,
)
CLOSE_SURFACE_REMOVE_VIEW_RE = re.compile(
    r"\bremove\b.{0,80}\b(?:from|out of)\s+(?:view|sight|the screen)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class InvokedSurface:
    kind: str
    role: str
    reason: str
    status: str = "summoned"

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "role": self.role,
            "reason": self.reason,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class SurfaceInvocation:
    intent: str
    primary_surface: str
    supporting_surfaces: tuple[str, ...]
    surfaces: tuple[InvokedSurface, ...]
    write_behavior: str
    reason: str
    confidence: float
    whiteboard_mode: str | None = None
    trigger: str = "deterministic_policy"
    requires_confirmation: bool = False
    surface_action: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "policy_version": POLICY_VERSION,
            "intent": self.intent,
            "primary_surface": self.primary_surface,
            "supporting_surfaces": list(self.supporting_surfaces),
            "surfaces": [surface.to_dict() for surface in self.surfaces],
            "write_behavior": self.write_behavior,
            "reason": self.reason,
            "confidence": self.confidence,
            "whiteboard_mode": self.whiteboard_mode,
            "trigger": self.trigger,
            "requires_confirmation": self.requires_confirmation,
        }
        if self.surface_action is not None:
            payload["surface_action"] = dict(self.surface_action)
        return payload

    @property
    def summons_whiteboard(self) -> bool:
        return self.primary_surface == SURFACE_WHITEBOARD or SURFACE_WHITEBOARD in self.supporting_surfaces

    def resolved_whiteboard_mode(self, *, requested_mode: str | None, current_mode: str) -> str:
        if requested_mode in {"chat", "offer", "draft"}:
            return requested_mode
        if self.whiteboard_mode in {"draft", "offer", "chat"}:
            return self.whiteboard_mode
        return current_mode


def build_surface_invocation(
    *,
    user_message: str,
    requested_whiteboard_mode: str | None = "auto",
    navigation: Any | None = None,
    visible_artifacts: list[dict[str, Any]] | None = None,
) -> SurfaceInvocation:
    message = _clean(user_message)
    requested_mode = _clean(requested_whiteboard_mode).lower() or "auto"
    navigation_mode = _clean(getattr(navigation, "mode", "")).lower()
    visible_surface_kind = _visible_surface_kind(visible_artifacts)
    close_action = _close_visible_surface_action(message, visible_artifacts)
    if close_action is not None:
        status = "closed_client_side" if close_action.get("status") != "no_visible_surface" else "no_visible_surface"
        return _invocation(
            intent="close_visible_surface",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="none",
            reason=close_action.get("reason")
            or "The user asked to close a visible surface without deleting saved data.",
            confidence=0.9 if status != "no_visible_surface" else 0.78,
            whiteboard_mode="chat",
            status=status,
            surface_action=close_action,
        )
    if navigation_mode == "scenario_lab":
        return _invocation(
            intent="scenario_comparison",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="artifact_branching",
            reason="The request is being handled by Scenario Lab, which owns branch workspaces and comparison artifacts.",
            confidence=0.82,
            status="handled_elsewhere",
        )
    if _is_chat_only(message, requested_mode=requested_mode):
        return _invocation(
            intent="chat_only",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="none",
            reason="The user explicitly asked to keep this response in chat.",
            confidence=0.95,
        )
    if _is_explicit_whiteboard_draft_request(message):
        return _invocation(
            intent="durable_artifact",
            primary=SURFACE_WHITEBOARD,
            supporting=(),
            write_behavior="draft_only",
            reason="The user explicitly asked to work in the whiteboard.",
            confidence=0.88,
            whiteboard_mode="draft",
        )
    if visible_surface_kind and _is_current_artifact_followup(message):
        return _invocation(
            intent="current_artifact_followup",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="none",
            reason=(
                "The user is asking a follow-up while an artifact is already visible, "
                "so Vantage should answer using the current view instead of replacing it."
            ),
            confidence=0.78,
            whiteboard_mode="chat",
            status="kept_current_view",
        )
    if not visible_surface_kind and _is_current_material_question(message):
        return _invocation(
            intent="selected_material_question",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="none",
            reason="The user is asking a normal question about current or selected material, not asking Vantage to draft or save.",
            confidence=0.74,
            whiteboard_mode="chat",
        )
    if _is_travel_plan(message):
        return _invocation(
            intent="durable_artifact",
            primary=SURFACE_WHITEBOARD,
            supporting=(),
            write_behavior="draft_only",
            reason="The user is asking for a durable travel plan or itinerary, so Vantage should draft it in the whiteboard automatically.",
            confidence=0.86,
            whiteboard_mode="draft",
        )
    if _is_schedule_planning(message):
        calendar_surface = SURFACE_CALENDAR_WEEK if _wants_week_view(message) else SURFACE_CALENDAR_DAY
        return _invocation(
            intent="schedule_planning",
            primary=calendar_surface,
            supporting=(SURFACE_TASK_FOCUS, SURFACE_WHITEBOARD),
            write_behavior="proposal_only",
            reason="The user is asking Vantage to plan time around a day, schedule, task, or study commitment.",
            confidence=0.9,
            whiteboard_mode="draft",
        )
    if _is_code_artifact(message):
        return _invocation(
            intent="code_artifact",
            primary=SURFACE_CODE_ARTIFACT,
            supporting=(SURFACE_WHITEBOARD,),
            write_behavior="draft_only",
            reason="The user is asking for code or implementation work, which should become an inspectable work product.",
            confidence=0.82,
            whiteboard_mode="draft",
        )
    if _is_durable_work_product(message):
        return _invocation(
            intent="durable_artifact",
            primary=SURFACE_WHITEBOARD,
            supporting=(),
            write_behavior="draft_only",
            reason="The user is asking for a durable work product, so Vantage should draft it in the whiteboard automatically.",
            confidence=0.86,
            whiteboard_mode="draft",
        )
    if _is_schedule_lookup(message):
        calendar_surface = SURFACE_CALENDAR_WEEK if _wants_week_view(message) else SURFACE_CALENDAR_DAY
        return _invocation(
            intent="schedule_lookup",
            primary=calendar_surface,
            supporting=_task_support(message),
            write_behavior="read_only",
            reason="The user is asking about calendar, agenda, availability, or what is planned for a day.",
            confidence=0.88,
        )
    if _is_task_focus(message):
        return _invocation(
            intent="task_focus",
            primary=SURFACE_TASK_FOCUS,
            supporting=(),
            write_behavior="proposal_only",
            reason="The user is asking about tasks, deadlines, priorities, or what to focus on.",
            confidence=0.84,
        )
    if LIGHTWEIGHT_CHAT_RE.search(message):
        return _invocation(
            intent="quick_chat",
            primary=SURFACE_CHAT,
            supporting=(),
            write_behavior="none",
            reason="The request looks like a lightweight chat turn rather than a durable artifact or operational surface.",
            confidence=0.72,
        )
    return _invocation(
        intent="general_chat",
        primary=SURFACE_CHAT,
        supporting=(),
        write_behavior="none",
        reason="No durable artifact or operational surface was strongly implied.",
        confidence=0.62,
    )


def _invocation(
    *,
    intent: str,
    primary: str,
    supporting: tuple[str, ...],
    write_behavior: str,
    reason: str,
    confidence: float,
    whiteboard_mode: str | None = None,
    status: str = "summoned",
    surface_action: dict[str, Any] | None = None,
) -> SurfaceInvocation:
    deduped_supporting = tuple(surface for surface in dict.fromkeys(supporting) if surface != primary)
    surfaces = (
        InvokedSurface(kind=primary, role="primary", reason=reason, status=status),
        *(
            InvokedSurface(
                kind=surface,
                role="supporting",
                reason=_supporting_reason(surface, intent),
                status=status,
            )
            for surface in deduped_supporting
        ),
    )
    return SurfaceInvocation(
        intent=intent,
        primary_surface=primary,
        supporting_surfaces=deduped_supporting,
        surfaces=surfaces,
        write_behavior=write_behavior,
        reason=reason,
        confidence=confidence,
        whiteboard_mode=whiteboard_mode,
        surface_action=surface_action,
    )


def _supporting_reason(surface: str, intent: str) -> str:
    if surface == SURFACE_WHITEBOARD:
        return "A durable plan or work product may need to be drafted after the operational context is gathered."
    if surface == SURFACE_TASK_FOCUS:
        return "Task context can help decide what matters inside the available time."
    if surface == SURFACE_CALENDAR_DAY:
        return "Calendar context can anchor this request in real time blocks and commitments."
    if surface == SURFACE_CALENDAR_WEEK:
        return "A week view can show commitments and open space across multiple days."
    if surface == SURFACE_CODE_ARTIFACT:
        return "Code work should remain inspectable as a concrete artifact."
    return f"{surface} supports the {intent} request."


def _task_support(message: str) -> tuple[str, ...]:
    return (SURFACE_TASK_FOCUS,) if _is_task_focus(message) or re.search(r"\b(?:what should i do|planned for today|my day)\b", message, re.IGNORECASE) else ()


def _is_chat_only(message: str, *, requested_mode: str) -> bool:
    return bool(CHAT_ONLY_RE.search(message))


def _is_schedule_lookup(message: str) -> bool:
    return bool(SCHEDULE_LOOKUP_RE.search(message))


def _is_schedule_planning(message: str) -> bool:
    return bool(SCHEDULE_PLANNING_RE.search(message))


def _wants_week_view(message: str) -> bool:
    return bool(WEEK_VIEW_RE.search(message))


def _is_travel_plan(message: str) -> bool:
    return bool(TRAVEL_PLAN_RE.search(message))


def _is_task_focus(message: str) -> bool:
    return bool(TASK_FOCUS_RE.search(message))


def _is_current_artifact_followup(message: str) -> bool:
    if VISIBLE_ARTIFACT_WRITE_RE.search(message):
        return False
    if CURRENT_ARTIFACT_FOLLOWUP_RE.search(message):
        return True
    return bool(VISIBLE_ARTIFACT_QNA_RE.search(message) and VISIBLE_ARTIFACT_REFERENCE_RE.search(message))


def _is_current_material_question(message: str) -> bool:
    if VISIBLE_ARTIFACT_WRITE_RE.search(message):
        return False
    return bool(VISIBLE_ARTIFACT_QNA_RE.search(message) and VISIBLE_ARTIFACT_REFERENCE_RE.search(message))


def _is_explicit_whiteboard_draft_request(message: str) -> bool:
    return bool(EXPLICIT_WHITEBOARD_DRAFT_RE.search(message))


def _visible_surface_kind(visible_artifacts: list[dict[str, Any]] | None) -> str | None:
    for artifact in visible_artifacts or []:
        kind = _clean(artifact.get("kind")).lower()
        if kind in {
            SURFACE_CALENDAR_DAY,
            SURFACE_CALENDAR_WEEK,
            SURFACE_TASK_FOCUS,
            SURFACE_WHITEBOARD,
            "artifact",
            "today_briefing",
            SURFACE_CODE_ARTIFACT,
        }:
            return kind
    return None


def _close_visible_surface_action(
    message: str,
    visible_artifacts: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if not _looks_like_close_surface_command(message, visible_artifacts):
        return None
    target = _close_target(message)
    target_artifact = _matching_visible_artifact(message, visible_artifacts, target=target)
    if target_artifact is None:
        return {
            "type": "close_visible_surface",
            "status": "no_visible_surface",
            "target": target or "current",
            "target_id": None,
            "target_kind": target or "current",
            "title": None,
            "reason": "The user asked to close a surface, but there is no matching visible surface in context.",
        }
    target_kind = _clean(target_artifact.get("kind")).lower() or target or "artifact"
    target_id = _clean(target_artifact.get("id")) or None
    title = _clean(target_artifact.get("title")) or None
    return {
        "type": "close_visible_surface",
        "status": "requested",
        "target": target or _close_target_from_kind(target_kind),
        "target_id": target_id,
        "target_kind": target_kind,
        "title": title,
        "reason": "The user asked to remove the current visible surface from view without deleting saved data.",
    }


def _looks_like_close_surface_command(
    message: str,
    visible_artifacts: list[dict[str, Any]] | None,
) -> bool:
    verb = CLOSE_SURFACE_VERB_RE.search(message)
    if not verb:
        return False
    if verb.group(0).lower() == "remove":
        return bool(CLOSE_SURFACE_REMOVE_VIEW_RE.search(message))
    if CLOSE_SURFACE_REMOVE_VIEW_RE.search(message):
        return True
    if CLOSE_SURFACE_TARGET_RE.search(message):
        return True
    return _message_mentions_visible_title(message, visible_artifacts)


def _close_target(message: str) -> str | None:
    if re.search(r"\b(?:whiteboard|workspace)\b", message, re.IGNORECASE):
        return "whiteboard"
    if re.search(r"\b(?:calendar|today|agenda|schedule|day|week)\b", message, re.IGNORECASE):
        return "calendar"
    if re.search(r"\b(?:tasks?|to[-\s]?dos?|todo)\b", message, re.IGNORECASE):
        return "task"
    if re.search(r"\b(?:artifact|item|document|draft|plan|study plan|material|content)\b", message, re.IGNORECASE):
        return "artifact"
    if re.search(r"\b(?:current view|what i(?:'m| am) looking at|this|that|it)\b", message, re.IGNORECASE):
        return "current"
    return None


def _matching_visible_artifact(
    message: str,
    visible_artifacts: list[dict[str, Any]] | None,
    *,
    target: str | None,
) -> dict[str, Any] | None:
    artifacts = [artifact for artifact in visible_artifacts or [] if isinstance(artifact, dict)]
    if not artifacts:
        return None
    if target == "whiteboard":
        return _first_visible_kind(artifacts, {"whiteboard", "artifact"})
    if target == "calendar":
        return _first_visible_kind(artifacts, {"today_briefing", "calendar_day", "calendar_week"})
    if target == "task":
        return _first_visible_kind(artifacts, {"task_focus"})
    if target == "artifact":
        return (
            _visible_artifact_matching_title(message, artifacts)
            or _first_visible_kind(artifacts, {"whiteboard", "artifact"})
            or artifacts[0]
        )
    if target == "current":
        return artifacts[0]
    return _visible_artifact_matching_title(message, artifacts) or artifacts[0]


def _first_visible_kind(artifacts: list[dict[str, Any]], kinds: set[str]) -> dict[str, Any] | None:
    for artifact in artifacts:
        if _clean(artifact.get("kind")).lower() in kinds:
            return artifact
    return None


def _message_mentions_visible_title(message: str, visible_artifacts: list[dict[str, Any]] | None) -> bool:
    return _visible_artifact_matching_title(message, visible_artifacts or []) is not None


def _visible_artifact_matching_title(
    message: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    normalized_message = _normalized_words(message)
    if not normalized_message:
        return None
    for artifact in artifacts:
        title = _normalized_words(_clean(artifact.get("title")))
        if not title:
            continue
        important_phrase = _important_title_phrase(title)
        if title in normalized_message or bool(important_phrase and important_phrase in normalized_message):
            return artifact
    return None


def _important_title_phrase(title_words: str) -> str:
    words = [word for word in title_words.split() if len(word) > 2]
    if len(words) <= 2:
        return " ".join(words)
    return " ".join(words[-2:])


def _normalized_words(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _close_target_from_kind(kind: str) -> str:
    if kind in {"today_briefing", "calendar_day", "calendar_week"}:
        return "calendar"
    if kind == "task_focus":
        return "task"
    if kind == "whiteboard":
        return "whiteboard"
    return "artifact"


def _is_code_artifact(message: str) -> bool:
    if not CODE_ARTIFACT_RE.search(message):
        return False
    return bool(re.search(r"\b(?:can you|please|help me|write|build|implement|fix|create|make|refactor|test)\b", message, re.IGNORECASE))


def _is_durable_work_product(message: str) -> bool:
    if EMAIL_DRAFT_RE.search(message):
        return True
    if DURABLE_WORK_PRODUCT_RE.search(message):
        return True
    return False


def _clean(value: Any) -> str:
    return str(value or "").strip()
