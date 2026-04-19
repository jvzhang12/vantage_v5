function normalizedString(value, fallback = "") {
  const normalized = String(value ?? "").trim();
  return normalized || fallback;
}

function hasOwn(object, key) {
  return Boolean(object) && Object.prototype.hasOwnProperty.call(object, key);
}

export function buildWorkspaceSnapshot(workspace = {}) {
  const workspaceId = normalizedString(workspace.workspaceId || workspace.workspace_id);
  const content = String(workspace.content ?? "");
  const dirty = workspace.dirty === true;
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
