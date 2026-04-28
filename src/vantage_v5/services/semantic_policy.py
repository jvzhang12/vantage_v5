from __future__ import annotations

from dataclasses import dataclass

from vantage_v5.services.semantic_frame import SemanticFrame
from vantage_v5.services.semantic_frame import semantic_frame_has_referenced_object
from vantage_v5.services.semantic_frame import semantic_frame_has_signal


@dataclass(frozen=True, slots=True)
class SemanticPolicyContext:
    """Small caller-provided facts needed to decide whether acting is safe."""

    has_current_artifact: bool = False
    has_pending_whiteboard: bool = False
    has_pinned_context: bool = False
    has_active_experiment: bool = False
    has_inspectable_context: bool = False
    publish_target_confirmed: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "has_current_artifact": self.has_current_artifact,
            "has_pending_whiteboard": self.has_pending_whiteboard,
            "has_pinned_context": self.has_pinned_context,
            "has_active_experiment": self.has_active_experiment,
            "has_inspectable_context": self.has_inspectable_context,
            "publish_target_confirmed": self.publish_target_confirmed,
        }


@dataclass(frozen=True, slots=True)
class SemanticPolicyDecision:
    """Deterministic action read-model derived from a semantic frame."""

    action_type: str
    should_clarify: bool
    clarification_prompt: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "action_type": self.action_type,
            "semantic_action": self.action_type,
            "should_clarify": self.should_clarify,
            "needs_clarification": self.should_clarify,
            "clarification_prompt": self.clarification_prompt,
            "reason": self.reason,
        }


def decide_semantic_policy(
    frame: SemanticFrame,
    *,
    context: SemanticPolicyContext | None = None,
) -> SemanticPolicyDecision:
    """Decide whether the current semantic intent is safe to act on.

    The policy is deterministic and deliberately narrow. It only interrupts for
    save, publish, experiment-management, and context-inspection turns when the
    frame intent lacks enough caller-provided context to choose a safe target.
    """

    policy_context = context or SemanticPolicyContext()

    if frame.task_type == "artifact_save":
        return _artifact_save_decision(frame, policy_context)
    if frame.task_type == "artifact_publish":
        return _artifact_publish_decision(frame, policy_context)
    if frame.task_type == "experiment_management":
        return _experiment_decision(policy_context)
    if frame.task_type == "context_inspection":
        return _context_inspection_decision(frame, policy_context)

    return SemanticPolicyDecision(
        action_type=_default_action_type(frame),
        should_clarify=frame.needs_clarification,
        clarification_prompt=frame.clarification_prompt,
        reason="Semantic frame maps directly to the default action.",
    )


def _artifact_save_decision(frame: SemanticFrame, context: SemanticPolicyContext) -> SemanticPolicyDecision:
    if _has_artifact_target(frame, context):
        return SemanticPolicyDecision(
            action_type="artifact_save",
            should_clarify=False,
            reason="A save target is available from the frame or caller context.",
        )
    return SemanticPolicyDecision(
        action_type="artifact_save",
        should_clarify=True,
        clarification_prompt="What should I save: the current whiteboard, the latest answer, or something else?",
        reason="The user asked to save something, but no concrete save target is available.",
    )


def _artifact_publish_decision(frame: SemanticFrame, context: SemanticPolicyContext) -> SemanticPolicyDecision:
    if not _has_artifact_target(frame, context):
        return SemanticPolicyDecision(
            action_type="artifact_publish",
            should_clarify=True,
            clarification_prompt="What should I publish: the current whiteboard, the latest answer, or another artifact?",
            reason="The user asked to publish, but no concrete publish target is available.",
        )
    if not context.publish_target_confirmed:
        return SemanticPolicyDecision(
            action_type="artifact_publish",
            should_clarify=True,
            clarification_prompt="Should I publish the current work product as the reusable artifact?",
            reason="Publishing is durable enough to require target confirmation.",
        )
    return SemanticPolicyDecision(
        action_type="artifact_publish",
        should_clarify=False,
        reason="A publish target is available and caller context confirms it.",
    )


def _experiment_decision(context: SemanticPolicyContext) -> SemanticPolicyDecision:
    if context.has_active_experiment:
        return SemanticPolicyDecision(
            action_type="experiment_manage",
            should_clarify=False,
            reason="An active experiment session is available to manage.",
        )
    return SemanticPolicyDecision(
        action_type="experiment_manage",
        should_clarify=True,
        clarification_prompt="Which experiment should I manage, or do you want to start a new one?",
        reason="The user mentioned experiment management, but no active experiment is known.",
    )


def _context_inspection_decision(frame: SemanticFrame, context: SemanticPolicyContext) -> SemanticPolicyDecision:
    if context.has_inspectable_context or context.has_pinned_context or semantic_frame_has_referenced_object(frame):
        return SemanticPolicyDecision(
            action_type="context_inspect",
            should_clarify=False,
            reason="Inspectable context is available from the frame or caller context.",
        )
    return SemanticPolicyDecision(
        action_type="context_inspect",
        should_clarify=True,
        clarification_prompt="Which answer or context path would you like me to inspect?",
        reason="The user asked for context inspection, but no inspectable target is available.",
    )


def _has_artifact_target(frame: SemanticFrame, context: SemanticPolicyContext) -> bool:
    if context.has_current_artifact or context.has_pending_whiteboard:
        return True
    if semantic_frame_has_signal(frame, "has_pending_whiteboard"):
        return True
    return semantic_frame_has_referenced_object(frame)


def _default_action_type(frame: SemanticFrame) -> str:
    if frame.task_type == "scenario_comparison":
        return "scenario_compare"
    if frame.task_type in {"drafting", "revision", "whiteboard_follow_up"}:
        return "whiteboard_draft" if frame.target_surface == "whiteboard" else "chat_response"
    if frame.target_surface == "vantage_inspect":
        return "context_inspect"
    if frame.target_surface == "experiment":
        return "experiment_manage"
    return "chat_response"
