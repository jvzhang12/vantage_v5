import { asArray, asRecord, text } from "./normalizers";
import { surfaceLabel } from "./capabilities";
import type { ContextBudgetRow, NormalizedTurn, SurfacePayload } from "./types";

export interface SummaryColumnModel {
  key: string;
  label: string;
  value: string;
  detail?: string;
}

export interface ContextUsedItemModel {
  id: string;
  type: string;
  title: string;
  description: string;
  why: string;
  status?: string;
}

export interface SurfaceDecisionModel {
  id: string;
  name: string;
  opened: boolean;
  mode: string;
  reason: string;
  detail?: string;
}

export interface DecisionPathStepModel {
  id: string;
  label: string;
  value: string;
  detail?: string;
}

export interface MemoryActionsWritesModel {
  savedMemory: string[];
  proposedMemory: string[];
  updatedTasks: string[];
  editedCalendar: string[];
  createdArtifacts: string[];
  draftWrites: string[];
  mode: string;
  assumptions: string[];
  summary: string;
}

export interface InspectionReceipt {
  request: string;
  intent: string;
  grounding: string[];
  mode: string;
  summary: string;
  timestamp: string;
  summaryColumns: SummaryColumnModel[];
  contextItems: ContextUsedItemModel[];
  surfaceDecisions: SurfaceDecisionModel[];
  decisionPath: DecisionPathStepModel[];
  writes: MemoryActionsWritesModel;
}

const CONTEXT_LABELS: Record<string, { type: string; title: string; why: string }> = {
  recall: { type: "Memory", title: "Recall", why: "The context budget marked recalled records as included." },
  protocol: { type: "Protocol", title: "Protocols", why: "Protocol guidance was selected for this turn." },
  whiteboard: { type: "Whiteboard", title: "Whiteboard", why: "The visible whiteboard was part of the model context." },
  recent_chat: { type: "Conversation", title: "Recent chat", why: "Conversation continuity was included by the backend." },
  pending_whiteboard: { type: "Draft", title: "Prior draft", why: "A pending draft was still relevant to the request." },
  pinned_context: { type: "Pinned context", title: "Pinned context", why: "Pinned context was preserved for this turn." },
  memory_trace: { type: "Memory", title: "Memory Trace", why: "Recent turn continuity entered Recall." },
};

export function buildInspectionReceipt(
  turn: NormalizedTurn | null,
  activeSurface: SurfacePayload | null = null,
): InspectionReceipt | null {
  if (!turn) {
    return null;
  }

  const surfaces = uniqueSurfaces([activeSurface, ...turn.surfacePayloads]);
  const writes = buildWrites(turn, surfaces);
  const request = "Turn input received";
  const requestDetail = requestMetadata(turn);
  const intent = humanize(
    turn.surfaceInvocation?.intent
      || turn.semanticFrame?.taskType
      || turn.activity?.mode
      || turn.mode
      || "general_chat",
  );
  const grounding = groundingTypes(turn, surfaces);
  const mode = readableMode(turn.surfaceInvocation?.writeBehavior || writes.mode);
  const summary = generationSummary({ turn, surfaces, grounding, intent, writes });

  return {
    request,
    intent,
    grounding,
    mode,
    summary,
    timestamp: turn.timestamp,
    summaryColumns: [
      { key: "request", label: "Input", value: request, detail: requestDetail },
      { key: "intent", label: "Intent", value: intent, detail: confidenceLabel(turn.surfaceInvocation?.confidence ?? turn.semanticFrame?.confidence) },
      { key: "grounding", label: "Grounding", value: grounding.join(" · ") || turn.answerBasis.label || "Current request" },
      { key: "mode", label: "Mode", value: mode },
      { key: "summary", label: "Summary", value: summary },
    ],
    contextItems: contextItems(turn, surfaces),
    surfaceDecisions: surfaceDecisions(turn, surfaces),
    decisionPath: decisionPath(turn, surfaces, writes, { request, requestDetail, intent, summary }),
    writes,
  };
}

function uniqueSurfaces(surfaces: Array<SurfacePayload | null>): SurfacePayload[] {
  const byId = new Map<string, SurfacePayload>();
  for (const surface of surfaces) {
    if (surface?.id && !byId.has(surface.id)) {
      byId.set(surface.id, surface);
    }
  }
  return [...byId.values()];
}

