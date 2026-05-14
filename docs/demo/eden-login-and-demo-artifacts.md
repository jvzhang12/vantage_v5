# Eden Login And Demo Artifacts

## Login

- App URL: `http://127.0.0.1:8005/`
- Username: `eden`
- Password: `vantage-demo-eden`
- Recommended demo model: `gpt-5.3-codex-spark` via `VANTAGE_V5_MODEL`

Note: the `eden` account has been reset to the demo password above.

## Demo Readme

This profile is seeded to show Vantage as a chat-first context manager that summons operational surfaces and durable artifacts only when useful.

Start with:

1. `What does my day look like?`
2. `When should I study for the midterm today?`
3. `Show my to-do list and what I should focus on.`
4. `Draft a warm concise email to Morgan asking for feedback on the Vantage demo.`
5. Click `Vantage` after an answer to show the latest-turn receipt.

## User-Specific Data

- Calendar: `users/eden/state/calendar/events.json`
- Tasks: `users/eden/state/tasks/tasks.json`
- Active whiteboard: `users/eden/workspaces/vantage-demo-day-plan.md`
- Seed manifest: `users/eden/state/demo_manifest.json`

Calendar and task providers are user-specific by default in profile mode. Global files are restricted to explicit environment configuration.

## Demo Artifacts

- `users/eden/artifacts/email-draft-to-morgan-product-feedback.md`
- `users/eden/artifacts/email-draft-to-professor-kim-extension-request.md`
- `users/eden/artifacts/midterm-study-plan.md`
- `users/eden/artifacts/vantage-demo-one-page-brief.md`

## Demo Memories And Protocols

- `users/eden/memories/eden-prefers-concise-warm-email-drafts.md`
- `users/eden/memories/eden-current-academic-focus.md`
- `users/eden/memories/eden-vantage-demo-goals.md`
- `users/eden/concepts/daily-planning-protocol.md`
- `users/eden/concepts/vantage-demo-script.md`

## What To Show

- A schedule/day prompt opens the Today surface using Eden calendar and tasks.
- A task prompt opens the focus stack.
- A durable drafting prompt opens or updates the whiteboard.
- The `Vantage` button shows why the latest answer was generated: interpreted intent, context used, surfaces opened, write mode, assumptions, and whether anything changed.
