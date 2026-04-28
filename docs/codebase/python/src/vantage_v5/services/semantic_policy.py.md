# `src/vantage_v5/services/semantic_policy.py`

Deterministic semantic policy read-model for Vantage turns.

## Purpose

- Consume `SemanticFrame` plus small caller-provided context flags.
- Decide whether an interpreted turn is safe to act on or should ask a clarification first.
- Keep save, publish, experiment-management, and context-inspection ambiguity handling out of server routing.

## Public Contract

- `SemanticPolicyContext`: frozen dataclass of simple booleans supplied by the caller.
- `SemanticPolicyDecision`: frozen dataclass with `action_type`, `should_clarify`, `clarification_prompt`, and `reason`; its payload also mirrors `action_type` as `semantic_action` and `should_clarify` as `needs_clarification` for frontend normalization.
- `decide_semantic_policy(frame, *, context=None)`: pure function returning a `SemanticPolicyDecision`.

## Context Flags

- `has_current_artifact`: a concrete answer or artifact is available to save or publish.
- `has_pending_whiteboard`: an active or pending whiteboard draft is available as the target.
- `has_pinned_context`: a pinned item can anchor inspection.
- `has_active_experiment`: an experiment session exists and can be managed.
- `has_inspectable_context`: an answer, reasoning path, or context trail can be inspected.
- `publish_target_confirmed`: the publish target has already been confirmed by the caller or user.

## Action Types

- `chat_response`: ordinary chat response.
- `whiteboard_draft`: drafting, revision, or whiteboard follow-up.
- `scenario_compare`: Scenario Lab comparison.
- `artifact_save`: save the current work product.
- `artifact_publish`: publish a reusable artifact.
- `experiment_manage`: manage an experiment session.
- `context_inspect`: inspect reasoning or context provenance.

## Clarification Behavior

- `artifact_save` clarifies when no referenced object, current artifact, or pending whiteboard exists.
- `artifact_publish` clarifies when there is no target, or when the target exists but has not been confirmed for publishing.
- `experiment_manage` clarifies when there is no active experiment session.
- `context_inspect` clarifies when there is no inspectable context, pinned context, or referenced object.

## Notable Behavior

- The module is deterministic and side-effect free.
- It does not import server code, make model calls, or mutate frame fields.
- `SemanticPolicyDecision.to_dict()` and `SemanticPolicyContext.to_dict()` are provided for response payloads and inspect surfaces.
- `LocalSemanticActionEngine` now consumes this policy for narrow local actions before generic chat: visible-whiteboard save, visible-whiteboard publish, ambiguous save/publish clarification, and experiment-mode status/exit explanation.
