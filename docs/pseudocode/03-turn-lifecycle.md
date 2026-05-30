# 03. Turn Lifecycle

> Status: Current source of truth
> Note: This describes the intended processing model. Current modules may split or bridge these steps differently during migration.

## High-Level Flow

```text
function handle_chat_turn(request):
    prepared = prepare_turn_context(request)
    navigation = interpret_user_intent(prepared)
    protocols = resolve_protocol_guidance(navigation, prepared)
    resource_seed = prepare_visible_pinned_surface_resources(prepared, navigation, protocols)
    candidate_pool = search_bounded_candidate_pool(prepared, navigation, resource_seed)
    attention = select_attention_resources(resource_seed, candidate_pool, prepared, navigation)
    recall = project_and_vet_recall(attention, candidate_pool, prepared)
    handoff = build_attention_recall_handoff(attention, recall, protocols, prepared)
    pre_authority = compute_pre_generation_intent_envelope(navigation, prepared, handoff)

    if pre_authority.accepts_pending_proposal:
        response, effects = accept_proposal_flow(prepared, navigation, pre_authority)
        authority_receipts = merge(pre_authority, effects.accepted_proposal_revalidation)
    else:
        response = generate_or_route_response(prepared, handoff, pre_authority)
        candidates = derive_post_generation_candidates(response, navigation, prepared)
        post_authority = validate_post_generation_candidates(candidates, pre_authority, prepared)
        effects = execute_authorized_effects(post_authority, prepared)
        authority_receipts = merge(pre_authority, post_authority)

    trace = record_memory_trace(prepared, response, handoff, effects)
    payload = build_public_payload(response, handoff, authority_receipts, effects, trace)
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

## Step 4: Prepare Broad Resource Seed

```text
prepare_visible_pinned_surface_resources(prepared, navigation, protocols):
    resources = []
    resources += visible surfaces that are allowed for this turn
    resources += pinned context
    resources += current Whiteboard only when visible/editing/currently targeted or pinned
    resources += app resources named by structured intent
    resources += protocol guidance candidates
    return bounded metadata-first resources
```

This step does not perform memory search. It prepares the known turn state and user-controlled surfaces that Attention may consider alongside search results.

## Step 5: Search Bounded Candidate Pool

```text
search_bounded_candidate_pool(prepared, navigation, resource_seed):
    pool = bounded_search(Memory Trace + Concepts + Memories + Artifacts + Reference Notes)
    filter hidden or suppressed records
    keep source kind, summary, and safe provenance
    return bounded candidate pool
```

Search proposes candidates; it does not decide final relevance or surface authority.

## Step 6: Select Attention

```text
select_attention_resources(resource_seed, candidate_pool, prepared, navigation):
    resources = resource_seed + candidate_pool
    selected = LLM_or_structured_selection(resources, prepared.message)
    if selected invalid:
        selected = narrow conservative fallback(resources)
    return bounded selected resources
```

Attention is broader than Recall. It includes things that may open surfaces, guide the answer, or shape continuity.

## Step 7: Recall And Vet

```text
project_and_vet_recall(attention, candidate_pool, prepared):
    memory_grounding_candidates = candidate_pool filtered by attention-selected memory roles
    keep protocol guidance in protocol_guidance role, not factual recall
    vetted = LLM_vet(memory_grounding_candidates, prepared.message, attention)
    return bounded vetted memory-grounding subset
```

Recall does not invent relevance deterministically. Deterministic code can bound, normalize, filter hidden records, and serialize.

## Step 8: Build Handoff

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

## Step 9: Compute Pre-Generation Intent Envelope

```text
compute_pre_generation_intent_envelope(navigation, prepared, handoff):
    deny writes for hard no-write turns
    record allowed action classes:
        no_write
        pending_draft
        confirmation_gated_proposal
        durable_write_candidate
        scenario_lab_output_candidate
        accepted_pending_proposal
    record expected target/scope/type constraints when known
    produce receipts for the intent envelope
```

Pre-generation authority permits only action classes and constraints. It never permits persisting arbitrary later model output. Actual target, content, scope, safety, and persistence are validated after generation or during proposal acceptance.

## Step 10: Generate Or Route

```text
generate_or_route_response(prepared, handoff, pre_authority):
    if route is Scenario Lab:
        run Scenario Lab only when pre_authority allows scenario_lab_output_candidate
    else:
        model_input = build_generation_context(prepared, handoff, pre_authority)
        assert model_input is bounded and safe
        return ResponseLLM(model_input)
```

Generation should consume handoff-derived context where possible. Legacy retrieval/search can remain as a source or diagnostic seam until retired.

## Step 11: Validate Post-Generation Candidates

```text
validate_post_generation_candidates(candidates, pre_authority, prepared):
    for candidate in candidates:
        require candidate.kind matches allowed pre_authority action class
        validate target, content, source scope, experiment/durable scope, and safety
        validate candidate does not conflict with hard no-write policy
        deny or downgrade to clarification/proposal when validation fails
    return approved_effects
```

Post-generation validation may approve, deny, clarify, or return a pending proposal. It must not recompute broad semantic authority from raw text, and it must not let pre-generation write intent become a blank check for generated text.

## Step 12: Accepted Proposal Flow

```text
accept_proposal_flow(prepared, navigation, pre_authority):
    proposal = match_pending_proposal(navigation.confirmation, prepared.pending_proposals)
    if no proposal or multiple plausible proposals:
        return clarification("Which proposal should I apply?"), no_effects
    if proposal expired or stale relative to current state:
        return clarification_or_refresh(proposal), no_effects
    revalidated = revalidate_proposal(proposal, current_permissions, current_targets, current_time)
    if not revalidated.safe:
        return clarification_or_denial(revalidated.reason), no_effects
    effects = execute_approved_proposal(revalidated)
    return acknowledgement(effects), effects
```

Proposal acceptance is a write turn with its own validation. A bare "yes" should commit only one still-valid pending proposal.

## Step 13: Execute Effects

```text
execute_authorized_effects(post_authority, prepared):
    if post_authority approves no writes:
        execute no writes
    if pending draft approved:
        create pending draft or offer, not durable save
    if durable write approved:
        write through existing storage service
    if proposal approved:
        return proposal with requires_confirmation=true
    if accepted proposal revalidated:
        execute the confirmed mutation
```

## Step 14: Trace And Public Payload

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
