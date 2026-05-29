# 03. Turn Lifecycle

> Status: Current source of truth
> Note: This describes the intended processing model. Current modules may split or bridge these steps differently during migration.

## High-Level Flow

```text
function handle_chat_turn(request):
    prepared = prepare_turn_context(request)
    navigation = interpret_user_intent(prepared)
    protocols = resolve_protocol_guidance(navigation, prepared)
    attention = select_attention_resources(prepared, navigation, protocols)
    recall = retrieve_and_vet_recall(attention, prepared)
    handoff = build_attention_recall_handoff(attention, recall, protocols, prepared)
    turn_plan = compute_turn_authority(navigation, prepared, handoff)
    response = generate_or_route_response(prepared, handoff, turn_plan)
    effects = execute_authorized_effects(response, turn_plan, prepared)
    trace = record_memory_trace(prepared, response, handoff, effects)
    payload = build_public_payload(response, handoff, turn_plan, effects, trace)
    return payload
```

## Step 1: Prepare Context

```text
prepare_turn_context(request):
    load durable or experiment runtime
    load current Whiteboard state if present
    apply visible surface scope rules
    load pinned context
    load pending Whiteboard draft/offer context only when intentionally carried
    build compact continuity frame for Navigator
```

Preparation should not perform writes.

## Step 2: Interpret Intent

```text
interpret_user_intent(prepared):
    decision = NavigatorLLM(prepared.message, compact_state)
    if decision invalid:
        decision = narrow_labeled_fallback(prepared)
    return structured actions and route hints
```

The Navigator/control panel is the semantic intent seam. Deterministic code validates the result; it should not become the broad semantic interpreter.

## Step 3: Resolve Protocols

```text
resolve_protocol_guidance(navigation, prepared):
    if navigation requests apply_protocol:
        validate supported protocol kind
        choose user/session override before canonical default before builtin
        return protocol guidance candidate
    else:
        return no protocol guidance
```

Protocols guide task performance. They are not factual evidence.

## Step 4: Select Attention

```text
select_attention_resources(prepared, navigation, protocols):
    resources = visible surfaces + pinned context + app resources + retrieval candidates + protocol guidance
    selected = LLM_or_structured_selection(resources, prepared.message)
    if selected invalid:
        selected = narrow conservative fallback(resources)
    return bounded selected resources
```

Attention is broader than Recall. It includes things that may open surfaces, guide the answer, or shape continuity.

## Step 5: Recall And Vet

```text
retrieve_and_vet_recall(attention, prepared):
    pool = bounded_search(Memory Trace + Concepts + Memories + Artifacts + Reference Notes)
    pool += protocol guidance when structurally applied
    vetted = LLM_vet(pool, prepared.message, attention)
    return bounded vetted memory-grounding subset
```

Recall does not invent relevance deterministically. Deterministic code can bound, normalize, filter hidden records, and serialize.

## Step 6: Build Handoff

```text
build_attention_recall_handoff(...):
    group resources by role:
        answer_context
        recall_context
        protocol_guidance
        surface_to_open
        pinned_or_continuity_context
    project trace-derived resources into safe aliases/summaries
    preserve enough provenance for inspection and parity diagnostics
```

The handoff should be the shared source for generation context, role projection, and safe Working Memory views.

## Step 7: Compute Turn Authority

```text
compute_turn_authority(navigation, prepared, handoff):
    deny writes for hard no-write turns
    allow drafts only with structured draft/Whiteboard authority
    allow durable writes only with explicit intent and safe candidates
    keep calendar/task proposals confirmation-gated
    produce receipts for allow/deny decisions
```

Authority is separate from generation. A good response can be generated without a write being authorized.

## Step 8: Generate Or Route

```text
generate_or_route_response(prepared, handoff, turn_plan):
    if route is Scenario Lab:
        run Scenario Lab with explicit protocol and output expectations
    else:
        model_input = build_generation_context(prepared, handoff, turn_plan)
        assert model_input is bounded and safe
        return ResponseLLM(model_input)
```

Generation should consume handoff-derived context where possible. Legacy retrieval/search can remain as a source or diagnostic seam until retired.

## Step 9: Execute Effects

```text
execute_authorized_effects(response, turn_plan, prepared):
    if turn_plan authorizes no writes:
        execute no writes
    if draft authorized:
        create pending draft or offer, not durable save
    if durable save authorized:
        write through existing storage service
    if calendar/task action proposed:
        return proposal with requires_confirmation=true
```

Execution must not recompute broad semantic authority from raw text.

## Step 10: Trace And Public Payload

```text
record_memory_trace(...):
    save internal recent-history record
    include enough structure for future recall

build_public_payload(...):
    include answer, safe working_memory_view, learned/saved outcomes, surface actions, trace-safe diagnostics
    preserve compatibility aliases where required
    project or remove unsafe Memory Trace bodies and prompt-derived ids
```

Public payloads are not internal traces. They are bounded user-visible state.
