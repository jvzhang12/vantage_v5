# `src/vantage_v5/webapp/product_identity.mjs`

Presentation helpers for the small “this product is different” signals shown directly in chat and in guided inspection.

## Purpose

- Build compact per-turn evidence chips such as recalled-item counts, learned items, Scenario Lab identity, and product-specific grounding labels like Recall, Whiteboard, Prior Whiteboard, or Recall + Recent Chat.
- Decide not only which compact chat evidence chips appear, but also their relative emphasis, so the transcript can stay truthful without giving every chip equal visual weight.
- Build the short Vantage header summary that mirrors the same turn truth without conflating Recall with broader Working Memory framing or other grounded context such as Whiteboard or Recent Chat, and allow the Library count to be omitted while the Library surface is hidden.
- Build concise semantic action and clarification copy from normalized semantic policy/frame payloads, keeping the text ready for future UI surfaces without wiring it into the DOM yet.
- Build the staged `Reasoning Path` inspection model for the answer dock: Request, Route, Considered context, Recall, Working Memory, and Outcome, including stage metadata and drill-down groups.
- Build the short Memory Trace inspection copy that explains whether recent history contributed to Recall and whether the turn created a durable or experiment-scoped trace record.
- Normalize whiteboard lifecycle labels such as transient draft, saved whiteboard, and promoted artifact.
- Normalize learned correction copy so the UI can distinguish direct whiteboard/pin actions, supported hide/suppress correction actions, and non-direct make-temporary/edit/delete requests without inventing unsupported backend mutations.
- Normalize learned-item correction language around the current pinned-context contract, so the UI can say `Pin as context` / `Unpin context` instead of implying single-turn carry.
- Count Scenario Lab branches from the saved comparison hub’s indexed branch roster when the live branch list is missing, so the transcript chip and Vantage summary still point at the saved comparison as the durable revisit hub.
- Accept both canonical `branchIndex` and backend-compatible `branch_index` shapes when deriving Scenario Lab evidence, so the compact chat chips stay aligned during the compatibility window.
- Translate Scenario Lab route confidence and branch-confidence text into calmer product language so the recommendation surface reads qualitative rather than console-like.
- Build the short first-read Vantage summary sentence that keeps the top of the provenance panel outcome-focused instead of stacking long explanatory copy.
- Build Inspect taxonomy buckets for Protocol, Used, Recent, and Draft context so guidance, evidence, continuity, and live draft scope do not collapse into one flat Recall list.
- Build quiet activity copy from final-turn activity, semantic policy, Scenario Lab, draft updates, and grounding state, using the production busy copy `Vantage is interpreting the request and preparing context.` while a turn is in flight.

## Key Functions

- `buildChatTurnEvidence()`
- `buildInspectBuckets()`
- `buildQuietActivityCopy()`
- `buildGuidedInspectionSummary()`
- `buildLearnedCorrectionModel()`
- `buildReasoningPathInspection()`
- `buildMemoryTraceSummary()`
- `buildSemanticPolicyCopy()`
- `buildTurnAtAGlanceSummary()`
- `describeSemanticActionCopy()`
- `describeSemanticClarificationCopy()`
- `describeLearnedCorrectionModeLabel()`
- `describeScenarioRouteConfidence()`
- `describeScenarioBranchConfidence()`
- `describeLearnedScopeLabel()`
- `describeRecallReason()`
- `describeResponseModeLabel()`
- `deriveTurnGrounding()`
- `deriveWhiteboardLifecycle()`

## Notable Behavior

