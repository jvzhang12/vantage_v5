# Vantage V5

Vantage V5 is a fresh restart point for the product and architecture.

The core reset is simple:

`Vantage should feel like talking to any other good LLM, while quietly building durable concept-based memory behind the scenes.`

## Product Principles

### 1. Chat First
The first requirement is a simple, natural chat experience.

The user should feel like they are talking to a normal high-quality LLM:
- natural back-and-forth
- smooth topic changes
- no visible architecture getting in the way
- no refusals caused by internal workspace problems

### 2. Architecture Supports Chat
Vantage-specific systems should improve chat, not replace it.

The user-facing default should be:
- a standard chat transcript
- a message composer
- compact per-turn evidence in chat so the product difference is visible without opening internals every turn
- a deliberate `Vantage` view for Reasoning Path, Working Memory, Learned, and the library
- an on-demand whiteboard that appears only when the user asks for it or accepts an invite/draft flow, and then becomes the main drafting surface rather than another inspection dock

### 3. Persistent Memory
The assistant should have persistent memory across conversations.

That memory should come from a durable concept graph, not from replaying whole transcripts.

### 4. Whiteboard
V5 should include a whiteboard where the user and assistant can collaboratively view, edit, and work on a Markdown file.

This live shared draft is for active collaboration.
It is intentionally on-demand rather than always visible.
It is not automatically the same thing as durable memory.

The user and assistant should be able to:
- read the current Markdown whiteboard
- edit it collaboratively
- use chat to discuss and modify it
- surface whiteboard offers as chat-level prompts until the user opens the whiteboard
- stage replace-or-append choices as explicit in-product whiteboard decisions rather than browser-native confirmation dialogs
- keep whiteboard lifecycle cues legible as a transient draft, saved whiteboard, or promoted artifact
- later promote it into a durable artifact when appropriate
- derive a concept from it only when the goal is timeless knowledge rather than preserving the draft itself

### Suggested Whiteboard Rule
For the MVP, there should be one optional active whiteboard document.

It only exists when the user opens or creates one.
Chat should still work normally when no whiteboard document is active.

### Canonical Product Terms

The intended top-level product vocabulary is:

- `Whiteboard`: the live shared draft the user and the LLM are working on
- `Memory Trace`: the automatically captured recent searchable history for every turn
- `Working Memory`: the bounded context actually sent to the LLM for generation
- `Library`: the curated durable layer of concepts, memories, artifacts, and reference notes

`Recall` should be treated mainly as the retrieval step or recalled subset that feeds Working Memory, not as the main top-level product noun. In the current API, `recall` carries that narrowed vetted subset and `working_memory` remains a compatibility alias for it.

`Workspace` should now be treated as a deprecated implementation term.
Existing payloads and storage paths may still use `workspace_*` names for compatibility, but new product language should prefer `Whiteboard`.

## Core Memory Model

### Separate Knowledgebases
V5 should keep the concept knowledgebase separate from the memory and artifact knowledgebase.

- `concepts/` stores timeless, reusable reasoning knowledge
- `memories/` stores retained user, project, and session facts
- `artifacts/` stores concrete outputs such as drafts, plans, essays, and workspace snapshots

This means Vantage should not treat every saved thing as a concept.

### Experiment Mode
V5 should support bounded temporary experiment sessions.

In experiment mode:
- the user can chat, edit a workspace, and let the system create temporary concepts, memories, and artifacts
- those saved items are written as temporary Markdown files inside a session-local graph
- retrieval can use those temporary notes for the duration of the session
- the durable Vantage graph remains untouched unless the user explicitly promotes something

This allows Vantage to learn within a session without polluting long-term memory.

### Concepts Are Durable Memory
Timeless durable knowledge is stored as concepts in Markdown files.

If something is genuinely novel, a concept should be made for it as an `.md` file.

Concepts are the canonical durable reasoning objects.

### Memories and Artifacts
Saved memories and artifacts are also durable, but they are not concepts.

- memories preserve continuity
- artifacts preserve concrete work products
- concepts preserve timeless knowledge

