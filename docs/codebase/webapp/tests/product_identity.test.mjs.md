# `tests/product_identity.test.mjs`

Focused frontend unit tests for the product-identity helpers.

## Purpose

- Verify compact chat evidence labels and guided-inspection summary copy, including Scenario Lab fallback visibility, explicit `Best Guess` disclosure, and the separation between recall counts and other grounded context such as whiteboard, prior whiteboard, or recall plus recent chat.
- Verify chat evidence trusts canonical recall counts so chat chips and Vantage stay aligned even when the visible recalled-item list is shorter.
- Verify the shared grounding view-model trusts canonical normalized counts even when the visible recalled-item list is shorter.
- Verify the staged `Reasoning Path` inspection model stays truthful across recall-grounded, whiteboard-grounded, recent-chat-grounded, prior-whiteboard-grounded, mixed-context-grounded, and true best-guess turns, while also covering continuity-aware interpretation metadata, the Working Memory scope table, inspectable candidate/recall detail groups, and the memory-trace candidate bucket.
- Verify `buildMemoryTraceSummary()` keeps recent-history contribution and the created trace record visible in Vantage without turning Memory Trace into a separate grounding mode.
- Verify whiteboard lifecycle labels stay stable across transient, saved, and promoted states.

## Why It Matters

- These tests protect the small UX cues that make Vantage feel distinct without opening `Vantage` on every turn, including the shared truth between chat chips, the Vantage header, the Reasoning Path rail, and the Memory Trace summary.
