import { describe, expect, it } from "vitest";
import { activeSurface, appReducer, initialState } from "./appReducer";
import type { NormalizedTurn } from "./types";

function turn(overrides: Partial<NormalizedTurn> = {}): NormalizedTurn {
  return {
    userMessage: "What does my day look like?",
    assistantMessage: "You have one class and one open focus block.",
    mode: "chat",
    timestamp: "",
    answerBasis: {
      kind: "intuitive",
      label: "Intuitive Answer",
      summary: "",
      hasFactualGrounding: false,
      sources: [],
      counts: {},
    },
    responseMode: {
      kind: "best_guess",
      label: "Intuitive Answer",
      groundingMode: "ungrounded",
      contextSources: [],
      recallCount: 0,
      note: "",
    },
    recallItems: [],
    learnedItems: [],
    memoryTraceRecord: null,
    surfaceInvocation: null,
    surfacePayloads: [],
    activeSurfaceId: null,
    artifactActions: [],
    appCapabilities: null,
    workspaceUpdate: null,
    contextBudget: null,
    activity: null,
    turnInterpretation: null,
    semanticFrame: null,
    semanticPolicy: null,
    visibleArtifacts: [],
    metaAction: null,
    graphAction: null,
    createdRecord: null,
    stageProgress: [],
    queryFrame: null,
    attentionCandidates: [],
    navigatorSelection: null,
    selectedAttentionResources: [],
    raw: {},
    ...overrides,
  };
}