### Shared Workspace vs Concept Graph
V5 should explicitly distinguish between:

- `whiteboard`
- `memory trace`
- `concept graph`

The whiteboard is the live drafting and collaboration surface.
Memory Trace is the recent structured history layer created for every turn, whether or not a whiteboard is active.
The concept graph and the wider Library are the curated durable memory layer.
Working Memory is the full bounded in-scope context shared with the assistant for the current turn.
That includes the current user message plus any recalled Memory Trace or Library items, relevant recent chat, whiteboard context, pending whiteboard context, and explicitly preserved selected context.
The Vantage view is where the user deliberately inspects Working Memory, learned items, and other internals.
When the whiteboard is open, it should feel like a drafting mode, not like another panel inside Vantage.

This means:
- not every whiteboard draft becomes a concept
- the user and assistant can iterate on a Markdown file before it is worth remembering
- every turn should leave memory trace
- memory trace now has a first-class Markdown store in `memory_trace/`, distinct from JSON debug traces in `traces/`
- a whiteboard document can later be promoted into an artifact
- a concept can also be derived from a whiteboard document instead of being a raw copy of it
- the whiteboard should stay visibly separate from working memory, from the durable library, and from the default chat surface

### Suggested Concept Granularity
For the MVP, a concept should default to one coherent durable unit of meaning.

In practice, this usually means:
- one compact note
- one coherent artifact-sized note
- not an entire transcript
- not a fragmented sentence-level object

### Concept Card
Every concept should have a concept card: a one-sentence summary of the concept.

The concept card is the primary routing and retrieval representation of the concept.

Each concept therefore has at least:
- `title`
- `card`
- `body`
- `links`
- metadata

### Example Concept Shape

```md
---
id: thanksgiving-dinner-plan
title: Thanksgiving Dinner Plan
type: concept
card: A plan for preparing and coordinating a full Thanksgiving dinner.
created_at: 2026-04-06
links_to:
  - cooking
  - hosting
---

This concept captures the user's request to plan and prepare a full Thanksgiving dinner, including menu planning, cooking order, timing, and coordination.
```

## Retrieval Rule

The assistant should never receive the entire concept graph in its context window.

Instead:
1. search retrieves candidate items from the bounded local memory system
2. those candidates may come from `Memory Trace`, `concepts/`, `memories/`, `artifacts/`, and optional read-only vault notes
3. an LLM vetting call chooses which items are actually relevant
4. only those vetted items are sent to the assistant as part of Working Memory

This is a hard boundedness rule.

### Search Contract
For the MVP:
- chat-time retrieval returns a mixed candidate pool rather than concept-only results
- the current implementation retrieves up to 16 combined candidates across concepts, memories, artifacts, and vault notes
- the vetting LLM selects up to 5 relevant items
- only those selected items are passed into assistant context

The top 5 vetted items are the bounded memory neighborhood for the turn.

### Suggested Search Implementation
For the MVP, search should be hybrid:
- title search
- concept card search
- body fallback
- embeddings when available

This keeps search practical without making the whole system depend on embeddings from day one.

## Runtime Loop

The intended V5 runtime is:

1. user sends a message
2. the system records memory trace for the turn
3. search retrieves candidate items from memory trace, concepts, memories, artifacts, and optional reference notes
4. a vetting LLM chooses the relevant subset
5. the assistant responds using:
   - the user message
   - bounded recent chat
   - the vetted relevant recalled items
   - the whiteboard when relevant
6. after the assistant response, a meta call runs
7. the meta call decides the best graph action relative to the existing knowledge graph
8. the system executes that graph action when needed

### Suggested Recent Chat Rule
For the MVP, the assistant should receive bounded recent chat in addition to vetted memory items.

A good default is the last 4 to 8 turns.

### Interpretation Rule
V5 should rely on LLM reasoning for semantic interpretation and deterministic code for safety and execution.

In practice:
- the turn interpreter should decide whether a turn stays in chat or enters Scenario Lab
- the turn interpreter should decide whether selected context should stay anchored for continuity
- the turn interpreter should decide whether normal chat should stay in chat, invite the whiteboard, or draft there
- deterministic code should validate schemas, enforce guardrails, merge explicit UI choices, and perform durable writes

