import {
  normalizeAnswerBasis,
  normalizeLearnedItems,
  normalizeProtocolMetadata,
  normalizeResponseMode,
} from "./turn_payloads.mjs?v=20260429-answer-basis-2";

function pluralize(word, count) {
  if (word === "branch") {
    return count === 1 ? "branch" : "branches";
  }
  return `${word}${count === 1 ? "" : "s"}`;
}

function scenarioLabBranchCount(scenarioLab) {
  if (!scenarioLab || typeof scenarioLab !== "object") {
    return 0;
  }
  if (Array.isArray(scenarioLab.branches) && scenarioLab.branches.length) {
    return scenarioLab.branches.length;
  }
  const comparisonArtifact = scenarioLab.comparisonArtifact
    || scenarioLab.comparison_artifact
    || null;
  if (Array.isArray(comparisonArtifact?.branchIndex) && comparisonArtifact.branchIndex.length) {
    return comparisonArtifact.branchIndex.length;
  }
  if (Array.isArray(comparisonArtifact?.branch_index) && comparisonArtifact.branch_index.length) {
    return comparisonArtifact.branch_index.length;
  }
  if (Array.isArray(comparisonArtifact?.branchWorkspaceIds) && comparisonArtifact.branchWorkspaceIds.length) {
    return comparisonArtifact.branchWorkspaceIds.length;
  }
  if (Array.isArray(comparisonArtifact?.branch_workspace_ids) && comparisonArtifact.branch_workspace_ids.length) {
    return comparisonArtifact.branch_workspace_ids.length;
  }
  return 0;
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
    return "idea";
  }
  if (source === "memory" || kind === "memory" || type === "memory") {
    return "note";
  }
  if (source === "artifact" || kind === "artifact" || type === "artifact" || type === "scenario_comparison") {
    return "work product";
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
  const answerBasis = normalizeAnswerBasisFromPayload(payload);
  if (answerBasis && answerBasis.kind !== "idle") {
    return answerBasis.label;
  }
  const responseMode = normalizeResponseMode(payload?.response_mode, recallCountFromPayload(payload));
  return responseModeEvidenceLabel(responseMode, payload);
}

export function describeResponseModeLabel(responseMode = null, recallCount = 0, answerBasis = null) {
  const normalizedAnswerBasis = answerBasis && typeof answerBasis === "object"
    ? normalizeAnswerBasis(answerBasis, { responseMode })
    : null;
  if (normalizedAnswerBasis && normalizedAnswerBasis.kind !== "idle") {
    return normalizedAnswerBasis.label;
  }
  const kind = String(responseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(responseMode?.groundingMode || responseMode?.grounding_mode || "").trim().toLowerCase();
  const contextSources = responseModeContextSources(responseMode);
  if (!kind || kind === "idle") {
    return "";
  }
  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "Intuitive Answer";
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
  answerBasis = null,
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
  const normalizedAnswerBasis = normalizeAnswerBasis(answerBasis, {
    responseMode: normalizedResponseMode,
    recallItems: Array.isArray(recallItems) && recallItems.length ? recallItems : workingMemoryItems,
  });
  const responseRecallCount = Number.isFinite(Number(normalizedResponseMode?.recallCount))
    ? Number(normalizedResponseMode.recallCount)
    : Number.isFinite(Number(normalizedResponseMode?.workingMemoryCount))
      ? Number(normalizedResponseMode.workingMemoryCount)
      : visibleRecallCount;
  const answerBasisRecallCount = Number.isFinite(Number(normalizedAnswerBasis?.counts?.recall))
    ? Number(normalizedAnswerBasis.counts.recall)
    : null;
  const recallCount = normalizedAnswerBasis?.kind && normalizedAnswerBasis.kind !== "idle"
    ? (answerBasisRecallCount ?? responseRecallCount)
    : responseRecallCount;
  const groundingLabel = describeResponseModeLabel(normalizedResponseMode, recallCount, normalizedAnswerBasis) || "Idle";
  const responseKind = String(normalizedResponseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(normalizedResponseMode?.groundingMode || "").trim().toLowerCase();
  const groundingSources = normalizedAnswerBasis?.kind && normalizedAnswerBasis.kind !== "idle"
    ? normalizedAnswerBasis.contextSources
    : Array.isArray(normalizedResponseMode?.contextSources)
      ? normalizedResponseMode.contextSources
      : Array.isArray(normalizedResponseMode?.groundingSources)
        ? normalizedResponseMode.groundingSources
        : [];
  const isIdle = responseKind === "idle" && normalizedAnswerBasis?.kind === "idle";
  const hasAnswerBasisContext = Boolean(
    normalizedAnswerBasis?.kind
      && !["idle", "intuitive_answer"].includes(normalizedAnswerBasis.kind),
  );
  const isBestGuess = normalizedAnswerBasis?.kind === "intuitive_answer"
    || (responseKind === "best_guess" && !hasAnswerBasisContext);
  const hasGroundedContext = responseKind === "grounded" || hasAnswerBasisContext;
  const hasBroaderGrounding = hasGroundedContext && (
    ["whiteboard", "recent_chat", "pending_whiteboard", "mixed_context"].includes(groundingMode)
    || groundingSources.some((source) => normalizeContextSourceName(source) !== "recall")
    || ["protocol_guided", "whiteboard_grounded", "mixed_context", "recent_chat"].includes(normalizedAnswerBasis?.kind)
  );

  return {
    responseMode: normalizedResponseMode,
    answerBasis: normalizedAnswerBasis,
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
    hasFactualGrounding: Boolean(normalizedAnswerBasis?.hasFactualGrounding),
    evidenceSources: Array.isArray(normalizedAnswerBasis?.evidenceSources) ? normalizedAnswerBasis.evidenceSources : [],
    guidanceSources: Array.isArray(normalizedAnswerBasis?.guidanceSources) ? normalizedAnswerBasis.guidanceSources : [],
    isBestGuess,
    isIdle,
  };
}

function normalizeRecallReasonText(value) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text) {
    return "";
  }
  if (/[=:]/.test(text) && /\btitle=|\bcard=|\bbody=|\bcontext=|\bmetadata=/.test(text)) {
    return "";
  }
  return text.endsWith(".") ? text : `${text}.`;
}

