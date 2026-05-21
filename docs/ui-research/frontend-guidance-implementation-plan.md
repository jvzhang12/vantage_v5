# Frontend Guidance Implementation Plan

> Status: Historical rationale
> Current source of truth: [docs/architecture-overview.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/architecture-overview.md) and [docs/codebase/webapp/README.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/codebase/webapp/README.md)
> Note: This file is preserved as the UI polish tracker used during earlier frontend passes. File-target references to `src/vantage_v5/webapp/*` describe the retired vanilla frontend and should not guide new implementation work.

This was the implementation plan for an earlier Vantage UI polish pass. It superseded the older UI implementation plans listed in [Retired Planning Docs](#retired-planning-docs) during that pass.

## Purpose

Use the frontend guidance rubric to make Vantage feel more stable, ergonomic, and product-grade without changing the core architecture:

- Chat remains the default work surface.
- Draft remains the focused whiteboard/document surface.
- Inspect remains the deliberate provenance and memory review surface.
- Scenario Lab remains a distinct comparison mode.

This plan is meant to be easy to track. Update the checkboxes as slices land, and add short notes under `Progress Log` when behavior changes.

## Progress Log

- [x] Slice 0: Baseline visual QA captured.
- [x] Slice 1: Responsive shell stability.
- [x] Slice 2: Typography and text-fit normalization.
- [x] Slice 3: Surface controls and toolbar ergonomics.
- [x] Slice 4: Card nesting, radius, and decorative-style reduction.
- [ ] Slice 5: Explanatory-copy reduction and progressive disclosure.
- [ ] Slice 6: Whiteboard mode ergonomics.
- [ ] Slice 7: Accessibility, labels, and tooltips.
- [ ] Slice 8: Final visual QA and documentation updates.

## Tracker Table

Use this table as the compact execution view. Update `Status` first, then add short implementation notes in the slice section below if the behavior changes.

| Slice | Status | Scope | Exit Signal |
| --- | --- | --- | --- |
| 0 | Complete | Capture desktop and narrow baseline screenshots before CSS or DOM changes. | Baseline screenshots and notes exist. |
| 1 | Complete | Stabilize Chat, Draft, and Inspect shell behavior across common widths. | No horizontal clipping at 390px, 640px, 768px, 1024px, and desktop. |
| 2 | Complete | Normalize core UI typography, text fit, and letter spacing. | No core `font-size: clamp(...)`; major UI text uses `letter-spacing: 0`. |
| 3 | Complete | Clarify surface controls and quiet account/provider utilities. | Active surface is obvious; utility controls do not compete with workflow controls. |
| 4 | Complete | Reduce nested-card feeling, oversized radii, and decorative gradients. | Inspect and Scenario Lab read as calmer operational surfaces. |
| 5 | Not started | Shorten explanatory copy and move durable explanation behind disclosure. | First screen feels action-oriented while safety copy remains visible. |
| 6 | Not started | Improve Draft/Whiteboard ergonomics and medium-width chat rail behavior. | Draft is focused, while Chat and Inspect remain recoverable. |
| 7 | Not started | Add accessible names, tooltips, and focus treatment for compact controls. | Core inputs and compact controls have discoverable labels. |
| 8 | Not started | Run final QA, screenshots, tests, and doc updates. | Tests pass and retired docs are not presented as active implementation paths. |

## Current Findings

The frontend guidance audit identified these concrete improvement areas:

- `shell--vantage` can become cramped before the mobile breakpoint because the two-column minimums and shell padding can exceed available width.
- Major headings use viewport-scaled `clamp(...)` font sizes and negative letter spacing, while the rubric asks for stable font sizing and `letter-spacing: 0`.
- Inspect, Scenario Lab, and Library surfaces still contain several cards inside cards, with many radii above the requested 8px default.
- Top-level controls are text buttons (`API key`, `Draft`, `Inspect`, `Sign out`) rather than a clearer surface switch plus quieter utility controls.
- Some visible copy explains how the product works instead of letting controls, state, and progressive disclosure carry the interaction.
- Whiteboard mode makes chat secondary, but the chat rail can become too narrow and hides utility affordances in a way that may make navigation feel less reliable.
- Gradients and radial backgrounds appear in many places; the product would likely feel calmer if color was reserved for state, category, and action.
- Textareas and utility controls need stronger accessible labeling and tooltip treatment before icon/tool controls are expanded.

## Guardrails

- Preserve current surface semantics in `surface_state.mjs`.
- Do not turn Inspect into a developer console.
- Do not expose hidden Library as part of this polish pass unless a slice explicitly says so.
- Do not change backend payload contracts for a visual-only slice.
- Keep UI labels aligned with current product vocabulary: Chat, Draft, Inspect, Whiteboard, Working Memory, Recall, Memory Trace, Library, Saved for Later.
- Prefer small, verifiable slices over a broad redesign sweep.
- After each visual slice, run at least:
  - `node --check src/vantage_v5/webapp/app.js`
  - `node --test tests/webapp_state_model.test.mjs`
  - `git diff --check`

## Slice 0: Baseline Visual QA

Status: complete.

Goal: capture the current UI before changing it, so polish work can be compared against real screenshots instead of memory.

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- [x] Capture desktop screenshots for sign-in, chat, Draft, and Inspect.
- [x] Capture narrow/mobile screenshots for sign-in, chat, Draft, and Inspect.
- [x] Record any obvious overlap, clipping, cramped controls, or excessive chrome.
- [x] Save notes in this document under the relevant later slice.

Baseline artifacts:

- [desktop-1440x1000-sign-in.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/desktop-1440x1000-sign-in.png)
- [desktop-1440x1000-chat.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/desktop-1440x1000-chat.png)
- [desktop-1440x1000-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/desktop-1440x1000-draft.png)
- [desktop-1440x1000-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/desktop-1440x1000-inspect.png)
- [mobile-390x900-sign-in.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-sign-in.png)
- [mobile-390x900-chat.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-chat.png)
- [mobile-390x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-draft.png)
- [mobile-390x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-inspect.png)
- [mobile-390x900-draft-fullpage.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-draft-fullpage.png)
- [mobile-390x900-inspect-fullpage.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-0/mobile-390x900-inspect-fullpage.png)

Baseline notes:

- Sign-in is stable at desktop and 390px mobile widths.
- Chat is readable at both widths, but mobile header controls wrap into multiple rows and compete with the durable-session pill.
- Desktop Draft exposes the suspected narrow chat rail: account controls, Inspect, status, composer, and Send are squeezed into a thin left column.
- Mobile Draft makes the document readable, but the utility/chat rail is pushed below the draft surface; `Publish artifact` wraps into a separate row.
- Desktop Inspect entered from Draft shows duplicated `Back to draft` controls and leaves a large empty chat column beside the inspection panel.
- Mobile Inspect starts below the chat surface, so the first viewport after clicking Inspect still looks like Chat rather than Inspect. The full-page capture confirms Inspect exists below the fold.
- Inspect uses several nested cards and explanatory blocks, which supports the later card/copy simplification slices.

Acceptance criteria:

- There is a visual baseline before CSS or DOM changes.
- The baseline includes at least one narrow viewport.

## Slice 1: Responsive Shell Stability

Status: complete.

Goal: make Chat, Draft, and Inspect stable across desktop, tablet, and mobile widths.

Primary files:

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)

