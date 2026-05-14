import {
  hasWhiteboardActiveContext,
  normalizeSurfaceState,
} from "./surface_state.mjs";

const EXPLICIT_WHITEBOARD_OPEN_RE = /\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:(?:a|the)\s+)?(?:(?:fresh|new|blank|empty|shared)\s+)?whiteboard\b/i;
const EXPLICIT_WHITEBOARD_DRAFT_RE = /\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b/i;
const FRESH_WHITEBOARD_REQUEST_RE = /\b(?:open|pull up|bring up|show|use|start)\s+(?:(?:a|the)\s+)?(?:fresh|new|blank|empty|shared)\s+whiteboard\b/i;
const WHITEBOARD_FOR_DEICTIC_TARGET_RE = /\b(?:open|show|load|reopen|pull up|bring up|use|start|resume)\s+(?:the\s+)?whiteboard\b.{0,50}\b(?:for|with|about)\s+(?:it|this|that|the draft|this draft|that draft|the current draft)\b/i;
const DEICTIC_WHITEBOARD_REOPEN_VERB_RE = /\b(?:open|show|load|reopen)\b|\bpull\b.{0,20}\bup\b|\bbring\b.{0,20}\bup\b/i;
const DEICTIC_WHITEBOARD_REOPEN_TARGET_RE = /\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b/i;
const DEICTIC_WHITEBOARD_REOPEN_RE = /\b(?:open|show|load|reopen)\b.{0,80}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,80}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b|\bpull\b.{0,40}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,20}\bup\b.{0,60}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b|\bbring\b.{0,40}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,20}\bup\b.{0,60}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b/i;
const NARROW_EXPLICIT_WHITEBOARD_OPEN_RE = /^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard(?:\s+(?:for|about|with)\s+(?:it|this|that|the draft|this draft|that draft|the current draft))?\s*[.!?]?\s*$/i;
const NARROW_EXPLICIT_WHITEBOARD_DEICTIC_RE = /^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:put|move|place|add|draft|write|edit|revise|refine|update|change|adjust|include|incorporate|work on|build|create|outline|sketch|review|rewrite)\b.{0,40}\b(?:it|this|that|the draft|this draft|that draft|the current draft)\b.{0,40}\b(?:in|on|into|onto|to)\s+(?:the\s+)?whiteboard\s*[.!?]?\s*$/i;
const PENDING_DEICTIC_FOLLOW_UP_RE = /^\s*(?:(?:please\s+)?(?:which one|what about(?:\s+(?:it|this|that|that one|this one|those|these))?|tell me more|go deeper|elaborate|expand(?:\s+on\s+(?:it|this|that))?|that one|this one|those|these))\s*[.!?]?\s*$/i;
const PENDING_ACCEPT_RE = /\b(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\b/i;
const PENDING_CONTINUE_RE = /\b(?:continue|keep going|go on|carry on|pick up where we left off|resume)\b/i;
const PENDING_REFERENCE_RE = /\b(?:draft|whiteboard|email|plan|list|outline|document|note|it|this|that)\b/i;
const PENDING_EDIT_VERB_RE = /\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve|make|replace|apply|use)\b/i;
const PENDING_EDIT_TARGET_RE = /\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b/i;
const HIDDEN_DRAFT_REVISION_VERB_RE = /\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve|make|replace|rework|trim|soften|sharpen|simplify|mention)\b/i;
const HIDDEN_DRAFT_REVISION_TARGET_RE = /\b(?:current\s+)?(?:draft|email|document|doc|whiteboard|letter|message|note|outline|plan|proposal|it|this|that)\b|\b(?:greeting|intro|opening|signoff|signature|paragraph|section|tone)\b/i;
const CHAT_ONLY_REQUEST_RE = /\bchat[-\s]?only\b|\b(?:answer|respond|reply)\s+(?:only\s+)?(?:in|inside|over)\s+chat\b|\b(?:in|inside|over)\s+chat\s+only\b|\bkeep\s+(?:it|this|that|the\s+(?:answer|response|reply|draft|email|document|doc)|everything)\s+(?:in\s+)?chat\b|\bdon'?t\s+(?:use|open|touch|include|look\s+at)\s+(?:the\s+)?whiteboard\b|\b(?:no|without\s+(?:using\s+)?)\s+(?:the\s+)?whiteboard\b|\bnot\s+(?:in|on|into)\s+(?:the\s+)?whiteboard\b/i;
const NEW_OR_FRESH_DRAFT_REQUEST_RE = /\b(?:new|fresh|blank|empty)\s+(?:draft|email|document|doc|whiteboard|outline|plan|essay|note)\b|\b(?:draft|write|compose|create|start|build)\s+(?:me\s+)?(?:(?:a|an|the)\s+)?(?:new|fresh|blank|empty)\s+(?:draft|email|document|doc|outline|plan|essay|note)\b|\b(?:start|begin)\s+(?:a\s+)?(?:new|fresh)\s+(?:draft|email|document|doc|outline|plan|essay|note)\b|\bmake\s+(?:me\s+)?(?:a|an)\b.{0,60}\b(?:draft|email|document|doc|outline|plan|essay|note)\b/i;
const SUBJECT_LINE_BRAINSTORM_RE = /\bsubject\s+lines?\b.{0,80}\b(?:ideas?|options?|alternatives?|brainstorm|suggest(?:ions)?|come\s+up\s+with|generate|what\s+should)\b|\b(?:ideas?|options?|alternatives?|brainstorm|suggest(?:ions)?|come\s+up\s+with|generate)\b.{0,80}\bsubject\s+lines?\b/i;
const PINNED_RECORD_FOLLOW_UP_RE = /\b(?:pinned|selected|saved|library|recalled)\s+(?:context|record|item|draft|email|document|doc|artifact|note)\b|\b(?:that|this|the)\s+(?:pinned|selected|saved|library|recalled)\s+(?:context|record|item|draft|email|document|doc|artifact|note)\b/i;
const MAX_PENDING_FOLLOW_UP_LENGTH = 240;
const WORKSPACE_CONTEXT_SCOPES = new Set(["auto", "excluded", "visible", "pinned", "requested"]);
const IN_SCOPE_WORKSPACE_CONTEXT_SCOPES = new Set(["visible", "pinned", "requested"]);

