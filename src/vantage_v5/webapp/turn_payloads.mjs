import {
  isWorkspaceResolutionDecision,
  normalizeWorkspaceDecision,
} from "./whiteboard_decisions.mjs";

const CANONICAL_CONTEXT_SOURCES = ["recall", "whiteboard", "recent_chat", "pending_whiteboard"];
const CANONICAL_WORKSPACE_CONTEXT_SCOPES = ["auto", "excluded", "visible", "pinned", "requested"];
const STAGE_LABEL_MAX_LENGTH = 72;
const STAGE_MESSAGE_MAX_LENGTH = 180;
const STAGE_AUDIT_MAX_LENGTH = 140;
const HIDDEN_STAGE_TEXT_PATTERN = /\b(chain[-\s]?of[-\s]?thought|scratchpad|system\s+prompt|developer\s+message|raw\s+provider|stack\s+trace|traceback|json\s+schema|hidden\s+context|hidden\s+context\s+bodies?|openai|gpt[-_\s]?\d|o[1345](?:[-_\s]?(?:mini|preview|pro))?|model\s+(?:id|identifier|name)|provider\s+(?:request|response|payload|body))\b/i;
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

export function normalizeAnswerBasis(answerBasis = null, {
  responseMode = null,
  recallItems = [],
  workingMemoryItems = [],
} = {}) {
  const visibleRecallItems = Array.isArray(recallItems) && recallItems.length
    ? recallItems
    : Array.isArray(workingMemoryItems)
      ? workingMemoryItems
      : [];
  const fallbackResponseMode = responseMode && typeof responseMode === "object"
    ? normalizeResponseMode(responseMode, visibleRecallItems.length)
    : normalizeResponseMode(null, visibleRecallItems.length);
  const provided = answerBasis && typeof answerBasis === "object" ? answerBasis : null;
  const visibleProtocolCount = visibleRecallItems.filter(isProtocolAnswerBasisItem).length;
  const visibleMemoryCount = Math.max(0, visibleRecallItems.length - visibleProtocolCount);
  const responseRecallCount = Number.isFinite(Number(fallbackResponseMode?.recallCount))
    ? Number(fallbackResponseMode.recallCount)
    : visibleRecallItems.length;
  const derivedProtocolCount = visibleProtocolCount;
  const derivedMemoryCount = visibleRecallItems.length
    ? (visibleMemoryCount > 0
      ? Math.max(visibleMemoryCount, responseRecallCount - derivedProtocolCount)
      : 0)
    : Math.max(0, responseRecallCount);

  const providedContextSources = provided
    ? normalizeAnswerBasisSources(provided.context_sources || provided.contextSources)
    : [];
  const providedEvidenceSources = provided
    ? normalizeAnswerBasisSources(provided.evidence_sources || provided.evidenceSources)
    : [];
  const providedGuidanceSources = provided
    ? normalizeAnswerBasisSources(provided.guidance_sources || provided.guidanceSources)
    : [];
  const responseContextSources = normalizeAnswerBasisSources(
    fallbackResponseMode?.contextSources || fallbackResponseMode?.context_sources || fallbackResponseMode?.groundingSources || fallbackResponseMode?.grounding_sources,
  );
  const fallbackContextSources = deriveAnswerBasisContextSources({
    responseContextSources,
    memoryCount: derivedMemoryCount,
    protocolCount: derivedProtocolCount,
  });
  const guidanceSources = providedGuidanceSources.length
    ? providedGuidanceSources
    : (derivedProtocolCount > 0 ? ["protocol"] : []);
  const evidenceSources = providedEvidenceSources.length
    ? providedEvidenceSources
    : deriveAnswerBasisEvidenceSources({
      contextSources: providedContextSources.length ? providedContextSources : fallbackContextSources,
      memoryCount: derivedMemoryCount,
      protocolCount: derivedProtocolCount,
    });
  const contextSources = providedContextSources.length
    ? providedContextSources
    : normalizeAnswerBasisSources([
      ...fallbackContextSources,
      ...guidanceSources,
    ]);
  const sources = normalizeAnswerBasisSources(
    provided?.sources || [
      ...contextSources,
      ...evidenceSources,
      ...guidanceSources,
    ],
  );
  const hasFactualGrounding = normalizeInterpretationBoolean(
    provided?.has_factual_grounding ?? provided?.hasFactualGrounding,
  ) ?? evidenceSources.length > 0;
  const counts = normalizeAnswerBasisCounts(provided?.counts, {
    recall: derivedMemoryCount,
    memory: derivedMemoryCount,
    protocol: derivedProtocolCount,
    whiteboard: contextSources.includes("whiteboard") ? 1 : 0,
    recentChat: contextSources.includes("recent_chat") ? 1 : 0,
    pendingWhiteboard: contextSources.includes("pending_whiteboard") ? 1 : 0,
    evidence: derivedMemoryCount + countIncludedContextSources(evidenceSources, ["whiteboard", "recent_chat", "pending_whiteboard"]),
    guidance: guidanceSources.length,
    context: contextSources.length,
    sources: sources.length,
  });
  const kind = normalizeAnswerBasisKind(
    provided?.kind || provided?.basis_kind || provided?.basisKind,
    {
      responseMode: fallbackResponseMode,
      contextSources,
      evidenceSources,
      guidanceSources,
      counts,
      hasFactualGrounding,
    },
  );
  const label = answerBasisLabelForKind(kind, provided?.label);
  const note = sanitizeAnswerBasisCopy(
    provided?.note || answerBasisNoteForKind(kind, counts, contextSources, evidenceSources, guidanceSources),
  );
  const summary = sanitizeAnswerBasisCopy(provided?.summary || note);

  return {
    kind,
    label,
    note,
    summary,
    hasFactualGrounding,
    sources,
    contextSources,
    evidenceSources,
    guidanceSources,
    counts,
  };
}

export function normalizeWriteReview(value) {
  const source = value && typeof value === "object" ? value : null;
  if (!source) {
    return null;
  }
  const reason = firstNonEmptyString(
    source.reason,
    source.write_reason,
    source.writeReason,
    source.why_saved,
    source.whySaved,
    source.why_learned,
    source.whyLearned,
    source.rationale,
  );
  const scope = firstNonEmptyString(source.scope, source.review_scope, source.reviewScope);
  const durability = firstNonEmptyString(source.durability);
  const summary = firstNonEmptyString(source.summary, source.copy, source.review_copy, source.reviewCopy);
  const primaryAction = source.primary_action && typeof source.primary_action === "object"
    ? source.primary_action
    : source.primaryAction && typeof source.primaryAction === "object"
      ? source.primaryAction
      : null;
  const normalized = {
    ...source,
    ...(reason ? { reason } : {}),
    ...(reason ? { write_reason: reason, writeReason: reason } : {}),
    ...(scope ? { scope } : {}),
    ...(durability ? { durability } : {}),
    ...(summary ? { summary } : {}),
    ...(primaryAction ? { primaryAction, primary_action: primaryAction } : {}),
  };
  return Object.keys(normalized).length ? normalized : null;
}