Checklist:

- [x] Rework `shell--vantage` breakpoints so the two-column layout collapses before its minimum widths create horizontal pressure.
- [x] Verify `shell--whiteboard` does not produce a too-narrow chat rail on medium-width screens.
- [x] Ensure body/shell overflow behavior does not trap content or create hidden controls.
- [x] Confirm composer, notices, and panel headers stay visible without overlap.

Implementation notes:

- `shell--whiteboard` now uses a grid with a wider desktop Draft chat rail instead of the prior very narrow flex rail.
- At tablet/mobile widths, Draft switches to a compact top utility toolbar followed by the document surface. This keeps `Inspect` visible without forcing the user below the document first.
- `shell--vantage` collapses to a vertical stack before the two-column minimums become cramped. Follow-up user testing moved the compact Chat/Draft/Inspect controls back above Inspect on narrow screens so users are not stranded below a long diagnostic page.
- Narrow shells allow page scrolling instead of trapping overflow inside a fixed-height shell.
- Follow-up after Slice 4: the base `body` and `.shell` overflow behavior now allows normal page/shell scrolling when Chat content exceeds the visible viewport.
- Follow-up after in-app testing: surface changes now reset document/shell scroll to the top, so returning from Inspect or Draft starts at the reachable navigation controls.

Verification artifacts:

