import type {
  AppState,
  ArtifactAction,
  HealthPayload,
  NormalizedTurn,
  SelectedResourceState,
  SelectedAttentionResource,
  SurfaceInvocation,
  SurfacePayload,
  VisibleSurfacesState,
  ViewKind,
  WhiteboardEditorState,
  WorkspacePayload,
  WorkspaceState,
} from "./types";

const initialWorkspace: WorkspaceState = {
  id: "",
  title: "Whiteboard",
  content: "",
  scope: "durable",
  dirty: false,
  pinnedToChat: false,
};

const initialWhiteboardEditor: WhiteboardEditorState = {
  ...initialWorkspace,
  sourceResourceId: "",
  sourceKind: "",
};

export const initialState: AppState = {
  auth: {
    checking: true,
    required: false,
    authenticated: false,
    accountCreationEnabled: false,
    accountCreationCodeRequired: false,
    userId: "",
    modelLabel: "",
    error: "",
  },
  view: "chat",
  returnView: "chat",
  composerValue: "",
  busy: false,
  profileOpen: false,
  history: [],
  latestTurn: null,
  activeSurfaceId: null,
  surfacePayloads: [],
  workspace: initialWorkspace,
  visibleSurfaces: {
    foreground: "chat",
    activeSurfaceId: null,
    visibleSurfaceIds: [],
    whiteboardVisible: false,
  },
  whiteboardEditor: initialWhiteboardEditor,
  selectedResource: null,
  pinnedContext: null,
  includedContext: {
    visibleArtifactIds: [],
    activeSurfaceId: null,
    whiteboardVisible: false,
  },
  notice: null,
};

type Action =
  | { type: "BOOTSTRAP_HEALTH"; payload: HealthPayload }
  | { type: "AUTH_ERROR"; message: string }
  | { type: "SET_WORKSPACE"; payload: WorkspacePayload }
  | { type: "SET_COMPOSER"; value: string }
  | { type: "CHAT_START" }
  | { type: "CHAT_SUCCESS"; turn: NormalizedTurn }
  | { type: "CHAT_ERROR"; message: string }
  | { type: "SET_VIEW"; view: ViewKind }
  | { type: "SET_PROFILE_OPEN"; open: boolean }
  | { type: "SET_NOTICE"; title: string; message: string; tone?: "info" | "success" | "warning" }
  | { type: "CLEAR_NOTICE" }
  | { type: "UPDATE_WORKSPACE_CONTENT"; content: string }
  | { type: "WORKSPACE_SAVED"; payload: WorkspacePayload }
  | { type: "UPSERT_SURFACE"; surface: SurfacePayload; active?: boolean }
  | { type: "REMOVE_ACTIVE_ARTIFACT" }
  | {
      type: "ARTIFACT_ACTION_RESULT";
      result: {
        artifactActions: ArtifactAction[];
        surfacePayloads: SurfacePayload[];
        activeSurfaceId: string | null;
        assistantMessage: string;
        graphAction: Record<string, unknown> | null;
        surfaceInvocation: SurfaceInvocation | null;
        appCapabilities: NormalizedTurn["appCapabilities"];
      };
    }
  | { type: "LOGOUT" };

function modelLabel(payload: HealthPayload): string {
  return [payload.model_provider || payload.mode, payload.model].filter(Boolean).join(" / ");
}

function workspaceFromPayload(payload: WorkspacePayload, current: WorkspaceState = initialState.workspace): WorkspaceState {
  return {
    ...current,
    id: payload.workspace_id || payload.id || current.id,
    title: payload.title || current.title || "Whiteboard",
    content: typeof payload.content === "string" ? payload.content : current.content,
    scope: payload.scope || current.scope,
    dirty: false,
  };
}

function whiteboardEditorFromPayload(
  payload: WorkspacePayload,
  current: WhiteboardEditorState = initialState.whiteboardEditor,
): WhiteboardEditorState {
  return {
    ...workspaceFromPayload(payload, current),
    sourceResourceId: current.sourceResourceId,
    sourceKind: current.sourceKind,
  };
}