function normalizeMessage(message = "") {
  return String(message || "").trim();
}

function normalizeRequestedWhiteboardMode(requestedWhiteboardMode = "auto") {
  return String(requestedWhiteboardMode || "").trim().toLowerCase();
}

function hasNonEmptyWorkspaceDraft(workspace = {}) {
  return Boolean(String(workspace?.content ?? workspace?.workspace_content ?? "").trim());
}

export function isExplicitChatOnlyRequest(message = "") {
  const text = normalizeMessage(message);
  if (!text) {
    return false;
  }
  return CHAT_ONLY_REQUEST_RE.test(text);
}

function hasChatOnlyOverride({ message = "", requestedWhiteboardMode = "auto" } = {}) {
  return normalizeRequestedWhiteboardMode(requestedWhiteboardMode) === "chat"
    || isExplicitChatOnlyRequest(message);
}

function isChatFocused(surface = {}) {
  return normalizeSurfaceState(surface).current === "chat";
}

export function isExplicitWhiteboardRequest(message = "") {
  const text = normalizeMessage(message);
  if (!text) {
    return false;
  }
  return EXPLICIT_WHITEBOARD_OPEN_RE.test(text) || EXPLICIT_WHITEBOARD_DRAFT_RE.test(text);
}

export function isDeicticWhiteboardReopenRequest(message = "") {
  const text = normalizeMessage(message);
  if (!text) {
    return false;
  }
  if (FRESH_WHITEBOARD_REQUEST_RE.test(text)) {
    return false;
  }
  if (DEICTIC_WHITEBOARD_REOPEN_RE.test(text)) {
    return true;
  }
  return WHITEBOARD_FOR_DEICTIC_TARGET_RE.test(text);
}

function isReopenableWhiteboardTarget(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const id = normalizeMessage(item.id);
  const source = normalizeMessage(item.source).toLowerCase();
  const type = normalizeMessage(item.type).toLowerCase();
  const kind = normalizeMessage(item.kind).toLowerCase();
  const memoryRole = normalizeMessage(item.memory_role || item.memoryRole).toLowerCase();
  const protocolKind = normalizeMessage(
    item.protocol_kind
      || item.protocolKind
      || item.protocol?.protocol_kind
      || item.protocol?.protocolKind,
  );
  return Boolean(id)
    && item.isVaultNote !== true
    && source !== "memory_trace"
    && type !== "protocol"
    && kind !== "protocol"
    && memoryRole !== "protocol"
    && !protocolKind;
}

