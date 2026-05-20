import { describe, expect, it } from "vitest";
import { buildVisibleArtifacts, surfaceToMarkdown } from "./visibleArtifacts";
import type { SurfacePayload, WorkspaceState } from "./types";

const calendarWeekSurface: SurfacePayload = {
  id: "calendar-week-2026-05-11",
  kind: "calendar_week",
  title: "Week",
  summary: "1 scheduled event this week",
  sourceRefs: [],
  data: {
    date: "2026-05-13",
    calendar_week: {
      start_date: "2026-05-11",
      end_date: "2026-05-17",
      days: [
        {
          date: "2026-05-13",
          events: [
            {
              id: "algorithms-lab",
              title: "Algorithms lab",
              start: "2026-05-13T10:00:00",
              end: "2026-05-13T11:00:00",
              location: "Room 204",
            },
          ],
        },
      ],
    },
  },
};

const workspace: WorkspaceState = {
  id: "v5-milestone-1",
  title: "Whiteboard",
  content: "# Draft\n\nVisible whiteboard text.",
  scope: "durable",
  dirty: false,
  pinnedToChat: false,
};

describe("visible artifact context", () => {
  it("renders the current calendar week into markdown for the next model call", () => {
    const markdown = surfaceToMarkdown(calendarWeekSurface);

    expect(markdown).toContain("# Week");
    expect(markdown).toContain("Algorithms lab");
    expect(markdown).toContain("2026-05-11");
  });

  it("includes the active surface only when the artifact is in view", () => {
    const artifacts = buildVisibleArtifacts({
      activeSurface: calendarWeekSurface,
      workspace,
      view: "artifact",
      visibleSurfaces: {
        foreground: "artifact",
        activeSurfaceId: calendarWeekSurface.id,
        visibleSurfaceIds: [calendarWeekSurface.id],
        whiteboardVisible: false,
      },
    });

    expect(artifacts).toHaveLength(1);
    expect(String(artifacts[0].content)).toContain("Algorithms lab");
  });

  it("does not include cached surfaces after the artifact view is removed", () => {
    const artifacts = buildVisibleArtifacts({
      activeSurface: calendarWeekSurface,
      workspace,
      view: "chat",
      visibleSurfaces: {
        foreground: "chat",
        activeSurfaceId: null,
        visibleSurfaceIds: [],
        whiteboardVisible: false,
      },
    });

    expect(artifacts).toHaveLength(0);
  });

  it("includes visible whiteboard content when visible surface state says it is open", () => {
    const artifacts = buildVisibleArtifacts({
      activeSurface: null,
      workspace,
      view: "chat",
      visibleSurfaces: {
        foreground: "chat",
        activeSurfaceId: null,
        visibleSurfaceIds: [],
        whiteboardVisible: true,
      },
    });

    expect(artifacts).toHaveLength(1);
    expect(String(artifacts[0].content)).toContain("Visible whiteboard text.");
  });
});