function workspaceFromEditor(editor: WhiteboardEditorState): WorkspaceState {
  return {
    id: editor.id,
    title: editor.title,
    content: editor.content,
    scope: editor.scope,
    dirty: editor.dirty,
    pinnedToChat: editor.pinnedToChat,
  };
}

function includedContextFrom(
  visibleSurfaces: VisibleSurfacesState,
  whiteboardEditor: WhiteboardEditorState,
): AppState["includedContext"] {
  const visibleArtifactIds = [...visibleSurfaces.visibleSurfaceIds];
  if (visibleSurfaces.whiteboardVisible && whiteboardEditor.content.trim()) {
    visibleArtifactIds.push(whiteboardEditor.id || "whiteboard");
  }
  return {
    visibleArtifactIds,
    activeSurfaceId: visibleSurfaces.activeSurfaceId,
    whiteboardVisible: visibleSurfaces.whiteboardVisible,
  };
}

function syncStateContext(state: AppState): AppState {
  return {
    ...state,
    workspace: workspaceFromEditor(state.whiteboardEditor),
    includedContext: includedContextFrom(state.visibleSurfaces, state.whiteboardEditor),
  };
}

function validSurfaceId(surfaceId: string | null, surfaces: SurfacePayload[]): string | null {
  if (!surfaceId) {
    return null;
  }
  return surfaces.some((surface) => surface.id === surfaceId) ? surfaceId : null;
}

function selectedWhiteboardResource(turn: NormalizedTurn): SelectedAttentionResource | null {
  const hasWhiteboardOpenDirective = turn.navigatorSelection?.surfaceToOpen === "whiteboard"
    || isOpenOnlyWhiteboardInvocation(turn);
  if (!hasWhiteboardOpenDirective) {
    return null;
  }
  const primaryResourceId = turn.navigatorSelection?.primaryResourceId;
  const primaryResource = turn.selectedAttentionResources.find((resource) => (
    Boolean(primaryResourceId) && resource.resourceId === primaryResourceId
  ));
  const selectedResource = (
    primaryResource && isOpenableWhiteboardResource(primaryResource)
      ? primaryResource
      : turn.selectedAttentionResources.find(isOpenableWhiteboardResource)
  ) || null;
  if (!selectedResource?.content.trim()) {
    return null;
  }
  return selectedResource;
}

function selectedResourceStateFromTurn(
  turn: NormalizedTurn,
  openedResource: SelectedAttentionResource | null,
): SelectedResourceState | null {
  const primaryResourceId = turn.navigatorSelection?.primaryResourceId;
  const primaryResource = turn.selectedAttentionResources.find((resource) => (
    Boolean(primaryResourceId) && resource.resourceId === primaryResourceId
  ));
  const resource = openedResource || primaryResource || turn.selectedAttentionResources[0] || null;
  if (!resource) {
    return null;
  }
  return {
    id: resource.id,
    resourceId: resource.resourceId,
    kind: resource.kind,
    title: resource.title,
    source: resource.source,
    suggestedSurface: resource.suggestedSurface,
    openedInSurface: Boolean(openedResource && openedResource.resourceId === resource.resourceId),
  };
}

function isOpenableWhiteboardResource(resource: SelectedAttentionResource): boolean {
  return resource.app === "whiteboard" || resource.suggestedSurface === "whiteboard" || resource.kind === "whiteboard";
}

function isOpenOnlyWhiteboardInvocation(turn: NormalizedTurn): boolean {
  const invocation = turn.surfaceInvocation;
  if (invocation?.writeBehavior !== "open_only") {
    return false;
  }
  if (invocation.primarySurface === "whiteboard") {
    return true;
  }
  return invocation.surfaces.some((surface) => surface.kind === "whiteboard");
}

function workspaceIdFromResource(resource: SelectedAttentionResource): string {
  const [, id] = resource.resourceId.split(":", 2);
  return id || resource.resourceId || resource.id;
}

