# Vantage V5 Glossary

## Purpose

This glossary defines the core product terms for `vantage-v5`.

Use these definitions when changing UI copy, API semantics, retrieval behavior, or documentation.

If another document uses these terms differently, this glossary should be treated as the canonical semantic reference for the current repo unless `README.md` explicitly says otherwise.

For implementation-facing behavioral rules built on top of these definitions, see [semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md).

For the small structured continuity payload implemented for the navigator interpreter, see [navigator-continuity-contract.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/navigator-continuity-contract.md).

## Core Terms

### Working Memory

`Working Memory` is everything in scope that is sent to the LLM for generation of the current response.

It includes:

- the current user message
- recalled items from `Memory Trace`
- recalled items from the `Library`
- pinned context
- selected context only when a turn explicitly preserves it in scope
- recent chat
- whiteboard content when the whiteboard is in scope
- pending whiteboard context when it is intentionally carried into the turn

Working Memory must stay bounded and inspectable.

In the product UI, Working Memory should make Recall and active context legible rather than collapsing all inputs into an opaque blob.

In the current API, top-level `recall` carries that narrower recall-shaped subset produced by retrieval and vetting.

Legacy `working_memory` is still emitted as a compatibility alias for that same subset.

The product meaning of Working Memory is broader than those fields, and the UI should say so explicitly instead of implying they are the same thing.

### Whiteboard

`Whiteboard` is the shared editable document that the user and the LLM can both read and modify collaboratively.

The whiteboard is a drafting surface, not the default chat surface.

The whiteboard may contribute to Working Memory when it is in scope, but it remains a separate product surface and should stay visibly distinct from Working Memory and from the Library.

### Memory Trace

`Memory Trace` is the automatically captured recent history of the system.

Every user request should create Memory Trace, whether or not a whiteboard is active.

Memory Trace is:

- automatic
- searchable
- recent-history oriented
- recallable
- separate from the curated durable Library

Memory Trace is not the same thing as Working Memory.
It is the recent history layer that retrieval can search before vetting decides what enters the current turn.

### Library

`Library` is the inspectable collection of saved material available to the system.

It includes:

- `Concept KB`
- `Memories`
- `Artifacts`
- `Reference Notes`

An item can exist in the Library without being in Working Memory for the current turn.

### Recall

`Recall` is primarily the retrieval step or recalled subset that feeds Working Memory.

It may include:

- `Memory Trace`
- `Concept KB`
- `Memories`
- `Artifacts`
- `Reference Notes`

`Recall` is a turn-level retrieval result, not the whole of `Working Memory`.
In the current API, top-level `recall` reflects the vetted recalled subset, while legacy `working_memory` remains as a compatibility alias rather than the full product meaning of Working Memory.

### Workspace

`Workspace` is now a deprecated implementation term.

Use `Whiteboard` for the user-facing live shared draft.

Near-term backend compatibility fields such as `workspace_id`, `workspace_content`, and `workspace_update` may remain until payload migration is complete, but new product language should prefer `Whiteboard`.

### Vantage

`Vantage` is the guided inspection surface for the system.

It is where the user can inspect:

- Working Memory
- Learned items
- the Library
- Reasoning Path
- turn interpretation and other internals

`Vantage` is not the default chat surface and is not the whiteboard.

### Learned

`Learned` is what the system created, saved, or updated as a result of the current turn.

This should answer a narrow question:

`What changed durably because of this turn?`

### Pinned Context

`Pinned Context` is context the user explicitly wants carried into future Working Memory until it is cleared.

Pinning is stronger than opening or inspecting an item.

In the current public client/server seam, `pinned_context_id` / `pinned_context` are the canonical continuity fields, while `selected_record_id` / `selected_record` remain compatibility aliases.

### Open / Inspect

`Open` or `Inspect` means the user is viewing an item.

Opening an item does not automatically make it part of future Working Memory.
Inspection selection stays local to the Vantage view unless the user explicitly pins it.

For artifacts, `Inspect` should stay read-only and `Reopen in whiteboard` should be the explicit continuation action.