describe("appReducer", () => {
  it("stores backend history without rendering a user-prompt transcript model", () => {
    const state = appReducer(initialState, { type: "CHAT_SUCCESS", turn: turn() });

    expect(state.latestTurn?.assistantMessage).toBe("You have one class and one open focus block.");
    expect(state.history).toEqual([
      {
        user_message: "What does my day look like?",
        assistant_message: "You have one class and one open focus block.",
      },
    ]);
    expect(state.view).toBe("chat");
  });

  it("activates returned artifact surfaces", () => {
    const surface = {
      id: "calendar-week-2026-05-11",
      kind: "calendar_week" as const,
      title: "Week",
      summary: "1 scheduled event this week",
      sourceRefs: [],
      data: { calendar_week: { start_date: "2026-05-11", days: [] } },
    };
    const state = appReducer(initialState, {
      type: "CHAT_SUCCESS",
      turn: turn({ surfacePayloads: [surface], activeSurfaceId: surface.id }),
    });

    expect(state.view).toBe("artifact");
    expect(activeSurface(state)?.id).toBe(surface.id);
  });

  it("keeps the active artifact visible across follow-up turns without new surfaces", () => {
    const surface = {
      id: "calendar-week-2026-05-11",
      kind: "calendar_week" as const,
      title: "Week",
      summary: "1 scheduled event this week",
      sourceRefs: [],
      data: { calendar_week: { start_date: "2026-05-11", days: [] } },
    };
    const artifactState = appReducer(initialState, {
      type: "CHAT_SUCCESS",
      turn: turn({ surfacePayloads: [surface], activeSurfaceId: surface.id }),
    });
    const followUpState = appReducer(artifactState, {
      type: "CHAT_SUCCESS",
      turn: turn({
        userMessage: "What should I do next?",
        assistantMessage: "Use the open block for review.",
        surfacePayloads: [],
        activeSurfaceId: null,
        visibleArtifacts: [{ id: surface.id, kind: surface.kind }],
      }),
    });

    expect(followUpState.view).toBe("artifact");
    expect(activeSurface(followUpState)?.id).toBe(surface.id);
    expect(followUpState.latestTurn?.assistantMessage).toBe("Use the open block for review.");
  });

  it("foregrounds a newly returned artifact over the previous active surface", () => {
    const calendarSurface = {
      id: "calendar-week-2026-05-11",
      kind: "calendar_week" as const,
      title: "Week",
      summary: "1 scheduled event this week",
      sourceRefs: [],
      data: { calendar_week: { start_date: "2026-05-11", days: [] } },
    };
    const taskSurface = {
      id: "task-focus-2026-05-14",
      kind: "task_focus" as const,
      title: "Tasks",
      summary: "3 active tasks",
      sourceRefs: [],
      data: { tasks: { groups: {} } },
    };
    const artifactState = appReducer(initialState, {
      type: "CHAT_SUCCESS",
      turn: turn({ surfacePayloads: [calendarSurface], activeSurfaceId: calendarSurface.id }),
    });
    const updated = appReducer(artifactState, {
      type: "CHAT_SUCCESS",
      turn: turn({ surfacePayloads: [taskSurface], activeSurfaceId: taskSurface.id }),
    });

    expect(updated.view).toBe("artifact");
    expect(activeSurface(updated)?.id).toBe(taskSurface.id);
  });

  it("removes the active artifact without treating cached surfaces as visible", () => {
    const surface = {
      id: "calendar-week-2026-05-11",
      kind: "calendar_week" as const,
      title: "Week",
      summary: "1 scheduled event this week",
      sourceRefs: [],
      data: { calendar_week: { start_date: "2026-05-11", days: [] } },
    };
    const artifactState = appReducer(initialState, {
      type: "CHAT_SUCCESS",
      turn: turn({ surfacePayloads: [surface], activeSurfaceId: surface.id }),
    });
    const removed = appReducer(artifactState, { type: "REMOVE_ACTIVE_ARTIFACT" });

    expect(removed.view).toBe("chat");
    expect(removed.activeSurfaceId).toBeNull();
    expect(activeSurface(removed)).toBeNull();
    expect(removed.surfacePayloads).toHaveLength(1);
  });

  it("merges artifact action results and refreshed surfaces", () => {
    const proposedAction = {
      id: "artifact-action-1",
      artifactKind: "calendar",
      operation: "replace_event",
      status: "proposed",
      summary: "Replace Advisor check-in with Grocery shopping.",
      targetRefs: [],
      payload: {},
      preview: {},
      warnings: [],
      requiresConfirmation: true,
      sourceRefs: [],
      capture: null,
    };
    const acceptedAction = { ...proposedAction, status: "accepted", summary: "Updated calendar event 'Advisor check-in'." };
    const surface = {
      id: "today-2026-05-14",
      kind: "today_briefing" as const,
      title: "Today",
      summary: "1 scheduled event",
      sourceRefs: [],
      data: { calendar: { events: [{ title: "Grocery shopping" }] } },
    };
    const busyState = appReducer(initialState, { type: "CHAT_START" });
    const state = appReducer(busyState, {
      type: "CHAT_SUCCESS",
      turn: turn({ artifactActions: [proposedAction] }),
    });
    const applyingState = appReducer(state, { type: "CHAT_START" });
    const updated = appReducer(state, {
      type: "ARTIFACT_ACTION_RESULT",
      result: {
        artifactActions: [acceptedAction],
        surfacePayloads: [surface],
        activeSurfaceId: surface.id,
        assistantMessage: "Done. Updated calendar event.",
        graphAction: { type: "calendar_replace_event", status: "accepted" },
        surfaceInvocation: null,
        appCapabilities: null,
      },
    });
    const updatedFromBusy = appReducer(applyingState, {
      type: "ARTIFACT_ACTION_RESULT",
      result: {
        artifactActions: [acceptedAction],
        surfacePayloads: [surface],
        activeSurfaceId: surface.id,
        assistantMessage: "Done. Updated calendar event.",
        graphAction: { type: "calendar_replace_event", status: "accepted" },
        surfaceInvocation: null,
        appCapabilities: null,
      },
    });

    expect(updated.latestTurn?.artifactActions[0].status).toBe("accepted");
    expect(updated.latestTurn?.assistantMessage).toBe("Done. Updated calendar event.");
    expect(activeSurface(updated)?.id).toBe(surface.id);
    expect(updated.view).toBe("artifact");
    expect(updatedFromBusy.busy).toBe(false);
  });
});
