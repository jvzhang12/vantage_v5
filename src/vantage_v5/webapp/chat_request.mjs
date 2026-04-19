import { isWhiteboardFocused } from "./surface_state.mjs";

const EXPLICIT_WHITEBOARD_OPEN_RE = /\b(?:open|pull up|bring up|show|use|start|resume)\s+(?:the\s+)?whiteboard\b/i;
const EXPLICIT_WHITEBOARD_DRAFT_RE = /\b(?:draft|write|put|move|build|plan|outline|sketch|work|create|review|refine|play)\b.{0,80}\b(?:in|on|into)\s+(?:the\s+)?whiteboard\b/i;
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
  if (isExplicitWhiteboardRequest(text)) {
    return true;
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
