import type {
  ActivityPayload,
  ActivityStep,
  AnswerBasis,
  AttentionCandidate,
  AppCapability,
  AppCapabilityManifest,
  AppCapabilityResource,
  AppCapabilitySource,
  AppCapabilitySurface,
  AppCapabilityTool,
  ArtifactAction,
  ContextBudget,
  ContextBudgetRow,
  JsonRecord,
  NavigatorSelection,
  NormalizedTurn,
  QueryFrame,
  RecallItem,
  ResponseMode,
  SemanticFrame,
  SemanticPolicy,
  SourceRef,
  SelectedAttentionResource,
  SurfaceAction,
  SurfaceInvocation,
  SurfaceInvocationSurface,
  SurfacePayload,
  SurfaceKind,
  WorkingMemoryExecutionSummary,
  WorkingMemoryResource,
  WorkingMemoryRoleName,
  WorkingMemoryRoleReference,
  WorkingMemoryView,
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

function booleanOrNull(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
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
        resourceId: text(record.resource_id || record.resourceId),
        capabilityRef: text(record.capability_ref || record.capabilityRef),
        writable: Boolean(record.writable),
        readOnly: Boolean(record.read_only ?? record.readOnly),
      };
    })
    .filter((item): item is SourceRef => item !== null);
}

export function normalizeAppCapabilityManifest(value: unknown): AppCapabilityManifest | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    policyVersion: text(record.policy_version || record.policyVersion),
    apps: asArray(record.apps).map(normalizeAppCapability).filter((item): item is AppCapability => item !== null),
    resources: asArray(record.resources).map(normalizeAppCapabilityResource).filter((item): item is AppCapabilityResource => item !== null),
    tools: asArray(record.tools).map(normalizeAppCapabilityTool).filter((item): item is AppCapabilityTool => item !== null),
    surfaces: asArray(record.surfaces).map(normalizeAppCapabilitySurface).filter((item): item is AppCapabilitySurface => item !== null),
    receiptEvents: asArray(record.receipt_events || record.receiptEvents).map(asRecord).filter((item) => Object.keys(item).length),
  };
}

function normalizeAppCapability(value: unknown): AppCapability | null {
  const record = asRecord(value);
  const id = text(record.id);
  if (!id) {
    return null;
  }
  return {
    id,
    label: text(record.label || id),
    summary: text(record.summary),
    invocationPolicy: asRecord(record.invocation_policy || record.invocationPolicy),
    writeBehavior: asRecord(record.write_behavior || record.writeBehavior),
    jsonInterface: asRecord(record.json_interface || record.jsonInterface),
  };
}

function normalizeAppCapabilityResource(value: unknown): AppCapabilityResource | null {
  const record = asRecord(value);
  const id = text(record.id);
  if (!id) {
    return null;
  }
  const source = normalizeAppCapabilitySource(record.source);
  return {
    id,
    appId: text(record.app_id || record.appId),
    kind: text(record.kind),
    label: text(record.label || id),
    description: text(record.description),
    uri: text(record.uri),
    readable: Boolean(record.readable ?? true),
    writable: Boolean(record.writable),
    readOnly: Boolean(record.read_only ?? record.readOnly),
    visibleContext: text(record.visible_context || record.visibleContext || "markdown"),
    source,
  };
}

function normalizeAppCapabilitySource(value: unknown): AppCapabilitySource {
  const record = asRecord(value);
  const counts = countMap({
    event_count: record.event_count,
    task_count: record.task_count,
  });
  return {
    kind: text(record.kind),
    label: text(record.label),
    configured: Boolean(record.configured),
    readOnly: Boolean(record.read_only ?? record.readOnly),
    writable: Boolean(record.writable),
    counts,
    meta: record,
  };
}

function normalizeAppCapabilityTool(value: unknown): AppCapabilityTool | null {
  const record = asRecord(value);
  const name = text(record.name);
  if (!name) {
    return null;
  }
  return {
    name,
    appId: text(record.app_id || record.appId),
    operation: text(record.operation),
    label: text(record.label || name),
    description: text(record.description),
    resourceIds: stringList(record.resource_ids || record.resourceIds),
    write: Boolean(record.write),
    requiresConfirmation: Boolean(record.requires_confirmation ?? record.requiresConfirmation),
    destructive: Boolean(record.destructive),
    status: text(record.status || "available"),
  };
}

