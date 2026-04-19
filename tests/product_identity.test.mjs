import test from "node:test";
import assert from "node:assert/strict";

import {
  buildMemoryTraceSummary,
  buildReasoningPathInspection,
  buildChatTurnEvidence,
  buildGuidedInspectionSummary,
  describeResponseModeLabel,
  deriveTurnGrounding,
  deriveWhiteboardLifecycle,
} from "../src/vantage_v5/webapp/product_identity.mjs";

test("buildChatTurnEvidence reports recalled items and learned memories from the canonical recall payload", () => {
  const evidence = buildChatTurnEvidence({
    mode: "chat",
    recall: [{ id: "a" }, { id: "b" }],
    learned: [{ source: "memory", id: "m1" }],
    response_mode: {
      kind: "grounded",
      grounding_mode: "recall",
      recall_count: 2,
    },
  });

  assert.deepEqual(
    evidence.map((item) => item.label),
    ["Used 2 recalled items", "Learned 1 memory"],
  );
});

test("buildChatTurnEvidence trusts canonical working-memory counts over a shorter visible list", () => {
  const evidence = buildChatTurnEvidence({
    mode: "chat",
    working_memory: [{ id: "only-visible" }],
    response_mode: {
      kind: "grounded",
      grounding_mode: "working_memory",
      working_memory_count: 4,
    },
  });

  assert.deepEqual(
    evidence.map((item) => item.label),
    ["Used 4 recalled items"],
  );
});

test("buildChatTurnEvidence surfaces Scenario Lab identity, branches, and draft readiness without mislabeling it as best guess", () => {
  const evidence = buildChatTurnEvidence({
    mode: "scenario_lab",
    scenario_lab: {
      branches: [{ id: "a" }, { id: "b" }, { id: "c" }],
    },
    response_mode: {
      kind: "best_guess",
      grounding_mode: "ungrounded",
    },
    workspace_update: {
      status: "draft_ready",
    },
  });

  assert.deepEqual(
    evidence.map((item) => item.label),
    ["Scenario Lab", "3 branches", "Best Guess", "Draft ready"],
  );
});

test("buildChatTurnEvidence keeps Scenario Lab fallback visible in chat", () => {
  const evidence = buildChatTurnEvidence({
    mode: "chat",
    scenario_lab: {
      status: "failed",
    },
    response_mode: {
      kind: "best_guess",
      grounding_mode: "ungrounded",
    },
  });

  assert.deepEqual(
    evidence.map((item) => item.label),
    ["Scenario Lab", "Fallback", "Best Guess"],
  );
});

test("buildChatTurnEvidence surfaces product-specific grounding labels for whiteboard turns", () => {
  const evidence = buildChatTurnEvidence({
    mode: "chat",
    response_mode: {
      kind: "grounded",
      grounding_mode: "whiteboard",
      working_memory_count: 0,
    },
    workspace_update: {
      status: "draft_ready",
    },
  });

  assert.deepEqual(
    evidence.map((item) => item.label),
    ["Whiteboard", "Draft ready"],
  );
});

test("buildChatTurnEvidence uses product-facing labels for prior whiteboard and mixed-context grounding", () => {
  assert.deepEqual(
    buildChatTurnEvidence({
      mode: "chat",
      response_mode: {
        kind: "grounded",
        grounding_mode: "pending_whiteboard",
        context_sources: ["pending_whiteboard"],
      },
    }).map((item) => item.label),
    ["Prior Whiteboard"],
  );

  assert.deepEqual(
    buildChatTurnEvidence({
      mode: "chat",
      response_mode: {
        kind: "grounded",
        grounding_mode: "mixed_context",
        context_sources: ["working_memory", "recent_chat"],
      },
    }).map((item) => item.label),
    ["Recall + Recent Chat"],
  );
});