function normalizeLearnedItem(item) {
  if (!item || typeof item !== "object") {
    return null;
  }
  const id = normalizeRecordId(item, "");
  if (!id) {
    return null;
  }
  const writeReview = normalizeWriteReview(item.write_review || item.writeReview);
  return {
    ...item,
    id,
    ...(writeReview ? { writeReview, write_review: writeReview } : {}),
  };
}

export function normalizeLearnedItems(payload) {
  if (Array.isArray(payload?.learned)) {
    return payload.learned.map((item) => normalizeLearnedItem(item)).filter(Boolean);
  }
  const createdRecord = payload?.created_record || payload?.createdRecord;
  if (createdRecord && typeof createdRecord === "object") {
    const normalized = normalizeLearnedItem(createdRecord);
    return normalized ? [normalized] : [];
  }
  return [];
}

export function normalizeContextBudget(contextBudget = null, {
  responseMode = null,
  answerBasis = null,
  recallItems = [],
  workspaceContextScope = "excluded",
  interpretation = null,
} = {}) {
  const source = contextBudget && typeof contextBudget === "object" ? contextBudget : null;
  const rows = source
    ? normalizeContextBudgetRows(source.rows || source.items)
    : deriveContextBudgetRows({
      responseMode,
      answerBasis,
      recallItems,
      workspaceContextScope,
      interpretation,
    });
  const counts = source?.counts && typeof source.counts === "object"
    ? normalizeContextBudgetCounts(source.counts, rows)
    : contextBudgetCountsFromRows(rows);
  const contextSources = normalizeAnswerBasisSources(
    source?.context_sources
      || source?.contextSources
      || answerBasis?.contextSources
      || answerBasis?.context_sources
      || responseMode?.contextSources
      || responseMode?.context_sources
      || responseMode?.groundingSources
      || responseMode?.grounding_sources
      || [],
  );
  const summary = firstNonEmptyString(source?.summary, describeContextBudgetRows(rows));
  return {
    label: firstNonEmptyString(source?.label, "Context Budget"),
    summary,
    rows,
    items: rows,
    counts,
    contextSources,
    context_sources: contextSources,
  };
}

function normalizeContextBudgetRows(rows) {
  return (Array.isArray(rows) ? rows : [])
    .map((row) => normalizeContextBudgetRow(row))
    .filter(Boolean);
}

function normalizeContextBudgetRow(row) {
  if (!row || typeof row !== "object") {
    return null;
  }
  const key = normalizeSemanticToken(row.key || row.id || row.name, "");
  const label = firstNonEmptyString(row.label, humanizeContextBudgetKey(key));
  if (!key || !label) {
    return null;
  }
  const status = normalizeContextBudgetStatus(row.status || row.state || row.display_status || row.displayStatus);
  const count = normalizeContextBudgetCount(row.count);
  const detail = firstNonEmptyString(row.detail, row.summary, row.note, "");
  const scope = firstNonEmptyString(row.scope, row.scope_label, row.scopeLabel, "");
  return {
    ...row,
    key,
    label,
    status,
    displayStatus: status === "included" ? "Included" : "Excluded",
    display_status: status === "included" ? "Included" : "Excluded",
    ...(Number.isFinite(count) ? { count } : {}),
    ...(detail ? { detail } : {}),
    ...(scope ? { scope } : {}),
  };
}

function deriveContextBudgetRows({
  responseMode = null,
  answerBasis = null,
  recallItems = [],
  workspaceContextScope = "excluded",
  interpretation = null,
} = {}) {
  const sources = normalizeAnswerBasisSources([
    ...(answerBasis?.contextSources || answerBasis?.context_sources || []),
    ...(answerBasis?.guidanceSources || answerBasis?.guidance_sources || []),
    ...(responseMode?.contextSources || responseMode?.context_sources || responseMode?.groundingSources || responseMode?.grounding_sources || []),
  ]);
  const counts = answerBasis?.counts && typeof answerBasis.counts === "object" ? answerBasis.counts : {};
  const recallCount = normalizeCountAlias(
    counts,
    ["recalled_items", "recalledItems", "recall", "recall_count", "recallCount"],
    Number.isFinite(Number(responseMode?.recallCount ?? responseMode?.recall_count))
      ? Number(responseMode?.recallCount ?? responseMode?.recall_count)
      : Array.isArray(recallItems)
        ? recallItems.length
        : 0,
  );
  const protocolCount = normalizeCountAlias(
    counts,
    ["protocol", "protocols", "guidance"],
    Array.isArray(recallItems) ? recallItems.filter(isProtocolAnswerBasisItem).length : 0,
  );
  const traceCount = Array.isArray(recallItems)
    ? recallItems.filter((item) => String(item?.source || item?.type || "").trim().toLowerCase() === "memory_trace").length
    : 0;
  const whiteboardIncluded = sources.includes("whiteboard");
  const recentChatIncluded = sources.includes("recent_chat");
  const pendingWhiteboardIncluded = sources.includes("pending_whiteboard");
  const pinnedPreserved = interpretation
    ? normalizeInterpretationBoolean(
      interpretation.preservePinnedContext
        ?? interpretation.preserve_pinned_context
        ?? interpretation.preserveSelectedRecord
        ?? interpretation.preserve_selected_record,
    )
    : null;
  const scope = humanizeContextBudgetScope(workspaceContextScope);
  const rows = [
    createDerivedContextBudgetRow("user_request", "User request", true, "The current user message is always included."),
    createDerivedContextBudgetRow(
      "recall",
      "Recall",
      recallCount > 0,
      recallCount > 0 ? `${recallCount} item${recallCount === 1 ? "" : "s"} entered Recall.` : "No recalled Library or Memory Trace item entered Recall.",
      recallCount,
    ),
    createDerivedContextBudgetRow(
      "protocol",
      "Protocols",
      protocolCount > 0,
      protocolCount > 0 ? `${protocolCount} protocol${protocolCount === 1 ? "" : "s"} shaped the task as guidance.` : "No reusable protocol guidance was applied.",
      protocolCount,
    ),
    createDerivedContextBudgetRow(
      "whiteboard",
      "Whiteboard",
      whiteboardIncluded,
      whiteboardIncluded
        ? (scope ? `Whiteboard content was included. Scope hint: ${scope}.` : "Whiteboard content was included.")
        : (scope ? `Whiteboard scope hint was ${scope}, but it was not listed as a generation source.` : "No whiteboard content was included."),
      whiteboardIncluded ? 1 : 0,
      scope,
    ),
    createDerivedContextBudgetRow(
      "recent_chat",
      "Recent chat",
      recentChatIncluded,
      recentChatIncluded ? "Recent conversation context was included." : "Recent chat was not included as a separate grounding source.",
      recentChatIncluded ? 1 : 0,
    ),
    createDerivedContextBudgetRow(
      "pending_whiteboard",
      "Prior draft",
      pendingWhiteboardIncluded,
      pendingWhiteboardIncluded ? "A prior pending whiteboard draft was included." : "No prior pending whiteboard draft was included.",
      pendingWhiteboardIncluded ? 1 : 0,
    ),
    createDerivedContextBudgetRow(
      "pinned_context",
      "Pinned context",
      pinnedPreserved === true,
      pinnedPreserved === true
        ? firstNonEmptyString(interpretation?.pinnedContextReason, interpretation?.pinned_context_reason, interpretation?.selectedRecordReason, interpretation?.selected_record_reason, "Pinned context stayed in scope.")
        : "No pinned context was preserved for this turn.",
      pinnedPreserved === true ? 1 : 0,
    ),
  ];
  if (traceCount > 0) {
    rows.push(createDerivedContextBudgetRow(
      "memory_trace",
      "Memory Trace",
      true,
      `${traceCount} recent history item${traceCount === 1 ? "" : "s"} entered Recall.`,
      traceCount,
    ));
  }
  return rows;
}