function uniqueReopenTargets(items = []) {
  const deduped = new Map();
  for (const item of Array.isArray(items) ? items : []) {
    if (!isReopenableWhiteboardTarget(item)) {
      continue;
    }
    const id = normalizeMessage(item.id);
    if (!deduped.has(id)) {
      deduped.set(id, {
        id,
        title: normalizeMessage(item.title) || id,
        source: normalizeMessage(item.source).toLowerCase() || "saved_note",
      });
    }
  }
  return [...deduped.values()];
}

export function resolveWhiteboardReopenTarget({
  message = "",
  pinnedItem = null,
  recalledItems = [],
  learnedItems = [],
} = {}) {
  if (!isDeicticWhiteboardReopenRequest(message)) {
    return null;
  }
  if (isReopenableWhiteboardTarget(pinnedItem)) {
    return uniqueReopenTargets([pinnedItem])[0] || null;
  }
  const targets = uniqueReopenTargets([
    ...(Array.isArray(recalledItems) ? recalledItems : []),
    ...(Array.isArray(learnedItems) ? learnedItems : []),
  ]);
  if (targets.length !== 1) {
    return null;
  }
  return targets[0];
}

export function shouldCarryPendingWorkspaceUpdate(message = "", { force = false } = {}) {
  if (force) {
    return true;
  }
  const text = normalizeMessage(message);
  if (!text) {
    return false;
  }
  if (text.length > MAX_PENDING_FOLLOW_UP_LENGTH) {
    return false;
  }
  if (NARROW_EXPLICIT_WHITEBOARD_OPEN_RE.test(text) || NARROW_EXPLICIT_WHITEBOARD_DEICTIC_RE.test(text)) {
    return true;
  }
  if (isExplicitWhiteboardRequest(text)) {
    return false;
  }
  if (PENDING_ACCEPT_RE.test(text)) {
    return true;
  }
  if (PENDING_CONTINUE_RE.test(text) && PENDING_REFERENCE_RE.test(text)) {
    return true;
  }
  if (PENDING_EDIT_VERB_RE.test(text) && PENDING_EDIT_TARGET_RE.test(text)) {
    return true;
  }
  if (PENDING_DEICTIC_FOLLOW_UP_RE.test(text)) {
    return true;
  }
  return false;
}

export function deriveWorkspaceContextScope({
  surface = {},
  workspace = {},
  workspacePinned = false,
  message = "",
  forceScope = null,
  requestedWhiteboardMode = "auto",
} = {}) {
  if (hasChatOnlyOverride({ message, requestedWhiteboardMode })) {
    return "excluded";
  }
  const normalizedForcedScope = String(forceScope || "").trim().toLowerCase();
  if (WORKSPACE_CONTEXT_SCOPES.has(normalizedForcedScope)) {
    return normalizedForcedScope;
  }
  if (workspacePinned) {
    return "pinned";
  }
  if (hasWhiteboardActiveContext(surface)) {
    return "visible";
  }
  if (shouldUseHiddenActiveWorkspaceDraftForRevision({
    surface,
    workspace,
    message,
    requestedWhiteboardMode,
  })) {
    return "requested";
  }
  if (isExplicitWhiteboardRequest(message) && shouldUseHiddenWorkspaceAsRequestedContext(message)) {
    return "requested";
  }
  return "excluded";
}

function shouldUseHiddenWorkspaceAsRequestedContext(message = "") {
  const text = normalizeMessage(message);
  if (!text) {
    return false;
  }
  return /\b(?:resume|continue|reopen)\b.{0,80}\b(?:the\s+)?whiteboard\b/i.test(text)
    || /\b(?:the\s+)?whiteboard\b.{0,80}\b(?:resume|continue|reopen)\b/i.test(text)
    || /\b(?:current|existing|active)\s+(?:whiteboard|draft)\b/i.test(text);
}

function shouldUseHiddenActiveWorkspaceDraftForRevision({
  surface = {},
  workspace = {},
  message = "",
  requestedWhiteboardMode = "auto",
} = {}) {
  const text = normalizeMessage(message);
  if (
    !text
    || hasChatOnlyOverride({ message: text, requestedWhiteboardMode })
    || !isChatFocused(surface)
    || !hasNonEmptyWorkspaceDraft(workspace)
    || FRESH_WHITEBOARD_REQUEST_RE.test(text)
    || NEW_OR_FRESH_DRAFT_REQUEST_RE.test(text)
    || SUBJECT_LINE_BRAINSTORM_RE.test(text)
    || PINNED_RECORD_FOLLOW_UP_RE.test(text)
  ) {
    return false;
  }
  return HIDDEN_DRAFT_REVISION_VERB_RE.test(text)
    && HIDDEN_DRAFT_REVISION_TARGET_RE.test(text);
}

