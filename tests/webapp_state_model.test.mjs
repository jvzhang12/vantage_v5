import test from "node:test";
import assert from "node:assert/strict";

import {
  buildWorkspaceContextPayload,
  deriveWorkspaceContextScope,
  isDeicticWhiteboardReopenRequest,
  isExplicitWhiteboardRequest,
  resolveWhiteboardReopenTarget,
  shouldCarryPendingWorkspaceUpdate,
} from "../src/vantage_v5/webapp/chat_request.mjs";
import {
  buildScopedTurnSnapshotKey,
  buildTurnSnapshotKey,
  closeVantageSurface,
  hasWhiteboardActiveContext,
  hideWhiteboardSurface,
  normalizeSurfaceState,
  normalizeRestoredTurnSnapshotState,
  openVantageSurface,
  revealWhiteboardSurface,
  toggleWhiteboardSurface,
} from "../src/vantage_v5/webapp/surface_state.mjs";
import {
  buildWorkspaceSnapshot,
  reconcileRestoredWorkspaceAfterLoad,
  shouldPreserveUnsavedWorkspace,
} from "../src/vantage_v5/webapp/workspace_state.mjs";
import {
  buildTurnPanelGroundingCopy,
} from "../src/vantage_v5/webapp/turn_panel_grounding.mjs";
import {
  buildSemanticPolicyCopy,
  buildReasoningPathInspection,
  describeSemanticActionCopy,
  describeSemanticClarificationCopy,
} from "../src/vantage_v5/webapp/product_identity.mjs";
import {
  normalizeLearnedItems,
  normalizeComparisonBranchIndex,
  normalizeActivity,
  normalizeProtocolMetadata,
  normalizeRecordId,
  normalizeResponseMode,
  normalizeScenarioLabPayload,
  normalizeSemanticFrame,
  normalizeSemanticPolicy,
  normalizeSystemState,
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

test("deictic whiteboard reopen requests can resolve a unique recalled durable item", () => {
  assert.equal(
    isDeicticWhiteboardReopenRequest("yea can you pull that up on the whiteboard?"),
    true,
  );
  assert.deepEqual(
    resolveWhiteboardReopenTarget({
      message: "yea can you pull that up on the whiteboard?",
      recalledItems: [
        {
          id: "email-insights-on-predicting-behavior",
          title: "Email Draft: Insights on Predicting Behavior",
          source: "artifact",
          isVaultNote: false,
        },
      ],
    }),
    {
      id: "email-insights-on-predicting-behavior",
      title: "Email Draft: Insights on Predicting Behavior",
      source: "artifact",
    },
  );
  assert.equal(
    resolveWhiteboardReopenTarget({
      message: "open that in the whiteboard",
      recalledItems: [
        { id: "artifact-a", title: "Artifact A", source: "artifact", isVaultNote: false },
        { id: "artifact-b", title: "Artifact B", source: "artifact", isVaultNote: false },
      ],
    }),
    null,
  );
  assert.equal(
    resolveWhiteboardReopenTarget({
      message: "open that in the whiteboard",
      recalledItems: [
        { id: "note-a", title: "Reference note", source: "vault_note", isVaultNote: true },
      ],
    }),
    null,
  );
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

test("snapshot restore preserves inspection state only for workspace-scoped restores", () => {
  const snapshot = {
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "concept-42",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
    pinnedContext: { id: "concept-42", kind: "concept" },
    turn: {
      workspaceContextScope: "visible",
    },
  };

  assert.deepEqual(
    normalizeRestoredTurnSnapshotState(snapshot, { scopeScopedFallback: false }),
    {
      surface: { current: "vantage", returnSurface: "whiteboard" },
      selectedConceptId: "concept-42",
      selectedVaultNoteId: "note-17",
      selectionOrigin: "user",
      pinnedContext: { id: "concept-42", kind: "concept" },
      workspaceContextScope: "visible",
    },
  );

  assert.deepEqual(
    normalizeRestoredTurnSnapshotState(snapshot, { scopeScopedFallback: true }),
    {
      surface: { current: "whiteboard", returnSurface: "chat" },
      selectedConceptId: "",
      selectedVaultNoteId: "",
      selectionOrigin: "bootstrap",
      pinnedContext: { id: "concept-42", kind: "concept" },
      workspaceContextScope: "visible",
    },
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
      latestArtifact: null,
    },
  );

  assert.deepEqual(
    buildWorkspaceSnapshot({
      workspaceId: "roadmap-draft",
      content: "# Roadmap",
      dirty: false,
      latestArtifact: {
        id: "artifact-roadmap-v1",
        title: "Roadmap v1",
        card: "Saved from the whiteboard.",
      },
    }).latestArtifact,
    {
      id: "artifact-roadmap-v1",
      title: "Roadmap v1",
      card: "Saved from the whiteboard.",
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

test("boot workspace reconciliation preserves restored drafts while clearing stale inspection state", () => {
  const reconciliation = reconcileRestoredWorkspaceAfterLoad({
    currentWorkspace: {
      workspaceId: "draft-email-to-jerry",
      scope: "experiment",
      title: "Draft Email to Jerry",
      content: "# Draft Email to Jerry\n\nHi Jerry,",
      savedContent: "",
      dirty: true,
      lifecycle: "transient_draft",
    },
    incomingWorkspace: {
      workspace_id: "experiment-workspace",
      scope: "experiment",
      title: "Experiment Workspace",
      content: "# Experiment Workspace",
    },
    preserveDirty: true,
    scopeScopedFallback: true,
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "concept-42",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
  });

  assert.equal(reconciliation.preserveRestoredWorkspace, true);
  assert.equal(reconciliation.workspace.workspaceId, "draft-email-to-jerry");
  assert.equal(reconciliation.workspace.dirty, true);
  assert.deepEqual(reconciliation.surface, { current: "whiteboard", returnSurface: "chat" });
  assert.equal(reconciliation.selectedConceptId, "");
  assert.equal(reconciliation.selectedVaultNoteId, "");
  assert.equal(reconciliation.selectionOrigin, "bootstrap");
});

test("boot workspace reconciliation keeps stable inspection state when the workspace does not change", () => {
  const reconciliation = reconcileRestoredWorkspaceAfterLoad({
    currentWorkspace: {
      workspaceId: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A",
      dirty: false,
      lifecycle: "saved_whiteboard",
    },
    incomingWorkspace: {
      workspace_id: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A",
    },
    preserveDirty: true,
    scopeScopedFallback: false,
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "concept-42",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
  });

  assert.equal(reconciliation.workspaceReplaced, false);
  assert.equal(reconciliation.surface.current, "vantage");
  assert.equal(reconciliation.surface.returnSurface, "whiteboard");
  assert.equal(reconciliation.selectedConceptId, "concept-42");
  assert.equal(reconciliation.selectedVaultNoteId, "note-17");
  assert.equal(reconciliation.selectionOrigin, "user");
});

test("boot workspace reconciliation keeps continuity through harmless title-only normalization", () => {
  const reconciliation = reconcileRestoredWorkspaceAfterLoad({
    currentWorkspace: {
      workspaceId: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A\n\nBody",
      dirty: false,
      lifecycle: "saved_whiteboard",
    },
    incomingWorkspace: {
      workspace_id: "workspace-a",
      scope: "durable",
      title: "Whiteboard A (Renamed)",
      content: "# Whiteboard A\n\nBody\n",
    },
    preserveDirty: true,
    scopeScopedFallback: false,
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "artifact-a-v1",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
  });

  assert.equal(reconciliation.workspaceReplaced, false);
  assert.equal(reconciliation.surface.current, "vantage");
  assert.equal(reconciliation.surface.returnSurface, "whiteboard");
  assert.equal(reconciliation.selectedConceptId, "artifact-a-v1");
  assert.equal(reconciliation.selectedVaultNoteId, "note-17");
  assert.equal(reconciliation.selectionOrigin, "user");
});

test("boot workspace reconciliation clears inspection state when a saved whiteboard reloads changed content under the same id", () => {
  const reconciliation = reconcileRestoredWorkspaceAfterLoad({
    currentWorkspace: {
      workspaceId: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A",
      dirty: false,
      lifecycle: "saved_whiteboard",
      latestArtifact: {
        id: "artifact-a-v1",
        title: "Whiteboard A v1",
      },
    },
    incomingWorkspace: {
      workspace_id: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A\n\nUpdated remotely",
    },
    preserveDirty: true,
    scopeScopedFallback: false,
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "artifact-a-v1",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
  });

  assert.equal(reconciliation.workspaceReplaced, true);
  assert.deepEqual(reconciliation.surface, { current: "whiteboard", returnSurface: "chat" });
  assert.equal(reconciliation.selectedConceptId, "");
  assert.equal(reconciliation.selectedVaultNoteId, "");
  assert.equal(reconciliation.selectionOrigin, "bootstrap");
});

test("boot workspace reconciliation collapses stale inspection state when the workspace anchor changes from blank to saved", () => {
  const reconciliation = reconcileRestoredWorkspaceAfterLoad({
    currentWorkspace: {
      workspaceId: "",
      scope: "durable",
      title: "Whiteboard",
      content: "",
      dirty: false,
      lifecycle: "ready",
    },
    incomingWorkspace: {
      workspace_id: "workspace-a",
      scope: "durable",
      title: "Whiteboard A",
      content: "# Whiteboard A",
    },
    preserveDirty: true,
    scopeScopedFallback: false,
    surface: { current: "vantage", returnSurface: "whiteboard" },
    selectedConceptId: "concept-42",
    selectedVaultNoteId: "note-17",
    selectionOrigin: "user",
  });

  assert.equal(reconciliation.workspaceReplaced, true);
  assert.deepEqual(reconciliation.surface, { current: "whiteboard", returnSurface: "chat" });
  assert.equal(reconciliation.selectedConceptId, "");
  assert.equal(reconciliation.selectedVaultNoteId, "");
  assert.equal(reconciliation.selectionOrigin, "bootstrap");
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
  assert.equal(shouldCarryPendingWorkspaceUpdate("Open the whiteboard."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Okay, open the whiteboard."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Put that in the whiteboard."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("That works, put that in the whiteboard."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Open it, put that in the whiteboard."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Which one?"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("What about that one?"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Tell me more."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("update the email with that information"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("add a signature and greeting"), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Resume that draft."), true);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Continue with the budget assumptions for next quarter."), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Open the whiteboard and draft a thank-you email to Judy."), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Draft a thank-you email in the whiteboard."), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate("Okay, draft a 7-day road trip itinerary in the whiteboard."), false);
  assert.equal(shouldCarryPendingWorkspaceUpdate("That works, draft a budget plan in the whiteboard."), false);
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

test("turn interpretation normalization prefers pinned context semantics while keeping legacy aliases", () => {
  const normalized = normalizeTurnInterpretation({
    preserve_pinned_context: true,
    pinned_context_reason: "The pinned context stays active for continuity.",
    preserve_selected_record: false,
    selected_record_reason: "Legacy selected-record wording should not win.",
    control_panel: {
      actions: [
        { type: "recall", reason: "Load the pinned context." },
        { type: "respond", reason: "Answer after Recall is assembled." },
      ],
      working_memory_queries: ["pinned context"],
      response_call: { type: "chat_response", after_working_memory: true },
    },
  });

  assert.equal(normalized.preservePinnedContext, true);
  assert.equal(normalized.pinnedContextReason, "The pinned context stays active for continuity.");
  assert.equal(normalized.preserveSelectedRecord, true);
  assert.equal(normalized.selectedRecordReason, "The pinned context stays active for continuity.");
  assert.deepEqual(normalized.controlPanel.actions.map((action) => action.type), ["recall", "respond"]);
  assert.deepEqual(normalized.controlPanel.workingMemoryQueries, ["pinned context"]);
  assert.equal(normalized.controlPanel.responseCall.after_working_memory, true);
});

test("reasoning path inspection uses pinned context labels for continuity", () => {
  const inspection = buildReasoningPathInspection({
    userMessage: "Please update the email with the pinned context in mind.",
    interpretation: {
      mode: "chat",
      confidence: 0.94,
      reason: "The turn should stay in chat with pinned context continuity.",
      resolvedWhiteboardMode: "chat",
      preservePinnedContext: true,
      pinnedContextReason: "The pinned context stays active for continuity.",
    },
    responseMode: {
      kind: "grounded",
      label: "Recall",
      groundingMode: "recall",
      recallCount: 1,
      groundingSources: ["recall"],
      contextSources: ["recall"],
    },
    recallItems: [{ id: "memory-trace-1", source: "memory_trace" }],
    learnedItems: [],
  });

  const routeStage = inspection.stages.find((stage) => stage.label === "Route" || stage.step === "Step 2");
  const workingMemoryStage = inspection.stages.find((stage) => stage.label === "Working Memory");
  assert.ok(routeStage);
  assert.ok(workingMemoryStage);
  assert.ok(routeStage.meta.some((item) => item.label === "Kept in scope" && item.value === "The pinned context stays active for continuity."));
  assert.ok(workingMemoryStage.detail.scopeRows.some((item) => item.label === "Kept in scope" && item.status === "Included"));
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
        metaText: "Recall: 2 items • What I learned: 1",
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
      metaText: "No grounded context surfaced yet • What I learned: 2",
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

  assert.deepEqual(
    normalizeLearnedItems({
      created_record: {
        id: "learned-memory",
        scope: "experiment",
        durability: "temporary",
        why_learned: "Saved as memory because the user asked Vantage to remember it.",
        correction_affordance: {
          kind: "open_in_whiteboard",
          label: "Open in whiteboard",
        },
      },
    }),
    [{
      id: "learned-memory",
      scope: "experiment",
      durability: "temporary",
      why_learned: "Saved as memory because the user asked Vantage to remember it.",
      correction_affordance: {
        kind: "open_in_whiteboard",
        label: "Open in whiteboard",
      },
    }],
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
      pinnedContextId: null,
      pinnedContext: null,
      selectedRecordId: null,
      selectedRecord: null,
      scenarioLab: null,
      semanticFrame: null,
      semanticPolicy: null,
      systemState: null,
      activity: [],
    },
  );

  assert.deepEqual(
    normalizeProtocolMetadata({
      type: "protocol",
      protocol: {
        protocol_kind: "scenario_lab",
        variables: { lens: "tradeoffs" },
        applies_to: ["scenario planning"],
        modifiable: "false",
        is_builtin: "true",
        overrides_builtin: "false",
      },
    }),
    {
      protocolKind: "scenario_lab",
      variables: { lens: "tradeoffs" },
      appliesTo: ["scenario planning"],
      modifiable: false,
      isBuiltin: true,
      overridesBuiltin: false,
    },
  );

  assert.deepEqual(
    normalizeSystemState({
      mode: "openai",
      workspace_scope: "durable",
      user: { id: "eden" },
      nexus_enabled: "true",
      experiment: { active: "yes", session_id: "exp-1" },
    }),
    {
      mode: "openai",
      scope: "durable",
      userId: "eden",
      nexusEnabled: true,
      experiment: {
        active: true,
        sessionId: "exp-1",
      },
    },
  );

  assert.deepEqual(
    normalizeActivity([
      { type: "apply protocol", label: "Applied Scenario Lab", message: "Protocol-as-guidance", quiet: "yes" },
    ]),
    [
      {
        type: "apply_protocol",
        label: "Applied Scenario Lab",
        message: "Protocol-as-guidance",
        tone: "neutral",
        source: "",
        quiet: true,
        createdAt: "",
      },
    ],
  );

  assert.deepEqual(
    normalizeSemanticFrame({
      user_goal: "Move the work into a shared draft.",
      task_type: "drafting",
      follow_up_type: "deictic_reference",
      target_surface: "whiteboard",
      referenced_object: {
        id: "v5-milestone-1",
        title: "Milestone Draft",
        type: "whiteboard",
        source: "workspace",
      },
      confidence: 0.86,
      needs_clarification: false,
      commitments: ["Keep drafting work visible in the whiteboard."],
    }),
    {
      userGoal: "Move the work into a shared draft.",
      taskType: "drafting",
      followUpType: "deictic_reference",
      targetSurface: "whiteboard",
      referencedObject: {
        id: "v5-milestone-1",
        title: "Milestone Draft",
        type: "whiteboard",
        source: "workspace",
      },
      confidence: 0.86,
      needsClarification: false,
      clarificationPrompt: null,
      signals: {},
      commitments: ["Keep drafting work visible in the whiteboard."],
    },
  );

  assert.deepEqual(
    normalizeSemanticPolicy({
      semantic_action: "ask clarification",
      action_label: "Clarify target draft",
      needs_clarification: "yes",
      clarification_prompt: "Which draft should I update?",
      clarification_options: ["Current whiteboard", "Pinned milestone"],
      status: "waiting_for_user",
      reason: "The referenced draft is ambiguous.",
      confidence: "0.71",
      blocking: true,
      signals: { ambiguous_reference: true },
    }),
    {
      semanticAction: "ask_clarification",
      actionLabel: "Clarify target draft",
      needsClarification: true,
      clarificationPrompt: "Which draft should I update?",
      clarificationOptions: ["Current whiteboard", "Pinned milestone"],
      status: "waiting_for_user",
      reason: "The referenced draft is ambiguous.",
      confidence: 0.71,
      blocking: true,
      signals: { ambiguous_reference: true },
    },
  );

  assert.equal(
    describeSemanticActionCopy({
      semanticPolicy: { semanticAction: "ask_clarification" },
      semanticFrame: { taskType: "revision", targetSurface: "whiteboard" },
    }),
    "Ask a clarifying question",
  );
  assert.equal(
    describeSemanticClarificationCopy({
      semanticPolicy: {
        needsClarification: true,
        clarificationPrompt: "Which draft should I update?",
      },
    }),
    "Which draft should I update?",
  );
  assert.deepEqual(
    buildSemanticPolicyCopy({
      semanticPolicy: normalizeSemanticPolicy({
        semanticAction: "draft_in_whiteboard",
        needsClarification: false,
        reason: "",
      }),
      semanticFrame: { taskType: "drafting", targetSurface: "whiteboard" },
    }),
    {
      visible: true,
      actionLabel: "Draft in whiteboard",
      clarificationLabel: "No clarification needed.",
      summary: "Draft in whiteboard. No clarification needed.",
    },
  );

  assert.deepEqual(
    normalizeTurnPayload({
      semanticFrame: {
        userGoal: "Revise the pinned draft.",
        taskType: "revision",
        targetSurface: "whiteboard",
        needsClarification: true,
        clarificationPrompt: "Should I revise the pinned draft or current whiteboard?",
      },
      semanticPolicy: {
        actionKind: "clarify",
        shouldClarify: true,
      },
    }).semanticPolicy,
    {
      semanticAction: "clarify",
      actionLabel: "",
      needsClarification: true,
      clarificationPrompt: "Should I revise the pinned draft or current whiteboard?",
      clarificationOptions: [],
      status: "needs_clarification",
      reason: "",
      confidence: 0,
      blocking: true,
      signals: {},
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
      preserve_pinned_context: true,
      pinned_context_reason: "Keep the pinned draft in scope.",
    }),
    {
      mode: "chat",
      confidence: 0.92,
      reason: "Stayed in chat.",
      requestedWhiteboardMode: "auto",
      resolvedWhiteboardMode: "draft",
      whiteboardModeSource: "request",
      controlPanel: {
        actions: [],
        workingMemoryQueries: [],
        responseCall: null,
      },
      preservePinnedContext: true,
      pinnedContextReason: "Keep the pinned draft in scope.",
      preserveSelectedRecord: true,
      selectedRecordReason: "Keep the pinned draft in scope.",
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
      branch_index: [
        {
          workspace_id: "focused-mvp",
          title: "Focused MVP",
          label: "focused-mvp",
          summary: "Launch narrowly to learn quickly.",
        },
      ],
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
      branch_index: [
        {
          workspace_id: "focused-mvp",
          title: "Focused MVP",
          label: "focused-mvp",
          summary: "Launch narrowly to learn quickly.",
        },
      ],
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
  assert.deepEqual(scenarioLab.comparisonArtifact.branchIndex, [
    {
      workspace_id: "focused-mvp",
      workspaceId: "focused-mvp",
      title: "Focused MVP",
      label: "focused-mvp",
      summary: "Launch narrowly to learn quickly.",
    },
  ]);
  assert.equal(scenarioLab.branches[0].riskSummary, "Feedback could be skewed by the initial segment.");
  assert.deepEqual(scenarioLab.branches[0].sections.openQuestions.items, ["Which segment is most diagnostic?"]);
  assert.deepEqual(scenarioLab.comparisonArtifact.branchIndex, [
    {
      workspaceId: "focused-mvp",
      workspace_id: "focused-mvp",
      title: "Focused MVP",
      label: "focused-mvp",
      summary: "Launch narrowly to learn quickly.",
    },
  ]);
});

test("scenario lab branch index normalization falls back to branch cards and workspace ids without throwing", () => {
  assert.deepEqual(
    normalizeComparisonBranchIndex(
      [
        { workspace_id: "branch-a", title: "Branch A", summary: "First branch" },
        { workspaceId: "branch-b", label: "Branch B", card: "Second branch" },
      ],
      ["branch-c"],
    ),
    [
      { workspace_id: "branch-a", workspaceId: "branch-a", title: "Branch A", label: "", summary: "First branch" },
      { workspace_id: "branch-b", workspaceId: "branch-b", title: "", label: "Branch B", summary: "Second branch", card: "Second branch" },
    ],
  );

  assert.deepEqual(
    normalizeComparisonBranchIndex([], ["branch-c"]),
    [{ workspaceId: "branch-c", workspace_id: "branch-c" }],
  );
});

test("scenario lab payload normalization falls back to branch cards when the comparison hub has no branch index yet", () => {
  const scenarioLab = normalizeScenarioLabPayload({
    comparison_question: "Which launch path should we choose?",
    branches: [
      {
        workspace_id: "focused-mvp",
        title: "Focused MVP",
        label: "focused-mvp",
        card: "Launch narrowly to learn quickly.",
      },
    ],
    comparison_artifact: {
      id: "launch-comparison",
      title: "Launch Comparison",
      branch_workspace_ids: ["focused-mvp"],
      body: "# Launch Comparison\n\n## Recommendation\nStart with focused MVP.\n",
    },
  });

  assert.equal(scenarioLab.branchCount, 1);
  assert.equal(scenarioLab.comparisonArtifact.branchIndex.length, 1);
  assert.equal(scenarioLab.comparisonArtifact.branchIndex[0].workspaceId, "focused-mvp");
  assert.equal(scenarioLab.comparisonArtifact.branchIndex[0].workspace_id, "focused-mvp");
  assert.equal(scenarioLab.comparisonArtifact.branchIndex[0].title, "Focused MVP");
  assert.equal(scenarioLab.comparisonArtifact.branchIndex[0].label, "focused-mvp");
  assert.equal(scenarioLab.comparisonArtifact.branchIndex[0].summary, "Launch narrowly to learn quickly.");
});
