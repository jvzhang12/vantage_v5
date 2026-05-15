import type {
  AppState,
  ArtifactAction,
  HealthPayload,
  NormalizedTurn,
  SelectedAttentionResource,
  SurfaceInvocation,
  SurfacePayload,
  ViewKind,
  WorkspacePayload,
} from "./types";

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
  workspace: {
    id: "",
    title: "Whiteboard",
    content: "",
    scope: "durable",
    dirty: false,
    pinnedToChat: false,
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

function workspaceFromPayload(payload: WorkspacePayload, current = initialState.workspace) {
  return {
    ...current,
    id: payload.workspace_id || payload.id || current.id,
    title: payload.title || current.title || "Whiteboard",
    content: typeof payload.content === "string" ? payload.content : current.content,
    scope: payload.scope || current.scope,
    dirty: false,
  };
}

function validSurfaceId(surfaceId: string | null, surfaces: SurfacePayload[]): string | null {
  if (!surfaceId) {
    return null;
  }
  return surfaces.some((surface) => surface.id === surfaceId) ? surfaceId : null;
}

function selectedWhiteboardResource(turn: NormalizedTurn): SelectedAttentionResource | null {
  if (turn.navigatorSelection?.surfaceToOpen !== "whiteboard") {
    return null;
  }
  const primaryResourceId = turn.navigatorSelection.primaryResourceId;
  const primaryResource = turn.selectedAttentionResources.find((resource) => (
    Boolean(primaryResourceId) && resource.resourceId === primaryResourceId
  ));
  const selectedResource = primaryResource || turn.selectedAttentionResources[0] || null;
  if (!selectedResource?.content.trim()) {
    return null;
  }
  if (selectedResource.app !== "whiteboard" && selectedResource.suggestedSurface !== "whiteboard") {
    return null;
  }
  return selectedResource;
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
  if (state.view === "artifact" && activeSurface(state)) {
    return "artifact";
  }
  if (state.view === "whiteboard" && state.workspace.content.trim()) {
    return "whiteboard";
  }
  return "chat";
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
  if (!state.activeSurfaceId) {
    return null;
  }
  return state.surfacePayloads.find((surface) => surface.id === state.activeSurfaceId) || null;
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
      return { ...state, workspace: workspaceFromPayload(action.payload, state.workspace) };
    case "SET_COMPOSER":
      return { ...state, composerValue: action.value };
    case "CHAT_START":
      return { ...state, busy: true, notice: null };
    case "CHAT_SUCCESS": {
      const turn = action.turn;
      const selectedResource = selectedWhiteboardResource(turn);
      const workspaceContent = turn.workspaceUpdate?.content || selectedResource?.content || state.workspace.content;
      const surfacePayloads = turn.surfacePayloads.length ? turn.surfacePayloads : state.surfacePayloads;
      const requestedActiveSurfaceId = turn.activeSurfaceId || turn.surfacePayloads[0]?.id || state.activeSurfaceId;
      const activeSurfaceId = validSurfaceId(requestedActiveSurfaceId, surfacePayloads);
      const nextState = {
        ...state,
        surfacePayloads,
        activeSurfaceId,
        workspace: {
          ...state.workspace,
          id: turn.workspaceUpdate?.content
            ? state.workspace.id
            : selectedResource
              ? workspaceIdFromResource(selectedResource)
              : state.workspace.id,
          title: turn.workspaceUpdate?.title || selectedResource?.title || state.workspace.title,
          content: workspaceContent,
          dirty: turn.workspaceUpdate?.content ? true : selectedResource ? false : state.workspace.dirty,
        },
      };
      return {
        ...nextState,
        busy: false,
        composerValue: "",
        latestTurn: turn,
        history: [
          ...state.history,
          { user_message: turn.userMessage, assistant_message: turn.assistantMessage },
        ],
        view: nextViewForTurn(turn, nextState),
      };
    }
    case "CHAT_ERROR":
      return {
        ...state,
        busy: false,
        notice: { id: Date.now(), title: "Chat failed", message: action.message, tone: "warning" },
      };
    case "SET_VIEW":
      return {
        ...state,
        returnView: action.view === "vantage" ? state.view : state.returnView,
        view: action.view,
        profileOpen: false,
      };
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
      return { ...state, workspace: { ...state.workspace, content: action.content, dirty: true } };
    case "WORKSPACE_SAVED":
      return {
        ...state,
        workspace: workspaceFromPayload(action.payload, state.workspace),
        notice: { id: Date.now(), title: "Whiteboard saved", message: "Your draft is saved.", tone: "success" },
      };
    case "UPSERT_SURFACE": {
      const surfaces = state.surfacePayloads.filter((surface) => surface.id !== action.surface.id);
      surfaces.push(action.surface);
      return {
        ...state,
        surfacePayloads: surfaces,
        activeSurfaceId: action.active ? action.surface.id : state.activeSurfaceId,
        view: action.active ? "artifact" : state.view,
      };
    }
    case "REMOVE_ACTIVE_ARTIFACT":
      return {
        ...state,
        activeSurfaceId: null,
        latestTurn: state.latestTurn ? { ...state.latestTurn, activeSurfaceId: null } : null,
        view: state.view === "artifact" ? "chat" : state.view,
      };
    case "ARTIFACT_ACTION_RESULT": {
      const surfacePayloads = action.result.surfacePayloads.length ? action.result.surfacePayloads : state.surfacePayloads;
      const requestedActiveSurfaceId = action.result.activeSurfaceId || action.result.surfacePayloads[0]?.id || state.activeSurfaceId;
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
      return {
        ...state,
        busy: false,
        latestTurn,
        surfacePayloads,
        activeSurfaceId,
        view: activeSurfaceId ? "artifact" : state.view,
      };
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
