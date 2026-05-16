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
    r"\b(?:essay|research paper|paper introduction|report|proposal|roadmap|study plan|project plan|"
    r"launch plan|itinerary|playbook)\b",
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

    def to_dict(self) -> dict[str, Any]:
        return {
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
    lowered = message.lower()
    requested_mode = _clean(requested_whiteboard_mode).lower() or "auto"
    navigation_mode = _clean(getattr(navigation, "mode", "")).lower()
    visible_surface_kind = _visible_surface_kind(visible_artifacts)
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
    if _is_durable_work_product(message, lowered=lowered):
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
    return bool(CURRENT_ARTIFACT_FOLLOWUP_RE.search(message))


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


def _is_code_artifact(message: str) -> bool:
    if not CODE_ARTIFACT_RE.search(message):
        return False
    return bool(re.search(r"\b(?:can you|please|help me|write|build|implement|fix|create|make|refactor|test)\b", message, re.IGNORECASE))


def _is_durable_work_product(message: str, *, lowered: str) -> bool:
    if EMAIL_DRAFT_RE.search(message):
        return True
    if DURABLE_WORK_PRODUCT_RE.search(message):
        return True
    return "study plan" in lowered or "project plan" in lowered


def _clean(value: Any) -> str:
    return str(value or "").strip()