function nextViewForTurn(turn: NormalizedTurn, state: AppState): ViewKind {
  if (turn.workspaceUpdate?.content) {
    return "whiteboard";
  }
  if (selectedWhiteboardResource(turn)) {
    return "whiteboard";
  }
  if (turn.surfacePayloads.length) {
    return "artifact";
  }
  if (state.visibleSurfaces.foreground === "artifact" && activeSurface(state)) {
    return "artifact";
  }
  if (state.visibleSurfaces.whiteboardVisible && state.whiteboardEditor.content.trim()) {
    return "whiteboard";
  }
  return "chat";
}

function applySurfaceAction(state: AppState, turn: NormalizedTurn): AppState {
  const action = turn.surfaceAction;
  if (!action || action.type !== "close_visible_surface" || action.status === "no_visible_surface") {
    return state;
  }
  const target = action.target || "current";
  const targetKind = action.targetKind || "";
  const targetId = action.targetId || "";
  const closeWhiteboard = (
    target === "whiteboard"
    || targetKind === "whiteboard"
    || (target === "artifact" && state.visibleSurfaces.foreground === "whiteboard")
    || (target === "current" && state.visibleSurfaces.foreground === "whiteboard")
    || (targetId && targetId === state.whiteboardEditor.id)
  );
  const closeActiveSurface = (
    target === "calendar"
    || target === "task"
    || targetKind === "today_briefing"
    || targetKind === "calendar_day"
    || targetKind === "calendar_week"
    || targetKind === "task_focus"
    || (target === "artifact" && state.visibleSurfaces.foreground === "artifact")
    || (target === "current" && state.visibleSurfaces.foreground === "artifact")
    || (targetId && targetId === state.visibleSurfaces.activeSurfaceId)
  );

  let nextState = state;
  if (closeActiveSurface) {
    nextState = {
      ...nextState,
      activeSurfaceId: null,
      visibleSurfaces: {
        ...nextState.visibleSurfaces,
        foreground: nextState.visibleSurfaces.foreground === "artifact" ? "chat" : nextState.visibleSurfaces.foreground,
        activeSurfaceId: null,
        visibleSurfaceIds: [],
      },
      latestTurn: nextState.latestTurn ? { ...nextState.latestTurn, activeSurfaceId: null } : null,
      view: nextState.view === "artifact" ? "chat" : nextState.view,
    };
  }
  if (closeWhiteboard) {
    nextState = {
      ...nextState,
      visibleSurfaces: {
        ...nextState.visibleSurfaces,
        foreground: nextState.visibleSurfaces.foreground === "whiteboard" ? "chat" : nextState.visibleSurfaces.foreground,
        whiteboardVisible: false,
      },
      view: nextState.view === "whiteboard" ? "chat" : nextState.view,
    };
  }
  return syncStateContext(nextState);
}

function mergeArtifactActions(existing: ArtifactAction[], updates: ArtifactAction[]): ArtifactAction[] {
  if (!updates.length) {
    return existing;
  }
  const byId = new Map(existing.map((action) => [action.id, action]));
  for (const action of updates) {
    byId.set(action.id, action);
  }
  return [...byId.values()];
}

export function activeSurface(state: AppState): SurfacePayload | null {
  const activeSurfaceId = state.visibleSurfaces.activeSurfaceId || state.activeSurfaceId;
  if (!activeSurfaceId) {
    return null;
  }
  return state.surfacePayloads.find((surface) => surface.id === activeSurfaceId) || null;
}

