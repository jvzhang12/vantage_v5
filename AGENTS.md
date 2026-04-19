# Agent Operating Rules

This file is the repo-level contract for any agent or subagent working in `vantage-v5`.

## Read First

Before changing code:

1. Read this file.
2. Read [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md).
3. Read the codebase map at [docs/codebase/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/README.md).
4. Read [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) before you split work across implementation or review subagents.
5. Read the mirrored Markdown summary for each source or test file you plan to edit.
6. Read the source code only after you understand the summary-level intent.

## Core Product Rules

- Keep the product chat-first.
- Do not let internal architecture make ordinary chat feel rigid or heavy.
- Preserve the distinction between:
  - `concepts/` for timeless reasoning knowledge
  - `memories/` for retained user, project, or session facts
  - `artifacts/` for concrete outputs and workspace snapshots
- Preserve the distinction between durable mode and experiment mode.
- Experiment-mode writes must stay session-local unless explicitly promoted.

## Documentation Rules

- If you change a Python file, update its mirrored summary in `docs/codebase/python/...`.
- If you change a webapp file under `src/vantage_v5/webapp`, update its mirrored summary in `docs/codebase/webapp/...`.
- If you add a new Python file, add a matching summary Markdown file in the mirrored docs tree during the same change.
- If you add a new webapp source/test file, add a matching summary Markdown file in the mirrored docs tree during the same change.
- If you remove or rename a Python file, update or remove its mirrored summary accordingly.
- If you remove or rename a webapp source/test file, update or remove its mirrored summary accordingly.
- If your change alters a repo-level behavior or architectural contract, update [README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/README.md) too.
- If your change affects the source/test/docs map itself, run `python3 scripts/check_repo_hygiene.py`.
- Keep summaries concise and practical: purpose, key functions/classes, major dependencies, and notable behaviors.

## Change Discipline

- Prefer small, targeted changes over broad refactors.
- Do not rename major routes, payload keys, or storage conventions unless necessary.
- Use LLM reasoning for semantic interpretation, routing, and continuity judgments; use deterministic code for validation, guardrails, and persistence.
- Do not replace semantic turn interpretation with brittle keyword logic unless you are working on an explicit offline fallback path.
- If you change API shapes, update:
  - backend implementation
  - frontend consumers
  - tests
  - mirrored docs summaries
- If you change the repo's source/test file layout, update the relevant codebase map under `docs/codebase/` and keep the hygiene check passing.
- Preserve backwards compatibility when it is cheap and useful.
- Do not silently introduce new architectural abstractions unless they clearly simplify the system.

## Testing Rules

- Add or update tests for behavior changes.
- Prefer focused tests near the changed behavior rather than broad speculative coverage.
- Do not leave the repo in a state where docs and tests disagree with the code.

## Storage And Retrieval Rules

- Do not collapse concepts, memories, and artifacts back into a single generic store.
- Concepts should remain high-trust reasoning substrate.
- Chat-time retrieval should stay mixed and bounded across concepts, memories, artifacts, and optional reference notes.
- The UI should keep the `Whiteboard`, `Working Memory`, `Learned`, and `Library` roles visibly separate.
- The library view should keep `Concept KB`, `Memories`, `Artifacts`, and `Reference Notes` visibly separate.
- Selection in the library should open an item for inspection only; pinned context is the explicit mechanism for carrying an item into future turns.
- Pinned context should persist until the user clears it.
- Saved items shown in the memory panel should come from memories and artifacts, not from the concept KB.
- Retrieval should stay bounded and explicit.
- Do not pass the entire knowledge graph into model context.

## Workspace Rules

- The shared workspace is for active collaboration.
- Default composer routing should stay chat-first and `auto`; explicit whiteboard controls should invite drafting rather than forcing whiteboard-first behavior for every turn.
- When the user is asking for a concrete work product such as an email, plan, itinerary, list, essay, paper, or code draft, prefer inviting whiteboard collaboration unless the user already clearly wants the whiteboard or explicitly wants the full output in chat.
- Once the user chooses the whiteboard, substantial structured drafts should prefer the whiteboard over verbose chat when that makes the interaction easier to refine.
- Whiteboard offers and whiteboard drafts returned from normal chat should stay pending and inspectable until the user explicitly accepts or saves them; do not silently apply them to disk.
- Workspace content should not automatically become a concept.
- Promoting workspace content should usually create an artifact unless the user explicitly wants timeless conceptualization.
- When no relevant working memory grounded a reply, keep the visible disclosure honest and plain: `This is new to me, but my best guess is:`

## Agent Conduct

- Make the minimum reasonable assumption needed to move forward.
- Do not revert unrelated user or agent changes.
- Do not delete durable user content unless explicitly asked.
- If you touch a file, leave it easier for the next agent to understand.

## Good Defaults

- Start from the docs map.
- Keep the codebase maps current enough that a fresh subagent can navigate without guesswork.
- Keep behavior inspectable.
- Keep write paths conservative.
- Prefer clarity over cleverness.

## Subagent Prompt Template

Use [docs/subagent-orchestration-protocol.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/subagent-orchestration-protocol.md) as the authoritative handoff contract. The shorter template below is only a convenience wrapper and must defer to the protocol for scope, review, and closeout expectations. If you need a quick starting point, use this shape when spawning a worker for this repo:

```text
You are working in /Users/eden/Documents/Obsidian Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5.

Before editing:
1. Read AGENTS.md.
2. Read README.md.
3. Read docs/codebase/README.md.
4. Read the mirrored Markdown summaries for the files you will touch.
5. For any semantic-contract wave, also read docs/glossary.md, docs/semantic-rules.md, and the exact roadmap section named by the task.
6. Only then read the source files themselves.

Repo rules:
- Keep Vantage chat-first.
- Preserve the distinction between concepts, memories, and artifacts.
- Preserve experiment-mode isolation.
- If you change a Python file, update its mirrored docs/codebase/python/... .py.md summary in the same task.
- If you change a webapp file, update its mirrored docs/codebase/webapp/... summary in the same task.
- If you add a Python file, add its mirrored summary too.
- If you add a webapp file, add its mirrored summary too.
- If you change API behavior, update backend, frontend, tests, and docs together.
- If you change source/test/docs layout, keep `python3 scripts/check_repo_hygiene.py` passing.
- Do not revert unrelated changes.
- You are not alone in the codebase; work only within your assigned files and adapt to existing edits.
- For semantic-contract waves, the quick template is not enough on its own; it only works when paired with the orchestration protocol and the exact semantic docs for the task.

At the end:
- List every file you changed.
- Mention any tests or checks you ran.
```
