# `src/vantage_v5/webapp_react/src/components/VantageMark.tsx`

Reusable static SVG logo mark for Vantage.

## Purpose

- Render the simple triangle-frame Vantage mark as static SVG paths.
- Keep the mark lightweight, accessible when labelled, and reusable across app chrome and composer surfaces.
- Inherit color with `currentColor` so parent styles can choose the muted cyan accent without duplicating SVG assets.

## Key Behaviors

- Accepts `size`, `className`, `title`, and `aria-label` props.
- Renders decorative by default with `aria-hidden`; labelled uses standard SVG image semantics.
- Does not include animation, gradients, shadows, blur, raster images, or backend/product behavior.
