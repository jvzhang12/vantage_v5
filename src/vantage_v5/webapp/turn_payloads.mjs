import {
  isWorkspaceResolutionDecision,
  normalizeWorkspaceDecision,
} from "./whiteboard_decisions.mjs";

const CANONICAL_CONTEXT_SOURCES = ["recall", "whiteboard", "recent_chat", "pending_whiteboard"];
const CANONICAL_WORKSPACE_CONTEXT_SCOPES = ["auto", "excluded", "visible", "pinned", "requested"];
const SCENARIO_SECTION_ALIASES = {
  thesis: "thesis",
  "shared context": "shared_context",
  "shared assumptions": "shared_assumptions",
  "preserved assumptions": "preserved_assumptions",
  "changed assumptions": "changed_assumptions",
  "predicted first-order effects": "first_order_effects",
  "predicted second-order effects": "second_order_effects",
  risks: "risks",
  "open questions": "open_questions",
  confidence: "confidence",
  "branches compared": "branches_compared",
  summary: "summary",
  tradeoffs: "tradeoffs",
  recommendation: "recommendation",
  "next steps": "next_steps",
};

export function normalizeResponseMode(responseMode, workingMemoryCount) {
  const fallbackCount = normalizeRecallCount(workingMemoryCount);
  if (responseMode && typeof responseMode === "object") {
    return normalizeProvidedResponseMode(responseMode, fallbackCount);
  }
  if (workingMemoryCount > 0) {
    return {
      kind: "grounded",
      label: "Recall",
      note: responseModeNoteForMode("grounded", "recall", fallbackCount, ["recall"]),
      recallCount: fallbackCount,
      workingMemoryCount: fallbackCount,
      groundingMode: "recall",
      groundingSources: ["recall"],
      contextSources: ["recall"],
    };
  }
  return {
    kind: "idle",
    label: "Idle",
    note: "Waiting for a turn.",
    recallCount: 0,
    workingMemoryCount: 0,
    groundingMode: null,
    groundingSources: [],
    contextSources: [],
  };
}

export function normalizeLearnedItems(payload) {
  if (Array.isArray(payload?.learned)) {
    return payload.learned;
  }
  if (payload?.created_record && typeof payload.created_record === "object") {
    return [payload.created_record];
  }
  return [];
}

export function normalizeMemoryTraceRecord(record) {
  if (!record || typeof record !== "object") {
    return null;
  }

  const normalized = {
    ...record,
    id: normalizeRecordId(record, record.id || record.record_id || ""),
    title: String(record.title || record.name || record.label || "Turn Trace").trim(),
    card: String(record.card || record.summary || "").trim(),
    body: String(record.body || record.content || "").trim(),
    source: String(record.source || "memory_trace").trim() || "memory_trace",
    type: String(record.type || "memory_trace").trim() || "memory_trace",
    status: String(record.status || "active").trim() || "active",
    scope: String(record.scope || "").trim(),
    sourceLabel: String(record.sourceLabel || record.source_label || "Memory Trace").trim() || "Memory Trace",
  };

  return normalized.id ? normalized : null;
}

export function normalizeRecordId(record, fallback = "") {
  if (!record || typeof record !== "object") {
    return String(fallback || "");
  }
  const id = record.id || record.record_id || record.concept_id || record.note_id || fallback;
  return typeof id === "string" || typeof id === "number" ? String(id) : "";
}

export function normalizeWorkspaceContextScope(scope, fallback = "excluded") {
  const normalizedScope = String(scope || "").trim().toLowerCase();
  if (CANONICAL_WORKSPACE_CONTEXT_SCOPES.includes(normalizedScope)) {
    return normalizedScope;
  }
  return CANONICAL_WORKSPACE_CONTEXT_SCOPES.includes(fallback) ? fallback : "excluded";
}

