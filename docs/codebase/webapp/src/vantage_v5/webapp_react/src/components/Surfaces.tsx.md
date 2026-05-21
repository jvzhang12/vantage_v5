# `src/vantage_v5/webapp_react/src/components/Surfaces.tsx`

React artifact and Vantage/Inspect surface renderers.

## Purpose

- Render summoned operational surfaces while keeping the composer available.
- Provide React equivalents for the first calendar/task/today/whiteboard/inspect slice.

## Coverage

- `TodayBriefingSurface`, `CalendarDaySurface`, `CalendarWeekSurface`, `TaskFocusSurface`, and `WhiteboardSurface`.
- Calendar week controls fetch a new week payload so visible artifact context follows the user view.
- The Vantage/Inspect route now delegates to `components/Inspection.tsx` for the full latest-turn “Why this answer?” receipt.
- The temporary Library placeholder no longer refers to the retired frontend fallback; Library parity is explicitly future React work while generated React remains the only product frontend path.