function contextItems(turn: NormalizedTurn, surfaces: SurfacePayload[]): ContextUsedItemModel[] {
  const items: ContextUsedItemModel[] = [];
  const seen = new Set<string>();
  const add = (item: ContextUsedItemModel) => {
    const key = item.id || `${item.type}:${item.title}`;
    if (!seen.has(key)) {
      seen.add(key);
      items.push(item);
    }
  };

  for (const row of turn.contextBudget?.rows || []) {
    if (row.status !== "included" || row.key === "user_request") {
      continue;
    }
    const copy = contextCopyForRow(row);
    add({
      id: `budget-${row.key}`,
      type: copy.type,
      title: copy.title,
      description: row.detail || "Included in the model context.",
      why: copy.why,
      status: row.displayStatus || "Included",
    });
  }

  for (const item of turn.recallItems) {
    add({
      id: `recall-${item.source}-${item.id}`,
      type: contextTypeFromRecord(item.type || item.source),
      title: item.title || item.id || "Recalled item",
      description: item.card || item.source || "Recalled context.",
      why: item.reason || "The recall layer selected this item for the latest answer.",
      status: "Included",
    });
  }

  for (const item of turn.selectedAttentionResources) {
    add({
      id: `attention-${item.resourceId}`,
      type: contextTypeFromRecord(item.kind || item.source || item.app),
      title: item.title || item.resourceId,
      description: firstNonEmpty(item.summary, firstSentence(item.content), "Navigator-selected context."),
      why: item.whySelected || turn.navigatorSelection?.reason || "Navigator selected this item from the deterministic attention shortlist.",
      status: "Selected",
    });
  }

  for (const artifact of turn.visibleArtifacts) {
    const title = text(artifact.title || artifact.label || artifact.id || "Visible artifact");
    add({
      id: `visible-${title}`,
      type: "Visible artifact",
      title,
      description: text(artifact.summary || artifact.kind || artifact.type || "Visible artifact content was sent with the turn."),
      why: "It was present in the user's view when the message was sent.",
      status: "Included",
    });
  }

  for (const surface of surfaces) {
    addSurfaceContext(surface, add);
  }

  for (const action of turn.artifactActions) {
    const capture = action.capture || asRecord(action.payload.capture);
    if (!Object.keys(capture).length) {
      continue;
    }
    add({
      id: `capture-${action.id}`,
      type: action.artifactKind === "task" ? "Tasks" : action.artifactKind === "calendar" ? "Calendar" : "Artifact action",
      title: action.summary || humanize(action.operation),
      description: text(asRecord(capture.parsed_fields).title || action.operation || "Captured operational item."),
      why: text(capture.reason || "The capture layer identified a durable operational item in the latest message."),
      status: humanize(action.status),
    });
  }

  if (!items.length) {
    add({
      id: "current-request",
      type: "Current request",
      title: "User request",
      description: "The latest message was the only context required.",
      why: "The context budget did not mark any additional artifacts, memories, protocols, or surfaces as used.",
      status: "Included",
    });
  }

  return items;
}

function contextCopyForRow(row: ContextBudgetRow): { type: string; title: string; why: string } {
  return CONTEXT_LABELS[row.key] || {
    type: humanize(row.key),
    title: row.label || humanize(row.key),
    why: "The backend context budget marked this item as included.",
  };
}

function addSurfaceContext(surface: SurfacePayload, add: (item: ContextUsedItemModel) => void) {
  const data = surface.data;
  const date = text(data.date || asRecord(data.calendar).date || asRecord(data.calendar_week).start_date);
  if (["today_briefing", "calendar_day", "calendar_week"].includes(surface.kind)) {
    add({
      id: `surface-calendar-${surface.id}`,
      type: "Calendar",
      title: surface.kind === "calendar_week" ? "Calendar week" : "Calendar day",
      description: surface.summary || "Calendar events and open time were used.",
      why: `The opened ${surfaceLabel(surface.kind)} surface needed schedule data.`,
      status: "Included",
    });
  }
  if (["today_briefing", "task_focus"].includes(surface.kind)) {
    const taskSummary = taskSummaryFromSurface(surface);
    add({
      id: `surface-tasks-${surface.id}`,
      type: "Tasks",
      title: "Task focus",
      description: taskSummary || "Task groups were used.",
      why: `The opened ${surfaceLabel(surface.kind)} surface needed task priority data.`,
      status: "Included",
    });
  }
  if (date) {
    add({
      id: `surface-date-${surface.id}`,
      type: "Current date",
      title: "Date interpretation",
      description: `Interpreted the request against ${formatDate(date)}.`,
      why: "The request used today, this week, or another date-bound planning frame.",
      status: "Included",
    });
  }
}

