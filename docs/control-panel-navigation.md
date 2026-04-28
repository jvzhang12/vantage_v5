# Control Panel Navigation

Vantage's target architecture is an LLM-directed control system rather than scattered deterministic intent classifiers.

## Mental Model

The Navigator LLM receives the user message, recent chat, visible whiteboard state, pinned context, pending whiteboard state, and continuity context. It returns a constrained control-panel plan:

- `actions`: product controls to press, such as `respond`, `recall`, `apply_protocol`, `open_whiteboard`, `draft_whiteboard`, `open_scenario_lab`, `inspect_context`, `save_whiteboard`, `publish_artifact`, `manage_experiment`, or `ask_clarification`.
- `working_memory_queries`: context requests the system should satisfy before response generation.
- `response_call`: whether another LLM call should answer after working memory is assembled.

Each action should include `protocol_kind: null` unless the action is `apply_protocol`.
For `apply_protocol`, `protocol_kind` is required and must be one of `email`, `research_paper`, or `scenario_lab`.

The deterministic layer should execute only the structured control-panel decision. It should validate targets, check whether a control is available, persist files, enforce confirmations, and return structured errors or clarification requests. It should not infer the user's intent from raw text when the Navigator can make that call.

## Current Slice

- `NavigationDecision` now carries a `control_panel` object.
- The Navigator prompt asks the model to return control-panel actions alongside mode and whiteboard decisions.
- The Navigator can press `apply_protocol` with a `protocol_kind`, letting deterministic code load durable or built-in protocols into working memory before response generation.
- Scenario Lab comparisons should apply the `scenario_lab` protocol so first-principles, counterfactual, causal, tradeoff, and assumption-surfacing guidance can enter working memory without raw-text keyword sorting.
- `/api/chat` exposes that control panel under `turn_interpretation.control_panel`.
- `/api/chat` also exposes safe `system_state` and final-turn `activity`, so the UI can show what Vantage did without interpreting raw user text.
- The frontend turn-payload normalizer preserves the control panel as `controlPanel`.
- Fallback routing returns a minimal `respond` control panel instead of inventing product actions.

## Remaining Migration Work

The following older paths still deterministically interpret user text and should migrate behind Navigator control-panel actions:

- `semantic_frame.py`: regex-based task and surface classification.
- `server.py`: explicit whiteboard overrides, current-draft continuation checks, pending-whiteboard carry checks, and save/publish target confirmation helpers.
- `services/meta.py`: fallback graph-write decisions based on message phrases.
- `services/vetting.py`: follow-up and whiteboard-edit continuity heuristics.
- `webapp/app.js`: local deictic whiteboard reopen interception before `/api/chat`.

The migration order should be: move semantic frame fields into the Navigator schema, make pending-whiteboard carry a Navigator control action, replace whiteboard override regexes with `draft_whiteboard` / `open_whiteboard` actions, then move graph-write choices into explicit control-panel actions validated by deterministic executors.
