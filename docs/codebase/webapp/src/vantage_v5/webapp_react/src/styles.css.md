# `src/vantage_v5/webapp_react/src/styles.css`

Tailwind stylesheet for the React Vantage interface.

## Purpose

- Implements the premium graphite Vantage theme using Tailwind layers.
- Keeps the default state sparse, centered, and chat-first.
- Styles the latest-turn Vantage “Why this answer?” receipt without dashboard chrome.
- Defines the static Vantage mark sizing and shared color treatment.

## Coverage

- Top bar, static Vantage mark, greeting, composer, latest answer card, today briefing, calendar day/week, task focus, whiteboard, the Vantage inspection receipt, Working Memory role/resource panels, notices, login, and responsive layouts.
- Adds small-screen PWA polish for iPhone-sized Safari/home-screen use: `svh` viewport sizing, compact masthead/composer controls, readable 16px inputs, flexible latest-answer metadata, and single-column inspection/artifact layouts.
- Foregrounded surface views reserve space for the latest answer or pending state, the open surface, and sticky composer so normal chat replies stay visible while Whiteboard or operational surfaces remain foregrounded.
- Styles the generic pending-answer card and send-button spinner used while chat requests are in flight.
