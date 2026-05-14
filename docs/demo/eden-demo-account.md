# Eden Demo Account

Seeded by `scripts/seed_eden_demo.py` on 2026-05-14T07:55:15.971841+00:00.

## Account

- Username: `eden`
- Password: `vantage-demo-eden`
- Demo date anchor: `2026-05-14`

## Operational Data

- Calendar: `users/eden/state/calendar/events.json` with 9 events across school, Vantage, and personal calendars.
- Tasks: `users/eden/state/tasks/tasks.json` with 8 tasks, including one completed task hidden from focus.
- Active whiteboard: `users/eden/workspaces/vantage-demo-day-plan.md`

## Memories And Context

- `users/eden/memories/eden-prefers-concise-warm-email-drafts.md`
- `users/eden/memories/eden-current-academic-focus.md`
- `users/eden/memories/eden-vantage-demo-goals.md`
- `users/eden/concepts/daily-planning-protocol.md`
- `users/eden/concepts/vantage-demo-script.md`

## Demo Artifacts

- `users/eden/artifacts/email-draft-to-morgan-product-feedback.md`
- `users/eden/artifacts/email-draft-to-professor-kim-extension-request.md`
- `users/eden/artifacts/midterm-study-plan.md`
- `users/eden/artifacts/vantage-demo-one-page-brief.md`

## Suggested Demo Prompts

1. `What does my day look like?`
2. `When should I study for the midterm today?`
3. `Show my to-do list and what I should focus on.`
4. `Draft a warm concise email to Morgan asking for feedback on the Vantage demo.`
5. `Make a study plan for the midterm and put it on the whiteboard.`
6. Click `Vantage` after any answer to show the latest-turn receipt: intent, grounding, context used, surfaces opened, and read/write state.

## What This Demonstrates

- Chat-first default UI.
- Automatic Today surface invocation from day/schedule questions.
- Calendar plus task focus surfaces from planning requests.
- Whiteboard artifact behavior for durable drafts and plans.
- Memory/protocol recall for email and daily planning.
- The Vantage receipt explaining why the latest answer used particular context and surfaces.