This keeps routing fluid and semantic without making persistence or safety brittle.

## Meta Call

After every user request and assistant response, a meta call should ask:

`What is the best thing I can do with this information in the context of our existing knowledge graph?`

This meta call is graph-conditioned.

It should not evaluate the turn in isolation.
It should evaluate the turn relative to the retrieved relevant memory neighborhood, with concepts remaining the highest-trust graph substrate.
The current policy direction is concept-forward: when a turn is stable, generalizable, and durable enough to matter beyond the current moment, the meta call should lean toward `create_concept` instead of defaulting to `no_op`.

### Meta Call Inputs
The meta call should receive:
- user message
- assistant response
- top 5 vetted relevant memory items, with concepts treated as the highest-trust reasoning substrate
- possibly bounded recent chat/session context

### Meta Call Responsibility
The meta call decides the highest-value graph action implied by the interaction.

This includes questions like:
- is this already represented?
- is this novel relative to the graph?
- should this become a new concept?
- should this revise an existing concept?
- should this link to an existing concept?
- should this do nothing?

### Meta Call Action Types
The MVP action vocabulary should stay small:
- `no_op`
- `create_concept`
- `create_memory`
- `promote_workspace_to_artifact`

### Suggested Vetting Call Output
For the MVP, the vetting call should return:
- selected item ids
- short rationale
- whether none of the candidates are relevant
- optional novelty signal

### Suggested Meta Call Policy
The meta call should be concept-forward, but only inside the durable-write guardrails.

If a turn is stable, generalizable, and durable enough to matter beyond the current moment, it should prefer `create_concept` over `no_op`.

If a new concept is close to an existing concept but still captures a distinct durable unit, it should usually still be created and linked into that nearby concept neighborhood rather than being suppressed just because it is related.

If the user explicitly said `dont_save`, or the turn is a pending whiteboard offer or draft, it should still return `no_op`.

If the turn is a near-duplicate of an existing concept, ambiguous, workspace-only, or not durable enough to matter later, it should still prefer `no_op` rather than writing noisy concepts.

## Novelty Rule

Novelty is not determined in isolation.
Novelty is determined relative to the retrieved memory neighborhood, especially the vetted concept context.

A turn is novel when it is not already well represented by the top relevant context and is durable enough to matter beyond the current moment.

If a turn is genuinely novel and durable, a Markdown concept should usually be created for it unless a guardrail says otherwise.

Not every turn should become a concept.
Only durable, semantically coherent novelty should become a concept.

### Suggested Concept Creation Rule
For the MVP:
- novel durable information in chat should lean toward concept creation automatically
- shared workspace documents should automatically leave an artifact trail as drafting iterations are produced or saved, even when the whiteboard file itself remains the collaborative working surface
- concept derivation from workspace should remain a narrower, more intentional path than artifact promotion

## Workspace Promotion

The shared workspace document should be promotable into durable saved state.

There are at least two useful promotion paths:

- `store workspace as artifact`
- `derive concept from workspace`

This allows the user and assistant to collaborate in Markdown first, then persist either concrete outputs or distilled knowledge later.

### Suggested Editing Model
For the MVP, the assistant should usually propose edits first rather than silently changing the workspace document.

This keeps collaboration legible and reduces accidental destructive changes.

The main exception is work-product collaboration during normal chat. When the model determines that the user is asking for a concrete artifact such as an email, plan, itinerary, checklist, outline, essay, paper, list, or code draft, it should invite whiteboard collaboration first unless the user already clearly wants the whiteboard or explicitly wants the full output in chat.

That whiteboard path remains separate from concept and memory writes: a draft can live in the shared workspace without becoming a concept or memory, while each whiteboard draft iteration is automatically captured as an artifact snapshot.

