from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import re
from typing import Any

from vantage_v5.services.navigator import NavigationDecision
from vantage_v5.storage.workspaces import WorkspaceDocument


_SAVE_RE = re.compile(r"\b(?:save|store)\b", re.IGNORECASE)
_PUBLISH_RE = re.compile(r"\b(?:publish|artifact|finalize|ship)\b", re.IGNORECASE)
_DRAFT_RE = re.compile(r"\b(?:draft|write|compose|outline|plan|sketch|create|build)\b", re.IGNORECASE)
_REVISE_RE = re.compile(r"\b(?:revise|edit|rewrite|refine|polish|tighten|update|change|adjust|add|remove|include)\b", re.IGNORECASE)
_INSPECT_RE = re.compile(
    r"\b(?:why|what shaped|what did you use|inspect|provenance|source|reasoning|memory trace|trace this)\b",
    re.IGNORECASE,
)
_EXPERIMENT_RE = re.compile(r"\b(?:experiment mode|switch out|turn off|end experiment|leave experiment)\b", re.IGNORECASE)
_SCENARIO_RE = re.compile(r"\b(?:compare|trade[- ]?off|what if|scenario|branch|option|alternative)\b", re.IGNORECASE)
_ACCEPT_RE = re.compile(r"^\s*(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|sounds good|let'?s do that)\b", re.IGNORECASE)
_DEICTIC_RE = re.compile(r"\b(?:this|that|it|those|these|that one|this one|same|current|previous)\b", re.IGNORECASE)


@dataclass(slots=True)
class SemanticFrame:
    """Compact, product-facing interpretation of what Vantage thinks the turn is doing."""

    user_goal: str
    task_type: str
    follow_up_type: str
    target_surface: str
    confidence: float
    referenced_object: dict[str, Any] | None = None
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    commitments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_goal": self.user_goal,
            "task_type": self.task_type,
            "follow_up_type": self.follow_up_type,
            "target_surface": self.target_surface,
            "referenced_object": self.referenced_object,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt,
            "signals": dict(self.signals),
            "commitments": list(self.commitments),
        }


def semantic_frame_has_referenced_object(frame: SemanticFrame) -> bool:
    """Return whether the frame points at a concrete object Vantage can act on."""

    referenced_object = frame.referenced_object or {}
    return bool(str(referenced_object.get("id") or "").strip() or str(referenced_object.get("title") or "").strip())


def semantic_frame_has_signal(frame: SemanticFrame, signal_name: str) -> bool:
    """Read a boolean signal from a frame without coupling policy to signal storage."""

    return bool(frame.signals.get(signal_name))


def build_semantic_frame(
    *,
    user_message: str,
    navigation: NavigationDecision,
    requested_whiteboard_mode: str | None,
    resolved_whiteboard_mode: str | None,
    whiteboard_entry_mode: str | None,
    workspace: WorkspaceDocument,
    workspace_scope: str,
    pinned_context_id: str | None,
    pinned_context: dict[str, Any] | None,
    pending_workspace_update: dict[str, Any] | None,
) -> SemanticFrame:
    """Build a stable semantic read-model from existing routing signals.

    This is intentionally deterministic for now. It gives the UI and future agent
    policy a richer contract without making new hidden model calls.
    """

    message = user_message or ""
    target_surface = _target_surface(
        message=message,
        navigation=navigation,
        resolved_whiteboard_mode=resolved_whiteboard_mode,
    )
    task_type = _task_type(
        message=message,
        navigation=navigation,
        resolved_whiteboard_mode=resolved_whiteboard_mode,
        pending_workspace_update=pending_workspace_update,
    )
    follow_up_type = _follow_up_type(
        message=message,
        pinned_context=pinned_context,
        pending_workspace_update=pending_workspace_update,
        whiteboard_entry_mode=whiteboard_entry_mode,
    )
    referenced_object = _referenced_object(
        workspace=workspace,
        workspace_scope=workspace_scope,
        pinned_context_id=pinned_context_id,
        pinned_context=pinned_context,
        target_surface=target_surface,
    )
    commitments = _commitments(
        target_surface=target_surface,
        task_type=task_type,
        referenced_object=referenced_object,
        preserve_pinned_context=navigation.preserve_pinned_context
        if navigation.preserve_pinned_context is not None
        else navigation.preserve_selected_record,
    )
    signals = {
        "navigation_mode": navigation.mode,
        "requested_whiteboard_mode": requested_whiteboard_mode or "auto",
        "resolved_whiteboard_mode": resolved_whiteboard_mode,
        "whiteboard_entry_mode": whiteboard_entry_mode,
        "workspace_scope": workspace_scope,
        "has_pinned_context": bool(pinned_context_id or pinned_context),
        "has_pending_whiteboard": bool(pending_workspace_update),
    }
    return SemanticFrame(
        user_goal=_user_goal(
            task_type=task_type,
            target_surface=target_surface,
            referenced_object=referenced_object,
        ),
        task_type=task_type,
        follow_up_type=follow_up_type,
        target_surface=target_surface,
        referenced_object=referenced_object,
        confidence=_confidence(navigation, task_type=task_type, follow_up_type=follow_up_type),
        needs_clarification=False,
        clarification_prompt=None,
        signals=signals,
        commitments=commitments,
    )


