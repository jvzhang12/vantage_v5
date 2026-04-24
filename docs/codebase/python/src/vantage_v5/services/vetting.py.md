# `src/vantage_v5/services/vetting.py`

Filters search candidates down to the small set that is actually relevant to the current user message. This is the second pass after retrieval: search finds possibilities, vetting decides what should be carried forward. In the next migration slice, recent `Memory Trace` candidates should join the same decision path rather than bypassing it.

## Purpose

- Reduce noisy retrieval results to a focused subset.
- Optionally use an OpenAI model to select the best ids.
- Fall back to a deterministic score-threshold heuristic when no model is available.

## Core Data Flow

- `ConceptVettingService.vet()` returns immediately with an empty result when there are no candidates.
- With an OpenAI client, `_openai_vet()` sends the user message, the candidate payload, and an optional continuity hint to the model and expects selected ids plus a rationale.
- The response is re-mapped back onto the original candidate objects so the caller keeps the full records.
- Without a client, `_fallback_vet()` keeps items above a score threshold derived from the top result.
- If the OpenAI vetting call raises at runtime, `vet()` logs the error and falls back to the same deterministic score-threshold path instead of bubbling an exception up to `/api/chat`.
- Shared helpers now build a continuity hint for selected-record follow-ups, pending whiteboard continuations, and live whiteboard drafts, so chat and Scenario Lab can give the model the right semantic anchor without duplicating the same heuristics in multiple places. The hint is advisory only, summary-level context; it should not become a second hidden context channel that bypasses vetting, and selected-record hints are only emitted when preservation is actually in effect for the turn. Automatic selected-record preservation now yields to pending whiteboard or live whiteboard continuity when the navigator has not made an explicit preserve decision. Memory Trace retrieval should feed into the same bounded vetting pass once that store lands.

## Key Classes / Functions

- `ConceptVettingService`: main vetting façade.
- `vet()`: public entry point returning `(vetted_candidates, vetting_metadata)`.
- `_openai_vet()`: LLM-based selector with a capped result size.
- `_fallback_vet()`: deterministic selection by score threshold.
- `ContinuityHint`: compact payload describing the current continuity anchor or live draft context using summary-level metadata, not a second copy of the full working set.
- `build_continuity_hint()`: derives the continuity hint from the current turn, a genuinely preserved selected record, pending whiteboard state, and live workspace content.
- `should_preserve_selected_record()`: decides when an explicitly selected record should be treated as a continuity anchor.
- `anchor_selected_record_candidate()`: re-inserts the selected record into the vetted set when preservation is requested.
- `resolve_selected_record_candidate()`: resolves a selected record id into a candidate memory object from graph stores or the vault.

## Notable Edge Cases

- Empty candidate lists produce a structured “none relevant” result instead of raising.
- The OpenAI path truncates selected ids to five, even if the model returns more.
- If the model selects ids that are not present in the candidate list, they are silently ignored by the list comprehension that reconstructs the vetted set.
- Provider/runtime failures on the OpenAI path now degrade to `_fallback_vet()` so chat can still complete with deterministic candidate selection.
- The fallback threshold is `max(1.0, top_score * 0.35)`, so very weak candidate sets can still be filtered out entirely.
- Result order in the fallback path follows the original ranked candidate order, not the model’s order.
- Continuity hints are advisory context for the model, not hard selection rules; the actual candidate subset still comes from vetting, with a separate five-item cap when the selected record is explicitly preserved. When the navigator leaves preservation unset, pending whiteboard or live whiteboard continuity takes priority over the older short-follow-up heuristic.
