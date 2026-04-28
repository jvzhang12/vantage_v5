# Vantage Semantic Frame

This document captures the first production-safe slices of Vantage's semantic interpretation layer.

## Goal

Vantage should feel less like a button-driven chat wrapper and more like an agentic workspace that understands what the user is trying to do. The semantic frame is the compact contract for that understanding: it describes the user's likely goal, the task type, whether the turn is a follow-up, the intended surface, the referenced object, and the commitments Vantage should honor.

## Current Slice

- The frame is deterministic and built from signals Vantage already trusts: navigator routing, whiteboard mode resolution, pending whiteboard context, workspace scope, and pinned context.
- The server returns `semantic_frame` next to the existing `turn_interpretation`, then derives a sibling `semantic_policy` decision from the frame plus caller-known context.
- The webapp normalizes the frame and policy, surfaces a compact `Understood As` fact in Inspect, and can show the next semantic action or clarification prompt without adding another diagnostics panel.
- The contract is intentionally product-facing. It avoids raw prompt/debug wording and gives future UI and agent policy a stable view-model.
- The first active policy actions are narrow: explicit save/publish requests on a visible whiteboard are handled locally, ambiguous save/publish requests ask a clarification, and experiment-mode status/exit requests are answered as product behavior instead of generic chat.

## Fields

- `user_goal`: one short sentence describing what Vantage thinks the user wants.
- `task_type`: normalized task family such as `question_answering`, `drafting`, `revision`, `scenario_comparison`, `artifact_save`, `artifact_publish`, `context_inspection`, or `experiment_management`.
- `follow_up_type`: `new_request`, `continuation`, `acceptance`, `revision`, or `deictic_reference`.
- `target_surface`: `chat`, `whiteboard`, `scenario_lab`, `artifact`, `vantage_inspect`, or `experiment`.
- `referenced_object`: optional compact id/title/type/source for the pinned item or whiteboard in focus.
- `confidence`: bounded confidence score, inherited from navigation when possible and boosted only for deterministic local intents.
- `needs_clarification` and `clarification_prompt`: reserved for future clarification policy.
- `signals`: inspectable routing inputs that produced the frame.
- `commitments`: behavioral promises Vantage should preserve, such as keeping pinned context active or making reasoning inspectable.

## Semantic Policy

`src/vantage_v5/services/semantic_policy.py` adds a deterministic policy layer. It does not call models. Callers pass a `SemanticFrame` and optional `SemanticPolicyContext`; the return value is a serializable `SemanticPolicyDecision`.

Policy context flags:

- `has_current_artifact`: the caller has a concrete current artifact or assistant output that can be saved or published.
- `has_pending_whiteboard`: a pending or active whiteboard draft can be used as the artifact target.
- `has_pinned_context`: a pinned record or context item is active.
- `has_active_experiment`: an experiment session is active and can be managed.
- `has_inspectable_context`: an answer, reasoning path, frame, or context trail is available for inspection.
- `publish_target_confirmed`: the caller has already confirmed which artifact should be published.

Decision fields:

- `action_type` / `semantic_action`: normalized action such as `chat_response`, `whiteboard_draft`, `scenario_compare`, `artifact_save`, `artifact_publish`, `experiment_manage`, or `context_inspect`.
- `should_clarify`: whether the caller should ask before acting.
- `needs_clarification`: compatibility alias for `should_clarify`.
- `clarification_prompt`: a concise user-facing prompt when clarification is required.
- `reason`: a short inspectable explanation of why the deterministic policy chose that outcome.

Clarification rules:

- Save asks what to save when there is no referenced object, current artifact, or pending whiteboard.
- Publish asks what to publish when there is no target, and asks for confirmation until `publish_target_confirmed` is true.
- Experiment management asks which experiment to manage when there is no active experiment.
- Context inspection asks which answer or context path to inspect when no inspectable or pinned context is available.

## Next Steps

- Add a richer clarification-response flow for multi-target references such as “save the second one.”
- Feed selected semantic policy outcomes into `MetaService` as explicit no-write constraints for command-like turns that still go through chat.
- Keep UI affordances sparse; the frame should clarify the product, not become another diagnostics panel.