### In Scope

`In Scope` means a context source is allowed to influence the current answer.

An item or surface can be visible but out of scope.

This distinction matters especially for:

- whiteboard visibility
- opened library items
- pinned context

### Recent Chat

`Recent Chat` is the bounded short-term conversation history automatically carried into the current turn.

It is part of the current-turn context model, and it can be part of Working Memory, but it should stay conceptually distinct from recalled saved knowledge and from the whiteboard.

### Navigator Continuity Frame

`Navigator Continuity Frame` is the small structured continuity payload implemented for the turn interpreter.

It is not the same thing as `Working Memory`.

Its job is narrower:

- help the navigator resolve what the user is referring to right now
- help the navigator distinguish current-draft continuation from reopening an older saved draft
- keep short deictic follow-ups like `that one` or `pull that up on the whiteboard` interpretable

It should stay metadata-first and intentionally small.

Recommended default ingredients are:

- current whiteboard
- a short recent-whiteboards list
- the strongest last-turn referenced saved record when confidence is high
- a small last-turn recall shortlist
- pending whiteboard update when present

### Concepts

`Concepts` are timeless reasoning knowledge.

They are the highest-trust durable substrate for reusable understanding.

### Memories

`Memories` are retained facts about the user, project, or ongoing continuity.

They preserve continuity rather than timeless theory.

### Artifacts

`Artifacts` are concrete work products.

Examples include:

- drafts
- emails
- plans
- essays
- comparisons
- saved whiteboards

Artifacts are durable Library items.
They should be inspected in `Vantage` and reopened into the `Whiteboard` when the user wants to continue editing from a saved version.

### Scenario Lab

`Scenario Lab` is an explicit reasoning mode for multi-branch what-if work.

It should produce durable branch outputs and a comparison artifact, not just a formatted ordinary chat answer.
It is routed separately from ordinary chat.

### Experiment Mode

`Experiment Mode` is a session-local sandbox.

In Experiment Mode, created notes remain temporary unless the user explicitly promotes them.

## Canonical Distinctions

These distinctions should not drift:

- `Visible` is not the same as `active`.
- `Open` is not the same as `pinned`.
- `Saved` is not the same as `in Working Memory`.
- `Whiteboard` is a shared drafting surface; it is not the same thing as the Library.
- `Memory Trace` is the recent searchable history layer; it is not the same thing as the Library.
- `Whiteboard` may be in Working Memory, but it is still a separate surface.
- `Working Memory` is the whole in-scope generation context; top-level `recall` is only the vetted recalled subset, with `working_memory` retained as an alias.
- `Recall` is the retrieval step or vetted subset that can become part of Working Memory.
- `Learned` is about what changed this turn, not everything the system considered.
- `Workspace` is a compatibility term; `Whiteboard` is the intended product term.
- `Pinned Context` is the canonical continuity noun for the public/client seam; selected-record naming is now a compatibility alias.

## Product Rules Implied By These Definitions

- Working Memory should stay bounded.
- Every turn should leave Memory Trace.
- The user should be able to inspect what influenced a response.
- Whiteboard content should influence the answer only when it is in scope.
- Opening a saved item should default to inspection, not automatic carry-forward.
- Pinning is the explicit mechanism for keeping context active across turns.
- Durable saved material should remain visibly split into concepts, memories, artifacts, and reference notes.

## UI Guidance

The UI should preserve these roles:

- `Chat` is the default interaction surface.
- `Whiteboard` is the collaborative drafting surface.
- `Vantage` is the inspection surface.
- `Working Memory` explains the full current-turn generation context, while `working_memory` names the narrower vetted recalled subset when that distinction matters.
- `Memory Trace` explains the recent searchable history layer available for recall.
- `Recall` should usually be explained as what was pulled in from Memory Trace and the Library, rather than as the top-level product noun.
- `Learned` explains durable changes from the turn.
- `Library` explains what exists beyond the current turn.

That separation is part of the product, not just implementation detail.
