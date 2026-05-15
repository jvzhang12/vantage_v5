import { useId } from "react";

export function VantageMark({
  "aria-label": ariaLabel,
  className = "",
  size = 24,
  title,
}: {
  "aria-label"?: string;
  className?: string;
  size?: number | string;
  title?: string;
}) {
  const generatedTitleId = useId();
  const labelled = Boolean(ariaLabel || title);
  const titleId = title ? generatedTitleId : undefined;

  return (
    <svg
      aria-hidden={labelled ? undefined : true}
      aria-label={title ? undefined : ariaLabel}
      aria-labelledby={titleId}
      className={["vantage-mark", className].filter(Boolean).join(" ")}
      fill="none"
      focusable="false"
      height={size}
      role={labelled ? "img" : undefined}
      viewBox="0 0 64 64"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      {title ? <title id={titleId}>{title}</title> : null}
      <path
        d="M32 6 58 56H6L32 6Z"
        stroke="currentColor"
        strokeLinejoin="miter"
        strokeWidth="3"
      />
      <path
        d="M32 14 50 52H14L32 14Z"
        opacity="0.45"
        stroke="currentColor"
        strokeLinejoin="miter"
        strokeWidth="1.5"
      />
      <path d="M21 26H28L32 40 37 26H44L35 52H29L21 26Z" fill="currentColor" />
    </svg>
  );
}
