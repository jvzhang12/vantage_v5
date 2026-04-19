# `src/vantage_v5/services/navigator.py`

LLM-based turn interpreter for Vantage V5. It decides whether a chat turn should stay in normal chat or enter Scenario Lab, and it can also return semantic hints for whiteboard collaboration and selected-record continuity using the current message, recent history, active whiteboard excerpt plus any stable workspace scenario metadata, and an optional selected saved-item summary as context. The implementation still uses `WorkspaceDocument` because the on-disk whiteboard storage layer is backed by workspace filenames.

## Purpose

- Classify turns into `chat` or `scenario_lab`.
- Provide semantic hints for `whiteboard_mode` during normal chat.
- Decide whether an explicitly selected record should be preserved as continuity context for the turn.
- Stay conservative and route ambiguous requests back to normal chat.
- Provide structured hints for Scenario Lab, including branch count and branch labels.

## Core Data Flow

- `NavigatorService.route_turn()` builds a compact payload from the user message, recent chat, active whiteboard, any parsed workspace scenario metadata, the requested composer-side whiteboard mode, the selected record id, any resolved selected-record summary, and any still-pending whiteboard offer/draft context from the previous turn.
- If OpenAI is unavailable it returns a fallback decision that keeps the turn in normal chat and leaves the whiteboard / continuity hints unset so later layers can use conservative fallback behavior.
- Otherwise it calls the Responses API with a JSON schema contract and conservative instructions that reserve Scenario Lab for clear comparative what-if or option-analysis requests while also choosing whether normal chat should stay in chat, invite whiteboard collaboration, or draft directly into the whiteboard.
- Those instructions now explicitly frame workspace scenario metadata as transparent facts about the currently open whiteboard rather than a second hidden continuity system, so reopening a saved branch does not by itself force a fresh Scenario Lab rerun.
- Those instructions now explicitly tell the model to treat `pending_workspace_update` as live drafting context, so a short acceptance or continuation turn can flip a previous whiteboard offer into `whiteboard_mode="draft"` instead of repeating the invitation or misclassifying the turn as ordinary chat.
- The prompt also now tells the model that if the active whiteboard already contains a live draft and the user is revising that work, it should choose `whiteboard_mode="draft"` rather than reopening or reoffering the whiteboard.
- The same interpretation pass can mark an explicitly selected concept, memory, artifact, or reference note for continuity even when the follow-up is longer than the old short-message heuristic, so “let us keep playing with these rules in mind” can stay anchored to the selected rules concept.
- The response is parsed into a `NavigationDecision`.
- Invalid, missing, or unusable model output falls back to a chat decision instead of blocking the request.

## Key Classes / Functions

- `NavigationDecision`: structured interpretation result with `mode`, `confidence`, `reason`, optional `comparison_question`, branch hints, optional `whiteboard_mode`, and optional selected-record continuity fields.
- `NavigationDecision.to_dict()`: serializes the router decision for traces and downstream payloads.
- `NavigatorService`: OpenAI-backed interpreter used by the server before it dispatches a turn.
- `route_turn()`: main entry point for interpretation.
- `_openai_route()`: builds the structured navigator request and parses the model response.
- `_fallback_decision()`: returns a safe chat decision when routing cannot be completed.
- `_normalize_whiteboard_mode_hint()` and `_normalize_preserve_selected_record()`: validate the semantic hint fields coming back from the model.

## Notable Edge Cases

- The service never writes files or opens workspaces directly; it only interprets the turn.
- Confidence is clamped into a `0.0` to `1.0` range.
- Branch labels and counts are treated as hints, not guarantees, because Scenario Lab still validates and normalizes them later.
- The allowed route set is intentionally small so the rest of the system can dispatch deterministically after interpretation.
- Whiteboard and continuity hints are advisory rather than authoritative until the server merges them with explicit UI choices and policy guardrails.
- Whiteboard hints are also expected to distinguish between starting a fresh work product and continuing an already-visible draft in the current whiteboard.
- Selected saved-item context is strong enough to keep follow-up turns anchored to an existing scenario comparison or other active record when the request does not clearly ask for new branches, and the same conservative revisit bias applies when the current whiteboard is already a saved scenario branch.
