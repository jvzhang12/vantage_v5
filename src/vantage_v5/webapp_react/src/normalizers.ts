import type {
  ActivityPayload,
  ActivityStep,
  AnswerBasis,
  ArtifactAction,
  ContextBudget,
  ContextBudgetRow,
  JsonRecord,
  NormalizedTurn,
  RecallItem,
  ResponseMode,
  SemanticFrame,
  SemanticPolicy,
  SourceRef,
  SurfaceInvocation,
  SurfaceInvocationSurface,
  SurfacePayload,
  SurfaceKind,
  WorkspaceUpdate,
} from "./types";

export function asRecord(value: unknown): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : {};
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function text(value: unknown, fallback = ""): string {
  return String(value ?? fallback).trim();
}

function numberOrNull(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function stringList(value: unknown): string[] {
  return asArray(value).map((item) => text(item)).filter(Boolean);
}

function countMap(value: unknown): Record<string, number> {
  const source = asRecord(value);
  return Object.fromEntries(
    Object.entries(source)
      .map(([key, raw]) => [key, Number(raw)])
      .filter((entry): entry is [string, number] => Number.isFinite(entry[1])),
  );
}

export function normalizeSourceRefs(value: unknown): SourceRef[] {
  return asArray(value)
    .map((item): SourceRef | null => {
      const record = asRecord(item);
      const id = text(record.id || record.record_id || record.recordId);
      const title = text(record.title || record.label || id);
      if (!id && !title) {
        return null;
      }
      return {
        id,
        title,
        source: text(record.source),
        kind: text(record.kind || record.type),
        label: text(record.label || title),
      };
    })
    .filter((item): item is SourceRef => item !== null);
}

export function normalizeSurfacePayloads(value: unknown): SurfacePayload[] {
  return asArray(value)
    .map((item) => {
      const record = asRecord(item);
      const id = text(record.id);
      const kind = text(record.kind) as SurfaceKind;
      if (!id || !kind) {
        return null;
      }
      return {
        id,
        kind,
        title: text(record.title || kind),
        summary: text(record.summary),
        sourceRefs: normalizeSourceRefs(record.source_refs || record.sourceRefs),
        data: asRecord(record.data),
      };
    })
    .filter((item): item is SurfacePayload => Boolean(item));
}

export function normalizeArtifactActions(value: unknown): ArtifactAction[] {
  return asArray(value)
    .map((item): ArtifactAction | null => {
      const record = asRecord(item);
      const id = text(record.id);
      if (!id) {
        return null;
      }
      return {
        id,
        artifactKind: text(record.artifact_kind || record.artifactKind),
        operation: text(record.operation),
        status: text(record.status || "proposed"),
        summary: text(record.summary),
        targetRefs: normalizeSourceRefs(record.target_refs || record.targetRefs),
        payload: asRecord(record.payload),
        preview: asRecord(record.preview),
        warnings: stringList(record.warnings),
        requiresConfirmation: Boolean(record.requires_confirmation ?? record.requiresConfirmation),
        sourceRefs: normalizeSourceRefs(record.source_refs || record.sourceRefs),
      };
    })
    .filter((item): item is ArtifactAction => item !== null);
}

export function normalizeSurfaceInvocation(value: unknown): SurfaceInvocation | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    intent: text(record.intent || "general"),
    primarySurface: text(record.primary_surface || record.primarySurface || "chat"),
    supportingSurfaces: stringList(record.supporting_surfaces || record.supportingSurfaces),
    surfaces: normalizeSurfaceInvocationSurfaces(record.surfaces),
    writeBehavior: text(record.write_behavior || record.writeBehavior || "proposal_only"),
    reason: text(record.reason),
    confidence: numberOrNull(record.confidence),
    dataSources: stringList(record.data_sources || record.dataSources || record.sources),
    trigger: text(record.trigger),
    policyVersion: text(record.policy_version || record.policyVersion),
  };
}

function normalizeSurfaceInvocationSurfaces(value: unknown): SurfaceInvocationSurface[] {
  return asArray(value)
    .map((item): SurfaceInvocationSurface | null => {
      const record = asRecord(item);
      const kind = text(record.kind);
      if (!kind) {
        return null;
      }
      return {
        kind,
        role: text(record.role),
        reason: text(record.reason),
        status: text(record.status || "summoned"),
      };
    })
    .filter((item): item is SurfaceInvocationSurface => item !== null);
}

export function normalizeAnswerBasis(value: unknown, responseMode?: ResponseMode): AnswerBasis {
  const record = asRecord(value);
  const rawLabel = text(record.label || responseMode?.label || "Intuitive Answer");
  const label = rawLabel === "Best Guess" ? "Intuitive Answer" : rawLabel;
  return {
    kind: text(record.kind || responseMode?.kind || "intuitive"),
    label,
    summary: text(record.summary || record.note || responseMode?.note),
    hasFactualGrounding: Boolean(record.has_factual_grounding ?? record.hasFactualGrounding ?? responseMode?.kind === "grounded"),
    sources: stringList(record.sources || record.context_sources || record.contextSources || responseMode?.contextSources),
    counts: countMap(record.counts),
  };
}