- [390x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/390x900-draft.png)
- [390x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/390x900-inspect.png)
- [768x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/768x900-draft.png)
- [768x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/768x900-inspect.png)
- [1024x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/1024x900-draft.png)
- [1440x1000-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/1440x1000-draft.png)
- [verification.json](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-1/verification.json)

Verification notes:

- Automated viewport checks found no horizontal overflow at 390px, 640px, 768px, 1024px, or 1440px.
- Mobile Inspect now keeps the compact surface controls above the Inspect panel, then shows Inspect content below them.
- Mobile and tablet Draft keep `Inspect` visible near the top of the screen.
- Desktop Draft keeps a usable chat composer rail while preserving Draft as the dominant surface.
- Desktop/tablet Inspect still shows some duplicate `Back to draft` affordances when entered from Draft; leave that for the surface-control ergonomics slice.

Acceptance criteria:

- No horizontal clipping at common widths: 390px, 640px, 768px, 1024px, and desktop.
- Chat, Draft, and Inspect can all be entered and exited at each tested width.
- Text in header buttons and dock labels wraps or truncates intentionally.

## Slice 2: Typography And Text-Fit Normalization

Status: complete.

Goal: make typography stable, readable, and aligned with the frontend rubric.

Primary files:

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- [x] Replace viewport-scaled heading font sizes with stable size tokens.
- [x] Set negative letter spacing to `0` unless a specific local exception is documented.
- [x] Audit small uppercase labels so they remain legible and do not crowd compact panels.
- [x] Ensure long labels such as `Reusable ideas` and `Published artifact` fit in badges/buttons.

Implementation notes:

- Removed all `font-size: clamp(...)` declarations from core UI text rules.
- Removed all negative `letter-spacing` declarations from the stylesheet.
- Normalized major heading tracking to `letter-spacing: 0`.
- Added text-fit safeguards for buttons, status pills, badges, and concept-type chips so long labels can wrap intentionally inside their containers.
- Reduced the Draft title sizing on narrow screens so long document titles wrap as product UI, not as hero copy.

Verification artifacts:

- [390x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/390x900-draft.png)
- [390x900-draft-long-labels.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/390x900-draft-long-labels.png)
- [768x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/768x900-draft.png)
- [1024x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/1024x900-inspect.png)
- [1440x1000-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/1440x1000-draft.png)
- [verification.json](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-2/verification.json)

Verification notes:

- `rg -n "font-size:\s*clamp|letter-spacing:\s*-" src/vantage_v5/webapp/styles.css` returned no matches.
- Automated viewport checks found no horizontal overflow at 390px, 640px, 768px, 1024px, or 1440px.
- Long-label stress checks found no overflowing text in buttons, badges, status pills, `h1`, or `h2` elements.
- Mobile Draft long-title rendering is acceptable after the narrower fixed title size.

Acceptance criteria:

- No `font-size: clamp(...)` remains for core UI text.
- Major UI text uses `letter-spacing: 0`.
- Buttons, chips, and compact cards handle long labels without incoherent overlap.

## Slice 3: Surface Controls And Toolbar Ergonomics

Status: complete.