export function describeRecallReason(item = null) {
  const provided = normalizeRecallReasonText(
    item?.recallReason
    || item?.recall_reason
    || item?.whyRecalled
    || item?.why_recalled
    || item?.userReason
    || item?.user_reason,
  );
  if (provided) {
    return provided;
  }

  const source = String(item?.source || "").trim().toLowerCase();
  const type = String(item?.type || "").trim().toLowerCase();
  if (source === "memory_trace") {
    return "Recent memory trace looked relevant to this turn.";
  }
  if (source === "vault_note") {
    return "A reference note looked relevant to this request.";
  }
  if (source === "artifact" || type === "artifact" || type === "scenario_comparison" || type === "scenario comparison") {
    return "A prior work product looked relevant to this request.";
  }
  if (source === "memory") {
    return "A saved memory looked relevant to this request.";
  }
  if (type === "protocol") {
    return "A reusable protocol was applied to guide this turn.";
  }
  if (source === "concept" || type === "concept") {
    return "A reusable idea in your library looked relevant to this request.";
  }
  return "";
}

function isLearnedArtifact(item = null) {
  const source = String(item?.source || "").trim().toLowerCase();
  const type = String(item?.type || "").trim().toLowerCase();
  return source === "artifact" || type === "artifact" || type === "scenario_comparison" || type === "scenario comparison";
}

function isLearnedScenarioComparison(item = null) {
  const scenarioKind = String(item?.scenarioKind || item?.scenario_kind || "").trim().toLowerCase();
  return isLearnedArtifact(item) && scenarioKind === "comparison";
}

export function describeLearnedScopeLabel(item = null) {
  const durability = String(item?.durability || "").trim().toLowerCase();
  const scope = String(item?.scope || "").trim().toLowerCase();
  if (durability === "temporary" || scope === "experiment") {
    return "Temporary in this experiment";
  }
  if (durability === "durable" || scope === "durable") {
    return "Saved in your library";
  }
  return "Saved from this turn";
}

