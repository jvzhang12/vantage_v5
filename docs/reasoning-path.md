# Reasoning Path

## Purpose

`Reasoning Path` is the guided inspection view for how Vantage built a given turn.

It lives inside `Vantage`, not in ordinary chat and not in the whiteboard.

The goal is to make the turn pipeline inspectable without turning the product into a raw operator console or a prompt dump.

This document is grounded in the current `vantage-v5` repository rather than an idealized future architecture. The current UI exposes a six-stage reasoning rail inside the Vantage answer dock:

- `Request`
- `Route`
- `Candidate Context`
- `Recall`
- `Working Memory`
- `Outcome`

The rail is product-facing, not a raw trace dump. `Recall` is the vetted subset that entered the turn, while `Working Memory` is the broader in-scope generation summary. `Memory Trace` appears in that inspection flow, but it is not the same thing as the `Recall` list.

## Product Framing

Reasoning Path should not be described as raw `chain of thought`.

For this repository, the better product framing is:

- a structured turn trace
- a guided reasoning path
- a step-by-step explanation of how Vantage assembled context and chose a path

That framing matches the current architecture more truthfully because Vantage already has explicit stages for:

- request intake
- whiteboard scoping
- navigator interpretation
- retrieval
- vetting
- working-memory assembly
- answer generation
- grounding disclosure
- post-turn durable writes

The feature should answer a practical user question:

`How did Vantage build this answer?`

It should not attempt to expose:

- hidden prompt internals as the main product
- freeform internal monologue
- raw model scratchpad text
- token-level reasoning artifacts

## Why It Belongs In Vantage

`Chat` should remain the default surface.

`Whiteboard` should remain the collaborative drafting surface.

`Vantage` is already the inspection surface for:

- Working Memory
- Learned
- the Library
- Reasoning Path
- turn interpretation and other internals

That makes `Vantage` the right home for Reasoning Path.

It should be implemented as a deeper inspection layer inside the existing Vantage turn review, not as a brand-new top-level product surface.

Putting Reasoning Path directly in chat would make the chat surface heavy and operator-like.

Putting it in the whiteboard would blur the distinction between:

- collaborative drafting
- current-turn inspection

That would violate the current repo semantics described in:

