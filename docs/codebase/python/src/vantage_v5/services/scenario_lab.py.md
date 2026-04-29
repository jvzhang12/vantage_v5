# `src/vantage_v5/services/scenario_lab.py`

Scenario Lab service for Vantage V5. It takes a navigator decision, runs bounded retrieval and vetting, asks the model to turn the request into a small set of scenario branches plus a comparison plan, then saves those branches as workspace Markdown and the comparison as an artifact while preserving the same turn-explanation contract used by normal chat.

## Purpose

- Turn comparative what-if turns into durable workspace branches.
- Preserve a structured comparison artifact alongside the branches.
- Reuse the normal search and vetting stack so scenario branches stay grounded in existing context.
- Produce a response payload that the UI can render as a distinct mode without losing the shared `recall` / `working_memory`, `learned`, and `response_mode` fields.

## Core Data Flow

- `ScenarioLabService.run()` merges durable and reference concepts, memories, artifacts, and memory traces, resolves a selected record when one is in focus, honors any navigator-provided preserve / do-not-preserve decision for that selected record, builds the shared continuity hint from the selected record and any live whiteboard context, then retrieves candidate memory from the current question plus vault notes.
- Navigator-applied protocols are resolved through `ProtocolEngine.build_guidance()` and merged into the candidate set before vetting, so persisted protocol overrides or the built-in Scenario Lab protocol can guide first-principles, counterfactual, causal, tradeoff, and assumption reasoning even when those concepts are not semantically close to the user's wording.
- The vetted memory is passed into an OpenAI scenario-building call with the navigator hints for comparison question, branch count, and branch labels.
- Follow-up turns can preserve the selected record in candidate and vetted memory when the message reads like a natural continuation, not just when it is ultra-short, and the shared continuity hint lets active whiteboard drafts inform vetting without turning the draft into extra saved context.
- The selected record is no longer injected into the candidate pool by default; only explicit preservation or the shared fallback continuity heuristic can pull it back into the five-item working set.
- When continuity is not being preserved, Scenario Lab also avoids forwarding the selected record into the scenario-building prompt as a separate hidden anchor.
- `response_mode` now reuses the shared `build_response_mode_payload()` grounding classifier from normal chat, so Scenario Lab can truthfully report canonical `recall` grounding plus `whiteboard`, `recent_chat`, `pending_whiteboard`, `mixed_context`, or `best_guess` instead of collapsing everything into a coarse private contract.
- The model returns a `ScenarioPlan` with shared context, branch-specific assumptions/effects/risks, and comparison text.
- The chat-facing Scenario Lab answer is now built from the structured plan as a compact decision brief: recommendation, why, top tradeoffs, and the saved branch list. The full branch and comparison artifacts remain the deeper inspectable output.
- Before persistence, Scenario Lab now decides whether the scenario namespace is `anchored` to the active workspace id or `detached` into its own stable namespace, then previews the comparison artifact id so both branches and the artifact can point at the same durable hub on first write.
- `_save_branches()` normalizes the branch plans, shortens or humanizes branch titles when the model drifts into sentence-like headings, generates unique workspace ids inside the anchored or detached scenario namespace, renders Markdown with a stable `## Scenario Metadata` block, and saves each branch through `WorkspaceStore` with rollback cleanup if branch persistence fails midway.
- `_save_comparison_artifact()` renders the comparison Markdown, neutralizes outcome-biased comparison titles when needed, reuses that neutral title for the saved artifact body heading, stores the artifact through `ArtifactStore` with `type="scenario_comparison"` as a stable marker, writes `artifact_origin="scenario_lab"` plus `artifact_lifecycle="comparison_hub"`, and persists durable scenario metadata including the branch ids, a stable branch index, the namespace, and the comparison artifact id into the Markdown body/frontmatter.
- `ScenarioLabTurn.to_body_parts()` exposes the Scenario Lab facts needed by the turn assembler, including the navigator decision, concise summary plus recommendation, saved branch metadata, comparison artifact, unified product-safe `recall` / `working_memory`, `learned`, `response_mode`, additive taxonomy fields, and a `created_record` compatibility source for UI reuse. `to_dict()` remains a compatibility helper that delegates the public response-body shape to `turn_payloads.py` through `ScenarioLabTurnBodyParts`, so Scenario Lab owns comparison facts while the assembler owns compatibility aliases. The learned comparison-artifact payload now also carries lifecycle-owned artifact card fields, a user-facing `why_learned`, a truthful `durability` marker, and a small `correction_affordance` hint so the comparison hub reads like an inspectable saved object rather than a generic artifact blob.
- Scenario Lab now writes Memory Trace records with `turn_mode="scenario_lab"` and exposes the same structured trace metadata back through the turn payload, so recent-history continuity stays inspectable even for navigator-routed turns. Those traces also carry an internal referenced-record fact, typically pointing at the freshly created comparison artifact, so short follow-ups can reopen the right durable scenario hub without re-inferring it from the whole previous answer.
- `_trace_turn()` writes a JSON trace that includes the turn payload, workspace excerpt, recent history, any carried pending whiteboard context, and the scenario plan.