Once the user chooses the whiteboard, Vantage may return a pending whiteboard draft proposal and keep the chat reply concise.
That proposal should be surfaced through `workspace_update` metadata rather than silently applying the draft to the workspace file.
If the whiteboard is already open with a live draft and the user is clearly revising that draft, Vantage should continue editing the current whiteboard rather than reoffering or reopening a new one.
If the accepted draft is clearly a different document from the currently active whiteboard, the UI should open it as a fresh unsaved whiteboard draft instead of overwriting the existing one.

### Suggested Revision Policy
For durable concepts, revisions should create a new concept rather than overwrite the old one by default.

The new concept should link back to the old one using `comes from`.

## Search and Vetting Roles

Search and LLM vetting have different jobs:

- search is responsible for broad recall
- the vetting LLM is responsible for semantic relevance selection
- the assistant is responsible for answering well with bounded context
- the meta call is responsible for deciding graph changes

This division of labor is central to V5.

## UI Direction

The MVP UI should be chat-first and deliberately minimal:
- standard chat transcript
- message input
- the whiteboard only when the user asks for it or accepts an invite/draft flow
- a `Vantage` view for Working Memory, Learned items, the library, Reasoning Path, and internals
- a Working Memory view showing the bounded in-scope context behind the final answer, with Recall made explicit and whiteboard / recent-chat / pending-whiteboard grounding disclosed when they are the real source
- a learned view showing what Vantage created after the turn
- a library view for inspecting concepts, memories, artifacts, and reference notes

The user should not need to manage workspaces in order to chat.
Pending whiteboard offers should appear as chat-surface prompts rather than as always-on workspace UI.

Memory and structure should be inspectable, not mandatory.

The whiteboard should stay visibly separate from working memory and should only be brought forward when the user opts in.
Accepted whiteboard drafts should preserve that separation too: opening a new email, plan, or other work product should not silently replace an unrelated draft that was already on the whiteboard.
When the whiteboard is open, it should take visual priority: the draft should occupy the main canvas, chat should collapse into a smaller companion pane, and Working Memory / Learned / Library views should remain exclusive to `Vantage`.
Mode labels should stay explicit enough that the user always knows whether they are chatting, drafting, or inspecting internals.
See [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md) for the canonical definitions of `Working Memory`, `Whiteboard`, `Library`, `Learned`, and related terms.

For the proposed terminology reset around `Whiteboard`, `Memory Trace`, and `Working Memory`, see [docs/working-memory-and-trace-model.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/working-memory-and-trace-model.md).

When the UI shows working state, it should stay visibly split into:
- `Whiteboard` for the active shared workspace
- `Working Memory` for the bounded in-scope context behind the final answer, with `Recall` made explicit and non-retrieval grounding sources such as whiteboard or recent chat clearly labeled
- `Learned` for concepts, memories, or artifacts created after the answer
- `Library` for the durable stores behind the system

Inside the library, memory should stay visibly split into:
- the concept KB
- durable memories
- durable artifacts
- read-only reference notes

Selection in the library should stay separate from next-turn context.
Selecting something opens it for inspection.
Pinning it makes it persistent context for future turns until the user clears it.

Responses should also disclose their grounding mode:
- `Grounded` when relevant context materially informed the final answer, with the finer path surfaced as working memory, whiteboard, recent chat, pending whiteboard, or mixed context
- `Best Guess` when no relevant grounded context supported the turn

The visible best-guess disclosure should be honest and plain:

`This is new to me, but my best guess is:`

### Suggested User Controls
Useful first controls for the MVP:
- `next turn: remember`
- `next turn: don't save`
- `open related now`
- `pin selected context`
- `save whiteboard as artifact`
- `open Vantage view`
- natural-language `open whiteboard` / `draft this in the whiteboard`

### Suggested Transparency Rule
The system should be visible but not noisy.

Good MVP behavior:
- show when a durable saved item is created
- show which memory items were retrieved when helpful
- allow the user to inspect memory/context
- do not expose every internal system call by default

## MVP Boundaries

V5 should start with:
- a simple chat UI
- a shared collaborative Markdown workspace
- persistent concept memory in Markdown
- mixed retrieval over concepts, memories, artifacts, and optional reference notes
- LLM vetting of relevant memory items
- bounded assistant context
- a graph-conditioned meta call
- concept creation for genuine novelty
- explicit promotion of workspace documents into saved artifacts
- open-into-workspace behavior for saved items