- [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
- [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)
- [docs/semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md)

## Canonical Distinctions

Reasoning Path should preserve these distinctions rather than flatten them.

### Working Memory vs Recall

The current repo keeps an important distinction:

- `Recall` is the vetted recalled item set produced by retrieval plus vetting.
- `Working Memory` is the broader bounded in-scope generation context.
- top-level `recall` carries the narrower recalled subset.
- legacy `working_memory` remains a compatibility alias for that subset.

Other grounded context is represented separately through `response_mode`, especially:

- `whiteboard`
- `recent_chat`
- `pending_whiteboard`
- `mixed_context`

Reasoning Path should make that explicit instead of hiding it.

Recommended UI interpretation:

- `Working Memory`: the full in-scope generation context behind the answer, including the current user message, recent chat, whiteboard content when in scope, pending whiteboard context when intentionally carried, pinned context when preserved, and recalled items
- `Recall`: the recall-shaped subset exposed today through top-level `recall`, with `working_memory` kept only as a compatibility alias
- `Memory Trace`: the searchable recent-history layer that can contribute recalled items to Working Memory
- `Other Grounded Context`: whiteboard, recent chat, pending whiteboard, and other non-retrieval context that was still in scope
- `Answer Context Summary`: a guided explanation of what supported the answer, not a raw payload viewer
- the current turn’s `memory_trace_record` can expose structured metadata such as turn mode, trace scope, workspace scope, recalled ids, learned ids, and preserved-context ids for inspection, but that metadata still explains Recall rather than replacing it

### Whiteboard vs Working Memory

The whiteboard is a separate collaborative surface that may contribute to current-turn context when it is in scope.

It should not be represented as if it were just another recalled note.

The whiteboard's history belongs to Memory Trace, not to the surface itself.

### Turn Interpretation vs Retrieval

The navigator decides:

- whether the turn stays in chat or enters Scenario Lab
- whether whiteboard collaboration should be invited or drafted directly
- whether explicitly pinned context should be preserved for continuity

The current repository now gives the navigator a small structured continuity frame for recently active whiteboards and last-turn referenced saved items. Newer turns write that referenced-record fact explicitly into Memory Trace; older turns can still fall back to preserved-context or unique-recall reconstruction.

That implemented V1 contract is documented in:

- [docs/navigator-continuity-contract.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/navigator-continuity-contract.md)

The intent is to improve deictic follow-ups such as `pull that up on the whiteboard` without broadening Working Memory or flooding the interpreter with too much context.

Retrieval and vetting happen later.

That later stage is where Memory Trace, Library items, and other continuity sources are assembled into Recall.

Reasoning Path shows those as separate stages, and the current UI exposes a clickable inspection rail so the user can open concrete detail for `Request`, `Route`, `Candidate Context`, `Recall`, `Working Memory`, and `Outcome` directly in Vantage.

### Learning vs Internal Reasoning

`Learned` should remain the answer to:

`What changed durably because of this turn?`

It should not become a bucket for transient internal reasoning.

### Scenario Lab vs Normal Chat

Scenario Lab is a navigator-routed mode with its own generation and persistence path.

Reasoning Path should show when the turn entered that mode rather than treating it like an ordinary chat answer with extra cards.

## Current Architecture Map

This is the current request-to-response pipeline for `POST /api/chat`.

## Current UI Mapping

The Vantage answer dock maps the pipeline into a compact staged inspection rail.

Each stage is clickable and opens turn-scoped detail directly inside the same dock.

### Request

Shows the explicit user message for the turn.

### Route

Shows the routed turn decision already exposed through `turn_interpretation`, including:

- path (`Chat` or `Scenario Lab`)
- whiteboard decision when relevant
- reason
- confidence
- continuity preservation when pinned context stays in scope

The stage label is `Route` because the shipped UI uses it as the user-facing summary of where the turn went and why, while the detailed metadata still comes from `turn_interpretation`.

### Candidate Context

Shows the concrete candidate items that were surfaced before vetting narrowed the set.

It lets the user inspect which concepts, saved notes, memory-trace candidates, and reference notes were considered.

### Recall

Shows the recalled items that actually entered Recall for the answer.

This is the selected subset, not the whole candidate pool.

### Working Memory

Shows a summary of what was in scope for the answer, not just the recalled-item list.

That includes:

- recalled items when present
- additional grounded context from `response_mode`
- whiteboard scope when the whiteboard was intentionally in scope
- Memory Trace contribution when recent history supplied recalled items

The current UI opens an inline include/exclude table for generation scope. The table is intentionally compact and truth-preserving:

- `User request`: always included
- `Recall`: count-based, showing `0 items`, `1 item`, or `N items`
- `Whiteboard`: included or excluded based on `response_mode.context_sources`
- `Whiteboard scope hint`: shown separately when `workspace_context_scope` is available
- `Recent chat`: included or excluded based on `response_mode.context_sources`
- `Prior whiteboard`: shown only when `pending_whiteboard` was actually in scope
- `Pinned context preserved`: shown only when `interpretation.preservePinnedContext` is explicitly boolean, with the legacy selected-record alias accepted only for compatibility
- `Memory Trace contribution`: counts only recalled `memory_trace` items that entered Recall

The turn payload can also expose structured metadata for the current trace record itself, including:

- `turn_mode`
- `trace_scope`
- `workspace_scope`
- `grounding_mode`
- `recalled_ids`
- `learned_ids`
- preserved-context ids when continuity was explicit

That detail supports guided inspection without turning `Memory Trace` into a raw transcript browser or a second Library.

The stage headline should read as scope, not hidden causality. Prefer phrasing like `In scope for generation: Recall + Whiteboard.` over `Working Memory used ...`.

Candidate `memory_trace` items stay in `Candidate Context`; they do not appear in `Working Memory`.

### Outcome

Shows the answer/result side of the turn, including:

- grounding label
- learned durable changes
- whiteboard draft/update outcome when relevant
- Memory Trace capture

The current UI keeps `Recall` and the candidate pools inspectable without promoting them into the main chat surface or dumping the user into the general library inspector.

### Backend Notes

The request enters through `/api/chat` in [src/vantage_v5/server.py](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/server.py).

Important incoming fields already exist:

- `message`
- `history`
- `workspace_id`
- `workspace_scope`
- `workspace_content`
- `whiteboard_mode`
- `pinned_context_id`
- `selected_record_id` as a compatibility alias
- `memory_intent`
- `pending_workspace_update`

These names are still compatibility-oriented implementation fields. In product terms, `workspace_content` is the live whiteboard buffer, `workspace_scope` is the whiteboard scope hint, and pinned context is the canonical continuity noun for the public/client seam.

Before interpretation, the server normalizes workspace scope and may carry pending whiteboard context forward when the turn clearly continues it.

The navigator then decides whether the turn stays in chat or enters Scenario Lab, and whether the whiteboard should stay in chat, invite collaboration, or draft directly.

After that, retrieval searches the bounded mixed pool, vetting chooses the recalled subset, and the response mode explains whether the answer was grounded by recall, whiteboard, recent chat, pending whiteboard, or a mixed combination.

That is the current Reasoning Path contract: show the route, show the candidate pool, show the recalled subset, and show the bounded in-scope context without collapsing everything into one opaque bucket.
