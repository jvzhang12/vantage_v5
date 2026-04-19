import test from "node:test";
import assert from "node:assert/strict";

import {
  buildWorkspaceContextPayload,
  deriveWorkspaceContextScope,
  isExplicitWhiteboardRequest,
  shouldCarryPendingWorkspaceUpdate,
} from "../src/vantage_v5/webapp/chat_request.mjs";
import {
  buildScopedTurnSnapshotKey,
  buildTurnSnapshotKey,
  closeVantageSurface,
  hasWhiteboardActiveContext,
  hideWhiteboardSurface,
  normalizeSurfaceState,
  openVantageSurface,
  revealWhiteboardSurface,
  toggleWhiteboardSurface,
} from "../src/vantage_v5/webapp/surface_state.mjs";
import {
  buildWorkspaceSnapshot,
  shouldPreserveUnsavedWorkspace,
} from "../src/vantage_v5/webapp/workspace_state.mjs";
import {
  buildTurnPanelGroundingCopy,
} from "../src/vantage_v5/webapp/turn_panel_grounding.mjs";
import {
  normalizeLearnedItems,
  normalizeRecordId,
  normalizeResponseMode,
  normalizeScenarioLabPayload,
  normalizeTurnPayload,
  normalizeTurnInterpretation,
  normalizeWorkspaceUpdate,
} from "../src/vantage_v5/webapp/turn_payloads.mjs";

test("surface state preserves whiteboard return flow through Vantage", () => {
  const fromWhiteboard = openVantageSurface({ current: "whiteboard", returnSurface: "chat" });
  assert.deepEqual(fromWhiteboard, { current: "vantage", returnSurface: "whiteboard" });
  assert.equal(hasWhiteboardActiveContext(fromWhiteboard), false);
  assert.deepEqual(closeVantageSurface(fromWhiteboard), { current: "whiteboard", returnSurface: "chat" });
  assert.deepEqual(toggleWhiteboardSurface({ current: "whiteboard", returnSurface: "chat" }), { current: "chat", returnSurface: "chat" });
  assert.deepEqual(revealWhiteboardSurface({ current: "chat", returnSurface: "chat" }), { current: "whiteboard", returnSurface: "chat" });
  assert.deepEqual(revealWhiteboardSurface(fromWhiteboard), { current: "whiteboard", returnSurface: "chat" });
  assert.deepEqual(hideWhiteboardSurface({ current: "whiteboard", returnSurface: "chat" }), { current: "chat", returnSurface: "chat" });
  assert.deepEqual(hideWhiteboardSurface(fromWhiteboard), { current: "chat", returnSurface: "chat" });
});

test("surface state normalizes legacy booleans and snapshot keys are fully scoped", () => {
  assert.deepEqual(
    normalizeSurfaceState({ vantageOpen: true, whiteboardVisible: true }),
    { current: "vantage", returnSurface: "whiteboard" },
  );
  assert.deepEqual(
    normalizeSurfaceState({ current: "vantage", whiteboardVisible: true }),
    { current: "vantage", returnSurface: "whiteboard" },
  );
  assert.equal(
    buildTurnSnapshotKey({
      scope: "experiment",
      experimentSessionId: "exp-123",
      workspaceId: "draft-abc",
    }),
    "vantage-v5-turn-snapshot::experiment::exp-123::draft-abc",
  );
  assert.equal(
    buildScopedTurnSnapshotKey({
      scope: "experiment",
      experimentSessionId: "exp-123",
    }),
    "vantage-v5-turn-snapshot::experiment::exp-123::active",
  );
});