test("describeResponseModeLabel keeps the guided-inspection badges compact", () => {
  assert.equal(
    describeResponseModeLabel({ kind: "grounded", groundingMode: "whiteboard", label: "Whiteboard" }),
    "Whiteboard",
  );
  assert.equal(
    describeResponseModeLabel({
      kind: "grounded",
      groundingMode: "pending_whiteboard",
      label: "Prior Whiteboard",
      contextSources: ["pending_whiteboard"],
    }),
    "Prior Whiteboard",
  );
  assert.equal(
    describeResponseModeLabel({
      kind: "grounded",
      groundingMode: "mixed_context",
      label: "Recall + Recent Chat",
      contextSources: ["recall", "recent_chat"],
    }),
    "Recall + Recent Chat",
  );
  assert.equal(
    describeResponseModeLabel({
      kind: "grounded",
      groundingMode: "working_memory",
      label: "Recall",
      contextSources: ["working_memory"],
    }),
    "Recall",
  );
  assert.equal(
    describeResponseModeLabel({ kind: "best_guess", groundingMode: "ungrounded", label: "Best Guess" }),
    "Best Guess",
  );
});

test("buildGuidedInspectionSummary keeps the Vantage header aligned with turn truth", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: { kind: "grounded", groundingMode: "whiteboard", label: "Whiteboard" },
      scenarioLab: {
        branches: [{ id: "a" }, { id: "b" }],
      },
      recallCount: 0,
      learnedCount: 1,
      libraryCount: 7,
      pinnedTitle: "Roadmap",
    }),
    "Scenario Lab: 2 branches • Grounding: Whiteboard • Learned: 1 item • Library: 7 items • Pinned: Roadmap",
  );
});

test("buildGuidedInspectionSummary prefers recalled counts over generic recall labels", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: { kind: "grounded", groundingMode: "working_memory", label: "Recall" },
      recallCount: 3,
      learnedCount: 0,
      libraryCount: 4,
    }),
    "Recall: 3 items • Learned: nothing new yet • Library: 4 items",
  );
});

test("buildGuidedInspectionSummary keeps broader grounded context separate from working-memory recall counts", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: { kind: "grounded", groundingMode: "recent_chat", label: "Recent Chat" },
      recallCount: 0,
      learnedCount: 0,
      libraryCount: 2,
    }),
    "Grounding: Recent Chat • Learned: nothing new yet • Library: 2 items",
  );
});

test("buildGuidedInspectionSummary uses product-facing labels for prior whiteboard grounding", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: {
        kind: "grounded",
        groundingMode: "pending_whiteboard",
        label: "Prior Whiteboard",
        contextSources: ["pending_whiteboard"],
      },
      recallCount: 0,
      learnedCount: 0,
      libraryCount: 3,
    }),
    "Grounding: Prior Whiteboard • Learned: nothing new yet • Library: 3 items",
  );
});

test("buildGuidedInspectionSummary preserves broader grounding when working memory and other context both apply", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: {
        kind: "grounded",
        groundingMode: "mixed_context",
        label: "Recall + Recent Chat",
        contextSources: ["recall", "recent_chat"],
      },
      recallCount: 2,
      learnedCount: 0,
      libraryCount: 5,
    }),
    "Recall: 2 items • Grounding: Recall + Recent Chat • Learned: nothing new yet • Library: 5 items",
  );
});

test("buildGuidedInspectionSummary surfaces best-guess grounding explicitly", () => {
  assert.equal(
    buildGuidedInspectionSummary({
      responseMode: { kind: "best_guess", groundingMode: "ungrounded", label: "Best Guess" },
      recallCount: 0,
      learnedCount: 0,
      libraryCount: 2,
    }),
    "Grounding: Best Guess • Learned: nothing new yet • Library: 2 items",
  );
});

test("buildMemoryTraceSummary explains trace-backed recall and the created trace record", () => {
  assert.equal(
    buildMemoryTraceSummary({
      traceNotes: [{ id: "trace-1" }, { id: "trace-2" }],
      memoryTraceRecord: { id: "turn-trace-3", scope: "durable" },
    }),
    "Recent history contributed 2 recalled items to Recall. This turn also left a durable Memory Trace record.",
  );

  assert.equal(
    buildMemoryTraceSummary({
      traceNotes: [],
      memoryTraceRecord: { id: "turn-trace-4", scope: "experiment" },
    }),
    "No recalled items came from recent history for this answer, but this turn still left an experiment-scoped Memory Trace record for future continuity.",
  );
});

