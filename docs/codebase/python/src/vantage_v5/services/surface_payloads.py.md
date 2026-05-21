# `src/vantage_v5/services/surface_payloads.py`

Surface payload builder for Vantage operational artifacts.

## Purpose

- Convert deterministic `surface_invocation` decisions into renderable UI payloads.
- Combine calendar and task providers into the composite `today_briefing` surface.
- Keep operational surfaces read-only and source-referenced for Inspect.

## Key Classes / Functions

- `SurfacePayloadResult`: small DTO for `surface_payloads` and `active_surface_id`.
- `SurfacePayloadBuilder`: builds turn-level surface payloads from calendar/task providers and invocation metadata.
- `build_today_briefing_surface()`: combines calendar day, task focus, source refs, summary text, and focus suggestions.
- `build_calendar_surface()` and `build_task_surface()`: build single-domain operational surfaces.
- `build_focus_suggestions()`: pairs open calendar blocks with prioritized focus tasks.
- `resolve_surface_date()`: resolves simple date phrases or ISO dates from the user message using the configured app/user timezone.

## Notable Behavior

- Non-operational surfaces such as `chat` and `whiteboard` produce no operational payload.
- Operational surface dates are timezone-explicit, matching calendar/task proposal parsing rather than depending on the process `TZ`.
- Calendar plus task-focus schedule intents render as `today_briefing`.
- Calendar-only and task-only prompts keep separate `calendar_day` or `task_focus` payloads.
- Source refs include configured/read-only status and item counts so Inspect can explain what data was used.