export function buildWorkspaceContextPayload({
  surface = {},
  workspace = {},
  workspacePinned = false,
  message = "",
  forceScope = null,
  requestedWhiteboardMode = "auto",
} = {}) {
  const workspaceScope = deriveWorkspaceContextScope({
    surface,
    workspace,
    workspacePinned,
    message,
    forceScope,
    requestedWhiteboardMode,
  });
  const payload = {
    workspace_id: workspace?.workspaceId || null,
    workspace_scope: workspaceScope,
  };
  if (IN_SCOPE_WORKSPACE_CONTEXT_SCOPES.has(workspaceScope)) {
    payload.workspace_content = String(workspace?.content ?? "");
  }
  return payload;
}

export function buildVisibleArtifactsPayload({
  surface = {},
  workspace = {},
  turn = {},
} = {}) {
  const artifacts = [];
  const normalizedSurface = normalizeSurfaceState(surface);
  if (normalizedSurface.current === "whiteboard" && hasNonEmptyWorkspaceDraft(workspace)) {
    artifacts.push({
      id: workspace?.workspaceId || "visible-whiteboard",
      kind: "whiteboard",
      title: workspace?.title || "Whiteboard",
      summary: "Visible whiteboard draft.",
      content: String(workspace?.content ?? ""),
      source: "visible_whiteboard",
      active: true,
    });
  }
  const operationalSurface = activeOperationalSurface(turn);
  if (normalizedSurface.current === "chat" && operationalSurface) {
    const artifact = operationalSurfaceToArtifact(operationalSurface);
    if (artifact) {
      artifacts.push(artifact);
    }
  }
  return artifacts;
}

export function deriveChatWhiteboardMode({
  requestedWhiteboardMode = "auto",
  surface = {},
  workspace = {},
  message = "",
} = {}) {
  const normalizedMode = normalizeRequestedWhiteboardMode(requestedWhiteboardMode);
  if (hasChatOnlyOverride({ message, requestedWhiteboardMode: normalizedMode })) {
    return "chat";
  }
  const text = normalizeMessage(message);
  if (
    hasWhiteboardActiveContext(surface)
    && PENDING_EDIT_VERB_RE.test(text)
    && PENDING_EDIT_TARGET_RE.test(text)
  ) {
    return "draft";
  }
  if (shouldUseHiddenActiveWorkspaceDraftForRevision({
    surface,
    workspace,
    message: text,
    requestedWhiteboardMode: normalizedMode,
  })) {
    return "draft";
  }
  if (["offer", "draft", "auto"].includes(normalizedMode)) {
    return normalizedMode;
  }
  return "auto";
}

function activeOperationalSurface(turn = {}) {
  const surfaces = Array.isArray(turn?.surfacePayloads || turn?.surface_payloads)
    ? (turn.surfacePayloads || turn.surface_payloads)
    : [];
  if (!surfaces.length) {
    return null;
  }
  const activeId = String(turn?.activeSurfaceId || turn?.active_surface_id || "").trim();
  return surfaces.find((surface) => String(surface?.id || "") === activeId) || surfaces[0] || null;
}

function operationalSurfaceToArtifact(surface = {}) {
  const id = normalizeMessage(surface.id);
  const kind = normalizeMessage(surface.kind).toLowerCase();
  if (!id || !kind) {
    return null;
  }
  const content = operationalSurfaceMarkdown(surface);
  if (!content) {
    return null;
  }
  return {
    id,
    kind,
    title: normalizeMessage(surface.title) || humanizeSurfaceKind(kind),
    summary: normalizeMessage(surface.summary),
    source_refs: Array.isArray(surface.sourceRefs || surface.source_refs) ? (surface.sourceRefs || surface.source_refs) : [],
    content,
    data: surface.data && typeof surface.data === "object" ? surface.data : {},
    source: "visible_operational_surface",
    active: true,
  };
}