test("buildReasoningPathInspection keeps the staged path aligned with the six grounding cases", () => {
  const cases = [
    {
      name: "working-memory grounded",
      responseMode: {
        kind: "grounded",
        groundingMode: "working_memory",
        recallCount: 2,
        contextSources: ["recall"],
      },
      interpretation: {
        mode: "chat",
        reason: "Recall grounded this answer.",
      },
      expectedGrounding: "Recall",
      expectedWorkingMemory: "In scope for generation: Recall.",
    },
    {
      name: "whiteboard grounded",
      responseMode: {
        kind: "grounded",
        groundingMode: "whiteboard",
        contextSources: ["whiteboard"],
      },
      interpretation: {
        mode: "chat",
        resolvedWhiteboardMode: "draft",
        reason: "The whiteboard handled the draft.",
      },
      expectedGrounding: "Whiteboard",
      expectedWorkingMemory: "In scope for generation: Whiteboard.",
    },
    {
      name: "recent-chat grounded",
      responseMode: {
        kind: "grounded",
        groundingMode: "recent_chat",
        contextSources: ["recent_chat"],
      },
      interpretation: {
        mode: "chat",
        reason: "Recent chat carried the answer.",
      },
      expectedGrounding: "Recent Chat",
      expectedWorkingMemory: "In scope for generation: Recent Chat.",
    },
    {
      name: "pending-whiteboard grounded",
      responseMode: {
        kind: "grounded",
        groundingMode: "pending_whiteboard",
        contextSources: ["pending_whiteboard"],
      },
      interpretation: {
        mode: "chat",
        resolvedWhiteboardMode: "chat",
        reason: "The prior whiteboard still mattered.",
      },
      expectedGrounding: "Prior Whiteboard",
      expectedWorkingMemory: "In scope for generation: Prior Whiteboard.",
    },
    {
      name: "mixed-context grounded",
      responseMode: {
        kind: "grounded",
        groundingMode: "mixed_context",
        contextSources: ["recall", "recent_chat"],
        recallCount: 2,
      },
      interpretation: {
        mode: "chat",
        reason: "Recall and recent chat both shaped the answer.",
      },
      expectedGrounding: "Recall + Recent Chat",
      expectedWorkingMemory: "In scope for generation: Recall + Recent Chat.",
    },
    {
      name: "true best guess",
      responseMode: {
        kind: "best_guess",
        groundingMode: "ungrounded",
      },
      interpretation: {
        mode: "chat",
        reason: "The answer was not grounded in recalled context.",
      },
      expectedGrounding: "Best Guess",
      expectedWorkingMemory: "In scope for generation: no grounded context (Best Guess).",
    },
  ];

  for (const testCase of cases) {
    const inspection = buildReasoningPathInspection({
      userMessage: "Draft an email to Judy thanking her for the flowers.",
      interpretation: testCase.interpretation,
      responseMode: testCase.responseMode,
      candidateConcepts: [{ id: "concept-1" }],
      candidateSavedNotes: [{ id: "memory-1" }],
      candidateVaultNotes: [{ id: "vault-1" }],
      recallItems: [{ id: "recall-1" }, { id: "recall-2" }],
    });

    assert.equal(inspection.label, "Reasoning Path", testCase.name);
    assert.equal(inspection.groundingLabel, testCase.expectedGrounding, testCase.name);
    assert.equal(inspection.stages[0].label, "Request", testCase.name);
    assert.equal(inspection.stages[1].label, "Route", testCase.name);
    assert.equal(inspection.stages[2].label, "Candidate context", testCase.name);
    assert.equal(inspection.stages[2].text, "3 candidate items were considered before vetting (1 concept, 1 memory, 1 reference note).", testCase.name);
    assert.equal(inspection.stages[2].detail.groups.length, 4, testCase.name);
    assert.equal(inspection.stages[2].detail.groups[0].items.length, 1, testCase.name);
    assert.equal(inspection.stages[2].detail.groups[2].items.length, 0, testCase.name);
    assert.equal(inspection.stages[3].label, "Recall", testCase.name);
    assert.equal(inspection.stages[3].text, "2 recalled items were selected into Recall.", testCase.name);
    assert.equal(inspection.stages[3].detail.groups[0].items.length, 2, testCase.name);
    assert.equal(inspection.stages[4].label, "Working Memory", testCase.name);
    assert.equal(inspection.stages[4].text, testCase.expectedWorkingMemory, testCase.name);
    assert.equal(inspection.stages[5].label, "Outcome", testCase.name);
    assert.ok(inspection.summary.includes(testCase.expectedGrounding), testCase.name);
  }
});

