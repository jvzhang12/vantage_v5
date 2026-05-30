# 05. Write Authority

> Status: Current source of truth
> Note: This is intended authority logic. It does not authorize changing existing write execution paths or public payload shape.

## Write Principle

Vantage should never mutate durable user state merely because a reply could be useful.

```text
if action writes durable state:
    require pre-generation intent envelope
    require post-generation candidate validation
    require safe target, content, scope, and persistence path
    execute through the approved write service
else:
    keep it as chat, draft, proposal, or inspection
```

Pre-generation authority is not a blank check. It can say "this turn may produce a memory candidate" or "this turn may propose a task," but it cannot pre-approve arbitrary later model output for persistence.

## Action Classes

```text
NoWrite:
    ordinary chat
    Q&A about visible artifacts
    open/close/preserve surface actions
    inspect-only Library actions

Draft:
    pending Whiteboard content
    not durable until accepted/saved

Proposal:
    calendar/task or other operational mutation candidate
    requires_confirmation=true
    status="proposed"

AcceptedProposal:
    user confirmation matched to one pending proposal
    executes only after staleness, ambiguity, permission, target, and safety revalidation

DurableWrite:
    concept, memory, artifact, protocol, Reference Note import, or promoted Whiteboard save
    persists to durable or experiment-scoped storage

ScenarioLabOutput:
    branch workspaces and comparison artifact for explicit Scenario Lab invocation
    durable or experiment-scoped only after Scenario Lab authority and post-generation validation
```

## Phase 1: Pre-Generation Intent Envelope

```text
function compute_pre_generation_intent_envelope(turn):
    if turn has hard_no_write surface action:
        return envelope(allowed=[NoWrite], reason="hard no-write turn")

    envelope = envelope(allowed=[NoWrite])

    if structured Whiteboard draft intent exists:
        envelope.allow(Draft, constraints=target_whiteboard_or_offer)

    if structured calendar/task/proposal intent exists:
        envelope.allow(Proposal, constraints=operation_kind + normalized target hints)

    if structured save/remember/learn/publish/protocol/import intent exists:
        envelope.allow(DurableWrite, constraints=expected_record_type + target scope hints)

    if explicit Scenario Lab invocation exists:
        envelope.allow(ScenarioLabOutput, constraints=branch_count + comparison intent + scope)

    if current turn confirms a pending proposal:
        envelope.allow(AcceptedProposal, constraints=pending_proposal_reference)

    return envelope
```

The envelope records allowed action classes, expected types, target hints, and scope constraints. It does not validate generated content because that content does not exist yet.

## Phase 2: Post-Generation Candidate Validation

```text
function validate_post_generation_candidate(candidate, envelope, turn):
    if candidate.kind not in envelope.allowed:
        return deny("candidate not allowed by pre-generation intent")

    if candidate conflicts with hard no-write policy:
        return deny("blocked by no-write authority")

    if candidate.kind == Draft:
        if target, content, and conflict policy are safe:
            return allow_pending_draft()
        return clarify_or_deny("unsafe or ambiguous draft target")

    if candidate.kind == Proposal:
        if operation, target, normalized arguments, expiry, and confirmation copy are safe:
            return allow_confirmation_gated()
        return clarify_or_deny("unsafe or unsupported proposal")

    if candidate.kind == DurableWrite:
        if record type, target, content, source scope, and persistence path are safe:
            return allow_durable_write()
        return clarify_or_deny("unsafe durable write candidate")

    if candidate.kind == ScenarioLabOutput:
        if explicit Scenario Lab authority exists and branch/comparison outputs are safe:
            return allow_scenario_lab_outputs()
        return clarify_or_deny("missing or unsafe Scenario Lab output authority")

    return no_write()
```

Post-generation validation checks target, content, source scope, experiment/durable scope, safety, and persistence. If validation fails, the system should deny, ask, or return a pending proposal rather than writing anyway.

## Explicit Intent Beats Convenience

```text
if user says "remember this":
    treat this as write intent, then classify content by durable type
    prefer Memory for user/project/session continuity facts
    prefer Concept for timeless reusable reasoning knowledge
    prefer Artifact for concrete outputs or snapshots
    ask if the type materially changes behavior and remains ambiguous
elif user says "save this draft":
    evaluate artifact or Whiteboard save authority
elif user says "update the email protocol":
    evaluate protocol durable-write authority
elif user asks "what do you think?":
    answer without writing
```

