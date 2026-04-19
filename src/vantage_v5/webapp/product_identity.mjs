import {
  normalizeLearnedItems,
  normalizeResponseMode,
} from "./turn_payloads.mjs";

function pluralize(word, count) {
  if (word === "branch") {
    return count === 1 ? "branch" : "branches";
  }
  return `${word}${count === 1 ? "" : "s"}`;
}

function recallCountFromPayload(payload) {
  const visibleRecallCount = Array.isArray(payload?.recall)
    ? payload.recall.length
    : Array.isArray(payload?.working_memory)
      ? payload.working_memory.length
      : 0;
  return normalizeResponseMode(payload?.response_mode, visibleRecallCount).recallCount;
}

function learnedKind(item) {
  const source = String(item?.source || "").trim().toLowerCase();
  const kind = String(item?.kind || "").trim().toLowerCase();
  const type = String(item?.type || "").trim().toLowerCase();
  if (source === "concept" || kind === "concept" || type === "concept") {
    return "concept";
  }
  if (source === "memory" || kind === "memory" || type === "memory") {
    return "memory";
  }
  if (source === "artifact" || kind === "artifact" || type === "artifact" || type === "scenario_comparison") {
    return "artifact";
  }
  return "item";
}

function learnedEvidenceLabel(items) {
  if (!items.length) {
    return null;
  }
  const kinds = items.map((item) => learnedKind(item));
  const first = kinds[0];
  const sameKind = kinds.every((kind) => kind === first);
  const labelKind = sameKind ? pluralize(first, items.length) : pluralize("item", items.length);
  return `Learned ${items.length} ${labelKind}`;
}

function groundingEvidenceLabel(payload) {
  const responseMode = normalizeResponseMode(payload?.response_mode, recallCountFromPayload(payload));
  const responseModeLabel = responseModeEvidenceLabel(responseMode, payload);
  if (responseModeLabel) {
    return responseModeLabel;
  }
  return null;
}

export function describeResponseModeLabel(responseMode = null, recallCount = 0) {
  const kind = String(responseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(responseMode?.groundingMode || responseMode?.grounding_mode || "").trim().toLowerCase();
  const contextSources = responseModeContextSources(responseMode);
  if (!kind || kind === "idle") {
    return "";
  }
  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "Best Guess";
  }
  if (groundingMode === "whiteboard") {
    return "Whiteboard";
  }
  if (groundingMode === "recent_chat") {
    return "Recent Chat";
  }
  if (groundingMode === "pending_whiteboard") {
    return "Prior Whiteboard";
  }
  if (groundingMode === "mixed_context") {
    const derivedLabel = describeMixedContextLabel(contextSources);
    const responseModeLabel = String(responseMode?.label || "").trim();
    return derivedLabel || (responseModeLabel && responseModeLabel !== "Mixed Context" ? responseModeLabel : "Mixed Context");
  }
  if (groundingMode === "recall" || groundingMode === "working_memory") {
    return "Recall";
  }
  const label = String(responseMode?.label || "").trim();
  return label || (recallCount > 0 ? `${recallCount} recalled` : "");
}