export function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "BOOTSTRAP_HEALTH":
      return {
        ...state,
        auth: {
          checking: false,
          required: Boolean(action.payload.auth_required),
          authenticated: Boolean(action.payload.authenticated),
          accountCreationEnabled: Boolean(action.payload.account_creation_enabled),
          accountCreationCodeRequired: Boolean(action.payload.account_creation_code_required),
          userId: action.payload.user?.id || "",
          modelLabel: modelLabel(action.payload),
          error: "",
        },
      };
    case "AUTH_ERROR":
      return {
        ...state,
        auth: { ...state.auth, checking: false, authenticated: false, error: action.message },
      };
    case "SET_WORKSPACE":
      return syncStateContext({
        ...state,
        whiteboardEditor: whiteboardEditorFromPayload(action.payload, state.whiteboardEditor),
      });
    case "SET_COMPOSER":
      return { ...state, composerValue: action.value };
    case "CHAT_START":
      return { ...state, busy: true, notice: null };
    case "CHAT_SUCCESS": {
      const turn = action.turn;
      const selectedResource = selectedWhiteboardResource(turn);
      const selectedResourceState = selectedResourceStateFromTurn(turn, selectedResource);
      const workspaceContent = turn.workspaceUpdate?.content || selectedResource?.content || state.whiteboardEditor.content;
      const surfacePayloads = turn.surfacePayloads.length ? turn.surfacePayloads : state.surfacePayloads;
      const requestedActiveSurfaceId = turn.activeSurfaceId || turn.surfacePayloads[0]?.id || state.visibleSurfaces.activeSurfaceId;
      const activeSurfaceId = validSurfaceId(requestedActiveSurfaceId, surfacePayloads);
      const foregroundsOperationalSurface = Boolean(turn.surfacePayloads.length && activeSurfaceId);
      const whiteboardVisible = Boolean(
        turn.workspaceUpdate?.content
        || selectedResource
        || (!foregroundsOperationalSurface && state.visibleSurfaces.whiteboardVisible),
      );
      const visibleSurfaces = {
        ...state.visibleSurfaces,
        activeSurfaceId,
        visibleSurfaceIds: activeSurfaceId ? [activeSurfaceId] : [],
        whiteboardVisible,
      };
      const whiteboardEditor = {
        ...state.whiteboardEditor,
        id: turn.workspaceUpdate?.content
          ? state.whiteboardEditor.id
          : selectedResource
            ? workspaceIdFromResource(selectedResource)
            : state.whiteboardEditor.id,
        title: turn.workspaceUpdate?.title || selectedResource?.title || state.whiteboardEditor.title,
        content: workspaceContent,
        dirty: turn.workspaceUpdate?.content ? true : selectedResource ? false : state.whiteboardEditor.dirty,
        sourceResourceId: selectedResource?.resourceId || state.whiteboardEditor.sourceResourceId,
        sourceKind: selectedResource?.kind || (turn.workspaceUpdate?.content ? "workspace_update" : state.whiteboardEditor.sourceKind),
      };
      const nextState = syncStateContext({
        ...state,
        surfacePayloads,
        activeSurfaceId,
        visibleSurfaces,
        whiteboardEditor,
        selectedResource: selectedResourceState,
      });
      const nextView = nextViewForTurn(turn, nextState);
      const updatedState = syncStateContext({
        ...nextState,
        busy: false,
        composerValue: "",
        latestTurn: turn,
        history: [
          ...state.history,
          { user_message: turn.userMessage, assistant_message: turn.assistantMessage },
        ],
        view: nextView,
        visibleSurfaces: {
          ...nextState.visibleSurfaces,
          foreground: nextView,
        },
      });
      return applySurfaceAction(updatedState, turn);
    }
    case "CHAT_ERROR":
      return {
        ...state,
        busy: false,
        notice: { id: Date.now(), title: "Chat failed", message: action.message, tone: "warning" },
      };
    case "SET_VIEW":
      return syncStateContext({
        ...state,
        returnView: action.view === "vantage" ? state.view : state.returnView,
        view: action.view,
        visibleSurfaces: {
          ...state.visibleSurfaces,
          foreground: action.view,
          whiteboardVisible: action.view === "whiteboard"
            ? Boolean(state.whiteboardEditor.content.trim())
            : state.visibleSurfaces.whiteboardVisible,
        },
        profileOpen: false,
      });
    case "SET_PROFILE_OPEN":
      return { ...state, profileOpen: action.open };
    case "SET_NOTICE":
      return {
        ...state,
        notice: {
          id: Date.now(),
          title: action.title,
          message: action.message,
          tone: action.tone || "info",
        },
      };
    case "CLEAR_NOTICE":
      return { ...state, notice: null };
    case "UPDATE_WORKSPACE_CONTENT":
      return syncStateContext({
        ...state,
        whiteboardEditor: { ...state.whiteboardEditor, content: action.content, dirty: true },
      });
    case "WORKSPACE_SAVED":
      return syncStateContext({
        ...state,
        whiteboardEditor: whiteboardEditorFromPayload(action.payload, state.whiteboardEditor),
        notice: { id: Date.now(), title: "Whiteboard saved", message: "Your draft is saved.", tone: "success" },
      });
    case "UPSERT_SURFACE": {
      const surfaces = state.surfacePayloads.filter((surface) => surface.id !== action.surface.id);
      surfaces.push(action.surface);
      return syncStateContext({
        ...state,
        surfacePayloads: surfaces,
        activeSurfaceId: action.active ? action.surface.id : state.activeSurfaceId,
        visibleSurfaces: action.active
          ? {
              ...state.visibleSurfaces,
              foreground: "artifact",
              activeSurfaceId: action.surface.id,
              visibleSurfaceIds: [action.surface.id],
              whiteboardVisible: false,
            }
          : state.visibleSurfaces,
        view: action.active ? "artifact" : state.view,
      });
    }
    case "REMOVE_ACTIVE_ARTIFACT":
      return syncStateContext({
        ...state,
        activeSurfaceId: null,
        visibleSurfaces: {
          ...state.visibleSurfaces,
          foreground: state.visibleSurfaces.foreground === "artifact" ? "chat" : state.visibleSurfaces.foreground,
          activeSurfaceId: null,
          visibleSurfaceIds: [],
        },
        latestTurn: state.latestTurn ? { ...state.latestTurn, activeSurfaceId: null } : null,
        view: state.view === "artifact" ? "chat" : state.view,
      });
    case "ARTIFACT_ACTION_RESULT": {
      const surfacePayloads = action.result.surfacePayloads.length ? action.result.surfacePayloads : state.surfacePayloads;
      const requestedActiveSurfaceId = action.result.activeSurfaceId || action.result.surfacePayloads[0]?.id || state.visibleSurfaces.activeSurfaceId;
      const activeSurfaceId = validSurfaceId(requestedActiveSurfaceId, surfacePayloads);
      const latestTurn = state.latestTurn
        ? {
            ...state.latestTurn,
            assistantMessage: action.result.assistantMessage || state.latestTurn.assistantMessage,
            artifactActions: mergeArtifactActions(state.latestTurn.artifactActions, action.result.artifactActions),
            surfacePayloads,
            activeSurfaceId,
            graphAction: action.result.graphAction || state.latestTurn.graphAction,
            surfaceInvocation: action.result.surfaceInvocation || state.latestTurn.surfaceInvocation,
            appCapabilities: action.result.appCapabilities || state.latestTurn.appCapabilities,
          }
        : state.latestTurn;
      return syncStateContext({
        ...state,
        busy: false,
        latestTurn,
        surfacePayloads,
        activeSurfaceId,
        visibleSurfaces: {
          ...state.visibleSurfaces,
          foreground: activeSurfaceId ? "artifact" : state.visibleSurfaces.foreground,
          activeSurfaceId,
          visibleSurfaceIds: activeSurfaceId ? [activeSurfaceId] : [],
          whiteboardVisible: activeSurfaceId ? false : state.visibleSurfaces.whiteboardVisible,
        },
        view: activeSurfaceId ? "artifact" : state.view,
      });
    }
    case "LOGOUT":
      return {
        ...initialState,
        auth: { ...initialState.auth, checking: false, required: true, authenticated: false },
      };
    default:
      return state;
  }
}