export function normalizeScenarioLabPayload(scenarioLab) {
  if (!scenarioLab || typeof scenarioLab !== "object") {
    return null;
  }
  const comparisonArtifact = normalizeScenarioArtifact(scenarioLab.comparison_artifact);
  const branches = Array.isArray(scenarioLab.branches)
    ? scenarioLab.branches.map((branch) => normalizeScenarioBranch(branch)).filter(Boolean)
    : [];
  const question = firstNonEmptyString(
    scenarioLab.question,
    scenarioLab.comparison_question,
    comparisonArtifact?.comparisonQuestion,
  );
  const summary = firstNonEmptyString(
    scenarioLab.summary,
    comparisonArtifact?.card,
    comparisonArtifact?.sections.summary.text,
  );
  const recommendation = firstNonEmptyString(
    scenarioLab.recommendation,
    comparisonArtifact?.recommendation,
    comparisonArtifact?.sections.recommendation.text,
  );
  return {
    ...scenarioLab,
    question,
    comparison_question: question,
    summary,
    recommendation,
    branchCount: branches.length,
    branches,
    comparisonArtifact,
    sharedContext: comparisonArtifact?.sections.sharedContext.text || "",
    sharedAssumptions: comparisonArtifact?.sections.sharedAssumptions.items || [],
    tradeoffs: comparisonArtifact?.sections.tradeoffs.items || [],
    nextSteps: comparisonArtifact?.sections.nextSteps.items || [],
  };
}

export function normalizeTurnPayload(payload) {
  const normalizedPayload = payload && typeof payload === "object" ? payload : {};
  const recallItems = normalizeRecallItems(normalizedPayload);
  return {
    recallItems,
    workingMemoryItems: recallItems,
    learnedItems: normalizeLearnedItems(normalizedPayload),
    memoryTraceRecord: normalizeMemoryTraceRecord(normalizedPayload.memory_trace_record || normalizedPayload.memoryTraceRecord),
    responseMode: normalizeResponseMode(normalizedPayload.response_mode, recallItems.length),
    scenarioLab: normalizeScenarioLabPayload(normalizedPayload.scenario_lab),
    workspaceUpdate: normalizeWorkspaceUpdate(normalizedPayload.workspace_update, normalizedPayload.workspace),
    workspaceContextScope: normalizeWorkspaceContextScope(normalizedPayload.workspace?.context_scope),
  };
}

function normalizeProvidedResponseMode(responseMode, fallbackRecallCount) {
  const recallCount = normalizeRecallCount(
    Number.isFinite(Number(responseMode.recall_count))
      ? Number(responseMode.recall_count)
      : Number.isFinite(Number(responseMode.recallCount))
        ? Number(responseMode.recallCount)
        : Number.isFinite(Number(responseMode.working_memory_count))
          ? Number(responseMode.working_memory_count)
          : Number.isFinite(Number(responseMode.workingMemoryCount))
            ? Number(responseMode.workingMemoryCount)
            : fallbackRecallCount,
  );
  const rawKind = normalizeResponseModeKind(responseMode.kind);
  const explicitContextSources = normalizeProvidedContextSources(responseMode);
  const groundingMode = normalizeGroundingMode(
    responseMode.grounding_mode
      || responseMode.groundingMode
      || responseMode.legacy_grounding_mode
      || responseMode.legacyGroundingMode
      || responseMode.recall_mode
      || responseMode.recallMode,
    rawKind,
    explicitContextSources,
    recallCount,
  );
  const groundingSources = explicitContextSources.length
    ? explicitContextSources
    : inferContextSourcesFromLegacyShape(groundingMode, recallCount);
  const kind = canonicalResponseModeKind(rawKind, groundingMode);
  const label = String(responseMode.label || "").trim()
    || responseModeLabelForMode(kind, groundingMode, groundingSources, recallCount);
  const note = String(responseMode.note || "").trim()
    || responseModeNoteForMode(kind, groundingMode, recallCount, groundingSources);

  return {
    kind,
    label,
    note,
    recallCount,
    workingMemoryCount: recallCount,
    groundingMode,
    groundingSources: [...groundingSources],
    contextSources: [...groundingSources],
  };
}

