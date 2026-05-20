import { surfaceToMarkdown } from "./capabilities";
import type { SurfacePayload, VisibleSurfacesState, WorkspaceState } from "./types";

export { surfaceToMarkdown };

export function buildVisibleArtifacts(params: {
  activeSurface?: SurfacePayload | null;
  workspace: WorkspaceState;
  view: string;
  visibleSurfaces?: VisibleSurfacesState;
}): Record<string, unknown>[] {
  const artifacts: Record<string, unknown>[] = [];
  const activeSurfaceVisible = params.visibleSurfaces
    ? Boolean(params.activeSurface && params.visibleSurfaces.activeSurfaceId === params.activeSurface.id)
    : params.view === "artifact";
  const whiteboardVisible = params.visibleSurfaces
    ? params.visibleSurfaces.whiteboardVisible
    : params.view === "whiteboard";
  if (activeSurfaceVisible && params.activeSurface) {
    artifacts.push({
      id: params.activeSurface.id,
      kind: params.activeSurface.kind,
      title: params.activeSurface.title,
      summary: params.activeSurface.summary,
      content: surfaceToMarkdown(params.activeSurface),
      data: params.activeSurface.data,
    });
  }
  if (whiteboardVisible && params.workspace.content.trim()) {
    artifacts.push({
      id: params.workspace.id || "whiteboard",
      kind: "whiteboard",
      title: params.workspace.title || "Whiteboard",
      summary: "Visible whiteboard content in the user's current view.",
      content: params.workspace.content,
      data: {
        workspace_id: params.workspace.id,
        scope: params.workspace.scope,
      },
    });
  }
  return artifacts;
}
