# `scripts/seed_eden_demo.py`

Seeds the local `eden` profile with a repeatable Vantage demo dataset.

## Purpose

- Populate user-scoped calendar and task provider files under `users/eden/state/`.
- Add demo memories, protocols/concepts, artifacts, and an active whiteboard workspace for product walkthroughs.
- Preserve any existing `eden` password while creating the account only if it is missing.

## Coverage

- Writes `users/eden/state/calendar/events.json` and `users/eden/state/tasks/tasks.json`.
- Writes demo memory, concept/protocol, artifact, active workspace, and manifest files.
- Generates `docs/demo/eden-demo-account.md` with demo prompts and a catalog of seeded content.