Goal: make top-level navigation and utility actions easier to scan.

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- [x] Convert `Chat / Draft / Inspect` into a clear surface control or segmented control while preserving current button ids or updating tests safely.
- [x] Move account/provider utilities (`API key`, `Sign out`) into a quieter utility group.
- [x] Add tooltips or `aria-label` copy for compact utility controls.
- [x] Do not add an icon dependency unless the repo already has one or the slice explicitly includes it.

Implementation notes:

- Added a stable `Chat / Draft / Inspect` surface switch in the chat masthead.
- Preserved existing `whiteboardToggleButton` and `vantageToggleButton` ids, and added `chatSurfaceButton` for the explicit Chat surface.
- Kept surface labels stable while using active state and `aria-pressed` to communicate the current surface.
- Moved `API key` and `Sign out` into a lower-emphasis utility group with accessible names and tooltip copy.
- Kept the existing return flow intact: Inspect can still return to Draft when opened from Draft, while only Inspect is visually active.

Verification artifacts:

- [390x900-chat.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-3/390x900-chat.png)
- [390x900-draft.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-3/390x900-draft.png)
- [1024x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-3/1024x900-inspect.png)
- [1440x1000-chat.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-3/1440x1000-chat.png)
- [verification.json](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-3/verification.json)

Verification notes:

- `node --check src/vantage_v5/webapp/app.js` passed.
- `node --test tests/webapp_state_model.test.mjs` passed: 24 tests.
- `git diff --check` passed.
- Automated viewport checks found no horizontal overflow at 390px, 640px, 768px, 1024px, or 1440px.
- Automated active-state checks confirmed exactly one active surface button for Chat, Draft, and Inspect at each tested width.
- Automated text-fit checks found no overflowing text in visible buttons, badges, or status pills.

Acceptance criteria:

- The active surface is obvious from the top-level controls.
- Provider/account controls do not compete with primary workflow controls.
- Keyboard and screen-reader labels remain clear.

## Slice 4: Card Nesting, Radius, And Decorative-Style Reduction

Status: complete.

Goal: make the UI feel more like a quiet operational tool and less like nested decorative panels.

Primary files:

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)

Checklist:

- [x] Reduce default card/control radii toward 8px, with explicit exceptions for modals and tiny chips.
- [x] Remove page-section-as-card styling where a full-width or unframed section works better.
- [x] Flatten repeated gradients and radial backgrounds.
- [x] Reserve color for state, category, and primary action.
- [x] Keep repeated item cards visually distinct but less ornamental.

Implementation notes:

- Reduced shared card/control radii to `8px`, while keeping larger outer panels, modals, and tiny pills as intentional exceptions.
- Flattened decorative gradients and shadows across the Answer Context, Scenario Lab, protocol guidance, context budget, reasoning path, concept cards, and library inspector shells.
- Converted several blue/green gradient treatments into quiet fills plus simple border accents so color reads as state/category instead of decoration.
- Made Scenario Lab's hero unframed and lighter, while keeping branch cards, comparison-hub cards, and support cards visually distinct.
- Fixed a narrow mobile Scenario Lab header case where a metadata badge could get squeezed into a vertical label.

Verification artifacts:

- [390x900-scenario-lab.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-4/390x900-scenario-lab.png)
- [1024x900-inspect.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-4/1024x900-inspect.png)
- [1024x900-scenario-lab.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-4/1024x900-scenario-lab.png)
- [1440x1000-scenario-lab.png](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-4/1440x1000-scenario-lab.png)
- [verification.json](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/baselines/2026-04-30-slice-4/verification.json)

Verification notes:

- `node --check src/vantage_v5/webapp/app.js` passed.
- `node --test tests/webapp_state_model.test.mjs` passed: 24 tests.
- `git diff --check` passed.
- Automated viewport checks found no horizontal overflow across Chat, Draft, Inspect, and mocked Scenario Lab at 390px, 768px, 1024px, and 1440px.
- Automated text-fit checks found no overflowing visible button, badge, status pill, or dock label text.
- A broader mobile text-overflow probe on Scenario Lab headings/body copy returned no overflowing text.

Acceptance criteria:

- Inspect and Scenario Lab no longer read as many nested cards of equal weight.
- The palette is not dominated by one hue family.
- The UI still preserves clear state/category cues.