V5 should not start with:
- full graph visualization
- heavy workspace management UI
- transcript-first memory
- whole-graph context loading
- complex ontology or excessive link types

## Implementation Defaults

The following implementation defaults are locked in for the V5 MVP.

### Product Scope
The V5 MVP is explicitly:
- single-user
- local-first

This keeps the system aligned with Markdown-backed personal/project memory and avoids premature multi-user complexity.

### Model Roles
For the MVP, chat, vetting, and meta calls should use the same default model family unless a strong reason emerges to split them later.

### Context Budget
The V5 MVP should use a hard bounded context policy:
- up to 5 vetted memory items
- last 6 chat turns
- one relevant workspace excerpt, capped to a bounded size

This budget should be treated as a real system rule, not just a guideline.

### Filesystem Layout
Use a simple local filesystem structure:

- `concepts/`
- `memories/`
- `memory_trace/`
- `artifacts/`
- `workspaces/`
- `state/`
- `traces/`
- `prompts/`

Recommended roles:
- `concepts/` stores durable Markdown concepts
- `memories/` stores durable retained user, project, and session facts
- `memory_trace/` stores first-class Markdown Memory Trace records for recent-turn recall
- `artifacts/` stores durable concrete outputs and workspace snapshots
- `workspaces/` stores shared collaborative Markdown documents
- `state/` stores index data, embeddings, metadata, and active UI state
- `traces/` stores debug traces for search, vetting, meta decisions, and writes
- `prompts/` stores the prompt templates and schemas used by the system

### Concept File Naming
Concept files should use slug-based filenames with stable ids in frontmatter.

Example:
- filename: `thanksgiving-dinner-plan.md`
- id: `thanksgiving-dinner-plan`

Revisions should create new files rather than overwrite existing ones.

Suggested revision naming:
- `thanksgiving-dinner-plan--v2.md`
- or timestamp/version-suffixed equivalents

### Concept Frontmatter Schema
The MVP base schema for concepts should be:

- `id`
- `title`
- `type`
- `card`
- `created_at`
- `updated_at`
- `links_to`
- `comes_from`
- `status`

Optional later additions may include:
- `source_workspace`
- `tags`
- `revision_of`

### Workspace Model
There may be multiple named workspace documents in `workspaces/`, but only one should be actively open in the UI at a time.

Chat should still function even when no workspace is open.

### Search Index Strategy
For the MVP, search should start with:
- keyword search over title
- keyword search over concept card
- body fallback
- embeddings as an optional second layer

The MVP should not block on a full embedding-only retrieval pipeline.

### Assistant Edit Protocol
The assistant should not silently rewrite shared workspace files in ordinary conversational turns.

For the MVP, it should produce structured edit proposals such as:
- replace section
- append block
- rewrite full document when explicitly chosen

Patch-style or block-style edits are preferred over arbitrary raw rewrites.

Whiteboard-first drafting is an intentional exception for structured working outputs. In those cases the assistant may return a pending whiteboard offer or draft. The system should not silently apply that proposal to the workspace file itself, but once a concrete draft iteration exists it should automatically capture a durable artifact snapshot so the iteration history is preserved.

### Meta Call Executor
The LLM should never directly mutate files.

It should return structured actions, and a strict executor layer should validate and apply them.

### Frontend / Backend Boundary
The MVP should use a simple local web app first.

Recommended API shape:
- `POST /api/chat`
- `GET /api/workspace`
- `POST /api/workspace`
- `POST /api/workspace/open`
- `GET /api/concepts/search`
- `GET /api/memory`
- `GET /api/memory/search`
- `POST /api/concepts/promote`
- `POST /api/concepts/open`

`POST /api/chat` should carry the full turn contract used by the current UI:
- `message` and bounded `history`
- `workspace_id` plus transient `workspace_content` so the assistant can see the live unsaved whiteboard buffer without silently persisting it
- `whiteboard_mode` so the composer can stay on `auto` or explicitly invite whiteboard collaboration
- `selected_record_id` for selected-item continuity, decided separately from pinning or opening
- `memory_intent` for next-turn remember / do-not-save hints

