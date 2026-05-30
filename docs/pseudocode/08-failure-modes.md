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

## Failure Mode: Whiteboard Scope Creep

Symptom:

- hidden or stale Whiteboard content grounds unrelated chat

Guard:

```text
if Whiteboard not active, pinned, or referenced:
    exclude from Working Memory
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

- one public or generation path sanitizes trace-derived data, but another parallel path forwards raw selected resources

Guard:

```text
all public/model-input Memory Trace-derived resources:
    pass through shared projection helper
    preserve non-trace records unless unsafe by source evidence
```
