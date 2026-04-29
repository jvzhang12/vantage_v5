from __future__ import annotations

import re
from typing import Any

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.storage.workspaces import WorkspaceDocument


EXPLICIT_WHITEBOARD_OPEN_RE = re.compile(
    r"\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:(?:a|the)\s+)?(?:(?:fresh|new|blank|empty|shared)\s+)?whiteboard\b",
    re.IGNORECASE,
)
EXPLICIT_WHITEBOARD_DRAFT_RE = re.compile(
    r"\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b",
    re.IGNORECASE,
)
NARROW_EXPLICIT_WHITEBOARD_OPEN_RE = re.compile(
    r"^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard(?:\s+(?:for|about|with)\s+.{1,100})?\s*[.!?]?\s*$",
    re.IGNORECASE,
)
NARROW_EXPLICIT_WHITEBOARD_DEICTIC_RE = re.compile(
    r"^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:put|move|place|add|draft|write|edit|revise|refine|update|change|adjust|include|incorporate|work on|build|create|outline|sketch|review|rewrite)\b.{0,40}\b(?:it|this|that|the draft|this draft|that draft|the current draft)\b.{0,40}\b(?:in|on|into|onto|to)\s+(?:the\s+)?whiteboard\s*[.!?]?\s*$",
    re.IGNORECASE,
)
PENDING_DEICTIC_FOLLOW_UP_RE = re.compile(
    r"^\s*(?:(?:please\s+)?(?:which one|what about(?:\s+(?:it|this|that|that one|this one|those|these))?|tell me more|go deeper|elaborate|expand(?:\s+on\s+(?:it|this|that))?|that one|this one|those|these))\s*[.!?]?\s*$",
    re.IGNORECASE,
)
WHITEBOARD_EDIT_VERB_RE = re.compile(
    r"\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve|make|mention|say|note|emphasize|clarify|soften|replace|apply|use)\b",
    re.IGNORECASE,
)
WHITEBOARD_EDIT_TARGET_RE = re.compile(
    r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b",
    re.IGNORECASE,
)
PENDING_ACCEPT_RE = re.compile(
    r"\b(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\b",
    re.IGNORECASE,
)
PENDING_CONTINUE_RE = re.compile(
    r"\b(?:continue|keep going|go on|carry on|pick up where we left off|resume)\b",
    re.IGNORECASE,
)
PENDING_REFERENCE_RE = re.compile(
    r"\b(?:draft|whiteboard|email|plan|list|outline|document|note|it|this|that)\b",
    re.IGNORECASE,
)
PENDING_EDIT_TARGET_RE = re.compile(
    r"\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b",
    re.IGNORECASE,
)
MAX_PENDING_FOLLOW_UP_LENGTH = 240


class WhiteboardRoutingEngine:
    """Narrow whiteboard routing rules that support Navigator-led decisions."""

    def resolve_whiteboard_mode(
        self,
        requested_whiteboard_mode: str | None,
        decision: NavigationDecision,
        *,
        user_message: str | None,
        workspace: WorkspaceDocument,
    ) -> str:
        if requested_whiteboard_mode == "chat":
            return requested_whiteboard_mode
        if self.is_explicit_whiteboard_draft_request(user_message) and decision.mode == "chat":
            return "draft"
        if (
            decision.mode == "chat"
            and requested_whiteboard_mode != "chat"
            and self.should_continue_current_whiteboard_draft(user_message, workspace)
        ):
            return "draft"
        if requested_whiteboard_mode in {"offer", "draft"}:
            return requested_whiteboard_mode
        if decision.whiteboard_mode in {"chat", "offer", "draft", "auto"}:
            return decision.whiteboard_mode
        return "auto"

    def is_explicit_whiteboard_draft_request(self, message: str | None) -> bool:
        if not message:
            return False
        return bool(
            EXPLICIT_WHITEBOARD_OPEN_RE.search(message)
            or EXPLICIT_WHITEBOARD_DRAFT_RE.search(message)
        )

    def should_continue_current_whiteboard_draft(
        self,
        message: str | None,
        workspace: WorkspaceDocument,
    ) -> bool:
        if not message or not workspace.content.strip():
            return False
        if not WHITEBOARD_EDIT_VERB_RE.search(message):
            return False
        return bool(WHITEBOARD_EDIT_TARGET_RE.search(message))

    def should_carry_pending_workspace_update(
        self,
        message: str | None,
        pending_workspace_update: dict[str, Any] | None,
    ) -> bool:
        if not self.is_pending_workspace_update_active(pending_workspace_update):
            return False
        text = normalize_message(message)
        if NARROW_EXPLICIT_WHITEBOARD_OPEN_RE.search(text) or NARROW_EXPLICIT_WHITEBOARD_DEICTIC_RE.search(text):
            return True
        if self.is_explicit_whiteboard_draft_request(text):
            return False
        if len(text) > MAX_PENDING_FOLLOW_UP_LENGTH:
            return False
        if self.is_pending_accept_follow_up(text):
            return True
        if self.is_pending_edit_follow_up(text):
            return True
        if PENDING_DEICTIC_FOLLOW_UP_RE.search(text):
            return True
        return False

    def is_pending_accept_follow_up(self, text: str) -> bool:
        if not text:
            return True
        if len(text) > MAX_PENDING_FOLLOW_UP_LENGTH:
            return False
        if PENDING_ACCEPT_RE.search(text):
            return True
        return bool(PENDING_CONTINUE_RE.search(text) and PENDING_REFERENCE_RE.search(text))

    def is_pending_edit_follow_up(self, text: str) -> bool:
        if not text or len(text) > MAX_PENDING_FOLLOW_UP_LENGTH:
            return False
        return bool(WHITEBOARD_EDIT_VERB_RE.search(text) and PENDING_EDIT_TARGET_RE.search(text))

    def is_pending_workspace_update_active(self, value: dict[str, Any] | None) -> bool:
        if not isinstance(value, dict):
            return False
        return (
            value.get("type") in {"offer_whiteboard", "draft_whiteboard"}
            and value.get("status") in {"offered", "draft_ready"}
            and bool(value.get("origin_user_message"))
        )


def normalize_message(message: str | None) -> str:
    return str(message or "").strip()