The response should keep the UI honest and inspectable:
- `assistant_message`
- bounded candidate and selected memory payloads
- canonical `recall` for the narrower recall-shaped subset used in the final answer, plus legacy `working_memory` as a compatibility alias rather than the whole product meaning of Working Memory
- `learned` for concepts, memories, or artifacts created after the answer
- `response_mode` so the UI can distinguish `Grounded` from `Best Guess`, surface the truthful grounding path, and report canonical `recall_count` plus canonical context sources alongside legacy aliases
- `turn_interpretation` so the UI can show why Vantage chose chat, Scenario Lab, a whiteboard invitation, or selected-context continuity
- `workspace_update` for pending whiteboard offers or drafts that have not yet been applied, including offer context that can carry into the next turn so a semantic “yes / continue” can start the draft instead of repeating the invitation
- `scenario_lab` for Scenario Lab turns, plus `scenario_lab_error` when Scenario Lab was selected but fell back to normal chat

#### C3 Contract Snapshot
Wave 3 C3 hardens the whiteboard in-scope contract without changing the chat-first product shape.

Canonical request fields:
- `message`
- `history`
- `workspace_id`
- `workspace_scope`
- `workspace_content`
- `whiteboard_mode`
- `selected_record_id`
- `memory_intent`
- `pending_workspace_update`

`workspace_scope` meanings:
- `auto`: the server decides whether the whiteboard is in scope
- `excluded`: the whiteboard is out of scope for that turn
- `visible`: the active whiteboard is in scope because it is open
- `pinned`: the selected item is kept active by explicit pinning
- `requested`: the user explicitly asked to open or draft in the whiteboard

Canonical response fields:
- `assistant_message`
- `recall`
- `working_memory` as a compatibility alias
- `learned`
- `created_record` as a compatibility alias derived from `learned[0]` while the UI still bridges older paths
- `response_mode`
- `turn_interpretation`
- `workspace_update`
- `scenario_lab`
- `scenario_lab_error`
- `graph_action`
- `selected_record`
- `selected_record_id`
- `workspace.context_scope` as the returned scope disclosure that tells the UI what was actually in scope
- `workspace.scenario_kind` plus nested `workspace.scenario`, and `selected_record.scenario_kind` plus nested `selected_record.scenario`, whenever the active workspace or selected saved item is part of a durable Scenario Lab branch or comparison

### C3 Alias Inventory
| Canonical field | Current legacy alias(es) | Current producer / consumer | Removal condition |
| --- | --- | --- | --- |
| `learned` | `created_record` | Server emits both; the webapp prefers `learned` and falls back to `created_record` for compatibility. | Remove the alias once the webapp no longer needs the fallback and tests cover `learned` only. |
| `workspace_update.status` | `workspace_update.type` | Server and webapp normalize around `status`; the webapp still carries `type` through pending whiteboard context and older payloads. | Remove the alias once pending-workspace flows only use `status` end to end. |
| `selected_record_id` | none | The webapp sends `selected_record_id`; the server consumes it for selected-item continuity. | Keep this row as documentation only; there is no active request alias to remove. |
| `record_id` | `concept_id` | `POST /api/concepts/open` accepts both; the server resolves either one for opening a saved item into the workspace. | Remove `concept_id` once every caller uses `record_id`. |

In the current architecture, `whiteboard_mode` from the UI is a user preference, not the whole routing decision.
The navigator interprets the turn semantically and can return continuity and whiteboard hints for auto-mode turns before the normal chat reply is generated.
Pending whiteboard carry-over should be treated as explicit context too: if it is forwarded into a turn, the response explanation surface should disclose that fact rather than presenting the answer as an ungrounded best guess.
When pending whiteboard context crosses the wire, the backend treats `workspace_update.status` as canonical but still backfills `type` and `status` from each other as a thin compatibility bridge so older pending payloads do not silently drop out of scope.