export function buildLearnedCorrectionModel(item = null) {
  const correctionKind = String(
    item?.correctionAffordance?.kind
    || item?.correction_affordance?.kind
    || "",
  ).trim().toLowerCase();
  const explicitPrimaryLabel = String(
    item?.correctionAffordance?.label
    || item?.correction_affordance?.label
    || "",
  ).trim();
  const scopeLabel = describeLearnedScopeLabel(item);
  const temporary = scopeLabel === "Temporary in this experiment";
  const canonicalPrimaryActionLabel = isLearnedArtifact(item)
    ? (isLearnedScenarioComparison(item) ? "Continue comparison in whiteboard" : "Continue in whiteboard")
    : "Revise in whiteboard";
  const normalizedExplicitLabel = explicitPrimaryLabel.toLowerCase();
  const explicitLooksLikeWhiteboardAction = correctionKind === "open_in_whiteboard" && (
    normalizedExplicitLabel === "open in whiteboard"
      || normalizedExplicitLabel.includes("whiteboard")
      || normalizedExplicitLabel.includes("revise")
      || normalizedExplicitLabel.includes("continue")
  );
  const primaryActionLabel = explicitLooksLikeWhiteboardAction && normalizedExplicitLabel !== "open in whiteboard"
    ? explicitPrimaryLabel
    : canonicalPrimaryActionLabel;
  const summary = temporary
    ? "This item is temporary in this experiment. Direct correction works through the whiteboard, and you can pin it for the next turn while you explain what should change."
    : "This item is saved in your library. Direct correction works through the whiteboard, and you can pin it for the next turn while you explain what should change.";
  const modeSummaries = {
    overview: summary,
    wrong: temporary
      ? "Not direct yet. Vantage cannot mark this temporary item as wrong directly in this build. Revise it in the whiteboard and pin it for the next turn if you want the correction carried forward."
      : "Not direct yet. Vantage cannot mark this library-saved item as wrong directly in this build. Revise it in the whiteboard and pin it for the next turn if you want the correction carried forward.",
    temporary: temporary
      ? "This item is already temporary in this experiment. It stays session-local unless you promote a later revision."
      : "Not direct yet. Changing this learned item from library-saved to temporary is not supported directly in this build. Revise it in the whiteboard during an experiment if you want a temporary follow-up instead.",
    forget: temporary
      ? "Not direct yet. Direct forget or delete is not supported here yet. This temporary item will disappear when the experiment ends unless you promote it."
      : "Not direct yet. Direct forget or delete is not supported for library-saved items yet. Leave it unpinned so it stops carrying forward, or revise it in the whiteboard to make a corrected replacement.",
  };
  const limitations = temporary
    ? [
        "Pin it for the next turn if you want to explain what should change before deciding what to keep.",
        "Direct mark-wrong, make-temporary, and forget actions are not available yet; revise it in the whiteboard to create the corrected follow-up.",
      ]
    : [
        "Revise it in the whiteboard if you want a corrected follow-up without overwriting the saved original in place.",
        "Direct mark-wrong, make-temporary, and forget actions are not available yet; pin it for the next turn or revise it in the whiteboard instead.",
      ];

  return {
    primaryActionLabel,
    keepContextLabel: "Pin for next turn",
    pinnedContextLabel: "Pinned for next turn",
    scopeLabel,
    summary,
    modeSummaries,
    limitations,
  };
}

export function describeLearnedCorrectionModeLabel(mode, scopeLabel = "") {
  const normalizedMode = String(mode || "").trim().toLowerCase();
  const temporary = String(scopeLabel || "").trim().toLowerCase() === "temporary in this experiment";
  switch (normalizedMode) {
    case "wrong":
      return "How to mark wrong";
    case "temporary":
      return temporary ? "Already temporary" : "How to make temporary";
    case "forget":
      return "How to forget";
    default:
      return "";
  }
}

export function describeScenarioRouteConfidence(confidence) {
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return {
      label: "",
      badge: "",
      summary: "",
    };
  }
  if (numeric >= 0.9) {
    return {
      label: "Clear fit",
      badge: "Clear fit",
      summary: "The navigator saw Scenario Lab as a clear fit for this request.",
    };
  }
  if (numeric >= 0.75) {
    return {
      label: "Strong fit",
      badge: "Strong fit",
      summary: "The navigator saw Scenario Lab as a strong fit for this request.",
    };
  }
  if (numeric >= 0.55) {
    return {
      label: "Possible fit",
      badge: "Possible fit",
      summary: "The navigator saw Scenario Lab as a possible fit for this request.",
    };
  }
  return {
    label: "Tentative fit",
    badge: "Tentative fit",
    summary: "Scenario Lab was chosen tentatively for this request.",
  };
}

export function describeScenarioBranchConfidence(confidence) {
  const normalized = String(confidence || "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  if (normalized.startsWith("high") || normalized.startsWith("strong")) {
    return "Stronger case";
  }
  if (normalized.startsWith("moderate") || normalized.startsWith("medium") || normalized.startsWith("balanced")) {
    return "Balanced case";
  }
  if (normalized.startsWith("low") || normalized.startsWith("weak") || normalized.startsWith("tentative")) {
    return "Riskier case";
  }
  return String(confidence || "").trim();
}