function normalizeProvidedContextSources(responseMode) {
  return normalizeContextSources(
    Array.isArray(responseMode.context_sources)
      ? responseMode.context_sources
      : Array.isArray(responseMode.contextSources)
        ? responseMode.contextSources
        : Array.isArray(responseMode.grounding_sources)
          ? responseMode.grounding_sources
          : Array.isArray(responseMode.groundingSources)
            ? responseMode.groundingSources
            : Array.isArray(responseMode.legacy_context_sources)
              ? responseMode.legacy_context_sources
              : Array.isArray(responseMode.legacyContextSources)
                ? responseMode.legacyContextSources
                : Array.isArray(responseMode.legacy_grounding_sources)
                  ? responseMode.legacy_grounding_sources
                  : Array.isArray(responseMode.legacyGroundingSources)
                    ? responseMode.legacyGroundingSources
                    : [],
  );
}

function normalizeResponseModeKind(kind) {
  const normalized = String(kind || "").trim().toLowerCase();
  switch (normalized) {
    case "recall_grounded":
    case "working_memory_grounded":
    case "whiteboard_grounded":
    case "recent_chat_grounded":
    case "pending_whiteboard_grounded":
    case "mixed_context_grounded":
    case "grounded":
    case "best_guess":
    case "idle":
      return normalized;
    case "mixed_context":
      return "grounded";
    case "ungrounded":
      return "best_guess";
    default:
      return normalized || "idle";
  }
}

function canonicalResponseModeKind(kind, groundingMode) {
  if (kind === "idle") {
    return "idle";
  }
  if (kind === "best_guess") {
    return "best_guess";
  }
  if (kind === "grounded") {
    return groundingMode === "ungrounded" ? "best_guess" : "grounded";
  }
  if (legacyGroundingModeForKind(kind)) {
    return kind === "ungrounded" ? "best_guess" : "grounded";
  }
  return groundingMode === "ungrounded" ? "best_guess" : "grounded";
}

function normalizeGroundingMode(groundingMode, kind, groundingSources, workingMemoryCount) {
  const normalizedMode = String(groundingMode || "").trim().toLowerCase();
  if (normalizedMode === "recall" || normalizedMode === "working_memory") {
    return "recall";
  }
  if (isCanonicalGroundingMode(normalizedMode)) {
    return normalizedMode;
  }
  const legacyMode = legacyGroundingModeForKind(kind);
  if (legacyMode) {
    return legacyMode;
  }
  if (groundingSources.includes("recall")) {
    return groundingSources.length > 1 ? "mixed_context" : "recall";
  }
  if (groundingSources.length > 1) {
    return "mixed_context";
  }
  if (groundingSources.includes("whiteboard")) {
    return "whiteboard";
  }
  if (groundingSources.includes("recent_chat")) {
    return "recent_chat";
  }
  if (groundingSources.includes("pending_whiteboard")) {
    return "pending_whiteboard";
  }
  if (workingMemoryCount > 0) {
    return "recall";
  }
  return "ungrounded";
}

function isCanonicalGroundingMode(mode) {
  return [
    "recall",
    "whiteboard",
    "recent_chat",
    "pending_whiteboard",
    "mixed_context",
    "ungrounded",
  ].includes(mode);
}

function legacyGroundingModeForKind(kind) {
  switch (kind) {
    case "recall_grounded":
    case "working_memory_grounded":
      return "recall";
    case "whiteboard_grounded":
      return "whiteboard";
    case "recent_chat_grounded":
      return "recent_chat";
    case "pending_whiteboard_grounded":
      return "pending_whiteboard";
    case "mixed_context_grounded":
      return "mixed_context";
    case "ungrounded":
      return "ungrounded";
    default:
      return null;
  }
}