test("dirty local whiteboard state is preserved across passive workspace refreshes", () => {
  const dirtyDraft = buildWorkspaceSnapshot({
    workspaceId: "draft-email-to-jerry",
    scope: "experiment",
    title: "Draft Email to Jerry",
    content: "# Draft Email to Jerry\n\nHi Jerry,",
    savedContent: "",
    dirty: true,
    lifecycle: "transient_draft",
    note: "Draft pulled into the whiteboard from this turn. Save the whiteboard when you're ready.",
  });

  assert.equal(
    shouldPreserveUnsavedWorkspace({
      currentWorkspace: dirtyDraft,
      incomingWorkspace: {
        workspace_id: "experiment-workspace",
        scope: "experiment",
        title: "Experiment Workspace",
        content: "# Experiment Workspace",
      },
      preserveDirty: true,
    }),
    true,
  );

  assert.equal(
    shouldPreserveUnsavedWorkspace({
      currentWorkspace: dirtyDraft,
      incomingWorkspace: {
        workspace_id: "default-workspace",
        scope: "durable",
        title: "Whiteboard",
        content: "# Whiteboard",
      },
      preserveDirty: true,
    }),
    false,
  );

  assert.equal(dirtyDraft.workspaceId, "draft-email-to-jerry");
  assert.equal(dirtyDraft.dirty, true);
  assert.equal(dirtyDraft.lifecycle, "transient_draft");

  assert.deepEqual(
    buildWorkspaceSnapshot({
      workspaceId: "draft-plan",
      content: "# Draft Plan",
      dirty: true,
    }),
    {
      workspaceId: "draft-plan",
      scope: "durable",
      title: "Whiteboard",
      content: "# Draft Plan",
      savedContent: "",
      dirty: true,
      pinnedToChat: false,
      lifecycle: "transient_draft",
      note: "",
    },
  );

  assert.equal(
    shouldPreserveUnsavedWorkspace({
      currentWorkspace: {
        workspaceId: "draft-email-to-jerry",
        scope: "experiment",
        content: "# Draft Email to Jerry\n\nHi Jerry,",
        savedContent: "# Draft Email to Jerry\n\nHi Jerry,",
        dirty: true,
      },
      incomingWorkspace: {
        workspace_id: "different-experiment-workspace",
        scope: "experiment",
        title: "Different Workspace",
        content: "# Completely Different Workspace",
      },
      preserveDirty: true,
    }),
    false,
  );
});

test("workspace context payload only includes whiteboard content when it is intentionally in scope", () => {
  const workspace = {
    workspaceId: "draft-plan",
    content: "# Draft\n\nPlan",
  };

  assert.equal(deriveWorkspaceContextScope({
    surface: { current: "chat", returnSurface: "chat" },
    message: "What do you recommend?",
  }), "excluded");

  assert.equal(isExplicitWhiteboardRequest("Open the whiteboard for this."), true);
  assert.equal(isExplicitWhiteboardRequest("Put that on the whiteboard so we can refine it there."), true);
  assert.equal(isExplicitWhiteboardRequest("Can you review the whiteboard rules with me?"), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate(""), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate("", { force: true }), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("yes, do it"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("okay"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Let's do that."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("That works"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("That sounds good"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("update the email with that information"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("add a signature and greeting"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Resume that draft."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Continue with the budget assumptions for next quarter."), false);
  assert.equal(
    shouldCarryPendingWorkspaceUpdate(
      "That works, but before we do anything else I want to switch topics completely and talk through the quarterly planning assumptions, the travel budget, the meeting schedule, the hiring plan, and several unrelated notes in one long message that should definitely exceed the pending follow-up guard.",
    ),
    false,
  );
  assert.equal(shouldCarryPendingWorkspaceUpdate("can you draft an email to jerry asking how his day is going"), false);
  assert.equal(deriveWorkspaceContextScope({
    surface: { current: "vantage", returnSurface: "whiteboard" },
    message: "What do you recommend?",
  }), "excluded");
  assert.equal(deriveWorkspaceContextScope({
    surface: { current: "chat", returnSurface: "chat" },
    workspacePinned: true,
    message: "What do you recommend?",
  }), "pinned");
  assert.equal(deriveWorkspaceContextScope({
    surface: { current: "chat", returnSurface: "chat" },
    message: "update the email with that information",
  }), "excluded");
  assert.equal(deriveWorkspaceContextScope({
    surface: { current: "whiteboard", returnSurface: "chat" },
    forceScope: "excluded",
  }), "excluded");

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "chat", returnSurface: "chat" },
      workspace,
      message: "What do you recommend?",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "excluded",
    },
  );

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "whiteboard", returnSurface: "chat" },
      workspace,
      message: "What do you recommend?",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "visible",
      workspace_content: "# Draft\n\nPlan",
    },
  );

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "vantage", returnSurface: "whiteboard" },
      workspace,
      message: "What do you recommend?",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "excluded",
    },
  );

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "chat", returnSurface: "chat" },
      workspace,
      workspacePinned: true,
      message: "What do you recommend?",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "pinned",
      workspace_content: "# Draft\n\nPlan",
    },
  );

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "chat", returnSurface: "chat" },
      workspace,
      forceScope: "auto",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "auto",
    },
  );

  assert.deepEqual(
    buildWorkspaceContextPayload({
      surface: { current: "chat", returnSurface: "chat" },
      workspace,
      message: "Draft this in the whiteboard.",
    }),
    {
      workspace_id: "draft-plan",
      workspace_scope: "requested",
      workspace_content: "# Draft\n\nPlan",
    },
  );
});

