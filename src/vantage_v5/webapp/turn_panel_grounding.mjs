export function buildTurnPanelGroundingCopy({
  grounding = null,
  learnedCount = 0,
} = {}) {
  const rawGroundingLabel = String(grounding?.groundingLabel || "").trim() || "Idle";
  const groundingLabel = rawGroundingLabel === "Best Guess" ? "Intuitive Answer" : rawGroundingLabel;
  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : Number.isFinite(Number(grounding?.workingMemoryCount))
      ? Number(grounding.workingMemoryCount)
    : 0;
  const hasBroaderGrounding = Boolean(grounding?.hasBroaderGrounding);
  const hasGroundedContext = Boolean(grounding?.hasGroundedContext);
  const isBestGuess = Boolean(grounding?.isBestGuess);

  const metaParts = [];
  if (recallCount > 0) {
    metaParts.push(`Recall: ${recallCount} item${recallCount === 1 ? "" : "s"}`);
    if (hasBroaderGrounding || (groundingLabel && groundingLabel !== "Recall")) {
      metaParts.push(`Grounding: ${groundingLabel}`);
    }
  } else if (hasGroundedContext || isBestGuess) {
    metaParts.push("Recall: none");
    metaParts.push(`Grounding: ${groundingLabel}`);
  } else {
    metaParts.push("No grounded context surfaced yet");
  }

  if (learnedCount > 0) {
    metaParts.push(`Saved for Later: ${learnedCount}`);
  }

  return {
    groundingLabel,
    metaText: metaParts.join(" • "),
    answerDockLabel: hasBroaderGrounding
      ? groundingLabel
      : recallCount > 0
        ? (groundingLabel && groundingLabel !== "Recall" ? groundingLabel : "Recall")
        : hasGroundedContext
          ? groundingLabel
          : learnedCount > 0
            ? `${learnedCount} saved`
            : groundingLabel,
    turnIntentLabel: groundingLabel,
  };
}