## Key Classes / Functions

- `ScenarioBranchPlan`: per-branch plan returned by the model.
- `ScenarioComparisonPlan`: comparison summary, tradeoffs, recommendation, and next steps.
- `ScenarioPlan`: normalized structured output from the model.
- `ScenarioLabTurn`: structured Scenario Lab turn facts, with `to_body_parts()` for the deep assembler boundary and `to_dict()` retained for compatibility callers.
- `ScenarioLabService`: coordinates retrieval, generation, persistence, and tracing.
- `_openai_build_scenario()`: calls OpenAI to build the structured scenario plan, treating protocol items in vetted memory as task recipes rather than factual source claims.
- `_scenario_chat_brief()`: turns the structured comparison plan into the short visible chat brief so users get the recommendation and tradeoffs without opening the saved artifact.
- `_save_branches()`: renders and persists branch workspaces.
- `_save_comparison_artifact()`: renders and persists the comparison artifact.
- `resolve_selected_record_candidate()`, `should_preserve_selected_record()`, `build_continuity_hint()`, `_merge_candidate_memory()`, and `anchor_selected_record_candidate()`: preserve selected-record continuity for genuine follow-up turns while keeping Scenario Lab aligned with the same bounded continuity contract as normal chat.
- The continuity helpers now live in `vetting.py`, where they are shared with normal chat so selected-record preservation and live-draft continuity use one path instead of two slightly different heuristics.
- `_render_branch_workspace()`: builds the Markdown document for one branch.
- `_render_comparison_artifact()`: builds the Markdown comparison document.
- `_normalize_branch_plans()`: clamps branch count to 2-3 and fills in defaults when needed.
- `_scenario_namespace()`: chooses whether branch ids should stay anchored to the active workspace or use a detached scenario namespace derived from the comparison itself, and returns both the namespace id and mode.
- `_neutral_comparison_title()`: rewrites recommendation-like titles into a neutral comparison title before artifact naming and namespace derivation.
- `_cleanup_paths()`: removes newly written workspace or artifact files if Scenario Lab persistence fails after partial success.
- `_trace_turn()`: writes the scenario trace file.

## Notable Edge Cases

- If OpenAI is unavailable, the service raises and the server falls back to normal chat.
- If persistence fails after some scenario outputs have already been written, the service deletes the files it created during that run before re-raising.
- Requested branch count is normalized into a 2-3 branch output, even when the navigator suggests something outside that range.
- Branch labels are slugified, generic comparisons can break out of the active workspace namespace, workspace ids are made unique before saving, and both branch workspaces and the comparison artifact now carry parseable scenario metadata in Markdown rather than a hidden store. Comparison artifacts also carry a stable branch index so revisit flows can recover branch id, title, label, and summary from the record itself.
- If the model returns an outcome-biased comparison title such as a recommendation or declared winner, Scenario Lab rewrites that title into a neutral comparison label so the artifact and branch namespace do not look pre-decided.
- Long descriptive branch titles are converted into shorter human-facing headings while the original meaning is preserved as the branch thesis card.
- Scenario Lab does not write memory or graph actions; it saves workspaces and an artifact, then returns `mode: "scenario_lab"` with the same explanation fields ordinary chat uses.
- Scenario Lab `response_mode` stays compatible with the frontend's coarse/fine structure while remaining explicit about when the answer was grounded by the whiteboard, recent chat, pending whiteboard continuity, or canonical Recall instead of only the legacy working-memory wording.
- Scenario Lab retrieval now forwards current whiteboard and preserved-context hints into the shared search service only for bounded Memory Trace tuning, keeping continuity semantic without forcing the selected record into scope.
- Protocol candidates are advisory reasoning guidance, not evidence. `ProtocolEngine` owns their candidate DTO construction, and the Scenario Lab prompt explicitly tells the model to use the Scenario Lab Protocol when present while keeping factual grounding separate.
- Selected comparison artifacts continue to be valid continuity anchors for revisit turns, and Scenario Lab now reloads the selected record's lineage when building that continuity payload so legacy `scenario_comparison` artifacts can still recover base-workspace and branch metadata from `comes_from` even when the body predates the newer metadata block.
- That selected-record payload now mirrors the ordinary server lineage helpers: `comes_from` stays raw provenance, while `derived_from_id`, `revision_parent_id`, and `lineage_kind` distinguish comparison-artifact provenance from true concept revisions.
- Scenario comparison artifacts are marked with `type="scenario_comparison"`, selected-record payloads now surface parsed comparison metadata when available, and the Scenario Lab API payload emits richer branch/comparison metadata such as `base_workspace_id`, `comparison_artifact_id`, `scenario_namespace_id`, and `namespace_mode`.
- The comparison artifact is promoted into the existing saved-item UI path via both `learned` and its `created_record` compatibility alias, while the branch workspaces remain separate workspace records. Its payload now also carries explicit lifecycle cues plus the product-safe learned rationale/correction affordance fields so the UI can present it as a comparison hub instead of a generic derived artifact.