When intent is ambiguous, ask or propose. Do not silently persist.

## Protocol Updates

Protocol updates are durable writes when the user explicitly asks to create or modify reusable task guidance.

```text
if user explicitly updates protocol:
    pre_authority.allow(DurableWrite, type=Protocol)
    post_generation validates protocol kind, content, override scope, and persistence path
elif model infers a possible preference but user did not ask to update protocol:
    ask or propose; do not silently persist protocol changes
```

## Multi-Action Writes

Multi-action turns should be decomposed into independent candidates.

```text
if user says "remember this and add a task tomorrow":
    envelope.allow(DurableWrite, type=Memory or classified saved type)
    envelope.allow(Proposal, type=Task)

for each candidate:
    validate independently
    execute only candidates that pass
    report partial success, pending proposals, denials, or clarifications separately
```

One authorized action must not launder authority for another.

## Experiment Mode

```text
if experiment_mode and write authorized:
    write to session-local store
    label saved outcome as temporary/session-scoped
    require explicit promotion for durable store
```

Experiment mode is not a shortcut around write authority.

## Pending And Accepted Proposals

Pending proposals are write candidates waiting for user confirmation. They need stable identity and lifecycle state.

```text
PendingProposal:
    proposal_id
    action_kind                 # calendar_event, task, etc.
    normalized_arguments
    safe_title_or_summary
    source_turn_id_or_safe_alias
    created_at
    expires_at
    status = proposed | accepted | expired | superseded | rejected
```

Acceptance flow:

```text
function accept_pending_proposal(user_confirmation, pending_proposals, current_state):
    matches = match_confirmation(user_confirmation, pending_proposals)

    if matches.count == 0:
        return clarify("I do not see a pending proposal to apply.")
    if matches.count > 1:
        return clarify("Which proposal should I apply?")

    proposal = matches.only()

    if proposal.expired or proposal.superseded:
        return clarify_or_refresh("That proposal is stale.")

    revalidated = revalidate(proposal, current_state)
    if not revalidated.safe:
        return deny_or_clarify(revalidated.reason)

    return execute_confirmed_mutation(revalidated)
```

Revalidation must check current permissions, target existence, time/date interpretation, operation safety, experiment/durable scope, and conflicts with newer state.

## Calendar And Task Proposals

```text
if user requests calendar/task mutation:
    parse proposal in configured user/app timezone
    return proposed action
    requires_confirmation = true
    do not mutate calendar/task state until accepted
```

Read-only calendar/task lookup remains read-only.

## Scenario Lab Writes

Explicit Scenario Lab invocation authorizes Scenario Lab output candidates, not arbitrary writes.

```text
if user explicitly asks for Scenario Lab or Navigator routes there with high confidence:
    pre_authority.allow(ScenarioLabOutput)
    generate branches and comparison according to Scenario Lab protocol
    post_generation validates branch outputs, comparison artifact, scope, and storage targets
    persist only validated Scenario Lab outputs
else:
    ask clarification or offer Scenario Lab; do not create comparison artifacts
```

Current design intent treats explicit Scenario Lab invocation as authority for branch outputs and a comparison artifact after validation. If product direction later changes to pending Scenario Lab drafts, this section should be updated before implementation changes.

## Fallback Write Boundary

Fallback should not execute durable writes.

```text
if structured model/control-panel output fails:
    fallback may return:
        no_write
        clarification
        confirmation-gated proposal shell
    fallback must not execute DurableWrite or AcceptedProposal
```

Unresolved product decision: whether provider-offline fallback may create non-durable draft content. Until decided, fallback-generated drafts should be treated as pending, inspectable, and non-durable.

## Receipts

```text
write_receipt:
    status: allowed | denied | proposed | accepted | executed | no_write | clarification_needed
    authority_source: Navigator | control_panel | explicit_user_intent | fallback_guardrail
    target: safe summary
    effect: safe summary
    phase: pre_generation_envelope | post_generation_validation | accepted_proposal_revalidation
```

Receipts should explain what happened without exposing raw internal prompts or trace bodies.
