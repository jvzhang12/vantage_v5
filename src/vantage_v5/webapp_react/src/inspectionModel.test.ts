import { describe, expect, it } from "vitest";
import { buildInspectionReceipt } from "./inspectionModel";
import type { NormalizedTurn, SurfacePayload } from "./types";

const todaySurface: SurfacePayload = {
  id: "today-2026-05-14",
  kind: "today_briefing",
  title: "Today",
  summary: "2 scheduled events, 1 focus block, 4h open.",
  sourceRefs: [],
  data: {
    date: "2026-05-14",
    calendar: { summary: { event_count: 2, free_minutes: 240 }, events: [] },
    tasks: {
      summary: { total_count: 3 },
      groups: { must_do_today: [{ id: "hw-2", title: "Homework 2" }], good_next: [], can_defer: [], unscheduled: [] },
    },
  },
};

function turn(overrides: Partial<NormalizedTurn> = {}): NormalizedTurn {
  return {
    userMessage: "What does my day look like?",
    assistantMessage: "You have two events and a good focus window.",
    mode: "chat",
    timestamp: "2026-05-14T16:41:00Z",
    answerBasis: {
      kind: "grounded",
      label: "Grounded Answer",
      summary: "Calendar and task context shaped the answer.",
      hasFactualGrounding: true,
      sources: ["calendar", "tasks"],
      counts: {},
    },
    responseMode: {
      kind: "grounded",
      label: "Recall",
      groundingMode: "surface",
      contextSources: ["calendar", "tasks"],
      recallCount: 0,
      note: "",
    },
    recallItems: [],
    learnedItems: [],
    memoryTraceRecord: null,
    surfaceInvocation: {
      intent: "schedule_lookup",
      primarySurface: "calendar_day",
      supportingSurfaces: ["task_focus"],
      surfaces: [
        {
          kind: "calendar_day",
          role: "primary",
          reason: "The user asked what the day looks like.",
          status: "summoned",
        },
        {
          kind: "task_focus",
          role: "supporting",
          reason: "Tasks help prioritize open blocks.",
          status: "summoned",
        },
      ],
      writeBehavior: "read_only",
      reason: "The user asked about calendar, agenda, availability, or what is planned for a day.",
      confidence: 0.88,
      dataSources: [],
      capabilityRefs: [],
      trigger: "deterministic_policy",
      policyVersion: "surface-invocation-v1",
    },
    surfaceAction: null,
    surfacePayloads: [todaySurface],
    activeSurfaceId: todaySurface.id,
    artifactActions: [],
    appCapabilities: null,
    workspaceUpdate: null,
    contextBudget: {
      label: "Context Budget",
      summary: "Context budget: user request, recall.",
      contextSources: ["calendar", "tasks"],
      counts: { recall: 1 },
      rows: [
        { key: "user_request", label: "User request", status: "included", displayStatus: "Included", detail: "Always included.", count: 1, scope: "" },
        { key: "recall", label: "Recall", status: "included", displayStatus: "Included", detail: "1 item entered Recall.", count: 1, scope: "" },
        { key: "protocol", label: "Protocols", status: "excluded", displayStatus: "Excluded", detail: "No protocols.", count: 0, scope: "" },
      ],
    },
    activity: {
      mode: "chat",
      kind: "chat",
      status: "completed",
      summary: "Response ready.",
      steps: [],
      recallCount: 1,
      learnedCount: 0,
      createdRecordId: "",
      graphActionType: "",
      workspaceUpdateStatus: "",
    },
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

describe("inspection model", () => {
  it("maps latest-turn provenance into the Why this answer receipt", () => {
    const receipt = buildInspectionReceipt(turn(), todaySurface);

    expect(receipt?.summaryColumns.map((column) => column.label)).toEqual([
      "Input",
      "Intent",
      "Grounding",
      "Mode",
      "Summary",
    ]);
    expect(receipt?.summaryColumns[0].value).toBe("Turn input received");
    expect(receipt?.summaryColumns[0].detail).toContain("Raw prompt text is not shown");
    expect(receipt?.contextItems.some((item) => item.type === "Calendar")).toBe(true);
    expect(receipt?.contextItems.some((item) => item.type === "Tasks")).toBe(true);
    expect(receipt?.contextItems.some((item) => item.title === "Protocols")).toBe(false);
    expect(receipt?.surfaceDecisions.some((decision) => decision.name === "Today Briefing" && decision.opened)).toBe(true);
    expect(receipt?.decisionPath.map((step) => step.label)).toEqual([
      "Input",
      "Intent",
      "Query keys",
      "Context selection",
      "Surface decision",
      "Answer",
      "After-turn changes",
    ]);
    expect(receipt?.decisionPath[0].value).toBe("Turn input received");
    expect(receipt?.decisionPath[0].detail).toContain("Raw prompt text is not shown");
    expect(JSON.stringify(receipt)).not.toContain("What does my day look like?");
    expect(receipt?.writes.summary).toBe("No writes. Read-only.");
    expect(receipt?.writes.mode).toBe("Read-only");
  });

  it("falls back to current-request-only context when no provenance was selected", () => {
    const receipt = buildInspectionReceipt(turn({
      surfaceInvocation: null,
      surfacePayloads: [],
      activeSurfaceId: null,
      contextBudget: null,
      answerBasis: {
        kind: "intuitive",
        label: "Intuitive Answer",
        summary: "",
        hasFactualGrounding: false,
        sources: [],
        counts: {},
      },
    }));

    expect(receipt?.contextItems).toHaveLength(1);
    expect(receipt?.contextItems[0].type).toBe("Current request");
    expect(receipt?.surfaceDecisions.some((decision) => !decision.opened)).toBe(true);
  });

  it("shows attention query keys and selected resources", () => {
    const receipt = buildInspectionReceipt(turn({
      queryFrame: {
        rawText: "Go back to the draft from last Tuesday.",
        normalizedText: "go back to the draft from last tuesday.",
        tokens: ["back", "draft", "last", "tuesday"],
        domains: ["whiteboard"],
        operations: ["reopen"],
        entities: [],
        artifactKinds: ["whiteboard"],
        temporalReferences: [{ rawText: "last Tuesday", relation: "worked_on", start: "2026-05-12", end: "2026-05-12", grain: "day" }],
      },
      attentionCandidates: [
        {
          id: "candidate-artifact",
          resourceId: "artifact:tuesday-draft",
          kind: "artifact",
          app: "whiteboard",
          title: "Tuesday Draft",
          summary: "Draft from Tuesday.",
          source: "artifact",
          score: 9.4,
          matchedKeys: ["draft"],
          temporalMatches: ["worked_on:last Tuesday"],
          suggestedSurface: "whiteboard",
          whyCandidate: "matched time",
          retrievalScores: { deterministic: 4.2, temporal: 5, vector_similarity: 0.31, vector_bonus: 1.12, hybrid: 10.32 },
        },
      ],
      navigatorSelection: {
        selectedIds: ["artifact:tuesday-draft"],
        primaryResourceId: "artifact:tuesday-draft",
        supportingResourceIds: [],
        rejectedCandidateIds: [],
        surfaceToOpen: "whiteboard",
        reason: "The user asked to reopen the Tuesday draft.",
        confidence: 0.9,
        fallback: false,
      },
      selectedAttentionResources: [
        {
          id: "selected-artifact:tuesday-draft",
          resourceId: "artifact:tuesday-draft",
          kind: "artifact",
          app: "whiteboard",
          title: "Tuesday Draft",
          summary: "Draft from Tuesday.",
          source: "artifact",
          content: "# Tuesday Draft",
          data: {},
          timestamps: { last_edited_at: "2026-05-12" },
          suggestedSurface: "whiteboard",
          whySelected: "The user asked to reopen the Tuesday draft.",
        },
      ],
    }), null);

    expect(receipt?.contextItems.some((item) => item.title === "Tuesday Draft" && item.status === "Selected")).toBe(true);
    expect(receipt?.decisionPath.some((step) => step.label === "Query keys" && step.value.includes("last Tuesday"))).toBe(true);
    expect(receipt?.decisionPath.some((step) => step.label === "Context selection" && step.value.includes("Tuesday draft"))).toBe(true);
    expect(receipt?.decisionPath.some((step) => step.label === "Context selection" && step.detail?.includes("semantic vector match"))).toBe(true);
  });
});
