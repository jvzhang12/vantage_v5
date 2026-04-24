import {
  closeVantageSurface,
  normalizeSurfaceState,
} from "./surface_state.mjs";

function normalizedString(value, fallback = "") {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}

function hasOwn(object, key) {
  return Boolean(object) && Object.prototype.hasOwnProperty.call(object, key);
}

function normalizeWorkspaceContent(value) {
  return String(value ?? "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.replace(/[ \t]+$/g, ""))
    .join("\n")
    .trim();
}

function sameWorkspaceContinuity(currentWorkspace = {}, incomingWorkspace = {}) {
  const current = buildWorkspaceSnapshot(currentWorkspace);
  const incoming = buildWorkspaceSnapshot(incomingWorkspace);
  if (!current.workspaceId || !incoming.workspaceId) {
    return false;
  }
  return current.workspaceId === incoming.workspaceId
    && current.scope === incoming.scope
    && normalizeWorkspaceContent(current.content) === normalizeWorkspaceContent(incoming.content);
}

export function buildWorkspaceSnapshot(workspace = {}) {
  const workspaceId = normalizedString(workspace.workspaceId || workspace.workspace_id);
  const content = String(workspace.content ?? "");
  const dirty = workspace.dirty === true;
  const latestArtifact = workspace.latestArtifact && typeof workspace.latestArtifact === "object"
    ? { ...workspace.latestArtifact }
    : workspace.latest_artifact && typeof workspace.latest_artifact === "object"
      ? { ...workspace.latest_artifact }
      : null;
  const savedContent = hasOwn(workspace, "savedContent") || hasOwn(workspace, "saved_content")
    ? String(workspace.savedContent ?? workspace.saved_content ?? "")
    : dirty
      ? ""
      : content;

  return {
    workspaceId,
    scope: normalizedString(workspace.scope, "durable"),
    title: normalizedString(workspace.title, "Whiteboard"),
    content,
    savedContent,
    dirty,
    pinnedToChat: workspace.pinnedToChat === true,
    lifecycle: normalizedString(
      workspace.lifecycle,
      dirty ? "transient_draft" : workspaceId ? "saved_whiteboard" : "ready",
    ),
    note: normalizedString(workspace.note),
    latestArtifact,
  };
}

export function shouldPreserveUnsavedWorkspace({
  currentWorkspace = {},
  incomingWorkspace = {},
  preserveDirty = false,
} = {}) {
  if (!preserveDirty) {
    return false;
  }

  const current = buildWorkspaceSnapshot(currentWorkspace);
  if (!current.dirty) {
    return false;
  }

  const incoming = buildWorkspaceSnapshot({
    ...incomingWorkspace,
    dirty: false,
  });
  if (incoming.scope !== current.scope) {
    return false;
  }

  const currentSavedContent = String(current.savedContent || "").trim();
  const incomingContent = String(incoming.content || "").trim();
  if (currentSavedContent && incomingContent && incomingContent !== currentSavedContent) {
    return false;
  }

  return true;
}

export function reconcileRestoredWorkspaceAfterLoad({
  currentWorkspace = {},
  incomingWorkspace = {},
  preserveDirty = false,
  scopeScopedFallback = false,
  surface = {},
  selectedConceptId = "",
  selectedVaultNoteId = "",
  selectionOrigin = "bootstrap",
} = {}) {
  const restoredWorkspace = buildWorkspaceSnapshot(currentWorkspace);
  const loadedWorkspace = buildWorkspaceSnapshot(incomingWorkspace);
  const preserveRestoredWorkspace = shouldPreserveUnsavedWorkspace({
    currentWorkspace: restoredWorkspace,
    incomingWorkspace: loadedWorkspace,
    preserveDirty,
  });
  const workspace = preserveRestoredWorkspace ? restoredWorkspace : loadedWorkspace;
  const workspaceReplaced = !preserveRestoredWorkspace
    && !sameWorkspaceContinuity(restoredWorkspace, workspace);
  const resetInspectionState = scopeScopedFallback || workspaceReplaced;
  const normalizedSurface = normalizeSurfaceState(surface);

  return {
    workspace,
    preserveRestoredWorkspace,
    workspaceReplaced,
    surface: resetInspectionState ? closeVantageSurface(normalizedSurface) : normalizedSurface,
    selectedConceptId: resetInspectionState ? "" : normalizedString(selectedConceptId),
    selectedVaultNoteId: resetInspectionState ? "" : normalizedString(selectedVaultNoteId),
    selectionOrigin: resetInspectionState ? "bootstrap" : normalizedString(selectionOrigin, "bootstrap"),
  };
}
