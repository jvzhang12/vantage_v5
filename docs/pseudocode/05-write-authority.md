# 05. Write Authority

> Status: Current source of truth
> Note: This is intended authority logic. It does not authorize changing existing write execution paths or public payload shape.

## Write Principle

Vantage should never mutate durable user state merely because a reply could be useful.

```text
if action writes durable state:
    require explicit user intent or explicit confirmation flow
    require a safe target and safe content
    require TurnPlan authority
    execute through the approved write service
else:
    keep it as chat, draft, proposal, or inspection
```

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

DurableWrite:
    concept, memory, artifact, protocol, or promoted Whiteboard save
    persists to durable or experiment-scoped storage
```

## Authority Algorithm

```text
function authorize_effect(candidate, turn):
    if turn has hard_no_write surface action:
        return deny("hard no-write turn")

    if candidate.kind == Draft:
        if structured draft intent exists:
            return allow_pending_draft()
        return deny("missing draft authority")

    if candidate.kind == Proposal:
        if structured proposal intent exists and proposal is safe:
            return allow_confirmation_gated()
        return deny("unsafe or unsupported proposal")

    if candidate.kind == DurableWrite:
        if explicit save/remember/learn/publish/protocol intent exists:
            if target and content are safe:
                return allow_durable_write()
        return deny("missing durable write authority")

    return no_write()
```

## Explicit Intent Beats Convenience

```text
if user says "remember this":
    evaluate memory write authority
elif user says "save this draft":
    evaluate artifact or Whiteboard save authority
elif user asks "what do you think?":
    answer without writing
```

When intent is ambiguous, ask or propose. Do not silently persist.

## Experiment Mode

```text
if experiment_mode and write authorized:
    write to session-local store
    label saved outcome as temporary/session-scoped
    require explicit promotion for durable store
```

Experiment mode is not a shortcut around write authority.

## Calendar And Task Proposals

```text
if user requests calendar/task mutation:
    parse proposal in configured user/app timezone
    return proposed action
    requires_confirmation = true
    do not mutate calendar/task state until accepted
```

Read-only calendar/task lookup remains read-only.

## Receipts

```text
write_receipt:
    status: allowed | denied | proposed | no_write
    authority_source: Navigator | control_panel | explicit_user_intent | fallback_guardrail
    target: safe summary
    effect: safe summary
```

Receipts should explain what happened without exposing raw internal prompts or trace bodies.
