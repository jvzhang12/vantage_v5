# Stale Artifact Inventory

> Status: Current source of truth
> Note: This guide inventories local and repo artifacts that can look authoritative during LLM-assisted Vantage work. It is report-only guidance; it does not authorize deletion, archiving, migration, or behavior changes.

Date: 2026-05-21

## Source Truth Rule

When a file or directory looks like product truth, first classify it:

- Tracked source: visible in `git ls-files`; treat as repository truth unless another current doc marks it historical or superseded.
- Untracked local file: visible in `git status --short`; treat as local draft or scratch until explicitly added.
- Ignored runtime output: visible in `git status --ignored --short`; treat as generated/local state unless it is intentionally promoted.
- External worktree: visible in `git worktree list`; treat as a separate checkout that may have its own branch, detached commit, or smoke evidence.

Read-only inventory commands:

```bash
git status --short
git status --ignored --short
git ls-files <path>
git worktree list
git branch --merged main
```

Do not delete, prune, archive, or rewrite anything from this guide without an explicit cleanup task and review of the current branch/worktree state.

## Inventory

| Category | Why it accumulates | How to detect it | Safe to delete after review | Requires review | Cautious commands |
|---|---|---|---|---|---|
| Git worktrees and old branch folders | Each review, smoke, or branch refresh can create a separate checkout so agents can test without disturbing the main worktree. | `git worktree list`; `find ~/Documents /private/tmp -maxdepth 2 -type d -name '.git'` for non-registered clones. | Detached temp worktrees whose commits are merged or no longer needed, after confirming no uncommitted work. | Any registered worktree on an active branch, any uncommitted changes, or any directory containing unique smoke evidence. | `git worktree list`; `git -C <worktree> status --short --branch`; `git branch --contains <sha>` |
| Detached review and smoke temp worktrees | Browser/API smoke and review workflows often create dated `/private/tmp/vantage-*` worktrees pinned to a commit. | `git worktree list | rg 'vantage-(review|smoke|v6)'`; inspect each worktree status. | Old detached temp worktrees with clean status and commits already reachable from `main` or a closed branch. | Any temp worktree with local modifications, untracked evidence files, or a commit not reachable from a kept branch. | `git -C <worktree> status --short`; `git branch --contains $(git -C <worktree> rev-parse HEAD)`; `git worktree prune --dry-run` |
| Runtime Markdown stores | Vantage writes product data as Markdown during local use: artifacts, concepts, memories, workspaces, and memory trace records. Ignored runtime output can sit beside tracked seed/demo records. | `git status --ignored --short artifacts concepts memories workspaces memory_trace state`; `git ls-files artifacts concepts memories workspaces memory_trace state`. | Ignored local outputs that are clearly scratch, after confirming they are not durable user content or smoke evidence. | Any tracked seed/demo record, user-authored durable content, experiment evidence, or file named in a current test/doc. | `git status --ignored --short artifacts concepts memories workspaces memory_trace state`; `git ls-files artifacts concepts memories workspaces memory_trace state` |
| Traces and Memory Trace files | Every chat turn and many smokes can create JSON traces and Markdown `memory_trace/` records. Raw traces may contain prompts, assistant text, and internal diagnostics. | `git status --ignored --short traces memory_trace`; inspect file dates and branch context. | Old ignored traces after confirming no active review needs them. | Any trace used as review/smoke evidence, any public-payload safety investigation artifact, and any durable Memory Trace record intentionally kept for recall behavior. | `find traces memory_trace -maxdepth 1 -type f | sort | tail`; `git status --ignored --short traces memory_trace` |
| Generated frontend assets | `npm run build` emits the React production bundle to `src/vantage_v5/webapp/generated/`; it is required for serving but reproducible and ignored. | `git status --ignored --short src/vantage_v5/webapp/generated`; check build docs. | Generated bundle output when rebuilding locally, after confirming it is not staged or committed. | Any tracked file under generated paths, which would indicate a contract or hygiene problem. | `git status --ignored --short src/vantage_v5/webapp/generated`; `git ls-files src/vantage_v5/webapp/generated` |
| Dependency, cache, and build directories | Python, Node, test, and packaging tools leave local output that can swamp repository scans. | `git status --ignored --short .venv node_modules build .pytest_cache tmp eval_runs src/vantage_v5.egg-info`. | Tool caches and dependency installs when no process is using them. | Anything outside ignored paths or anything needed to reproduce a failing smoke. | `git status --ignored --short .venv node_modules build .pytest_cache tmp eval_runs`; `du -sh .venv node_modules build tmp 2>/dev/null` |
| Untracked brainstorm/canon docs | Fast planning often creates local docs before the team decides whether they should become tracked source truth. | `git status --short docs`; compare against task instructions. | Nothing by default in agent work. Treat as local user/agent planning until explicitly handled. | `docs/brainstorm.md`, `docs/brainstorm-implementation-list.md`, `docs/vantage-behavioral-workflow-canon.md`, and similarly named canon/assessment docs. | `git status --short docs`; `git ls-files docs/brainstorm.md docs/brainstorm-implementation-list.md docs/vantage-behavioral-workflow-canon.md` |
| Archived or planning docs that sound active | Historical plans can preserve useful rationale but mention retired vanilla frontend files, old workspace names, or completed migration phases. | Check top status blocks; search for "Status:", "active execution tracker", `src/vantage_v5/webapp/*`, and old fallback language. | Nothing in this slice. These should be labeled or archived by a dedicated docs cleanup task, not deleted casually. | Any doc linked from `docs/README.md`, `docs/architecture-overview.md`, active branch prompts, or current tests. | `rg -n "Status:|active execution tracker|src/vantage_v5/webapp/|old frontend fallback|legacy frontend" docs` |
| Compatibility tests and old payload aliases | Tests intentionally preserve old public aliases and fallback behavior while React/backend code migrates. They can look like desired future product behavior. | Search for `working_memory`, `workspace_`, `created_record`, `concept_id`, `selected_record`, `camelCase`, and fallback language in tests and normalizers. | No test deletion by default. Compatibility removal needs a dedicated behavior-preservation and consumer-review slice. | Any public `/api/chat` payload alias, storage path name, TurnPlan behavior, write gate, or frontend normalizer. | `rg -n "working_memory|workspace_|created_record|concept_id|selected_record|camelCase|fallback" tests src/vantage_v5 docs/codebase` |
| UI evidence and screenshots | Visual audits and browser smokes produce screenshots, baselines, and JSON evidence that can outlive the UI state they captured. | `find docs/ui-research -maxdepth 3 -type f | rg 'baseline|screenshot|png|json'`; check status blocks and dates. | Old local-only screenshots after confirming they are not tracked evidence. | Tracked baselines, published audits, and evidence referenced by review findings. | `git ls-files docs/ui-research | rg 'baseline|screenshot|png|json'`; `git status --ignored --short docs/ui-research` |

## Practical Review Flow

1. Start with `git status --short --branch` so you do not confuse branch changes with runtime clutter.
2. Run `git status --ignored --short` only when you need local-state inventory; it can be noisy by design.
3. For any suspicious file, check `git ls-files <path>` before deciding whether it is source truth.
4. For worktrees, inspect the target worktree status directly before considering cleanup.
5. If a file contains user content, prompts, assistant text, trace data, or durable Markdown records, assume review is required.
6. Prefer labels and pointers over deletion when the artifact is historical rationale.

## Cleanup Slice Candidates

- Worktree cleanup slice: review registered `/private/tmp/vantage-*` worktrees, verify clean status and merged commits, then prune/remove only with explicit approval.
- Runtime state source-truth slice: add a short guide distinguishing tracked seed/demo records from ignored local stores under `artifacts/`, `concepts/`, `memories/`, `workspaces/`, `memory_trace/`, `traces/`, and `state/`.
- Compatibility ledger slice: catalog old public aliases and compatibility tests, with consumer, reason, and removal condition for each.
- UI evidence labeling slice: add status notes to screenshot/baseline evidence so dated UI snapshots do not read as current design contracts.
- Path portability slice: replace old absolute checkout links with repo-relative links where practical.