export function normalizeResponseMode(value: unknown): ResponseMode {
  const record = asRecord(value);
  const rawLabel = text(record.label || (record.kind === "best_guess" ? "Best Guess" : "Grounded"));
  return {
    kind: text(record.kind || "best_guess"),
    label: rawLabel === "Best Guess" ? "Intuitive Answer" : rawLabel,
    groundingMode: text(record.grounding_mode || record.groundingMode || "ungrounded"),
    contextSources: stringList(record.context_sources || record.contextSources || record.grounding_sources || record.groundingSources),
    recallCount: Number(record.recall_count || record.recallCount || record.working_memory_count || 0) || 0,
    note: text(record.note),
  };
}

export function normalizeRecallItems(value: unknown): RecallItem[] {
  return asArray(value)
    .map((item) => {
      const record = asRecord(item);
      const id = text(record.id || record.record_id || record.recordId);
      const title = text(record.title || id);
      if (!id && !title) {
        return null;
      }
      return {
        id,
        title,
        source: text(record.source || "memory"),
        type: text(record.type || record.kind || record.source || "memory"),
        card: text(record.card || record.summary || record.body || record.content),
        reason: text(record.why_recalled || record.whyRecalled || record.reason || record.rationale),
      };
    })
    .filter((item): item is RecallItem => Boolean(item));
}

export function normalizeWorkspaceUpdate(value: unknown): WorkspaceUpdate | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    type: text(record.type),
    status: text(record.status),
    proposalKind: text(record.proposal_kind || record.proposalKind),
    summary: text(record.summary),
    title: text(record.title),
    content: typeof record.content === "string" ? record.content : "",
    decision: text(record.decision),
    persisted: Boolean(record.persisted),
  };
}

function normalizeContextBudgetRow(value: unknown): ContextBudgetRow | null {
  const record = asRecord(value);
  const key = text(record.key || record.id || record.name);
  const label = text(record.label || key);
  if (!key && !label) {
    return null;
  }
  const status = text(record.status || record.state || record.display_status || record.displayStatus).toLowerCase() || "excluded";
  return {
    key,
    label,
    status: ["included", "include", "used", "active", "preserved", "true"].includes(status) ? "included" : "excluded",
    displayStatus: text(record.display_status || record.displayStatus || (status === "included" ? "Included" : "Excluded")),
    detail: text(record.detail || record.summary || record.note),
    count: numberOrNull(record.count),
    scope: text(record.scope || record.scope_label || record.scopeLabel),
  };
}

export function normalizeContextBudget(value: unknown): ContextBudget | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  const rows = asArray(record.rows || record.items)
    .map(normalizeContextBudgetRow)
    .filter((item): item is ContextBudgetRow => item !== null);
  return {
    label: text(record.label || "Context Budget"),
    summary: text(record.summary),
    rows,
    counts: countMap(record.counts),
    contextSources: stringList(record.context_sources || record.contextSources),
  };
}

function normalizeActivityStep(value: unknown): ActivityStep | null {
  const record = asRecord(value);
  const label = text(record.label || record.title || record.type || record.kind || "Activity");
  const summary = text(record.summary || record.message || record.detail || record.reason);
  if (!label && !summary) {
    return null;
  }
  return {
    id: text(record.id || record.key || label),
    type: text(record.type || record.kind || record.event || "activity"),
    label,
    status: text(record.status || record.state || record.tone || "completed"),
    summary,
    createdAt: text(record.created_at || record.createdAt || record.timestamp),
  };
}

export function normalizeActivity(value: unknown): ActivityPayload | null {
  const record = asRecord(value);
  const source = Object.keys(record).length ? record : {};
  const stepsSource = asArray(record.steps || record.items || record.events || (Array.isArray(value) ? value : []));
  const steps = stepsSource
    .map(normalizeActivityStep)
    .filter((item): item is ActivityStep => item !== null);
  if (!Object.keys(source).length && !steps.length) {
    return null;
  }
  return {
    mode: text(record.mode || record.kind),
    kind: text(record.kind || record.mode),
    status: text(record.status),
    summary: text(record.summary),
    steps,
    recallCount: Number(record.recall_count || record.recallCount || 0) || 0,
    learnedCount: Number(record.learned_count || record.learnedCount || 0) || 0,
    createdRecordId: text(record.created_record_id || record.createdRecordId),
    graphActionType: text(record.graph_action_type || record.graphActionType),
    workspaceUpdateStatus: text(record.workspace_update_status || record.workspaceUpdateStatus),
  };
}

