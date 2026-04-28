# `src/vantage_v5/services/navigator.py`

LLM-based turn interpreter for Vantage V5. It decides whether a chat turn should stay in normal chat or enter Scenario Lab, and it can also return semantic hints for whiteboard collaboration and pinned-context continuity using the current message, recent history, active whiteboard excerpt plus any stable workspace scenario metadata, and an optional pinned saved-item summary as context. The implementation still uses `WorkspaceDocument` because the on-disk whiteboard storage layer is backed by workspace filenames. The model-facing router contract is pinned-context-first; legacy `selected_record*` wording survives only as parser tolerance for older outputs.

## Purpose

- Classify turns into `chat` or `scenario_lab`.
- Provide semantic hints for `whiteboard_mode` during normal chat.
- Decide whether an explicitly pinned context should be preserved as continuity context for the turn.
- Stay conservative and route ambiguous requests back to normal chat.
- Provide structured hints for Scenario Lab, including branch count and branch labels.
- Provide a first-class `control_panel` plan describing the product controls the Navigator would press and the working-memory context it wants assembled.

## Core Data Flow

- `NavigatorService.route_turn()` builds a compact payload from the user message, recent chat, active whiteboard, any parsed workspace scenario metadata, the requested composer-side whiteboard mode, the canonical `pinned_context_id`, any resolved pinned-context summary, any still-pending whiteboard offer/draft context from the previous turn, and a small structured `continuity_context`.
- That `continuity_context` is now metadata-first and intentionally small: `current_whiteboard`, a short `recent_whiteboards` list, `last_turn_referenced_record`, and `last_turn_recall`. It is server-built and internal to the navigator call; it does not require the public `/api/chat` request schema to change, and its newest referenced-record fact is read from internal Memory Trace frontmatter rather than inferred only from public payload aliases.
- If OpenAI is unavailable it returns a fallback decision that keeps the turn in normal chat and leaves the whiteboard / continuity hints unset so later layers can use conservative fallback behavior.
- Otherwise it calls the Responses API with a JSON schema contract and conservative instructions that reserve Scenario Lab for clear comparative what-if or option-analysis requests while also choosing whether normal chat should stay in chat, invite whiteboard collaboration, or draft directly into the whiteboard.
- The model now also returns a `control_panel` object with action button presses, requested working-memory queries, and the intended response call after context assembly. This is additive for now, but it is the migration target for removing scattered deterministic intent classifiers.
- The available control-panel actions include `apply_protocol`, which lets the Navigator choose reusable task guidance such as the Scenario Lab protocol before the response call.
- Control-panel actions now include a nullable `protocol_kind` field. It should be `null` for non-protocol actions, and it is required for `apply_protocol` with one of `email`, `research_paper`, or `scenario_lab`.
- Those instructions now explicitly frame workspace scenario metadata as transparent facts about the currently open whiteboard rather than a second hidden continuity system, so reopening a saved branch does not by itself force a fresh Scenario Lab rerun.
- Those instructions now explicitly tell the model to treat `pending_workspace_update` as live drafting context, so a short acceptance or continuation turn can flip a previous whiteboard offer into `whiteboard_mode="draft"` instead of repeating the invitation or misclassifying the turn as ordinary chat.
- The prompt also now tells the model that if the active whiteboard already contains a live draft and the user is revising that work, it should choose `whiteboard_mode="draft"` rather than reopening or reoffering the whiteboard.
- The prompt now also tells the model how to use the small continuity frame: prefer the current whiteboard for clear active-draft continuation, but prefer `last_turn_referenced_record` over generic recent-whiteboard recency when the user refers back to a recently surfaced saved item.
- The same interpretation pass can mark an explicitly pinned concept, memory, artifact, or reference note for continuity even when the follow-up is longer than the old short-message heuristic, so “let us keep playing with these rules in mind” can stay anchored to the pinned rules concept.
- The response is parsed into a `NavigationDecision`.
- Invalid, missing, or unusable model output falls back to a chat decision instead of blocking the request.

## Key Classes / Functions

- `NavigationDecision`: structured interpretation result with `mode`, `confidence`, `reason`, optional `comparison_question`, branch hints, optional `whiteboard_mode`, optional pinned-context continuity fields plus legacy compatibility aliases, and an optional `control_panel`.
- `NavigationDecision.to_dict()`: serializes the router decision for traces and downstream payloads.
- `NavigatorService`: OpenAI-backed interpreter used by the server before it dispatches a turn.
- `route_turn()`: main entry point for interpretation.
- `_openai_route()`: builds the structured navigator request and parses the model response.
- `_fallback_decision()`: returns a safe chat decision when routing cannot be completed.
- `_normalize_whiteboard_mode_hint()`, `_normalize_preserve_pinned_context()`, `_normalize_reason()`, and `_normalize_control_panel()`: validate the semantic hint fields coming back from the model while keeping the legacy selected-record aliases tolerated at parse time.

## Notable Edge Cases

- The service never writes files or opens workspaces directly; it only interprets the turn and now describes intended button presses in `control_panel`.
- `apply_protocol` is only a structured request; the server and protocol service validate the protocol kind and assemble working memory later.
- If `apply_protocol` omits `protocol_kind`, deterministic execution should not guess; the Navigator contract should be tightened instead so the model names the supported protocol explicitly.
- Confidence is clamped into a `0.0` to `1.0` range.
- Branch labels and counts are treated as hints, not guarantees, because Scenario Lab still validates and normalizes them later.
- The allowed route set is intentionally small so the rest of the system can dispatch deterministically after interpretation.
- Whiteboard and continuity hints are advisory rather than authoritative until the server merges them with explicit UI choices and policy guardrails.
- Whiteboard hints are also expected to distinguish between starting a fresh work product and continuing an already-visible draft in the current whiteboard.
- Pinned saved-item context is strong enough to keep follow-up turns anchored to an existing scenario comparison or other active record when the request does not clearly ask for new branches, and the same conservative revisit bias applies when the current whiteboard is already a saved scenario branch. The public/client seam still exposes compatibility `selected_record*` aliases, but the navigator now speaks pinned context to the model.
- The continuity frame stays intentionally small: the current implementation does not dump a long recent-whiteboard history into every navigator call, and it now prefers an explicit internal Memory Trace referenced-record fact for `last_turn_referenced_record` while still falling back to older preserved-context or unique-recall traces when needed.