function createDerivedContextBudgetRow(key, label, included, detail, count = null, scope = "") {
  return {
    key,
    label,
    status: included ? "included" : "excluded",
    displayStatus: included ? "Included" : "Excluded",
    display_status: included ? "Included" : "Excluded",
    detail,
    ...(Number.isFinite(Number(count)) ? { count: Number(count) } : {}),
    ...(scope ? { scope } : {}),
  };
}

function normalizeContextBudgetStatus(value) {
  const normalized = String(value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (["included", "include", "used", "active", "preserved", "yes", "true"].includes(normalized)) {
    return "included";
  }
  return "excluded";
}

function normalizeContextBudgetCount(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(0, numeric) : null;
}

function normalizeContextBudgetCounts(counts, rows) {
  return {
    ...contextBudgetCountsFromRows(rows),
    ...Object.fromEntries(
      Object.entries(counts)
        .map(([key, value]) => [key, normalizeContextBudgetCount(value)])
        .filter(([, value]) => Number.isFinite(value)),
    ),
  };
}

function contextBudgetCountsFromRows(rows) {
  return rows.reduce((counts, row) => {
    counts[row.key] = Number.isFinite(Number(row.count)) ? Number(row.count) : (row.status === "included" ? 1 : 0);
    return counts;
  }, {});
}

function describeContextBudgetRows(rows) {
  const included = rows
    .filter((row) => row.status === "included")
    .map((row) => {
      if (Number.isFinite(Number(row.count)) && Number(row.count) > 0 && !["user_request", "whiteboard", "recent_chat", "pending_whiteboard", "pinned_context"].includes(row.key)) {
        return `${row.label}: ${Number(row.count)}`;
      }
      return row.label;
    });
  return included.length
    ? `Context budget: ${included.join(", ")}.`
    : "Context budget: current request only.";
}

function humanizeContextBudgetKey(key) {
  switch (String(key || "").trim().toLowerCase()) {
    case "user_request":
      return "User request";
    case "recall":
      return "Recall";
    case "protocol":
      return "Protocols";
    case "whiteboard":
      return "Whiteboard";
    case "recent_chat":
      return "Recent chat";
    case "pending_whiteboard":
      return "Prior draft";
    case "pinned_context":
      return "Pinned context";
    case "memory_trace":
      return "Memory Trace";
    default:
      return "";
  }
}

function humanizeContextBudgetScope(scope) {
  switch (String(scope || "").trim().toLowerCase()) {
    case "visible":
      return "Visible";
    case "pinned":
      return "Pinned";
    case "requested":
      return "Requested";
    case "auto":
      return "Auto";
    default:
      return "";
  }
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
  const branches = Array.isArray(scenarioLab.branches)
    ? scenarioLab.branches.map((branch) => normalizeScenarioBranch(branch)).filter(Boolean)
    : [];
  const rawComparisonArtifact = normalizeScenarioArtifact(scenarioLab.comparison_artifact);
  const derivedBranchIndex = branches
    .map((branch) => normalizeComparisonBranchIndex([branch]))
    .flat();
  const artifactBranchIndex = rawComparisonArtifact?.branchIndex || [];
  const artifactBranchIndexHasDetail = artifactBranchIndex.some((branch) => branch?.title || branch?.label || branch?.summary);
  const comparisonArtifact = rawComparisonArtifact
    ? {
      ...rawComparisonArtifact,
      branchIndex: artifactBranchIndexHasDetail ? artifactBranchIndex : (derivedBranchIndex.length ? derivedBranchIndex : artifactBranchIndex),
      branch_index: artifactBranchIndexHasDetail ? artifactBranchIndex : (derivedBranchIndex.length ? derivedBranchIndex : artifactBranchIndex),
    }
    : null;
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
  const branchCount = branches.length || comparisonArtifact?.branchIndex?.length || comparisonArtifact?.branchWorkspaceIds?.length || 0;
  return {
    ...scenarioLab,
    question,
    comparison_question: question,
    summary,
    recommendation,
    branchCount,
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
  const pinnedContext = normalizedPayload.pinned_context || normalizedPayload.pinnedContext || normalizedPayload.selected_record || normalizedPayload.selectedRecord || null;
  const semanticFrame = normalizeSemanticFrame(normalizedPayload.semantic_frame || normalizedPayload.semanticFrame);
  const responseMode = normalizeResponseMode(normalizedPayload.response_mode || normalizedPayload.responseMode, recallItems.length);
  const answerBasis = normalizeAnswerBasis(normalizedPayload.answer_basis || normalizedPayload.answerBasis, {
    responseMode,
    recallItems,
  });
  const workspaceContextScope = normalizeWorkspaceContextScope(normalizedPayload.workspace?.context_scope);
  const interpretation = normalizeTurnInterpretation(normalizedPayload.turn_interpretation || normalizedPayload.turnInterpretation);
  const providedContextBudget = normalizedPayload.context_budget || normalizedPayload.contextBudget;
  const contextBudget = providedContextBudget
    ? normalizeContextBudget(providedContextBudget, {
      responseMode,
      answerBasis,
      recallItems,
      workspaceContextScope,
      interpretation,
    })
    : null;
  return {
    recallItems,
    workingMemoryItems: recallItems,
    learnedItems: normalizeLearnedItems(normalizedPayload),
    memoryTraceRecord: normalizeMemoryTraceRecord(normalizedPayload.memory_trace_record || normalizedPayload.memoryTraceRecord),
    responseMode,
    answerBasis,
    contextBudget,
    scenarioLab: normalizeScenarioLabPayload(normalizedPayload.scenario_lab),
    semanticFrame,
    semanticPolicy: normalizeSemanticPolicy(normalizedPayload.semantic_policy || normalizedPayload.semanticPolicy, semanticFrame),
    systemState: normalizeSystemState(normalizedPayload.system_state || normalizedPayload.systemState),
    activity: normalizeActivity(normalizedPayload.activity || normalizedPayload.activities || normalizedPayload.events),
    turnStage: normalizeTurnStage(normalizedPayload.turn_stage || normalizedPayload.turnStage),
    stageProgress: normalizeStageProgress(normalizedPayload.stage_progress || normalizedPayload.stageProgress),
    stageAudit: normalizeStageAudit(normalizedPayload.stage_audit || normalizedPayload.stageAudit),
    workspaceUpdate: normalizeWorkspaceUpdate(normalizedPayload.workspace_update, normalizedPayload.workspace),
    workspaceContextScope,
    pinnedContextId: normalizedPayload.pinned_context_id || normalizedPayload.pinnedContextId || normalizedPayload.selected_record_id || normalizedPayload.selectedRecordId || null,
    pinnedContext,
    selectedRecordId: normalizedPayload.selected_record_id || normalizedPayload.selectedRecordId || normalizedPayload.pinned_context_id || normalizedPayload.pinnedContextId || null,
    selectedRecord: pinnedContext,
  };
}

export function normalizeProtocolMetadata(item) {
  const source = item && typeof item === "object" ? item : {};
  const protocol = source.protocol && typeof source.protocol === "object" ? source.protocol : {};
  const metadata = source.metadata && typeof source.metadata === "object" ? source.metadata : {};
  const variables = firstObject(protocol.variables, source.variables, metadata.variables);
  const protocolKind = normalizeSemanticToken(
    protocol.protocol_kind
      || protocol.protocolKind
      || source.protocol_kind
      || source.protocolKind
      || metadata.protocol_kind
      || metadata.protocolKind
      || "",
    "",
  );
  return {
    protocolKind,
    variables,
    appliesTo: normalizeSemanticStringList(
      protocol.applies_to
        || protocol.appliesTo
        || source.applies_to
        || source.appliesTo
        || metadata.applies_to
        || metadata.appliesTo
        || [],
    ),
    modifiable: normalizeInterpretationBoolean(
      protocol.modifiable
        ?? source.modifiable
        ?? metadata.modifiable
        ?? true,
    ) ?? true,
    isBuiltin: normalizeInterpretationBoolean(
      protocol.is_builtin
        ?? protocol.isBuiltin
        ?? source.is_builtin
        ?? source.isBuiltin
        ?? metadata.is_builtin
        ?? metadata.isBuiltin,
    ) ?? false,
    overridesBuiltin: normalizeInterpretationBoolean(
      protocol.overrides_builtin
        ?? protocol.overridesBuiltin
        ?? source.overrides_builtin
        ?? source.overridesBuiltin
        ?? metadata.overrides_builtin
        ?? metadata.overridesBuiltin,
    ) ?? false,
  };
}

export function normalizeSystemState(systemState) {
  if (!systemState || typeof systemState !== "object") {
    return null;
  }
  const experiment = systemState.experiment && typeof systemState.experiment === "object"
    ? systemState.experiment
    : {};
  const user = systemState.user && typeof systemState.user === "object"
    ? systemState.user
    : {};
  return {
    mode: normalizeSemanticToken(systemState.mode || systemState.runtime_mode || systemState.runtimeMode, ""),
    scope: normalizeSemanticToken(systemState.scope || systemState.workspace_scope || systemState.workspaceScope, ""),
    userId: String(user.id || systemState.user_id || systemState.userId || "").trim(),
    nexusEnabled: normalizeInterpretationBoolean(systemState.nexus_enabled ?? systemState.nexusEnabled),
    experiment: {
      active: normalizeInterpretationBoolean(experiment.active ?? systemState.experiment_active ?? systemState.experimentActive) ?? false,
      sessionId: String(experiment.session_id || experiment.sessionId || systemState.experiment_session_id || systemState.experimentSessionId || "").trim(),
    },
  };
}

export function normalizeActivity(activity) {
  const source = Array.isArray(activity)
    ? activity
    : activity && typeof activity === "object" && Array.isArray(activity.steps)
      ? activity.steps
      : activity && typeof activity === "object" && Array.isArray(activity.items)
        ? activity.items
        : activity && typeof activity === "object" && Array.isArray(activity.events)
          ? activity.events
          : activity && typeof activity === "object"
            ? [activity]
            : [];
  return source
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      type: normalizeSemanticToken(item.type || item.kind || item.event, "activity"),
      label: normalizeSemanticDisplayText(item.label || item.title || item.type || item.kind || "Activity"),
      message: normalizeSemanticDisplayText(item.message || item.summary || item.detail || item.reason || ""),
      tone: normalizeSemanticToken(item.tone || item.status || "", "neutral"),
      source: normalizeSemanticToken(item.source || item.origin || "", ""),
      quiet: normalizeInterpretationBoolean(item.quiet ?? item.subtle) ?? true,
      createdAt: String(item.created_at || item.createdAt || item.timestamp || "").trim(),
    }))
    .filter((item) => item.label || item.message);
}

