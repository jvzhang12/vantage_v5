# `src/vantage_v5/webapp_react/src/components/Core.tsx`

Reusable core UI components for the React Vantage shell.

## Purpose

- Provide the premium graphite application shell and default chat-only experience.
- Keep top chrome, composer, answer card, login, notices, and small shared controls reusable.
- Host the reusable static Vantage mark wrapper used by the topbar, composer, latest answer card, and auth screen.
- Mark the outer shell with a stable class so responsive layout rules can allow mobile whiteboard/chat content to scroll without changing desktop chrome.

## Components

- `AppShell`, `TopBar`, `VantageButton` behavior through the top-left button, `Profile` menu, `GreetingState`, `CommandComposer`, `LatestAnswerCard`, `SourcePill`, `NoticeRail`, `ConfirmDialog`, and `LoginScreen` with optional account creation plus an optional access-code field.
- `VantageGlyph` wraps the static `VantageMark` SVG so brand surfaces share one triangle-frame, currentColor mark at compact or composer scale.