function normalizeSemanticFrame(value: unknown): SemanticFrame | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    userGoal: text(record.user_goal || record.userGoal),
    taskType: text(record.task_type || record.taskType || "question_answering"),
    followUpType: text(record.follow_up_type || record.followUpType || "new_request"),
    targetSurface: text(record.target_surface || record.targetSurface || "chat"),
    confidence: numberOrNull(record.confidence) ?? 0,
    needsClarification: Boolean(record.needs_clarification ?? record.needsClarification),
    clarificationPrompt: text(record.clarification_prompt || record.clarificationPrompt) || null,
    commitments: stringList(record.commitments),
    signals: asRecord(record.signals),
  };
}

function normalizeSemanticPolicy(value: unknown): SemanticPolicy | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    semanticAction: text(record.semantic_action || record.semanticAction || record.action || "respond"),
    actionLabel: text(record.action_label || record.actionLabel),
    needsClarification: Boolean(record.needs_clarification ?? record.needsClarification),
    clarificationPrompt: text(record.clarification_prompt || record.clarificationPrompt || record.prompt) || null,
    status: text(record.status || record.state),
    reason: text(record.reason || record.rationale || record.summary),
    confidence: numberOrNull(record.confidence) ?? 0,
    blocking: Boolean(record.blocking ?? record.is_blocking ?? record.isBlocking),
    signals: asRecord(record.signals),
  };
}

function normalizeRecordOrNull(value: unknown): JsonRecord | null {
  const record = asRecord(value);
  return Object.keys(record).length ? record : null;
}

function normalizeRecordArray(value: unknown): JsonRecord[] {
  return asArray(value)
    .map(asRecord)
    .filter((record) => Object.keys(record).length);
}

function firstTimestamp(record: JsonRecord): string {
  const direct = text(
    record.created_at
      || record.createdAt
      || record.timestamp
      || record.updated_at
      || record.updatedAt
      || record.date,
  );
  if (direct) {
    return direct;
  }
  const memoryTrace = asRecord(record.memory_trace_record || record.memoryTraceRecord);
  return text(
    memoryTrace.created_at
      || memoryTrace.createdAt
      || memoryTrace.timestamp
      || memoryTrace.updated_at
      || memoryTrace.updatedAt
      || memoryTrace.date,
  );
}

export function normalizeTurnPayload(payload: unknown): NormalizedTurn {
  const record = asRecord(payload);
  const responseMode = normalizeResponseMode(record.response_mode || record.responseMode);
  const recallItems = normalizeRecallItems(record.recall || record.working_memory || record.memory);
  return {
    userMessage: text(record.user_message || record.userMessage),
    assistantMessage: text(record.assistant_message || record.assistantMessage || "(No assistant response.)"),
    mode: text(record.mode || "chat"),
    timestamp: firstTimestamp(record),
    responseMode,
    answerBasis: normalizeAnswerBasis(record.answer_basis || record.answerBasis, responseMode),
    recallItems,
    learnedItems: normalizeRecallItems(record.learned || (record.created_record ? [record.created_record] : [])),
    memoryTraceRecord: normalizeRecallItems(record.memory_trace_record ? [record.memory_trace_record] : [])[0] || null,
    surfaceInvocation: normalizeSurfaceInvocation(record.surface_invocation || record.surfaceInvocation),
    surfacePayloads: normalizeSurfacePayloads(record.surface_payloads || record.surfacePayloads),
    activeSurfaceId: text(record.active_surface_id || record.activeSurfaceId) || null,
    artifactActions: normalizeArtifactActions(record.artifact_actions || record.artifactActions),
    workspaceUpdate: normalizeWorkspaceUpdate(record.workspace_update || record.workspaceUpdate),
    contextBudget: normalizeContextBudget(record.context_budget || record.contextBudget),
    activity: normalizeActivity(record.activity || record.activities || record.events),
    turnInterpretation: normalizeRecordOrNull(record.turn_interpretation || record.turnInterpretation),
    semanticFrame: normalizeSemanticFrame(record.semantic_frame || record.semanticFrame),
    semanticPolicy: normalizeSemanticPolicy(record.semantic_policy || record.semanticPolicy),
    visibleArtifacts: normalizeRecordArray(record.visible_artifacts || record.visibleArtifacts),
    metaAction: normalizeRecordOrNull(record.meta_action || record.metaAction),
    graphAction: normalizeRecordOrNull(record.graph_action || record.graphAction),
    createdRecord: normalizeRecordOrNull(record.created_record || record.createdRecord),
    stageProgress: asArray(record.stage_progress || record.stageProgress)
      .map(normalizeActivityStep)
      .filter((item): item is ActivityStep => item !== null),
    raw: record,
  };
}