export function normalizeTurnStage(turnStage) {
  if (turnStage === null || turnStage === undefined || turnStage === "") {
    return null;
  }
  if (typeof turnStage === "string" || typeof turnStage === "number") {
    const label = normalizeSafeStageDisplayText(turnStage, { maxLength: STAGE_LABEL_MAX_LENGTH });
    return label ? { key: normalizeSemanticToken(label, "stage"), label, status: "", message: "" } : null;
  }
  if (!turnStage || typeof turnStage !== "object" || Array.isArray(turnStage)) {
    return null;
  }
  const key = normalizeSafeStageToken(turnStage.key || turnStage.stage_id || turnStage.id || turnStage.name || turnStage.label || turnStage.contract || "", "");
  const label = normalizeSafeStageDisplayText(
    turnStage.label || turnStage.title || turnStage.name || turnStage.stage || turnStage.contract || turnStage.task_kind || turnStage.key,
    { maxLength: STAGE_LABEL_MAX_LENGTH },
  );
  const status = normalizeSemanticToken(turnStage.status || turnStage.state || turnStage.phase || "", "");
  const message = normalizeSafeStageDisplayText(
    turnStage.message || turnStage.public_summary || turnStage.reason || turnStage.summary || turnStage.note || turnStage.detail || "",
    { maxLength: STAGE_MESSAGE_MAX_LENGTH },
  );
  const progress = normalizeStageProgressValue(
    turnStage.progress ?? turnStage.percent ?? turnStage.percentage,
  );
  if (!key && !label && !status && !message && progress === null) {
    return null;
  }
  return {
    key: key || normalizeSafeStageToken(label || status || "stage", "stage"),
    label,
    status,
    message,
    progress,
  };
}