### Save Semantics
For the MVP:
- concepts created by the meta call may be written immediately
- memories may be written immediately when the user explicitly asks to remember or save a durable fact
- workspace promotion should usually be explicit or clearly surfaced
- explicit workspace promotion should normally create an artifact rather than a concept copy
- transient whiteboard content included with `POST /api/chat` should remain transient unless the user separately saves the whiteboard
- whiteboard content should only count as model context when it is intentionally in scope
  that means the whiteboard is open, explicitly requested, or later pinned for chat continuity
- the UI should visibly confirm when something has been saved

### Workspace Promotion UX
The normal workspace flow should be explicit promotion.

Recommended MVP behavior:
- the assistant can suggest `Save workspace as artifact`
- the assistant can optionally suggest `Derive concept from workspace` when the goal is timeless knowledge rather than a snapshot
- the user confirms promotion
- strong novelty may still create concepts automatically in the background when appropriate

### Saved-Item Opening Behavior
Saved items should be openable into the shared workspace.

This includes concepts, memories, and artifacts through the same saved-item opening path.
Read-only vault notes can remain inspectable without being treated as editable saved items.

Scenario Lab branch workspaces should reopen through a dedicated workspace route rather than the saved-item opening path.
That keeps branch activation separate from promoting a concept, memory, or artifact into the active editor.
That workspace route should return stable branch scenario metadata from the workspace store so reopened branches stay legible even when the whiteboard content is hidden for the current turn.
Scenario Lab comparison artifacts should still behave like ordinary saved artifacts and carry a stable `scenario_comparison` marker plus durable branch metadata so follow-up turns can preserve continuity without relying on heading text.

### Failure Behavior
If search, vetting, meta, or write steps fail:
- the assistant should still answer the user
- memory actions for that turn may be skipped
- the failure should be recorded in traces

Chat quality should not depend on every memory subsystem succeeding.

### Tracing
The system should trace every turn with at least:
- search candidates
- vetted memory items
- items sent to assistant context
- meta call output
- executed graph action

Tracing is required for debugging and evaluation.

### Prompt Contracts
The system should define structured schemas for:
- vetting call
- meta call
- edit proposal call

These schemas should stay compact and explicit.

### Starter Data
The MVP should ship with:
- a few seed concepts
- one sample workspace document
- one simple trace example
- one end-to-end sample scenario

This should make the system immediately testable in local development.

### Deletion / Archive Policy
The MVP should not hard-delete concepts.

If removal is needed, use archive behavior rather than permanent deletion.

### Search Result Format
Each search result should expose:
- title
- card
- type
- source
- trust
- score
- optional path or relation hint

### Evaluation Scenarios
The MVP should be tested against a fixed set of scenarios such as:
- casual chat
- topic shift
- new durable fact
- draft in workspace
- promote workspace to artifact
- derive concept from workspace
- revise concept
- retrieve an old concept later

### Build Sequence
Recommended implementation order:

1. simple chat UI
2. shared workspace UI
3. concept file schema
4. search
5. vetting call
6. assistant context assembly
7. meta call
8. concept creation, memory creation, and workspace promotion
9. traces
10. polish and evaluation

## Summary

The V5 architecture can be summarized like this:

- chat is primary
- chat is the default visible surface
- the client should model surfaces explicitly as `chat`, `whiteboard`, or `Vantage` rather than through interacting booleans
- the `Vantage` view is the deliberate place to inspect Working Memory, learned items, the library, and internals
- the whiteboard is an on-demand collaborative drafting surface and is distinct from working memory
- hidden whiteboards should not silently ground ordinary chat turns
- concrete work products can trigger an invitation to collaborate in the whiteboard, but the invitation should stay in chat until accepted
- library selection is for inspection, while pinned context is the explicit way to keep an item active across turns
- concepts, memories, and artifacts live as Markdown files
- concepts have one-sentence concept cards
- search retrieves mixed candidate memory from concepts, memories, artifacts, and optional reference notes
- an LLM vets which memory items are relevant
- only vetted memory items enter assistant context
- the navigator interprets turns semantically before chat executes them
- the navigator can route comparative what-if turns into Scenario Lab
- the navigator can preserve selected context for continuity and steer auto-mode whiteboard collaboration
- Scenario Lab writes branch workspaces plus a comparison artifact
- a graph-conditioned meta call decides what to do with each interaction
- timeless knowledge can become a concept
- remembered continuity can become a memory
- workspace outputs can become artifacts