function surfaceDecisions(turn: NormalizedTurn, surfaces: SurfacePayload[]): SurfaceDecisionModel[] {
  const decisions: SurfaceDecisionModel[] = [];
  const seen = new Set<string>();
  const invocation = turn.surfaceInvocation;

  const add = (decision: SurfaceDecisionModel) => {
    if (!seen.has(decision.id)) {
      seen.add(decision.id);
      decisions.push(decision);
    }
  };

  for (const invoked of invocation?.surfaces || []) {
    const opened = surfaceStatusOpened(invoked.status);
    add({
      id: `invoked-${invoked.kind}`,
      name: surfaceLabel(invoked.kind),
      opened,
      mode: invoked.role ? humanize(invoked.role) : readableMode(invocation?.writeBehavior || ""),
      reason: safeReason(invoked.reason || invocation?.reason, "Surface policy selected this route."),
      detail: opened ? "Opened" : humanize(invoked.status || "not opened"),
    });
  }

  for (const surface of surfaces) {
    add({
      id: `payload-${surface.kind}`,
      name: surfaceLabel(surface.kind),
      opened: true,
      mode: readableMode(invocation?.writeBehavior || "read_only"),
      reason: safeReason(surface.summary, "The backend returned this surface payload for the latest answer."),
      detail: "Opened",
    });
  }

  for (const kind of notOpenedCandidates(turn, surfaces)) {
    add({
      id: `not-opened-${kind}`,
      name: surfaceLabel(kind),
      opened: false,
      mode: "Not opened",
      reason: notOpenedReason(kind, invocation),
      detail: "Not opened",
    });
  }

  if (!decisions.length) {
    add({
      id: "chat-only",
      name: "Artifact surfaces",
      opened: false,
      mode: "Chat only",
      reason: "No artifact or operational domain was selected for this turn.",
      detail: "Not opened",
    });
  }

  return decisions;
}

function decisionPath(
  turn: NormalizedTurn,
  surfaces: SurfacePayload[],
  writes: MemoryActionsWritesModel,
  basics: { request: string; requestDetail: string; intent: string; summary: string },
): DecisionPathStepModel[] {
  const selectedContext = turn.contextBudget?.summary || turn.answerBasis.summary || "Current request was prepared as context.";
  const attentionContext = turn.navigatorSelection?.reason
    || (turn.selectedAttentionResources.length
      ? `Selected ${turn.selectedAttentionResources.length} attention resource${turn.selectedAttentionResources.length === 1 ? "" : "s"}.`
      : "");
  const selectedSurfaceNames = surfaces.map((surface) => surfaceLabel(surface.kind));
  const surfaceCopy = selectedSurfaceNames.length
    ? `Opened ${selectedSurfaceNames.join(" + ")}`
    : (turn.surfaceInvocation?.primarySurface && turn.surfaceInvocation.primarySurface !== "chat"
        ? `Selected ${surfaceLabel(turn.surfaceInvocation.primarySurface)}`
        : "Stayed in chat");
  return [
    { id: "request", label: "Input", value: basics.request, detail: basics.requestDetail },
    { id: "intent", label: "Intent", value: basics.intent, detail: confidenceLabel(turn.surfaceInvocation?.confidence ?? turn.semanticFrame?.confidence) },
    { id: "query", label: "Query keys", value: queryKeySummary(turn) },
    { id: "context", label: "Context selection", value: safeReason(attentionContext, selectedContext), detail: attentionSelectionDetail(turn) },
    { id: "surface", label: "Surface decision", value: surfaceCopy, detail: safeReason(turn.surfaceInvocation?.reason, "No separate surface was required.") },
    { id: "answer", label: "Answer", value: basics.summary },
    { id: "after-turn", label: "After-turn changes", value: writes.summary },
  ];
}

