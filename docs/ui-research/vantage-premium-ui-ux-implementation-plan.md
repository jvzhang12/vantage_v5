# Vantage Premium UI/UX Implementation Plan

## Goal

Make Vantage feel like a premium, calm, Apple-like workspace where the user mostly chats naturally and the product quietly routes work into drafting or inspection when useful.

## Product Principles

- Chat is home base. The default surface should feel like a focused conversation, not a control panel.
- Drafting is a document canvas. The whiteboard should read as a premium writing surface with minimal chrome.
- Inspection is an intelligence layer. Vantage should explain what happened in plain language before exposing deeper provenance.
- Product language should hide machinery. Internal terms such as Recall, Memory Trace, and Working Memory can remain in code, but visible labels should translate them into user-facing concepts.
- Progressive disclosure should do more work. First screens should show summaries, with deeper details behind calm disclosure controls.

## Implementation Passes

### 1. Top-Level Navigation And Status

- Rename the visible surface controls from implementation labels toward user jobs:
  - `Whiteboard` becomes `Draft`.
  - `Vantage` becomes `Inspect`.
- Keep the product name `Vantage V5` quiet in the masthead.
- Add a compact session status line with a small dot:
  - `Temporary session` when experiment mode is active.
  - `Durable session` when experiment mode is inactive.
  - `Offline` when health is unavailable.
- Keep the full experiment explanation in the first system message, not the header.

### 2. Chat Surface

- Keep the composer placeholder as `Ask anything.`
- Hide `Use sample prompt` once the user has sent a real message so the app stops feeling like a demo.
- Make transcript and assistant response presentation feel more editorial and less bubble-heavy.

### 3. Whiteboard Surface

- Reframe whiteboard copy around `Draft` and `document` language.
- Keep save/publish as lifecycle actions:
  - Draft
  - Saved whiteboard
  - Published artifact
- Reduce stacked-card feeling around whiteboard decision and artifact cues.

### 4. Inspect Surface

- Rename user-visible inspection sections:
  - `Why This Answer` -> `What I Used`
  - `Working Memory` -> `Context in Scope`
  - `Recall` -> `Pulled In`
  - `Learned` -> `Saved for Later`
  - `Look Deeper` -> `Details`
- Keep detailed technical language inside deeper collapsed sections where needed.
- Rewrite summary copy as narrative explanation instead of payload taxonomy.

### 5. Confirmation And Safety

- Keep the persistent in-app confirmation overlay for ending experiment mode.
- Do not allow backdrop clicks to cancel destructive confirmations.
- Keep `Keep experiment` as the initially focused safe action.

## Acceptance Checks

- The default chat view shows only a quiet brand mark, compact session status, `Draft`, `Inspect`, transcript, and composer.
- After the first real user message, `Use sample prompt` no longer appears.
- Experiment-ending confirmation stays visible until the user clicks `Keep experiment`, `End experiment`, or presses Escape.
- Vantage/Inspect view reads like a plain-language explanation before it reads like a diagnostics panel.
- Existing browser and Python tests pass.
- The browser picks up the change through updated cache-busting query strings.
