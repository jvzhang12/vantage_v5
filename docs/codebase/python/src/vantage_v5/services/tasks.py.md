# `src/vantage_v5/services/tasks.py`

Read-only local task provider for Vantage operational surfaces.

## Purpose

- Load tasks from a local JSON file before external task/reminder sync exists.
- Normalize common task fields into typed DTOs.
- Filter closed tasks out of the focus view.
- Group open tasks into Today surface buckets: `must_do_today`, `good_next`, `can_defer`, and `unscheduled`.

## Key Classes / Functions

- `TaskItem`: normalized task DTO with id, title, due date, status, priority, project, notes, optional duration, and source.
- `TaskFocus`: day-level grouped task payload with source metadata and summary counts.
- `LocalTaskProvider`: reads `tasks.json`, returns read-only focus payloads, and reports source status.
- `group_tasks_for_focus()`: pure grouping and sorting helper for focus-stack behavior.

## Local JSON Shape

The provider accepts either a list of tasks or an object with a `tasks` key. Supported fields include `id`, `title`, `due_date`/`dueDate`/`due`, `status`, `completed`, `priority`, `project`, `notes`, and `duration_minutes`.

## Notable Behavior

- Missing or malformed files return an empty task focus payload.
- Completed, cancelled, and archived tasks are excluded.
- Due and high-priority tasks land in `must_do_today`.
- Near-term tasks land in `good_next`; low-priority or later tasks land in `can_defer`.
- Unscheduled normal-priority tasks stay separate so the UI can show them without inventing due dates.