export function normalizeStageProgress(stageProgress) {
  const source = normalizeStageCollectionSource(stageProgress);
  return source
    .map((item) => normalizeStageProgressItem(item))
    .filter(Boolean)
    .slice(0, 8);
}

export function normalizeStageAudit(stageAudit) {
  if (!stageAudit || typeof stageAudit !== "object") {
    return null;
  }
  const source = normalizeStageCollectionSource(stageAudit);
  const items = source
    .map((item) => normalizeStageAuditItem(item))
    .filter(Boolean)
    .slice(0, 8);
  const summary = normalizeSafeStageDisplayText(
    stageAudit.summary
      || stageAudit.message
      || stageAudit.note
      || (Array.isArray(stageAudit.issues) ? stageAudit.issues.join("; ") : "")
      || stageAudit.status
      || "",
    { maxLength: STAGE_AUDIT_MAX_LENGTH },
  );
  const rawStatus = stageAudit.status || stageAudit.state || "";
  const status = normalizeSemanticToken(rawStatus, "");
  const safeStatus = status && !isHiddenStageDisplayText(rawStatus) ? status : "";
  if (!summary && !safeStatus && !items.length) {
    return null;
  }
  return {
    summary,
    status: safeStatus,
    items,
  };
}

export function normalizeSafeStageDisplayText(value, { maxLength = STAGE_MESSAGE_MAX_LENGTH } = {}) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text || isHiddenStageDisplayText(text)) {
    return "";
  }
  return clampDisplayText(text, maxLength);
}

function normalizeStageCollectionSource(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (!value || typeof value !== "object") {
    return [];
  }
  if (Array.isArray(value.steps)) {
    return value.steps;
  }
  if (Array.isArray(value.items)) {
    return value.items;
  }
  if (Array.isArray(value.events)) {
    return value.events;
  }
  if (Array.isArray(value.progress)) {
    return value.progress;
  }
  return [value];
}

function normalizeStageProgressItem(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    const message = normalizeSafeStageDisplayText(item, { maxLength: STAGE_MESSAGE_MAX_LENGTH });
    return message ? { key: normalizeSemanticToken(message, "stage"), label: "", status: "", message, progress: null, createdAt: "" } : null;
  }
  const rawLabel = item.label || item.title || item.name || item.stage || item.type || item.kind;
  const rawMessage = item.message || item.summary || item.detail || item.note || item.reason || "";
  const rawStatus = item.status || item.state || item.phase || "";
  if (hasHiddenStageItemText(rawLabel, rawMessage, rawStatus)) {
    return null;
  }
  const label = normalizeSafeStageDisplayText(
    rawLabel,
    { maxLength: STAGE_LABEL_MAX_LENGTH },
  );
  const message = normalizeSafeStageDisplayText(
    rawMessage,
    { maxLength: STAGE_MESSAGE_MAX_LENGTH },
  );
  const status = normalizeSemanticToken(rawStatus, "");
  const safeStatus = status && !isHiddenStageDisplayText(rawStatus) ? status : "";
  const progress = normalizeStageProgressValue(item.progress ?? item.percent ?? item.percentage);
  if (!label && !message && !safeStatus && progress === null) {
    return null;
  }
  return {
    key: normalizeSafeStageToken(item.key || item.id || label || safeStatus || "stage", "stage"),
    label,
    status: safeStatus,
    message,
    progress,
    createdAt: String(item.created_at || item.createdAt || item.timestamp || "").trim(),
  };
}

function normalizeStageAuditItem(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    const message = normalizeSafeStageDisplayText(item, { maxLength: STAGE_AUDIT_MAX_LENGTH });
    return message ? { label: "", message, status: "" } : null;
  }
  const rawLabel = item.label || item.title || item.name || item.check || item.type || item.kind;
  const rawMessage = item.message || item.summary || item.detail || item.note || "";
  const rawStatus = item.status || item.state || item.result || "";
  if (hasHiddenStageItemText(rawLabel, rawMessage, rawStatus)) {
    return null;
  }
  const label = normalizeSafeStageDisplayText(
    rawLabel,
    { maxLength: STAGE_LABEL_MAX_LENGTH },
  );
  const message = normalizeSafeStageDisplayText(
    rawMessage,
    { maxLength: STAGE_AUDIT_MAX_LENGTH },
  );
  const status = normalizeSemanticToken(rawStatus, "");
  const safeStatus = status && !isHiddenStageDisplayText(rawStatus) ? status : "";
  if (!label && !message && !safeStatus) {
    return null;
  }
  return {
    label,
    message,
    status: safeStatus,
  };
}