function normalizeAppCapabilitySurface(value: unknown): AppCapabilitySurface | null {
  const record = asRecord(value);
  const kind = text(record.kind);
  if (!kind) {
    return null;
  }
  return {
    kind,
    appId: text(record.app_id || record.appId),
    label: text(record.label || kind),
    description: text(record.description),
    renderer: text(record.renderer),
    resourceIds: stringList(record.resource_ids || record.resourceIds),
    visibleContext: text(record.visible_context || record.visibleContext || "markdown"),
  };
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
      const payload = asRecord(record.payload);
      const capture = asRecord(record.capture || payload.capture);
      return {
        id,
        artifactKind: text(record.artifact_kind || record.artifactKind),
        operation: text(record.operation),
        status: text(record.status || "proposed"),
        summary: text(record.summary),
        targetRefs: normalizeSourceRefs(record.target_refs || record.targetRefs),
        payload,
        preview: asRecord(record.preview),
        warnings: stringList(record.warnings),
        requiresConfirmation: Boolean(record.requires_confirmation ?? record.requiresConfirmation),
        sourceRefs: normalizeSourceRefs(record.source_refs || record.sourceRefs),
        capture: Object.keys(capture).length ? capture : null,
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
    capabilityRefs: stringList(record.capability_refs || record.capabilityRefs),
    trigger: text(record.trigger),
    policyVersion: text(record.policy_version || record.policyVersion),
  };
}

export function normalizeSurfaceAction(value: unknown): SurfaceAction | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    type: text(record.type),
    status: text(record.status),
    target: text(record.target),
    targetId: text(record.target_id || record.targetId),
    targetKind: text(record.target_kind || record.targetKind),
    title: text(record.title),
    reason: text(record.reason),
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

function normalizeTemporalReferences(value: unknown) {
  return asArray(value)
    .map((item) => {
      const record = asRecord(item);
      const rawText = text(record.raw_text || record.rawText);
      if (!rawText) {
        return null;
      }
      return {
        rawText,
        relation: text(record.relation),
        start: text(record.start),
        end: text(record.end),
        grain: text(record.grain),
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);
}

function normalizeQueryFrame(value: unknown): QueryFrame | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    rawText: text(record.raw_text || record.rawText),
    normalizedText: text(record.normalized_text || record.normalizedText),
    tokens: stringList(record.tokens),
    domains: stringList(record.domains),
    operations: stringList(record.operations),
    entities: stringList(record.entities),
    artifactKinds: stringList(record.artifact_kinds || record.artifactKinds),
    temporalReferences: normalizeTemporalReferences(record.temporal_references || record.temporalReferences),
  };
}

function normalizeAttentionCandidates(value: unknown): AttentionCandidate[] {
  return asArray(value)
    .map((item): AttentionCandidate | null => {
      const record = asRecord(item);
      const resourceId = text(record.resource_id || record.resourceId || record.id);
      if (!resourceId) {
        return null;
      }
      return {
        id: text(record.id || `candidate-${resourceId}`),
        resourceId,
        kind: text(record.kind),
        app: text(record.app),
        title: text(record.title || resourceId),
        summary: text(record.summary),
        source: text(record.source),
        score: numberOrNull(record.score) ?? 0,
        matchedKeys: stringList(record.matched_keys || record.matchedKeys),
        temporalMatches: stringList(record.temporal_matches || record.temporalMatches),
        suggestedSurface: text(record.suggested_surface || record.suggestedSurface),
        whyCandidate: text(record.why_candidate || record.whyCandidate),
        retrievalScores: normalizeNumericRecord(record.retrieval_scores || record.retrievalScores),
      };
    })
    .filter((item): item is AttentionCandidate => item !== null);
}

function normalizeNumericRecord(value: unknown): Record<string, number> {
  const record = asRecord(value);
  return Object.fromEntries(
    Object.entries(record)
      .map(([key, item]) => [key, numberOrNull(item)] as const)
      .filter((entry): entry is readonly [string, number] => entry[1] !== null),
  );
}

