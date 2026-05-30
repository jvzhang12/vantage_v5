# 02. Information Model

> Status: Current source of truth
> Note: This is intended information design. Concrete schemas may still carry compatibility names such as `workspace_*` or top-level `working_memory`.

## Core Objects

```text
UserMessage:
    text
    attachments or visible context references
    composer mode and control hints

RecentChat:
    bounded prior conversational turns
    not a durable memory store

MemoryTrace:
    automatic recent-history record
    searchable by Recall
    not public as raw body/content

Concept:
    timeless reusable reasoning knowledge
    title, card, body, links, metadata

Memory:
    retained continuity fact about user, project, or session
    compact enough for future grounding

Artifact:
    concrete output, saved draft, plan, comparison, or Whiteboard snapshot

Protocol:
    reusable task guidance
    guidance, not factual evidence

ReferenceNote:
    read-only or import-only reference material
    not a Memory, Concept, or Artifact unless explicitly converted with write authority

Whiteboard:
    live collaborative Markdown draft
    may enter Working Memory only when intentionally in scope

PinnedContext:
    explicit carry-forward context
    persists until cleared

PendingProposal:
    confirmation-gated mutation candidate
    has stable proposal identity, normalized arguments, source turn, expiry, and status
    not executed until an AcceptedProposal flow revalidates it
```

## Turn Context Roles

```text
AttentionResource:
    any resource or surface candidate relevant to this turn
    may include Library records, Memory Trace, visible surfaces, protocols, app resources

RecallCandidate:
    memory-grounding candidate drawn from selected Attention resources
    may enter generation after vetting and safe adaptation

WorkingMemory:
    exact bounded context sent to the response model
    includes current message and selected in-scope contributors

AttentionRecallContextHandoff:
    compact internal handoff grouping resources by role:
        answer_context
        recall_context
        protocol_guidance
        surface_to_open
        pinned_or_continuity_context
```

## Durable Type Boundaries

```text
function classify_saved_item(item):
    if item is timeless reasoning substrate:
        return Concept
    if item is continuity fact:
        return Memory
    if item is concrete output or snapshot:
        return Artifact
    if item is reusable process guidance:
        return Protocol
    if item is external/reference material:
        return ReferenceNote
    return NeedsClarification
```

## Reference Note Rule

Reference Notes are read-only by default.

```text
if user asks to use a Reference Note:
    treat it as recallable reference context

if user asks to import or save a Reference Note:
    require explicit import/write authority
    choose target type deliberately:
        keep as ReferenceNote for imported read-only source material
        convert to Concept only for timeless reasoning knowledge
        convert to Memory only for retained continuity facts
        convert to Artifact only for concrete outputs
```

Do not silently turn reference material into a memory, concept, or artifact merely because it was useful in a turn.

## Projection Tiers

Memory Trace and source-turn-derived rows require projection before they appear in public payloads, safe diagnostics, or model-input paths not designed for raw trace bodies.

```text
internal_storage:
    may keep raw and summarized records when policy allows
    may include full Memory Trace for recall/debug
    remains private and storage-scoped

generation_safe:
    may include selected bounded content needed for the answer
    may include fuller selected Artifact or Whiteboard excerpts within budget
    may include Memory Trace only as a bounded excerpt or summary appropriate for model input
    must exclude prompt-derived trace ids and unrelated raw trace bodies

public_safe:
    exposes compact aliases, titles, summaries, roles, provenance, receipts
    keeps working_memory_view compact even when generation_safe context is richer
    excludes raw prompts, raw assistant text, full trace bodies, and prompt-derived trace ids

diagnostic_safe:
    exposes bounded comparison metadata and safe ids
    may show mismatch/parity status
    excludes raw trace bodies and prompt-derived ids
```

Shared invariants:

```text
every tier must:
    preserve source kind and role
    avoid hidden chain-of-thought
    avoid prompt-derived public ids
    avoid unrelated or unbounded context
```

Public projection:

```text
function public_project(resource):
    if resource derives from Memory Trace or source-turn body:
        return {
            id: safe_alias(resource),              # current-turn or memory_trace:prior-turn-N
            resource_id: safe_alias(resource),
            title: "Prior turn trace",
            label: "Prior turn trace",
            summary: "Prior turn context selected by Recall.",
            body: absent,
            content: absent,
            raw_prompt_text: absent,
            raw_assistant_text: absent,
            prompt_derived_ids: absent,
        }

    if resource has a prompt-derived id only because it is trace-derived:
        replace with safe alias

    return preserve_useful_non_trace_fields(resource)
```

Prompt-derived ids are unsafe in public context when they identify Memory Trace/source-turn records. Natural non-trace slugs that happen to begin with similar words must not be reclassified as trace records without source evidence.

## Public vs Internal Data

```text
internal_storage:
    may keep full Memory Trace records for recall and debugging
    must stay out of public payloads unless projected

public_payload:
    may expose bounded summaries, aliases, roles, provenance, receipts
    must not expose raw trace bodies, raw prompts, assistant text, or prompt-derived trace ids

model_input:
    may receive selected bounded generation_safe context
    may be richer than public working_memory_view
    must not receive unsafe trace content through bypass paths
```

## Memory Trace Retention And Privacy

Memory Trace is automatic, but automatic does not mean unlimited or always recallable.

```text
when recording Memory Trace:
    store enough structure for continuity, recall, and audit
    prefer summarized or excerpted recall text for future model input
    keep raw turn text private to internal storage when retained
    suppress or redact obvious secrets, credentials, and user-declared sensitive content
    mark non-recallable when the user explicitly says not to remember or asks to forget that trace
```

Retention policy:

- Raw vs summarized trace: intended model input should use summaries or bounded excerpts; raw bodies are internal storage only unless a future policy explicitly permits more.
- Retention horizon: unresolved product decision. Until a horizon is chosen, treat Memory Trace as privacy-sensitive local recent history with suppression and eventual-retention hooks.
- Sensitive content: explicit secrets, credentials, private identifiers, or user-declared "do not remember" material should be suppressed from recall and public diagnostics.
- Forget/correction effects: saved-item `mark_incorrect` and `forget` suppress Library records from recall. For Memory Trace, the intended equivalent is a non-recallable/suppressed trace state; exact hard deletion vs suppression is unresolved.
- Assistant text: prior assistant text is continuity evidence about what Vantage said or did. It is not automatically factual evidence about the world unless backed by recalled Library/reference material or current reasoning.

## Compatibility Names

Some current payloads and storage paths use old names:

- `workspace_*` for Whiteboard implementation/storage compatibility
- top-level `working_memory` as a compatibility alias for narrower Recall-like data
- `selected_record*` aliases beside pinned context
- `created_record` beside richer learned/record-card outputs

Future code should not infer product intent from those names alone. Check the compatibility ledger before changing them.
