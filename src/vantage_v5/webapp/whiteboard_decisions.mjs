import { isWhiteboardFocused } from "./surface_state.mjs";

export { isWhiteboardFocused };

const WORKSPACE_RESOLUTION_DECISIONS = new Set([
  "opened_whiteboard",
  "applied",
  "appended",
  "kept_in_chat",
  "kept_current",
]);

export function normalizeWorkspaceDecision(value) {
  return String(value || "").trim().toLowerCase();
}

export function isWorkspaceResolutionDecision(value) {
  return WORKSPACE_RESOLUTION_DECISIONS.has(normalizeWorkspaceDecision(value));
}

export function hasPendingWorkspaceDecision(workspaceUpdate) {
  return Boolean(
    workspaceUpdate
    && ["offered", "draft_ready"].includes(String(workspaceUpdate.status || "").trim().toLowerCase())
    && !isWorkspaceResolutionDecision(workspaceUpdate.decision),
  );
}

export function workspaceUpdateHasDraft(workspaceUpdate) {
  return Boolean(workspaceUpdate && typeof workspaceUpdate.content === "string" && workspaceUpdate.content.trim());
}

export function shouldHideChatWorkspaceUpdate({ hidden = false, view = {}, workspaceUpdate = null } = {}) {
  return Boolean(hidden || isWhiteboardFocused(view) || !hasPendingWorkspaceDecision(workspaceUpdate));
}

function buildLocalDecisionPresentation(localDecision) {
  const targetLabel = localDecision?.targetLabel || "this item";
  switch (localDecision?.kind) {
    case "open_record":
      return {
        visible: true,
        label: "Replace Current Whiteboard?",
        summary: `Opening ${targetLabel} would replace the current unsaved whiteboard. You can replace it or keep the current draft.`,
        actions: [
          { id: "replace_current", label: "Replace current", tone: "primary" },
          { id: "cancel_decision", label: "Keep current", tone: "secondary" },
        ],
      };
    case "open_workspace":
      return {
        visible: true,
        label: "Open Workspace?",
        summary: `Opening ${targetLabel} would replace the current unsaved whiteboard. You can replace it or keep the current draft.`,
        actions: [
          { id: "replace_current", label: "Replace current", tone: "primary" },
          { id: "cancel_decision", label: "Keep current", tone: "secondary" },
        ],
      };
    case "pending_draft_replace":
      return {
        visible: true,
        label: "Replace Current Whiteboard?",
        summary: "A new draft is ready, but replacing now would overwrite the current unsaved whiteboard. You can replace it, append it instead, or keep the current draft.",
        actions: [
          { id: "replace_current", label: "Replace current", tone: "primary" },
          { id: "append_instead", label: "Append instead", tone: "secondary" },
          { id: "cancel_decision", label: "Keep current", tone: "secondary" },
        ],
      };
    default:
      return { visible: false, label: "", summary: "", actions: [] };
  }
}

export function deriveWhiteboardDecisionPresentation({ view = {}, localDecision = null, workspaceUpdate = null } = {}) {
  if (!isWhiteboardFocused(view)) {
    return { visible: false, label: "", summary: "", actions: [] };
  }
  if (localDecision && typeof localDecision === "object") {
    const presentation = buildLocalDecisionPresentation(localDecision);
    if (presentation.visible) {
      return presentation;
    }
  }
  if (!hasPendingWorkspaceDecision(workspaceUpdate)) {
    return { visible: false, label: "", summary: "", actions: [] };
  }

  const status = String(workspaceUpdate.status || "").trim().toLowerCase();
  if (status === "offered") {
    return {
      visible: true,
      label: "Whiteboard Offer",
      summary: workspaceUpdate.summary || "Vantage suggested continuing this work in the whiteboard.",
      actions: [
        {
          id: "open_offer",
          label: workspaceUpdateHasDraft(workspaceUpdate) ? "Open draft" : "Start draft",
          tone: "primary",
        },
        { id: "keep_in_chat", label: "Keep in chat", tone: "secondary" },
      ],
    };
  }

  return {
    visible: true,
    label: "Whiteboard Draft Ready",
    summary: workspaceUpdate.summary || "A whiteboard draft is ready to review before it changes the current whiteboard.",
    actions: [
      { id: "apply_draft", label: "Replace current", tone: "primary" },
      { id: "append_draft", label: "Append instead", tone: "secondary" },
      { id: "keep_current", label: "Keep current", tone: "secondary" },
    ],
  };
}