function requestMetadata(turn: NormalizedTurn): string {
  const candidates = [
    turn.surfaceInvocation?.intent,
    turn.semanticFrame?.taskType,
    turn.activity?.mode,
    turn.mode,
  ].filter(Boolean);
  const requestType = humanize(String(candidates[0] || "chat"));
  return `${requestType} input. Raw prompt text is not shown in Working Memory.`;
}

function safeReason(value: string | undefined | null, fallback: string): string {
  const cleaned = text(value).trim();
  if (!cleaned) {
    return fallback;
  }
  const normalized = cleaned.toLowerCase();
  if (
    normalized.includes("user explicitly requested")
    || normalized.includes("user requested")
    || normalized.includes("user asked")
    || normalized.includes("the user asked")
  ) {
    if (normalized.includes("close") || normalized.includes("hide") || normalized.includes("remove")) {
      return "Surface close action.";
    }
    if (normalized.includes("keep") || normalized.includes("leave") || normalized.includes("preserve")) {
      return "Surface preserve action.";
    }
    return fallback;
  }
  return cleaned;
}

function buildWrites(turn: NormalizedTurn, surfaces: SurfacePayload[]): MemoryActionsWritesModel {
  const savedMemory = turn.learnedItems.map((item) => item.title || item.id).filter(Boolean);
  const createdArtifacts: string[] = [];
  const draftWrites: string[] = [];
  const updatedTasks: string[] = [];
  const editedCalendar: string[] = [];
  const proposedMemory: string[] = [];
  const assumptions: string[] = [];

  if (turn.workspaceUpdate) {
    draftWrites.push(turn.workspaceUpdate.summary || turn.workspaceUpdate.title || "Whiteboard draft updated.");
  }
  if (turn.createdRecord) {
    createdArtifacts.push(text(turn.createdRecord.title || turn.createdRecord.id || "Created record"));
  }
  for (const surface of surfaces) {
    createdArtifacts.push(`${surface.title || surfaceLabel(surface.kind)} (read-only surface)`);
    const date = text(surface.data.date || asRecord(surface.data.calendar).date || asRecord(surface.data.calendar_week).start_date);
    if (date) {
      assumptions.push(`Date-bound request resolved to ${formatDate(date)}.`);
    }
  }

  const graphType = text(turn.graphAction?.type || turn.graphAction?.kind);
  const graphSummary = text(turn.graphAction?.summary || turn.graphAction?.message || graphType);
  if (graphSummary) {
    if (/task|todo/i.test(graphType)) {
      updatedTasks.push(graphSummary);
    } else if (/calendar|event/i.test(graphType)) {
      editedCalendar.push(graphSummary);
    } else {
      proposedMemory.push(graphSummary);
    }
  }
  const metaSummary = text(turn.metaAction?.summary || turn.metaAction?.message || turn.metaAction?.type);
  if (metaSummary && !savedMemory.includes(metaSummary)) {
    proposedMemory.push(metaSummary);
  }
  for (const action of turn.artifactActions) {
    const summary = `${humanize(action.status)}: ${action.summary || action.operation}`;
    const capture = action.capture || asRecord(action.payload.capture);
    if (action.artifactKind === "calendar") {
      editedCalendar.push(summary);
    } else if (/task|todo/i.test(action.artifactKind)) {
      updatedTasks.push(summary);
    } else {
      createdArtifacts.push(summary);
    }
    if (Object.keys(capture).length) {
      const fields = asRecord(capture.parsed_fields);
      const parsedTitle = text(fields.title);
      assumptions.push(text(capture.reason || "Capture layer produced this proposed action."));
      if (parsedTitle) {
        assumptions.push(`Parsed captured item: ${parsedTitle}.`);
      }
    }
    for (const warning of action.warnings) {
      assumptions.push(warning);
    }
  }

  const mode = readableMode(turn.surfaceInvocation?.writeBehavior || (hasWrites({
    savedMemory,
    proposedMemory,
    updatedTasks,
    editedCalendar,
    createdArtifacts: turn.createdRecord ? createdArtifacts : [],
    draftWrites,
  }) ? "proposal_only" : "read_only"));

  const mutableWrites = hasWrites({ savedMemory, proposedMemory, updatedTasks, editedCalendar, createdArtifacts: turn.createdRecord ? createdArtifacts : [], draftWrites });
  const summary = mutableWrites ? "Changes or proposals were recorded." : "No writes. Read-only.";

  return {
    savedMemory,
    proposedMemory,
    updatedTasks,
    editedCalendar,
    createdArtifacts,
    draftWrites,
    mode,
    assumptions: assumptions.length ? assumptions : ["None"],
    summary,
  };
}

