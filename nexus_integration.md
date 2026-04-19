# Vantage V5 Nexus Integration

## Goal

Connect the wider Nexus Obsidian vault to Vantage without breaking the V5 product principles.

The core rule is:

`The full Nexus vault should be a searchable library, not raw always-on assistant context.`

Vantage concepts remain the assistant's durable memory layer.
Nexus notes remain a broader read-only reference corpus.

## Core Architecture

The system should operate across three distinct context layers:

### 1. Active Context

This is the context directly used for the current turn:
- current user message
- recent chat turns
- active shared workspace
- up to 5 vetted relevant items

This is the only context that enters the assistant call.

### 2. Vantage Memory

This is the durable Vantage concept graph:
- Markdown concepts created or revised by Vantage
- concept cards used for retrieval and routing
- high-trust memory layer
- writable by the Vantage executor

This is what the assistant should rely on most strongly over time.

### 3. Nexus Corpus

This is the wider Obsidian vault:
- project docs
- architecture notes
- decision logs
- product notes
- selected preference or reference notes

This layer is:
- searchable
- read-only by default
- not fully trusted
- not directly injected wholesale into assistant context

## Key Principle

The Nexus vault is not the assistant's memory.

It is the assistant's library.

That means:
- Nexus notes can inform answers
- Nexus notes can provide source material
- Nexus notes can inspire or justify new concepts
- Nexus notes should not automatically become trusted durable memory

## Retrieval Model

For each user turn, the system should search both:

1. `Vantage concepts`
2. `Allowed Nexus notes`

Then:
- retrieve top candidates from each source
- run a vetting call over the merged candidate set
- select only the best few items
- pass only those vetted items into the assistant

This preserves boundedness while allowing the wider vault to help.

## Suggested Retrieval Pipeline

1. user sends a message
2. search Vantage concepts
3. search allowed Nexus notes
4. merge candidate sets
5. run vetting call with source labels
6. select up to 5 relevant items
7. send only selected items into assistant context
8. assistant answers
9. run the meta call
10. write only to the Vantage graph unless the user explicitly requests something else

## Trust Classes

Every retrieved item should carry an explicit trust class:

- `concept`
  Vantage durable memory, high trust
- `workspace`
  active draft or collaborative document, medium trust
- `vault_note`
  Nexus reference note, medium or low trust depending on freshness and source
- `archive`
  older reference material, low trust unless explicitly requested

The assistant prompt should mention these trust classes so the model does not flatten all sources into the same certainty level.

## Indexing Strategy

For the Nexus vault, index lightweight note representations first.

Suggested indexed fields:
- note path
- title
- aliases
- tags
- one-sentence note card
- short body excerpt
- modified time
- folder
- optional embeddings

The assistant should not receive full raw note bodies by default.
Full note bodies should be loaded only when the selected item needs deeper inspection.

## Allowed vs Excluded Scope

The first Nexus integration should be explicit and conservative.

### Good First Allowlist

- project hubs
- decision logs
- architecture docs
- product specs
- workflow docs
- explicitly allowed preference notes

### Good First Exclusions

- daily notes
- journal or private personal notes
- inbox capture folders
- scratch notes
- templates
- attachments
- obsolete archive folders
- large unstructured reference dumps

## Safety Rules

The Nexus integration should start with these safeguards:

1. read-only vault access
2. folder allowlist
3. explicit excluded folders
4. source provenance retained for every retrieved note
5. note freshness metadata surfaced
6. visible "used sources" or "used notes" UI
7. no automatic writeback into Nexus
8. local-only indexing by default

## Meta Call Behavior With Nexus

The meta call should be allowed to reason over Nexus-derived information, but the executor should still write only to Vantage memory by default.

That means the meta call may decide:
- `no_op`
- `create_concept`
- `create_revision`
- `create_link`
- `attach_to_existing_concept`
- `promote_workspace_to_concept`

If a Nexus note is important, the meta call should usually:
- create or revise a Vantage concept derived from that note
- link the concept back to the note path or source metadata

The system should not silently rewrite Nexus notes.

## Source Provenance

When Nexus notes influence a turn, the system should preserve provenance:

- note title
- note path
- folder
- modified time
- short excerpt used

This provenance should be available in traces and optionally visible in the UI.

## UI Recommendations

The UI should keep Vantage memory and Nexus references visually separate.

Recommended behavior:
- `Concept KB` panel for durable Vantage concepts
- `Saved Notes` panel for durable Vantage memories and artifacts
- `Reference Notes` panel for Nexus retrieval results
- source labels on every result card
- small "used this turn" indicators
- visible note/concept inspector

The system should feel like it is consulting a library, not dumping the whole vault into the conversation.

## Recommended Write Policy

For the first Nexus integration:

- Vantage may read from Nexus
- Vantage may quote or summarize Nexus notes in bounded ways
- Vantage may create Vantage concepts derived from Nexus material
- Vantage should not write back into Nexus
- Vantage should not promote every relevant Nexus note into concept memory automatically

## Build Sequence

Recommended implementation order:

1. add allowlist and exclusion config for Nexus folders
2. build a read-only Nexus indexer
3. expose a `vault_note` search path alongside concept search
4. merge concept and Nexus candidates into one vetting input
5. add source labels and trust classes to vetting and chat prompts
6. add UI surfaces for `Concepts` and `Vault Notes`
7. add provenance traces
8. add optional "promote this Nexus note into a Vantage concept"

## Success Criteria

The Nexus integration is successful if:

1. the assistant still feels like a normal chat assistant
2. the entire vault is never injected wholesale into model context
3. only a bounded vetted subset enters assistant context
4. Vantage concepts remain the durable memory layer
5. Nexus notes remain read-only reference material
6. the user can see when a Nexus note influenced a response
7. the system becomes more useful without becoming noisier or less trustworthy

## Bottom Line

The right framing is:

`Nexus is the library.`
`Vantage is the memory.`

That preserves V5's chat-first design while letting the wider vault make the system dramatically more useful.