test("turn payload normalization surfaces the returned memory trace record", () => {
  const normalized = normalizeTurnPayload({
    memory_trace_record: {
      id: "turn-trace-123",
      title: "Turn Trace: Jerry",
      card: "Recent history contributed to Recall.",
      scope: "durable",
      source: "memory_trace",
    },
  });

  assert.deepEqual(normalized.memoryTraceRecord, {
    id: "turn-trace-123",
    title: "Turn Trace: Jerry",
    card: "Recent history contributed to Recall.",
    body: "",
    source: "memory_trace",
    type: "memory_trace",
    status: "active",
    scope: "durable",
    sourceLabel: "Memory Trace",
  });
});

test("turn panel grounding copy keeps the dock and meta labels aligned for the six grounding cases", () => {
  const cases = [
    {
      name: "recall grounded",
      grounding: {
        groundingLabel: "Recall",
        recallCount: 2,
        workingMemoryCount: 2,
        hasBroaderGrounding: false,
        hasGroundedContext: true,
        isBestGuess: false,
      },
      learnedCount: 1,
      expected: {
        metaText: "Recall: 2 items • Learned: 1",
        answerDockLabel: "Recall",
        turnIntentLabel: "Recall",
      },
    },
    {
      name: "whiteboard grounded",
      grounding: {
        groundingLabel: "Whiteboard",
        workingMemoryCount: 0,
        hasBroaderGrounding: true,
        hasGroundedContext: true,
        isBestGuess: false,
      },
      learnedCount: 0,
      expected: {
        metaText: "Grounding: Whiteboard",
        answerDockLabel: "Whiteboard",
        turnIntentLabel: "Whiteboard",
      },
    },
    {
      name: "recent-chat grounded",
      grounding: {
        groundingLabel: "Recent Chat",
        workingMemoryCount: 0,
        hasBroaderGrounding: true,
        hasGroundedContext: true,
        isBestGuess: false,
      },
      learnedCount: 0,
      expected: {
        metaText: "Grounding: Recent Chat",
        answerDockLabel: "Recent Chat",
        turnIntentLabel: "Recent Chat",
      },
    },
    {
      name: "pending-whiteboard grounded",
      grounding: {
        groundingLabel: "Prior Whiteboard",
        workingMemoryCount: 0,
        hasBroaderGrounding: true,
        hasGroundedContext: true,
        isBestGuess: false,
      },
      learnedCount: 0,
      expected: {
        metaText: "Grounding: Prior Whiteboard",
        answerDockLabel: "Prior Whiteboard",
        turnIntentLabel: "Prior Whiteboard",
      },
    },
    {
      name: "mixed-context grounded",
      grounding: {
        groundingLabel: "Recall + Recent Chat",
        recallCount: 2,
        workingMemoryCount: 2,
        hasBroaderGrounding: true,
        hasGroundedContext: true,
        isBestGuess: false,
      },
      learnedCount: 0,
      expected: {
        metaText: "Recall: 2 items • Grounding: Recall + Recent Chat",
        answerDockLabel: "Recall + Recent Chat",
        turnIntentLabel: "Recall + Recent Chat",
      },
    },
    {
      name: "true best guess",
      grounding: {
        groundingLabel: "Best Guess",
        workingMemoryCount: 0,
        hasBroaderGrounding: false,
        hasGroundedContext: false,
        isBestGuess: true,
      },
      learnedCount: 0,
      expected: {
        metaText: "Grounding: Best Guess",
        answerDockLabel: "Best Guess",
        turnIntentLabel: "Best Guess",
      },
    },
  ];

  for (const testCase of cases) {
    assert.deepEqual(
      buildTurnPanelGroundingCopy({
        grounding: testCase.grounding,
        learnedCount: testCase.learnedCount,
      }),
      {
        groundingLabel: testCase.expected.turnIntentLabel,
        metaText: testCase.expected.metaText,
        answerDockLabel: testCase.expected.answerDockLabel,
        turnIntentLabel: testCase.expected.turnIntentLabel,
      },
      testCase.name,
    );
  }
});

