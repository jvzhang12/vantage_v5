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

Whiteboard:
    live collaborative Markdown draft
    may enter Working Memory only when intentionally in scope

PinnedContext:
    explicit carry-forward context
    persists until cleared
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
    return NeedsClarification
```

## Safety Projection

Memory Trace and source-turn-derived rows require projection before they appear in public payloads, safe diagnostics, or model-input paths not designed for raw trace bodies.

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
    may receive selected bounded context
    must not receive unsafe trace content through bypass paths
```

## Compatibility Names

Some current payloads and storage paths use old names:

- `workspace_*` for Whiteboard implementation/storage compatibility
- top-level `working_memory` as a compatibility alias for narrower Recall-like data
- `selected_record*` aliases beside pinned context
- `created_record` beside richer learned/record-card outputs

Future code should not infer product intent from those names alone. Check the compatibility ledger before changing them.