## Slice 5: Explanatory Copy And Progressive Disclosure

Status: not started.

Goal: reduce visible instructional text while keeping Vantage understandable.

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/product_identity.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/product_identity.mjs)

Checklist:

- [ ] Remove or shorten static copy that explains how to use the app.
- [ ] Keep dynamic state copy where it tells the user what happened in this turn.
- [ ] Move deeper explanatory text behind existing disclosure controls where appropriate.
- [ ] Keep safety copy, API key warnings, and destructive-action confirmations explicit.

Acceptance criteria:

- First-screen UI feels action-oriented rather than tutorial-like.
- Inspect still explains provenance when opened.
- Safety-critical warnings remain visible and specific.

## Slice 6: Whiteboard Mode Ergonomics

Status: not started.

Goal: make Draft feel focused without making Chat or Inspect feel unavailable.

Primary files:

- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/surface_state.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/surface_state.mjs)
- [tests/webapp_state_model.test.mjs](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/tests/webapp_state_model.test.mjs)

Checklist:

- [ ] Revisit the chat rail width in Draft mode.
- [ ] Keep the path to Inspect visible or clearly recoverable while drafting.
- [ ] Ensure Draft actions (`Back to chat`, `Save draft`, `Publish artifact`) do not visually crowd the document title.
- [ ] Preserve current non-destructive draft application behavior.

Acceptance criteria:

- Draft feels like the primary authored surface.
- Chat remains usable for follow-up requests.
- Surface return behavior still passes frontend state tests.

## Slice 7: Accessibility, Labels, And Tooltips

Status: not started.

Goal: make compact controls accessible before adding more compact/icon-like affordances.

Primary files:

- [src/vantage_v5/webapp/index.html](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/index.html)
- [src/vantage_v5/webapp/app.js](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/app.js)
- [src/vantage_v5/webapp/styles.css](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/src/vantage_v5/webapp/styles.css)

Checklist:

- [ ] Add explicit labels or `aria-label`s for composer and whiteboard textarea.
- [ ] Add tooltip behavior for any compact utility controls introduced in Slice 3.
- [ ] Verify modal/dialog focus states remain visible.
- [ ] Verify disabled button states remain visually clear.

Acceptance criteria:

- Core input controls have accessible names.
- Compact controls have discoverable labels.
- Focus-visible states are consistent after visual simplification.

## Slice 8: Final Visual QA And Docs

Status: not started.

Goal: verify the full polish pass and keep documentation current.

Checklist:

- [ ] Run focused JS and Python tests.
- [ ] Capture desktop and mobile screenshots after the final slice.
- [ ] Compare against Slice 0 baseline.
- [ ] Update codebase docs for `index.html`, `app.js`, and `styles.css`.
- [ ] Update this plan's progress log.
- [ ] Update [docs/system-improvements-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/system-improvements-checklist.md) if a parent item is completed.

Acceptance criteria:

- No known layout overlap or clipping remains in the tested viewports.
- The app remains chat-first, Draft-focused when drafting, and Inspect-focused when inspecting.
- The retired docs are not presented as active implementation paths.

## Retired Planning Docs

These docs remain useful historical context, but they are no longer the active execution tracker:

- [external-feedback-implementation-slices.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-implementation-slices.md)
- [external-feedback-follow-on-roadmap.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/external-feedback-follow-on-roadmap.md)
- [vantage-premium-ui-ux-implementation-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-premium-ui-ux-implementation-plan.md)
- [vantage-visual-redesign-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-checklist.md)
- [vantage-visual-redesign-master-plan.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/vantage-visual-redesign-master-plan.md)
- [archive/vantage-ui-implementation-checklist.md](/Users/eden/Documents/Obsidian%20Vault/Nexus/99_Reference/openclaw-workspace-seal-vantage/vantage-v5/docs/ui-research/archive/vantage-ui-implementation-checklist.md)

When a retired doc conflicts with this plan, this plan wins for frontend implementation sequencing.
