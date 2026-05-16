import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
});