function inferContextSourcesFromLegacyShape(groundingMode, workingMemoryCount) {
  switch (groundingMode) {
    case "recall":
    case "working_memory":
      return workingMemoryCount > 0 ? ["recall"] : [];
    case "whiteboard":
      return ["whiteboard"];
    case "recent_chat":
      return ["recent_chat"];
    case "pending_whiteboard":
      return ["pending_whiteboard"];
    default:
      return [];
  }
}

function responseModeLabelForMode(kind, groundingMode, groundingSources = [], workingMemoryCount = 0) {
  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "Best Guess";
  }
  switch (groundingMode) {
    case "recall":
    case "working_memory":
      return "Recall";
    case "whiteboard":
      return "Whiteboard";
    case "recent_chat":
      return "Recent Chat";
    case "pending_whiteboard":
      return "Prior Whiteboard";
    case "mixed_context":
      return describeMixedContextLabel(workingMemoryCount, groundingSources);
    case "ungrounded":
      return "Best Guess";
    default:
      return kind === "grounded" ? "Grounded" : "Idle";
  }
}

function responseModeNoteForMode(kind, groundingMode, workingMemoryCount, groundingSources = []) {
  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "No grounded context supported this answer.";
  }
  switch (groundingMode) {
    case "recall":
    case "working_memory":
      return `Supported by ${workingMemoryCount} recalled item${workingMemoryCount === 1 ? "" : "s"} from Recall.`;
    case "whiteboard":
      return "Supported by the active whiteboard.";
    case "recent_chat":
      return "Supported by the recent conversation.";
    case "pending_whiteboard":
      return "Supported by the prior whiteboard.";
    case "mixed_context":
      return `Supported by ${describeMixedContextSupport(workingMemoryCount, groundingSources)}.`;
    default:
      return kind === "grounded" ? "Supported by available context." : "Waiting for a turn.";
  }
}

function describeMixedContextLabel(workingMemoryCount, groundingSources) {
  const sources = mixedContextSourceLabels(workingMemoryCount, groundingSources, { style: "label" });
  return sources.length ? sources.join(" + ") : "Mixed Context";
}

function describeMixedContextSupport(workingMemoryCount, groundingSources) {
  const sources = mixedContextSourceLabels(workingMemoryCount, groundingSources, { style: "note" });
  return sources.length ? joinReadableList(sources) : "multiple context sources";
}

function mixedContextSourceLabels(workingMemoryCount, groundingSources, { style = "label" } = {}) {
  const normalizedSources = normalizeContextSources([
    ...(Array.isArray(groundingSources) ? groundingSources : []),
    ...(workingMemoryCount > 0 ? ["recall"] : []),
  ]);
  const sources = [];
  for (const source of normalizedSources) {
    const label = describeContextSource(source, style);
    if (label) {
      sources.push(label);
    }
  }
  return sources;
}