test("buildReasoningPathInspection surfaces continuity, working-memory scope, and outcome truthfully", () => {
  const inspection = buildReasoningPathInspection({
    userMessage: "Update the email with my name.",
    interpretation: {
      mode: "chat",
      reason: "The existing draft should stay in scope while the answer remains in chat.",
      confidence: 0.91,
      requestedWhiteboardMode: "auto",
      resolvedWhiteboardMode: "offer",
      whiteboardModeSource: "interpreter",
      preserveSelectedRecord: true,
      selectedRecordReason: "Keep the draft email in continuity.",
    },
    responseMode: {
      kind: "grounded",
      groundingMode: "mixed_context",
      label: "Recall + Whiteboard",
      contextSources: ["recall", "whiteboard"],
      recallCount: 1,
    },
    candidateConcepts: [{ id: "candidate-1" }],
    candidateSavedNotes: [{ id: "candidate-2" }],
    candidateVaultNotes: [{ id: "candidate-3" }],
    recallItems: [{ id: "memory-1" }],
    learnedItems: [{ id: "artifact-1", source: "artifact" }],
    memoryTraceRecord: { id: "turn-trace-1", title: "Turn Trace" },
  });

  assert.equal(inspection.stages.length, 6);
  assert.equal(inspection.stages[1].label, "Route");
  assert.match(inspection.stages[1].text, /existing draft should stay in scope/i);
  assert.deepEqual(
    inspection.stages[1].meta.map((item) => item.label),
    ["Path", "Whiteboard", "Requested", "Decision Source", "Continuity", "Confidence"],
  );
  assert.equal(inspection.stages[2].label, "Candidate context");
  assert.match(inspection.stages[2].text, /3 candidate items were considered before vetting/);
  assert.equal(inspection.stages[2].detail.groups.length, 4);
  assert.equal(inspection.stages[2].detail.groups[0].items.length, 1);
  assert.equal(inspection.stages[3].label, "Recall");
  assert.match(inspection.stages[3].text, /1 recalled item was selected into Recall\./);
  assert.equal(inspection.stages[3].detail.groups[0].items.length, 1);
  assert.equal(inspection.stages[4].label, "Working Memory");
  assert.match(inspection.stages[4].text, /In scope for generation: Recall \+ Whiteboard\./);
  assert.deepEqual(
    inspection.stages[4].detail.notes.map((item) => [item.label, item.value]),
    [
      ["User request", "Included"],
      ["Recall", "1 item"],
      ["Whiteboard", "Included"],
      ["Recent chat", "Excluded"],
      ["Selected context preserved", "Included"],
      ["Memory Trace contribution", "None"],
    ],
  );
  assert.deepEqual(
    inspection.stages[4].detail.scopeRows.map((row) => [row.label, row.status]),
    [
      ["User request", "Included"],
      ["Recall", "Included"],
      ["Whiteboard", "Included"],
      ["Recent chat", "Excluded"],
      ["Selected context preserved", "Included"],
      ["Memory Trace contribution", "Excluded"],
    ],
  );
  assert.match(inspection.stages[4].detail.summary, /This describes scope, not causal attribution\./);
  assert.equal(inspection.stages[5].label, "Outcome");
  assert.match(inspection.stages[5].text, /A Memory Trace record was captured/i);
  assert.equal(inspection.stages[5].detail.groups.length, 2);
  assert.match(inspection.summary, /3 candidate items were considered before vetting/);
  assert.match(inspection.summary, /1 recalled item entered Working Memory\./);
});

