# `src/vantage_v5/webapp_react/src/styles.css`

Tailwind stylesheet for the React Vantage interface.

## Purpose

- Implements the premium graphite Vantage theme using Tailwind layers.
- Keeps the default state sparse, centered, and chat-first.
- Styles the latest-turn Vantage “Why this answer?” receipt without dashboard chrome.

## Coverage

- Top bar, Vantage glyph, greeting, composer, latest answer card, today briefing, calendar day/week, task focus, whiteboard, the Vantage inspection receipt, notices, login, and responsive layouts.
- Adds small-screen PWA polish for iPhone-sized Safari/home-screen use: `svh` viewport sizing, compact masthead/composer controls, readable 16px inputs, flexible latest-answer metadata, and single-column inspection/artifact layouts.