test("turn panel grounding copy covers idle and learned-only fallback branches", () => {
  assert.deepEqual(
    buildTurnPanelGroundingCopy({
      grounding: {
        groundingLabel: "Idle",
        workingMemoryCount: 0,
        hasBroaderGrounding: false,
        hasGroundedContext: false,
        isBestGuess: false,
      },
      learnedCount: 0,
    }),
    {
      groundingLabel: "Idle",
      metaText: "No grounded context surfaced yet",
      answerDockLabel: "Idle",
      turnIntentLabel: "Idle",
    },
  );

  assert.deepEqual(
    buildTurnPanelGroundingCopy({
      grounding: {
        groundingLabel: "Idle",
        workingMemoryCount: 0,
        hasBroaderGrounding: false,
        hasGroundedContext: false,
        isBestGuess: false,
      },
      learnedCount: 2,
    }),
    {
      groundingLabel: "Idle",
      metaText: "No grounded context surfaced yet • Learned: 2",
      answerDockLabel: "2 learned",
      turnIntentLabel: "Idle",
    },
  );
});

test("turn payload normalization now expects canonical backend DTOs", () => {
  assert.deepEqual(
    normalizeLearnedItems({
      learned: [{ id: "learned-memory" }],
      created_record: { id: "legacy-created-record" },
    }),
    [{ id: "learned-memory" }],
  );

  assert.deepEqual(
    normalizeLearnedItems({
      created_record: { id: "legacy-created-record" },
    }),
    [{ id: "legacy-created-record" }],
  );

  assert.equal(
    normalizeRecordId({ record_id: "record-123", concept_id: "concept-123" }),
    "record-123",
  );

  assert.equal(
    normalizeRecordId({ concept_id: "concept-123" }),
    "concept-123",
  );

  assert.deepEqual(
    normalizeWorkspaceUpdate(
      {
        type: "draft_whiteboard",
        status: "draft_ready",
        summary: "Draft ready.",
        workspace_id: "draft-plan",
        title: "Draft Plan",
        content: "# Draft Plan",
      },
      {},
    ),
    {
      type: "draft_whiteboard",
      status: "draft_ready",
      summary: "Draft ready.",
      workspace_id: "draft-plan",
      title: "Draft Plan",
      content: "# Draft Plan",
      workspaceId: "draft-plan",
      decision: null,
    },
  );

  assert.deepEqual(
    normalizeResponseMode(
      {
        kind: "grounded",
        grounding_mode: "pending_whiteboard",
        context_sources: ["pending_whiteboard"],
        grounding_sources: ["pending_whiteboard"],
        working_memory_count: 0,
      },
      0,
    ),
    {
      kind: "grounded",
      label: "Prior Whiteboard",
      note: "Supported by the prior whiteboard.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: "pending_whiteboard",
      groundingSources: ["pending_whiteboard"],
      contextSources: ["pending_whiteboard"],
    },
  );

  assert.deepEqual(
    normalizeResponseMode(
      {
        kind: "grounded",
        grounding_mode: "whiteboard",
        grounding_sources: ["whiteboard"],
        working_memory_count: 0,
      },
      0,
    ),
    {
      kind: "grounded",
      label: "Whiteboard",
      note: "Supported by the active whiteboard.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: "whiteboard",
      groundingSources: ["whiteboard"],
      contextSources: ["whiteboard"],
    },
  );

  assert.deepEqual(
    normalizeResponseMode(
      {
        kind: "grounded",
        grounding_mode: "mixed_context",
        context_sources: ["working_memory", "recent_chat"],
        working_memory_count: 2,
      },
      0,
    ),
    {
      kind: "grounded",
      label: "Recall + Recent Chat",
      note: "Supported by Recall and the recent conversation.",
      recallCount: 2,
      workingMemoryCount: 2,
      groundingMode: "mixed_context",
      groundingSources: ["recall", "recent_chat"],
      contextSources: ["recall", "recent_chat"],
    },
  );

  assert.deepEqual(
    normalizeResponseMode(
      {
        kind: "grounded",
        grounding_mode: "recall",
        recall_count: 1,
      },
      0,
    ),
    {
      kind: "grounded",
      label: "Recall",
      note: "Supported by 1 recalled item from Recall.",
      recallCount: 1,
      workingMemoryCount: 1,
      groundingMode: "recall",
      groundingSources: ["recall"],
      contextSources: ["recall"],
    },
  );

  assert.deepEqual(
    normalizeResponseMode(
      {
        kind: "whiteboard_grounded",
        working_memory_count: 0,
      },
      0,
    ),
    {
      kind: "grounded",
      label: "Whiteboard",
      note: "Supported by the active whiteboard.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: "whiteboard",
      groundingSources: ["whiteboard"],
      contextSources: ["whiteboard"],
    },
  );

  assert.deepEqual(
    normalizeResponseMode(null, 0),
    {
      kind: "idle",
      label: "Idle",
      note: "Waiting for a turn.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: null,
      groundingSources: [],
      contextSources: [],
    },
  );

  assert.deepEqual(
    normalizeTurnPayload({
      recall: [{ id: "wm-1" }],
      learned: [{ id: "learned-1" }],
      response_mode: {
        kind: "grounded",
        grounding_mode: "recall",
        recall_count: 1,
      },
      workspace: {
        context_scope: "visible",
      },
      workspace_update: {
        status: "draft_ready",
        summary: "Draft ready.",
      },
    }),
    {
      recallItems: [{ id: "wm-1" }],
      workingMemoryItems: [{ id: "wm-1" }],
      learnedItems: [{ id: "learned-1" }],
      memoryTraceRecord: null,
      responseMode: {
        kind: "grounded",
        label: "Recall",
        note: "Supported by 1 recalled item from Recall.",
        recallCount: 1,
        workingMemoryCount: 1,
        groundingMode: "recall",
        groundingSources: ["recall"],
        contextSources: ["recall"],
      },
      workspaceUpdate: {
        status: "draft_ready",
        summary: "Draft ready.",
        title: "",
        workspaceId: "",
        content: "",
        decision: null,
      },
      workspaceContextScope: "visible",
      scenarioLab: null,
    },
  );

  assert.deepEqual(
    normalizeTurnInterpretation({
      mode: "chat",
      confidence: 0.92,
      reason: "Stayed in chat.",
      requested_whiteboard_mode: "auto",
      resolved_whiteboard_mode: "draft",
      whiteboard_mode_source: "request",
      preserve_selected_record: true,
      selected_record_reason: "Keep the selected draft in scope.",
    }),
    {
      mode: "chat",
      confidence: 0.92,
      reason: "Stayed in chat.",
      requestedWhiteboardMode: "auto",
      resolvedWhiteboardMode: "draft",
      whiteboardModeSource: "request",
      preserveSelectedRecord: true,
      selectedRecordReason: "Keep the selected draft in scope.",
    },
  );
});