export function deriveTurnGrounding({
  responseMode = null,
  recallItems = [],
  workingMemoryItems = [],
  learnedItems = [],
} = {}) {
  const visibleRecallCount = Array.isArray(recallItems) && recallItems.length
    ? recallItems.length
    : Array.isArray(workingMemoryItems)
      ? workingMemoryItems.length
      : 0;
  const learnedCount = Array.isArray(learnedItems) ? learnedItems.length : 0;
  const normalizedResponseMode = responseMode && typeof responseMode === "object"
    ? normalizeResponseMode(responseMode, visibleRecallCount)
    : normalizeResponseMode(null, visibleRecallCount);
  const recallCount = Number.isFinite(Number(normalizedResponseMode?.recallCount))
    ? Number(normalizedResponseMode.recallCount)
    : Number.isFinite(Number(normalizedResponseMode?.workingMemoryCount))
      ? Number(normalizedResponseMode.workingMemoryCount)
      : visibleRecallCount;
  const groundingLabel = describeResponseModeLabel(normalizedResponseMode, recallCount) || "Idle";
  const responseKind = String(normalizedResponseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(normalizedResponseMode?.groundingMode || "").trim().toLowerCase();
  const groundingSources = Array.isArray(normalizedResponseMode?.contextSources)
    ? normalizedResponseMode.contextSources
    : Array.isArray(normalizedResponseMode?.groundingSources)
      ? normalizedResponseMode.groundingSources
      : [];
  const isIdle = responseKind === "idle";
  const isBestGuess = responseKind === "best_guess";
  const hasGroundedContext = responseKind === "grounded";
  const hasBroaderGrounding = hasGroundedContext && (
    ["whiteboard", "recent_chat", "pending_whiteboard", "mixed_context"].includes(groundingMode)
    || groundingSources.some((source) => normalizeContextSourceName(source) !== "recall")
  );

  return {
    responseMode: normalizedResponseMode,
    groundingLabel,
    recallCount,
    workingMemoryCount: recallCount,
    visibleRecallCount,
    visibleWorkingMemoryCount: visibleRecallCount,
    learnedCount,
    groundingMode,
    groundingSources,
    hasBroaderGrounding,
    hasGroundedContext,
    isBestGuess,
    isIdle,
  };
}

function responseModeEvidenceLabel(responseMode, payload) {
  const kind = String(responseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(responseMode?.groundingMode || responseMode?.grounding_mode || "").trim().toLowerCase();
  const count = recallCountFromPayload(payload);

  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "Best Guess";
  }
  if (groundingMode === "recall" || groundingMode === "working_memory") {
    return count > 0 ? `Used ${count} recalled ${pluralize("item", count)}` : "Recall";
  }
  if (groundingMode === "whiteboard") {
    return "Whiteboard";
  }
  if (groundingMode === "recent_chat") {
    return "Recent Chat";
  }
  if (groundingMode === "pending_whiteboard") {
    return "Prior Whiteboard";
  }
  if (groundingMode === "mixed_context") {
    return describeResponseModeLabel(responseMode, count);
  }
  if (kind === "grounded") {
    return count > 0 ? `Used ${count} recalled ${pluralize("item", count)}` : (String(responseMode?.label || "").trim() || "Recall");
  }
  return null;
}

function responseModeContextSources(responseMode = null) {
  if (Array.isArray(responseMode?.contextSources)) {
    return responseMode.contextSources.map(normalizeContextSourceName);
  }
  if (Array.isArray(responseMode?.context_sources)) {
    return responseMode.context_sources.map(normalizeContextSourceName);
  }
  if (Array.isArray(responseMode?.groundingSources)) {
    return responseMode.groundingSources.map(normalizeContextSourceName);
  }
  if (Array.isArray(responseMode?.grounding_sources)) {
    return responseMode.grounding_sources.map(normalizeContextSourceName);
  }
  return [];
}

function normalizeContextSourceName(source) {
  const normalizedSource = String(source || "").trim().toLowerCase();
  if (normalizedSource === "working_memory") {
    return "recall";
  }
  return normalizedSource;
}

function describeMixedContextLabel(contextSources = []) {
  const labels = contextSources
    .map((source) => describeContextSourceLabel(source))
    .filter(Boolean);
  if (!labels.length) {
    return "";
  }
  return labels.join(" + ");
}

function describeContextSourceLabel(source) {
  switch (String(source || "").trim().toLowerCase()) {
    case "recall":
    case "working_memory":
      return "Recall";
    case "whiteboard":
      return "Whiteboard";
    case "recent_chat":
      return "Recent Chat";
    case "pending_whiteboard":
      return "Prior Whiteboard";
    default:
      return "";
  }
}

export function buildGuidedInspectionSummary({
  responseMode = null,
  scenarioLab = null,
  recallCount = 0,
  recalledCount = 0,
  learnedCount = 0,
  libraryCount = 0,
  pinnedTitle = "",
} = {}) {
  const normalizedRecallCount = Number.isFinite(Number(recallCount))
    ? Number(recallCount)
    : Number.isFinite(Number(recalledCount))
      ? Number(recalledCount)
      : 0;
  const parts = [];
  if (scenarioLab) {
    const branchCount = Array.isArray(scenarioLab.branches) ? scenarioLab.branches.length : 0;
    parts.push(
      scenarioLab.status === "failed"
        ? "Scenario Lab: fallback"
        : branchCount
          ? `Scenario Lab: ${branchCount} ${pluralize("branch", branchCount)}`
          : "Scenario Lab: ready",
    );
  }
  const responseModeLabel = describeResponseModeLabel(responseMode, normalizedRecallCount);
  if (normalizedRecallCount > 0) {
    parts.push(`Recall: ${normalizedRecallCount} ${pluralize("item", normalizedRecallCount)}`);
    if (responseModeLabel && responseModeLabel !== "Recall") {
      parts.push(`Grounding: ${responseModeLabel}`);
    }
  } else if (responseModeLabel) {
    parts.push(`Grounding: ${responseModeLabel}`);
  } else {
    parts.push("Recall: none surfaced yet");
  }
  parts.push(`Learned: ${learnedCount ? `${learnedCount} item${learnedCount === 1 ? "" : "s"}` : "nothing new yet"}`);
  parts.push(`Library: ${libraryCount} item${libraryCount === 1 ? "" : "s"}`);
  if (pinnedTitle) {
    parts.push(`Pinned: ${pinnedTitle}`);
  }
  return parts.join(" • ");
}

export function buildMemoryTraceSummary({
  traceNotes = [],
  memoryTraceRecord = null,
} = {}) {
  const traceCount = Array.isArray(traceNotes) ? traceNotes.length : 0;
  const hasRecord = Boolean(memoryTraceRecord && typeof memoryTraceRecord === "object" && memoryTraceRecord.id);
  if (traceCount > 0 && hasRecord) {
    const scopeLabel = String(memoryTraceRecord.scope || "").trim().toLowerCase() === "experiment"
      ? "experiment-scoped"
      : "durable";
    const article = scopeLabel === "experiment-scoped" ? "an" : "a";
    return `Recent history contributed ${traceCount} recalled item${traceCount === 1 ? "" : "s"} to Recall. This turn also left ${article} ${scopeLabel} Memory Trace record.`;
  }
  if (traceCount > 0) {
    return `Recent history contributed ${traceCount} recalled item${traceCount === 1 ? "" : "s"} to Recall.`;
  }
  if (hasRecord) {
    const scopeLabel = String(memoryTraceRecord.scope || "").trim().toLowerCase() === "experiment"
      ? "experiment-scoped"
      : "durable";
    const article = scopeLabel === "experiment-scoped" ? "an" : "a";
    return `No recalled items came from recent history for this answer, but this turn still left ${article} ${scopeLabel} Memory Trace record for future continuity.`;
  }
  return "No Memory Trace details are available for this turn yet.";
}

function summarizeReasoningText(text, fallback, maxLength = 180) {
  const cleaned = String(text || "").trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return fallback;
  }
  const sentence = cleaned.match(/^[^.?!]+[.?!]?/);
  const summary = (sentence ? sentence[0] : cleaned).slice(0, maxLength);
  return summary.endsWith(".") ? summary : `${summary}.`;
}