function generationSummary({
  turn,
  surfaces,
  grounding,
  intent,
  writes,
}: {
  turn: NormalizedTurn;
  surfaces: SurfacePayload[];
  grounding: string[];
  intent: string;
  writes: MemoryActionsWritesModel;
}): string {
  const used = grounding.length ? grounding.join(", ") : "the current request";
  const opened = surfaces.map((surface) => surfaceLabel(surface.kind));
  if (opened.length) {
    return `Answered as ${intent} using ${used}; opened ${opened.join(" + ")}. ${writes.summary}`;
  }
  const basis = firstNonEmpty(turn.answerBasis.summary, turn.responseMode.note, turn.activity?.summary);
  if (basis) {
    return `${basis} ${writes.summary}`;
  }
  return `Answered as ${intent} using ${used}. ${writes.summary}`;
}

function hasWrites(groups: Omit<MemoryActionsWritesModel, "mode" | "assumptions" | "summary">): boolean {
  return [
    groups.savedMemory,
    groups.proposedMemory,
    groups.updatedTasks,
    groups.editedCalendar,
    groups.createdArtifacts,
    groups.draftWrites,
  ].some((items) => items.length > 0);
}

function groundingTypes(turn: NormalizedTurn, surfaces: SurfacePayload[]): string[] {
  const values = [
    ...turn.answerBasis.sources,
    ...turn.responseMode.contextSources,
    ...(turn.contextBudget?.contextSources || []),
    ...turn.selectedAttentionResources.map((item) => item.app || item.kind || "attention"),
    ...surfaces.flatMap((surface) => {
      if (surface.kind === "today_briefing") {
        return ["calendar", "tasks", "current_date"];
      }
      if (surface.kind.startsWith("calendar")) {
        return ["calendar", "current_date"];
      }
      if (surface.kind === "task_focus") {
        return ["tasks"];
      }
      return [surface.kind];
    }),
  ].map(humanize).filter(Boolean);
  return [...new Set(values)].slice(0, 5);
}

function notOpenedCandidates(turn: NormalizedTurn, surfaces: SurfacePayload[]): string[] {
  const invocation = turn.surfaceInvocation;
  const selected = new Set([
    invocation?.primarySurface,
    ...(invocation?.supportingSurfaces || []),
    ...(invocation?.surfaces || []).map((surface) => surface.kind),
    ...surfaces.map((surface) => surface.kind),
  ].filter(Boolean));
  const capabilitySurfaces = turn.appCapabilities?.surfaces.map((surface) => surface.kind) || [];
  const candidates = [...capabilitySurfaces, "whiteboard", "draft", "scenario_lab", "calendar_day", "task_focus"];
  return candidates.filter((kind) => !selected.has(kind)).slice(0, surfaces.length ? 3 : 2);
}

function notOpenedReason(kind: string, invocation: NormalizedTurn["surfaceInvocation"]): string {
  if (kind === "whiteboard") {
    return "No durable draft or long-form canvas was required by the selected route.";
  }
  if (kind === "draft") {
    return "No draft write was returned by the backend for this turn.";
  }
  if (kind === "scenario_lab") {
    return "No branching, tradeoff comparison, or scenario request was detected.";
  }
  if (kind.startsWith("calendar")) {
    return invocation?.reason || "The request did not require calendar data.";
  }
  if (kind === "task_focus") {
    return invocation?.reason || "The request did not require task prioritization.";
  }
  return "This surface was not selected for the latest answer.";
}