function normalizeStageProgressValue(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  if (numeric <= 1 && numeric >= 0) {
    return Math.round(numeric * 100);
  }
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function normalizeSafeStageToken(value, fallback = "") {
  return isHiddenStageDisplayText(value) ? fallback : normalizeSemanticToken(value, fallback);
}

function isHiddenStageDisplayText(value) {
  return HIDDEN_STAGE_TEXT_PATTERN.test(String(value || ""));
}

function hasHiddenStageItemText(...values) {
  return values.some((value) => value !== null && value !== undefined && isHiddenStageDisplayText(value));
}

function clampDisplayText(text, maxLength) {
  const normalizedMax = Number.isFinite(Number(maxLength)) ? Math.max(12, Number(maxLength)) : STAGE_MESSAGE_MAX_LENGTH;
  if (text.length <= normalizedMax) {
    return text;
  }
  return `${text.slice(0, normalizedMax - 3).trimEnd()}...`;
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

function normalizeAnswerBasisSources(sources) {
  const sourceList = Array.isArray(sources)
    ? sources
    : typeof sources === "string"
      ? [sources]
      : [];
  return [...new Set(
    sourceList
      .map((source) => normalizeAnswerBasisSource(source))
      .filter(Boolean),
  )];
}

function normalizeAnswerBasisSource(source) {
  const normalized = String(source || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  switch (normalized) {
    case "working_memory":
    case "memory":
    case "memories":
    case "recalled_memory":
    case "recalled_items":
      return "recall";
    case "draft":
    case "active_whiteboard":
    case "whiteboard_context":
      return "whiteboard";
    case "prior_whiteboard":
    case "earlier_whiteboard":
      return "pending_whiteboard";
    case "conversation":
    case "recent_conversation":
      return "recent_chat";
    case "protocol":
    case "protocols":
    case "protocol_guidance":
    case "guidance":
      return "protocol";
    case "recall":
    case "whiteboard":
    case "recent_chat":
    case "pending_whiteboard":
      return normalized;
    default:
      return "";
  }
}

function deriveAnswerBasisContextSources({
  responseContextSources = [],
  memoryCount = 0,
  protocolCount = 0,
} = {}) {
  return normalizeAnswerBasisSources([
    ...responseContextSources.filter((source) => source !== "recall" || memoryCount > 0 || protocolCount === 0),
    ...(memoryCount > 0 ? ["recall"] : []),
    ...(protocolCount > 0 ? ["protocol"] : []),
  ]);
}

function deriveAnswerBasisEvidenceSources({
  contextSources = [],
  memoryCount = 0,
  protocolCount = 0,
} = {}) {
  return normalizeAnswerBasisSources(
    contextSources.filter((source) => source !== "protocol" && (
      source !== "recall" || memoryCount > 0 || protocolCount === 0
    )),
  );
}

function normalizeAnswerBasisCounts(counts, fallback = {}) {
  const source = counts && typeof counts === "object" ? counts : {};
  const recall = normalizeCountAlias(source, ["recall", "recall_count", "recallCount", "recalled", "recalled_count", "working_memory", "workingMemory", "working_memory_count", "workingMemoryCount"], fallback.recall);
  const memory = normalizeCountAlias(source, ["memory", "memory_count", "memoryCount", "evidence_memory", "evidenceMemory"], fallback.memory ?? recall);
  const protocol = normalizeCountAlias(source, ["protocol", "protocol_count", "protocolCount", "protocols", "protocols_count", "protocolsCount"], fallback.protocol);
  const whiteboard = normalizeCountAlias(source, ["whiteboard", "whiteboard_count", "whiteboardCount"], fallback.whiteboard);
  const recentChat = normalizeCountAlias(source, ["recent_chat", "recentChat", "recent_chat_count", "recentChatCount"], fallback.recentChat);
  const pendingWhiteboard = normalizeCountAlias(source, ["pending_whiteboard", "pendingWhiteboard", "pending_whiteboard_count", "pendingWhiteboardCount"], fallback.pendingWhiteboard);
  const evidence = normalizeCountAlias(source, ["evidence", "evidence_count", "evidenceCount", "factual", "factual_count", "factualCount"], fallback.evidence);
  const guidance = normalizeCountAlias(source, ["guidance", "guidance_count", "guidanceCount"], fallback.guidance);
  const context = normalizeCountAlias(source, ["context", "context_count", "contextCount"], fallback.context);
  const sources = normalizeCountAlias(source, ["sources", "source_count", "sourceCount"], fallback.sources);
  return {
    recall,
    memory,
    protocol,
    protocols: protocol,
    whiteboard,
    recentChat,
    pendingWhiteboard,
    evidence,
    guidance,
    context,
    sources,
  };
}

function normalizeCountAlias(source, aliases, fallback = 0) {
  for (const alias of aliases) {
    if (Number.isFinite(Number(source[alias]))) {
      return Math.max(0, Number(source[alias]));
    }
  }
  return Number.isFinite(Number(fallback)) ? Math.max(0, Number(fallback)) : 0;
}

function normalizeAnswerBasisKind(kind, {
  responseMode = null,
  contextSources = [],
  evidenceSources = [],
  guidanceSources = [],
  counts = {},
  hasFactualGrounding = false,
} = {}) {
  const normalizedKind = String(kind || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  switch (normalizedKind) {
    case "intuitive":
    case "intuitive_answer":
    case "best_guess":
    case "ungrounded":
      return "intuitive_answer";
    case "memory":
    case "memory_backed":
    case "recall":
    case "recall_grounded":
    case "working_memory":
    case "working_memory_grounded":
      return "memory_backed";
    case "protocol":
    case "protocol_guided":
    case "guided":
      return "protocol_guided";
    case "whiteboard":
    case "whiteboard_grounded":
    case "pending_whiteboard":
    case "pending_whiteboard_grounded":
    case "prior_whiteboard":
      return "whiteboard_grounded";
    case "recent_chat":
    case "recent_chat_grounded":
      return "recent_chat";
    case "mixed":
    case "mixed_context":
    case "mixed_context_grounded":
      return "mixed_context";
    case "idle":
      return "idle";
    default:
      break;
  }

  const sourceGroups = new Set();
  if ((counts.memory || counts.recall) > 0 || evidenceSources.includes("recall")) {
    sourceGroups.add("memory");
  }
  if (guidanceSources.includes("protocol") || contextSources.includes("protocol") || counts.protocol > 0) {
    sourceGroups.add("protocol");
  }
  if (
    contextSources.includes("whiteboard")
    || contextSources.includes("pending_whiteboard")
    || evidenceSources.includes("whiteboard")
    || evidenceSources.includes("pending_whiteboard")
  ) {
    sourceGroups.add("whiteboard");
  }
  if (contextSources.includes("recent_chat") || evidenceSources.includes("recent_chat")) {
    sourceGroups.add("recent_chat");
  }
  if (sourceGroups.size > 1) {
    return "mixed_context";
  }
  if (sourceGroups.has("memory")) {
    return "memory_backed";
  }
  if (sourceGroups.has("protocol")) {
    return "protocol_guided";
  }
  if (sourceGroups.has("whiteboard")) {
    return "whiteboard_grounded";
  }
  if (sourceGroups.has("recent_chat")) {
    return "recent_chat";
  }
  if (hasFactualGrounding) {
    return "memory_backed";
  }

  const responseKind = String(responseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(responseMode?.groundingMode || responseMode?.grounding_mode || "").trim().toLowerCase();
  if (responseKind === "idle" || (!responseKind && !groundingMode)) {
    return "idle";
  }
  if (responseKind === "best_guess" || groundingMode === "ungrounded") {
    return "intuitive_answer";
  }
  if (groundingMode === "whiteboard" || groundingMode === "pending_whiteboard") {
    return "whiteboard_grounded";
  }
  if (groundingMode === "recent_chat") {
    return "recent_chat";
  }
  if (groundingMode === "mixed_context") {
    return "mixed_context";
  }
  if (groundingMode === "recall" || groundingMode === "working_memory" || responseKind === "grounded") {
    return "memory_backed";
  }
  return "intuitive_answer";
}

function answerBasisLabelForKind(kind, fallbackLabel = "") {
  switch (kind) {
    case "intuitive_answer":
      return "Intuitive Answer";
    case "memory_backed":
      return "Memory-Backed";
    case "protocol_guided":
      return "Protocol-Guided";
    case "whiteboard_grounded":
      return "Whiteboard-Grounded";
    case "mixed_context":
      return "Mixed Context";
    case "recent_chat":
      return "Recent Chat";
    case "idle":
      return "Idle";
    default: {
      const label = sanitizeAnswerBasisCopy(fallbackLabel);
      return label || "Intuitive Answer";
    }
  }
}

function answerBasisNoteForKind(kind, counts = {}, contextSources = [], evidenceSources = [], guidanceSources = []) {
  switch (kind) {
    case "intuitive_answer":
      return "This was an intuitive answer from the current request, without grounded Vantage context.";
    case "memory_backed": {
      const count = counts.memory || counts.recall || 0;
      return count
        ? `Backed by ${count} memory item${count === 1 ? "" : "s"} from Recall.`
        : "Backed by surfaced memory context.";
    }
    case "protocol_guided":
      return "Guided by reusable protocol context; no factual memory evidence was used.";
    case "whiteboard_grounded":
      return contextSources.includes("pending_whiteboard") && !contextSources.includes("whiteboard")
        ? "Grounded in prior whiteboard context."
        : "Grounded in the whiteboard draft context.";
    case "mixed_context":
      return `Combined ${describeAnswerBasisSources([...evidenceSources, ...guidanceSources, ...contextSources])}.`;
    case "recent_chat":
      return "Grounded in recent chat continuity.";
    default:
      return "Waiting for a turn.";
  }
}

function describeAnswerBasisSources(sources = []) {
  const labels = normalizeAnswerBasisSources(sources)
    .map((source) => {
      switch (source) {
        case "recall":
          return "memory";
        case "protocol":
          return "protocol guidance";
        case "whiteboard":
          return "whiteboard context";
        case "pending_whiteboard":
          return "prior whiteboard context";
        case "recent_chat":
          return "recent chat";
        default:
          return "";
      }
    })
    .filter(Boolean);
  return joinReadableList([...new Set(labels)]) || "multiple context sources";
}

function sanitizeAnswerBasisCopy(value) {
  return String(value || "").trim().replace(/\bbest guess\b/ig, "Intuitive Answer");
}

function countIncludedContextSources(sources, included) {
  return included.filter((source) => sources.includes(source)).length;
}

function isProtocolAnswerBasisItem(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const type = String(item.type || "").trim().toLowerCase();
  const kind = String(item.kind || "").trim().toLowerCase();
  const source = String(item.source || "").trim().toLowerCase();
  const protocol = normalizeProtocolMetadata(item);
  return type === "protocol"
    || kind === "protocol"
    || source === "protocol"
    || Boolean(protocol.protocolKind);
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
  const branchIndex = normalizeComparisonBranchIndex(artifact.branch_index || artifact.branchIndex, artifact.branch_workspace_ids || artifact.branchWorkspaceIds);
  const branchWorkspaceIds = branchIndex.length
    ? branchIndex.map((branch) => branch.workspace_id).filter(Boolean)
    : Array.isArray(artifact.branch_workspace_ids)
      ? artifact.branch_workspace_ids.map((item) => String(item || "").trim()).filter(Boolean)
      : Array.isArray(artifact.branchWorkspaceIds)
        ? artifact.branchWorkspaceIds.map((item) => String(item || "").trim()).filter(Boolean)
        : [];
  return {
    ...artifact,
    id: normalizeRecordId(artifact),
    title: firstNonEmptyString(artifact.title) || "Scenario comparison",
    card: firstNonEmptyString(artifact.card, sections.summary.text),
    body,
    recommendation,
    comparisonQuestion: firstNonEmptyString(artifact.comparison_question),
    branchWorkspaceIds,
    branchIndex,
    branch_index: branchIndex,
    sections,
  };
}

export function normalizeComparisonBranchIndex(branchIndex, branchWorkspaceIds = []) {
  const normalized = [];
  const source = Array.isArray(branchIndex) ? branchIndex : [];
  for (const item of source) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const workspaceId = firstNonEmptyString(item.workspace_id, item.workspaceId, item.id);
    if (!workspaceId) {
      continue;
    }
    const entry = {
      ...item,
      workspaceId,
      workspace_id: workspaceId,
      title: firstNonEmptyString(item.title) || "",
      label: firstNonEmptyString(item.label) || "",
      summary: firstNonEmptyString(item.summary, item.card) || "",
    };
    normalized.push(entry);
  }
  if (normalized.length) {
    return normalized;
  }
  return normalizeBranchWorkspaceIds(branchWorkspaceIds);
}

function normalizeBranchWorkspaceIds(branchWorkspaceIds) {
  if (!Array.isArray(branchWorkspaceIds)) {
    return [];
  }
  return branchWorkspaceIds
    .map((workspaceId) => {
      const normalized = firstNonEmptyString(workspaceId);
      return normalized ? { workspaceId: normalized, workspace_id: normalized } : null;
    })
    .filter(Boolean);
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
  const preservePinnedContext = normalizeInterpretationBoolean(
    interpretation.preserve_pinned_context
      ?? interpretation.preservePinnedContext
      ?? interpretation.preserve_selected_record
      ?? interpretation.preserveSelectedRecord,
  );
  const pinnedContextReason = String(
    interpretation.pinned_context_reason
      ?? interpretation.pinnedContextReason
      ?? interpretation.selected_record_reason
      ?? interpretation.selectedRecordReason
      ?? "",
  ).trim() || "";
  return {
    mode: String(interpretation.mode || "").trim().toLowerCase() || "chat",
    confidence: Number.isFinite(confidence) ? confidence : 0,
    reason: String(interpretation.reason || "").trim(),
    requestedWhiteboardMode: String(interpretation.requested_whiteboard_mode || "").trim().toLowerCase() || null,
    resolvedWhiteboardMode: String(interpretation.resolved_whiteboard_mode || "").trim().toLowerCase() || null,
    whiteboardModeSource: String(interpretation.whiteboard_mode_source || "").trim().toLowerCase() || null,
    controlPanel: normalizeControlPanel(interpretation.control_panel || interpretation.controlPanel),
    preservePinnedContext,
    pinnedContextReason,
    preserveSelectedRecord: preservePinnedContext,
    selectedRecordReason: pinnedContextReason,
  };
}

export function normalizeControlPanel(controlPanel) {
  if (!controlPanel || typeof controlPanel !== "object") {
    return {
      actions: [],
      workingMemoryQueries: [],
      responseCall: null,
    };
  }
  const actions = Array.isArray(controlPanel.actions)
    ? controlPanel.actions
      .filter((action) => action && typeof action === "object")
      .map((action) => ({
        ...action,
        type: String(action.type || "").trim(),
        reason: String(action.reason || "").trim(),
      }))
      .filter((action) => action.type)
    : [];
  const rawQueries = controlPanel.working_memory_queries || controlPanel.workingMemoryQueries;
  const workingMemoryQueries = Array.isArray(rawQueries)
    ? rawQueries.map((query) => String(query || "").trim()).filter(Boolean)
    : [];
  const responseCall = controlPanel.response_call || controlPanel.responseCall || null;
  return {
    actions,
    workingMemoryQueries,
    responseCall: responseCall && typeof responseCall === "object" ? responseCall : null,
  };
}

export function normalizeSemanticFrame(frame) {
  if (!frame || typeof frame !== "object") {
    return null;
  }
  const confidence = Number(frame.confidence);
  const referencedObject = frame.referenced_object || frame.referencedObject || null;
  return {
    userGoal: String(frame.user_goal || frame.userGoal || "").trim(),
    taskType: normalizeSemanticToken(frame.task_type || frame.taskType, "question_answering"),
    followUpType: normalizeSemanticToken(frame.follow_up_type || frame.followUpType, "new_request"),
    targetSurface: normalizeSemanticToken(frame.target_surface || frame.targetSurface, "chat"),
    referencedObject: referencedObject && typeof referencedObject === "object"
      ? {
        id: String(referencedObject.id || referencedObject.record_id || "").trim(),
        title: String(referencedObject.title || referencedObject.name || "").trim(),
        type: String(referencedObject.type || "").trim(),
        source: String(referencedObject.source || "").trim(),
      }
      : null,
    confidence: Number.isFinite(confidence) ? confidence : 0,
    needsClarification: Boolean(frame.needs_clarification ?? frame.needsClarification),
    clarificationPrompt: String(frame.clarification_prompt || frame.clarificationPrompt || "").trim() || null,
    signals: frame.signals && typeof frame.signals === "object" ? { ...frame.signals } : {},
    commitments: Array.isArray(frame.commitments)
      ? frame.commitments.map((item) => String(item || "").trim()).filter(Boolean)
      : [],
  };
}

export function normalizeSemanticPolicy(policy, semanticFrame = null) {
  if (!policy || typeof policy !== "object") {
    return null;
  }
  const confidence = Number(policy.confidence);
  const needsClarification = normalizeInterpretationBoolean(
    policy.needs_clarification
      ?? policy.needsClarification
      ?? policy.ask_clarification
      ?? policy.askClarification
      ?? policy.should_clarify
      ?? policy.shouldClarify
      ?? semanticFrame?.needsClarification,
  ) ?? false;
  const clarificationPrompt = normalizeSemanticDisplayText(
    policy.clarification_prompt
      || policy.clarificationPrompt
      || policy.prompt
      || semanticFrame?.clarificationPrompt
      || "",
  ) || null;
  return {
    semanticAction: normalizeSemanticToken(
      policy.semantic_action
        || policy.semanticAction
        || policy.action
        || policy.action_type
        || policy.actionType
        || policy.action_kind
        || policy.actionKind
        || policy.recommended_action
        || policy.recommendedAction,
      needsClarification ? "ask_clarification" : "respond",
    ),
    actionLabel: normalizeSemanticDisplayText(policy.action_label || policy.actionLabel),
    needsClarification,
    clarificationPrompt,
    clarificationOptions: normalizeSemanticStringList(policy.clarification_options || policy.clarificationOptions || policy.options),
    status: normalizeSemanticToken(policy.status || policy.state, needsClarification ? "needs_clarification" : "ready"),
    reason: normalizeSemanticDisplayText(policy.reason || policy.rationale || policy.summary),
    confidence: Number.isFinite(confidence) ? confidence : 0,
    blocking: Boolean(policy.blocking ?? policy.is_blocking ?? policy.isBlocking ?? needsClarification),
    signals: policy.signals && typeof policy.signals === "object" ? { ...policy.signals } : {},
  };
}

function normalizeSemanticDisplayText(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function normalizeSemanticStringList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => normalizeSemanticDisplayText(item)).filter(Boolean);
}

function normalizeSemanticToken(value, fallback) {
  return String(value || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || fallback;
}

function firstObject(...values) {
  for (const value of values) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return { ...value };
    }
  }
  return {};
}

function normalizeInterpretationBoolean(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "boolean") {
    return value;
  }
  const normalized = String(value).trim().toLowerCase();
  if (["true", "yes", "1"].includes(normalized)) {
    return true;
  }
  if (["false", "no", "0"].includes(normalized)) {
    return false;
  }
  return null;
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
      normalized.summary = "Vantage suggested continuing this work in the whiteboard.";
    } else if (normalized.status === "draft_ready") {
      normalized.summary = "A whiteboard draft is ready to review before it enters the whiteboard.";
    } else if (normalized.status === "updated") {
      normalized.summary = "The whiteboard was updated from this turn.";
    }
  }
  return normalized;
}
