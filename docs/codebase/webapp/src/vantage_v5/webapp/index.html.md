# `src/vantage_v5/webapp/index.html`

Static shell for the Vantage web app.

## Purpose

- Define the three visible product surfaces: chat, whiteboard, and `Vantage`.
- Provide the DOM anchors consumed by `app.js`.
- Load the CSS theme and the module-based frontend entrypoint with cache-busting query strings.

## Major Regions

- Chat panel with transcript, chat-side whiteboard-decision panel, and composer. This is the default visible surface.
- Whiteboard panel with lifecycle label, whiteboard-owned decision panel, editor, and save/promote controls. When the whiteboard is focused it becomes the main drafting surface, with chat reduced to a sidebar.
- `Vantage` panel with three docks:
  - an answer dock framed as `Working Memory`, containing `Reasoning Path`, `Answer summary`, `Recall`, `Memory Trace`, and `What did the system learn?`
  - a separate Scenario Lab review dock
  - a Library dock with search, pinned-context controls, separate concept/memory/artifact/reference sections, and an inspector

## Notable Behavior

- The frontend relies on the element ids here heavily, so structural changes should move with matching `app.js` updates.
- The `Vantage` subtitle is intentionally dynamic. It starts with guided-inspection copy and is replaced at runtime with a turn summary built from response mode, recall count, learned items, library count, and Scenario Lab state.
- The Scenario Lab dock is framed as a comparison-first review surface, separate from the Working Memory dock, with summary copy that emphasizes question, recommendation, branch paths, and the saved comparison artifact.
- The `Reasoning Path` region is a staged clickable inspection rail rather than a raw console: Request, Route, Candidate context, Recall, Working Memory, and Outcome.
- Each stage card now opens turn-scoped detail inside the same dock so the user can inspect concrete candidates, recalled items, and route details without jumping into the general library inspector.
- `Recall` and `Memory Trace` are separate sections inside the answer dock. `Memory Trace` is not merged into the Library dock.
- The stylesheet and script tags both carry cache-busting query strings and should move whenever frontend semantics change, so the browser does not mix stale and fresh ES modules.
