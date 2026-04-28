# `src/vantage_v5/services/semantic_frame.py`

Deterministic semantic read-model builder for Vantage turns.

## Purpose

- Convert existing trusted routing signals into a product-facing `semantic_frame` payload.
- Describe what Vantage thinks the user is trying to do without replacing `NavigatorService` or changing chat policy.
- Give the UI and future agent policy a stable contract for user goal, task type, follow-up type, target surface, referenced object, confidence, signals, and commitments.

## Key Classes / Functions

- `SemanticFrame`: dataclass with `to_dict()` serialization for the public response payload.
- `build_semantic_frame()`: builds the frame from the user message, `NavigationDecision`, resolved whiteboard mode, whiteboard entry mode, workspace scope, pinned context, and pending whiteboard state.

## Notable Behavior

- Stays deterministic for the first slice so the frame is safe to expose and easy to test.
- Treats Scenario Lab routing, explicit save/publish wording, context-inspection wording, experiment-management wording, whiteboard drafting, pinned-context continuity, and pending-whiteboard acceptance as separate semantic cases.
- Prefers pinned context as the referenced object when present; otherwise it references the active whiteboard when the whiteboard is the target surface or explicitly in scope.
- Keeps clarification fields on the frame itself conservative; the sibling semantic policy layer decides whether to interrupt, clarify, or act.
- Keeps `remember` out of artifact-save matching so explicit memory requests still flow through the memory/meta pipeline instead of being mistaken for whiteboard saves.
- Produces commitments that can later become product policy, such as keeping pinned context active, drafting visibly in the whiteboard, or making reasoning inspectable.
