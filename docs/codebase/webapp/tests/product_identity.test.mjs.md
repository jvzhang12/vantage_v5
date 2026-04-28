# `tests/product_identity.test.mjs`

Focused frontend unit tests for the product-identity helpers.

## Purpose

- Verify compact chat evidence labels and guided-inspection summary copy, including Scenario Lab fallback visibility, explicit `Best Guess` disclosure, and the separation between recall counts and other grounded context such as whiteboard, prior whiteboard, or recall plus recent chat.
- Verify the remaining compact transcript chips stay product-facing rather than systemy, while still preserving the deeper Vantage grounding labels for guided inspection.
- Verify compact chat evidence emphasis stays intentional: lower-priority grounding chips remain quiet, while `Scenario Lab`, fallback, `Best Guess`, and durable `Learned` stay visually stronger.
- Verify the guided summary speaks in calmer product nouns such as `What I learned`, and that considered-context details use idea/note/reference wording instead of console-style source labels.
- Verify learned-item chips stay inspectable and use softer product nouns such as idea, note, and work product.
- Verify the first-pass learned-correction model stays truthful: temporary vs library-saved scope labels remain distinct, direct revision defaults to the whiteboard, pinned-context language stays explicit, and wrong / temporary / forget requests are disclosed as non-direct when the backend cannot do them yet.
- Verify Scenario Lab confidence helpers stay qualitative and product-facing for both route-level and branch-level presentation.
- Verify the short at-a-glance Vantage summary stays outcome-focused instead of expanding back into a long explanatory paragraph.
- Verify whiteboard offer / draft state is not repeated in transcript chips once the dedicated whiteboard notice owns that status.
- Verify chat evidence trusts canonical recall counts so chat chips and Vantage stay aligned even when the visible recalled-item list is shorter.
- Verify the shared grounding view-model trusts canonical normalized counts even when the visible recalled-item list is shorter.
- Verify the Scenario Lab branch count can still be derived from the saved comparison artifact’s indexed branch roster when the live branch list is missing, so the transcript chip and Vantage summary still point at the artifact as the durable revisit hub.
- Verify the staged `Reasoning Path` inspection model stays truthful across recall-grounded, whiteboard-grounded, recent-chat-grounded, prior-whiteboard-grounded, mixed-context-grounded, and true best-guess turns, while also covering continuity-aware interpretation metadata, the Working Memory scope table, inspectable considered-context / recall detail groups, and the memory-trace bucket.
- Verify `buildMemoryTraceSummary()` keeps recent-history contribution and the created trace record visible in Vantage without turning Memory Trace into a separate grounding mode.
- Verify `describeRecallReason()` prefers explicit user-facing recall rationale, ignores machine scoring strings, and falls back to plain-language source-specific copy.
- Verify `buildInspectBuckets()` separates protocol guidance, used Recall items, recent continuity, and draft signals.
- Verify `buildQuietActivityCopy()` prefers explicit activity steps and falls back to concise turn-state summaries.
- Verify learned-item correction helpers keep the first-pass correction loop truthful by distinguishing temporary versus durable saves and exposing continuation-oriented correction copy without claiming direct delete or scope mutation support.
- Verify whiteboard lifecycle labels stay stable across transient, saved, and promoted states.

## Why It Matters

- These tests protect the small UX cues that make Vantage feel distinct without opening `Vantage` on every turn, including the shared truth between chat chips, the Vantage header, the Reasoning Path rail, and the Memory Trace summary.