function normalizeNavigatorSelection(value: unknown): NavigatorSelection | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  return {
    selectedIds: stringList(record.selected_ids || record.selectedIds),
    primaryResourceId: text(record.primary_resource_id || record.primaryResourceId),
    supportingResourceIds: stringList(record.supporting_resource_ids || record.supportingResourceIds),
    rejectedCandidateIds: stringList(record.rejected_candidate_ids || record.rejectedCandidateIds),
    surfaceToOpen: text(record.surface_to_open || record.surfaceToOpen),
    reason: text(record.reason),
    confidence: numberOrNull(record.confidence) ?? 0,
    fallback: Boolean(record.fallback),
  };
}

function normalizeSelectedAttentionResources(value: unknown): SelectedAttentionResource[] {
  return asArray(value)
    .map((item): SelectedAttentionResource | null => {
      const record = asRecord(item);
      const resourceId = text(record.resource_id || record.resourceId || record.id);
      if (!resourceId) {
        return null;
      }
      return {
        id: text(record.id || `selected-${resourceId}`),
        resourceId,
        kind: text(record.kind),
        app: text(record.app),
        title: text(record.title || resourceId),
        summary: text(record.summary),
        source: text(record.source),
        content: text(record.content),
        data: asRecord(record.data),
        timestamps: asRecord(record.timestamps),
        suggestedSurface: text(record.suggested_surface || record.suggestedSurface),
        whySelected: text(record.why_selected || record.whySelected),
      };
    })
    .filter((item): item is SelectedAttentionResource => item !== null);
}

const WORKING_MEMORY_ROLES: WorkingMemoryRoleName[] = [
  "answer_context",
  "recall_context",
  "protocol_guidance",
  "surface_to_open",
  "pinned_or_continuity_context",
];

function normalizeWorkingMemoryRoleReference(value: unknown): WorkingMemoryRoleReference | null {
  const record = asRecord(value);
  const resourceId = text(record.resource_id || record.resourceId);
  if (!resourceId) {
    return null;
  }
  return {
    resourceId,
    kind: text(record.kind),
    title: text(record.title || resourceId),
    origins: stringList(record.origins),
    sentToResponseLlm: booleanOrNull(record.sent_to_response_llm ?? record.sentToResponseLlm),
  };
}

function normalizeWorkingMemoryRoles(value: unknown): Record<WorkingMemoryRoleName, WorkingMemoryRoleReference[]> {
  const record = asRecord(value);
  return Object.fromEntries(
    WORKING_MEMORY_ROLES.map((role) => [
      role,
      asArray(record[role]).map(normalizeWorkingMemoryRoleReference).filter((item): item is WorkingMemoryRoleReference => item !== null),
    ]),
  ) as Record<WorkingMemoryRoleName, WorkingMemoryRoleReference[]>;
}

function normalizeWorkingMemoryResource(value: unknown): WorkingMemoryResource | null {
  const record = asRecord(value);
  const resourceId = text(record.resource_id || record.resourceId || record.id);
  if (!resourceId) {
    return null;
  }
  const flags = asRecord(record.flags);
  const provenance = asRecord(record.provenance);
  const sourceStatus = asRecord(provenance.source_status || provenance.sourceStatus);
  const influence = asRecord(record.influence);
  return {
    id: text(record.id || resourceId),
    resourceId,
    kind: text(record.kind),
    type: text(record.type),
    title: text(record.title || record.label || resourceId),
    label: text(record.label),
    roles: stringList(record.roles),
    origins: stringList(record.origins),
    flags: {
      selected: Boolean(flags.selected),
      visible: Boolean(flags.visible),
      pinned: Boolean(flags.pinned),
    },
    summary: text(record.summary),
    excerpt: text(record.excerpt),
    sentToResponseLlm: booleanOrNull(record.sent_to_response_llm ?? record.sentToResponseLlm),
    provenance: {
      source: text(provenance.source),
      sourceLabel: text(provenance.source_label || provenance.sourceLabel),
      scope: text(provenance.scope),
      durability: text(provenance.durability),
      isCanonical: booleanOrNull(provenance.is_canonical ?? provenance.isCanonical),
      sourceStatus,
    },
    influence: {
      answerGeneration: Boolean(influence.answer_generation ?? influence.answerGeneration),
      uiSurfaceAction: Boolean(influence.ui_surface_action ?? influence.uiSurfaceAction),
      writeOrProposalDecision: booleanOrNull(influence.write_or_proposal_decision ?? influence.writeOrProposalDecision),
    },
  };
}

