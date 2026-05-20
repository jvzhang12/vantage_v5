import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { NormalizedTurn, WorkingMemoryView } from "./types";

const api = vi.hoisted(() => ({
  acceptArtifactAction: vi.fn(),
  createAccount: vi.fn(),
  getCalendarWeek: vi.fn(),
  getHealth: vi.fn(),
  getWorkspace: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  promoteWorkspace: vi.fn(),
  rejectArtifactAction: vi.fn(),
  saveWorkspace: vi.fn(),
  sendChat: vi.fn(),
}));

vi.mock("./api", () => api);

function turn(overrides: Partial<NormalizedTurn> = {}): NormalizedTurn {
  return {
    userMessage: "What should I do first from this study plan?",
    assistantMessage: "Start by reviewing the highest-weight material.",
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
    surfaceAction: null,
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
    workingMemoryView: null,
    raw: {},
    ...overrides,
  };
}

const todaySurface = {
  id: "today-2026-05-19",
  kind: "today_briefing" as const,
  title: "Today",
  summary: "1 scheduled event and one open focus block",
  sourceRefs: [],
  data: {
    date: "2026-05-19",
    calendar: {
      date: "2026-05-19",
      events: [
        {
          id: "class-1",
          title: "Data Structures",
          start: "2026-05-19T10:00:00",
          end: "2026-05-19T11:00:00",
          location: "Room 201",
        },
      ],
      free_blocks: [
        {
          start: "2026-05-19T13:00:00",
          end: "2026-05-19T14:00:00",
          duration_minutes: 60,
        },
      ],
    },
    tasks: {
      groups: {
        must_do_today: [{ id: "review", title: "Review graph traversal notes", project: "Midterm" }],
        good_next: [],
        can_defer: [],
      },
    },
    suggestions: [{ task_title: "Review graph traversal notes", reason: "Best open focus window." }],
  },
};

const taskFocusSurface = {
  id: "task-focus-2026-05-19",
  kind: "task_focus" as const,
  title: "Tasks",
  summary: "3 active tasks",
  sourceRefs: [],
  data: {
    tasks: {
      groups: {
        must_do_today: [{ id: "review", title: "Review graph traversal notes", project: "Midterm" }],
        good_next: [{ id: "practice", title: "Solve one BFS problem", project: "Midterm" }],
        can_defer: [],
        unscheduled: [{ id: "mistake-log", title: "Update mistake log", project: "Midterm" }],
      },
    },
  },
};

