import { normalizeAppCapabilityManifest, normalizeArtifactActions, normalizeSurfaceInvocation, normalizeSurfacePayloads, normalizeTurnPayload, text, asRecord } from "./normalizers";
import type { AppCapabilityManifest, ArtifactAction, ChatHistoryItem, HealthPayload, NormalizedTurn, SurfaceInvocation, SurfacePayload, WorkspacePayload } from "./types";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : `Request failed with status ${response.status}`;
    throw new ApiError(detail, response.status, payload);
  }
  return payload as T;
}

export function getHealth(): Promise<HealthPayload> {
  return requestJson<HealthPayload>("/api/health");
}

export function login(username: string, password: string): Promise<HealthPayload> {
  return requestJson<HealthPayload>("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function createAccount(username: string, password: string, accessCode = ""): Promise<HealthPayload> {
  return requestJson<HealthPayload>("/api/accounts", {
    method: "POST",
    body: JSON.stringify({ username, password, access_code: accessCode || null }),
  });
}

export function logout(): Promise<{ authenticated: boolean }> {
  return requestJson<{ authenticated: boolean }>("/api/logout", { method: "POST" });
}

export function getWorkspace(): Promise<WorkspacePayload> {
  return requestJson<WorkspacePayload>("/api/workspace");
}

export function saveWorkspace(content: string, workspaceId?: string): Promise<WorkspacePayload> {
  return requestJson<WorkspacePayload>("/api/workspace", {
    method: "POST",
    body: JSON.stringify({ content, workspace_id: workspaceId || null }),
  });
}

export function promoteWorkspace(params: { workspaceId?: string; title?: string; content: string }): Promise<unknown> {
  return requestJson<unknown>("/api/concepts/promote", {
    method: "POST",
    body: JSON.stringify({
      workspace_id: params.workspaceId || null,
      title: params.title || null,
      content: params.content,
    }),
  });
}

export function getCalendarWeek(date: string): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(`/api/calendar/week?date=${encodeURIComponent(date)}`);
}

export interface ArtifactActionResult {
  artifactActions: ArtifactAction[];
  surfacePayloads: SurfacePayload[];
  activeSurfaceId: string | null;
  assistantMessage: string;
  graphAction: Record<string, unknown> | null;
  surfaceInvocation: SurfaceInvocation | null;
  appCapabilities: AppCapabilityManifest | null;
}

function normalizeArtifactActionResult(payload: unknown): ArtifactActionResult {
  const record = asRecord(payload);
  return {
    artifactActions: normalizeArtifactActions(record.artifact_actions || record.artifactActions || (record.artifact_action ? [record.artifact_action] : [])),
    surfacePayloads: normalizeSurfacePayloads(record.surface_payloads || record.surfacePayloads),
    activeSurfaceId: text(record.active_surface_id || record.activeSurfaceId) || null,
    assistantMessage: text(record.assistant_message || record.assistantMessage),
    graphAction: Object.keys(asRecord(record.graph_action || record.graphAction)).length ? asRecord(record.graph_action || record.graphAction) : null,
    surfaceInvocation: normalizeSurfaceInvocation(record.surface_invocation || record.surfaceInvocation),
    appCapabilities: normalizeAppCapabilityManifest(record.app_capabilities || record.appCapabilities),
  };
}

export function acceptArtifactAction(actionId: string): Promise<ArtifactActionResult> {
  return requestJson<Record<string, unknown>>(`/api/artifact-actions/${encodeURIComponent(actionId)}/accept`, {
    method: "POST",
  }).then(normalizeArtifactActionResult);
}

export function rejectArtifactAction(actionId: string): Promise<ArtifactActionResult> {
  return requestJson<Record<string, unknown>>(`/api/artifact-actions/${encodeURIComponent(actionId)}/reject`, {
    method: "POST",
  }).then(normalizeArtifactActionResult);
}

export function sendChat(params: {
  message: string;
  history: ChatHistoryItem[];
  workspaceId?: string;
  workspaceScope: string;
  workspaceContent?: string | null;
  visibleArtifacts: Record<string, unknown>[];
}): Promise<NormalizedTurn> {
  return requestJson<Record<string, unknown>>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      history: params.history,
      workspace_id: params.workspaceId || null,
      workspace_scope: params.workspaceScope,
      workspace_content: params.workspaceContent ?? null,
      whiteboard_mode: "auto",
      visible_artifacts: params.visibleArtifacts,
    }),
  }).then(normalizeTurnPayload);
}