function describeContextSource(source, style = "label") {
  const normalizedSource = String(source || "").trim().toLowerCase();
  if (style === "note") {
    switch (normalizedSource) {
      case "recall":
      case "working_memory":
        return "Recall";
      case "whiteboard":
        return "the active whiteboard";
      case "recent_chat":
        return "the recent conversation";
      case "pending_whiteboard":
        return "the prior whiteboard";
      default:
        return "";
    }
  }
  switch (normalizedSource) {
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

function normalizeContextSources(sources) {
  if (!Array.isArray(sources)) {
    return [];
  }
  return [...new Set(
    sources
      .map((source) => normalizeContextSource(source))
      .filter((source) => CANONICAL_CONTEXT_SOURCES.includes(source)),
  )];
}

function normalizeContextSource(source) {
  const normalized = String(source || "").trim().toLowerCase();
  if (normalized === "working_memory") {
    return "recall";
  }
  return normalized;
}

function normalizeRecallCount(count) {
  return Number.isFinite(Number(count)) ? Number(count) : 0;
}

function normalizeRecallItems(payload) {
  if (Array.isArray(payload?.recall)) {
    return payload.recall;
  }
  if (Array.isArray(payload?.working_memory)) {
    return payload.working_memory;
  }
  return [];
}

function firstNonEmptyString(...values) {
  for (const value of values) {
    const text = normalizeScenarioText(value);
    if (text) {
      return text;
    }
  }
  return "";
}

function normalizeScenarioText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeScenarioSectionHeading(heading) {
  const normalizedHeading = String(heading || "").trim().toLowerCase();
  if (SCENARIO_SECTION_ALIASES[normalizedHeading]) {
    return SCENARIO_SECTION_ALIASES[normalizedHeading];
  }
  return normalizedHeading.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function parseScenarioMarkdownSections(body) {
  const lines = String(body || "").split(/\r?\n/);
  const sections = {};
  let currentSection = "";
  for (const rawLine of lines) {
    const headingMatch = rawLine.match(/^##\s+(.+?)\s*$/);
    if (headingMatch) {
      currentSection = normalizeScenarioSectionHeading(headingMatch[1]);
      sections[currentSection] = [];
      continue;
    }
    if (!currentSection) {
      continue;
    }
    sections[currentSection].push(rawLine);
  }
  return sections;
}

function collapseScenarioSectionText(lines = []) {
  return lines
    .map((line) => String(line || "").trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*]\s+/, "").trim())
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractScenarioListItems(lines = []) {
  return lines
    .map((line) => String(line || "").trim())
    .filter((line) => /^[-*]\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, "").trim())
    .filter(Boolean);
}

function normalizeScenarioSection(lines = []) {
  return {
    text: collapseScenarioSectionText(lines),
    items: extractScenarioListItems(lines),
  };
}

function normalizeScenarioBranch(branch) {
  if (!branch || typeof branch !== "object") {
    return null;
  }
  const body = typeof branch.body === "string" ? branch.body : "";
  const sectionLines = parseScenarioMarkdownSections(body);
  const sections = {
    thesis: normalizeScenarioSection(sectionLines.thesis),
    sharedContext: normalizeScenarioSection(sectionLines.shared_context),
    sharedAssumptions: normalizeScenarioSection(sectionLines.shared_assumptions),
    preservedAssumptions: normalizeScenarioSection(sectionLines.preserved_assumptions),
    changedAssumptions: normalizeScenarioSection(sectionLines.changed_assumptions),
    firstOrderEffects: normalizeScenarioSection(sectionLines.first_order_effects),
    secondOrderEffects: normalizeScenarioSection(sectionLines.second_order_effects),
    risks: normalizeScenarioSection(sectionLines.risks),
    openQuestions: normalizeScenarioSection(sectionLines.open_questions),
    confidence: normalizeScenarioSection(sectionLines.confidence),
  };
  const workspaceId = firstNonEmptyString(branch.workspace_id, branch.workspaceId, branch.id);
  const confidence = firstNonEmptyString(branch.confidence, sections.confidence.text);
  const card = firstNonEmptyString(branch.card, branch.summary, sections.thesis.text)
    || "Scenario branch ready to open in the whiteboard.";
  const summary = firstNonEmptyString(branch.summary, branch.card, sections.thesis.text) || card;
  const riskSummary = firstNonEmptyString(branch.risk_summary, sections.risks.items[0], sections.risks.text);
  return {
    ...branch,
    id: normalizeRecordId(branch, workspaceId),
    workspaceId,
    workspace_id: workspaceId,
    title: firstNonEmptyString(branch.title, workspaceId) || "Scenario branch",
    label: normalizeScenarioText(branch.label),
    card,
    summary,
    confidence,
    riskSummary,
    sections,
  };
}

function normalizeScenarioArtifact(artifact) {
  if (!artifact || typeof artifact !== "object") {
    return null;
  }
  const body = typeof artifact.body === "string" ? artifact.body : "";
  const sectionLines = parseScenarioMarkdownSections(body);
  const sections = {
    sharedContext: normalizeScenarioSection(sectionLines.shared_context),
    sharedAssumptions: normalizeScenarioSection(sectionLines.shared_assumptions),
    branchesCompared: normalizeScenarioSection(sectionLines.branches_compared),
    summary: normalizeScenarioSection(sectionLines.summary),
    tradeoffs: normalizeScenarioSection(sectionLines.tradeoffs),
    recommendation: normalizeScenarioSection(sectionLines.recommendation),
    nextSteps: normalizeScenarioSection(sectionLines.next_steps),
  };
  const recommendation = firstNonEmptyString(artifact.recommendation, sections.recommendation.text);
  return {
    ...artifact,
    id: normalizeRecordId(artifact),
    title: firstNonEmptyString(artifact.title) || "Scenario comparison",
    card: firstNonEmptyString(artifact.card, sections.summary.text),
    body,
    recommendation,
    comparisonQuestion: firstNonEmptyString(artifact.comparison_question),
    branchWorkspaceIds: Array.isArray(artifact.branch_workspace_ids)
      ? artifact.branch_workspace_ids.map((item) => String(item || "").trim()).filter(Boolean)
      : [],
    sections,
  };
}

function joinReadableList(items) {
  if (!items.length) {
    return "";
  }
  if (items.length === 1) {
    return items[0];
  }
  if (items.length === 2) {
    return `${items[0]} and ${items[1]}`;
  }
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

export function normalizeTurnInterpretation(interpretation) {
  if (!interpretation || typeof interpretation !== "object") {
    return null;
  }
  const confidence = Number(interpretation.confidence);
  return {
    mode: String(interpretation.mode || "").trim().toLowerCase() || "chat",
    confidence: Number.isFinite(confidence) ? confidence : 0,
    reason: String(interpretation.reason || "").trim(),
    requestedWhiteboardMode: String(interpretation.requested_whiteboard_mode || "").trim().toLowerCase() || null,
    resolvedWhiteboardMode: String(interpretation.resolved_whiteboard_mode || "").trim().toLowerCase() || null,
    whiteboardModeSource: String(interpretation.whiteboard_mode_source || "").trim().toLowerCase() || null,
    preserveSelectedRecord: interpretation.preserve_selected_record ?? null,
    selectedRecordReason: String(interpretation.selected_record_reason || "").trim() || "",
  };
}

export function normalizeWorkspaceUpdate(workspaceUpdate, workspacePayload = {}) {
  if (!workspaceUpdate || typeof workspaceUpdate !== "object") {
    return null;
  }
  const decision = normalizeWorkspaceDecision(workspaceUpdate.decision);
  const status = String(workspaceUpdate.status || "").trim().toLowerCase() || "updated";
  const normalized = {
    ...workspaceUpdate,
    status,
    title: workspaceUpdate.title || workspacePayload?.title || "",
    workspaceId: workspaceUpdate.workspace_id || workspacePayload?.workspace_id || "",
    content: typeof workspaceUpdate.content === "string"
      ? workspaceUpdate.content
      : status === "updated" && typeof workspacePayload?.content === "string"
        ? workspacePayload.content
        : "",
    decision: isWorkspaceResolutionDecision(decision) ? decision : null,
  };
  if (!normalized.summary) {
    if (normalized.status === "offered") {
      normalized.summary = "Vantage suggested continuing this work product in the whiteboard.";
    } else if (normalized.status === "draft_ready") {
      normalized.summary = "A whiteboard draft is ready to review before it changes the whiteboard.";
    } else if (normalized.status === "updated") {
      normalized.summary = "The whiteboard was updated from this turn.";
    }
  }
  return normalized;
}