- Prefers short product-facing labels over raw internal payload names, including softer idea/note/work-product nouns for learned items and calmer `Considered context` wording ahead of Recall.
- Keeps compact transcript evidence a little more human than the deeper Vantage labels: chat chips now prefer phrases like `Used your draft`, `From recent conversation`, or `From earlier` instead of echoing internal nouns such as `Whiteboard` or `Recent Chat` in isolation.
- Reads the canonical backend truth from `kind`, `groundingMode`, and recall counts instead of depending on synthetic client-only grounding kinds.
- Reuses the shared turn-payload helpers for learned-item fallback and canonical recall counts, so compact evidence chips do not depend on their own parallel `created_record` or camelCase/snake_case parsing.
- Centralizes the turn-grounding view-model the app uses for Vantage summaries and panels, including the canonical `recallCount` even when the visible recalled-item list is shorter.
- Uses the same canonical recall count for compact chat evidence, so chat chips and Vantage do not disagree when the visible recalled-item list is shorter than the grounded count.
- Makes no-recall states explicit without treating them as errors: Vantage summaries say when no recalled Vantage context was used, guided inspection shows `Recall: none` before non-recall grounding labels, and Reasoning Path names the absent source bucket as Library or Memory Trace rather than saying all context was missing.
- Normalizes user-facing recall rationale from canonical fields such as `recall_reason` and `why_recalled`, ignores machine scoring strings, and falls back to calm source-specific copy for Recall cards, including protocol-specific fallback copy when a protocol item has no explicit rationale.
- Separates applied protocols from factual recalled items in Inspect. Protocols appear as task guidance, recent trace items appear as Recent, and response-mode draft sources appear in Draft without double-counting the same recalled item.
- Normalizes a learned-item correction model from existing payload truth such as `scope`, `durability`, and `correction_affordance`, so the UI can expose direct whiteboard revision, pinned-context continuity, and direct hide-from-recall labels for supported saved-item corrections.
- Keeps correction-mode helper labels truthful: supported hide paths read as `Hide as incorrect` / `Don't use again`, unsupported scope mutation remains `How to make temporary`, and whiteboard revision remains the content-changing path.
- Translates response-mode payloads into user-facing badges like `Best Guess`, `Recall`, `Whiteboard`, `Prior Whiteboard`, source-specific mixed-context labels such as `Recall + Recent Chat`, or `Used 2 recalled items`.
- Keeps whiteboard offer / draft state out of compact transcript chips because that state already has a dedicated whiteboard notice surface; this avoids repeating the same whiteboard status in the answer chip rail, chat notice, and Vantage at once.
- Marks only the most important chat evidence as visually strong: `Scenario Lab`, `Fallback`, durable `Learned`, and `Best Guess`. Ordinary grounding and branch-count chips are intentionally returned as quieter evidence.
- Marks only the most important chat evidence as visually strong: `Scenario Lab`, `Back to chat` for Scenario Lab fallback, durable `Learned`, and `Best Guess`. Ordinary grounding and branch-count chips are intentionally returned as quieter evidence.
- Translates Scenario Lab route confidence into qualitative product copy such as `Clear fit`, `Strong fit`, `Possible fit`, or `Tentative fit`, and softens branch-level confidence copy into labels such as `Stronger case`, `Balanced case`, or `Riskier case`.
- Keeps `Memory Trace` out of response-mode grounding labels. Recent history contributes to the UI as a recall source and a trace-record summary, not as a separate top-level grounding mode.
- Keeps the `Reasoning Path` rail grounded in the existing request, interpretation, candidate context, recall, working-memory, and outcome payloads instead of inventing a separate backend trace shape.
- Keeps Scenario Lab `Best Guess` turns explicitly marked in chat evidence and guided inspection instead of suppressing the ungrounded state behind branch-count badges.
- Keeps Scenario Lab fallback turns visibly marked in chat so they still read as a routed reasoning mode rather than ordinary chat.
- Keeps the Vantage summary aligned with the same truth used for chat chips, including Scenario Lab branch counts and library context.
- Allows the Vantage summary to suppress the Library segment when the visible product surface hides the Library dock, while preserving the default Library count behavior for callers that still expose that surface.
- Uses product-facing grounding labels even when the backend still reports machine-facing mixed-context modes, so the compact chat and Vantage surfaces explain what actually supported the answer.
- Keeps `Reasoning Path` truthful to the repository’s current contract by summarizing full Working Memory as “what was in scope for this answer,” while leaving the narrower recalled-item list visible separately as `Recall`. The Working Memory drill-down is a scope table, so the user can see which inputs were included or excluded for generation. Candidate `memory_trace` items stay in `Considered context`, while recalled recent-history items contribute to the Memory Trace summary and the scope table. The path now uses softer route labels such as `used for recall`, `Kept in scope`, and humanized route confidence instead of colder console wording.
- Exposes the concrete candidate pools and selected recall items in the stage drill-down so users can inspect what was actually pulled up without opening chat internals, including recent-history candidates from `candidate_trace_notes`.
- Carries requested whiteboard mode, resolved whiteboard mode, decision source, and pinned-context continuity reason into the path summary so the interpretation stage can explain route choices without exposing raw chain-of-thought text.
- Adds a compact at-a-glance summary helper for the top of Vantage, so the first visible explanation can say things like `This answer used 2 recalled items` or `Scenario Lab prepared 3 branches` before the user opens deeper support sections.
- Adds semantic policy copy helpers that convert action tokens such as `ask_clarification`, `draft_in_whiteboard`, `run_scenario_lab`, or `show_reasoning` into short product-facing labels and pair them with a concise clarification line.