test("scenario lab payload normalization turns markdown-heavy scenario outputs into UI-ready sections", () => {
  const scenarioLab = normalizeScenarioLabPayload({
    comparison_question: "Which launch path should we choose?",
    branches: [
      {
        workspace_id: "focused-mvp",
        title: "Focused MVP",
        card: "Launch narrowly to learn quickly.",
        body: [
          "# Focused MVP",
          "",
          "Question: Which launch path should we choose?",
          "",
          "## Shared Assumptions",
          "- Time and budget are limited.",
          "",
          "## Preserved Assumptions",
          "- We still want real users quickly.",
          "",
          "## Changed Assumptions",
          "- We launch to one narrow segment first.",
          "",
          "## Risks",
          "- Feedback could be skewed by the initial segment.",
          "",
          "## Open Questions",
          "- Which segment is most diagnostic?",
          "",
          "## Confidence",
          "High",
        ].join("\n"),
      },
    ],
    comparison_artifact: {
      id: "launch-comparison",
      title: "Launch Comparison",
      body: [
        "# Launch Comparison",
        "",
        "## Shared Assumptions",
        "- Time and budget are limited.",
        "",
        "## Summary",
        "Focused MVP offers the best speed-to-learning tradeoff.",
        "",
        "## Tradeoffs",
        "- Conservative rollout reduces downside but slows learning.",
        "- Aggressive launch speeds exposure but increases operational risk.",
        "",
        "## Recommendation",
        "Start with a focused MVP launch.",
        "",
        "## Next Steps",
        "- Define the first target segment.",
        "- Choose the metrics that trigger expansion.",
      ].join("\n"),
      branch_workspace_ids: ["focused-mvp"],
    },
  });

  assert.equal(scenarioLab.question, "Which launch path should we choose?");
  assert.equal(scenarioLab.recommendation, "Start with a focused MVP launch.");
  assert.deepEqual(scenarioLab.sharedAssumptions, ["Time and budget are limited."]);
  assert.deepEqual(scenarioLab.tradeoffs, [
    "Conservative rollout reduces downside but slows learning.",
    "Aggressive launch speeds exposure but increases operational risk.",
  ]);
  assert.deepEqual(scenarioLab.nextSteps, [
    "Define the first target segment.",
    "Choose the metrics that trigger expansion.",
  ]);
  assert.equal(scenarioLab.branches[0].riskSummary, "Feedback could be skewed by the initial segment.");
  assert.deepEqual(scenarioLab.branches[0].sections.openQuestions.items, ["Which segment is most diagnostic?"]);
});