test("buildReasoningPathInspection includes memory-trace candidates in candidate context details", () => {
  const inspection = buildReasoningPathInspection({
    userMessage: "What should I ask next?",
    interpretation: {
      mode: "chat",
      reason: "Search for nearby continuity before answering.",
    },
    responseMode: {
      kind: "grounded",
      groundingMode: "working_memory",
      recallCount: 1,
      contextSources: ["recall"],
    },
    candidateConcepts: [{ id: "concept-1", title: "Concept" }],
    candidateSavedNotes: [{ id: "memory-1", title: "Memory" }],
    candidateTraceNotes: [{ id: "trace-1", title: "Turn Trace", source: "memory_trace", type: "memory_trace" }],
    candidateVaultNotes: [{ id: "vault-1", title: "Reference", source: "vault" }],
    recallItems: [{ id: "trace-1", title: "Turn Trace", source: "memory_trace", type: "memory_trace" }],
    traceNotes: [
      { id: "trace-1", title: "Turn Trace", source: "memory_trace", type: "memory_trace" },
      { id: "trace-2", title: "Candidate Only", source: "memory_trace", type: "memory_trace" },
    ],
  });

  assert.equal(
    inspection.stages[2].text,
    "4 candidate items were considered before vetting (1 concept, 1 memory, 1 memory trace item, 1 reference note).",
  );
  assert.equal(inspection.stages[2].detail.groups[2].label, "Memory Trace candidates");
  assert.equal(inspection.stages[2].detail.groups[2].items.length, 1);
  assert.equal(inspection.stages[2].detail.groups[2].items[0].reasoningStatusLabel, "selected into recall");
  assert.deepEqual(
    inspection.stages[4].detail.notes.map((item) => [item.label, item.value]),
    [
      ["User request", "Included"],
      ["Recall", "1 item"],
      ["Whiteboard", "Excluded"],
      ["Recent chat", "Excluded"],
      ["Memory Trace contribution", "1 item"],
    ],
  );
  assert.deepEqual(
    inspection.stages[4].detail.scopeRows.map((row) => [row.label, row.status]),
    [
      ["User request", "Included"],
      ["Recall", "Included"],
      ["Whiteboard", "Excluded"],
      ["Recent chat", "Excluded"],
      ["Memory Trace contribution", "Included"],
    ],
  );
});

test("deriveTurnGrounding trusts canonical recall counts over visible list length", () => {
  const grounding = deriveTurnGrounding({
    responseMode: {
      kind: "grounded",
      groundingMode: "recall",
      recallCount: 4,
      contextSources: ["recall"],
    },
    recallItems: [{ id: "only-visible-item" }],
    learnedItems: [],
  });

  assert.equal(grounding.workingMemoryCount, 4);
  assert.equal(grounding.visibleWorkingMemoryCount, 1);
  assert.equal(grounding.recallCount, 4);
  assert.equal(grounding.groundingLabel, "Recall");
  assert.equal(grounding.hasGroundedContext, true);
  assert.equal(grounding.hasBroaderGrounding, false);
});

test("deriveTurnGrounding surfaces product-facing labels for broader grounding modes", () => {
  const mixed = deriveTurnGrounding({
    responseMode: {
      kind: "grounded",
      groundingMode: "mixed_context",
      contextSources: ["recall", "recent_chat"],
    },
    workingMemoryItems: [],
    learnedItems: [],
  });

  const prior = deriveTurnGrounding({
    responseMode: {
      kind: "grounded",
      groundingMode: "pending_whiteboard",
      label: "Prior Whiteboard",
      contextSources: ["pending_whiteboard"],
    },
    workingMemoryItems: [],
    learnedItems: [],
  });

  assert.equal(mixed.groundingLabel, "Recall + Recent Chat");
  assert.equal(prior.groundingLabel, "Prior Whiteboard");
});

test("deriveWhiteboardLifecycle distinguishes transient draft, saved whiteboard, and promoted artifact", () => {
  assert.equal(
    deriveWhiteboardLifecycle({ dirty: true, lifecycle: "transient_draft", workspaceId: "draft" }).label,
    "Transient draft",
  );
  assert.equal(
    deriveWhiteboardLifecycle({ dirty: false, lifecycle: "saved_whiteboard", workspaceId: "plan" }).label,
    "Saved whiteboard",
  );
  assert.equal(
    deriveWhiteboardLifecycle({ dirty: false, lifecycle: "promoted_artifact", workspaceId: "plan" }).label,
    "Promoted artifact",
  );
});
