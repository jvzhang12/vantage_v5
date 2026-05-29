# 04. Attention, Recall, And Working Memory

> Status: Current source of truth
> Note: This file states the intended relationship among Attention, Recall, and Working Memory. It should guide future cutovers without changing current behavior by itself.

## Definitions

```text
Attention = broad turn resource and surface selection
Recall = memory-grounding role/view over selected resources
Working Memory = full bounded context sent to the response model
```

Attention can include resources that are not Recall:

- visible or open surfaces
- surface actions
- pinned continuity context
- protocols
- app resources such as calendar/task candidates
- Library records
- Memory Trace records

Recall is narrower:

- Memory Trace selected for grounding
- Concepts selected for reasoning substrate
- Memories selected for continuity
- Artifacts selected for concrete saved work
- Reference notes selected as read-only material

Working Memory is broader than top-level API `recall`:

- current user message
- bounded recent chat
- recalled items
- pinned context
- Whiteboard context when in scope
- pending draft/offer context when intentionally carried
- protocol guidance when applied

## Desired Selection Model

```text
function build_working_memory(turn):
    attention = select_broad_resources(turn)
    recall = select_memory_grounding(attention, turn)
    handoff = group_by_role(attention, recall)

    return bounded_context(
        user_message=turn.message,
        recent_chat=bounded_recent_chat(turn),
        answer_context=handoff.answer_context,
        recall_context=handoff.recall_context,
        protocol_guidance=handoff.protocol_guidance,
        pinned_or_continuity_context=handoff.pinned_or_continuity_context,
        whiteboard_context=intentional_whiteboard_context(turn),
    )
```

## Role Projection

```text
answer_context:
    resources directly useful for answering

recall_context:
    Memory Trace or Library records used as grounding

protocol_guidance:
    task recipe or policy guidance

surface_to_open:
    resources that should be shown or opened, not necessarily grounded

pinned_or_continuity_context:
    explicit carry-forward or compact continuity frame resources
```

The same resource can be relevant in more than one conceptual way, but public projection should keep labels clear and compact.

## Handoff Requirements

```text
handoff must:
    be bounded
    preserve source kind and role
    preserve safe provenance
    project Memory Trace safely
    support generation context
    support public working_memory_view
    support trace-safe diagnostics
```

Handoff should not:

- pass full Memory Trace bodies to public payloads
- expose prompt-derived trace ids publicly
- use different safety rules for generation and public views
- invent semantic relevance deterministically
- silently drop valid non-trace records because their ids resemble trace ids

## Memory Trace Equivalence

Memory Trace records may have different aliases in different transitional paths.

```text
safe_equivalence(memory_trace_item):
    compare by safe class:
        source kind is Memory Trace
        bounded safe summary/category
        selected role
        non-sensitive position if needed
    do not compare by raw prompt-derived storage id
    do not require display aliases to match exactly
```

This avoids false mismatches while keeping prompt-derived ids out of public diagnostics.

## Current Implementation May Differ

Known transitional seams can remain until reviewed:

- legacy search/retrieval paths may still supply candidates
- handoff parity diagnostics may compare new and old shapes
- API `working_memory` may still alias narrower Recall-shaped data
- deterministic fallback may supply conservative selections when model output fails

Future cleanup should shrink these seams only with tests and smokes that prove behavior is preserved or intentionally changed.