function countReasoningCandidates({
  candidateConcepts = [],
  candidateSavedNotes = [],
  candidateTraceNotes = [],
  candidateVaultNotes = [],
} = {}) {
  const conceptCount = Array.isArray(candidateConcepts) ? candidateConcepts.length : 0;
  const savedCount = Array.isArray(candidateSavedNotes) ? candidateSavedNotes.length : 0;
  const traceCount = Array.isArray(candidateTraceNotes) ? candidateTraceNotes.length : 0;
  const vaultCount = Array.isArray(candidateVaultNotes) ? candidateVaultNotes.length : 0;
  return {
    conceptCount,
    savedCount,
    traceCount,
    vaultCount,
    totalCount: conceptCount + savedCount + traceCount + vaultCount,
  };
}

function cloneReasoningItems(items = []) {
  return Array.isArray(items) ? items.filter(Boolean).map((item) => ({ ...item })) : [];
}

function annotateCandidateItems(items = [], recallIds = new Set()) {
  return cloneReasoningItems(items).map((item) => ({
    ...item,
    reasoningStatusLabel: recallIds.has(String(item?.id || "").trim())
      ? "selected into recall"
      : "considered but not selected",
  }));
}

function describeReasoningRoute(interpretation, grounding) {
  const pathMode = String(interpretation?.mode || "").trim().toLowerCase();
  const routeLabel = pathMode === "scenario_lab" ? "Scenario Lab" : "Chat";
  const reason = summarizeReasoningText(
    interpretation?.reason || interpretation?.note || "",
    `Navigator routed this turn through ${routeLabel}.`,
  );
  const whiteboardMode = String(interpretation?.resolvedWhiteboardMode || "").trim().toLowerCase();
  const whiteboardLabel = whiteboardMode === "draft"
    ? "Draft in whiteboard"
    : whiteboardMode === "offer"
      ? "Invite whiteboard"
      : whiteboardMode === "chat"
        ? "Keep in chat"
        : whiteboardMode === "auto"
          ? "Auto"
          : "";
  const continuityLabel = interpretation?.preserveSelectedRecord === true
    ? "Preserved selected context"
    : "";
  const pieces = [reason];
  if (whiteboardLabel) {
    pieces.push(`Whiteboard: ${whiteboardLabel}.`);
  }
  if (continuityLabel) {
    pieces.push(`${continuityLabel}.`);
  }
  if (grounding?.groundingLabel && grounding.groundingLabel !== "Idle") {
    pieces.push(`Grounding: ${grounding.groundingLabel}.`);
  }
  return pieces.join(" ").replace(/\s+/g, " ").trim();
}

function describeReasoningRequest(userMessage) {
  return summarizeReasoningText(
    userMessage,
    "No user request was captured for this turn yet.",
    180,
  );
}

