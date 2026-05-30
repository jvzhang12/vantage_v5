# 08. Failure Modes

> Status: Current source of truth
> Note: These are intended guardrails for future implementation and review. They do not imply every current path is already clean.

## Failure Mode: Architecture-First Chat

Symptom:

- ordinary Q&A opens panels, asks unnecessary confirmations, or exposes internal terms

Guard:

```text
if normal chat can satisfy the request:
    keep response conversational
    surface only compact evidence/receipts
```

## Failure Mode: Unbounded Context

Symptom:

- whole graph, whole transcript, unbounded or unrelated full artifact bodies, or raw Memory Trace records enter generation
- selected, in-scope artifact or Whiteboard content is blocked merely because it is fuller than the compact public view

Guard:

```text
assert context_source_count <= budget
assert each source has role and summary
allow selected in-scope artifact_or_whiteboard_content within budget
keep public working_memory_view compact even when internal model context is fuller
assert raw trace bodies are absent unless internal-only and explicitly allowed
```

## Failure Mode: Premature Write Authority

Symptom:

- pre-generation intent is treated as permission to persist whatever the model later writes
- generated content bypasses target, content, scope, safety, or persistence validation

Guard:

```text
pre_authority = allowed action classes and constraints only
post_authority = validate generated candidates against pre_authority
if candidate does not match both phases:
    do not write
```

## Failure Mode: Orphaned Proposal

Symptom:

- a confirmation-gated proposal can be shown, but later "yes" has no safe commit path
- a stale or ambiguous "yes" commits the wrong calendar/task mutation

Guard:

```text
pending proposal has stable id, normalized arguments, created_at, expires_at, and status
confirmation must match exactly one fresh proposal
accepted proposal must be revalidated before execution
ambiguous or stale confirmation asks clarification
```

## Failure Mode: Circular Attention/Recall

Symptom:

- Attention requires Recall results before search exists
- Recall claims to vet only Attention-selected resources before Attention has a candidate pool

Guard:

```text
prepare visible/pinned/surface resources
search bounded candidate pool
Attention selects broad resources from seed + candidates
Recall projects/vets memory-grounding subset
Working Memory composes final bounded model context
```

## Failure Mode: Public Trace Leak

Symptom:

- `/api/chat` exposes raw Memory Trace body, `## User Message`, `## Assistant Response`, prompt-derived ids, or prior raw prompt phrases

Guard:

```text
for public_payload in chat_response:
    scan for unsafe trace markers
    project Memory Trace candidates through shared safe projection
    replace prompt-derived trace ids with safe aliases
```

## Failure Mode: Projection Tier Confusion

Symptom:

- compact public `working_memory_view` is mistaken for the full internal model context
- generation receives public-only summaries when selected in-scope artifact or Whiteboard content is needed
- public payloads expose generation-safe or internal storage content

Guard:

```text
internal_storage may be richest and private
generation_safe may include selected bounded content within budget
public_safe stays compact and trace-safe
diagnostic_safe shows bounded parity/status only
never leak raw trace bodies or prompt-derived ids across tiers
```

## Failure Mode: Deterministic Routing Drift

Symptom:

- keyword checks become the real semantic router
- Navigator/control-panel output becomes decorative

Guard:

```text
if code infers broad user intent from raw text:
    require proof this is a narrow fallback or safety validation
    label fallback source
    prefer structured LLM intent repair
```

## Failure Mode: Accidental Writes

Symptom:

- visible artifact Q&A, open/close actions, or ordinary chat creates memories, artifacts, concepts, or drafts

Guard:

```text
if turn_plan says no_write:
    execute no write candidates
    expose denial/no-write receipt if useful
```

## Failure Mode: Scenario Lab Write Bypass

Symptom:

- Scenario Lab creates branch workspaces or comparison artifacts without explicit Scenario Lab authority
- generated branch content persists without post-generation validation

Guard:

```text
explicit Scenario Lab invocation creates ScenarioLabOutput intent envelope
post-generation validates branch/comparison content, scope, and storage targets
ambiguous Scenario Lab intent asks or offers instead of writing
```

## Failure Mode: Whiteboard Scope Creep

Symptom:

- hidden or stale Whiteboard content grounds unrelated chat

Guard:

```text
if Whiteboard is not editing, currently targeted, pinned, or explicitly referenced:
    exclude from Working Memory
```

## Failure Mode: Memory Trace Privacy Drift

Symptom:

- automatic trace retention becomes raw transcript replay
- sensitive user content stays recallable after "do not remember" or correction/forget flows
- prior assistant text is treated as factual evidence without backing

Guard:

```text
store raw trace only in private internal tier when policy allows
use summaries or bounded excerpts for recall/generation
mark sensitive or user-suppressed traces non-recallable
treat prior assistant text as continuity evidence unless independently grounded
track unresolved retention horizon before broadening retention
```

## Failure Mode: Concept/Memory/Artifact Collapse

Symptom:

- every saved thing becomes a concept or generic memory

Guard:

```text
classify saved outcome by role:
    timeless knowledge -> Concept
    continuity fact -> Memory
    concrete output -> Artifact
    imported source material -> Reference Note by explicit import authority
```

## Failure Mode: Protocols Treated As Facts

Symptom:

- protocol guidance is cited as factual evidence

Guard:

```text
if source.kind == protocol:
    role = protocol_guidance
    evidence_label = guidance, not factual grounding
```

## Failure Mode: Compatibility Amnesia

Symptom:

- old aliases or workspace names are deleted because they look stale

Guard:

```text
before removing alias/path/fallback:
    check compatibility ledger
    check test taxonomy
    check React/API consumers
    require explicit retirement slice
```

## Failure Mode: Local State Mistaken For Source Truth

Symptom:

- generated assets, traces, runtime stores, temp worktrees, or untracked brainstorm docs are treated as canonical

Guard:

```text
if file is generated, ignored, runtime, or untracked:
    treat as evidence only
    do not stage or rewrite unless explicitly instructed
```

## Failure Mode: Safe Projection Bypass

Symptom:

- one public, generation, or diagnostic path sanitizes trace-derived data, but another parallel path forwards raw selected resources

Guard:

```text
all Memory Trace-derived resources crossing a tier boundary:
    pass through the projection helper for that tier
    preserve non-trace records unless unsafe by source evidence
    keep generation_safe richer than public_safe only when selected, in scope, and budgeted
```
