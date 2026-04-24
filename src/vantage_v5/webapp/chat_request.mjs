import { isWhiteboardFocused } from "./surface_state.mjs";

const EXPLICIT_WHITEBOARD_OPEN_RE = /\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard\b/i;
const EXPLICIT_WHITEBOARD_DRAFT_RE = /\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b/i;
const DEICTIC_WHITEBOARD_REOPEN_VERB_RE = /\b(?:open|show|load|reopen)\b|\bpull\b.{0,20}\bup\b|\bbring\b.{0,20}\bup\b/i;
const DEICTIC_WHITEBOARD_REOPEN_TARGET_RE = /\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b/i;
const DEICTIC_WHITEBOARD_REOPEN_RE = /\b(?:open|show|load|reopen)\b.{0,80}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,80}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b|\bpull\b.{0,40}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,20}\bup\b.{0,60}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b|\bbring\b.{0,40}\b(?:it|this|that|that one|this one|the other(?:\s+(?:email|draft|artifact|note|one))?|the previous(?:\s+(?:email|draft|artifact|note|one))?|the earlier(?:\s+(?:email|draft|artifact|note|one))?|the last(?:\s+(?:email|draft|artifact|note|one))?)\b.{0,20}\bup\b.{0,60}\b(?:in|on|into|onto)\s+(?:the\s+)?whiteboard\b/i;
const NARROW_EXPLICIT_WHITEBOARD_OPEN_RE = /^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard(?:\s+(?:for|about|with)\s+(?:it|this|that|the draft|this draft|that draft|the current draft))?\s*[.!?]?\s*$/i;
const NARROW_EXPLICIT_WHITEBOARD_DEICTIC_RE = /^\s*(?:(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\s*[,.:;-]?\s+)?(?:please\s+)?(?:put|move|place|add|draft|write|edit|revise|refine|update|change|adjust|include|incorporate|work on|build|create|outline|sketch|review|rewrite)\b.{0,40}\b(?:it|this|that|the draft|this draft|that draft|the current draft)\b.{0,40}\b(?:in|on|into|onto|to)\s+(?:the\s+)?whiteboard\s*[.!?]?\s*$/i;
const PENDING_DEICTIC_FOLLOW_UP_RE = /^\s*(?:(?:please\s+)?(?:which one|what about(?:\s+(?:it|this|that|that one|this one|those|these))?|tell me more|go deeper|elaborate|expand(?:\s+on\s+(?:it|this|that))?|that one|this one|those|these))\s*[.!?]?\s*$/i;
const PENDING_ACCEPT_RE = /\b(?:yes|yeah|yep|sure|ok(?:ay)?|please do|go ahead|do it|start draft|open draft|open it|use it|sounds good|works for me|let'?s do that|that works|that sounds good)\b/i;
const PENDING_CONTINUE_RE = /\b(?:continue|keep going|go on|carry on|pick up where we left off|resume)\b/i;
const PENDING_REFERENCE_RE = /\b(?:draft|whiteboard|email|plan|list|outline|document|note|it|this|that)\b/i;
const PENDING_EDIT_VERB_RE = /\b(?:update|revise|edit|refine|rewrite|change|adjust|add|remove|include|incorporate|personalize|polish|tighten|shorten|expand|improve)\b/i;
const PENDING_EDIT_TARGET_RE = /\b(?:email|draft|whiteboard|plan|list|outline|essay|document|note|signature|greeting|it|this|that)\b/i;
const MAX_PENDING_FOLLOW_UP_LENGTH = 240;
const WORKSPACE_CONTEXT_SCOPES = new Set(["auto", "excluded", "visible", "pinned", "requested"]);
const IN_SCOPE_WORKSPACE_CONTEXT_SCOPES = new Set(["visible", "pinned", "requested"]);

function normalizeMessage(message = "") {
  return String(message || "").trim();
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
  if (DEICTIC_WHITEBOARD_REOPEN_RE.test(text)) {
    return true;
  }
  return (
    text.toLowerCase().includes("whiteboard")
    && DEICTIC_WHITEBOARD_REOPEN_VERB_RE.test(text)
    && DEICTIC_WHITEBOARD_REOPEN_TARGET_RE.test(text)
  );
}

function isReopenableWhiteboardTarget(item) {
  if (!item || typeof item !== "object") {
    return false;
  }
  const id = normalizeMessage(item.id);
  const source = normalizeMessage(item.source).toLowerCase();
  return Boolean(id) && item.isVaultNote !== true && source !== "memory_trace";
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
  workspacePinned = false,
  message = "",
  forceScope = null,
} = {}) {
  const normalizedForcedScope = String(forceScope || "").trim().toLowerCase();
  if (WORKSPACE_CONTEXT_SCOPES.has(normalizedForcedScope)) {
    return normalizedForcedScope;
  }
  if (workspacePinned) {
    return "pinned";
  }
  if (isWhiteboardFocused(surface)) {
    return "visible";
  }
  if (isExplicitWhiteboardRequest(message)) {
    return "requested";
  }
  return "excluded";
}

export function buildWorkspaceContextPayload({
  surface = {},
  workspace = {},
  workspacePinned = false,
  message = "",
  forceScope = null,
} = {}) {
  const workspaceScope = deriveWorkspaceContextScope({
    surface,
    workspacePinned,
    message,
    forceScope,
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
