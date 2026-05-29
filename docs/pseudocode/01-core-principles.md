# 01. Core Principles

> Status: Current source of truth
> Note: These are intended rules for future implementation. Current compatibility fields and transitional fallbacks may remain until retired through reviewed slices.

## Principle 1: Chat First

```text
if the user's request can be answered naturally in chat:
    keep the turn in chat
    do not force a surface transition
    do not expose internal architecture unless it helps the user
```

Chat-first does not mean memory-free. It means memory and surfaces should support conversation without making conversation feel procedural.

## Principle 2: Bounded Context

```text
all_context = current message + recent chat + Memory Trace + Library + Whiteboard + pinned context
working_memory = select_relevant_subset(all_context)

assert working_memory is bounded
assert working_memory is inspectable
assert working_memory contains no raw private trace body unless explicitly allowed for internal-only use
```

Vantage should never pass the whole graph, whole transcript, or whole trace store into generation.

## Principle 3: Durable Types Stay Distinct

```text
if saved_item is timeless reusable knowledge:
    store as Concept
elif saved_item is retained continuity fact:
    store as Memory
elif saved_item is concrete output or snapshot:
    store as Artifact
else:
    ask, propose, or keep pending
```

Do not collapse everything into "memory." Type clarity is part of the product.

## Principle 4: Open, Pinned, And In Scope Are Different

```text
visible_item = user is looking at item
pinned_item = user explicitly wants item carried forward
in_scope_item = item may influence this turn's answer

if item is visible but not pinned and not referenced:
    do not automatically include it in Working Memory
```

Inspection is not carry-forward. Pinning is the explicit continuity mechanism.

## Principle 5: LLM Interprets, Deterministic Code Guards

```text
semantic_decision = Navigator_or_model_interpreter(message, compact_state)
validated_plan = deterministic_validation(semantic_decision, runtime_state)

if semantic_decision is missing or invalid:
    use only narrow fallback
    label fallback source
    avoid broad raw-text routing
```

Deterministic fallback is a guardrail, not the primary intelligence.

Allowed deterministic work:

- schema validation
- safety blocking
- bounded projection
- compatibility translation
- persistence execution after authority
- narrow provider-failure fallback

Not allowed as the primary product path:

- broad semantic routing by keyword
- inferred write intent from raw text when structured intent is absent
- hidden relevance invention

## Principle 6: Public Safety By Projection

```text
public_payload = project_safe(internal_state)

remove raw prompts
remove raw assistant text from trace-derived records
remove prompt-derived ids
remove full Memory Trace bodies
keep bounded aliases, summaries, provenance, and receipts
```

Internal trace/storage can retain richer data when appropriate. Public payloads and safe diagnostics must not leak it.

## Principle 7: Experiment Mode Is Bounded

```text
if experiment_mode:
    writable_store = session_local_store
    durable_store = read_only_reference
    promotion_to_durable requires explicit user action
```

Temporary learning should not pollute durable memory.

## Principle 8: Receipts Must Be Honest

```text
if answer used recalled Library or Memory Trace:
    receipt may say Recall grounded it
elif answer used Whiteboard:
    receipt should name Whiteboard context
elif answer used only current message or recent chat:
    receipt should not pretend durable memory was used
else:
    use honest best-guess disclosure when needed
```

Receipts are product trust, not decoration.
