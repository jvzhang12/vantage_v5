# `src/vantage_v5/services/visible_artifacts.py`

Normalization helpers for current-view artifact context.

## Purpose

- Accept the frontend's `visible_artifacts` payload from chat requests.
- Keep only bounded, text-bearing artifacts so model prompts stay portable and predictable.
- Preserve source refs and compact structured data for Inspect, traces, and model grounding.

## Key Functions

- `normalize_visible_artifacts()`: validates, truncates, and normalizes visible artifacts.
- `visible_artifacts_prompt_payload()`: returns a prompt-safe payload for model-backed services.
- `visible_artifacts_have_context()`: detects whether the current view should count as available context.

## Notable Behavior

- Limits the number of artifacts and truncates large content/data fields.
- Requires each artifact to have text content before it is included.
- Treats artifacts as active unless `active` is explicitly false.