function operationalSurfaceMarkdown(surface = {}) {
  const kind = normalizeMessage(surface.kind).toLowerCase();
  const data = surface.data && typeof surface.data === "object" ? surface.data : {};
  if (kind === "calendar_week") {
    return calendarWeekMarkdown(data.calendar_week || data.calendarWeek || {});
  }
  if (kind === "calendar_day") {
    return calendarDayMarkdown(data.calendar || {});
  }
  if (kind === "today_briefing") {
    return [
      `# ${normalizeMessage(surface.title) || "Today"}`,
      "",
      normalizeMessage(surface.summary),
      "",
      calendarDayMarkdown(data.calendar || {}),
      "",
      taskFocusMarkdown(data.tasks || {}),
    ].filter(Boolean).join("\n");
  }
  if (kind === "task_focus") {
    return taskFocusMarkdown(data.tasks || {});
  }
  return [
    `# ${normalizeMessage(surface.title) || humanizeSurfaceKind(kind)}`,
    "",
    normalizeMessage(surface.summary),
    "",
    JSON.stringify(data, null, 2),
  ].filter(Boolean).join("\n");
}

function calendarWeekMarkdown(week = {}) {
  const lines = [
    `# Calendar Week: ${normalizeMessage(week.start_date)} to ${normalizeMessage(week.end_date)}`.trim(),
    "",
    calendarSummaryLine(week.summary),
  ].filter(Boolean);
  const days = Array.isArray(week.days) ? week.days : [];
  for (const day of days) {
    lines.push("", `## ${formatArtifactDate(day.date)}`);
    appendCalendarDayLines(lines, day);
  }
  return lines.join("\n").trim();
}

function calendarDayMarkdown(day = {}) {
  const lines = [
    `# Calendar Day: ${normalizeMessage(day.date) || "Current day"}`,
    "",
    calendarSummaryLine(day.summary),
  ].filter(Boolean);
  appendCalendarDayLines(lines, day);
  return lines.join("\n").trim();
}

function appendCalendarDayLines(lines, day = {}) {
  const events = Array.isArray(day.events) ? day.events : [];
  const freeBlocks = Array.isArray(day.free_blocks || day.freeBlocks) ? (day.free_blocks || day.freeBlocks) : [];
  if (events.length) {
    lines.push("### Events");
    for (const event of events) {
      lines.push(`- ${formatArtifactTimeRange(event.start, event.end)} ${normalizeMessage(event.title) || "Calendar event"}${event.location ? ` (${event.location})` : ""}`);
    }
  } else {
    lines.push("- No scheduled events.");
  }
  if (freeBlocks.length) {
    lines.push("### Open Blocks");
    for (const block of freeBlocks) {
      lines.push(`- ${formatArtifactTimeRange(block.start, block.end)} (${block.duration_minutes || block.durationMinutes || 0} min)`);
    }
  }
}

function taskFocusMarkdown(taskFocus = {}) {
  const lines = [`# Task Focus: ${normalizeMessage(taskFocus.date) || "Current tasks"}`];
  const groups = taskFocus.groups && typeof taskFocus.groups === "object" ? taskFocus.groups : {};
  const labels = [
    ["must_do_today", "Must do today"],
    ["good_next", "Good next"],
    ["can_defer", "Can defer"],
    ["unscheduled", "Unscheduled"],
  ];
  let rendered = 0;
  for (const [key, label] of labels) {
    const tasks = Array.isArray(groups[key]) ? groups[key] : [];
    lines.push("", `## ${label}`);
    if (!tasks.length) {
      lines.push("- None");
      continue;
    }
    rendered += tasks.length;
    for (const task of tasks) {
      lines.push(`- ${normalizeMessage(task.title) || "Untitled task"}${task.due_date ? ` (due ${task.due_date})` : ""}`);
    }
  }
  if (!rendered) {
    lines.push("", "No open tasks are visible in this task surface.");
  }
  return lines.join("\n").trim();
}

function calendarSummaryLine(summary = {}) {
  if (!summary || typeof summary !== "object") {
    return "";
  }
  const eventCount = Number(summary.event_count || summary.eventCount || 0);
  const freeMinutes = Number(summary.free_minutes || summary.freeMinutes || 0);
  return `${eventCount} scheduled event${eventCount === 1 ? "" : "s"}; ${freeMinutes} open minutes.`;
}

function formatArtifactDate(value) {
  return normalizeMessage(value) || "Unknown date";
}

function formatArtifactTimeRange(start, end) {
  const startText = normalizeMessage(start);
  const endText = normalizeMessage(end);
  return [startText, endText].filter(Boolean).join(" - ") || "Time TBD";
}

function humanizeSurfaceKind(value) {
  return normalizeMessage(value).replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) || "Artifact";
}
