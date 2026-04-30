# `src/vantage_v5/webapp/index.html`

Static shell for the Vantage web app.

## Purpose

- Define the three visible product surfaces: chat, Draft, and Inspect.
- Define the sign-in gate used when auth is required or a browser session expires, including the create-account toggle and password confirmation field used when local account creation is enabled.
- Provide the DOM anchors consumed by `app.js`.
- Provide the persistent confirmation overlay used for high-friction local actions such as ending experiment mode.
- Provide the provider-key dialog used to enter, save, inspect masked status for, and clear the current user's OpenAI API key, including a reminder that clearing the key from Vantage does not rotate or revoke it at OpenAI.
- Load the CSS theme, the vendored local KaTeX and Highlight.js runtimes, and the module-based frontend entrypoint with cache-busting query strings.

## Major Regions

- Auth panel with sign-in/create-account form controls, then chat panel with a minimal masthead, transcript shell, chat-side draft-decision panel, and composer. The masthead keeps the brand, compact session status, provider-key access, and `Draft` / `Inspect` controls available while onboarding and session-mode explanation live in the first system message instead of the header.
- Draft panel with a utility header, title deck, draft-owned decision panel, a compact latest-work-product cue, document-sheet wrapper, source editor, a conditional live-preview section for math/code-rich drafts, and a single calm action row for `Back to chat`, `Save draft`, and `Publish artifact`. When Draft is focused it becomes the main drafting surface, with chat reduced to a sidebar.
- Inspect panel with two visible docks and one temporarily hidden Library dock:
  - a primary answer dock presented as `What I Used`, with the inner turn panel titled `This turn`, containing an at-a-glance summary first, then a dedicated `Context in Scope` narrative block, then separate `Pulled In` and `Saved for Later` sections, followed by a `Details` group for `Memory Trace` and the collapsed-by-default `Reasoning Path`
  - the support sections inside that primary dock use calmer collapsible summary rows with counts, so recalled items, learned items, and recent continuity stay legible without reading like one long always-open stack
  - a separate Scenario Lab review dock whose summary copy now frames the mode as one coherent reasoning experience: question, recommendation, durable hub, then the related branch set
  - a Library dock with search, pinned-context controls, separate reusable-ideas/memories/work-products/references sections, and an inspector; the dock remains in the DOM for later reuse but is hidden from the current Vantage view while the product surface is being simplified

## Notable Behavior