export function buildTurnAtAGlanceSummary({
  recallCount = 0,
  groundingLabel = "",
  hasGroundedContext = false,
  hasBroaderGrounding = false,
  isBestGuess = false,
  learnedCount = 0,
  scenarioLabStatus = "",
  scenarioLabBranchCount = 0,
  graphActionSummary = "",
} = {}) {
  const normalizedGrounding = String(groundingLabel || "").trim();
  const normalizedScenarioStatus = String(scenarioLabStatus || "").trim().toLowerCase();
  const parts = [];

  if (normalizedScenarioStatus === "failed") {
    parts.push("Scenario Lab fell back to chat.");
  } else if (normalizedScenarioStatus) {
    parts.push(
      scenarioLabBranchCount > 0
        ? `Scenario Lab prepared ${scenarioLabBranchCount} ${pluralize("branch", scenarioLabBranchCount)}.`
        : "Scenario Lab ran for this turn.",
    );
  } else if (isBestGuess) {
    parts.push("This was an intuitive answer from the current request.");
  } else if (recallCount > 0) {
    parts.push(`This answer used ${recallCount} recalled ${pluralize("item", recallCount)}.`);
  } else if ((hasGroundedContext || hasBroaderGrounding) && normalizedGrounding) {
    parts.push(answerBasisSummarySentence(normalizedGrounding));
  } else if (graphActionSummary) {
    parts.push(graphActionSummary);
  }

  if (learnedCount > 0) {
    parts.push(`Learned ${learnedCount} ${pluralize("item", learnedCount)} from this turn.`);
  }

  return parts.join(" ") || "This view explains why the answer happened, what entered Recall, and what changed after the turn.";
}

function answerBasisSummarySentence(label) {
  switch (String(label || "").trim()) {
    case "Protocol-Guided":
      return "Reusable protocol guidance shaped this answer.";
    case "Whiteboard-Grounded":
      return "Whiteboard context supported this answer.";
    case "Mixed Context":
      return "Multiple context sources shaped this answer.";
    case "Recent Chat":
      return "Recent chat continuity supported this answer.";
    case "Memory-Backed":
      return "Recalled memory supported this answer.";
    default:
      return `This answer used ${String(label || "").trim().toLowerCase()}.`;
  }
}

export function describeSemanticActionCopy({
  semanticPolicy = null,
  semanticFrame = null,
} = {}) {
  const explicitLabel = String(semanticPolicy?.actionLabel || "").trim();
  if (explicitLabel) {
    return explicitLabel;
  }
  const action = String(semanticPolicy?.semanticAction || "").trim().toLowerCase();
  switch (action) {
    case "ask_clarification":
    case "clarify":
      return "Ask a clarifying question";
    case "draft":
    case "draft_in_whiteboard":
      return "Draft in whiteboard";
    case "revise":
    case "revise_whiteboard":
      return "Revise the draft";
    case "compare":
    case "run_scenario_lab":
      return "Compare options";
    case "save":
    case "save_artifact":
    case "artifact_save":
      return "Save this work";
    case "publish":
    case "publish_artifact":
    case "artifact_publish":
      return "Publish artifact";
    case "inspect":
    case "show_reasoning":
    case "context_inspect":
      return "Show why";
    case "experiment_manage":
    case "manage_experiment":
      return "Manage experiment";
    case "respond":
    case "answer":
      return "Answer directly";
    default:
      return describeSemanticFrameAction(semanticFrame);
  }
}

export function describeSemanticClarificationCopy({
  semanticPolicy = null,
  semanticFrame = null,
} = {}) {
  const needsClarification = Boolean(
    semanticPolicy?.needsClarification
      ?? semanticFrame?.needsClarification,
  );
  const prompt = String(
    semanticPolicy?.clarificationPrompt
      || semanticFrame?.clarificationPrompt
      || "",
  ).trim();
  if (needsClarification) {
    return prompt || "Ask one clarifying question before continuing.";
  }
  return "No clarification needed.";
}

export function buildSemanticPolicyCopy({
  semanticPolicy = null,
  semanticFrame = null,
} = {}) {
  if (!semanticPolicy && !semanticFrame) {
    return {
      visible: false,
      actionLabel: "",
      clarificationLabel: "",
      summary: "",
    };
  }
  const actionLabel = describeSemanticActionCopy({ semanticPolicy, semanticFrame });
  const clarificationLabel = describeSemanticClarificationCopy({ semanticPolicy, semanticFrame });
  const reason = String(semanticPolicy?.reason || "").trim();
  return {
    visible: true,
    actionLabel,
    clarificationLabel,
    summary: reason || `${actionLabel}. ${clarificationLabel}`,
  };
}