function describeReasoningCandidates(candidateCounts) {
  const totalCount = Number(candidateCounts?.totalCount || 0);
  if (!totalCount) {
    return "No candidate context was surfaced before vetting.";
  }
  const parts = [
    `${totalCount} candidate item${totalCount === 1 ? "" : "s"} ${totalCount === 1 ? "was" : "were"} considered before vetting`,
  ];
  const detailParts = [];
  if (candidateCounts.conceptCount) {
    detailParts.push(`${candidateCounts.conceptCount} concept${candidateCounts.conceptCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.savedCount) {
    detailParts.push(`${candidateCounts.savedCount} memory${candidateCounts.savedCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.traceCount) {
    detailParts.push(`${candidateCounts.traceCount} memory trace item${candidateCounts.traceCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.vaultCount) {
    detailParts.push(`${candidateCounts.vaultCount} reference note${candidateCounts.vaultCount === 1 ? "" : "s"}`);
  }
  if (detailParts.length) {
    parts.push(`(${detailParts.join(", ")})`);
  }
  return parts.join(" ") + ".";
}

function describeReasoningRecall(grounding, recallItems = []) {
  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : Array.isArray(recallItems)
      ? recallItems.length
      : 0;
  if (!recallCount) {
    return "No recalled items were selected into Recall.";
  }
  return `${recallCount} recalled item${recallCount === 1 ? "" : "s"} ${recallCount === 1 ? "was" : "were"} selected into Recall.`;
}

function describeReasoningWorkingMemory(grounding) {
  if (grounding?.isBestGuess) {
    return "In scope for generation: no grounded context (Best Guess).";
  }
  if (grounding?.groundingLabel && grounding.groundingLabel !== "Idle") {
    return `In scope for generation: ${grounding.groundingLabel}.`;
  }
  return "Working Memory was not populated for this turn yet.";
}

export function buildReasoningPathInspection({
  userMessage = "",
  interpretation = null,
  responseMode = null,
  candidateConcepts = [],
  candidateSavedNotes = [],
  candidateTraceNotes = [],
  candidateVaultNotes = [],
  recallItems = [],
  learnedItems = [],
  traceNotes = [],
  workspaceContextScope = "excluded",
  workspaceUpdate = null,
  memoryTraceRecord = null,
  scenarioLab = null,
  graphAction = null,
} = {}) {
  const grounding = deriveTurnGrounding({
    responseMode,
    recallItems,
    learnedItems,
  });
  const candidateCounts = countReasoningCandidates({
    candidateConcepts,
    candidateSavedNotes,
    candidateTraceNotes,
    candidateVaultNotes,
  });
  const recallIds = new Set(
    Array.isArray(recallItems)
      ? recallItems.map((item) => String(item?.id || "").trim()).filter(Boolean)
      : [],
  );
  const request = describeReasoningRequest(userMessage);
  const route = describeReasoningRoute(interpretation, grounding);
  const candidates = describeReasoningCandidates(candidateCounts);
  const recall = describeReasoningRecall(grounding, recallItems);
  const workingMemory = describeReasoningWorkingMemory(grounding, scenarioLab);
  const workingMemoryScope = buildWorkingMemoryScopeSummary({
    grounding,
    interpretation,
    workspaceContextScope,
    recallItems,
    traceNotes,
  });
  const requestStage = {
    key: "request",
    label: "Request",
    text: request,
    step: "Step 1",
    meta: normalizeStageMeta([
      interpretation?.mode ? { label: "Path", value: humanizePathMode(interpretation.mode) } : null,
    ]),
    detail: {
      summary: request,
      notes: normalizeStageMeta([
        { label: "Full request", value: String(userMessage || "").trim() || "No user request was captured for this turn yet." },
      ]),
    },
  };
  const routeStage = {
    key: "route",
    label: "Route",
    text: route,
    step: "Step 2",
    meta: normalizeStageMeta([
      interpretation?.mode ? { label: "Path", value: humanizePathMode(interpretation.mode) } : null,
      interpretation?.resolvedWhiteboardMode
        ? { label: "Whiteboard", value: humanizeWhiteboardMode(interpretation.resolvedWhiteboardMode) }
        : null,
      interpretation?.requestedWhiteboardMode
        ? { label: "Requested", value: humanizeWhiteboardMode(interpretation.requestedWhiteboardMode) }
        : null,
      interpretation?.whiteboardModeSource
        ? { label: "Decision Source", value: humanizeWhiteboardModeSource(interpretation.whiteboardModeSource) }
        : null,
      interpretation?.preserveSelectedRecord === true
        ? { label: "Continuity", value: interpretation.selectedRecordReason || "Preserved selected context" }
        : null,
      Number.isFinite(Number(interpretation?.confidence)) && Number(interpretation.confidence) > 0
        ? { label: "Confidence", value: `${Math.round(Number(interpretation.confidence) * 100)}%` }
        : null,
    ]),
    detail: {
      summary: route,
      notes: normalizeStageMeta([
        { label: "Navigator reason", value: String(interpretation?.reason || interpretation?.note || "").trim() || "No navigator reason was returned for this turn." },
        interpretation?.preserveSelectedRecord === true
          ? { label: "Continuity rationale", value: interpretation.selectedRecordReason || "Selected context was preserved for continuity." }
          : null,
      ]),
    },
  };
  const candidateStage = {
    key: "candidate-context",
    label: "Candidate context",
    text: candidates,
    step: "Step 3",
    meta: normalizeStageMeta([
      candidateCounts.totalCount
        ? { label: "Candidates", value: `${candidateCounts.totalCount} item${candidateCounts.totalCount === 1 ? "" : "s"}` }
        : null,
    ]),
    detail: {
      summary: candidateCounts.totalCount
        ? "These were the candidate items pulled up before vetting narrowed them down."
        : "No candidate context was surfaced before vetting.",
      groups: [
        {
          label: "Concept candidates",
          items: annotateCandidateItems(candidateConcepts, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No concept candidates were pulled up.",
        },
        {
          label: "Saved note candidates",
          items: annotateCandidateItems(candidateSavedNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No saved-note candidates were pulled up.",
        },
        {
          label: "Memory Trace candidates",
          items: annotateCandidateItems(candidateTraceNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No memory-trace candidates were pulled up.",
        },
        {
          label: "Reference note candidates",
          items: annotateCandidateItems(candidateVaultNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No reference-note candidates were pulled up.",
        },
      ],
    },
  };
  const recallStage = {
    key: "recall",
    label: "Recall",
    text: recall,
    step: "Step 4",
    meta: normalizeStageMeta([
      { label: "Recall", value: grounding.recallCount ? `${grounding.recallCount} item${grounding.recallCount === 1 ? "" : "s"}` : "None" },
    ]),
    detail: {
      summary: grounding.recallCount
        ? "These recalled items made it through vetting and entered Recall for this answer."
        : "No recalled items were selected into Recall.",
      groups: [
        {
          label: "Selected recall",
          items: cloneReasoningItems(recallItems),
          context: "reasoning-recall",
          emptyMessage: "No recalled items were selected for this turn.",
        },
      ],
    },
  };
  const traceCount = Array.isArray(traceNotes) ? traceNotes.length : 0;
  const hasTraceRecord = Boolean(memoryTraceRecord && typeof memoryTraceRecord === "object" && memoryTraceRecord.id);
  const workingMemoryStage = {
    key: "working-memory",
    label: "Working Memory",
    text: workingMemory,
    step: "Step 5",
    meta: normalizeStageMeta([
      !grounding.isIdle ? { label: "Grounding", value: grounding.groundingLabel } : null,
      !grounding.isBestGuess && grounding.responseMode?.contextSources?.length
        ? { label: "Sources", value: grounding.responseMode.contextSources.map(describeContextSourceLabel).filter(Boolean).join(", ") }
        : null,
      traceCount > 0 ? { label: "Memory Trace", value: `${traceCount} item${traceCount === 1 ? "" : "s"}` } : null,
      String(workspaceContextScope || "").trim().toLowerCase() !== "excluded"
        ? { label: "Whiteboard Scope", value: humanizeWorkspaceContextScope(workspaceContextScope) }
        : null,
    ]),
    detail: {
      summary: `${workingMemoryScope.summary} This describes scope, not causal attribution.`,
      notes: workingMemoryScope.scopeRows,
      scopeRows: workingMemoryScope.scopeTableRows,
    },
  };
  const outcomeSummary = buildOutcomeSummary({
    grounding,
    learnedCount: Array.isArray(learnedItems) ? learnedItems.length : 0,
    scenarioLab,
    branchCount: Array.isArray(scenarioLab?.branches) ? scenarioLab.branches.length : 0,
    hasComparisonArtifact: Boolean(
      scenarioLab?.comparisonArtifact
      || (scenarioLab?.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"),
    ),
    workspaceUpdate,
    hasTraceRecord,
    graphAction,
  });
  const outcomeStage = {
    key: "outcome",
    label: "Outcome",
    text: outcomeSummary,
    step: "Step 6",
    meta: normalizeStageMeta([
      !grounding.isIdle ? { label: "Grounding", value: grounding.groundingLabel } : null,
      { label: "Learned", value: Array.isArray(learnedItems) && learnedItems.length ? `${learnedItems.length} item${learnedItems.length === 1 ? "" : "s"}` : "Nothing learned" },
      hasTraceRecord ? { label: "Memory Trace", value: "Recorded" } : null,
    ]),
    detail: {
      summary: outcomeSummary,
      notes: normalizeStageMeta([
        workspaceUpdate?.status ? { label: "Workspace", value: workspaceUpdate.status.replace(/_/g, " ") } : null,
        hasTraceRecord ? { label: "Memory Trace", value: String(memoryTraceRecord?.title || "Recorded") } : null,
        graphAction ? { label: "Durable change", value: "Yes" } : null,
      ]),
      groups: [
        {
          label: "Learned",
          items: cloneReasoningItems(learnedItems),
          context: "learned",
          emptyMessage: "No durable item was created by this turn.",
        },
        ...(hasTraceRecord
          ? [{
              label: "Memory Trace",
              items: [{ ...memoryTraceRecord }],
              context: "trace",
              emptyMessage: "No trace record was captured for this turn.",
            }]
          : []),
      ],
      workspaceUpdate,
      graphAction,
    },
  };
  const stages = [
    requestStage,
    routeStage,
    candidateStage,
    recallStage,
    workingMemoryStage,
    outcomeStage,
  ];

  const visible = Boolean(
    String(userMessage || "").trim()
    || interpretation
    || candidateCounts.totalCount
    || grounding.recallCount
    || Array.isArray(learnedItems) && learnedItems.length,
  );
  const summaryPieces = [route];
  if (candidateCounts.totalCount > 0) {
    summaryPieces.push(`${candidateCounts.totalCount} candidate item${candidateCounts.totalCount === 1 ? "" : "s"} ${candidateCounts.totalCount === 1 ? "was" : "were"} considered before vetting.`);
  }
  if (grounding.recallCount > 0) {
    summaryPieces.push(`${grounding.recallCount} recalled item${grounding.recallCount === 1 ? "" : "s"} entered Working Memory.`);
  }

  return {
    visible,
    label: "Reasoning Path",
    summary: summaryPieces.join(" ").replace(/\s+/g, " ").trim(),
    groundingLabel: deriveTurnGrounding({
      responseMode,
      recallItems,
      learnedItems,
    }).groundingLabel,
    stages,
  };
}

export function buildMemoryTraceInspectionSummary({
  memoryTraceRecord = null,
  recalledItems = [],
} = {}) {
  const recalledTraceCount = Array.isArray(recalledItems)
    ? recalledItems.filter((item) => String(item?.source || "").trim().toLowerCase() === "memory_trace").length
    : 0;
  const traceTitle = String(memoryTraceRecord?.title || "").trim() || "Turn Trace";
  const traceCard = String(memoryTraceRecord?.card || "").trim();
  const recentHistoryText = recalledTraceCount > 0
    ? `Recent history contributed ${recalledTraceCount} recalled ${pluralize("item", recalledTraceCount)} to Recall.`
    : "Recent history did not contribute to Recall.";
  const traceRecordText = memoryTraceRecord
    ? `Created trace: ${traceTitle}${traceCard ? ` - ${traceCard}` : ""}.`
    : "No trace record was returned for this turn.";

  return {
    visible: Boolean(memoryTraceRecord || recalledTraceCount > 0),
    label: "Memory Trace",
    summary: `${recentHistoryText} ${traceRecordText}`,
    metaText: recalledTraceCount > 0
      ? `Recent history: ${recalledTraceCount} ${pluralize("item", recalledTraceCount)}`
      : "Recent history: none",
    traceTitle,
    recalledTraceCount,
  };
}

function humanizePathMode(mode) {
  switch (String(mode || "").trim().toLowerCase()) {
    case "scenario_lab":
      return "Scenario Lab";
    case "chat":
      return "Chat";
    default:
      return "Chat";
  }
}

function humanizeWhiteboardMode(mode) {
  switch (String(mode || "").trim().toLowerCase()) {
    case "chat":
      return "Chat";
    case "offer":
      return "Offer";
    case "draft":
      return "Draft";
    case "auto":
      return "Auto";
    default:
      return "";
  }
}

function humanizeWorkspaceContextScope(scope) {
  switch (String(scope || "").trim().toLowerCase()) {
    case "visible":
      return "Visible";
    case "pinned":
      return "Pinned";
    case "requested":
      return "Requested";
    case "auto":
      return "Auto";
    case "excluded":
    default:
      return "Excluded";
  }
}

function normalizeStageMeta(meta = []) {
  return meta.filter((item) => item && item.label && item.value);
}

function buildWorkingMemoryScopeSummary({
  grounding,
  interpretation = null,
  workspaceContextScope = "excluded",
  recallItems = [],
  traceNotes = [],
} = {}) {
  const recallCount = Number(grounding?.recallCount || 0);
  const traceCount = Array.isArray(recallItems)
    ? recallItems.filter((item) => String(item?.source || "").trim().toLowerCase() === "memory_trace").length
    : 0;
  const contextSources = responseModeContextSources(grounding?.responseMode);
  const additionalContextLabels = contextSources
    .filter((source) => source !== "recall")
    .map((source) => describeContextSourceLabel(source))
    .filter(Boolean);
  const whiteboardScope = String(workspaceContextScope || "").trim().toLowerCase();
  const hasWhiteboardInScope = contextSources.includes("whiteboard");
  const hasRecentChatInScope = contextSources.includes("recent_chat");
  const hasPriorWhiteboardInScope = contextSources.includes("pending_whiteboard");

  const parts = [];
  parts.push("This is the bounded context that was in scope for generation.");
  if (recallCount > 0) {
    parts.push(`Recall contributed ${recallCount} item${recallCount === 1 ? "" : "s"}.`);
  } else {
    parts.push("No recalled items were surfaced for this turn.");
  }
  if (additionalContextLabels.length) {
    parts.push(`Additional context in scope: ${additionalContextLabels.join(", ")}.`);
  } else if (grounding?.isBestGuess) {
    parts.push("The answer was generated as a best guess without surfaced recall.");
  }
  if (traceCount > 0) {
    parts.push(`Memory Trace contributed ${traceCount} recalled item${traceCount === 1 ? "" : "s"}.`);
  }
  if (whiteboardScope !== "excluded") {
    parts.push(`Whiteboard scope: ${humanizeWorkspaceContextScope(workspaceContextScope)}.`);
  }

  const scopeTableRows = [
    {
      label: "User request",
      status: "Included",
      detail: "The current user message is always part of the turn input.",
    },
    {
      label: "Recall",
      status: recallCount > 0 ? "Included" : "Excluded",
      detail: recallCount > 0
        ? `${recallCount} recalled item${recallCount === 1 ? "" : "s"} entered Working Memory.`
        : "No recalled items were selected into Recall.",
      count: recallCount,
    },
    {
      label: "Whiteboard",
      status: hasWhiteboardInScope ? "Included" : "Excluded",
      detail: hasWhiteboardInScope
        ? whiteboardScope !== "excluded"
          ? `Whiteboard was in scope for generation. Scope hint: ${humanizeWorkspaceContextScope(workspaceContextScope)}.`
          : "Whiteboard was listed as an in-scope source by the response mode."
        : whiteboardScope !== "excluded"
          ? `Whiteboard was visible with scope hint ${humanizeWorkspaceContextScope(workspaceContextScope)}, but it was not included in generation scope.`
          : "No whiteboard content was in scope.",
      scope: whiteboardScope !== "excluded" ? humanizeWorkspaceContextScope(workspaceContextScope) : "",
    },
    {
      label: "Recent chat",
      status: hasRecentChatInScope ? "Included" : "Excluded",
      detail: hasRecentChatInScope
        ? "The recent conversation was part of the bounded context."
        : "Recent chat was not surfaced for this answer.",
    },
    ...(hasPriorWhiteboardInScope
      ? [{
          label: "Prior whiteboard",
          status: "Included",
          detail: "The previous whiteboard state was carried into the turn.",
        }]
      : []),
    ...(typeof interpretation?.preserveSelectedRecord === "boolean"
      ? [{
          label: "Selected context preserved",
          status: interpretation.preserveSelectedRecord ? "Included" : "Excluded",
          detail: interpretation.preserveSelectedRecord
            ? interpretation?.selectedRecordReason || "A selected record stayed in scope for continuity."
            : "No selected record was preserved.",
        }]
      : []),
    {
      label: "Memory Trace contribution",
      status: traceCount > 0 ? "Included" : "Excluded",
      detail: traceCount > 0
        ? `${traceCount} traced recalled item${traceCount === 1 ? "" : "s"} entered Recall.`
        : "No Memory Trace items were in scope for generation.",
      count: traceCount,
    },
  ];
  const scopeRows = normalizeStageMeta([
    { label: "User request", value: "Included" },
    { label: "Recall", value: recallCount ? `${recallCount} item${recallCount === 1 ? "" : "s"}` : "0 items" },
    { label: "Whiteboard", value: hasWhiteboardInScope ? "Included" : "Excluded" },
    whiteboardScope !== "excluded"
      ? { label: "Whiteboard scope hint", value: humanizeWorkspaceContextScope(workspaceContextScope) }
      : null,
    { label: "Recent chat", value: hasRecentChatInScope ? "Included" : "Excluded" },
    ...(hasPriorWhiteboardInScope
      ? [{ label: "Prior whiteboard", value: "Included" }]
      : []),
    ...(typeof interpretation?.preserveSelectedRecord === "boolean"
      ? [{ label: "Selected context preserved", value: interpretation.preserveSelectedRecord ? "Included" : "Excluded" }]
      : []),
    { label: "Memory Trace contribution", value: traceCount ? `${traceCount} item${traceCount === 1 ? "" : "s"}` : "None" },
  ]);

  return {
    summary: parts.join(" "),
    meta: normalizeStageMeta([
      { label: "Recall", value: recallCount ? `${recallCount} item${recallCount === 1 ? "" : "s"}` : "None" },
      additionalContextLabels.length
        ? { label: "Additional Context In Scope", value: additionalContextLabels.join(", ") }
        : null,
      String(workspaceContextScope || "").trim().toLowerCase() !== "excluded"
        ? { label: "Whiteboard Scope", value: humanizeWorkspaceContextScope(workspaceContextScope) }
        : null,
      traceCount > 0
        ? { label: "Memory Trace", value: `${traceCount} item${traceCount === 1 ? "" : "s"}` }
        : null,
    ]),
    scopeRows,
    scopeTableRows,
  };
}

export function buildReasoningPathStages({
  userMessage = "",
  interpretation = null,
  responseMode = null,
  recallItems = [],
  learnedItems = [],
  traceNotes = [],
  workspaceContextScope = "excluded",
  workspaceUpdate = null,
  memoryTraceRecord = null,
  scenarioLab = null,
  graphAction = null,
} = {}) {
  const grounding = deriveTurnGrounding({
    responseMode,
    recallItems,
    learnedItems,
  });
  const requestText = String(userMessage || "").trim() || "No user request was captured for this turn.";
  const branchCount = Array.isArray(scenarioLab?.branches) ? scenarioLab.branches.length : 0;
  const hasComparisonArtifact = Boolean(
    scenarioLab?.comparisonArtifact
    || (scenarioLab?.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"),
  );
  const workingMemoryScope = buildWorkingMemoryScopeSummary({
    grounding,
    interpretation,
    workspaceContextScope,
    recallItems,
    traceNotes,
  });
  const learnedCount = Array.isArray(learnedItems) ? learnedItems.length : 0;
  const hasTraceRecord = Boolean(memoryTraceRecord && typeof memoryTraceRecord === "object" && memoryTraceRecord.id);

  const stages = [
    {
      id: "request",
      step: "Step 1",
      label: "Request",
      summary: requestText,
      meta: normalizeStageMeta([
        interpretation?.mode ? { label: "Path", value: humanizePathMode(interpretation.mode) } : null,
      ]),
    },
    {
      id: "interpretation",
      step: "Step 2",
      label: "Interpretation",
      summary: String(interpretation?.reason || "").trim()
        || "Vantage chose a path for this turn based on the current message and local context.",
      meta: normalizeStageMeta([
        { label: "Path", value: humanizePathMode(interpretation?.mode) },
        interpretation?.resolvedWhiteboardMode
          ? { label: "Whiteboard", value: humanizeWhiteboardMode(interpretation.resolvedWhiteboardMode) }
          : null,
        interpretation?.requestedWhiteboardMode
          ? { label: "Requested", value: humanizeWhiteboardMode(interpretation.requestedWhiteboardMode) }
          : null,
        interpretation?.whiteboardModeSource
          ? { label: "Decision Source", value: humanizeWhiteboardModeSource(interpretation.whiteboardModeSource) }
          : null,
        interpretation?.preserveSelectedRecord === true
          ? { label: "Continuity", value: interpretation.selectedRecordReason || "Preserved selected context" }
          : null,
        Number.isFinite(Number(interpretation?.confidence)) && Number(interpretation.confidence) > 0
          ? { label: "Confidence", value: `${Math.round(Number(interpretation.confidence) * 100)}%` }
          : null,
      ]),
    },
    {
      id: "working-memory",
      step: "Step 3",
      label: "Working Memory",
      summary: workingMemoryScope.summary,
      meta: workingMemoryScope.meta,
    },
    {
      id: "outcome",
      step: "Step 4",
      label: "Outcome",
      summary: buildOutcomeSummary({
        grounding,
        learnedCount,
        scenarioLab,
        branchCount,
        hasComparisonArtifact,
        workspaceUpdate,
        hasTraceRecord,
        graphAction,
      }),
      meta: normalizeStageMeta([
        !grounding.isIdle
          ? { label: "Grounding", value: grounding.groundingLabel }
          : null,
        { label: "Learned", value: learnedCount ? `${learnedCount} item${learnedCount === 1 ? "" : "s"}` : "Nothing learned" },
        hasTraceRecord ? { label: "Memory Trace", value: "Recorded" } : null,
      ]),
    },
  ];

  return stages;
}

function buildOutcomeSummary({
  grounding,
  learnedCount = 0,
  scenarioLab = null,
  branchCount = 0,
  hasComparisonArtifact = false,
  workspaceUpdate = null,
  hasTraceRecord = false,
  graphAction = null,
} = {}) {
  const parts = [];
  if (scenarioLab && scenarioLab.status !== "failed") {
    if (branchCount > 0 && hasComparisonArtifact) {
      parts.push(`Scenario Lab produced ${branchCount} ${pluralize("branch", branchCount)} and a comparison artifact.`);
    } else if (branchCount > 0) {
      parts.push(`Scenario Lab produced ${branchCount} ${pluralize("branch", branchCount)}.`);
    } else {
      parts.push("Scenario Lab produced a comparison result for this turn.");
    }
  } else if (!grounding?.isIdle) {
    parts.push(`The answer was returned as ${String(grounding.groundingLabel || "Idle").toLowerCase()}.`);
  }

  if (learnedCount > 0) {
    parts.push(`Learned ${learnedCount} new item${learnedCount === 1 ? "" : "s"} after the answer.`);
  } else if (workspaceUpdate?.status === "updated") {
    parts.push("The whiteboard was updated from this turn.");
  } else if (workspaceUpdate?.status === "draft_ready") {
    parts.push("A whiteboard draft was prepared for review.");
  } else if (workspaceUpdate?.status === "offered") {
    parts.push("Vantage offered to continue the work in the whiteboard.");
  } else if (graphAction) {
    parts.push("The turn produced a durable action.");
  } else {
    parts.push("No new durable item was created from this turn.");
  }

  if (hasTraceRecord) {
    parts.push("A Memory Trace record was captured for continuity.");
  }
  return parts.join(" ");
}

function humanizeWhiteboardModeSource(source) {
  switch (String(source || "").trim().toLowerCase()) {
    case "composer":
      return "Composer";
    case "request":
      return "User request";
    case "interpreter":
      return "Interpreter";
    case "default":
      return "Default";
    default:
      return "Unknown";
  }
}

export function buildChatTurnEvidence(payload) {
  const evidence = [];
  if (!payload || typeof payload !== "object") {
    return evidence;
  }

  const scenarioLab = payload?.scenario_lab && typeof payload.scenario_lab === "object"
    ? payload.scenario_lab
    : null;
  if (payload.mode === "scenario_lab" || scenarioLab?.status === "failed") {
    evidence.push({ label: "Scenario Lab", tone: "accent" });
    if (scenarioLab?.status === "failed") {
      evidence.push({ label: "Fallback", tone: "warm" });
    } else {
      const branchCount = Array.isArray(scenarioLab?.branches) ? scenarioLab.branches.length : 0;
      if (branchCount > 0) {
        evidence.push({ label: `${branchCount} ${pluralize("branch", branchCount)}`, tone: "soft" });
      }
    }
  }

  const grounding = groundingEvidenceLabel(payload);
  if (grounding) {
    evidence.push({
      label: grounding,
      tone: grounding === "Best Guess" ? "warm" : grounding === "Whiteboard" ? "accent" : "soft",
    });
  }

  const learnedItems = normalizeLearnedItems(payload);
  const learnedLabel = learnedEvidenceLabel(learnedItems);
  if (learnedLabel) {
    evidence.push({ label: learnedLabel, tone: "success" });
  }

  const workspaceStatus = String(payload?.workspace_update?.status || "").trim().toLowerCase();
  if (workspaceStatus === "offered") {
    evidence.push({ label: "Whiteboard offer", tone: "soft" });
  } else if (workspaceStatus === "draft_ready") {
    evidence.push({ label: "Draft ready", tone: "soft" });
  }

  return evidence;
}

export function deriveWhiteboardLifecycle({ dirty = false, lifecycle = "", workspaceId = "" } = {}) {
  const normalizedLifecycle = String(lifecycle || "").trim().toLowerCase();
  if (normalizedLifecycle === "promoted_artifact") {
    return {
      kind: "promoted_artifact",
      label: "Promoted artifact",
      panelLabel: "Promoted artifact",
    };
  }
  if (dirty || normalizedLifecycle === "transient_draft") {
    return {
      kind: "transient_draft",
      label: "Transient draft",
      panelLabel: "Transient draft",
    };
  }
  if (workspaceId || normalizedLifecycle === "saved_whiteboard") {
    return {
      kind: "saved_whiteboard",
      label: "Saved whiteboard",
      panelLabel: "Saved whiteboard",
    };
  }
  return {
    kind: "ready",
    label: "Whiteboard ready",
    panelLabel: "Ready",
  };
}