This is the current Vantage V5 foundation.

For a grounded comparison between the current repository and the stricter historical canon, see [docs/implementation-vs-canon.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/implementation-vs-canon.md).

## Current Demo

The current local demo includes:
- chat-first web UI
- deliberate `Vantage` view for Working Memory, learned items, the library, and internals
- on-demand shared Markdown whiteboard with load/save
- natural-language whiteboard requests plus model-driven whiteboard routing for draft-oriented turns
- whiteboard-focused drafting mode with a compact companion chat sidebar
- ask-first whiteboard collaboration for emails, plans, itineraries, lists, essays, papers, code, and other work products
- pending whiteboard offers and pending whiteboard drafts surfaced in chat, with pending offers carrying enough context for a later acceptance turn or whiteboard-accept action to start the draft
- explicit whiteboard context scoping on chat requests, so the assistant only sees the live whiteboard when it is intentionally in play
- chat-time syncing of the current whiteboard buffer so the assistant sees the live draft, not just the last saved file, without silently persisting that buffer
- local whiteboard continuity for unsaved drafts, so passive runtime refreshes do not replace a dirty whiteboard with the last saved workspace
- concept search over the concept KB
- chat-time mixed retrieval over concepts, memories, artifacts, and optional vault notes
- a `Working Memory` view showing the bounded in-scope context behind the final answer, with `Recall` surfaced explicitly
- a compact `Turn interpretation` view explaining why Vantage chose chat, Scenario Lab, or a whiteboard path for the turn
- a `Learned` view for records created after the answer
- a `Library` view split into `Concept KB`, `Memories`, `Artifacts`, and `Reference Notes`
- a `Pinned Context` bar where selection stays inspect-only and pinning keeps an item active until cleared
- response-mode disclosure as `Grounded` or `Best Guess`
- explicit `workspace_update` signals for whiteboard offers and pending drafts during normal chat
- navigator-first Scenario Lab for comparative what-if turns
- navigator-driven auto-mode whiteboard invitations and selected-context continuity hints
- branch workspaces that reopen through `/api/workspace/open`
- reopened branch workspaces and selected comparison artifacts that expose stable scenario metadata, including namespace and branch workspace ids
- comparison artifacts marked as `scenario_comparison` so follow-up turns can stay anchored to the saved comparison
- separate durable stores for memories and artifacts
- vetting of relevant memory items before they enter assistant context
- a graph-conditioned meta call after each turn
- conservative concept and memory creation for explicit durable turns
- explicit workspace promotion into saved artifacts
- saved-item inspection and open-into-workspace flow for concepts, memories, and artifacts
- explicit Scenario Lab fallback payloads so the UI can explain when routing chose Scenario Lab but chat had to answer instead
- traces for turn-level retrieval and graph actions

## Repo Hygiene

The repo keeps mirrored code summaries under `docs/codebase/` so future agents can build context before editing:

- `docs/codebase/python/` for backend, storage, Python tests, and Python tooling
- `docs/codebase/webapp/` for the frontend shell, state helpers, and browser-facing tests

When source/test layout changes, or when you want a quick structural check that summaries did not drift, run:

```bash
python3 scripts/check_repo_hygiene.py
```

## Run Locally

To run the current V5 demo locally:

```bash
cd "/Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5"
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
vantage-v5-web
```

Then open [http://127.0.0.1:8005](http://127.0.0.1:8005).

If `OPENAI_API_KEY` is present in `.env`, chat runs through OpenAI.
If not, the app falls back to a local placeholder chat response so the UI and workspace flow still work.

## Milestones

- [milestone_1.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/milestone_1.md)
- [milestone_2.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/milestone_2.md)
- [milestone_3.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/milestone_3.md)

## Integration Docs

- [nexus_integration.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/nexus_integration.md)