export function buildInspectBuckets({
  protocolItems = [],
  usedItems = [],
  recentItems = [],
  draftItems = [],
} = {}) {
  const protocols = dedupeInspectItems([
    ...normalizeInspectItems(protocolItems),
    ...normalizeInspectItems(usedItems).filter(isProtocolItem),
  ]);
  const used = dedupeInspectItems(
    normalizeInspectItems(usedItems).filter((item) => !isProtocolItem(item)),
  );
  const recent = dedupeInspectItems(normalizeInspectItems(recentItems));
  const draft = dedupeInspectItems(normalizeInspectItems(draftItems));
  return [
    {
      key: "protocol",
      label: "Protocol",
      count: protocols.length,
      items: protocols,
      summary: protocols.length
        ? `${protocols.length} reusable ${pluralize("protocol", protocols.length)} guided this turn.`
        : "No protocol guidance was applied.",
      emptyMessage: "Protocols will appear here when reusable task guidance is applied.",
    },
    {
      key: "used",
      label: "Used",
      count: used.length,
      items: used,
      summary: used.length
        ? `${used.length} pulled-in ${pluralize("item", used.length)} supported the answer.`
        : "No pulled-in items were used.",
      emptyMessage: "Used items from Recall will appear here.",
    },
    {
      key: "recent",
      label: "Recent",
      count: recent.length,
      items: recent,
      summary: recent.length
        ? `${recent.length} recent ${pluralize("item", recent.length)} stayed inspectable.`
        : "No recent continuity item surfaced.",
      emptyMessage: "Recent Memory Trace context will appear here.",
    },
    {
      key: "draft",
      label: "Draft",
      count: draft.length,
      items: draft,
      summary: draft.length
        ? `${draft.length} draft ${pluralize("signal", draft.length)} shaped the turn.`
        : "No draft context was in scope.",
      emptyMessage: "Draft scope and draft actions will appear here.",
    },
  ];
}

export function buildQuietActivityCopy({
  activity = [],
  semanticPolicy = null,
  semanticFrame = null,
  scenarioLab = null,
  workspaceUpdate = null,
  grounding = null,
  busy = false,
} = {}) {
  const explicit = Array.isArray(activity)
    ? activity.map((item) => String(item?.message || item?.label || "").trim()).filter(Boolean)
    : [];
  if (explicit.length) {
    return explicit.slice(0, 2).join(" · ");
  }
  if (busy) {
    return "Vantage is interpreting the request and preparing context.";
  }
  const parts = [];
  const semanticCopy = buildSemanticPolicyCopy({ semanticPolicy, semanticFrame });
  if (semanticCopy.visible && semanticCopy.actionLabel) {
    parts.push(semanticCopy.actionLabel);
  }
  if (scenarioLab?.status === "failed") {
    parts.push("Scenario Lab returned to chat");
  } else if (scenarioLab) {
    const branchCount = scenarioLabBranchCount(scenarioLab);
    parts.push(branchCount ? `Scenario Lab prepared ${branchCount} ${pluralize("branch", branchCount)}` : "Scenario Lab ready");
  }
  if (workspaceUpdate?.status === "offered") {
    parts.push("Draft offered");
  } else if (workspaceUpdate?.status === "draft_ready" || workspaceUpdate?.status === "updated") {
    parts.push("Draft ready");
  }
  if (grounding?.groundingLabel && grounding.groundingLabel !== "Idle") {
    parts.push(`Context: ${grounding.groundingLabel}`);
  }
  return parts.slice(0, 3).join(" · ") || "Ready";
}

function normalizeInspectItems(items = []) {
  return (Array.isArray(items) ? items : [])
    .filter(Boolean)
    .map((item) => {
      const protocol = normalizeProtocolMetadata(item);
      return {
        ...item,
        protocol,
      };
    });
}

function dedupeInspectItems(items = []) {
  const seen = new Set();
  const deduped = [];
  for (const item of items) {
    const key = String(item?.id || item?.title || item?.label || JSON.stringify(item)).trim();
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(item);
  }
  return deduped;
}

function isProtocolItem(item = null) {
  const type = String(item?.type || item?.kind || "").trim().toLowerCase();
  const protocolKind = String(
    item?.protocol?.protocolKind
      || item?.protocol?.protocol_kind
      || item?.protocol_kind
      || item?.protocolKind
      || "",
  ).trim();
  return type === "protocol" || Boolean(protocolKind);
}