function queryKeySummary(turn: NormalizedTurn): string {
  const frame = turn.queryFrame;
  if (!frame) {
    return "No query frame was recorded.";
  }
  const parts = [
    frame.domains.length ? `Domains: ${frame.domains.map(humanize).join(", ")}` : "",
    frame.operations.length ? `Operations: ${frame.operations.map(humanize).join(", ")}` : "",
    frame.entities.length ? `Entities: ${frame.entities.join(", ")}` : "",
    frame.temporalReferences.length
      ? `Time: ${frame.temporalReferences.map((item) => `${item.rawText} (${item.relation})`).join(", ")}`
      : "",
  ].filter(Boolean);
  return parts.join(" · ") || "Current request only.";
}

function attentionSelectionDetail(turn: NormalizedTurn): string {
  const selection = turn.navigatorSelection;
  if (!selection) {
    return turn.attentionCandidates.length
      ? `${turn.attentionCandidates.length} candidates ranked; none selected.`
      : "No attention candidates were needed.";
  }
  const selected = selection.selectedIds.length;
  const rejected = selection.rejectedCandidateIds.length;
  const fallback = selection.fallback ? " Deterministic fallback was used." : "";
  const vectorHits = turn.attentionCandidates.filter((candidate) => attentionVectorScore(candidate) >= 0.16).length;
  const vectorCopy = vectorHits
    ? ` ${vectorHits} semantic vector match${vectorHits === 1 ? "" : "es"} contributed.`
    : "";
  return `${selected} selected, ${rejected} rejected.${fallback}${vectorCopy}`.trim();
}

function attentionVectorScore(candidate: { retrievalScores?: Record<string, number> }): number {
  return candidate.retrievalScores?.vector_similarity
    ?? candidate.retrievalScores?.vectorSimilarity
    ?? 0;
}

function taskSummaryFromSurface(surface: SurfacePayload): string {
  const tasks = asRecord(surface.data.tasks);
  const summary = asRecord(tasks.summary);
  const groups = asRecord(tasks.groups);
  const total = Number(summary.total_count || summary.total || 0)
    || asArray(groups.must_do_today).length
    + asArray(groups.good_next).length
    + asArray(groups.can_defer).length
    + asArray(groups.unscheduled).length;
  return `${total} task${total === 1 ? "" : "s"} grouped for focus.`;
}

function surfaceStatusOpened(status: string): boolean {
  const normalized = status.toLowerCase().replace(/[\s-]+/g, "_");
  return !["not_opened", "closed", "excluded", "none", "handled_elsewhere"].includes(normalized);
}

function contextTypeFromRecord(value: string): string {
  const normalized = value.toLowerCase().replace(/[\s-]+/g, "_");
  if (normalized.includes("protocol")) {
    return "Protocol";
  }
  if (normalized.includes("calendar")) {
    return "Calendar";
  }
  if (normalized.includes("task")) {
    return "Tasks";
  }
  if (normalized.includes("trace")) {
    return "Memory Trace";
  }
  if (normalized.includes("artifact") || normalized.includes("workspace")) {
    return "Visible artifact";
  }
  return "Memory";
}

function readableMode(value: string): string {
  const normalized = value.toLowerCase().replace(/[\s-]+/g, "_");
  if (normalized === "read_only" || normalized === "none") {
    return "Read-only";
  }
  if (normalized === "proposal_only") {
    return "Proposal-only";
  }
  if (normalized === "draft_only") {
    return "Draft-only";
  }
  return humanize(value || "read_only");
}

function confidenceLabel(value: number | null | undefined): string {
  return Number.isFinite(Number(value)) ? `${Math.round(Number(value) * 100)}% confidence` : "";
}

function firstSentence(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  const match = trimmed.match(/^(.{1,180}?[.!?])(?:\s|$)/);
  return match?.[1] || trimmed.slice(0, 180);
}

function firstNonEmpty(...values: Array<string | undefined | null>): string {
  for (const value of values) {
    const candidate = text(value);
    if (candidate) {
      return candidate;
    }
  }
  return "";
}

function humanize(value: string): string {
  return text(value)
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatDate(value: string): string {
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}