function normalizeWorkingMemoryExecutionSummary(value: unknown): WorkingMemoryExecutionSummary {
  const record = asRecord(value);
  const surface = asRecord(record.surface);
  const writes = asRecord(record.writes);
  return {
    surface: {
      mode: text(surface.mode),
      surface: text(surface.surface),
      targetResourceId: text(surface.target_resource_id || surface.targetResourceId),
      targetResourceKind: text(surface.target_resource_kind || surface.targetResourceKind),
      authority: text(surface.authority),
      activeSurfaceId: text(surface.active_surface_id || surface.activeSurfaceId),
      surfacePayloadCount: Number(surface.surface_payload_count || surface.surfacePayloadCount || 0) || 0,
    },
    writes: {
      categories: stringList(writes.categories),
      intendedWriteKind: text(writes.intended_write_kind || writes.intendedWriteKind),
      effectAgreement: text(writes.effect_agreement || writes.effectAgreement),
      workspaceUpdateType: text(writes.workspace_update_type || writes.workspaceUpdateType),
      graphActionType: text(writes.graph_action_type || writes.graphActionType),
      createdRecord: Object.keys(asRecord(writes.created_record || writes.createdRecord)).length
        ? asRecord(writes.created_record || writes.createdRecord)
        : null,
      artifactActionCount: Number(writes.artifact_action_count || writes.artifactActionCount || 0) || 0,
      proposalCount: Number(writes.proposal_count || writes.proposalCount || 0) || 0,
    },
  };
}

export function normalizeWorkingMemoryView(value: unknown): WorkingMemoryView | null {
  const record = asRecord(value);
  if (!Object.keys(record).length) {
    return null;
  }
  const turn = asRecord(record.turn);
  const source = asRecord(record.source);
  return {
    schema: text(record.schema),
    turn: {
      turnId: text(turn.turn_id || turn.turnId),
      traceId: text(turn.trace_id || turn.traceId),
      responseMode: text(turn.response_mode || turn.responseMode),
      mode: text(turn.mode),
    },
    roles: normalizeWorkingMemoryRoles(record.roles),
    resources: asArray(record.resources)
      .map(normalizeWorkingMemoryResource)
      .filter((item): item is WorkingMemoryResource => item !== null),
    comparison: Object.fromEntries(
      Object.entries(asRecord(record.comparison)).map(([key, item]) => [key, stringList(item)]),
    ),
    executionSummary: normalizeWorkingMemoryExecutionSummary(record.execution_summary || record.executionSummary),
    source: {
      attentionRecallRoleProjectionSchema: text(
        source.attention_recall_role_projection_schema || source.attentionRecallRoleProjectionSchema,
      ),
      turnPlanVersion: text(source.turn_plan_version || source.turnPlanVersion),
    },
    notes: stringList(record.notes),
  };
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
    surfaceAction: normalizeSurfaceAction(record.surface_action || record.surfaceAction),
    surfacePayloads: normalizeSurfacePayloads(record.surface_payloads || record.surfacePayloads),
    activeSurfaceId: text(record.active_surface_id || record.activeSurfaceId) || null,
    artifactActions: normalizeArtifactActions(record.artifact_actions || record.artifactActions),
    appCapabilities: normalizeAppCapabilityManifest(record.app_capabilities || record.appCapabilities),
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
    queryFrame: normalizeQueryFrame(record.query_frame || record.queryFrame),
    attentionCandidates: normalizeAttentionCandidates(record.attention_candidates || record.attentionCandidates),
    navigatorSelection: normalizeNavigatorSelection(record.navigator_selection || record.navigatorSelection),
    selectedAttentionResources: normalizeSelectedAttentionResources(record.selected_attention_resources || record.selectedAttentionResources),
    workingMemoryView: normalizeWorkingMemoryView(record.working_memory_view || record.workingMemoryView),
    raw: record,
  };
}
