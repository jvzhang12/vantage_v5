# `src/vantage_v5/storage/experiments.py`

This module manages temporary experiment sessions as isolated storage roots. `ExperimentSession` is the path bundle for one session, and `ExperimentSessionManager` creates, discovers, and tears down session directories under the configured state area.

Starting a session creates a timestamped session ID, builds the session directory tree, ensures separate `concepts`, `memories`, `memory_trace`, `artifacts`, `workspaces`, and `traces` folders exist, writes a session whiteboard file, and seeds an active workspace JSON state file. The manager also writes `active_experiment.json` so the app can rehydrate the session later. Ending a session removes that marker and deletes the whole session root.

Experiment sessions now isolate both:

- `traces/` for JSON debug traces
- `memory_trace/` for markdown-backed recent searchable history

The main constraint is isolation. Experiment data lives under its own session root and should not leak into durable repository storage. That now includes experiment-scoped memory traces. If the active session marker exists but the session root has already disappeared, the manager cleans up the stale marker and returns no active session.