- The frontend relies on the element ids here heavily, so structural changes should move with matching `app.js` updates.
- The page now loads local vendored KaTeX and Highlight.js scripts before the module graph so read surfaces can render LaTeX-style math and readable fenced code without runtime CDN dependencies.
- The Inspect subtitle is intentionally dynamic. It starts with guided-inspection copy and is replaced at runtime with a turn summary built from response mode, recall count, learned items, library count, and Scenario Lab state.
- The top Inspect dock owns the provenance framing, while the inner panel now reads as `This turn` so the first screen does not repeat the same headline twice.
- The answer dock now leads with `Context in Scope` as a distinct explanation layer before `Pulled In`, so the shell can tell the user what was broadly in scope for generation without implying that every in-scope source was a recalled library item.
- The stylesheet query string should move when visual-system semantics change so browser cache does not hold onto stale shell styling during iterative refinement passes.
- The stylesheet and module query strings now move together for production-facing whiteboard passes as well, because sidebar-copy and whiteboard-shell refinements can otherwise leave the browser showing fresh CSS with stale module text or vice versa.
- The cache-busting query strings were bumped again for the material-hardening follow-up pass so the browser reliably picks up the less frosted, less pill-heavy production polish without requiring manual cache cleanup.
- The cache-busting query strings were bumped again for the Apple-tech visual direction pass so the browser reliably picks up the cooler white/graphite palette, SF-style typography, and cleaner native editor treatment.
- The cache-busting query strings were bumped again for the masthead status-dot pass so the browser picks up both the copy change and the status-dot styling.
- The cache-busting query strings were bumped again for the system-introduction pass, which hides the default masthead onboarding copy and moves the product/session explanation into the initial system message.
- The cache-busting query strings were bumped again for the intro-copy follow-up so the browser picks up the revised message explaining what makes Vantage unique.
- The cache-busting query strings were bumped again for the first-person intro follow-up so the browser picks up the updated Vantage voice.
- The cache-busting query strings were bumped again for the context-management intro follow-up so the browser picks up the updated first-run message.
- The cache-busting query strings were bumped again for the Library dock cleanup, which keeps the dropdown summary title but hides the repeated inner Library title card when the dock is open.
- The cache-busting query strings were bumped again for the temporary Library-hide pass, which removes the Library dock from the visible Vantage surface while keeping the DOM anchors available for future restoration.
- The cache-busting query strings were bumped again for the Library-hide follow-up, which forces Chrome to reload the updated module graph that also suppresses the Library count from the Vantage header.
- The cache-busting query strings were bumped again for the turn-action removal pass, which removes the unclear `Next turn: remember`, `Next turn: don't save`, and `Open related now` controls from the Vantage answer dock.
- The cache-busting query strings were bumped again for the simplified composer pass, which changes the default chat placeholder to `Ask anything.` so users do not have to mention the whiteboard explicitly.
- The cache-busting query strings were bumped again for the Draft/Inspect copy-interaction pass, so the browser picks up the renamed surface controls, compact session status, and first-message sample-prompt hiding.
- The cache-busting query strings were bumped again for the premium UI pass, which removes dev-version chrome from the browser title/masthead and keeps the first Inspect dock framed as answer context rather than implementation provenance.
- The stylesheet cache-busting query string was bumped again for the chat-window pass, so the browser picks up the fixed-height shell, independent panel scrolling, and compact composer refinements.
- The module cache-busting query string was bumped again for the multi-user pass, so the browser picks up the user-aware compact status label from `/api/health`.
- The module cache-busting query string was bumped again for the semantic-frame pass, so the browser reliably picks up the new turn-payload normalization and compact Inspect understanding cue.
- The module cache-busting query string was bumped again for the semantic-policy pass, so the browser reliably picks up semantic policy normalization, product copy, and Inspect next-step cues.
- The module cache-busting query string was bumped again for the protocol-polish pass, so Inspect cards pick up protocol-specific labels and rationale copy instead of stale generic memory presentation.
- The module and stylesheet cache-busting query strings were bumped again for the Inspect activity/protocol-editor pass, so browsers pick up the quiet activity line, Inspect buckets, protocol editor, and supporting styles together.
- The module and stylesheet cache-busting query strings were bumped again for the protocol-editor follow-up, so browsers pick up the protocol-specific selection/opening behavior and final quiet-activity busy copy.
- The app module cache-busting query string was bumped again for the protocol-editor lookup fix, so browsers pick up turn-scoped protocol inspection without requiring a manual hard refresh.
- The app module cache-busting query string was bumped again for the visible protocol-editor fix, so browsers pick up the editor directly on applied protocol cards in Inspect.
- The app module cache-busting query string was bumped again for the Scenario Lab chat-card action cleanup, so browsers pick up the single `Inspect comparison` action on comparison-hub transcript cards.
- The app module cache-busting query string was bumped again for the Library category copy pass, so browsers pick up reusable idea, memory, work product, and reference labels consistently.
- The Scenario Lab dock is framed as a comparison-first review surface, separate from the Working Memory dock, with summary copy that keeps the comparison question, recommendation, durable hub, and related branch set legible on first read.
- The `Reasoning Path` region is a staged clickable inspection rail rather than a raw console: Request, Route, Considered context, Recall, Working Memory, and Outcome. It sits in the later `Details` group so the main turn explanation still leads.
- Each stage card now opens turn-scoped detail inside the same dock so the user can inspect concrete candidates, recalled items, and route details without jumping into the general library inspector.
- The answer dock now reads in a more explicit provenance order: at-a-glance summary, `Context in Scope`, `Pulled In`, `Saved for Later`, then deeper detail. `Memory Trace` remains separate from both `Pulled In` and the Library dock.
- The `What I learned` block now includes a dedicated `Correction path` region so learned items can expose direct revise / pin actions plus honest `not direct yet` guidance without routing the user to a separate mutation surface.
- Scenario Lab’s internal reading order now leads with the comparison question and recommendation, then the durable comparison hub, then the reopenable branches, with route/grounding support moved later as secondary inspection detail.
- The dock shell intentionally keeps Scenario Lab out of the ordinary answer/provenance framing so it can read as a distinct reasoning mode rather than a second answer block.
- The chat shell now separates the masthead utility row from the transcript shell so the turn stream can read as its own surface below the header instead of blending into the controls.
- The chat shell keeps the utility buttons intentionally quieter so the transcript remains the focus and the top bar reads as guidance, not as an operator panel.
- The experiment control now lives beside the mode badge instead of inside the main action cluster, so first-time users see it as an optional session mode rather than a primary conversation action.
- The Pass 02A chat voice pass keeps the default title/subtitle explicitly chat-first, shortens the initial masthead copy, and treats the first visible chat surface as transcript-led rather than shell-led.
- The same pass keeps a reduced experiment cue visible even in whiteboard-sidebar mode, so the session boundary remains legible without restoring the full header control cluster.
- The whiteboard shell keeps the utility header above the title deck, so the back/save/promote controls stay separate from the document title and canvas framing.
- The Pass 02B whiteboard pass now wraps the draft stack in a single centered page measure, so the title deck, decision state, latest saved work-product cue, editor, and conditional preview read as one authored surface instead of separate stacked panels.
- The same pass shortens the utility copy, keeps the action cluster quieter, and renames the preview heading to a more reading-oriented `Rendered Preview`.
- A later production pass keeps those same controls and labels but relies on the stylesheet to present them with a more sober tool feel, so `Back to chat`, `Save whiteboard`, and `Publish artifact` read as deliberate publishing actions instead of as consumer-app pills.
- The whiteboard surface uses a document-sheet wrapper around the editor so the writing area reads like a page on a surface rather than a plain textarea.
- The whiteboard preview is a separate read surface under the source editor. It only appears when the draft contains LaTeX-style math or code, so the whiteboard does not read like a constant source/preview tool during ordinary drafting.
- The chat transcript, concept cards, and library inspector all rely on the same renderer contract now, so this shell explicitly reserves a preview surface in the whiteboard rather than trying to typeset directly inside the textarea.
- When whiteboard mode is active, the chat shell is meant to read as a secondary sidebar rather than as a co-equal second surface, and the shell copy now reflects that separation explicitly.
- `Recall` and `Memory Trace` are separate sections inside the answer dock. `Memory Trace` is not merged into the Library dock.
- The whiteboard surface now includes a compact `Latest durable work product` cue so ordinary whiteboard saves can expose an inspect/reopen path without creating a separate artifact surface.
- The Library inspector remains the only artifact review surface; whiteboard and Scenario Lab entry points route into that inspector or reopen artifacts into the whiteboard rather than adding a second artifact panel.
- The stylesheet and script tags both carry cache-busting query strings and should move whenever frontend semantics change, so the browser does not mix stale and fresh ES modules during active refinement passes.
- The entrypoint intentionally bumps its module query string during hotfixes like Scenario Lab rendering fixes, because stale child-module caches can otherwise surface runtime errors even when the source tree is already corrected.
- The entrypoint intentionally uses cache-busting query strings aggressively during active refinement passes because a stale module graph can otherwise look like a dead chat form even when the backend is healthy.
- The stylesheet and module cache-busting query strings were bumped again for the user OpenAI-key pass, so browsers pick up the new provider-key dialog and masthead control together.
- The stylesheet and module cache-busting query strings were bumped again for the local account-creation pass, so browsers pick up the auth-form mode toggle and confirmation field together.
- The stylesheet and module cache-busting query strings were bumped again for the OpenAI-key warning pass, so browsers pick up the provider-key security reminder without stale modal markup.