function responseModeEvidenceLabel(responseMode, payload) {
  const kind = String(responseMode?.kind || "").trim().toLowerCase();
  const groundingMode = String(responseMode?.groundingMode || responseMode?.grounding_mode || "").trim().toLowerCase();
  const count = recallCountFromPayload(payload);

  if (kind === "best_guess" || groundingMode === "ungrounded") {
    return "Intuitive Answer";
  }
  if (groundingMode === "recall" || groundingMode === "working_memory") {
    return count > 0 ? `Used ${count} recalled ${pluralize("item", count)}` : "From earlier";
  }
  if (groundingMode === "whiteboard") {
    return "Used your draft";
  }
  if (groundingMode === "recent_chat") {
    return "From recent conversation";
  }
  if (groundingMode === "pending_whiteboard") {
    return "From your earlier draft";
  }
  if (groundingMode === "mixed_context") {
    return describeMixedContextEvidenceLabel(responseModeContextSources(responseMode))
      || describeResponseModeLabel(responseMode, count);
  }
  if (kind === "grounded") {
    return count > 0 ? `Used ${count} recalled ${pluralize("item", count)}` : (String(responseMode?.label || "").trim() || "From earlier");
  }
  return null;
}

function describeSemanticFrameAction(semanticFrame = null) {
  const taskType = String(semanticFrame?.taskType || semanticFrame?.task_type || "").trim().toLowerCase();
  const targetSurface = String(semanticFrame?.targetSurface || semanticFrame?.target_surface || "").trim().toLowerCase();
  if (targetSurface === "whiteboard") {
    return taskType === "revision" ? "Revise the draft" : "Draft in whiteboard";
  }
  if (targetSurface === "scenario_lab" || taskType === "scenario_comparison") {
    return "Compare options";
  }
  if (targetSurface === "artifact" || taskType === "artifact_save" || taskType === "artifact_publish") {
    return "Save this work";
  }
  if (targetSurface === "vantage_inspect" || taskType === "context_inspection") {
    return "Show why";
  }
  return "Answer directly";
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

function normalizeAnswerBasisFromPayload(payload = null) {
  if (!payload || typeof payload !== "object") {
    return normalizeAnswerBasis(null);
  }
  const recallItems = Array.isArray(payload.recall)
    ? payload.recall
    : Array.isArray(payload.working_memory)
      ? payload.working_memory
      : [];
  return normalizeAnswerBasis(payload.answer_basis || payload.answerBasis, {
    responseMode: payload.response_mode || payload.responseMode || null,
    recallItems,
  });
}

function normalizeContextSourceName(source) {
  const normalizedSource = String(source || "").trim().toLowerCase();
  if (normalizedSource === "working_memory" || normalizedSource === "memory") {
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

function describeMixedContextEvidenceLabel(contextSources = []) {
  const labels = contextSources
    .map((source) => describeContextSourceEvidenceLabel(source))
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
      return "Memory";
    case "whiteboard":
      return "Whiteboard";
    case "recent_chat":
      return "Recent Chat";
    case "pending_whiteboard":
      return "Prior Whiteboard";
    case "protocol":
      return "Protocol";
    default:
      return "";
  }
}

function describeContextSourceEvidenceLabel(source) {
  switch (String(source || "").trim().toLowerCase()) {
    case "recall":
    case "working_memory":
      return "From earlier";
    case "whiteboard":
      return "Used your draft";
    case "recent_chat":
      return "Recent conversation";
    case "pending_whiteboard":
      return "Earlier draft";
    case "protocol":
      return "Protocol guidance";
    default:
      return "";
  }
}

function normalizePinnedContinuityFlag(interpretation) {
  if (typeof interpretation?.preservePinnedContext === "boolean") {
    return interpretation.preservePinnedContext;
  }
  if (typeof interpretation?.preserveSelectedRecord === "boolean") {
    return interpretation.preserveSelectedRecord;
  }
  return null;
}

function normalizePinnedContinuityReason(interpretation) {
  return String(
    interpretation?.pinnedContextReason
    || interpretation?.selectedRecordReason
    || "",
  ).trim() || "";
}

export function buildGuidedInspectionSummary({
  responseMode = null,
  answerBasis = null,
  scenarioLab = null,
  recallCount = 0,
  recalledCount = 0,
  learnedCount = 0,
  libraryCount = 0,
  includeLibrary = true,
  pinnedTitle = "",
} = {}) {
  const normalizedRecallCount = Number.isFinite(Number(recallCount))
    ? Number(recallCount)
    : Number.isFinite(Number(recalledCount))
      ? Number(recalledCount)
      : 0;
  const parts = [];
  if (scenarioLab) {
    const branchCount = scenarioLabBranchCount(scenarioLab);
    parts.push(
      scenarioLab.status === "failed"
        ? "Scenario Lab: fallback"
        : branchCount
          ? `Scenario Lab: ${branchCount} ${pluralize("branch", branchCount)}`
          : "Scenario Lab: ready",
    );
  }
  const answerBasisLabel = answerBasis && typeof answerBasis === "object"
    ? normalizeAnswerBasis(answerBasis, { responseMode }).label
    : "";
  const responseModeLabel = answerBasisLabel || describeResponseModeLabel(responseMode, normalizedRecallCount);
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
  parts.push(`What I learned: ${learnedCount ? `${learnedCount} item${learnedCount === 1 ? "" : "s"}` : "nothing new yet"}`);
  if (includeLibrary) {
    parts.push(`Library: ${libraryCount} item${libraryCount === 1 ? "" : "s"}`);
  }
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
      ? "used for recall"
      : "not used this turn",
  }));
}

