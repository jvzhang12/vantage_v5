# Subagent Orchestration Protocol

## Purpose

This document is the execution contract for scoped implementation and review work in `vantage-v5`.

Use it when a task is being split across workers and you want the next agent to preserve context, respect scope, and close out cleanly without rediscovering the repo from scratch.

It stays faithful to the current repository, not to older or heavier canonical architecture that the repo does not implement today.

## Repository Invariants To Preserve

Keep these product facts in scope for every worker that touches behavior or documentation:

- the product is chat-first
- `Whiteboard` is a shared collaborative draft surface
- `Vantage` is the inspection surface for Working Memory, Learned, and the Library
- `Working Memory`, `Learned`, `Whiteboard`, and `Library` should remain visibly distinct
- concepts, memories, and artifacts are separate durable stores with different roles
- experiment mode is session-local unless something is explicitly promoted
- Scenario Lab is a distinct navigator-routed reasoning mode, not ordinary chat
- retrieval stays bounded; the whole graph is not passed into model context

If a task would violate one of those invariants, the worker should stop and report the conflict instead of silently broadening scope.

## Source Of Truth Order

When deciding what the repository means today, use this order:

1. the current source code and the current repo docs
2. [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
3. [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md)
4. [docs/semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md)
5. [docs/implementation-vs-canon.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/implementation-vs-canon.md)
6. [docs/implementation-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/implementation-roadmap.md)
7. [docs/codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md) and the mirrored summaries
8. older canonical Nexus docs only when they do not conflict with the current repo truth

This order keeps implementation work grounded in what `vantage-v5` actually does now.

## Required Reading Before A Worker Starts

Every worker should read, in this order:

1. [AGENTS.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/AGENTS.md)
2. [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md)
3. [docs/codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md)
4. this protocol
5. the mirrored summary files for the exact source or test files in scope
6. the source files themselves
7. any adjacent docs that define the product semantics touched by the task

Workers should not browse outside that bundle unless a clearly necessary dependency forces it.

For semantic-contract waves, the worker should also read [docs/glossary.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/glossary.md), [docs/semantic-rules.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/semantic-rules.md), and the exact roadmap section named by the task before starting implementation or review.

## Scope Rules

- Keep one worker focused on one coherent goal.
- Give the worker an exact file list, not a vague area.
- Include explicit non-goals so the worker does not widen the task.
- Allow adjacent-file reads only when the dependency is concrete and easy to explain.
- If a worker discovers an out-of-scope change that is necessary, it should stop and report it rather than expanding silently.
- Do not ask a worker to edit files that belong to another wave unless the new work is clearly part of the same contract.

Good scope bundles usually include:

- the change goal
- the allowed files
- the docs to read first
- the expected user-visible or API-visible behavior
- the tests or checks that should prove the change
- the explicit files or behaviors that are out of bounds

## Implementation Worker Responsibilities

Implementation workers are responsible for making the change and keeping docs aligned with it.

They should:

- edit only the scoped files unless they surface a necessary adjacent doc or test
- preserve unrelated user or agent changes
- use the repo's existing patterns instead of inventing a parallel architecture
- update mirrored documentation when behavior or file layout changes
- keep work small enough that a reviewer can reason about the diff quickly
- report the files they changed, the checks they ran, and any remaining risks

Implementation workers should not:

- perform their own review and treat that as a substitute for independent review
- broaden scope because a related improvement seems appealing
- silently rewrite the product model while "just fixing" a bug

## Review Worker Responsibilities

Review workers are independent checks, not co-authors.

They should:

- inspect the exact diff plus the immediately relevant surrounding context
- verify behavior, tests, docs, and scope boundaries
- call out regressions, missing tests, doc drift, and hidden coupling
- rank findings by severity
- say explicitly when no findings were found

Review workers should not:

- edit files unless they are asked to do a follow-up implementation pass
- re-scope the task
- hide uncertainty behind approval language
- treat a passing test run as proof that the design is correct

## Closeout Expectations

Every completed wave should end with a short closeout that answers:

- what changed
- which files changed
- which checks ran
- what remains risky
- whether docs are still in sync

If review finds an issue, the orchestrator should either:

- send a narrow revision pass, or
- stop the wave and report the blocker clearly

## Recommended Handoff Template

Use this shape when orchestrating implementation work:

```text
You are working in /Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5.

Before editing:
1. Read AGENTS.md.
2. Read README.md.
3. Read docs/codebase/README.md.
4. Read this protocol.
5. Read the mirrored summaries for the exact files in scope.
6. For any semantic-contract wave, also read docs/glossary.md, docs/semantic-rules.md, and the exact roadmap section named by the task.
7. Only then read the source files themselves.

Repo invariants:
- keep Vantage chat-first
- preserve the distinction between concepts, memories, artifacts, whiteboard, Working Memory, Learned, and Library
- preserve experiment isolation
- keep retrieval bounded
- keep Scenario Lab separate from ordinary chat

Your scope:
- list only the files you are allowed to edit
- list any adjacent files you may inspect but not edit
- list explicit non-goals

At the end:
- list every file you changed
- list the checks you ran
- report any risks or follow-up items
```

Use this shape when orchestrating review work:

```text
You are reviewing the exact diff for the scoped task in /Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5.

Read:
1. AGENTS.md
2. README.md
3. docs/codebase/README.md
4. this protocol
5. the changed files and their mirrored summaries
6. docs/glossary.md
7. docs/semantic-rules.md
8. the exact roadmap section named by the task

Review scope:
- do not edit files
- focus on correctness, regressions, docs drift, missing tests, and scope creep
- report findings ordered by severity
- say explicitly if there are no findings

At the end:
- summarize the highest-risk residue, if any
- note whether another revision pass is needed
```
