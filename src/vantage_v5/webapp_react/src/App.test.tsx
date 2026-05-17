import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { NormalizedTurn } from "./types";

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
    raw: {},
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
    expect((screen.getByLabelText("Whiteboard content") as HTMLTextAreaElement).value).toContain("Prioritize graph traversals");
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