function humanizeRouteConfidence(confidence) {
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return "";
  }
  if (numeric >= 0.9) {
    return "High";
  }
  if (numeric >= 0.75) {
    return "Steady";
  }
  if (numeric >= 0.55) {
    return "Tentative";
  }
  return "Low";
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
  const continuityLabel = normalizePinnedContinuityFlag(interpretation) === true
    ? "Preserved pinned context"
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
    return "No supporting items were surfaced before Recall was narrowed.";
  }
  const parts = [
    `${totalCount} supporting item${totalCount === 1 ? "" : "s"} ${totalCount === 1 ? "was" : "were"} considered before Recall was narrowed`,
  ];
  const detailParts = [];
  if (candidateCounts.conceptCount) {
    detailParts.push(`${candidateCounts.conceptCount} idea${candidateCounts.conceptCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.savedCount) {
    detailParts.push(`${candidateCounts.savedCount} note${candidateCounts.savedCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.traceCount) {
    detailParts.push(`${candidateCounts.traceCount} memory trace item${candidateCounts.traceCount === 1 ? "" : "s"}`);
  }
  if (candidateCounts.vaultCount) {
    detailParts.push(`${candidateCounts.vaultCount} reference${candidateCounts.vaultCount === 1 ? "" : "s"}`);
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
    return "No recalled items entered Recall.";
  }
  return `${recallCount} recalled item${recallCount === 1 ? "" : "s"} entered Recall.`;
}

function describeReasoningWorkingMemory(grounding) {
  if (grounding?.isBestGuess) {
    return "In scope for generation: current request only (Intuitive Answer).";
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
  answerBasis = null,
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
    answerBasis,
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
        ? { label: "Chose this from", value: humanizeWhiteboardModeSource(interpretation.whiteboardModeSource) }
        : null,
      normalizePinnedContinuityFlag(interpretation) === true
        ? { label: "Kept in scope", value: normalizePinnedContinuityReason(interpretation) || "Preserved" }
        : null,
      Number.isFinite(Number(interpretation?.confidence)) && Number(interpretation.confidence) > 0
        ? { label: "Route confidence", value: humanizeRouteConfidence(interpretation.confidence) }
        : null,
    ]),
    detail: {
      summary: route,
      notes: normalizeStageMeta([
        { label: "Navigator reason", value: String(interpretation?.reason || interpretation?.note || "").trim() || "No navigator reason was returned for this turn." },
        normalizePinnedContinuityFlag(interpretation) === true
          ? { label: "Why kept in scope", value: normalizePinnedContinuityReason(interpretation) || "Pinned context was preserved for continuity." }
          : null,
      ]),
    },
  };
  const candidateStage = {
    key: "candidate-context",
    label: "Considered context",
    text: candidates,
    step: "Step 3",
    meta: normalizeStageMeta([
      candidateCounts.totalCount
        ? { label: "Considered", value: `${candidateCounts.totalCount} item${candidateCounts.totalCount === 1 ? "" : "s"}` }
        : null,
    ]),
    detail: {
      summary: candidateCounts.totalCount
        ? "These were the supporting items considered before Recall was narrowed down."
        : "No supporting items were surfaced before Recall was narrowed.",
      groups: [
        {
          label: "Ideas considered",
          items: annotateCandidateItems(candidateConcepts, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No ideas were considered.",
        },
        {
          label: "Notes considered",
          items: annotateCandidateItems(candidateSavedNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No notes were considered.",
        },
        {
          label: "Memory Trace considered",
          items: annotateCandidateItems(candidateTraceNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No Memory Trace items were considered.",
        },
        {
          label: "References considered",
          items: annotateCandidateItems(candidateVaultNotes, recallIds),
          context: "reasoning-candidate",
          emptyMessage: "No references were considered.",
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
        : "No recalled items entered Recall.",
      groups: [
        {
          label: "Used for recall",
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
      { label: "What I learned", value: Array.isArray(learnedItems) && learnedItems.length ? `${learnedItems.length} item${learnedItems.length === 1 ? "" : "s"}` : "Nothing learned" },
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
          label: "Saved from this turn",
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
    summaryPieces.push(`${candidateCounts.totalCount} supporting item${candidateCounts.totalCount === 1 ? "" : "s"} ${candidateCounts.totalCount === 1 ? "was" : "were"} considered before Recall was narrowed.`);
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
      answerBasis,
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
  const contextSources = Array.isArray(grounding?.answerBasis?.contextSources) && grounding.answerBasis.contextSources.length
    ? grounding.answerBasis.contextSources.map(normalizeContextSourceName)
    : responseModeContextSources(grounding?.responseMode);
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
    parts.push("The answer was generated as an Intuitive Answer without surfaced memory.");
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
    ...(contextSources.includes("protocol")
      ? [{
          label: "Protocol",
          status: "Included",
          detail: "Reusable protocol guidance shaped the answer basis without counting as factual memory evidence.",
        }]
      : []),
    ...(hasPriorWhiteboardInScope
      ? [{
          label: "Prior whiteboard",
          status: "Included",
          detail: "The previous whiteboard state was carried into the turn.",
        }]
      : []),
    ...(typeof normalizePinnedContinuityFlag(interpretation) === "boolean"
      ? [{
          label: "Kept in scope",
          status: normalizePinnedContinuityFlag(interpretation) ? "Included" : "Excluded",
          detail: normalizePinnedContinuityFlag(interpretation)
            ? normalizePinnedContinuityReason(interpretation) || "Pinned context stayed in scope for continuity."
            : "No pinned context was preserved.",
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
    ...(contextSources.includes("protocol")
      ? [{ label: "Protocol", value: "Included" }]
      : []),
    ...(hasPriorWhiteboardInScope
      ? [{ label: "Prior whiteboard", value: "Included" }]
      : []),
    ...(typeof normalizePinnedContinuityFlag(interpretation) === "boolean"
      ? [{ label: "Kept in scope", value: normalizePinnedContinuityFlag(interpretation) ? "Included" : "Excluded" }]
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
  answerBasis = null,
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
    answerBasis,
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
          ? { label: "Chose this from", value: humanizeWhiteboardModeSource(interpretation.whiteboardModeSource) }
          : null,
      normalizePinnedContinuityFlag(interpretation) === true
        ? { label: "Kept in scope", value: normalizePinnedContinuityReason(interpretation) || "Preserved" }
        : null,
        Number.isFinite(Number(interpretation?.confidence)) && Number(interpretation.confidence) > 0
          ? { label: "Route confidence", value: humanizeRouteConfidence(interpretation.confidence) }
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
        { label: "What I learned", value: learnedCount ? `${learnedCount} item${learnedCount === 1 ? "" : "s"}` : "Nothing learned" },
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
    parts.push(`What I learned saved ${learnedCount} new item${learnedCount === 1 ? "" : "s"} after the answer.`);
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
    evidence.push({ label: "Scenario Lab", tone: "accent", emphasis: "strong" });
    if (scenarioLab?.status === "failed") {
      evidence.push({ label: "Back to chat", tone: "warm", emphasis: "strong" });
    } else {
      const branchCount = scenarioLabBranchCount(scenarioLab);
      if (branchCount > 0) {
        evidence.push({ label: `${branchCount} ${pluralize("branch", branchCount)}`, tone: "soft", emphasis: "quiet" });
      }
    }
  }

  const grounding = groundingEvidenceLabel(payload);
  if (grounding) {
    const intuitive = grounding === "Intuitive Answer";
    evidence.push({
      label: grounding,
      tone: intuitive ? "warm" : "soft",
      emphasis: intuitive ? "strong" : "quiet",
    });
  }

  const learnedItems = normalizeLearnedItems(payload);
  const learnedLabel = learnedEvidenceLabel(learnedItems);
  if (learnedLabel) {
    evidence.push({ label: learnedLabel, tone: "success", emphasis: "strong" });
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