def _target_surface(
    *,
    message: str,
    navigation: NavigationDecision,
    resolved_whiteboard_mode: str | None,
) -> str:
    if navigation.mode == "scenario_lab":
        return "scenario_lab"
    if _PUBLISH_RE.search(message) or _SAVE_RE.search(message):
        return "artifact"
    if _INSPECT_RE.search(message):
        return "vantage_inspect"
    if resolved_whiteboard_mode in {"offer", "draft"}:
        return "whiteboard"
    if _EXPERIMENT_RE.search(message):
        return "experiment"
    return "chat"


def _task_type(
    *,
    message: str,
    navigation: NavigationDecision,
    resolved_whiteboard_mode: str | None,
    pending_workspace_update: dict[str, Any] | None,
) -> str:
    if navigation.mode == "scenario_lab" or _SCENARIO_RE.search(message) and navigation.mode == "scenario_lab":
        return "scenario_comparison"
    if _PUBLISH_RE.search(message):
        return "artifact_publish"
    if _SAVE_RE.search(message):
        return "artifact_save"
    if _EXPERIMENT_RE.search(message):
        return "experiment_management"
    if _INSPECT_RE.search(message):
        return "context_inspection"
    if _REVISE_RE.search(message):
        return "revision"
    if pending_workspace_update and (_ACCEPT_RE.search(message) or _DRAFT_RE.search(message)):
        return "whiteboard_follow_up"
    if resolved_whiteboard_mode in {"offer", "draft"} or _DRAFT_RE.search(message):
        return "drafting"
    return "question_answering"


def _follow_up_type(
    *,
    message: str,
    pinned_context: dict[str, Any] | None,
    pending_workspace_update: dict[str, Any] | None,
    whiteboard_entry_mode: str | None,
) -> str:
    pending_origin = ""
    if pending_workspace_update:
        pending_origin = str(pending_workspace_update.get("origin_user_message") or "").strip()
    if pending_workspace_update and (_ACCEPT_RE.search(message) or (pending_origin and pending_origin == message.strip())):
        return "acceptance"
    if _REVISE_RE.search(message):
        return "revision"
    if pinned_context:
        return "continuation"
    if _DEICTIC_RE.search(message) and whiteboard_entry_mode in {"continued_current", "started_from_prior_material"}:
        return "deictic_reference"
    if whiteboard_entry_mode in {"continued_current", "started_from_prior_material"}:
        return "continuation"
    return "new_request"


def _referenced_object(
    *,
    workspace: WorkspaceDocument,
    workspace_scope: str,
    pinned_context_id: str | None,
    pinned_context: dict[str, Any] | None,
    target_surface: str,
) -> dict[str, Any] | None:
    if pinned_context_id or pinned_context:
        context = pinned_context or {}
        return {
            "id": pinned_context_id or str(context.get("id") or context.get("record_id") or ""),
            "title": str(context.get("title") or context.get("name") or "Pinned context"),
            "type": str(context.get("type") or context.get("source") or "record"),
            "source": str(context.get("source") or "pinned_context"),
        }
    if target_surface == "whiteboard" or workspace_scope != "excluded":
        return {
            "id": workspace.workspace_id,
            "title": workspace.title or "Whiteboard",
            "type": "whiteboard",
            "source": "workspace",
        }
    return None


def _commitments(
    *,
    target_surface: str,
    task_type: str,
    referenced_object: dict[str, Any] | None,
    preserve_pinned_context: bool | None,
) -> list[str]:
    commitments: list[str] = []
    if target_surface == "whiteboard":
        commitments.append("Keep drafting work visible in the whiteboard.")
    elif target_surface == "scenario_lab":
        commitments.append("Compare alternatives as explicit branches.")
    elif target_surface == "vantage_inspect":
        commitments.append("Make the reasoning and context path inspectable.")
    elif target_surface == "artifact":
        commitments.append("Treat the current work product as something reusable.")
    else:
        commitments.append("Answer directly in chat.")
    if preserve_pinned_context is True and referenced_object:
        commitments.append("Keep the pinned context active for this turn.")
    if task_type in {"artifact_save", "artifact_publish"}:
        commitments.append("Preserve the useful work product for later reuse.")
    return commitments


def _user_goal(
    *,
    task_type: str,
    target_surface: str,
    referenced_object: dict[str, Any] | None,
) -> str:
    if task_type == "scenario_comparison":
        return "Compare alternatives and make the tradeoffs explicit."
    if task_type == "artifact_publish":
        return "Publish the current work product as a reusable artifact."
    if task_type == "artifact_save":
        return "Save the current work product for reuse."
    if task_type == "context_inspection":
        return "Inspect what shaped the answer."
    if task_type == "experiment_management":
        return "Manage the current experiment session."
    if task_type in {"revision", "whiteboard_follow_up"} and referenced_object:
        return f"Continue working with {referenced_object['title']}."
    if target_surface == "whiteboard":
        return "Move the work into a shared draft."
    return "Answer the user directly."


def _confidence(navigation: NavigationDecision, *, task_type: str, follow_up_type: str) -> float:
    confidence = navigation.confidence if navigation.confidence else 0.72
    if task_type in {"artifact_save", "artifact_publish", "context_inspection", "experiment_management"}:
        confidence = max(confidence, 0.84)
    if follow_up_type in {"acceptance", "deictic_reference"}:
        confidence = max(confidence, 0.8)
    return max(0.0, min(1.0, round(float(confidence), 2)))