function workingMemoryView(overrides: Partial<WorkingMemoryView> = {}): WorkingMemoryView {
  const resourceId = "artifact:midterm-study-plan";
  return {
    schema: "working_memory_view.v1",
    turn: {
      turnId: "turn-1",
      traceId: "trace-1",
      responseMode: "grounded",
      mode: "chat",
    },
    roles: {
      answer_context: [
        {
          resourceId,
          kind: "artifact",
          title: "Midterm Study Plan",
          origins: ["attention_selection"],
          sentToResponseLlm: true,
        },
      ],
      recall_context: [],
      protocol_guidance: [],
      surface_to_open: [
        {
          resourceId,
          kind: "artifact",
          title: "Midterm Study Plan",
          origins: ["navigator_surface_open"],
          sentToResponseLlm: true,
        },
      ],
      pinned_or_continuity_context: [],
    },
    resources: [
      {
        id: resourceId,
        resourceId,
        kind: "artifact",
        type: "artifact",
        title: "Midterm Study Plan",
        label: "",
        roles: ["answer_context", "surface_to_open"],
        origins: ["attention_selection", "navigator_surface_open"],
        flags: { selected: true, visible: false, pinned: false },
        summary: "Exam preparation material about graphs and study priorities.",
        excerpt: "Practice BFS and DFS first, then review proof strategies.",
        sentToResponseLlm: true,
        provenance: {
          source: "artifact",
          sourceLabel: "Artifact",
          scope: "durable",
          durability: "durable",
          isCanonical: false,
          sourceStatus: {},
        },
        influence: {
          answerGeneration: true,
          uiSurfaceAction: true,
          writeOrProposalDecision: null,
        },
      },
    ],
    comparison: {},
    executionSummary: {
      surface: {
        mode: "open_only",
        surface: "whiteboard",
        targetResourceId: resourceId,
        targetResourceKind: "artifact",
        authority: "navigator_surface_open",
        activeSurfaceId: "",
        surfacePayloadCount: 0,
      },
      writes: {
        categories: ["open_only_no_write"],
        intendedWriteKind: "",
        effectAgreement: "",
        workspaceUpdateType: "",
        graphActionType: "",
        createdRecord: null,
        artifactActionCount: 0,
        proposalCount: 0,
      },
    },
    source: {
      attentionRecallRoleProjectionSchema: "attention_recall_role_projection.v1",
      turnPlanVersion: "turn_plan.v1",
    },
    notes: [],
    ...overrides,
  };
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getHealth.mockResolvedValue({
      authenticated: true,
      auth_required: false,
      model: "test-model",
      mode: "test",
      user: { id: "eden" },
    });
    api.getWorkspace.mockResolvedValue({
      workspace_id: "workspace-1",
      title: "Whiteboard",
      content: "",
      scope: "durable",
    });
  });

  it("shows and clears a pending assistant state while chat is generating", async () => {
    let resolveChat: (value: NormalizedTurn) => void = () => {};
    api.sendChat.mockReturnValueOnce(new Promise<NormalizedTurn>((resolve) => {
      resolveChat = resolve;
    }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "What does my day look like?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByLabelText("Pending Vantage answer")).toBeTruthy();
    expect(screen.getByText("Vantage is thinking...")).toBeTruthy();
    expect((screen.getByLabelText("Working") as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      resolveChat(turn({
        userMessage: "What does my day look like?",
        assistantMessage: "You have one class and one open focus block.",
      }));
    });

    await waitFor(() => {
      expect(screen.queryByLabelText("Pending Vantage answer")).toBeNull();
      expect(screen.getByText("You have one class and one open focus block.")).toBeTruthy();
    });
    expect((screen.getByLabelText("Send") as HTMLButtonElement).disabled).toBe(true);
  });

  it("clears the pending assistant state and shows the existing error UI when chat fails", async () => {
    let rejectChat: (error: Error) => void = () => {};
    api.sendChat.mockReturnValueOnce(new Promise<NormalizedTurn>((_resolve, reject) => {
      rejectChat = reject;
    }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Summarize this" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("Vantage is thinking...")).toBeTruthy();

    await act(async () => {
      rejectChat(new Error("Network went away"));
    });

    await waitFor(() => {
      expect(screen.queryByLabelText("Pending Vantage answer")).toBeNull();
      expect(screen.getByText("Chat failed")).toBeTruthy();
      expect(screen.getByText("Network went away")).toBeTruthy();
    });
  });

  it("shows the latest Working Memory view inside Vantage", async () => {
    api.sendChat.mockResolvedValueOnce(turn({
      userMessage: "Open Midterm Study Plan",
      assistantMessage: "Opened Midterm Study Plan.",
      workingMemoryView: workingMemoryView(),
    }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Open Midterm Study Plan" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("Opened Midterm Study Plan.")).toBeTruthy();
    fireEvent.click(screen.getByTitle("Open Vantage"));

    expect(await screen.findByText("What Vantage used for the latest response: bounded context, provenance, surface actions, and write summaries.")).toBeTruthy();
    expect(screen.getByText("Answer Context")).toBeTruthy();
    expect(screen.getByText("Recall Context")).toBeTruthy();
    expect(screen.getByText("Protocol Guidance")).toBeTruthy();
    expect(screen.getByText("Surface To Open")).toBeTruthy();
    expect(screen.getByText("Pinned / Continuity Context")).toBeTruthy();
    expect(screen.getAllByText("Midterm Study Plan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Practice BFS and DFS first, then review proof strategies.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Artifact · Artifact").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Selected").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sent to LLM").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Surface action").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Open-only Whiteboard").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Open Only No Write").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Turn input received").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Raw prompt text is not shown in Working Memory/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Open Midterm Study Plan")).toBeNull();
    expect(screen.getAllByText("No resources in this role.").length).toBeGreaterThan(0);
    expect(screen.getByText("This is grounding evidence and execution context, not hidden chain-of-thought.")).toBeTruthy();
  });

  it("opens Vantage without crashing when a turn has no Working Memory payload", async () => {
    api.sendChat.mockResolvedValueOnce(turn({
      userMessage: "Say hi",
      assistantMessage: "Hi.",
    }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Say hi" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("Hi.")).toBeTruthy();
    fireEvent.click(screen.getByTitle("Open Vantage"));

    expect(await screen.findByText("No Working Memory payload for this turn.")).toBeTruthy();
    expect(screen.getByText("Context Used")).toBeTruthy();
  });

  it("keeps the assistant answer visible when a normal turn follows an open whiteboard", async () => {
    const selectedArtifact = {
      id: "selected-artifact-midterm-study-plan",
      resourceId: "artifact:midterm-study-plan",
      kind: "artifact",
      app: "whiteboard",
      title: "Midterm Study Plan",
      summary: "Exam preparation material about graphs and study priorities.",
      source: "artifact",
      content: "# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
      data: {},
      timestamps: {},
      suggestedSurface: "whiteboard",
      whySelected: "The user asked for the study plan.",
    };
    api.sendChat
      .mockResolvedValueOnce(turn({
        userMessage: "Open Midterm Study Plan",
        assistantMessage: "Opened Midterm Study Plan.",
        selectedAttentionResources: [selectedArtifact],
        navigatorSelection: {
          selectedIds: [selectedArtifact.resourceId],
          primaryResourceId: selectedArtifact.resourceId,
          supportingResourceIds: [],
          rejectedCandidateIds: [],
          surfaceToOpen: "whiteboard",
          reason: "Open the matching saved artifact in the whiteboard.",
          confidence: 0.9,
          fallback: false,
        },
      }))
      .mockResolvedValueOnce(turn({
        userMessage: "What should I do first from this study plan?",
        assistantMessage: "Start with graph traversals, then spend the next block on proof review.",
      }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Open Midterm Study Plan" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    const whiteboard = await screen.findByLabelText("Whiteboard content");
    expect((whiteboard as HTMLTextAreaElement).value).toContain("Prioritize graph traversals");

    fireEvent.change(composer, { target: { value: "What should I do first from this study plan?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(screen.getByText("Start with graph traversals, then spend the next block on proof review.")).toBeTruthy();
    });
    expect(screen.getByLabelText("Latest Vantage answer")).toBeTruthy();
    expect((screen.getByLabelText("Whiteboard content") as HTMLTextAreaElement).value).toContain("Prioritize graph traversals");
  });

  it("keeps the assistant answer and pending state visible while an artifact surface stays open", async () => {
    let resolveFollowUp: (value: NormalizedTurn) => void = () => {};
    api.sendChat
      .mockResolvedValueOnce(turn({
        userMessage: "What does my day look like?",
        assistantMessage: "You have one class and one open focus block.",
        surfacePayloads: [todaySurface],
        activeSurfaceId: todaySurface.id,
      }))
      .mockReturnValueOnce(new Promise<NormalizedTurn>((resolve) => {
        resolveFollowUp = resolve;
      }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "What does my day look like?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("You have one class and one open focus block.")).toBeTruthy();
    expect(screen.getByText("Data Structures")).toBeTruthy();

    fireEvent.change(composer, { target: { value: "What should I do first?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("Vantage is thinking...")).toBeTruthy();
    expect(screen.getByText("Data Structures")).toBeTruthy();

    await act(async () => {
      resolveFollowUp(turn({
        userMessage: "What should I do first?",
        assistantMessage: "Use the open focus block for graph traversal review.",
        visibleArtifacts: [{ id: todaySurface.id, kind: todaySurface.kind }],
      }));
    });

    await waitFor(() => {
      expect(screen.queryByLabelText("Pending Vantage answer")).toBeNull();
      expect(screen.getByText("Use the open focus block for graph traversal review.")).toBeTruthy();
    });
    expect(screen.getByText("Data Structures")).toBeTruthy();
  });

  it("keeps the assistant answer and pending state visible while Task Focus stays open", async () => {
    let resolveFollowUp: (value: NormalizedTurn) => void = () => {};
    api.sendChat
      .mockResolvedValueOnce(turn({
        userMessage: "Show my task focus",
        assistantMessage: "Start with graph traversal review, then solve one BFS problem.",
        surfacePayloads: [taskFocusSurface],
        activeSurfaceId: taskFocusSurface.id,
      }))
      .mockReturnValueOnce(new Promise<NormalizedTurn>((resolve) => {
        resolveFollowUp = resolve;
      }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Show my task focus" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByText("Start with graph traversal review, then solve one BFS problem.")).toBeTruthy();
    expect(screen.getByText("Solve one BFS problem")).toBeTruthy();
    expect(screen.getByLabelText("Ask Vantage")).toBeTruthy();

    fireEvent.change(composer, { target: { value: "What should I do first?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByLabelText("Pending Vantage answer")).toBeTruthy();
    expect(screen.getByText("Vantage is thinking...")).toBeTruthy();
    expect(screen.getByText("Solve one BFS problem")).toBeTruthy();
    expect((screen.getByLabelText("Working") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getAllByLabelText("Pending Vantage answer")).toHaveLength(1);

    await act(async () => {
      resolveFollowUp(turn({
        userMessage: "What should I do first?",
        assistantMessage: "Use the open block for graph traversal review.",
        visibleArtifacts: [{ id: taskFocusSurface.id, kind: taskFocusSurface.kind }],
      }));
    });

    await waitFor(() => {
      expect(screen.queryByLabelText("Pending Vantage answer")).toBeNull();
      expect(screen.getByText("Use the open block for graph traversal review.")).toBeTruthy();
    });
    expect(screen.getByText("Solve one BFS problem")).toBeTruthy();
    expect(screen.getByLabelText("Ask Vantage")).toBeTruthy();
  });

  it("stops sending visible whiteboard context after a backend close action hides it", async () => {
    const selectedArtifact = {
      id: "selected-artifact-midterm-study-plan",
      resourceId: "artifact:midterm-study-plan",
      kind: "artifact",
      app: "whiteboard",
      title: "Midterm Study Plan",
      summary: "Exam preparation material about graphs and study priorities.",
      source: "artifact",
      content: "# Midterm Study Plan\n\nPrioritize graph traversals and proof review.",
      data: {},
      timestamps: {},
      suggestedSurface: "whiteboard",
      whySelected: "The user asked for the study plan.",
    };
    api.sendChat
      .mockResolvedValueOnce(turn({
        userMessage: "Open Midterm Study Plan",
        assistantMessage: "Opened Midterm Study Plan.",
        selectedAttentionResources: [selectedArtifact],
        navigatorSelection: {
          selectedIds: [selectedArtifact.resourceId],
          primaryResourceId: selectedArtifact.resourceId,
          supportingResourceIds: [],
          rejectedCandidateIds: [],
          surfaceToOpen: "whiteboard",
          reason: "Open the matching saved artifact in the whiteboard.",
          confidence: 0.9,
          fallback: false,
        },
      }))
      .mockResolvedValueOnce(turn({
        userMessage: "close the whiteboard",
        assistantMessage: "Closed Midterm Study Plan from view.",
        surfaceAction: {
          type: "close_visible_surface",
          status: "requested",
          target: "whiteboard",
          targetId: "midterm-study-plan",
          targetKind: "whiteboard",
          title: "Midterm Study Plan",
          reason: "The user asked to close the visible whiteboard.",
        },
      }))
      .mockResolvedValueOnce(turn({
        userMessage: "What now?",
        assistantMessage: "We can continue in chat.",
      }));

    render(<App />);

    const composer = await screen.findByLabelText("Ask Vantage");
    fireEvent.change(composer, { target: { value: "Open Midterm Study Plan" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    expect(await screen.findByLabelText("Whiteboard content")).toBeTruthy();

    fireEvent.change(composer, { target: { value: "close the whiteboard" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(screen.queryByLabelText("Whiteboard content")).toBeNull();
      expect(screen.getByText("Closed Midterm Study Plan from view.")).toBeTruthy();
    });

    fireEvent.change(composer, { target: { value: "What now?" } });
    fireEvent.submit(composer.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(api.sendChat).toHaveBeenCalledTimes(3);
    });
    expect(api.sendChat.mock.calls[2][0].workspaceScope).toBe("excluded");
    expect(api.sendChat.mock.calls[2][0].visibleArtifacts).toEqual([]);
  });
});
