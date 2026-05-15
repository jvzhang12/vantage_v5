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
      <Facet points="13 3 28 18 26 25 18 20" />
      <Facet points="16 24 26 34 25 39 20 35" />
      <Facet points="25 22 31 33 30 42 22 29" />
      <Facet points="20 40 29 47 28 53 24 49" />
      <Facet points="29 48 32 58 31 64 25 53" />
      <Facet points="51 3 36 18 38 25 46 20" />
      <Facet points="48 24 38 34 39 39 44 35" />
      <Facet points="39 22 33 33 34 42 42 29" />
      <Facet points="44 40 35 47 36 53 40 49" />
      <Facet points="35 48 32 58 33 64 39 53" />
    </svg>
  );
}

function Facet({ points }: { points: string }) {
  return <polygon fill="currentColor" points={points} />;
}
