import {
  deriveWhiteboardDecisionPresentation,
  hasPendingWorkspaceDecision,
  isWhiteboardFocused,
  shouldHideChatWorkspaceUpdate,
  workspaceUpdateHasDraft,
} from "./whiteboard_decisions.mjs?v=20260421-scenario-fix";
import {
  buildInspectBuckets,
  buildMemoryTraceSummary,
  buildChatTurnEvidence,
  buildGuidedInspectionSummary,
  buildLearnedCorrectionModel,
  buildQuietActivityCopy,
  buildReasoningPathInspection,
  buildSemanticPolicyCopy,
  buildTurnAtAGlanceSummary,
  describeScenarioBranchConfidence,
  describeScenarioRouteConfidence,
  describeLearnedCorrectionModeLabel,
  describeLearnedScopeLabel,
  describeRecallReason,
  describeResponseModeLabel,
  deriveTurnGrounding,
  deriveWhiteboardLifecycle,
} from "./product_identity.mjs?v=20260426-protocol-editor";
import {
  buildWorkspaceContextPayload,
  resolveWhiteboardReopenTarget,
  shouldCarryPendingWorkspaceUpdate,
} from "./chat_request.mjs?v=20260421-deictic-reopen-fix";
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
} from "./surface_state.mjs?v=20260421-scenario-fix";
import {
  buildWorkspaceSnapshot,
  reconcileRestoredWorkspaceAfterLoad,
  shouldPreserveUnsavedWorkspace,
} from "./workspace_state.mjs?v=20260421-scenario-fix";
import {
  buildTurnPanelGroundingCopy,
} from "./turn_panel_grounding.mjs?v=20260421-scenario-fix";
import {
  normalizeLearnedItems,
  normalizeComparisonBranchIndex,
  normalizeProtocolMetadata,
  normalizeRecordId,
  normalizeResponseMode,
  normalizeScenarioLabPayload,
  normalizeSemanticFrame,
  normalizeTurnPayload,
  normalizeTurnInterpretation,
  normalizeSemanticPolicy,
  normalizeWorkspaceUpdate,
} from "./turn_payloads.mjs?v=20260426-protocol-editor";
import {
  deriveWhiteboardPreviewState,
  renderRichText,
} from "./math_render.mjs?v=20260421-calm-state-pass";

const shellEl = document.getElementById("shell");
const transcriptEl = document.getElementById("transcript");
const composerEl = document.getElementById("composer");
const messageInputEl = document.getElementById("messageInput");
const chatSurfaceTitleEl = document.getElementById("chatSurfaceTitle");
const chatSurfaceSubtitleEl = document.getElementById("chatSurfaceSubtitle");
const sendButtonEl = document.getElementById("sendButton");
const seedPromptEl = document.getElementById("seedPrompt");
const experimentToggleButtonEl = document.getElementById("experimentToggleButton");
const experimentBadgeEl = document.getElementById("experimentBadge");
const whiteboardToggleButtonEl = document.getElementById("whiteboardToggleButton");
const vantageToggleButtonEl = document.getElementById("vantageToggleButton");
const vantagePanelEl = document.getElementById("vantagePanel");
const closeVantageButtonEl = document.getElementById("closeVantageButton");
const vantageSummaryEl = document.getElementById("vantageSummary");
const chatPanelEl = document.querySelector(".chat-panel");
const workspaceDockEl = document.getElementById("workspaceDock");
const answerDockEl = document.getElementById("answerDock");
const scenarioDockEl = document.getElementById("scenarioDock");
const memoryDockEl = document.getElementById("memoryDock");
const SHOW_LIBRARY_DOCK = false;
const workspaceDockLabelEl = document.getElementById("workspaceDockLabel");
const answerDockLabelEl = document.getElementById("answerDockLabel");
const scenarioDockLabelEl = document.getElementById("scenarioDockLabel");
const memoryDockLabelEl = document.getElementById("memoryDockLabel");
const workspaceEditorEl = document.getElementById("workspaceEditor");
const workspaceTitleEl = document.getElementById("workspaceTitle");
const workspaceMetaEl = document.getElementById("workspaceMeta");
const workspacePreviewSectionEl = document.getElementById("workspacePreviewSection");
const workspacePreviewEl = document.getElementById("workspacePreview");
const workspaceArtifactPanelEl = document.getElementById("workspaceArtifactPanel");
const workspaceArtifactSummaryEl = document.getElementById("workspaceArtifactSummary");
const workspaceArtifactActionsEl = document.getElementById("workspaceArtifactActions");
const whiteboardDecisionPanelEl = document.getElementById("whiteboardDecisionPanel");
const whiteboardDecisionLabelEl = document.getElementById("whiteboardDecisionLabel");
const whiteboardDecisionSummaryEl = document.getElementById("whiteboardDecisionSummary");
const whiteboardDecisionActionsEl = document.getElementById("whiteboardDecisionActions");
const hideWhiteboardButtonEl = document.getElementById("hideWhiteboardButton");
const saveWorkspaceButtonEl = document.getElementById("saveWorkspaceButton");
const promoteWorkspaceButtonEl = document.getElementById("promoteWorkspaceButton");
const statusPillEl = document.getElementById("statusPill");
const turnTitleEl = document.getElementById("turnTitle");
const turnMetaEl = document.getElementById("turnMeta");
const turnIntentEl = document.getElementById("turnIntent");
const turnReasoningPathSectionEl = document.getElementById("turnReasoningPathSection");
const turnReasoningPathSummaryEl = document.getElementById("turnReasoningPathSummary");
const turnReasoningPathStateEl = document.getElementById("turnReasoningPathState");
const turnReasoningPathMetaEl = document.getElementById("turnReasoningPathMeta");
const turnReasoningPathRailEl = document.getElementById("turnReasoningPathRail");
const turnNoticeEl = document.getElementById("turnNotice");
const turnSummaryFactsEl = document.getElementById("turnSummaryFacts");
const turnWorkingMemorySummaryMetaEl = document.getElementById("turnWorkingMemorySummaryMeta");
const turnWorkingMemoryNoticeEl = document.getElementById("turnWorkingMemoryNotice");
const turnWorkingMemoryFactsEl = document.getElementById("turnWorkingMemoryFacts");
const turnTraceNoticeEl = document.getElementById("turnTraceNotice");
const workspaceUpdatePanelEl = document.getElementById("workspaceUpdatePanel");
const workspaceUpdateLabelEl = document.getElementById("workspaceUpdateLabel");
const workspaceUpdateSummaryEl = document.getElementById("workspaceUpdateSummary");
const workspaceUpdateActionsEl = document.getElementById("workspaceUpdateActions");
const scenarioLabSectionEl = document.getElementById("scenarioLabSection");
const quietActivityLineEl = document.getElementById("quietActivityLine");
const turnInspectBucketsEl = document.getElementById("turnInspectBuckets");
const turnWorkingMemoryListEl = document.getElementById("turnWorkingMemoryList");
const turnTraceListEl = document.getElementById("turnTraceList");
const turnLearnedListEl = document.getElementById("turnLearnedList");
const turnRecallSectionEl = document.getElementById("turnRecallSection");
const turnRecallSummaryMetaEl = document.getElementById("turnRecallSummaryMeta");
const turnTraceSectionEl = document.getElementById("turnTraceSection");
const turnTraceSummaryMetaEl = document.getElementById("turnTraceSummaryMeta");
const turnLearnedSectionEl = document.getElementById("turnLearnedSection");
const turnLearnedSummaryMetaEl = document.getElementById("turnLearnedSummaryMeta");
const turnLearnedCorrectionPanelEl = document.getElementById("turnLearnedCorrectionPanel");
const turnLearnedCorrectionMetaEl = document.getElementById("turnLearnedCorrectionMeta");
const turnLearnedCorrectionSummaryEl = document.getElementById("turnLearnedCorrectionSummary");
const turnLearnedCorrectionActionsEl = document.getElementById("turnLearnedCorrectionActions");
const memorySearchEl = document.getElementById("memorySearch");
const clearSearchButtonEl = document.getElementById("clearSearchButton");
const refreshConceptsButtonEl = document.getElementById("refreshConceptsButton");
const conceptsTitleEl = document.getElementById("conceptsTitle");
const conceptsCountEl = document.getElementById("conceptsCount");
const conceptsSummaryEl = document.getElementById("conceptsSummary");
const memoriesSummaryEl = document.getElementById("memoriesSummary");
const artifactsSummaryEl = document.getElementById("artifactsSummary");
const vaultNotesSummaryEl = document.getElementById("vaultNotesSummary");
const nextTurnContextStatusEl = document.getElementById("nextTurnContextStatus");
const pinSelectedContextButtonEl = document.getElementById("pinSelectedContextButton");
const clearPinnedContextButtonEl = document.getElementById("clearPinnedContextButton");
const conceptsHintEl = document.getElementById("conceptsHint");
const memoriesHintEl = document.getElementById("memoriesHint");
const artifactsHintEl = document.getElementById("artifactsHint");
const vaultNotesHintEl = document.getElementById("vaultNotesHint");
const conceptListEl = document.getElementById("conceptList");
const memoryListEl = document.getElementById("memoryList");
const artifactListEl = document.getElementById("artifactList");
const vaultNoteListEl = document.getElementById("vaultNoteList");
const conceptInspectorEl = document.getElementById("conceptInspector");
const noticeRailEl = document.getElementById("noticeRail");
const confirmOverlayEl = document.getElementById("confirmOverlay");
const confirmEyebrowEl = document.getElementById("confirmEyebrow");
const confirmTitleEl = document.getElementById("confirmTitle");
const confirmMessageEl = document.getElementById("confirmMessage");
const confirmCancelButtonEl = document.getElementById("confirmCancelButton");
const confirmAcceptButtonEl = document.getElementById("confirmAcceptButton");
const messageTemplate = document.getElementById("messageTemplate");

const samplePrompt = "A small team is preparing to launch a new software product with limited time and budget. Create three scenario branches: conservative rollout, focused MVP launch, and aggressive feature launch. Compare tradeoffs, risks, and next steps, then recommend one.";
const LEGACY_TURN_SNAPSHOT_KEY = "vantage-v5-turn-snapshot";
const TURN_SNAPSHOT_VERSION = 7;
const COMPOSER_WHITEBOARD_MODES = new Set(["auto", "offer"]);

let hasLoadedHealth = false;

function hasRealUserMessage() {
  if (state.history.some((turn) => String(turn?.user_message || "").trim())) {
    return true;
  }
  return Boolean(transcriptEl?.querySelector(".message.user"));
}

function createEmptyLearnedCorrectionState() {
  return {
    itemId: "",
    source: "",
    mode: "overview",
  };
}

const state = {
  busy: false,
  mode: "fallback",
  nexusEnabled: false,
  user: {
    id: "",
  },
  experiment: {
    active: false,
    sessionId: "",
    savedNoteCount: 0,
  },
  composer: {
    whiteboardMode: "auto",
  },
  surface: {
    current: "chat",
    returnSurface: "chat",
  },
  history: [],
  catalogConcepts: [],
  catalogSavedNotes: [],
  catalogVaultNotes: [],
  sessionConcepts: [],
  sessionSavedNotes: [],
  sessionVaultNotes: [],
  allConcepts: [],
  allSavedNotes: [],
  allVaultNotes: [],
  allMemoryItems: [],
  turnConcepts: [],
  turnSavedNotes: [],
  turnVaultNotes: [],
  turnWorkingMemory: [],
  turnTraceNotes: [],
  turnMemoryTraceRecord: null,
  turnLearned: [],
  learnedCorrection: createEmptyLearnedCorrectionState(),
  turnReasoningPathStageKey: "",
  turnReasoningPathExpanded: false,
  candidateConcepts: [],
  candidateSavedNotes: [],
  candidateTraceNotes: [],
  candidateVaultNotes: [],
  pinnedContext: null,
  selectedConceptId: "",
  selectedVaultNoteId: "",
  selectionOrigin: "bootstrap",
  memoryQuery: "",
  notice: null,
  noticeCounter: 0,
  noticeTimeoutId: null,
  confirmation: {
    resolve: null,
  },
  workspace: {
    workspaceId: "",
    scope: "durable",
    title: "Draft",
    content: "",
    savedContent: "",
    dirty: false,
    pinnedToChat: false,
    lifecycle: "ready",
    note: "Draft ready as a separate drafting surface.",
    latestArtifact: null,
  },
  bootRestore: {
    pending: false,
    scopeScopedFallback: false,
  },
  pendingWhiteboardDecision: null,
  turn: {
    userMessage: "",
    assistantMessage: "",
    mode: "idle",
    responseMode: {
      kind: "idle",
      label: "Idle",
      note: "Waiting for a turn.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: null,
      groundingSources: [],
      contextSources: [],
    },
    workspaceContextScope: "excluded",
    workspaceUpdate: null,
    vetting: null,
    metaAction: null,
    graphAction: null,
    scenarioLab: null,
    semanticFrame: null,
    semanticPolicy: null,
    systemState: null,
    activity: [],
    interpretation: null,
  },
};

function createIdleTurnState() {
  return {
    userMessage: "",
    assistantMessage: "",
    mode: "idle",
    responseMode: {
      kind: "idle",
      label: "Idle",
      note: "Waiting for a turn.",
      recallCount: 0,
      workingMemoryCount: 0,
      groundingMode: null,
      groundingSources: [],
      contextSources: [],
    },
    workspaceContextScope: "excluded",
    workspaceUpdate: null,
    vetting: null,
    graphAction: null,
    scenarioLab: null,
    scenarioBranchInspectionWorkspaceId: "",
    semanticFrame: null,
    semanticPolicy: null,
    systemState: null,
    activity: [],
    interpretation: null,
  };
}

function resetTransientExperimentUiState() {
  state.sessionConcepts = [];
  state.sessionSavedNotes = [];
  state.sessionVaultNotes = [];
  state.turnConcepts = [];
  state.turnSavedNotes = [];
  state.turnVaultNotes = [];
  state.turnWorkingMemory = [];
  state.turnTraceNotes = [];
  state.turnMemoryTraceRecord = null;
  state.turnLearned = [];
  state.learnedCorrection = createEmptyLearnedCorrectionState();
  state.turnReasoningPathStageKey = "";
  state.turnReasoningPathExpanded = false;
  state.candidateConcepts = [];
  state.candidateSavedNotes = [];
  state.candidateTraceNotes = [];
  state.candidateVaultNotes = [];
  state.pinnedContext = null;
  state.selectedConceptId = "";
  state.selectedVaultNoteId = "";
  state.selectionOrigin = "bootstrap";
  state.pendingWhiteboardDecision = null;
  state.bootRestore = {
    pending: false,
    scopeScopedFallback: false,
  };
  state.workspace.lifecycle = "ready";
  state.workspace.latestArtifact = null;
  state.turn = createIdleTurnState();
}

function currentTurnSnapshotKey() {
  return buildTurnSnapshotKey({
    scope: state.workspace.scope,
    experimentSessionId: state.experiment.sessionId || "",
    workspaceId: state.workspace.workspaceId,
  });
}

function currentScopedTurnSnapshotKey() {
  return buildScopedTurnSnapshotKey({
    scope: state.workspace.scope,
    experimentSessionId: state.experiment.sessionId || "",
  });
}

function clearTurnSnapshot() {
  try {
    sessionStorage.removeItem(currentTurnSnapshotKey());
    sessionStorage.removeItem(currentScopedTurnSnapshotKey());
    sessionStorage.removeItem(LEGACY_TURN_SNAPSHOT_KEY);
  } catch {
    // Ignore storage failures and keep the UI functional.
  }
}

function persistTurnSnapshot() {
  try {
    sessionStorage.setItem(
      currentTurnSnapshotKey(),
      JSON.stringify({
        version: TURN_SNAPSHOT_VERSION,
        scope: state.workspace.scope,
        workspaceId: state.workspace.workspaceId,
        experimentSessionId: state.experiment.sessionId || "",
        experimentActive: state.experiment.active === true,
        surface: state.surface,
        workspace: buildWorkspaceSnapshot(state.workspace),
        turn: state.turn,
        selectedConceptId: state.selectedConceptId,
        selectedVaultNoteId: state.selectedVaultNoteId,
        selectionOrigin: state.selectionOrigin,
        turnConcepts: state.turnConcepts,
        turnSavedNotes: state.turnSavedNotes,
        turnVaultNotes: state.turnVaultNotes,
        turnWorkingMemory: state.turnWorkingMemory,
        turnTraceNotes: state.turnTraceNotes,
        turnMemoryTraceRecord: state.turnMemoryTraceRecord,
        turnLearned: state.turnLearned,
        learnedCorrection: state.learnedCorrection,
        turnReasoningPathStageKey: state.turnReasoningPathStageKey,
        turnReasoningPathExpanded: state.turnReasoningPathExpanded,
        candidateConcepts: state.candidateConcepts,
        candidateSavedNotes: state.candidateSavedNotes,
        candidateTraceNotes: state.candidateTraceNotes,
        candidateVaultNotes: state.candidateVaultNotes,
        pinnedContext: state.pinnedContext,
      }),
    );
    sessionStorage.setItem(
      currentScopedTurnSnapshotKey(),
      JSON.stringify({
        version: TURN_SNAPSHOT_VERSION,
        scope: state.workspace.scope,
        workspaceId: state.workspace.workspaceId,
        experimentSessionId: state.experiment.sessionId || "",
        experimentActive: state.experiment.active === true,
        surface: state.surface,
        workspace: buildWorkspaceSnapshot(state.workspace),
        turn: state.turn,
        selectedConceptId: state.selectedConceptId,
        selectedVaultNoteId: state.selectedVaultNoteId,
        selectionOrigin: state.selectionOrigin,
        turnConcepts: state.turnConcepts,
        turnSavedNotes: state.turnSavedNotes,
        turnVaultNotes: state.turnVaultNotes,
        turnWorkingMemory: state.turnWorkingMemory,
        turnTraceNotes: state.turnTraceNotes,
        turnMemoryTraceRecord: state.turnMemoryTraceRecord,
        turnLearned: state.turnLearned,
        learnedCorrection: state.learnedCorrection,
        turnReasoningPathStageKey: state.turnReasoningPathStageKey,
        turnReasoningPathExpanded: state.turnReasoningPathExpanded,
        candidateConcepts: state.candidateConcepts,
        candidateSavedNotes: state.candidateSavedNotes,
        candidateTraceNotes: state.candidateTraceNotes,
        candidateVaultNotes: state.candidateVaultNotes,
        pinnedContext: state.pinnedContext,
      }),
    );
  } catch {
    // Ignore session storage failures and keep the UI functional.
  }
}

function restoreTurnSnapshot() {
  try {
    const rawWorkspaceScoped = sessionStorage.getItem(currentTurnSnapshotKey());
    const rawScopeScoped = sessionStorage.getItem(currentScopedTurnSnapshotKey());
    const raw = rawWorkspaceScoped
      || rawScopeScoped
      || sessionStorage.getItem(LEGACY_TURN_SNAPSHOT_KEY);
    if (!raw) {
      return;
    }
    const snapshot = JSON.parse(raw);
    const restoredFromScopeScopedKey = !rawWorkspaceScoped && raw === rawScopeScoped;
    if (snapshot.version !== TURN_SNAPSHOT_VERSION) {
      return;
    }
    const currentExperimentSessionId = state.experiment.sessionId || "";
    const currentExperimentActive = state.experiment.active === true;
    if (
      !snapshot
      || (snapshot.scope || state.workspace.scope) !== state.workspace.scope
      || (!restoredFromScopeScopedKey && snapshot.workspaceId !== state.workspace.workspaceId)
      || (snapshot.experimentSessionId || "") !== currentExperimentSessionId
      || (snapshot.experimentActive === true) !== currentExperimentActive
    ) {
      return;
    }
    const restoredTurnState = normalizeRestoredTurnSnapshotState(snapshot, {
      scopeScopedFallback: restoredFromScopeScopedKey,
    });
    state.surface = restoredTurnState.surface;
    if (snapshot.workspace && typeof snapshot.workspace === "object") {
      state.workspace = {
        ...state.workspace,
        ...buildWorkspaceSnapshot({
          ...state.workspace,
          ...snapshot.workspace,
        }),
      };
      workspaceTitleEl.textContent = state.workspace.title;
      workspaceEditorEl.value = state.workspace.content;
    }
    const restoredWorkspaceUpdate = normalizeWorkspaceUpdate(
      snapshot.turn?.workspaceUpdate,
      {
        workspace_id: snapshot.workspaceId,
        title: state.workspace.title,
        content: state.workspace.content,
      },
    );
    state.turn = {
      userMessage: snapshot.turn?.userMessage || "",
      assistantMessage: snapshot.turn?.assistantMessage || "",
      mode: snapshot.turn?.mode || "idle",
      responseMode: normalizeResponseMode(snapshot.turn?.responseMode, Array.isArray(snapshot.turnWorkingMemory) ? snapshot.turnWorkingMemory.length : 0),
      workspaceContextScope: restoredTurnState.workspaceContextScope,
      workspaceUpdate: restoredWorkspaceUpdate,
      vetting: snapshot.turn?.vetting || null,
      metaAction: snapshot.turn?.metaAction || null,
      graphAction: snapshot.turn?.graphAction || null,
      scenarioLab: snapshot.turn?.scenarioLab || null,
      semanticFrame: normalizeSemanticFrame(snapshot.turn?.semanticFrame || null),
      semanticPolicy: normalizeSemanticPolicy(snapshot.turn?.semanticPolicy || null, normalizeSemanticFrame(snapshot.turn?.semanticFrame || null)),
      systemState: snapshot.turn?.systemState || null,
      activity: Array.isArray(snapshot.turn?.activity) ? snapshot.turn.activity : [],
      scenarioBranchInspectionWorkspaceId: restoredFromScopeScopedKey
        ? ""
        : snapshot.turn?.scenarioBranchInspectionWorkspaceId || "",
      interpretation: normalizeTurnInterpretation(snapshot.turn?.interpretation || null),
    };
    state.selectedConceptId = restoredTurnState.selectedConceptId;
    state.selectedVaultNoteId = restoredTurnState.selectedVaultNoteId;
    state.selectionOrigin = restoredTurnState.selectionOrigin;
    state.turnConcepts = Array.isArray(snapshot.turnConcepts) ? snapshot.turnConcepts : [];
    state.turnSavedNotes = Array.isArray(snapshot.turnSavedNotes) ? snapshot.turnSavedNotes : [];
    state.turnVaultNotes = Array.isArray(snapshot.turnVaultNotes) ? snapshot.turnVaultNotes : [];
    state.turnWorkingMemory = Array.isArray(snapshot.turnWorkingMemory) ? snapshot.turnWorkingMemory : [];
    state.turnTraceNotes = Array.isArray(snapshot.turnTraceNotes) ? snapshot.turnTraceNotes : [];
    state.turnMemoryTraceRecord = snapshot.turnMemoryTraceRecord && typeof snapshot.turnMemoryTraceRecord === "object"
      ? snapshot.turnMemoryTraceRecord
      : null;
    state.turnLearned = Array.isArray(snapshot.turnLearned) ? snapshot.turnLearned : [];
    state.learnedCorrection = restoredFromScopeScopedKey
      ? createEmptyLearnedCorrectionState()
      : (snapshot.learnedCorrection && typeof snapshot.learnedCorrection === "object"
          ? {
            itemId: String(snapshot.learnedCorrection.itemId || "").trim(),
            source: String(snapshot.learnedCorrection.source || "").trim(),
            mode: String(snapshot.learnedCorrection.mode || "overview").trim() || "overview",
          }
          : createEmptyLearnedCorrectionState());
    state.turnReasoningPathStageKey = snapshot.turnReasoningPathStageKey || "";
    state.turnReasoningPathExpanded = snapshot.turnReasoningPathExpanded === true;
    state.candidateConcepts = Array.isArray(snapshot.candidateConcepts) ? snapshot.candidateConcepts : [];
    state.candidateSavedNotes = Array.isArray(snapshot.candidateSavedNotes) ? snapshot.candidateSavedNotes : [];
    state.candidateTraceNotes = Array.isArray(snapshot.candidateTraceNotes) ? snapshot.candidateTraceNotes : [];
    state.candidateVaultNotes = Array.isArray(snapshot.candidateVaultNotes) ? snapshot.candidateVaultNotes : [];
    state.pinnedContext = restoredTurnState.pinnedContext;
    state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.turnConcepts);
    state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.candidateConcepts);
    state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.turnSavedNotes);
    state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.candidateSavedNotes);
    state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.turnVaultNotes);
    state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.candidateVaultNotes);
    syncLearnedCorrectionState({ persist: false });
    rebuildConceptCatalog();
    state.bootRestore = {
      pending: true,
      scopeScopedFallback: restoredFromScopeScopedKey,
    };
  } catch {
    // Ignore invalid snapshots and let the current session rebuild the turn state.
  }
}

seedPromptEl.addEventListener("click", () => {
  messageInputEl.value = samplePrompt;
  messageInputEl.focus();
});

vantageToggleButtonEl.addEventListener("click", () => {
  if (normalizeSurfaceState(state.surface).current === "vantage") {
    closeVantage();
    return;
  }
  openVantage();
});

whiteboardToggleButtonEl.addEventListener("click", () => {
  state.surface = toggleWhiteboardSurface(state.surface);
  persistTurnSnapshot();
  renderViewState();
});

closeVantageButtonEl.addEventListener("click", () => {
  closeVantage();
});

if (turnReasoningPathSectionEl) {
  turnReasoningPathSectionEl.addEventListener("toggle", () => {
    const expanded = turnReasoningPathSectionEl.open === true;
    if (state.turnReasoningPathExpanded === expanded) {
      return;
    }
    state.turnReasoningPathExpanded = expanded;
    persistTurnSnapshot();
    renderTurnPanel();
  });
}

if (turnLearnedCorrectionPanelEl && turnLearnedCorrectionMetaEl) {
  turnLearnedCorrectionPanelEl.addEventListener("toggle", () => {
    if (turnLearnedCorrectionPanelEl.hidden) {
      turnLearnedCorrectionMetaEl.textContent = "Collapsed";
      return;
    }
    const activeMode = String(state.learnedCorrection?.mode || "overview").trim() || "overview";
    turnLearnedCorrectionMetaEl.textContent = turnLearnedCorrectionPanelEl.open
      ? (describeLearnedCorrectionModeLabel(activeMode, describeLearnedScopeLabel(getLearnedCorrectionItem()))
          || "Expanded")
      : "Collapsed";
  });
}

experimentToggleButtonEl.addEventListener("click", async () => {
  if (state.experiment.active) {
    await endExperiment();
    return;
  }
  await startExperiment();
});

confirmCancelButtonEl?.addEventListener("click", () => {
  resolveConfirmation(false);
});

confirmAcceptButtonEl?.addEventListener("click", () => {
  resolveConfirmation(true);
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && confirmOverlayEl && !confirmOverlayEl.hidden) {
    resolveConfirmation(false);
  }
});

composerEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInputEl.value.trim();
  if (!message || state.busy) {
    return;
  }
  messageInputEl.value = "";
  addMessage("user", message);
  await sendMessage(message);
});

workspaceEditorEl.addEventListener("input", () => {
  syncWorkspaceFromEditor();
});

saveWorkspaceButtonEl.addEventListener("click", async () => {
  await saveWorkspace();
});

promoteWorkspaceButtonEl.addEventListener("click", async () => {
  await promoteWorkspaceToConcept();
});

hideWhiteboardButtonEl.addEventListener("click", () => {
  hideWhiteboard();
});

pinSelectedContextButtonEl.addEventListener("click", () => {
  pinSelectedMemoryForNextTurn();
});

clearPinnedContextButtonEl.addEventListener("click", () => {
  clearPinnedContext();
});

memorySearchEl.addEventListener("input", () => {
  state.memoryQuery = memorySearchEl.value;
  renderMemoryPanel();
});

clearSearchButtonEl.addEventListener("click", () => {
  memorySearchEl.value = "";
  state.memoryQuery = "";
  renderMemoryPanel();
  pushNotice("Review cleared", "The full notes catalog is visible again.", "info");
});

refreshConceptsButtonEl.addEventListener("click", async () => {
  await loadConceptCatalog({ silent: false });
});

window.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !state.busy) {
    composerEl.requestSubmit();
  }
});

window.addEventListener("focus", () => {
  if (!state.busy) {
    void refreshRuntimeStatus({ refreshCatalog: false, preserveDirtyWorkspace: true });
  }
});

window.addEventListener("error", (event) => {
  const message = event?.error?.message || event?.message || "Unexpected startup error.";
  statusPillEl.textContent = "Error";
  pushNotice("UI error", message, "warning");
});

window.addEventListener("unhandledrejection", (event) => {
  const reason = event?.reason;
  const message = reason instanceof Error ? reason.message : String(reason || "Unexpected startup error.");
  statusPillEl.textContent = "Error";
  pushNotice("UI error", message, "warning");
});

void boot().catch((error) => {
  const message = error instanceof Error ? error.message : String(error || "Unexpected startup error.");
  statusPillEl.textContent = "Error";
  pushNotice("UI error", message, "warning");
  addMessage("system", `UI startup failed: ${message}`);
});

function buildDefaultSystemMessage() {
  const experimentLine = state.experiment.active
    ? "You're currently in experiment mode, so temporary notes stay in this session."
    : "You're currently in durable mode, so saved memories and work products can stay in your library.";
  return [
    "Hi, I'm Vantage.",
    "I help manage context so our work stays inspectable and reusable. Chat with me naturally, open Inspect when you want to see what shaped an answer, move work into Draft, save or publish useful work products, and ask me to use Scenario Lab when you want to compare branches or explore tradeoffs.",
    experimentLine,
    "Let me know if you have any questions about how the system works. Otherwise, let's get going.",
  ].join("\n\n");
}

async function boot() {
  await loadHealth();
  restoreTurnSnapshot();
  await loadWorkspace({ preserveDirty: true });
  await loadConceptCatalog({ silent: true });
  renderComposerMode();
  renderViewState();
  if (!transcriptEl.children.length) {
    addMessage("system", buildDefaultSystemMessage());
  }
  renderWorkspaceMeta();
  renderTurnPanel();
  renderMemoryPanel();
}

async function loadHealth() {
  try {
    const previousExperimentActive = state.experiment.active === true;
    const previousExperimentSessionId = state.experiment.sessionId || "";
    const { payload } = await fetchJson("/api/health");
    state.mode = payload?.mode === "openai" ? "openai" : "fallback";
    state.nexusEnabled = payload?.nexus_enabled === true;
    state.user.id = payload?.user?.id || "";
    state.experiment.active = payload?.experiment?.active === true;
    state.experiment.sessionId = payload?.experiment?.session_id || "";
    state.experiment.savedNoteCount = payload?.experiment?.saved_note_count || 0;
    const experimentChanged = hasLoadedHealth
      && (
        previousExperimentActive !== state.experiment.active
        || (state.experiment.active && previousExperimentSessionId !== (state.experiment.sessionId || ""))
      );
    hasLoadedHealth = true;
    if (experimentChanged) {
      resetTransientExperimentUiState();
      clearTurnSnapshot();
    }
    renderExperimentStatus({ nexusEnabled: state.nexusEnabled });
  } catch {
    state.mode = "offline";
    state.nexusEnabled = false;
    statusPillEl.textContent = "Offline";
    pushNotice("Backend offline", "The app could not reach the health endpoint.", "warning");
  }
}

async function loadWorkspace({ preserveDirty = false } = {}) {
  const bootRestore = state.bootRestore.pending
    ? { ...state.bootRestore }
    : null;
  state.bootRestore.pending = false;

  if (preserveDirty && state.workspace.dirty) {
    if (bootRestore) {
      const reconciliation = reconcileRestoredWorkspaceAfterLoad({
        currentWorkspace: state.workspace,
        incomingWorkspace: state.workspace,
        preserveDirty: true,
        scopeScopedFallback: bootRestore.scopeScopedFallback,
        surface: state.surface,
        selectedConceptId: state.selectedConceptId,
        selectedVaultNoteId: state.selectedVaultNoteId,
        selectionOrigin: state.selectionOrigin,
      });
      state.surface = reconciliation.surface;
      state.selectedConceptId = reconciliation.selectedConceptId;
      state.selectedVaultNoteId = reconciliation.selectedVaultNoteId;
      state.selectionOrigin = reconciliation.selectionOrigin;
      state.bootRestore = {
        pending: false,
        scopeScopedFallback: false,
      };
      state.workspace.note = "Kept the unsaved whiteboard draft in place.";
      persistTurnSnapshot();
      renderWorkspaceMeta();
      renderViewState();
      return;
    }
    state.workspace.note = "Kept the unsaved whiteboard draft in place.";
    persistTurnSnapshot();
    renderWorkspaceMeta();
    return;
  }
  try {
    const { payload } = await fetchJson("/api/workspace");
    const reconciliation = bootRestore
      ? reconcileRestoredWorkspaceAfterLoad({
          currentWorkspace: state.workspace,
          incomingWorkspace: payload || {},
          preserveDirty,
          scopeScopedFallback: bootRestore.scopeScopedFallback,
          surface: state.surface,
          selectedConceptId: state.selectedConceptId,
          selectedVaultNoteId: state.selectedVaultNoteId,
          selectionOrigin: state.selectionOrigin,
        })
      : null;
    const applied = applyWorkspacePayload(payload || {}, { preserveDirty });
    if (reconciliation) {
      state.surface = reconciliation.surface;
      state.selectedConceptId = reconciliation.selectedConceptId;
      state.selectedVaultNoteId = reconciliation.selectedVaultNoteId;
      state.selectionOrigin = reconciliation.selectionOrigin;
    }
    state.workspace.note = applied
      ? payload?.scope === "experiment"
        ? "Temporary experiment whiteboard loaded."
        : "Draft loaded from disk."
      : "Kept the unsaved whiteboard draft in place instead of replacing it with the last saved whiteboard.";
    persistTurnSnapshot();
  } catch (error) {
    state.workspace.note = error instanceof Error ? error.message : "Draft unavailable.";
    workspaceMetaEl.textContent = state.workspace.note;
    pushNotice("Draft unavailable", state.workspace.note, "warning");
  } finally {
    if (bootRestore) {
      state.bootRestore = {
        pending: false,
        scopeScopedFallback: false,
      };
    }
  }
  renderWorkspaceMeta();
  if (bootRestore) {
    renderViewState();
  }
}

async function refreshRuntimeStatus({ refreshCatalog = true, preserveDirtyWorkspace = false } = {}) {
  await loadHealth();
  await loadWorkspace({ preserveDirty: preserveDirtyWorkspace });
  if (refreshCatalog) {
    await loadConceptCatalog({ silent: true });
  }
}

async function startExperiment() {
  await loadHealth();
  if (state.experiment.active) {
    await Promise.allSettled([loadWorkspace(), loadConceptCatalog({ silent: true })]);
    pushNotice("Experiment already active", "This session is already in experiment mode.", "info");
    return;
  }
  const canProceed = await confirmExperimentTransition("start an experiment");
  if (!canProceed) {
    return;
  }
  setBusy(true);
  try {
    const { payload, response } = await fetchJson("/api/experiment/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed_from_workspace: false }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Experiment start failed with status ${response.status}`);
    }
    await refreshRuntimeStatus({ refreshCatalog: true });
    state.workspace.note = payload?.workspace?.scope === "experiment"
      ? "Temporary experiment whiteboard loaded."
      : "Experiment started.";
    renderExperimentStatus({ nexusEnabled: state.nexusEnabled });
    renderWorkspaceMeta();
    pushNotice("Experiment started", "Temporary notes created in this session will be discarded when the experiment ends.", "success");
  } catch (error) {
    pushNotice("Experiment unavailable", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

async function endExperiment() {
  await loadHealth();
  if (!state.experiment.active) {
    await loadWorkspace();
    pushNotice("No experiment active", "You are already in durable mode.", "info");
    return { ended: false, alreadyDurable: true };
  }
  const confirmed = await showConfirmationDialog({
    eyebrow: "Experiment mode",
    title: "End experiment mode?",
    message: "Temporary notes from this experiment will be discarded. Saved or published durable work products will remain available.",
    confirmLabel: "End experiment",
    cancelLabel: "Keep experiment",
  });
  if (!confirmed) {
    pushNotice("Experiment kept", "Experiment mode is still active.", "info");
    return { ended: false, cancelled: true };
  }
  const canProceed = await confirmExperimentTransition("end the experiment");
  if (!canProceed) {
    return { ended: false, blocked: true };
  }
  setBusy(true);
  try {
    const { payload, response } = await fetchJson("/api/experiment/end", { method: "POST" });
    if (!response.ok) {
      throw new Error(payload?.detail || `Experiment end failed with status ${response.status}`);
    }
    await refreshRuntimeStatus({ refreshCatalog: true });
    renderExperimentStatus({ nexusEnabled: state.nexusEnabled });
    pushNotice("Experiment ended", "Temporary notes were discarded and the app returned to durable mode.", "success");
    return { ended: true };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    pushNotice("Could not end experiment", message, "warning");
    return { ended: false, error: message };
  } finally {
    setBusy(false);
  }
}

function renderExperimentStatus({ nexusEnabled } = { nexusEnabled: false }) {
  const userPrefix = state.user.id ? `${state.user.id} · ` : "";
  if (state.mode === "offline") {
    statusPillEl.textContent = "Offline";
  } else if (state.experiment.active) {
    statusPillEl.textContent = `${userPrefix}Experiment mode`;
    experimentBadgeEl.textContent = `Experiment mode. Temporary notes stay in this session${state.experiment.savedNoteCount ? ` • ${state.experiment.savedNoteCount} temporary notes` : ""}.`;
  } else {
    statusPillEl.textContent = state.mode === "offline" ? "Offline" : `${userPrefix}Durable session`;
    experimentBadgeEl.textContent = "Durable by default. Use an experiment for temporary notes.";
  }
  experimentToggleButtonEl.disabled = state.busy;
  experimentToggleButtonEl.textContent = state.experiment.active ? "End experiment" : "Start experiment";
}

function openVantage({ focus = "turn" } = {}) {
  state.surface = openVantageSurface(state.surface);
  if (focus === "library") {
    memoryDockEl.open = true;
  } else if (focus === "scenario") {
    scenarioDockEl.open = true;
  } else {
    answerDockEl.open = true;
    if (state.turn.scenarioLab) {
      scenarioDockEl.open = true;
    }
  }
  persistTurnSnapshot();
  renderViewState();
}

function closeVantage() {
  state.surface = closeVantageSurface(state.surface);
  persistTurnSnapshot();
  renderViewState();
}

function revealWhiteboard() {
  state.surface = revealWhiteboardSurface(state.surface);
  persistTurnSnapshot();
  renderViewState();
}

function hideWhiteboard() {
  state.surface = hideWhiteboardSurface(state.surface);
  persistTurnSnapshot();
  renderViewState();
}

function renderViewState() {
  const surface = normalizeSurfaceState(state.surface);
  const vantageOpen = surface.current === "vantage";
  const whiteboardFocused = isWhiteboardFocused(surface);
  const whiteboardActive = hasWhiteboardActiveContext(surface);

  shellEl.classList.toggle("shell--vantage", vantageOpen);
  shellEl.classList.toggle("shell--whiteboard", whiteboardFocused);
  vantagePanelEl.hidden = !vantageOpen;
  workspaceDockEl.hidden = !whiteboardFocused;
  chatPanelEl?.classList.toggle("chat-panel--sidebar", whiteboardFocused);

  vantageToggleButtonEl.classList.toggle("is-active", vantageOpen);
  vantageToggleButtonEl.setAttribute("aria-pressed", vantageOpen.toString());
  vantageToggleButtonEl.textContent = vantageButtonLabel(surface);

  whiteboardToggleButtonEl.classList.toggle("is-active", whiteboardActive);
  whiteboardToggleButtonEl.setAttribute("aria-pressed", whiteboardActive.toString());
  whiteboardToggleButtonEl.textContent = whiteboardButtonLabel(surface);

  closeVantageButtonEl.textContent = surface.returnSurface === "whiteboard" ? "Back to draft" : "Back to chat";
  closeVantageButtonEl.disabled = state.busy;
  whiteboardToggleButtonEl.disabled = state.busy;
  hideWhiteboardButtonEl.disabled = state.busy;

  renderSurfaceStatus();
  renderWhiteboardDecisionPanel();
}

function setComposerWhiteboardMode(mode) {
  state.composer.whiteboardMode = COMPOSER_WHITEBOARD_MODES.has(mode) ? mode : "auto";
  renderComposerMode();
}

function renderComposerMode() {
  sendButtonEl.textContent = "Send";
}

function resetComposerWhiteboardMode() {
  setComposerWhiteboardMode("auto");
}

function renderSurfaceStatus() {
  if (vantageSummaryEl) {
    vantageSummaryEl.textContent = buildVantageSummary();
  }
  renderChatSurfaceCopy();
  renderWorkspacePreview();
}

function renderWorkspacePreview() {
  if (!workspacePreviewSectionEl || !workspacePreviewEl) {
    return;
  }
  const content = String(state.workspace.content || "");
  const previewState = deriveWhiteboardPreviewState(content);
  if (!previewState.visible) {
    workspacePreviewSectionEl.hidden = true;
    workspacePreviewEl.innerHTML = "";
    return;
  }
  workspacePreviewSectionEl.hidden = false;
  renderRichText(workspacePreviewEl, content, {
    emptyText: "A rendered preview will appear here when the draft includes math or code.",
  });
  workspacePreviewSectionEl.classList.toggle("whiteboard-preview--math", previewState.hasMath);
  workspacePreviewSectionEl.classList.toggle("whiteboard-preview--code", previewState.hasCode);
}

function buildVantageSummary() {
  const grounding = currentTurnGrounding();
  return `Start here: ${buildGuidedInspectionSummary({
    responseMode: grounding.responseMode,
    scenarioLab: state.turn.scenarioLab,
    recallCount: grounding.recallCount,
    learnedCount: grounding.learnedCount,
    libraryCount: state.allConcepts.length + state.allSavedNotes.length + state.allVaultNotes.length,
    includeLibrary: SHOW_LIBRARY_DOCK,
    pinnedTitle: getPinnedMemoryItem()?.title || "",
  })}`;
}

function currentTurnGrounding() {
  return deriveTurnGrounding({
    responseMode: state.turn.responseMode,
    recallItems: state.turnWorkingMemory,
    learnedItems: state.turnLearned,
  });
}

function renderChatSurfaceCopy() {
  const surface = normalizeSurfaceState(state.surface);
  const whiteboardFocused = isWhiteboardFocused(surface);

  if (chatSurfaceTitleEl) {
    chatSurfaceTitleEl.hidden = true;
    chatSurfaceTitleEl.textContent = whiteboardFocused ? "Chat" : "";
  }
  if (chatSurfaceSubtitleEl) {
    chatSurfaceSubtitleEl.hidden = true;
    chatSurfaceSubtitleEl.textContent = "";
  }
  if (experimentBadgeEl) {
    experimentBadgeEl.hidden = true;
  }
  if (messageInputEl) {
    messageInputEl.placeholder = whiteboardFocused
      ? "Ask about this draft..."
      : "Ask anything.";
  }
  seedPromptEl.hidden = whiteboardFocused || hasRealUserMessage();
  experimentToggleButtonEl.hidden = true;
  whiteboardToggleButtonEl.hidden = whiteboardFocused;
  statusPillEl.hidden = false;
  vantageToggleButtonEl.textContent = whiteboardFocused ? "Inspect" : vantageButtonLabel(surface);
}

function whiteboardButtonLabel(surface) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current === "whiteboard") {
    return "Close draft";
  }
  if (
    normalized.current === "vantage"
    && normalized.returnSurface === "whiteboard"
  ) {
    return "Back to draft";
  }
  const workspaceUpdate = state.turn.workspaceUpdate;
  if (workspaceUpdate?.status === "draft_ready") {
    return "Review draft";
  }
  if (workspaceUpdate?.status === "offered") {
    return workspaceUpdateHasDraft(workspaceUpdate) ? "Review draft" : "Open draft";
  }
  return "Draft";
}

function vantageButtonLabel(surface) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current !== "vantage") {
    return "Inspect";
  }
  return normalized.returnSurface === "whiteboard" ? "Back to draft" : "Close Inspect";
}

async function confirmExperimentTransition(actionLabel) {
  if (!state.workspace.dirty) {
    return true;
  }
  pushNotice("Saving whiteboard", `Saving the current whiteboard before you ${actionLabel}.`, "info");
  await saveWorkspace();
  if (state.workspace.dirty) {
    pushNotice("Draft still unsaved", `The draft could not be saved, so ${actionLabel} was cancelled.`, "warning");
    return false;
  }
  return true;
}

function showConfirmationDialog({
  eyebrow = "Confirm",
  title = "Confirm action",
  message = "This action needs confirmation.",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
} = {}) {
  if (
    !confirmOverlayEl
    || !confirmEyebrowEl
    || !confirmTitleEl
    || !confirmMessageEl
    || !confirmCancelButtonEl
    || !confirmAcceptButtonEl
  ) {
    return Promise.resolve(false);
  }

  if (state.confirmation.resolve) {
    resolveConfirmation(false);
  }

  confirmEyebrowEl.textContent = eyebrow;
  confirmTitleEl.textContent = title;
  confirmMessageEl.textContent = message;
  confirmCancelButtonEl.textContent = cancelLabel;
  confirmAcceptButtonEl.textContent = confirmLabel;
  confirmOverlayEl.hidden = false;

  return new Promise((resolve) => {
    state.confirmation.resolve = resolve;
    window.requestAnimationFrame(() => confirmCancelButtonEl.focus());
  });
}

function resolveConfirmation(value) {
  const resolve = state.confirmation.resolve;
  if (!resolve) {
    return;
  }
  state.confirmation.resolve = null;
  if (confirmOverlayEl) {
    confirmOverlayEl.hidden = true;
  }
  resolve(value);
}

function normalizeWorkspaceContinuityContent(value) {
  return String(value ?? "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.replace(/[ \t]+$/g, ""))
    .join("\n")
    .trim();
}

function applyWorkspacePayload(payload, { preserveDirty = false } = {}) {
  if (shouldPreserveUnsavedWorkspace({
    currentWorkspace: state.workspace,
    incomingWorkspace: payload,
    preserveDirty,
  })) {
    return false;
  }
  const currentWorkspaceId = state.workspace.workspaceId || "";
  const nextWorkspaceId = payload?.workspace_id || "";
  const currentWorkspaceScope = state.workspace.scope || "durable";
  const nextWorkspaceScope = payload?.scope || currentWorkspaceScope || "durable";
  const currentWorkspaceContent = normalizeWorkspaceContinuityContent(state.workspace.content || "");
  const nextWorkspaceContent = normalizeWorkspaceContinuityContent(payload?.content || "");
  const preserveLatestArtifact = Boolean(currentWorkspaceId)
    && nextWorkspaceId === currentWorkspaceId
    && nextWorkspaceScope === currentWorkspaceScope
    && nextWorkspaceContent === currentWorkspaceContent;
  state.workspace.workspaceId = payload?.workspace_id || "";
  state.workspace.scope = payload?.scope || state.workspace.scope || "durable";
  state.workspace.title = payload?.title || "Draft";
  state.workspace.content = payload?.content || "";
  state.workspace.savedContent = state.workspace.content;
  state.workspace.dirty = false;
  state.workspace.lifecycle = state.workspace.workspaceId ? "saved_whiteboard" : "ready";
  state.workspace.latestArtifact = preserveLatestArtifact ? state.workspace.latestArtifact : null;
  workspaceTitleEl.textContent = state.workspace.title;
  workspaceEditorEl.value = state.workspace.content;
  return true;
}

async function loadConceptCatalog({ silent = false } = {}) {
  try {
    const [{ payload: memoryPayload }, { payload: conceptPayload }] = await Promise.all([
      fetchJson("/api/memory"),
      fetchJson("/api/concepts"),
    ]);
    const normalizedMemory = normalizeMemoryPayload(memoryPayload, "catalog");
    state.catalogConcepts = normalizeConceptList(conceptPayload?.concepts || [], "concept");
    state.catalogSavedNotes = normalizedMemory.savedNotes;
    state.catalogVaultNotes = normalizedMemory.referenceNotes;
    rebuildConceptCatalog();
    const selectedConcept = state.selectedConceptId ? getConceptById(state.selectedConceptId) : null;
    const selectedVaultNote = state.selectedVaultNoteId ? getVaultNoteById(state.selectedVaultNoteId) : null;
    if (state.selectedConceptId && !selectedConcept) {
      state.selectedConceptId = "";
      state.selectionOrigin = "bootstrap";
    }
    if (state.selectedVaultNoteId && !selectedVaultNote) {
      state.selectedVaultNoteId = "";
      state.selectionOrigin = "bootstrap";
    }
    prunePinnedContextIfMissing();
    renderMemoryPanel();
    if (!silent) {
      pushNotice(
        "Notes refreshed",
        `${state.allConcepts.length} concepts, ${state.allSavedNotes.length} durable notes, and ${state.allVaultNotes.length} reference notes are available.`,
        "success",
      );
    }
  } catch (error) {
    if (!silent) {
      pushNotice(
        "Notes unavailable",
        error instanceof Error ? error.message : "Could not load concepts, durable notes, and reference notes.",
        "warning",
      );
    }
  }
}

async function sendMessage(message) {
  setBusy(true);
  try {
    if (await handleLocalExperimentModeMessage(message)) {
      return;
    }
    const pinnedContextId = getPinnedContextIdForChat();
    const whiteboardReopenTarget = resolveWhiteboardReopenTarget({
      message,
      pinnedItem: getPinnedMemoryItem(),
      recalledItems: state.turnWorkingMemory,
      learnedItems: state.turnLearned,
    });
    if (whiteboardReopenTarget) {
      await handleDeicticWhiteboardReopen({
        target: whiteboardReopenTarget,
        message,
      });
      return;
    }
    const workspaceContext = buildWorkspaceContextPayload({
      surface: state.surface,
      workspace: state.workspace,
      workspacePinned: state.workspace.pinnedToChat,
      message,
    });
    const { payload, response } = await fetchJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: state.history,
        ...workspaceContext,
        whiteboard_mode: state.composer.whiteboardMode,
        pinned_context_id: pinnedContextId,
        pending_workspace_update: buildPendingWorkspaceContext(message),
      }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Chat failed with status ${response.status}`);
    }
    const normalizedTurnPayload = normalizeTurnPayload(payload || {});
    addMessage("assistant", payload?.assistant_message || "(No assistant response.)", {
      evidence: buildChatTurnEvidence(payload || {}),
      scenarioLab: normalizedTurnPayload.scenarioLab,
    });
    state.history.push({
      user_message: payload?.user_message || message,
      assistant_message: payload?.assistant_message || "",
    });
    applyChatPayload(payload || {});
    absorbGraphNotices(payload || {});
  } catch (error) {
    addMessage("system", error instanceof Error ? error.message : String(error));
    pushNotice("Chat failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setComposerWhiteboardMode("auto");
    setBusy(false);
  }
}

async function handleLocalExperimentModeMessage(message) {
  const normalized = normalizeUserText(message);
  if (!normalized.includes("experiment mode") && !normalized.includes("experiment")) {
    return false;
  }
  const asksAboutSwitching = /\b(can|could|how|what|where|is there|do i)\b/.test(normalized)
    && /\b(switch|exit|leave|end|turn off|durable mode)\b/.test(normalized);
  const asksToEnd = /\b(end|exit|leave|switch out of|turn off|stop)\b/.test(normalized)
    && /\bexperiment(?: mode)?\b/.test(normalized);
  const isQuestion = /^(can|could|how|what|where|is|do|does|should|would)\b/.test(normalized)
    || String(message || "").includes("?");
  if (!asksAboutSwitching && !asksToEnd) {
    return false;
  }

  if (asksAboutSwitching || isQuestion) {
    const response = state.experiment.active
      ? "Yes. You're currently in experiment mode. I can switch you back to durable mode, but ending the experiment discards temporary notes from this session. If you want to do that, say `end experiment mode` and I'll confirm before switching."
      : "You're already in durable mode. Saved memories and work products can stay available across sessions.";
    addMessage("assistant", response);
    state.history.push({
      user_message: message,
      assistant_message: response,
    });
    state.turn = createLocalExperimentTurnState({ message, response });
    renderTurnPanel();
    return true;
  }

  if (!state.experiment.active) {
    const response = "You're already in durable mode. There isn't an active experiment to end.";
    addMessage("assistant", response);
    state.history.push({
      user_message: message,
      assistant_message: response,
    });
    state.turn = createLocalExperimentTurnState({ message, response });
    renderTurnPanel();
    return true;
  }

  const outcome = await endExperiment();
  const response = experimentEndChatResponse(outcome);
  addMessage("assistant", response);
  state.history.push({
    user_message: message,
    assistant_message: response,
  });
  state.turn = createLocalExperimentTurnState({ message, response });
  renderTurnPanel();
  return true;
}

function createLocalExperimentTurnState({ message = "", response = "" } = {}) {
  return {
    ...createIdleTurnState(),
    userMessage: message,
    assistantMessage: response,
    mode: "local_action",
    semanticFrame: {
      userGoal: "Manage the current experiment session.",
      taskType: "experiment_management",
      followUpType: "new_request",
      targetSurface: "experiment",
      referencedObject: null,
      confidence: 0.92,
      needsClarification: false,
      clarificationPrompt: null,
      signals: { local_handler: true },
      commitments: ["Keep experiment-mode behavior explicit."],
    },
    semanticPolicy: {
      semanticAction: "experiment_manage",
      actionLabel: "Manage experiment",
      needsClarification: false,
      clarificationPrompt: null,
      clarificationOptions: [],
      status: "ready",
      reason: "Handled locally so experiment mode stays understandable.",
      confidence: 0.92,
      blocking: false,
      signals: { local_handler: true },
    },
  };
}

function experimentEndChatResponse(outcome = {}) {
  if (outcome.ended) {
    return "You're now back in durable mode. Temporary notes from the experiment were discarded.";
  }
  if (outcome.alreadyDurable) {
    return "You're already in durable mode. There isn't an active experiment to end.";
  }
  if (outcome.cancelled) {
    return "I didn't end experiment mode because the confirmation was cancelled. Experiment mode is still active.";
  }
  if (outcome.blocked) {
    return "I didn't end experiment mode because the current whiteboard could not be saved first. Experiment mode is still active.";
  }
  if (outcome.error) {
    return `I couldn't end experiment mode: ${outcome.error}`;
  }
  return state.experiment.active
    ? "I didn't end experiment mode. Experiment mode is still active."
    : "You're now back in durable mode. Temporary notes from the experiment were discarded.";
}

function normalizeUserText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}\s']/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function ensureReopenTargetAvailable(target) {
  if (!target?.id || getConceptById(target.id)) {
    return;
  }
  if (String(target.source || "").trim().toLowerCase() === "concept") {
    upsertSessionConcept(target);
    return;
  }
  upsertSessionSavedNote(target);
}

function recordLocalWhiteboardReopenTurn({ message, assistantMessage, target, queued = false } = {}) {
  const normalizedTarget = normalizeMemoryItem(target, "turn-recall");
  state.turn = {
    ...createIdleTurnState(),
    userMessage: message || "",
    assistantMessage: assistantMessage || "",
    mode: "local_action",
    responseMode: normalizeResponseMode(
      {
        kind: "grounded",
        label: queued ? "Recall" : "Recall + Whiteboard",
        note: queued
          ? "Supported by the recalled item while the whiteboard replacement waits for your decision."
          : "Supported by the recalled item and the reopened whiteboard.",
        grounding_mode: queued ? "recall" : "mixed_context",
        grounding_sources: queued ? ["recall"] : ["recall", "whiteboard"],
        context_sources: queued ? ["recall"] : ["recall", "whiteboard"],
        recall_count: normalizedTarget.id ? 1 : 0,
        working_memory_count: normalizedTarget.id ? 1 : 0,
      },
      normalizedTarget.id ? 1 : 0,
    ),
    workspaceContextScope: queued ? "excluded" : "requested",
    workspaceUpdate: null,
    vetting: null,
    graphAction: queued
      ? null
      : {
          type: "open_saved_item_into_workspace",
          record_id: normalizedTarget.id,
          record_title: normalizedTarget.title,
          source: normalizedTarget.source,
        },
    scenarioLab: null,
    scenarioBranchInspectionWorkspaceId: "",
    interpretation: normalizeTurnInterpretation(
      queued
        ? {
            mode: "chat",
            confidence: 1,
            reason: "The message referred to the previously recalled item, but reopening it would replace the current unsaved whiteboard, so a replace-or-keep decision was queued instead.",
            requested_whiteboard_mode: "auto",
            resolved_whiteboard_mode: "draft",
            whiteboard_mode_source: "request",
          }
        : {
            mode: "chat",
            confidence: 1,
            reason: "The message explicitly asked to pull the previously recalled item into the whiteboard, so the client reopened that saved item directly.",
            requested_whiteboard_mode: "auto",
            resolved_whiteboard_mode: "draft",
            whiteboard_mode_source: "request",
          },
    ),
  };
  state.turnReasoningPathStageKey = "";
  state.turnReasoningPathExpanded = false;
  state.turnWorkingMemory = normalizedTarget.id ? [normalizedTarget] : [];
  state.turnTraceNotes = [];
  state.turnMemoryTraceRecord = null;
  state.turnLearned = [];
  state.learnedCorrection = createEmptyLearnedCorrectionState();
  state.candidateConcepts = [];
  state.candidateSavedNotes = [];
  state.candidateTraceNotes = [];
  state.candidateVaultNotes = [];
  state.turnConcepts = [];
  state.turnSavedNotes = [];
  state.turnVaultNotes = [];
  if (normalizedTarget.id) {
    selectConcept(normalizedTarget.id, { silent: true, source: "user" });
  }
  persistTurnSnapshot();
  renderTurnPanel();
  renderMemoryPanel();
}

async function handleDeicticWhiteboardReopen({ target, message } = {}) {
  ensureReopenTargetAvailable(target);
  const status = await openConceptIntoWorkspace(target?.id);
  if (status !== "opened" && status !== "queued") {
    return;
  }
  const assistantMessage = status === "queued"
    ? `I found ${target.title}. Opening it would replace the current whiteboard, so I left a replace-or-keep decision for you.`
    : `I pulled ${target.title} into the whiteboard so we can continue from that saved draft.`;
  addMessage("assistant", assistantMessage, {
    evidence: [
      {
        label: status === "queued" ? "Whiteboard decision" : "Opened in whiteboard",
        tone: "soft",
      },
    ],
  });
  state.history.push({
    user_message: message || "",
    assistant_message: assistantMessage,
  });
  recordLocalWhiteboardReopenTurn({
    message,
    assistantMessage,
    target,
    queued: status === "queued",
  });
}

function applyChatPayload(payload) {
  const candidateMemory = normalizeMemoryPayload(payload.candidate_memory, "turn-candidate");
  const turnMemory = normalizeMemoryPayload(payload.memory, "turn");
  const normalizedTurnPayload = normalizeTurnPayload(payload || {});
  const recallItems = normalizeWorkingMemoryItems(
    normalizedTurnPayload.recallItems,
    "turn-recall",
  );
  const workspaceUpdate = normalizedTurnPayload.workspaceUpdate;
  const learnedItems = normalizeWorkingMemoryItems(
    normalizedTurnPayload.learnedItems,
    "turn-learned",
  );
  state.pendingWhiteboardDecision = null;
  state.turn = {
    userMessage: payload.user_message || "",
    assistantMessage: payload.assistant_message || "",
    mode: payload.mode || "chat",
    responseMode: normalizedTurnPayload.responseMode,
    workspaceContextScope: normalizedTurnPayload.workspaceContextScope,
    workspaceUpdate: normalizedTurnPayload.workspaceUpdate,
    vetting: payload.vetting || null,
    metaAction: payload.meta_action || null,
    graphAction: payload.graph_action || null,
    scenarioLab: normalizedTurnPayload.scenarioLab,
    semanticFrame: normalizedTurnPayload.semanticFrame,
    semanticPolicy: normalizedTurnPayload.semanticPolicy,
    systemState: normalizedTurnPayload.systemState,
    activity: normalizedTurnPayload.activity,
    scenarioBranchInspectionWorkspaceId: "",
    interpretation: normalizeTurnInterpretation(payload.turn_interpretation),
  };
  state.turnReasoningPathStageKey = "";
  state.turnReasoningPathExpanded = false;
  state.candidateConcepts = normalizeConceptList(payload.candidate_concepts || [], "concept");
  state.candidateSavedNotes = candidateMemory.savedNotes;
  state.candidateTraceNotes = normalizeWorkingMemoryItems(payload.candidate_trace_notes || [], "candidate-trace");
  state.candidateVaultNotes = candidateMemory.referenceNotes;
  state.turnConcepts = normalizeConceptList(payload.concept_cards || [], "concept");
  state.turnSavedNotes = turnMemory.savedNotes;
  state.turnVaultNotes = turnMemory.referenceNotes;
  state.turnWorkingMemory = recallItems;
  state.turnTraceNotes = normalizeWorkingMemoryItems(payload.trace_notes || [], "turn-trace");
  state.turnMemoryTraceRecord = normalizedTurnPayload.memoryTraceRecord
    ? normalizeMemoryItem(normalizedTurnPayload.memoryTraceRecord, "turn-trace-record")
    : null;
  state.turnLearned = learnedItems;
  syncLearnedCorrectionState({ persist: false });
  state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.turnConcepts);
  state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.candidateConcepts);
  state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.turnSavedNotes);
  state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.candidateSavedNotes);
  state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.turnVaultNotes);
  state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.candidateVaultNotes);
  rebuildConceptCatalog();
  prunePinnedContextIfMissing();

  const autoAppliedWorkspaceDraft = shouldAutoApplyWorkspaceDraft(workspaceUpdate, state.turn.interpretation)
    ? autoApplyWorkspaceDraft(workspaceUpdate)
    : false;
  const shouldDeferWorkspaceDraft = hasPendingWorkspaceDecision(workspaceUpdate) && !autoAppliedWorkspaceDraft;
  const shouldSyncReturnedWorkspacePayload = !shouldDeferWorkspaceDraft && !autoAppliedWorkspaceDraft;

  if (shouldSyncReturnedWorkspacePayload && payload.workspace?.title) {
    state.workspace.title = payload.workspace.title;
    workspaceTitleEl.textContent = state.workspace.title;
  }

  if (shouldSyncReturnedWorkspacePayload && payload.workspace?.workspace_id) {
    state.workspace.workspaceId = payload.workspace.workspace_id;
  }

  if (shouldSyncReturnedWorkspacePayload && typeof payload.workspace?.content === "string") {
    state.workspace.content = payload.workspace.content;
    state.workspace.savedContent = payload.workspace.content;
    state.workspace.dirty = false;
    state.workspace.lifecycle = state.workspace.workspaceId ? "saved_whiteboard" : "ready";
    workspaceEditorEl.value = payload.workspace.content;
  }

  if (payload.mode === "scenario_lab") {
    const branchCount = scenarioLabBranchCount(payload.scenario_lab);
    state.workspace.note = buildScenarioLabOutcomeCopy(branchCount, hasScenarioComparisonArtifact(payload.scenario_lab));
    answerDockEl.open = true;
    scenarioDockEl.open = true;
  } else {
    if (!autoAppliedWorkspaceDraft) {
      state.workspace.note = buildWorkspaceNote(payload);
    }
    if (workspaceUpdate?.status === "updated" || autoAppliedWorkspaceDraft) {
      state.workspace.lifecycle = "transient_draft";
      revealWhiteboard();
    }
    if (hasPendingWorkspaceDecision(workspaceUpdate) && !autoAppliedWorkspaceDraft) {
      answerDockEl.open = true;
    }
  }

  persistTurnSnapshot();
  renderWorkspaceMeta();
  renderTurnPanel();
  renderMemoryPanel();
}

function absorbGraphNotices(payload) {
  const notices = [];
  if (payload?.scenario_lab?.status === "failed") {
    const errorMessage = payload.scenario_lab?.error?.message || "Scenario Lab could not complete this turn.";
    notices.push({
      title: "Scenario Lab fallback",
      message: `${errorMessage} The answer stayed in chat instead.`,
      tone: "warning",
    });
  }
  if (typeof payload.notice === "string" && payload.notice.trim()) {
    notices.push({ title: "Update", message: payload.notice, tone: "info" });
  }
  if (Array.isArray(payload.notifications)) {
    for (const note of payload.notifications) {
      if (typeof note === "string") {
        notices.push({ title: "Update", message: note, tone: "info" });
      } else if (note && typeof note === "object") {
        notices.push({
          title: note.title || "Update",
          message: note.message || note.detail || "Graph update received.",
          tone: note.tone || "info",
        });
      }
    }
  }
  const createdRecord = normalizeLearnedItems(payload)[0] || null;
  if (createdRecord) {
    const isConcept = String(createdRecord.source || createdRecord.kind || createdRecord.type || "").toLowerCase() === "concept";
    const savedItem = isConcept
      ? normalizeConcept(createdRecord, "session")
      : normalizeMemoryItem(createdRecord, "session");
    if (savedItem.id) {
      if (isConcept) {
        upsertSessionConcept(savedItem);
      } else {
        upsertSessionSavedNote(savedItem);
      }
      rebuildConceptCatalog();
      renderMemoryPanel();
    }
  }
  const primaryNotice = notices.find((note) => note.tone === "warning")
    || notices.find((note) => note.tone === "success")
    || notices[0];
  if (primaryNotice) {
    pushNotice(primaryNotice.title, primaryNotice.message, primaryNotice.tone);
  }
}

async function saveWorkspace() {
  setBusy(true);
  try {
    const content = workspaceEditorEl.value;
    const { payload, response } = await fetchJson("/api/workspace", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        workspace_id: state.workspace.workspaceId || null,
      }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Save failed with status ${response.status}`);
    }
    state.workspace.workspaceId = payload?.workspace_id || state.workspace.workspaceId;
    state.workspace.title = payload?.title || state.workspace.title;
    state.workspace.content = payload?.content || content;
    state.workspace.savedContent = state.workspace.content;
    state.workspace.dirty = false;
    state.workspace.lifecycle = "saved_whiteboard";
    state.workspace.note = "Saved to the whiteboard library.";
    state.workspace.latestArtifact = payload?.artifact_snapshot
      ? normalizeMemoryItem(payload.artifact_snapshot, "session")
      : state.workspace.latestArtifact;
    workspaceTitleEl.textContent = state.workspace.title;
    persistTurnSnapshot();
    renderWorkspaceMeta();
    pushNotice("Draft saved", `${state.workspace.title} was written to disk.`, "success");
    if (payload?.artifact_snapshot) {
      const snapshot = state.workspace.latestArtifact;
      if (snapshot.id) {
        upsertSessionSavedNote(snapshot);
        rebuildConceptCatalog();
        renderMemoryPanel();
      }
    }
    if (payload?.graph_action) {
      pushNotice("Work product iteration saved", describeGraphAction(payload.graph_action), "success");
    }
  } catch (error) {
    pushNotice("Save failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

async function promoteWorkspaceToConcept() {
  const content = workspaceEditorEl.value.trim();
  if (!content) {
    pushNotice("Nothing to promote", "Write something in the workspace first.", "warning");
    return;
  }
  setBusy(true);
  try {
    const title = state.workspace.title || inferWorkspaceTitle(content);
    const { payload, response } = await fetchJson("/api/concepts/promote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_id: state.workspace.workspaceId,
        title,
        content,
      }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Promotion failed with status ${response.status}`);
    }

    const promoted = payload.promoted_record || payload.promoted_concept;
    const isConcept = String(promoted?.source || promoted?.kind || promoted?.type || "").toLowerCase() === "concept";
    const savedItem = isConcept ? normalizeConcept(promoted, "session") : normalizeMemoryItem(promoted, "session");
    if (savedItem.id) {
      if (isConcept) {
        upsertSessionConcept(savedItem);
      } else {
        upsertSessionSavedNote(savedItem);
      }
      rebuildConceptCatalog();
      selectConcept(savedItem.id, { silent: true });
      state.workspace.lifecycle = isConcept ? state.workspace.lifecycle : "promoted_artifact";
      if (!isConcept) {
        state.workspace.latestArtifact = savedItem;
      }
      state.workspace.note = isConcept
        ? `Concept preview: ${savedItem.title}.`
        : `Promoted artifact: ${savedItem.title}.`;
      renderWorkspaceMeta();
      renderMemoryPanel();
      pushNotice(isConcept ? "Concept added" : "Artifact added", `${savedItem.title} was promoted from the workspace.`, "success");
      openVantage({ focus: "library" });
      memoryDockEl.open = true;
      return;
    }

    const stagedConcept = buildLocalConceptFromWorkspace(content, title);
    upsertSessionConcept(stagedConcept);
    rebuildConceptCatalog();
    selectConcept(stagedConcept.id, { silent: true });
    state.workspace.note = `Promoted concept preview: ${stagedConcept.title}.`;
    renderWorkspaceMeta();
    renderMemoryPanel();
    pushNotice("Concept preview", `${stagedConcept.title} was staged in the memory panel.`, "success");
    openVantage({ focus: "library" });
    memoryDockEl.open = true;
  } catch (error) {
    pushNotice("Promotion failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

function queueWhiteboardDecision(decision) {
  state.pendingWhiteboardDecision = decision;
  revealWhiteboard();
  renderWorkspaceMeta();
  renderTurnPanel();
}

function clearWhiteboardDecision({ notice = null } = {}) {
  state.pendingWhiteboardDecision = null;
  renderWorkspaceMeta();
  renderTurnPanel();
  if (notice) {
    pushNotice(notice.title, notice.message, notice.tone);
  }
}

async function handleWhiteboardDecisionAction(actionId) {
  const localDecision = state.pendingWhiteboardDecision;
  if (localDecision) {
    if (actionId === "cancel_decision") {
      clearWhiteboardDecision({
        notice: {
          title: "Draft unchanged",
          message: "The current whiteboard was kept as-is.",
          tone: "info",
        },
      });
      return;
    }
    if (localDecision.kind === "open_record") {
      await performOpenConceptIntoWorkspace(localDecision.targetId);
      return;
    }
    if (localDecision.kind === "open_workspace") {
      await performOpenWorkspace(localDecision.targetId);
      return;
    }
    if (localDecision.kind === "pending_draft_replace") {
      if (actionId === "append_instead") {
        await applyPendingWorkspaceUpdate("append", { bypassDirtyCheck: true });
        return;
      }
      await applyPendingWorkspaceUpdate("replace", { bypassDirtyCheck: true });
      return;
    }
  }

  if (actionId === "open_offer") {
    await resolveWorkspaceOffer();
    return;
  }
  if (actionId === "keep_in_chat") {
    dismissWorkspaceUpdate("kept_in_chat", {
      title: "Kept in chat",
      message: "The current turn stayed in chat and the whiteboard was left unchanged.",
      tone: "info",
    });
    return;
  }
  if (actionId === "apply_draft") {
    await applyPendingWorkspaceUpdate("replace");
    return;
  }
  if (actionId === "append_draft") {
    await applyPendingWorkspaceUpdate("append");
    return;
  }
  if (actionId === "keep_current") {
    dismissWorkspaceUpdate("kept_current", {
      title: "Draft unchanged",
      message: "The pending draft was left in review and the current whiteboard was kept as-is.",
      tone: "info",
    });
  }
}

async function openConceptIntoWorkspace(conceptId) {
  const concept = getConceptById(conceptId);
  if (!concept) {
    pushNotice("Item unavailable", "That concept, memory, or artifact is not in the local catalog.", "warning");
    return "missing";
  }
  if (state.workspace.dirty) {
    queueWhiteboardDecision({
      kind: "open_record",
      targetId: concept.id,
      targetLabel: concept.title,
      targetTypeLabel: concept.type === "concept" ? "concept" : itemInspectorLabel(concept).toLowerCase(),
    });
    return "queued";
  }
  return await performOpenConceptIntoWorkspace(conceptId);
}

async function performOpenConceptIntoWorkspace(conceptId) {
  const concept = getConceptById(conceptId);
  if (!concept) {
    pushNotice("Item unavailable", "That concept, memory, or artifact is not in the local catalog.", "warning");
    return "missing";
  }
  setBusy(true);
  try {
    const { payload, response } = await fetchJson("/api/concepts/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ record_id: concept.id }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Open failed with status ${response.status}`);
    }

    if (typeof payload.content === "string") {
      state.workspace.workspaceId = payload.workspace_id || concept.id;
      applyWorkspaceDraft(payload.content, payload.title || concept.title, {
        note: `Started from saved material: ${concept.title}.`,
        markDirty: false,
      });
      persistTurnSnapshot();
      pushNotice("Draft opened", `${concept.title} was loaded into the draft surface.`, "success");
      clearWhiteboardDecision();
      revealWhiteboard();
      return "opened";
    }

    const draft = buildConceptWorkspaceDraft(concept);
    applyWorkspaceDraft(draft, concept.title, {
      note: `Started a new draft from ${concept.title}. Save when you're ready.`,
      markDirty: true,
    });
    persistTurnSnapshot();
    pushNotice("Draft opened", `${concept.title} is now in the draft surface.`, "success");
    clearWhiteboardDecision();
    revealWhiteboard();
    return "opened";
  } catch (error) {
    pushNotice("Open failed", error instanceof Error ? error.message : String(error), "warning");
    return "failed";
  } finally {
    setBusy(false);
  }
}

async function openWorkspace(workspaceId) {
  if (!workspaceId) {
    pushNotice("Draft unavailable", "That scenario branch does not have a draft id.", "warning");
    return;
  }
  if (state.workspace.dirty) {
    queueWhiteboardDecision({
      kind: "open_workspace",
      targetId: workspaceId,
      targetLabel: workspaceId,
    });
    return;
  }
  await performOpenWorkspace(workspaceId);
}

async function performOpenWorkspace(workspaceId) {
  setBusy(true);
  try {
    const { payload, response } = await fetchJson("/api/workspace/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Open failed with status ${response.status}`);
    }
    applyWorkspacePayload(payload || {});
    state.workspace.note = `Opened from saved branch ${payload?.title || workspaceId}.`;
    persistTurnSnapshot();
    renderWorkspaceMeta();
    pushNotice("Draft opened", `${payload?.title || workspaceId} is now the active draft.`, "success");
    clearWhiteboardDecision();
    revealWhiteboard();
  } catch (error) {
    pushNotice("Open failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

function applyWorkspaceDraft(content, title, { note, markDirty }) {
  state.workspace.title = title || state.workspace.title;
  state.workspace.content = content;
  state.workspace.savedContent = markDirty ? state.workspace.savedContent : content;
  state.workspace.dirty = markDirty || content !== state.workspace.savedContent;
  state.workspace.lifecycle = state.workspace.dirty ? "transient_draft" : "saved_whiteboard";
  state.workspace.note = note || "Updated your current draft.";
  state.workspace.latestArtifact = null;
  workspaceTitleEl.textContent = state.workspace.title;
  workspaceEditorEl.value = content;
  renderWorkspaceMeta();
}

function startFreshWorkspaceDraft(content, title, { note, markDirty = true } = {}) {
  const nextTitle = title || inferWorkspaceTitle(content) || "Draft";
  const nextWorkspaceId = slugify(nextTitle || "whiteboard-draft");
  state.workspace.workspaceId = nextWorkspaceId;
  state.workspace.title = nextTitle;
  state.workspace.content = content;
  state.workspace.savedContent = markDirty ? "" : content;
  state.workspace.dirty = markDirty || content !== state.workspace.savedContent;
  state.workspace.lifecycle = state.workspace.dirty ? "transient_draft" : "saved_whiteboard";
  state.workspace.note = note || "Started a new draft.";
  state.workspace.latestArtifact = null;
  workspaceTitleEl.textContent = state.workspace.title;
  workspaceEditorEl.value = content;
  renderWorkspaceMeta();
}

function isUntouchedExperimentWorkspace() {
  const content = String(state.workspace.content || "");
  return state.workspace.scope === "experiment"
    && state.workspace.workspaceId === "experiment-workspace"
    && state.workspace.dirty === false
    && content.includes("# Experiment Workspace")
    && content.includes("This is a temporary sandbox.");
}

function prepareWorkspaceForWhiteboardOffer() {
  if (!isUntouchedExperimentWorkspace()) {
    return;
  }
  state.workspace.workspaceId = "";
  state.workspace.title = "Draft";
  state.workspace.content = "";
  state.workspace.savedContent = "";
  state.workspace.dirty = false;
  state.workspace.lifecycle = "ready";
  state.workspace.latestArtifact = null;
  workspaceTitleEl.textContent = state.workspace.title;
  workspaceEditorEl.value = "";
}

async function resolveWorkspaceOffer() {
  const workspaceUpdate = state.turn.workspaceUpdate;
  if (!workspaceUpdate || workspaceUpdate.status !== "offered") {
    return;
  }
  if (!workspaceUpdateHasDraft(workspaceUpdate)) {
    await acceptPendingWorkspaceOffer();
    return;
  }
  await applyPendingWorkspaceUpdate("replace");
}

async function applyPendingWorkspaceUpdate(mode, { bypassDirtyCheck = false } = {}) {
  const workspaceUpdate = state.turn.workspaceUpdate;
  if (!workspaceUpdate || !workspaceUpdateHasDraft(workspaceUpdate)) {
    pushNotice("Draft unavailable", "This whiteboard update did not include draft content to apply yet.", "warning");
    return;
  }

  if (mode === "replace" && state.workspace.dirty && !bypassDirtyCheck) {
    queueWhiteboardDecision({
      kind: "pending_draft_replace",
      targetLabel: workspaceUpdate.title || "this draft",
    });
    return;
  }

  if (mode === "replace" && shouldForkWorkspaceForDraft(workspaceUpdate)) {
    startFreshWorkspaceDraft(workspaceUpdate.content, workspaceUpdate.title || state.workspace.title, {
      note: "Started a new draft from earlier work. Save when you're ready.",
      markDirty: true,
    });
    revealWhiteboard();
    dismissWorkspaceUpdate("applied", {
      title: "Draft opened",
      message: "The pending draft was opened as a fresh whiteboard so it would not overwrite the current one.",
      tone: "success",
    });
    clearWhiteboardDecision();
    return;
  }

  const nextContent = mode === "append"
    ? appendWorkspaceDraft(state.workspace.content, workspaceUpdate.content)
    : workspaceUpdate.content;
  const nextTitle = mode === "replace" ? (workspaceUpdate.title || state.workspace.title) : state.workspace.title;
  const note = mode === "append"
    ? "Updated your draft by appending this turn's changes. Save when you're ready."
    : "Updated your draft with this turn's changes. Save when you're ready.";

  applyWorkspaceDraft(nextContent, nextTitle, { note, markDirty: true });
  revealWhiteboard();
  dismissWorkspaceUpdate(mode === "append" ? "appended" : "applied", {
    title: mode === "append" ? "Draft appended" : "Draft applied",
    message: mode === "append"
      ? "The pending draft was appended to the whiteboard without saving it yet."
      : "The pending draft was applied to the whiteboard without saving it yet.",
    tone: "success",
  });
  clearWhiteboardDecision();
}

function appendWorkspaceDraft(currentContent, draftContent) {
  const left = String(currentContent || "").trimEnd();
  const right = String(draftContent || "").trim();
  if (!left) {
    return right;
  }
  if (!right) {
    return left;
  }
  return `${left}\n\n---\n\n${right}`;
}

function dismissWorkspaceUpdate(decision, notice = null) {
  if (!state.turn.workspaceUpdate) {
    return;
  }
  state.turn.workspaceUpdate = {
    ...state.turn.workspaceUpdate,
    decision,
  };
  persistTurnSnapshot();
  renderTurnPanel();
  if (notice) {
    pushNotice(notice.title, notice.message, notice.tone);
  }
}

async function acceptPendingWorkspaceOffer() {
  const pendingWorkspaceUpdate = buildPendingWorkspaceContext("", { forceCarry: true });
  if (!pendingWorkspaceUpdate) {
    prepareWorkspaceForWhiteboardOffer();
    revealWhiteboard();
    state.workspace.note = "Started a new draft. Continue here so we can shape it together.";
    renderWorkspaceMeta();
    return;
  }

  if (!workspaceUpdateHasDraft(state.turn.workspaceUpdate)) {
    prepareWorkspaceForWhiteboardOffer();
  }
  revealWhiteboard();
  state.workspace.note = "Opening a shared draft in the whiteboard.";
  renderWorkspaceMeta();

  setBusy(true);
  try {
    const pinnedContextId = getPinnedContextIdForChat();
    const workspaceContext = buildWorkspaceContextPayload({
      surface: state.surface,
      workspace: state.workspace,
      workspacePinned: state.workspace.pinnedToChat,
    });
    const { payload, response } = await fetchJson("/api/chat/whiteboard/accept", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        history: state.history,
        ...workspaceContext,
        pending_workspace_update: pendingWorkspaceUpdate,
        pinned_context_id: pinnedContextId,
      }),
    });
    if (!response.ok) {
      throw new Error(payload?.detail || `Workspace acceptance failed with status ${response.status}`);
    }
    if (payload?.assistant_message) {
      addMessage("assistant", payload.assistant_message, {
        evidence: buildChatTurnEvidence(payload || {}),
      });
    }
    applyChatPayload(payload || {});
    absorbGraphNotices(payload || {});
  } catch (error) {
    addMessage("system", error instanceof Error ? error.message : String(error));
    pushNotice("Draft accept failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

function buildPendingWorkspaceContext(message = "", { forceCarry = false } = {}) {
  const workspaceUpdate = state.turn.workspaceUpdate;
  if (!hasPendingWorkspaceDecision(workspaceUpdate)) {
    return null;
  }
  if (!shouldCarryPendingWorkspaceUpdate(message, { force: forceCarry })) {
    return null;
  }
  return {
    type: workspaceUpdate.type || null,
    status: workspaceUpdate.status || null,
    summary: workspaceUpdate.summary || null,
    origin_user_message: state.turn.userMessage || null,
    origin_assistant_message: state.turn.assistantMessage || null,
  };
}

function shouldAutoApplyWorkspaceDraft(workspaceUpdate, interpretation) {
  if (!workspaceUpdateHasDraft(workspaceUpdate) || !hasPendingWorkspaceDecision(workspaceUpdate)) {
    return false;
  }
  return String(interpretation?.resolvedWhiteboardMode || "").toLowerCase() === "draft";
}

function autoApplyWorkspaceDraft(workspaceUpdate) {
  if (!workspaceUpdateHasDraft(workspaceUpdate)) {
    return false;
  }
  if (shouldForkWorkspaceForDraft(workspaceUpdate)) {
    startFreshWorkspaceDraft(workspaceUpdate.content, workspaceUpdate.title || state.workspace.title, {
      note: "Started a new draft from this turn's earlier work. Save when you're ready.",
      markDirty: true,
    });
  } else {
    const nextTitle = workspaceUpdate.title || state.workspace.title;
    applyWorkspaceDraft(workspaceUpdate.content, nextTitle, {
      note: "Updated your draft with this turn's changes. Save when you're ready.",
      markDirty: true,
    });
  }
  state.turn.workspaceUpdate = {
    ...workspaceUpdate,
    decision: "applied",
  };
  pushNotice("Draft ready", "The draft is ready for editing.", "success");
  return true;
}

function shouldForkWorkspaceForDraft(workspaceUpdate) {
  if (!workspaceUpdateHasDraft(workspaceUpdate)) {
    return false;
  }
  const draftWorkspaceId = slugify(workspaceUpdate.title || inferWorkspaceTitle(workspaceUpdate.content) || "whiteboard-draft");
  if (!state.workspace.workspaceId) {
    return true;
  }
  if (state.workspace.workspaceId !== draftWorkspaceId) {
    return true;
  }
  return false;
}

function syncWorkspaceFromEditor() {
  state.workspace.content = workspaceEditorEl.value;
  state.workspace.dirty = state.workspace.content !== state.workspace.savedContent;
  state.workspace.lifecycle = state.workspace.dirty ? "transient_draft" : "saved_whiteboard";
  state.workspace.note = state.workspace.dirty ? "Unsaved changes in this draft." : "Saved whiteboard.";
  persistTurnSnapshot();
  renderWorkspaceMeta();
}

function renderWorkspaceMeta() {
  const whiteboardDecision = deriveWhiteboardDecisionPresentation({
    view: state.surface,
    localDecision: state.pendingWhiteboardDecision,
    workspaceUpdate: state.turn.workspaceUpdate,
  });
  const lifecycle = deriveWhiteboardLifecycle({
    dirty: state.workspace.dirty,
    lifecycle: state.workspace.lifecycle,
    workspaceId: state.workspace.workspaceId,
  });
  const parts = [];
  parts.push(lifecycle.label);
  if (state.experiment.active) {
    parts.push("Experiment session");
  }
  if (state.workspace.note) {
    parts.push(state.workspace.note);
  }
  workspaceMetaEl.textContent = parts.join(" • ");
  workspaceDockLabelEl.textContent = whiteboardDecision.visible
    ? "Decision needed"
    : lifecycle.panelLabel;
  saveWorkspaceButtonEl.disabled = state.busy;
  promoteWorkspaceButtonEl.disabled = state.busy || !workspaceEditorEl.value.trim();
  renderWorkspaceArtifactCue();
  renderWhiteboardDecisionPanel();
  renderSurfaceStatus();
}

function renderWorkspaceArtifactCue() {
  if (!workspaceArtifactPanelEl || !workspaceArtifactSummaryEl || !workspaceArtifactActionsEl) {
    return;
  }
  workspaceArtifactActionsEl.innerHTML = "";
  const latestArtifact = state.workspace.latestArtifact;
  if (!latestArtifact?.id) {
    workspaceArtifactPanelEl.hidden = true;
    return;
  }

  const lifecycleLabel = artifactLifecycleLabel(latestArtifact);
  workspaceArtifactPanelEl.hidden = false;
  workspaceArtifactSummaryEl.textContent = [
    `Latest ${lifecycleLabel}: ${latestArtifact.title || "Saved work product"}`,
    latestArtifact.card || "",
    state.workspace.dirty
      ? "You have unsaved changes since this saved version."
      : "Inspect it or reopen it here when you want to continue from the saved version.",
  ].filter(Boolean).join(" • ");

  const inspectButton = createActionButton("Inspect work product", "secondary");
  inspectButton.disabled = state.busy;
  inspectButton.addEventListener("click", () => {
    inspectWorkspaceLatestArtifact();
  });

  const reopenButton = createActionButton("Reopen in whiteboard", "secondary");
  reopenButton.disabled = state.busy;
  reopenButton.addEventListener("click", async () => {
    await reopenWorkspaceLatestArtifact();
  });

  workspaceArtifactActionsEl.append(inspectButton, reopenButton);
}

function inspectWorkspaceLatestArtifact() {
  const latestArtifact = state.workspace.latestArtifact;
  if (!latestArtifact?.id) {
    return;
  }
  upsertSessionSavedNote(latestArtifact);
  openVantage({ focus: "library" });
  memoryDockEl.open = true;
  selectConcept(latestArtifact.id, { silent: true, source: "whiteboard" });
  renderViewState();
  renderMemoryPanel();
}

async function reopenWorkspaceLatestArtifact() {
  const latestArtifact = state.workspace.latestArtifact;
  if (!latestArtifact?.id) {
    return;
  }
  upsertSessionSavedNote(latestArtifact);
  await openConceptIntoWorkspace(latestArtifact.id);
}

function renderTurnPanel() {
  const scenarioLab = state.turn.scenarioLab;
  const scenarioLabFailed = scenarioLab?.status === "failed";
  const scenarioBranchCount = scenarioLabBranchCount(scenarioLab);
  const grounding = currentTurnGrounding();
  const {
    responseMode,
    recallCount,
    learnedCount,
    hasGroundedContext,
    isBestGuess,
  } = grounding;
  const groundingCopy = buildTurnPanelGroundingCopy({
    grounding,
    learnedCount,
  });
  const workspaceUpdate = state.turn.workspaceUpdate;
  const interpretation = state.turn.interpretation;
  const semanticFrame = state.turn.semanticFrame;
  const semanticPolicy = state.turn.semanticPolicy;
  const semanticPolicyCopy = buildSemanticPolicyCopy({ semanticPolicy, semanticFrame });
  const reasoningPath = buildReasoningPathInspection({
    userMessage: state.turn.userMessage,
    interpretation,
    responseMode,
    candidateConcepts: state.candidateConcepts,
    candidateSavedNotes: state.candidateSavedNotes,
    candidateTraceNotes: state.candidateTraceNotes,
    candidateVaultNotes: state.candidateVaultNotes,
    recallItems: state.turnWorkingMemory,
    learnedItems: state.turnLearned,
    traceNotes: state.turnTraceNotes,
    workspaceContextScope: state.turn.workspaceContextScope,
    workspaceUpdate: state.turn.workspaceUpdate,
    memoryTraceRecord: state.turnMemoryTraceRecord,
    scenarioLab: state.turn.scenarioLab,
    graphAction: state.turn.graphAction,
  });

  turnTitleEl.textContent = "This turn";
  if (scenarioLab && !scenarioLabFailed && !recallCount && !learnedCount) {
    turnMetaEl.textContent = hasGroundedContext || isBestGuess
      ? `Scenario Lab • Grounding: ${groundingCopy.groundingLabel}`
      : "Scenario Lab ran separately for this turn";
  } else {
    turnMetaEl.textContent = groundingCopy.metaText;
  }
  answerDockLabelEl.textContent = groundingCopy.answerDockLabel;
  turnIntentEl.textContent = groundingCopy.turnIntentLabel;

  turnNoticeEl.textContent = semanticPolicy?.needsClarification
    ? semanticPolicyCopy.clarificationLabel
    : buildTurnAtAGlanceSummary({
    recallCount,
    groundingLabel: groundingCopy.groundingLabel,
    hasGroundedContext,
    hasBroaderGrounding: grounding.hasBroaderGrounding,
    isBestGuess,
    learnedCount,
    scenarioLabStatus: scenarioLabFailed ? "failed" : (scenarioLab ? "ready" : ""),
    scenarioLabBranchCount: scenarioBranchCount,
    graphActionSummary: learnedCount ? "" : describeGraphAction(state.turn.graphAction),
  });

  renderTurnSummaryFacts({ grounding, scenarioLab, scenarioLabFailed, semanticFrame, semanticPolicy, semanticPolicyCopy });
  renderInspectBuckets({ grounding, interpretation, workspaceUpdate });
  renderQuietActivityLine({ grounding, scenarioLab, workspaceUpdate, semanticFrame, semanticPolicy });
  renderWorkingMemoryPanel({
    grounding,
    interpretation,
    workspaceContextScope: state.turn.workspaceContextScope,
  });

  renderWorkspaceUpdatePanel(workspaceUpdate, { hidden: Boolean(scenarioLab && !scenarioLabFailed) });
  renderMemoryGroup(
    turnWorkingMemoryListEl,
    // Legacy name: `turnWorkingMemory` still holds the recalled subset only.
    state.turnWorkingMemory,
    "turn",
    "Nothing was pulled in for this turn.",
  );
  renderMemoryGroup(
    turnLearnedListEl,
    state.turnLearned,
    "learned",
    "Nothing new was learned from this turn.",
  );
  renderMemoryTracePanel();
  renderReasoningPathPanel(reasoningPath, interpretation);
  renderLearnedCorrectionPanel();
  updateTurnSupportHierarchy({
    recallCount,
    learnedCount,
    traceCount: state.turnTraceNotes.length,
    hasTraceRecord: Boolean(state.turnMemoryTraceRecord?.id),
  });
  renderWhiteboardDecisionPanel();
  renderScenarioLabPanel(scenarioLab);
  renderSurfaceStatus();
}

function renderQuietActivityLine({
  grounding = null,
  scenarioLab = null,
  workspaceUpdate = null,
  semanticFrame = null,
  semanticPolicy = null,
} = {}) {
  if (!quietActivityLineEl) {
    return;
  }
  quietActivityLineEl.textContent = buildQuietActivityCopy({
    activity: state.turn.activity,
    semanticFrame,
    semanticPolicy,
    scenarioLab,
    workspaceUpdate,
    grounding,
    busy: state.busy,
  });
}

function updateTurnSupportHierarchy({
  recallCount = 0,
  learnedCount = 0,
  traceCount = 0,
  hasTraceRecord = false,
} = {}) {
  if (turnRecallSummaryMetaEl) {
    turnRecallSummaryMetaEl.textContent = recallCount > 0
      ? `${recallCount} item${recallCount === 1 ? "" : "s"} entered`
      : "Nothing entered";
  }
  if (turnRecallSectionEl) {
    turnRecallSectionEl.open = recallCount > 0;
  }

  const continuityCount = traceCount + (hasTraceRecord ? 1 : 0);
  if (turnTraceSummaryMetaEl) {
    turnTraceSummaryMetaEl.textContent = continuityCount > 0
      ? `${continuityCount} recent item${continuityCount === 1 ? "" : "s"}`
      : "Quiet";
  }
  if (turnTraceSectionEl) {
    turnTraceSectionEl.open = recallCount === 0 && learnedCount === 0 && continuityCount > 0;
  }

  if (turnLearnedSummaryMetaEl) {
    turnLearnedSummaryMetaEl.textContent = learnedCount > 0
      ? `${learnedCount} saved item${learnedCount === 1 ? "" : "s"}`
      : "Nothing new yet";
  }
  if (turnLearnedSectionEl) {
    turnLearnedSectionEl.open = learnedCount > 0;
  }
}

function renderTurnSummaryFacts({
  grounding,
  scenarioLab,
  scenarioLabFailed,
  semanticFrame = null,
  semanticPolicy = null,
  semanticPolicyCopy = null,
} = {}) {
  if (!turnSummaryFactsEl) {
    return;
  }
  turnSummaryFactsEl.innerHTML = "";

  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : 0;
  const learnedCount = Number.isFinite(Number(grounding?.learnedCount))
    ? Number(grounding.learnedCount)
    : 0;
  const groundingLabel = String(grounding?.groundingLabel || "").trim() || "Idle";
  if (semanticFrame?.userGoal) {
    turnSummaryFactsEl.append(
      createMiniMeta("Understood As", semanticFrame.userGoal),
    );
  }
  if (semanticPolicy?.needsClarification) {
    turnSummaryFactsEl.append(
      createMiniMeta("Needs", "Clarification"),
    );
  } else if (semanticPolicyCopy?.actionLabel && semanticPolicyCopy.actionLabel !== "Answer directly") {
    turnSummaryFactsEl.append(
      createMiniMeta("Next Step", semanticPolicyCopy.actionLabel),
    );
  }

  if (recallCount > 0) {
    turnSummaryFactsEl.append(
      createMiniMeta("Pulled In", `${recallCount} item${recallCount === 1 ? "" : "s"}`),
    );
  }
  if (grounding?.hasBroaderGrounding || grounding?.hasGroundedContext || grounding?.isBestGuess) {
    turnSummaryFactsEl.append(
      createMiniMeta("Context in Scope", groundingLabel),
    );
  }
  if (learnedCount > 0) {
    turnSummaryFactsEl.append(
      createMiniMeta("Saved for Later", `${learnedCount} item${learnedCount === 1 ? "" : "s"}`),
    );
  }
  if (scenarioLab) {
    const branchCount = scenarioLabBranchCount(scenarioLab);
    turnSummaryFactsEl.append(
      createMiniMeta(
        "Scenario Lab",
        scenarioLabFailed
          ? "Back in chat"
          : branchCount > 0
            ? `${branchCount} branch${branchCount === 1 ? "" : "es"}`
            : "Ready",
      ),
    );
  }
  if (!turnSummaryFactsEl.childNodes.length) {
    turnSummaryFactsEl.append(
      createMiniMeta("Status", "Idle"),
    );
  }
}

function renderInspectBuckets({
  grounding = null,
  interpretation = null,
  workspaceUpdate = null,
} = {}) {
  if (!turnInspectBucketsEl) {
    return;
  }
  turnInspectBucketsEl.innerHTML = "";
  const traceItems = [
    ...(state.turnMemoryTraceRecord?.id ? [state.turnMemoryTraceRecord] : []),
    ...state.turnTraceNotes,
  ];
  const draftItems = buildDraftInspectItems({
    grounding,
    interpretation,
    workspaceUpdate,
  });
  const buckets = buildInspectBuckets({
    usedItems: state.turnWorkingMemory,
    recentItems: traceItems,
    draftItems,
  });
  for (const bucket of buckets) {
    turnInspectBucketsEl.append(createInspectBucket(bucket));
  }
}

function createInspectBucket(bucket) {
  const article = document.createElement("article");
  article.className = `inspect-bucket inspect-bucket--${bucket.key}`;

  const top = document.createElement("div");
  top.className = "inspect-bucket__top";
  const label = document.createElement("div");
  label.className = "section-label section-label--subtle";
  label.textContent = bucket.label;
  const count = document.createElement("span");
  count.className = "inspect-bucket__count";
  count.textContent = String(bucket.count || 0);
  top.append(label, count);

  const summary = document.createElement("p");
  summary.className = "inspect-bucket__summary";
  summary.textContent = bucket.summary || bucket.emptyMessage || "";

  article.append(top, summary);
  const firstItem = Array.isArray(bucket.items) ? bucket.items[0] : null;
  if (firstItem?.title || firstItem?.label) {
    const sample = document.createElement("p");
    sample.className = "inspect-bucket__sample";
    sample.textContent = firstItem.title || firstItem.label;
    article.append(sample);
  }
  return article;
}

function buildDraftInspectItems({
  grounding = null,
  interpretation = null,
  workspaceUpdate = null,
} = {}) {
  const items = [];
  const sourceLabels = workingMemorySourceLabels(grounding);
  const workspaceScope = humanizeWorkingMemoryScope(state.turn.workspaceContextScope);
  if (sourceLabels.includes("Draft")) {
    items.push({
      id: "draft-scope",
      title: workspaceScope ? `Draft scope: ${workspaceScope}` : "Draft in scope",
      label: "Draft in scope",
    });
  }
  if (workspaceUpdate?.status) {
    items.push({
      id: `workspace-update-${workspaceUpdate.status}`,
      title: workspaceUpdate.title || workspaceUpdate.summary || "Draft update",
      label: workspaceUpdate.status.replace(/_/g, " "),
    });
  }
  if (interpretation?.resolvedWhiteboardMode && interpretation.resolvedWhiteboardMode !== "chat") {
    items.push({
      id: `draft-route-${interpretation.resolvedWhiteboardMode}`,
      title: humanizeInterpretationWhiteboardMode(interpretation.resolvedWhiteboardMode),
      label: "Draft route",
    });
  }
  return items;
}

function renderWorkingMemoryPanel({
  grounding = null,
  interpretation = null,
  workspaceContextScope = "excluded",
} = {}) {
  if (!turnWorkingMemoryNoticeEl || !turnWorkingMemoryFactsEl) {
    return;
  }
  if (turnWorkingMemorySummaryMetaEl) {
    turnWorkingMemorySummaryMetaEl.textContent = buildWorkingMemorySummaryMeta({
      grounding,
    });
  }
  turnWorkingMemoryNoticeEl.textContent = buildWorkingMemoryNotice({
    grounding,
    interpretation,
    workspaceContextScope,
  });
  turnWorkingMemoryFactsEl.innerHTML = "";

  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : 0;
  const sourceLabels = workingMemorySourceLabels(grounding);
  const whiteboardScopeLabel = humanizeWorkingMemoryScope(workspaceContextScope);
  const keptInScope = interpretation?.preservePinnedContext ?? interpretation?.preserveSelectedRecord;
  const keptInScopeReason = String(
    interpretation?.pinnedContextReason || interpretation?.selectedRecordReason || "",
  ).trim();
  const inScopeLabel = buildWorkingMemorySummaryMeta({
    grounding,
  });

  turnWorkingMemoryFactsEl.append(
    createMiniMeta("In scope", inScopeLabel),
    createMiniMeta("Pulled In", recallCount > 0 ? `${recallCount} item${recallCount === 1 ? "" : "s"} surfaced` : "None surfaced"),
  );
  if (sourceLabels.length) {
    turnWorkingMemoryFactsEl.append(
      createMiniMeta("Broader context", sourceLabels.join(", ")),
    );
  }
  if (whiteboardScopeLabel && sourceLabels.includes("Draft")) {
    turnWorkingMemoryFactsEl.append(
      createMiniMeta("Draft scope", whiteboardScopeLabel),
    );
  }
  if (keptInScope === true) {
    turnWorkingMemoryFactsEl.append(
      createMiniMeta("Kept in scope", keptInScopeReason || "Pinned context"),
    );
  }
  if (grounding?.isBestGuess) {
    turnWorkingMemoryFactsEl.append(
      createMiniMeta("Response", "Best Guess"),
    );
  }
}

function buildWorkingMemoryNotice({
  grounding = null,
  interpretation = null,
  workspaceContextScope = "excluded",
} = {}) {
  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : 0;
  const sourceLabels = workingMemorySourceLabels(grounding);
  const whiteboardScopeLabel = humanizeWorkingMemoryScope(workspaceContextScope);
  const keptInScope = interpretation?.preservePinnedContext ?? interpretation?.preserveSelectedRecord;
  const pieces = [];

  if (grounding?.isBestGuess) {
    pieces.push("Context in scope stayed minimal for this turn.");
    pieces.push("The answer was generated from the current request only, without pulled-in items or broader grounded context.");
  } else {
    const included = [];
    if (recallCount > 0) {
      included.push("Pulled In");
    }
    included.push(...sourceLabels);
    if (recallCount > 0 && sourceLabels.length) {
      pieces.push(`Context in scope combined ${joinReadableList(included)} for generation.`);
      pieces.push("The pulled-in items below are only the retrieved subset that surfaced into this turn.");
    } else if (recallCount > 0) {
      pieces.push("Context in scope for this answer came from pulled-in items.");
      pieces.push("The pulled-in items below are the retrieved subset that surfaced into this turn.");
    } else if (sourceLabels.length) {
      pieces.push(`Context in scope came from ${joinReadableList(sourceLabels)}.`);
      pieces.push("No separate pulled-in items surfaced for this turn.");
    } else if (grounding?.hasGroundedContext && grounding?.groundingLabel && grounding.groundingLabel !== "Idle") {
      pieces.push(`Context in scope stayed grounded in ${grounding.groundingLabel}.`);
      pieces.push("The turn payload did not expose a more detailed context source mix.");
    } else {
      pieces.push("Context in scope held the current request only.");
      pieces.push("No additional context was in scope for generation.");
    }
  }

  if (whiteboardScopeLabel && sourceLabels.includes("Draft")) {
    pieces.push(`Draft scope was ${whiteboardScopeLabel.toLowerCase()}.`);
  }
  if (keptInScope === true) {
    pieces.push("Pinned context stayed in scope for this turn.");
  }
  return pieces.join(" ");
}

function buildWorkingMemorySummaryMeta({
  grounding = null,
} = {}) {
  const recallCount = Number.isFinite(Number(grounding?.recallCount))
    ? Number(grounding.recallCount)
    : 0;
  const sourceLabels = workingMemorySourceLabels(grounding);
  const parts = [];
  if (recallCount > 0) {
    parts.push("Pulled In");
  }
  parts.push(...sourceLabels);
  if (parts.length) {
    return parts.join(" + ");
  }
  if (grounding?.isBestGuess) {
    return "Current request only";
  }
  if (grounding?.groundingLabel && grounding.groundingLabel !== "Idle") {
    return grounding.groundingLabel;
  }
  return "Current request only";
}

function workingMemorySourceLabels(grounding = null) {
  const labels = new Set();
  for (const source of Array.isArray(grounding?.groundingSources) ? grounding.groundingSources : []) {
    const normalized = normalizeWorkingMemorySource(source);
    const label = describeWorkingMemorySource(normalized);
    if (label) {
      labels.add(label);
    }
  }
  if (!labels.size) {
    const fallbackLabel = describeWorkingMemorySource(grounding?.groundingMode);
    if (fallbackLabel) {
      labels.add(fallbackLabel);
    }
  }
  return [...labels];
}

function normalizeWorkingMemorySource(source) {
  const normalized = String(source || "").trim().toLowerCase();
  return normalized === "working_memory" ? "recall" : normalized;
}

function describeWorkingMemorySource(source) {
  switch (normalizeWorkingMemorySource(source)) {
    case "whiteboard":
      return "Draft";
    case "recent_chat":
      return "Recent Chat";
    case "pending_whiteboard":
      return "Prior Draft";
    default:
      return "";
  }
}

function humanizeWorkingMemoryScope(scope) {
  switch (String(scope || "").trim().toLowerCase()) {
    case "visible":
      return "Visible";
    case "pinned":
      return "Pinned";
    case "requested":
      return "Requested";
    case "auto":
      return "Auto";
    default:
      return "";
  }
}

function joinReadableList(items = []) {
  const cleaned = items.filter(Boolean);
  if (!cleaned.length) {
    return "";
  }
  if (cleaned.length === 1) {
    return cleaned[0];
  }
  if (cleaned.length === 2) {
    return `${cleaned[0]} and ${cleaned[1]}`;
  }
  return `${cleaned.slice(0, -1).join(", ")}, and ${cleaned[cleaned.length - 1]}`;
}

function renderReasoningPathPanel(reasoningPath, interpretation, { hidden = false } = {}) {
  turnReasoningPathSectionEl.hidden = hidden || !reasoningPath?.visible;
  turnReasoningPathSectionEl.open = Boolean(state.turnReasoningPathExpanded) && !turnReasoningPathSectionEl.hidden;
  turnReasoningPathMetaEl.innerHTML = "";
  turnReasoningPathRailEl.innerHTML = "";
  if (turnReasoningPathSectionEl.hidden || !reasoningPath) {
    if (turnReasoningPathStateEl) {
      turnReasoningPathStateEl.textContent = "Collapsed";
    }
    return;
  }

  turnReasoningPathSummaryEl.textContent = reasoningPath.summary
    || "Inspect assembled a compact path for this turn.";
  if (turnReasoningPathStateEl) {
    turnReasoningPathStateEl.textContent = state.turnReasoningPathExpanded ? "Expanded" : "Collapsed";
  }

  const pathMode = interpretation?.mode ? humanizeInterpretationMode(interpretation.mode) : "Chat";
  turnReasoningPathMetaEl.append(
    createMiniMeta("Path", pathMode),
  );
  if (interpretation?.resolvedWhiteboardMode) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Draft", humanizeInterpretationWhiteboardMode(interpretation.resolvedWhiteboardMode)),
    );
  }
  if (typeof interpretation?.confidence === "number" && Number.isFinite(interpretation.confidence) && interpretation.confidence > 0) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Route confidence", humanizeRouteConfidence(interpretation.confidence)),
    );
  }
  const preservesPinnedContext = interpretation?.preservePinnedContext ?? interpretation?.preserveSelectedRecord;
  if (preservesPinnedContext === true) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Kept in scope", interpretation?.pinnedContextReason || interpretation?.selectedRecordReason || "Preserved"),
    );
  }
  if (interpretation?.whiteboardModeSource === "composer") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Chose this from", "Composer"),
    );
  } else if (interpretation?.whiteboardModeSource === "request") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Chose this from", "User request"),
    );
  } else if (interpretation?.whiteboardModeSource === "interpreter") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Chose this from", "Interpreter"),
    );
  }
  const semanticFrame = state.turn.semanticFrame;
  const semanticPolicyCopy = buildSemanticPolicyCopy({
    semanticPolicy: state.turn.semanticPolicy,
    semanticFrame,
  });
  if (semanticFrame?.targetSurface) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Target", humanizeSemanticSurface(semanticFrame.targetSurface)),
    );
  }
  if (semanticFrame?.followUpType && semanticFrame.followUpType !== "new_request") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Follow-up", humanizeSemanticToken(semanticFrame.followUpType)),
    );
  }
  if (semanticPolicyCopy.visible && semanticPolicyCopy.actionLabel !== "Answer directly") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Semantic Action", semanticPolicyCopy.actionLabel),
    );
  }

  for (const stage of reasoningPath.stages || []) {
    turnReasoningPathRailEl.appendChild(createReasoningPathCard(stage));
  }
}

function createReasoningPathCard(stage) {
  const details = document.createElement("details");
  details.className = "reasoning-path-card";
  details.open = state.turnReasoningPathStageKey === stage.key;

  const summary = document.createElement("summary");
  summary.className = "reasoning-path-card__summary";
  summary.addEventListener("click", (event) => {
    event.preventDefault();
    state.turnReasoningPathStageKey = state.turnReasoningPathStageKey === stage.key
      ? ""
      : stage.key;
    state.turnReasoningPathExpanded = true;
    persistTurnSnapshot();
    renderTurnPanel();
  });

  const top = document.createElement("div");
  top.className = "reasoning-path-card__top";

  const label = document.createElement("div");
  label.className = "reasoning-path-card__label";
  label.textContent = stage.label || "Stage";

  const step = document.createElement("span");
  step.className = "reasoning-path-card__step";
  step.textContent = stage.key ? stage.key.replace(/_/g, " ") : "";

  top.append(label, step);

  const body = document.createElement("p");
  body.className = "reasoning-path-card__body";
  body.textContent = stage.text || "No details available.";

  summary.append(top, body);
  if (Array.isArray(stage.meta) && stage.meta.length) {
    const meta = document.createElement("div");
    meta.className = "reasoning-path-card__meta";
    for (const item of stage.meta) {
      meta.appendChild(createMiniMeta(item.label, item.value));
    }
    summary.append(meta);
  }
  details.append(summary);

  const detailPanel = createReasoningPathDetailPanel(stage);
  if (detailPanel) {
    details.append(detailPanel);
  }
  return details;
}

function createReasoningPathDetailPanel(stage) {
  const detail = stage?.detail;
  if (!detail || typeof detail !== "object") {
    return null;
  }

  const panel = document.createElement("div");
  panel.className = "reasoning-path-card__detail-panel";

  if (detail.summary) {
    const summary = document.createElement("p");
    summary.className = "reasoning-path-card__detail-summary";
    summary.textContent = detail.summary;
    panel.append(summary);
  }

  if (Array.isArray(detail.notes) && detail.notes.length) {
    const notes = document.createElement("div");
    notes.className = "reasoning-path-card__detail-notes";
    for (const note of detail.notes) {
      notes.appendChild(createMiniMeta(note.label, note.value));
    }
    panel.append(notes);
  }

  if (Array.isArray(detail.scopeRows) && detail.scopeRows.length) {
    panel.appendChild(createReasoningPathScopeTable(detail.scopeRows));
  }

  if (Array.isArray(detail.groups) && detail.groups.length) {
    for (const group of detail.groups) {
      panel.appendChild(createReasoningPathDetailGroup(group));
    }
  }

  return panel.childNodes.length ? panel : null;
}

function createReasoningPathScopeTable(rows = []) {
  const table = document.createElement("table");
  table.className = "reasoning-path-scope-table";

  const caption = document.createElement("caption");
  caption.className = "reasoning-path-scope-table__caption";
  caption.textContent = "Included and excluded context for this generation step.";
  table.appendChild(caption);

  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const label of ["Scope", "Status", "Detail"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headRow.appendChild(cell);
  }
  head.appendChild(headRow);
  table.appendChild(head);

  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");

    const scopeCell = document.createElement("td");
    scopeCell.className = "reasoning-path-scope-table__scope";
    scopeCell.textContent = row.label || "Scope";

    const statusCell = document.createElement("td");
    statusCell.className = "reasoning-path-scope-table__status";
    const statusBadge = createBadge(row.status || "Excluded", row.status === "Included" ? "success" : "soft");
    statusBadge.classList.add("badge--message");
    statusCell.appendChild(statusBadge);
    if (Number.isFinite(Number(row.count)) && Number(row.count) > 0) {
      const count = document.createElement("div");
      count.className = "reasoning-path-scope-table__count";
      count.textContent = `${row.count} item${Number(row.count) === 1 ? "" : "s"}`;
      statusCell.appendChild(count);
    }
    if (row.scope) {
      const scopeNote = document.createElement("div");
      scopeNote.className = "reasoning-path-scope-table__scope-note";
      scopeNote.textContent = `Scope: ${row.scope}`;
      statusCell.appendChild(scopeNote);
    }

    const detailCell = document.createElement("td");
    detailCell.className = "reasoning-path-scope-table__detail";
    detailCell.textContent = row.detail || "";

    tr.append(scopeCell, statusCell, detailCell);
    body.appendChild(tr);
  }
  table.appendChild(body);
  return table;
}

function createReasoningPathDetailGroup(group) {
  const section = document.createElement("section");
  section.className = "reasoning-path-card__detail-group";

  const head = document.createElement("div");
  head.className = "section-head";
  const copy = document.createElement("div");
  const label = document.createElement("div");
  label.className = "section-label";
  label.textContent = group.label || "Details";
  copy.append(label);

  const items = Array.isArray(group.items) ? group.items : [];
  const count = document.createElement("div");
  count.className = "subtle";
  count.textContent = items.length
    ? `${items.length} item${items.length === 1 ? "" : "s"}`
    : "None";
  head.append(copy, count);

  const body = document.createElement("div");
  body.className = "concept-list compact";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = group.emptyMessage || "No details are available for this stage.";
    body.append(empty);
  } else {
    for (const item of items) {
      body.appendChild(createMemoryCard(item, group.context || "reasoning-detail"));
    }
  }

  section.append(head, body);
  return section;
}

function renderMemoryTracePanel() {
  const traceNotes = Array.isArray(state.turnTraceNotes) ? state.turnTraceNotes : [];
  const traceRecord = state.turnMemoryTraceRecord && typeof state.turnMemoryTraceRecord === "object"
    ? normalizeMemoryItem(state.turnMemoryTraceRecord, "turn-trace-record")
    : null;
  const seenIds = new Set();

  turnTraceNoticeEl.textContent = buildMemoryTraceSummary({
    traceNotes,
    memoryTraceRecord: traceRecord,
  });
  turnTraceListEl.innerHTML = "";

  if (traceRecord) {
    seenIds.add(traceRecord.id);
    const traceCard = {
      ...traceRecord,
      sourceLabel: traceRecord.sourceLabel || "Memory Trace",
      type: traceRecord.type || "memory_trace",
      card: traceRecord.card || "This turn left a searchable memory trace.",
    };
    turnTraceListEl.appendChild(createMemoryCard(traceCard, "trace"));
  }

  for (const note of traceNotes) {
    if (!note || seenIds.has(note.id)) {
      continue;
    }
    seenIds.add(note.id);
    turnTraceListEl.appendChild(createMemoryCard(note, "trace"));
  }

  if (!traceRecord && !traceNotes.length) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "Recent searchable history for this turn will appear here.";
    turnTraceListEl.appendChild(empty);
  }
}

function renderWorkspaceUpdatePanel(workspaceUpdate, { hidden = false } = {}) {
  workspaceUpdatePanelEl.hidden = shouldHideChatWorkspaceUpdate({
    hidden,
    view: state.surface,
    workspaceUpdate,
  });
  workspaceUpdateActionsEl.innerHTML = "";
  if (workspaceUpdatePanelEl.hidden || !workspaceUpdate) {
    return;
  }

  workspaceUpdateLabelEl.textContent = workspaceUpdate.status === "offered"
    ? "Start a shared draft?"
    : "Review whiteboard draft";
  workspaceUpdateSummaryEl.textContent = workspaceUpdate.summary || (
    workspaceUpdate.status === "offered"
      ? "Inspect suggested moving this work into Draft so a shared draft can start there."
      : "A draft is ready to review before it enters the whiteboard."
  );

  if (workspaceUpdate.status === "offered") {
    const draftButton = createActionButton(
      workspaceUpdateHasDraft(workspaceUpdate) ? "Review draft" : "Start draft",
      "primary",
    );
    draftButton.disabled = state.busy;
    draftButton.addEventListener("click", async () => {
      await handleWhiteboardDecisionAction("open_offer");
    });
    const keepButton = createActionButton("Keep in chat", "secondary");
    keepButton.disabled = state.busy;
    keepButton.addEventListener("click", () => {
      void handleWhiteboardDecisionAction("keep_in_chat");
    });
    workspaceUpdateActionsEl.append(draftButton, keepButton);
    return;
  }

  const applyButton = createActionButton("Use this draft", "primary");
  applyButton.disabled = state.busy || !workspaceUpdateHasDraft(workspaceUpdate);
  applyButton.addEventListener("click", async () => {
    await handleWhiteboardDecisionAction("apply_draft");
  });

  const appendButton = createActionButton("Append to whiteboard", "secondary");
  appendButton.disabled = state.busy || !workspaceUpdateHasDraft(workspaceUpdate);
  appendButton.addEventListener("click", async () => {
    await handleWhiteboardDecisionAction("append_draft");
  });

  const keepCurrentButton = createActionButton("Keep current", "secondary");
  keepCurrentButton.disabled = state.busy;
  keepCurrentButton.addEventListener("click", () => {
    void handleWhiteboardDecisionAction("keep_current");
  });

  workspaceUpdateActionsEl.append(applyButton, appendButton, keepCurrentButton);
}

function renderWhiteboardDecisionPanel() {
  const presentation = deriveWhiteboardDecisionPresentation({
    view: state.surface,
    localDecision: state.pendingWhiteboardDecision,
    workspaceUpdate: state.turn.workspaceUpdate,
  });
  whiteboardDecisionPanelEl.hidden = !presentation.visible;
  whiteboardDecisionActionsEl.innerHTML = "";
  if (!presentation.visible) {
    return;
  }

  whiteboardDecisionLabelEl.textContent = presentation.label || "Draft Decision";
  whiteboardDecisionSummaryEl.textContent = presentation.summary || "Choose how to handle this whiteboard change.";

  for (const action of presentation.actions || []) {
    const button = createActionButton(action.label, action.tone);
    button.disabled = state.busy;
    button.addEventListener("click", async () => {
      await handleWhiteboardDecisionAction(action.id);
    });
    whiteboardDecisionActionsEl.append(button);
  }
}

function renderScenarioLabPanel(scenarioLab) {
  scenarioDockEl.hidden = !scenarioLab;
  scenarioLabSectionEl.hidden = !scenarioLab;
  scenarioLabSectionEl.innerHTML = "";
  scenarioDockLabelEl.textContent = "Idle";
  if (!scenarioLab) {
    return;
  }

  const hero = document.createElement("section");
  hero.className = "scenario-lab__hero";

  const heroEyebrow = document.createElement("div");
  heroEyebrow.className = "section-label";
  heroEyebrow.textContent = "Scenario Lab";

  const heroTitle = document.createElement("h3");
  heroTitle.className = "scenario-lab__title";
  heroTitle.textContent = scenarioQuestionText(scenarioLab);

  const heroSummary = document.createElement("p");
  heroSummary.className = "scenario-lab__hero-copy";
  const heroRecommendation = document.createElement("p");
  heroRecommendation.className = "scenario-lab__recommendation";

  const heroMeta = document.createElement("div");
  heroMeta.className = "scenario-lab__hero-meta";

  if (scenarioLab.status === "failed") {
    scenarioDockLabelEl.textContent = "Back in chat";
    heroSummary.textContent = scenarioLab.reason
      || "Scenario Lab was selected for this turn but could not complete.";
    heroMeta.append(createBadge("fallback", "warm"));

    const errorLabel = document.createElement("div");
    errorLabel.className = "section-label";
    errorLabel.textContent = "Failure";

    const errorNotice = document.createElement("div");
    errorNotice.className = "turn-notice turn-notice--decision scenario-lab__why";
    errorNotice.textContent = scenarioLab.error?.message
      ? `${scenarioLab.error.message} The answer stayed in chat instead.`
      : "Scenario Lab could not complete, so the answer stayed in chat instead.";

    const fallbackLabel = document.createElement("div");
    fallbackLabel.className = "section-label";
    fallbackLabel.textContent = "Fallback";

    const fallbackNotice = document.createElement("div");
    fallbackNotice.className = "turn-notice turn-notice--decision scenario-lab__grounding";
    fallbackNotice.textContent = "The turn returned a normal chat answer instead of scenario branches.";

    hero.append(heroEyebrow, heroTitle, heroSummary, heroMeta);
    scenarioLabSectionEl.append(hero, errorLabel, errorNotice, fallbackLabel, fallbackNotice);
    return;
  }

  const grounding = currentTurnGrounding();
  const {
    responseMode,
    groundingLabel: currentGroundingLabel,
    recallCount,
    learnedCount,
    hasGroundedContext,
    isBestGuess,
  } = grounding;
  const responseModeNote = responseMode.note || currentGroundingLabel || "";
  const navigatorReason = scenarioLab.navigator?.reason || scenarioLab.navigator?.note || scenarioLab.reason || "";
  const confidence = describeScenarioRouteConfidence(scenarioLab.navigator?.confidence);
  const comparisonArtifact = scenarioLab.comparisonArtifact
    || (scenarioLab.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"
      ? scenarioLab.comparison_artifact
      : null);
  const artifactDetails = comparisonArtifact ? deriveScenarioArtifactDetails(comparisonArtifact) : null;
  const comparisonBranchRoster = Array.isArray(artifactDetails?.branchIndex) ? artifactDetails.branchIndex : [];
  const sharedAssumptions = scenarioLab.sharedAssumptions || artifactDetails?.sharedAssumptions || [];
  const tradeoffs = scenarioLab.tradeoffs || artifactDetails?.tradeoffs || [];
  const nextSteps = scenarioLab.nextSteps || artifactDetails?.nextSteps || [];
  const summary = [
    scenarioLab.summary || "Scenario Lab ran as a separate reasoning mode for this turn.",
    comparisonArtifact
      ? "The saved comparison hub is the durable revisit hub for this Scenario Lab turn."
      : "Alternate branches stay separate from the turn context and surface here as a comparison-first review.",
    confidence.summary,
  ].filter(Boolean).join(" ");
  const recommendation = scenarioLab.recommendation
    || artifactDetails?.recommendation
    || "A recommendation was not returned for this Scenario Lab run.";

  heroSummary.textContent = summary;
  heroRecommendation.textContent = recommendation;
  const branchCount = Number.isFinite(Number(scenarioLab.branchCount))
    ? Number(scenarioLab.branchCount)
    : Array.isArray(scenarioLab.branches)
      ? scenarioLab.branches.length
      : comparisonBranchRoster.length;
  scenarioDockLabelEl.textContent = branchCount
    ? `${branchCount} ${branchCount === 1 ? "branch" : "branches"} ready`
    : comparisonArtifact
      ? "Comparison ready"
      : "Scenario review";
  heroMeta.append(createBadge("Reasoning mode", "accent"));
  heroMeta.append(createBadge(branchCount ? `${branchCount} ${branchCount === 1 ? "branch" : "branches"}` : "No branches", "soft"));
  if (confidence.badge) {
    heroMeta.append(createBadge(confidence.badge, "soft"));
  }
  if (comparisonArtifact) {
    heroMeta.append(createBadge("Comparison hub", "success"));
  }
  if (comparisonBranchRoster.length) {
    heroMeta.append(createBadge(`${comparisonBranchRoster.length} branches indexed`, "soft"));
  }

  const overviewGrid = document.createElement("div");
  overviewGrid.className = "scenario-lab__overview-grid";
  if (sharedAssumptions.length) {
    overviewGrid.append(
      createScenarioOverviewCard({
        label: "Shared assumptions",
        items: sharedAssumptions,
        tone: "neutral",
      }),
    );
  }
  if (nextSteps.length) {
    overviewGrid.append(
      createScenarioOverviewCard({
        label: "Next steps",
        items: nextSteps,
        tone: "neutral",
      }),
    );
  }
  if (tradeoffs.length) {
    overviewGrid.append(
      createScenarioOverviewCard({
        label: "Tradeoffs to compare",
        items: tradeoffs,
        tone: "neutral",
      }),
    );
  }

  const whyLabel = document.createElement("div");
  whyLabel.className = "section-label section-label--subtle";
  whyLabel.textContent = "Why Scenario Lab ran";

  const whyNotice = document.createElement("div");
  whyNotice.className = "turn-notice turn-notice--decision scenario-lab__why";
  whyNotice.textContent = navigatorReason || "Scenario Lab ran because this turn asked for alternate branches or comparative planning.";

  const groundingSectionLabelEl = document.createElement("div");
  groundingSectionLabelEl.className = "section-label section-label--subtle";
  groundingSectionLabelEl.textContent = "Grounding";

  const groundingNotice = document.createElement("div");
  groundingNotice.className = "turn-notice turn-notice--decision scenario-lab__grounding";
  groundingNotice.textContent = responseModeNote
    || (hasGroundedContext
      ? `Grounded by ${currentGroundingLabel}.`
      : isBestGuess
        ? "No grounded context was used for this Scenario Lab turn."
        : "Grounding details were not returned for this Scenario Lab turn.");

  const branchLabel = document.createElement("div");
  branchLabel.className = "section-label";
  branchLabel.textContent = "Linked branches";

  const branchList = document.createElement("div");
  branchList.className = "concept-list compact scenario-lab__branch-list";

  const branches = Array.isArray(scenarioLab.branches) ? scenarioLab.branches : [];
  if (branches.length) {
    for (const branch of branches) {
      branchList.appendChild(createScenarioBranchCard(branch));
    }
  } else {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "No scenario branches were returned for this turn.";
    branchList.appendChild(empty);
  }

  const artifactLabel = document.createElement("div");
  artifactLabel.className = "section-label";
  artifactLabel.textContent = "Durable comparison hub";

  const artifactList = document.createElement("div");
  artifactList.className = "concept-list compact scenario-lab__artifact-list";
  if (comparisonArtifact) {
    artifactList.appendChild(createScenarioArtifactCard(comparisonArtifact));
  } else {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "No comparison hub was saved for this turn.";
    artifactList.appendChild(empty);
  }

  const artifactSection = document.createElement("section");
  artifactSection.className = "scenario-lab__section scenario-lab__section--artifact";
  artifactSection.append(
    createScenarioSectionLead({
      label: artifactLabel.textContent,
      summary: comparisonArtifact
        ? "Start here. The comparison hub is the durable anchor for this Scenario Lab run, with the recommendation and linked branch roster kept together."
        : "No durable comparison hub was saved for this turn.",
      metaItems: comparisonArtifact
        ? [
            { label: "Role", value: "Durable anchor" },
            { label: "Linked branches", value: String(comparisonBranchRoster.length || branchCount || 0) },
          ]
        : [],
    }),
    artifactList,
  );

  const branchSection = document.createElement("section");
  branchSection.className = "scenario-lab__section scenario-lab__section--branches";
  branchSection.append(
    createScenarioSectionLead({
      label: branchLabel.textContent,
      summary: branchCount
        ? `${branchCount} branch${branchCount === 1 ? "" : "es"} explore the same question from different directions. Use the hub above as the durable reference point, then compare the fuller branch details here.`
        : "No scenario branches were returned for this turn.",
      metaItems: branchCount
        ? [
            { label: "Branch set", value: `${branchCount} ready` },
            comparisonArtifact ? { label: "Hub", value: "Saved comparison" } : null,
          ].filter(Boolean)
        : [],
    }),
    branchList,
  );

  const supportSection = document.createElement("section");
  supportSection.className = "scenario-lab__section scenario-lab__section--support";
  const supportGrid = document.createElement("div");
  supportGrid.className = "scenario-lab__secondary-grid";
  supportGrid.append(
    createScenarioSupportCard({
      label: whyLabel.textContent,
      summary: whyNotice.textContent,
    }),
    createScenarioSupportCard({
      label: groundingSectionLabelEl.textContent,
      summary: groundingNotice.textContent,
    }),
  );
  supportSection.append(
    createScenarioSectionLead({
      label: "Supporting context",
      summary: "These notes explain why Scenario Lab ran and what grounded the turn. They stay secondary to the comparison itself.",
    }),
    supportGrid,
  );

  const primaryStack = document.createElement("section");
  primaryStack.className = "scenario-lab__primary-stack";
  if (overviewGrid.childNodes.length) {
    primaryStack.append(overviewGrid);
  }
  primaryStack.append(artifactSection, branchSection);

  scenarioLabSectionEl.append(
    hero,
    primaryStack,
    supportSection,
  );
  hero.append(heroEyebrow, heroTitle, heroSummary, heroRecommendation, heroMeta);
}

function renderMemoryPanel() {
  const query = state.memoryQuery.trim();
  const visible = getVisibleMemoryItems(query);
  const visibleSavedBuckets = splitSavedNotesByBucket(visible.savedNotes);
  const totalSavedBuckets = splitSavedNotesByBucket(state.allSavedNotes);
  const visibleConcepts = Array.isArray(visible.concepts) ? visible.concepts : [];
  const visibleMemories = visibleSavedBuckets.memories;
  const visibleArtifacts = visibleSavedBuckets.artifacts;
  const visibleVaultNotes = Array.isArray(visible.vaultNotes) ? visible.vaultNotes : [];
  const totalConcepts = state.allConcepts.length;
  const totalMemories = totalSavedBuckets.memories.length;
  const totalArtifacts = totalSavedBuckets.artifacts.length;
  const totalVaultNotes = state.allVaultNotes.length;
  const totalItems = totalConcepts + totalMemories + totalArtifacts + totalVaultNotes;
  const visibleItems = visibleConcepts.length + visibleMemories.length + visibleArtifacts.length + visibleVaultNotes.length;

  conceptsTitleEl.textContent = query ? "Search results" : "What Else Exists In The Library?";
  conceptsCountEl.textContent = query
    ? `${visibleItems} shown · ${totalItems} total`
    : `${totalConcepts} ideas · ${totalMemories} notes · ${totalArtifacts} work products · ${totalVaultNotes} references`;
  conceptsSummaryEl.textContent = `Ideas: ${visibleConcepts.length}`;
  memoriesSummaryEl.textContent = `Memories: ${visibleMemories.length}`;
  artifactsSummaryEl.textContent = `Work products: ${visibleArtifacts.length}`;
  vaultNotesSummaryEl.textContent = `References: ${visibleVaultNotes.length}`;
  conceptsHintEl.textContent = query
    ? "Filtered ideas"
    : state.experiment.active
      ? "Temporary experiment ideas first, then saved ideas"
      : "Saved reusable ideas";
  memoriesHintEl.textContent = query
    ? "Filtered notes"
    : state.experiment.active
      ? "Temporary experiment notes first, then saved notes"
      : "Saved notes";
  artifactsHintEl.textContent = query
    ? "Filtered work products and snapshots"
    : state.experiment.active
      ? "Temporary experiment work products first, then saved work products"
      : "Saved work products and snapshots";
  vaultNotesHintEl.textContent = query ? "Filtered read-only references" : "Read-only references";
  memoryDockLabelEl.textContent = `${totalItems} items`;

  renderMemoryGroup(
    conceptListEl,
    visibleConcepts,
    "memory",
    query ? "No ideas matched that search. Try a title, phrase, or id." : "No ideas found yet.",
  );
  renderMemoryGroup(
    memoryListEl,
    visibleMemories,
    "memory",
    query ? "No notes matched that search. Try a title, phrase, or id." : "No notes found yet.",
  );
  renderMemoryGroup(
    artifactListEl,
    visibleArtifacts,
    "memory",
    query ? "No work products matched that search. Try a title, phrase, or id." : "No work products found yet.",
  );
  renderMemoryGroup(
    vaultNoteListEl,
    visibleVaultNotes,
    "memory",
    query ? "No references matched that search. Try a path, label, or excerpt." : "No references found yet.",
  );

  renderMemoryInspector();
  renderPinnedContextBar();
}

function splitSavedNotesByBucket(items) {
  const memories = [];
  const artifacts = [];
  for (const item of Array.isArray(items) ? items : []) {
    if (savedNoteBucket(item) === "artifact") {
      artifacts.push(item);
    } else {
      memories.push(item);
    }
  }
  return { memories, artifacts };
}

function renderPinnedContextBar() {
  const pinnedItem = getPinnedMemoryItem();
  nextTurnContextStatusEl.textContent = pinnedItem
    ? `${pinnedItem.title} is pinned for the next turn until you clear it.`
    : "Selection only opens something in review. Pin an item here to keep it in context until you clear it.";
  pinSelectedContextButtonEl.disabled = state.busy || !getSelectedMemoryItem();
  clearPinnedContextButtonEl.disabled = state.busy || !pinnedItem;
  renderSurfaceStatus();
}

function renderMemoryGroup(container, items, context, emptyMessage) {
  const list = Array.isArray(items) ? items : [];
  container.innerHTML = "";
  if (!list.length) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = emptyMessage;
    container.appendChild(empty);
    return;
  }
  for (const item of list) {
    container.appendChild(createMemoryCard(item, context));
  }
}

function renderMemoryInspector() {
  conceptInspectorEl.innerHTML = "";
  const item = getSelectedMemoryItem();
  if (!item) {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "Select something from What I used, What I learned, or the library to review it here. Selection alone does not keep it in scope for the next turn.";
    conceptInspectorEl.appendChild(empty);
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "inspector-shell";
  if (item.isVaultNote) {
    wrap.classList.add("inspector-shell--vault");
  } else if (savedNoteBucket(item) === "artifact") {
    wrap.classList.add("inspector-shell--artifact");
  }

  const header = document.createElement("div");
  header.className = "inspector-head";

  const titleBlock = document.createElement("div");
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = itemSourceSectionLabel(item);
  const title = document.createElement("h3");
  title.className = "inspector-title";
  title.textContent = item.title || item.id;
  titleBlock.append(eyebrow, title);

  const badge = document.createElement("span");
  badge.className = "status-pill status-pill--soft";
  badge.textContent = item.isVaultNote ? item.readOnlyLabel || "read-only" : item.status || "active";
  header.append(titleBlock, badge);

  const meta = document.createElement("div");
  meta.className = "inspector-meta";
  meta.append(
    createMiniMeta("id", item.id),
    createMiniMeta("type", itemInspectorLabel(item).toLowerCase()),
    createMiniMeta("card", item.card ? "available" : "missing"),
    createMiniMeta("source", item.sourceLabel || item.source || "catalog"),
  );
  if (item.trustLabel || item.trustClass || item.trust) {
    meta.append(createMiniMeta("trust", item.trustLabel || item.trustClass || item.trust));
  }
  if (item.path || item.filename) {
    meta.append(createMiniMeta("path", item.path || item.filename));
  }
  if (!item.isVaultNote && savedNoteBucket(item) === "artifact") {
    meta.append(createMiniMeta("origin", artifactOriginLabel(item)));
    meta.append(createMiniMeta("lifecycle", artifactLifecycleLabel(item)));
  }
  if (item.type === "protocol") {
    const protocol = normalizeProtocolMetadata(item);
    meta.append(createMiniMeta("protocol", protocol.protocolKind || "custom"));
    meta.append(createMiniMeta("applies to", protocol.appliesTo.length ? protocol.appliesTo.join(", ") : "not specified"));
    meta.append(createMiniMeta("editable", protocol.modifiable ? "yes" : "no"));
    meta.append(createMiniMeta("source", protocol.isBuiltin ? "built-in" : protocol.overridesBuiltin ? "custom override" : "custom"));
  }
  if (isTurnLearnedItem(item)) {
    const learnedCorrection = buildLearnedCorrectionModel(item);
    meta.append(createMiniMeta("saved as", learnedCorrection.scopeLabel || describeLearnedScopeLabel(item)));
    meta.append(createMiniMeta("correction path", learnedCorrection.primaryActionLabel || "Revise in whiteboard"));
  }

  const summary = document.createElement("div");
  summary.className = "inspector-summary";
  renderRichText(summary, item.card || (item.isVaultNote
    ? "This reference note has no excerpt yet."
    : item.type === "concept"
      ? "This concept has no summary card yet."
      : savedNoteBucket(item) === "artifact"
        ? "This artifact has no summary card yet."
        : "This memory has no summary card yet."), { compact: true });

  const lifecycle = document.createElement("p");
  lifecycle.className = "inspector-lifecycle";
  if (!item.isVaultNote && savedNoteBucket(item) === "artifact") {
    renderRichText(lifecycle, artifactLifecycleDescription(item));
  }

  const learnedReasonText = isTurnLearnedItem(item)
    ? describeLearnedReason(item)
    : "";
  const learnedCorrection = isTurnLearnedItem(item)
    ? buildLearnedCorrectionModel(item)
    : null;
  const learnedReason = document.createElement("p");
  learnedReason.className = "inspector-lifecycle";
  if (learnedReasonText) {
    learnedReason.textContent = `Saved because: ${learnedReasonText}`;
  }

  const body = document.createElement("div");
  body.className = "inspector-body";
  const bodyLabel = document.createElement("div");
  bodyLabel.className = "inspector-body-label";
  bodyLabel.textContent = item.isVaultNote
    ? "Reference note excerpt"
    : isScenarioComparisonArtifact(item)
      ? "Comparison hub contents"
      : savedNoteBucket(item) === "artifact"
        ? "Work product contents"
        : itemInspectorLabel(item);
  const bodyText = document.createElement("div");
  bodyText.className = "inspector-pre";
  renderRichText(bodyText, item.body || (item.isVaultNote
      ? "Full reference note text is not available in this build. The memory panel has loaded the read-only excerpt."
      : item.type === "concept"
        ? "Full idea text is not available in this build. The inspector has loaded the summary card and current excerpt."
        : savedNoteBucket(item) === "artifact"
          ? "Full work product text is not available in this build. The inspector has loaded the current summary card and excerpt."
          : "Full note text is not available in this build. The inspector has loaded the current summary card and excerpt."));
  body.append(bodyLabel, bodyText);

  const footer = document.createElement("div");
  footer.className = "inspector-actions";
  const pinButton = createActionButton(
    isPinnedMemoryItem(item) ? "Unpin next-turn scope" : "Pin for next turn",
    "secondary",
  );
  pinButton.addEventListener("click", () => {
    if (isPinnedMemoryItem(item)) {
      clearPinnedContext();
    } else {
      pinMemoryItemForNextTurn(item);
    }
  });
  const relatedButton = createActionButton("Show related", "secondary");
  relatedButton.addEventListener("click", () => {
    memorySearchEl.value = item.title || item.id;
    state.memoryQuery = memorySearchEl.value;
    renderMemoryPanel();
    pushNotice("Related notes", `Showing notes related to ${item.title}.`, "info");
    openVantage({ focus: "library" });
    memoryDockEl.open = true;
  });
  if (item.type === "protocol") {
    footer.append(pinButton, relatedButton);
  } else if (!item.isVaultNote) {
    const openButton = createActionButton(
      learnedCorrection?.primaryActionLabel
        || (savedNoteBucket(item) === "artifact"
          ? (isScenarioComparisonArtifact(item) ? "Continue comparison in whiteboard" : "Continue in whiteboard")
          : "Edit in whiteboard"),
      "primary",
    );
    openButton.addEventListener("click", async () => {
      await openConceptIntoWorkspace(item.id);
    });
    footer.append(openButton, pinButton, relatedButton);
  } else {
    footer.append(pinButton, relatedButton);
  }

  const correctionGuidance = learnedCorrection
    ? document.createElement("section")
    : null;
  if (correctionGuidance) {
    correctionGuidance.className = "inspector-guidance";
    const guidanceLabel = document.createElement("div");
    guidanceLabel.className = "inspector-body-label";
    guidanceLabel.textContent = "Correction options";

    const guidanceSummary = document.createElement("p");
    guidanceSummary.className = "inspector-guidance-copy";
    guidanceSummary.textContent = learnedCorrection.summary;

    const guidanceList = document.createElement("ul");
    guidanceList.className = "inspector-guidance-list";
    for (const limitation of learnedCorrection.limitations) {
      const guidanceItem = document.createElement("li");
      guidanceItem.className = "inspector-guidance-item";
      guidanceItem.textContent = limitation;
      guidanceList.append(guidanceItem);
    }

    correctionGuidance.append(guidanceLabel, guidanceSummary, guidanceList);
  }

  const protocolEditor = item.type === "protocol"
    ? createProtocolEditorSection(item)
    : null;

  wrap.append(header, meta, summary);
  if (learnedReasonText || (!item.isVaultNote && savedNoteBucket(item) === "artifact")) {
    wrap.append(lifecycle);
  }
  if (learnedReasonText) {
    wrap.append(learnedReason);
  }
  if (correctionGuidance) {
    wrap.append(correctionGuidance);
  }
  if (protocolEditor) {
    wrap.append(protocolEditor);
  }
  wrap.append(body, footer);
  conceptInspectorEl.appendChild(wrap);
}

function createProtocolEditorSection(item) {
  const protocol = normalizeProtocolMetadata(item);
  const section = document.createElement("section");
  section.className = "protocol-editor";

  const label = document.createElement("div");
  label.className = "inspector-body-label";
  label.textContent = "Editable protocol";

  const summary = document.createElement("p");
  summary.className = "protocol-editor__summary";
  summary.textContent = protocol.isBuiltin
    ? "This is a built-in protocol. Saving creates a custom override without mutating the built-in default."
    : protocol.overridesBuiltin
      ? "This protocol customizes a built-in default."
      : "This protocol guides recurring work and can be updated here.";

  const titleInput = createProtocolInput("Title", item.title || "");
  const cardInput = createProtocolTextarea("Summary card", item.card || "", { rows: 3 });
  const appliesInput = createProtocolInput("Applies to", protocol.appliesTo.join(", "));
  const variablesInput = createProtocolTextarea(
    "Variables JSON",
    JSON.stringify(protocol.variables || {}, null, 2),
    { rows: 7, monospace: true },
  );
  const bodyInput = createProtocolTextarea("Procedure", item.body || "", { rows: 10, monospace: true });

  const status = document.createElement("p");
  status.className = "protocol-editor__status";
  status.textContent = protocol.modifiable
    ? "Edit the fields, then save to update future matching requests."
    : "This protocol is not marked modifiable.";

  const actions = document.createElement("div");
  actions.className = "protocol-editor__actions";
  const saveButton = createActionButton(protocol.isBuiltin ? "Save custom override" : "Save protocol", "primary");
  saveButton.disabled = state.busy || !protocol.modifiable || !protocol.protocolKind;
  saveButton.addEventListener("click", async () => {
    status.textContent = "Saving protocol...";
    saveButton.disabled = true;
    try {
      let variables = {};
      const variablesText = variablesInput.control.value.trim();
      if (variablesText) {
        variables = JSON.parse(variablesText);
        if (!variables || typeof variables !== "object" || Array.isArray(variables)) {
          throw new Error("Variables JSON must be an object.");
        }
      }
      const appliesTo = appliesInput.control.value
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
      const { payload, response } = await fetchJson(`/api/protocols/${encodeURIComponent(protocol.protocolKind)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: titleInput.control.value.trim(),
          card: cardInput.control.value.trim(),
          body: bodyInput.control.value,
          variables,
          applies_to: appliesTo,
        }),
      });
      if (!response.ok) {
        throw new Error(payload?.detail || `Protocol save failed with status ${response.status}`);
      }
      upsertProtocolConcept(payload);
      state.selectedConceptId = payload.id || item.id;
      status.textContent = "Protocol saved. Future matching requests can use this guidance.";
      pushNotice("Protocol saved", `${payload.title || item.title} is updated.`, "success");
      renderMemoryPanel();
      renderTurnPanel();
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : "Protocol save failed.";
      pushNotice("Protocol not saved", status.textContent, "warning");
      saveButton.disabled = state.busy || !protocol.modifiable || !protocol.protocolKind;
    }
  });
  actions.append(saveButton);

  section.append(label, summary, titleInput.field, cardInput.field, appliesInput.field, variablesInput.field, bodyInput.field, status, actions);
  return section;
}

function createProtocolInput(labelText, value) {
  const field = document.createElement("label");
  field.className = "protocol-editor__field";
  const label = document.createElement("span");
  label.textContent = labelText;
  const control = document.createElement("input");
  control.type = "text";
  control.value = value;
  field.append(label, control);
  return { field, control };
}

function createProtocolTextarea(labelText, value, { rows = 4, monospace = false } = {}) {
  const field = document.createElement("label");
  field.className = "protocol-editor__field";
  const label = document.createElement("span");
  label.textContent = labelText;
  const control = document.createElement("textarea");
  control.rows = rows;
  control.value = value;
  if (monospace) {
    control.classList.add("protocol-editor__mono");
  }
  field.append(label, control);
  return { field, control };
}

function upsertProtocolConcept(protocolPayload) {
  const normalized = normalizeConcept(protocolPayload, "concept");
  const target = normalized.scope === "experiment" ? state.sessionConcepts : state.catalogConcepts;
  const index = target.findIndex((concept) => concept.id === normalized.id);
  if (index >= 0) {
    target[index] = { ...target[index], ...normalized };
  } else {
    target.unshift(normalized);
  }
  state.turnWorkingMemory = state.turnWorkingMemory.map((item) => item.id === normalized.id ? { ...item, ...normalized } : item);
  state.turnConcepts = state.turnConcepts.map((item) => item.id === normalized.id ? { ...item, ...normalized } : item);
  rebuildConceptCatalog();
}

function normalizeWorkingMemoryItems(items, source) {
  return (Array.isArray(items) ? items : [])
    .map((item) => normalizeMemoryItem(item, source))
    .filter((item) => item.id);
}

function humanizeInterpretationMode(mode) {
  switch (String(mode || "").toLowerCase()) {
    case "scenario_lab":
      return "Scenario Lab";
    case "chat":
      return "Chat";
    default:
      return "Chat";
  }
}

function humanizeInterpretationWhiteboardMode(mode) {
  switch (String(mode || "").toLowerCase()) {
    case "offer":
      return "Invite whiteboard";
    case "draft":
      return "Draft in whiteboard";
    case "chat":
      return "Keep in chat";
    case "auto":
      return "Auto";
    default:
      return "Auto";
  }
}

function humanizeSemanticSurface(surface) {
  switch (String(surface || "").toLowerCase()) {
    case "scenario_lab":
      return "Scenario Lab";
    case "whiteboard":
      return "Draft";
    case "vantage_inspect":
      return "Inspect";
    case "artifact":
      return "Artifact";
    case "experiment":
      return "Experiment";
    case "chat":
      return "Chat";
    default:
      return humanizeSemanticToken(surface || "chat");
  }
}

function humanizeSemanticToken(value) {
  return String(value || "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function humanizeRouteConfidence(confidence) {
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return "Unknown";
  }
  if (numeric >= 0.9) {
    return "High";
  }
  if (numeric >= 0.75) {
    return "Steady";
  }
  if (numeric >= 0.55) {
    return "Tentative";
  }
  return "Low";
}


function savedNoteBucket(item) {
  const fields = [
    item?.libraryBucket,
    item?.recordKind,
    item?.kind,
    item?.type,
    item?.sourceLabel,
    item?.path,
    item?.filename,
  ]
    .map((value) => String(value || "").toLowerCase())
    .join(" ");
  if (fields.includes("artifact") || fields.includes("/artifacts/") || fields.includes("artifacts/")) {
    return "artifact";
  }
  return "memory";
}

function isTurnLearnedItem(item) {
  if (!item?.id) {
    return false;
  }
  return state.turnLearned.some((candidate) => candidate?.id === item.id && candidate?.source === item.source);
}

function normalizeLearnedReasonText(value) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text) {
    return "";
  }
  return text.endsWith(".") ? text : `${text}.`;
}

function describeLearnedReason(item) {
  const provided = normalizeLearnedReasonText(
    item?.learnedReason
    || item?.learned_reason
    || item?.whyLearned
    || item?.why_learned
    || item?.saveReason
    || item?.save_reason
    || item?.rationale,
  );
  if (provided) {
    return provided;
  }
  if (state.turnLearned.length === 1 && isTurnLearnedItem(item)) {
    const turnRationale = normalizeLearnedReasonText(
      state.turn?.metaAction?.rationale
      || state.turn?.graphAction?.summary,
    );
    if (turnRationale) {
      return turnRationale;
    }
  }
  if (artifactLifecycleValue(item) === "whiteboard_snapshot") {
    return "This draft iteration was saved so you can revisit the whiteboard work later.";
  }
  if (artifactLifecycleValue(item) === "comparison_hub") {
    return "This comparison was saved so you can reopen the scenario branches later.";
  }
  if (artifactLifecycleValue(item) === "promoted_artifact") {
    return "This whiteboard work was promoted into a reusable work product.";
  }
  if (item?.type === "concept" || item?.source === "concept") {
    return "Saved as a reusable idea from the turn.";
  }
  if (savedNoteBucket(item) === "artifact") {
    return "Saved as work you made during the turn.";
  }
  if (item?.source === "memory") {
    return "Saved as something to remember later.";
  }
  return "";
}

function buildLearnedCorrectionHint(item, correctionModel) {
  if (!correctionModel) {
    return "";
  }
  if (isPinnedMemoryItem(item)) {
    return `Correction path: ${correctionModel.primaryActionLabel}. This item is already pinned for the next turn.`;
  }
  return `Correction path: ${correctionModel.primaryActionLabel} or pin it for the next turn.`;
}

function getLearnedCorrectionItem() {
  if (!state.learnedCorrection?.itemId) {
    return null;
  }
  return state.turnLearned.find((candidate) => candidate?.id === state.learnedCorrection.itemId
    && candidate?.source === state.learnedCorrection.source) || null;
}

function syncLearnedCorrectionState({ persist = false } = {}) {
  if (!state.turnLearned.length) {
    state.learnedCorrection = createEmptyLearnedCorrectionState();
    if (persist) {
      persistTurnSnapshot();
    }
    return null;
  }
  const current = getLearnedCorrectionItem();
  if (current) {
    return current;
  }
  const first = state.turnLearned[0];
  state.learnedCorrection = {
    itemId: first.id,
    source: first.source || "",
    mode: "overview",
  };
  if (persist) {
    persistTurnSnapshot();
  }
  return first;
}

function setLearnedCorrectionTarget(item, { mode = "", persist = true } = {}) {
  if (!item?.id || !isTurnLearnedItem(item)) {
    return;
  }
  const sameItem = state.learnedCorrection?.itemId === item.id
    && state.learnedCorrection?.source === (item.source || "");
  state.learnedCorrection = {
    itemId: item.id,
    source: item.source || "",
    mode: mode || (sameItem ? state.learnedCorrection.mode || "overview" : "overview"),
  };
  if (persist) {
    persistTurnSnapshot();
  }
}

function setLearnedCorrectionMode(mode, { persist = true } = {}) {
  const item = syncLearnedCorrectionState({ persist: false });
  if (!item) {
    return;
  }
  state.learnedCorrection = {
    itemId: item.id,
    source: item.source || "",
    mode: String(mode || "overview").trim() || "overview",
  };
  if (persist) {
    persistTurnSnapshot();
  }
}

function renderLearnedCorrectionPanel() {
  if (
    !turnLearnedCorrectionPanelEl
    || !turnLearnedCorrectionSummaryEl
    || !turnLearnedCorrectionActionsEl
  ) {
    return;
  }
  turnLearnedCorrectionActionsEl.innerHTML = "";
  if (!state.turnLearned.length) {
    turnLearnedCorrectionPanelEl.hidden = true;
    turnLearnedCorrectionPanelEl.open = false;
    turnLearnedCorrectionSummaryEl.textContent = "";
    if (turnLearnedCorrectionMetaEl) {
      turnLearnedCorrectionMetaEl.textContent = "Collapsed";
    }
    return;
  }

  const item = syncLearnedCorrectionState({ persist: false });
  const correctionModel = buildLearnedCorrectionModel(item);
  const activeMode = String(state.learnedCorrection?.mode || "overview").trim() || "overview";
  const summaryText = correctionModel?.modeSummaries?.[activeMode]
    || correctionModel?.summary
    || "Direct correction works through the whiteboard.";
  const title = item?.title || item?.id || "This learned item";
  const summary = isPinnedMemoryItem(item) && activeMode === "overview"
    ? `${title}: ${summaryText} It is currently pinned for the next turn.`
    : `${title}: ${summaryText}`;
  turnLearnedCorrectionSummaryEl.textContent = summary;
  turnLearnedCorrectionPanelEl.hidden = false;
  turnLearnedCorrectionPanelEl.open = activeMode !== "overview";
  if (turnLearnedCorrectionMetaEl) {
    turnLearnedCorrectionMetaEl.textContent = activeMode === "overview"
      ? "Collapsed"
      : describeLearnedCorrectionModeLabel(activeMode, correctionModel?.scopeLabel) || "Expanded";
  }

  const openButton = createActionButton(correctionModel?.primaryActionLabel || "Revise in whiteboard", "primary");
  openButton.addEventListener("click", async () => {
    setLearnedCorrectionMode("overview");
    await openConceptIntoWorkspace(item.id);
  });

  const pinButton = createActionButton(
    isPinnedMemoryItem(item)
      ? (correctionModel?.pinnedContextLabel || "Pinned for next turn")
      : (correctionModel?.keepContextLabel || "Pin for next turn"),
    "secondary",
  );
  if (isPinnedMemoryItem(item)) {
    pinButton.classList.add("is-active");
  }
  pinButton.addEventListener("click", () => {
    setLearnedCorrectionMode("overview");
    if (isPinnedMemoryItem(item)) {
      clearPinnedContext();
    } else {
      pinMemoryItemForNextTurn(item);
    }
  });

  const wrongButton = createActionButton(
    describeLearnedCorrectionModeLabel("wrong", correctionModel?.scopeLabel) || "How to mark wrong",
    "secondary",
  );
  if (activeMode === "wrong") {
    wrongButton.classList.add("is-active");
  }
  wrongButton.addEventListener("click", () => {
    setLearnedCorrectionMode("wrong");
    renderTurnPanel();
  });

  const temporaryButton = createActionButton(
    describeLearnedCorrectionModeLabel("temporary", correctionModel?.scopeLabel)
      || (correctionModel?.scopeLabel === "Temporary in this experiment" ? "Already temporary" : "How to make temporary"),
    "secondary",
  );
  if (activeMode === "temporary") {
    temporaryButton.classList.add("is-active");
  }
  temporaryButton.disabled = correctionModel?.scopeLabel === "Temporary in this experiment";
  temporaryButton.addEventListener("click", () => {
    setLearnedCorrectionMode("temporary");
    renderTurnPanel();
  });

  const forgetButton = createActionButton(
    describeLearnedCorrectionModeLabel("forget", correctionModel?.scopeLabel) || "How to forget",
    "secondary",
  );
  if (activeMode === "forget") {
    forgetButton.classList.add("is-active");
  }
  forgetButton.addEventListener("click", () => {
    setLearnedCorrectionMode("forget");
    renderTurnPanel();
  });

  turnLearnedCorrectionActionsEl.append(openButton, pinButton, wrongButton, temporaryButton, forgetButton);
}

function learnedTypeLabel(item) {
  if (item?.type === "concept" || item?.source === "concept") {
    return "Idea";
  }
  if (savedNoteBucket(item) === "artifact") {
    return "Work product";
  }
  if (item?.source === "memory") {
    return "Note";
  }
  return "Saved item";
}

function itemTypeLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "memory trace";
  }
  if (item?.type === "protocol") {
    return "protocol";
  }
  if (item?.isVaultNote) {
    return "reference";
  }
  if (item?.type === "concept") {
    return "insight";
  }
  return savedNoteBucket(item) === "artifact" ? "work product" : "memory";
}

function itemInspectorLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "Memory Trace";
  }
  if (item?.type === "protocol") {
    return "Protocol";
  }
  if (item?.isVaultNote) {
    return "Reference note";
  }
  if (item?.type === "concept") {
    return "Reusable insight";
  }
  if (isScenarioComparisonArtifact(item)) {
    return "Comparison hub";
  }
  return savedNoteBucket(item) === "artifact" ? "Work product" : "Memory";
}

function itemSourceSectionLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "Memory Trace";
  }
  if (item?.type === "protocol") {
    return "Protocols";
  }
  if (item?.isVaultNote) {
    return item.sourceLabel || "Reference notes";
  }
  if (item?.type === "concept") {
    return "Reusable insights";
  }
  if (isScenarioComparisonArtifact(item)) {
    return "Comparison hubs";
  }
  if (item?.source === "session") {
    return savedNoteBucket(item) === "artifact" ? "Staged work product" : "Staged memory";
  }
  return savedNoteBucket(item) === "artifact" ? "Work products" : "Memories";
}

function isScenarioComparisonArtifact(item) {
  return savedNoteBucket(item) === "artifact"
    && String(item?.scenarioKind || item?.scenario_kind || "").toLowerCase() === "comparison";
}

function artifactLifecycleValue(item) {
  return String(item?.artifactLifecycle || item?.artifact_lifecycle || "").trim().toLowerCase();
}

function artifactOriginValue(item) {
  return String(item?.artifactOrigin || item?.artifact_origin || "").trim().toLowerCase();
}

function artifactLifecycleLabel(item) {
  switch (artifactLifecycleValue(item)) {
    case "comparison_hub":
      return "comparison hub";
    case "whiteboard_snapshot":
      return "saved whiteboard";
    case "promoted_artifact":
      return "promoted artifact";
    default:
      return isScenarioComparisonArtifact(item) ? "comparison hub" : "artifact";
  }
}

function artifactOriginLabel(item) {
  switch (artifactOriginValue(item)) {
    case "scenario_lab":
      return "Scenario Lab";
    case "whiteboard":
      return "Draft";
    case "library":
      return "Library";
    default:
      if (isScenarioComparisonArtifact(item)) {
        return "Scenario Lab";
      }
      if (item?.source === "session") {
        return "Session";
      }
      if (Array.isArray(item?.comes_from) && item.comes_from.length) {
        return "Derived item";
      }
      return "Library";
  }
}

function artifactLifecycleDescription(item) {
  switch (artifactLifecycleValue(item)) {
    case "comparison_hub":
      return "Durable Scenario Lab comparison in the Library. Inspect it here read-only, or reopen it in the whiteboard when you want to continue from the saved comparison.";
    case "whiteboard_snapshot":
      return "Saved whiteboard in the Library. Inspect it here read-only, or reopen it in the whiteboard when you want to continue from this saved snapshot.";
    case "promoted_artifact":
      return "Promoted artifact in the Library. Inspect it here read-only, or reopen it in the whiteboard when you want to continue from the promoted version.";
    default:
      return "Durable work product in the Library. Inspect it here read-only, or reopen it in the whiteboard when you want to continue from the saved version.";
  }
}

function lineageSummary(item) {
  const revisionParentId = item?.revisionParentId || item?.revision_parent_id || "";
  const derivedFromId = item?.derivedFromId || item?.derived_from_id || "";
  const comesFrom = Array.isArray(item?.comes_from) ? item.comes_from : [];
  if (revisionParentId) {
    return `Revision of ${revisionParentId}.`;
  }
  if (!derivedFromId) {
    return "";
  }
  switch (artifactLifecycleValue(item)) {
    case "comparison_hub": {
      const relatedCount = Math.max(comesFrom.length - 1, 0);
      return relatedCount
        ? `Comparison hub anchored on ${derivedFromId} with ${relatedCount} related branch${relatedCount === 1 ? "" : "es"}.`
        : `Comparison hub anchored on ${derivedFromId}.`;
    }
    case "whiteboard_snapshot":
      return `Saved from whiteboard ${derivedFromId}.`;
    case "promoted_artifact":
      return `Promoted from whiteboard ${derivedFromId}.`;
    default:
      break;
  }
  if (isScenarioComparisonArtifact(item) && comesFrom.length > 1) {
    const relatedCount = comesFrom.length - 1;
    return `Derived from ${derivedFromId} with ${relatedCount} related branch${relatedCount === 1 ? "" : "es"}.`;
  }
  return `Derived from ${derivedFromId}.`;
}

function createMemoryCard(item, context) {
  const article = document.createElement("article");
  article.className = "concept-card";
  if (context === "turn" || context === "learned") {
    article.classList.add("concept-card--turn");
  }
  if (item.isVaultNote) {
    article.classList.add("concept-card--vault");
  }
  if (item.id === state.selectedConceptId || item.id === state.selectedVaultNoteId) {
    article.classList.add("is-selected");
  }
  article.dataset.conceptId = item.id;
  article.dataset.memoryKind = item.isVaultNote ? "vault_note" : item.type === "concept" ? "concept" : "saved_note";

  const top = document.createElement("div");
  top.className = "concept-header";
  const type = document.createElement("span");
  type.className = "concept-type";
  type.textContent = itemTypeLabel(item);
  const id = document.createElement("span");
  id.className = "concept-id";
  id.textContent = item.path || item.filename || item.id;
  top.append(type, id);

  const title = document.createElement("h3");
  title.className = "concept-title";
  title.textContent = item.title || item.id;

  const summary = document.createElement("div");
  summary.className = "concept-card-text";
  renderRichText(summary, item.card || (item.isVaultNote
    ? "No reference note excerpt available."
    : item.source === "memory_trace" || item.type === "memory_trace"
      ? "No memory trace summary available."
    : item.type === "concept"
      ? "No concept card available."
      : "No saved note card available."), { compact: true });

  const recallReasonText = shouldShowRecallReason(item, context)
    ? describeRecallReason(item)
    : "";
  const recallReason = recallReasonText
    ? document.createElement("p")
    : null;
  if (recallReason) {
    recallReason.className = "concept-card-text concept-card-text--secondary concept-card-text--reason";
    recallReason.textContent = `Why recalled: ${recallReasonText}`;
  }

  const learnedReasonText = context === "learned"
    ? describeLearnedReason(item)
    : "";
  const learnedCorrection = context === "learned"
    ? buildLearnedCorrectionModel(item)
    : null;
  const learnedReason = learnedReasonText
    ? document.createElement("p")
    : null;
  if (learnedReason) {
    learnedReason.className = "concept-card-text concept-card-text--secondary concept-card-text--reason";
    learnedReason.textContent = `Saved because: ${learnedReasonText}`;
  }
  const learnedCorrectionHintText = context === "learned"
    ? buildLearnedCorrectionHint(item, learnedCorrection)
    : "";
  const learnedCorrectionHint = learnedCorrectionHintText
    ? document.createElement("p")
    : null;
  if (learnedCorrectionHint) {
    learnedCorrectionHint.className = "concept-card-text concept-card-text--secondary concept-card-text--hint";
    learnedCorrectionHint.textContent = learnedCorrectionHintText;
  }

  const meta = document.createElement("div");
  meta.className = "concept-meta-row";
  if (context === "turn") {
    meta.append(createBadge("pulled in", "accent"));
  } else if (context === "reasoning-candidate") {
    meta.append(
      createBadge(
        item.reasoningStatusLabel || "considered",
        item.reasoningStatusLabel === "used for recall" ? "accent" : "soft",
      ),
    );
  } else if (context === "reasoning-recall") {
    meta.append(createBadge("used for recall", "accent"));
  } else if (context === "trace") {
    meta.append(
      createBadge(
        item.source === "memory_trace" && item.id === state.turnMemoryTraceRecord?.id
          ? "captured this turn"
          : "recent history",
        "soft",
      ),
    );
  } else if (context === "learned") {
    meta.append(createBadge("learned this turn", "success"));
    meta.append(createBadge(learnedCorrection?.scopeLabel || describeLearnedScopeLabel(item), "soft"));
    meta.append(createBadge(learnedTypeLabel(item), "soft"));
  }
  if (isPinnedMemoryItem(item)) {
    meta.append(createBadge("pinned context", "success"));
  }
  if (item.isVaultNote) {
    meta.append(createBadge("read-only", "warm"));
  } else if (item.type === "protocol") {
    meta.append(createBadge("protocol", "accent"));
  } else if (item.type === "concept" && item.source !== "session") {
    meta.append(createBadge("idea library", "accent"));
  } else if (item.source === "session") {
    meta.append(createBadge(savedNoteBucket(item) === "artifact" ? "staged artifact" : "staged memory", "warm"));
  }
  if (item.sourceLabel) {
    meta.append(createBadge(item.sourceLabel, item.isVaultNote ? "warm" : "accent"));
  }
  if (item.trustLabel || item.trustClass || item.trust) {
    meta.append(createBadge(item.trustLabel || item.trustClass || item.trust, "soft"));
  }
  if (item.status) {
    meta.append(createBadge(item.status, "soft"));
  }
  if (savedNoteBucket(item) === "artifact" && !item.isVaultNote) {
    meta.append(createBadge(artifactLifecycleLabel(item), isScenarioComparisonArtifact(item) ? "accent" : "soft"));
  }
  if (item.lineageKind === "revision" || item.revisionParentId || item.revision_parent_id) {
    meta.append(createBadge("revision", "soft"));
  } else if ((item.derivedFromId || item.derived_from_id) && !isScenarioComparisonArtifact(item)) {
    meta.append(createBadge("derived", "soft"));
  }
  if ((item.links_to || []).length) {
    meta.append(createBadge(`${item.links_to.length} links`, "soft"));
  }

  const lineageText = lineageSummary(item);
  const lineage = lineageText
    ? document.createElement("p")
    : null;
  if (lineage) {
    lineage.className = "concept-card-text concept-card-text--secondary";
    lineage.textContent = lineageText;
  }

  const actions = document.createElement("div");
  actions.className = "concept-actions";
  const inspectButton = createActionButton(context === "learned" ? "Review" : "Inspect", "secondary");
  inspectButton.addEventListener("click", (event) => {
    event.stopPropagation();
    if (context === "learned") {
      setLearnedCorrectionTarget(item, { mode: "overview" });
    }
    if (item.source === "memory_trace") {
      pushNotice("Memory Trace item", "Memory Trace items stay inspectable inside this turn and do not open in the library inspector.", "info");
      return;
    }
    if (item.isVaultNote) {
      selectVaultNote(item.id);
      return;
    }
    selectConcept(item.id);
  });
  const canOpenItem = !item.isVaultNote
    && item.type !== "protocol"
    && item.source !== "memory_trace"
    && context !== "reasoning-candidate"
    && context !== "reasoning-recall";
  if (canOpenItem) {
    const openButton = createActionButton(
      context === "learned"
        ? (learnedCorrection?.primaryActionLabel || "Revise in whiteboard")
        : (savedNoteBucket(item) === "artifact"
            ? (isScenarioComparisonArtifact(item) ? "Reopen comparison" : "Reopen")
            : "Open"),
      "primary",
    );
    openButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (context === "learned") {
        setLearnedCorrectionTarget(item, { mode: "overview" });
      }
      await openConceptIntoWorkspace(item.id);
    });
    if (context === "learned") {
      const keepButton = createActionButton(
        isPinnedMemoryItem(item)
          ? (learnedCorrection?.pinnedContextLabel || "Pinned for next turn")
          : (learnedCorrection?.keepContextLabel || "Pin for next turn"),
        "secondary",
      );
      keepButton.addEventListener("click", (event) => {
        event.stopPropagation();
        setLearnedCorrectionTarget(item, { mode: "overview" });
        if (isPinnedMemoryItem(item)) {
          clearPinnedContext();
        } else {
          pinMemoryItemForNextTurn(item);
        }
      });
      actions.append(openButton, keepButton, inspectButton);
    } else {
      actions.append(openButton, inspectButton);
    }
  } else {
    actions.append(inspectButton);
  }

  article.addEventListener("click", () => {
    if (context === "learned") {
      setLearnedCorrectionTarget(item, { mode: "overview" });
    }
    if (item.source === "memory_trace") {
      pushNotice("Memory Trace item", "Memory Trace items stay inspectable inside this turn and do not open in the library inspector.", "info");
      return;
    }
    if (item.isVaultNote) {
      selectVaultNote(item.id);
    } else {
      selectConcept(item.id);
    }
  });

  article.append(top, title, summary);
  if (recallReason) {
    article.append(recallReason);
  }
  if (learnedReason) {
    article.append(learnedReason);
  }
  if (learnedCorrectionHint) {
    article.append(learnedCorrectionHint);
  }
  if (lineage) {
    article.append(lineage);
  }
  article.append(meta);
  if (item.type === "protocol" && context === "turn") {
    article.append(createProtocolEditorSection(item));
  }
  article.append(actions);
  return article;
}

function createConceptCard(concept, context) {
  return createMemoryCard(concept, context);
}

function createScenarioBranchCard(branch) {
  const detailsModel = deriveScenarioBranchDetails(branch);
  const isActiveWhiteboard = state.workspace.workspaceId === branch.workspace_id;
  const isInspectingDetails = state.turn.scenarioBranchInspectionWorkspaceId === branch.workspace_id;
  const article = document.createElement("article");
  article.className = "concept-card concept-card--turn scenario-lab__branch-card";
  article.dataset.scenarioBranchWorkspaceId = branch.workspace_id || "";
  article.tabIndex = -1;
  if (isActiveWhiteboard) {
    article.classList.add("scenario-lab__branch-card--active");
  }
  if (isInspectingDetails) {
    article.classList.add("scenario-lab__branch-card--inspecting");
  }

  const top = document.createElement("div");
  top.className = "concept-header";
  const type = document.createElement("span");
  type.className = "concept-type";
  type.textContent = "branch";
  const id = document.createElement("span");
  id.className = "concept-id";
  id.textContent = humanizeScenarioLabel(branch.label, isActiveWhiteboard ? "Active whiteboard" : "Whiteboard ready");
  top.append(type, id);

  const title = document.createElement("h3");
  title.className = "concept-title";
  title.textContent = branch.title || branch.workspace_id || "Scenario branch";

  const summary = document.createElement("p");
  summary.className = "concept-card-text";
  summary.textContent = branch.card || branch.summary || "Scenario branch ready to revisit in the whiteboard.";

  const meta = document.createElement("div");
  meta.className = "concept-meta-row";
  meta.append(createBadge("scenario branch", "accent"));
  if (isInspectingDetails) {
    meta.append(createBadge("detail focus", "success"));
  }
  if (isActiveWhiteboard) {
    meta.append(createBadge("active whiteboard", "success"));
  }
  if (branch.confidence) {
    meta.append(createBadge(describeScenarioBranchConfidence(branch.confidence), "soft"));
  }
  if (branch.status) {
    meta.append(createBadge(branch.status, "soft"));
  }

  const details = document.createElement("div");
  details.className = "scenario-lab__branch-meta";
  if (detailsModel.question) {
    details.append(createMiniMeta("question", detailsModel.question));
  }
  if (detailsModel.confidence) {
    details.append(createMiniMeta("confidence", describeScenarioBranchConfidence(detailsModel.confidence)));
  }
  if (branch.riskSummary || branch.risk_summary) {
    details.append(createMiniMeta("headline risk", branch.riskSummary || branch.risk_summary));
  }

  const signals = document.createElement("div");
  signals.className = "scenario-lab__signal-grid";
  appendScenarioListBlock(signals, "Shared assumptions", detailsModel.sharedAssumptions);
  appendScenarioListBlock(signals, "Risks", detailsModel.risks);
  appendScenarioListBlock(signals, "Preserved assumptions", detailsModel.preservedAssumptions);
  appendScenarioListBlock(signals, "Changed assumptions", detailsModel.changedAssumptions);
  appendScenarioListBlock(signals, "Open questions", detailsModel.openQuestions);

  article.append(top, title, summary, meta);
  if (details.children.length) {
    article.append(details);
  }
  if (signals.children.length) {
    article.append(signals);
  }
  return article;
}

function createScenarioArtifactCard(artifact) {
  const item = normalizeMemoryItem(artifact, "scenario-artifact");
  const detailsModel = deriveScenarioArtifactDetails(item);
  const branchRoster = Array.isArray(detailsModel.branchIndex) ? detailsModel.branchIndex : [];
  const linkedBranchCount = branchRoster.length || (Array.isArray(item.branchWorkspaceIds) ? item.branchWorkspaceIds.length : 0);
  const isSelected = item.id === state.selectedConceptId;
  const article = document.createElement("article");
  article.className = "concept-card scenario-lab__artifact-card";
  if (isSelected) {
    article.classList.add("is-selected");
  }

  const top = document.createElement("div");
  top.className = "concept-header";
  const type = document.createElement("span");
  type.className = "concept-type";
  type.textContent = "comparison hub";
  const id = document.createElement("span");
  id.className = "concept-id";
  id.textContent = isSelected ? "Open in review" : "Durable revisit hub";
  top.append(type, id);

  const title = document.createElement("h3");
  title.className = "concept-title";
  title.textContent = item.title || "Scenario Comparison";

  const summary = document.createElement("p");
  summary.className = "concept-card-text";
  summary.textContent = item.card || detailsModel.summary || "Saved comparison ready to inspect or reopen in the whiteboard.";

  let recommendationLead = null;
  if (detailsModel.recommendation) {
    recommendationLead = document.createElement("p");
    recommendationLead.className = "concept-card-text concept-card-text--secondary scenario-lab__artifact-recommendation";
    recommendationLead.textContent = detailsModel.recommendation;
  }

  const meta = document.createElement("div");
  meta.className = "concept-meta-row";
  meta.append(createBadge("comparison hub", "accent"));
  if (linkedBranchCount) {
    meta.append(createBadge(`${linkedBranchCount} branches indexed`, "soft"));
  }
  if (item.status) {
    meta.append(createBadge(item.status, "soft"));
  }

  const lifecycle = document.createElement("div");
  lifecycle.className = "scenario-lab__artifact-lifecycle";
  lifecycle.textContent = isSelected
    ? "This comparison is open in review now. Its recommendation and linked branch roster remain the durable anchor for this Scenario Lab run."
    : "Saved this turn as the durable anchor for this Scenario Lab run. Review the recommendation and linked branch roster here, then inspect or reopen individual branches as needed.";

  const signals = document.createElement("div");
  signals.className = "scenario-lab__signal-grid";
  appendScenarioListBlock(signals, "Shared assumptions", detailsModel.sharedAssumptions);
  appendScenarioListBlock(signals, "Tradeoffs", detailsModel.tradeoffs);
  appendScenarioListBlock(signals, "Next steps", detailsModel.nextSteps);

  const branchHub = document.createElement("div");
  branchHub.className = "scenario-lab__hub-roster";
  for (const branch of branchRoster) {
    branchHub.append(createScenarioHubBranchCard(branch));
  }

  const actions = document.createElement("div");
  actions.className = "concept-actions scenario-lab__card-actions";
  const inspectButton = createActionButton(isSelected ? "Inspecting comparison" : "Inspect comparison", "secondary");
  inspectButton.disabled = isSelected;
  inspectButton.addEventListener("click", (event) => {
    event.stopPropagation();
    selectConcept(item.id);
  });
  const openButton = createActionButton("Reopen comparison in whiteboard", "secondary");
  openButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await openConceptIntoWorkspace(item.id);
  });
  actions.append(inspectButton, openButton);

  article.addEventListener("click", () => {
    selectConcept(item.id);
  });

  article.append(top, title, summary);
  if (recommendationLead) {
    article.append(recommendationLead);
  }
  article.append(meta, lifecycle);
  if (signals.children.length) {
    article.append(signals);
  }
  if (branchHub.children.length) {
    article.append(branchHub);
  }
  article.append(actions);
  return article;
}

function createScenarioHubBranchCard(branch) {
  const workspaceId = branch?.workspace_id || branch?.workspaceId || "";
  const isActiveWhiteboard = Boolean(workspaceId) && state.workspace.workspaceId === workspaceId;
  const row = document.createElement("div");
  row.className = "scenario-lab__hub-branch";

  const copy = document.createElement("div");
  copy.className = "scenario-lab__hub-branch-copy";

  const title = document.createElement("p");
  title.className = "scenario-lab__hub-branch-title";
  title.textContent = branch.title || workspaceId || "Scenario branch";

  const summary = document.createElement("p");
  summary.className = "scenario-lab__hub-branch-summary";
  summary.textContent = branch.summary || "Reopen this branch from the comparison hub.";

  const meta = document.createElement("div");
  meta.className = "scenario-lab__branch-meta";
  if (branch.label) {
    meta.append(createBadge(humanizeScenarioLabel(branch.label, branch.label), "soft"));
  }
  meta.append(createBadge(isActiveWhiteboard ? "active whiteboard" : "linked branch", isActiveWhiteboard ? "success" : "soft"));

  copy.append(title, summary, meta);
  row.append(copy);

  if (workspaceId) {
    const actions = document.createElement("div");
    actions.className = "scenario-lab__hub-branch-actions";
    const inspectButton = createActionButton(
      state.turn.scenarioBranchInspectionWorkspaceId === workspaceId ? "Inspecting details" : "Inspect details",
      "secondary",
    );
    inspectButton.disabled = state.turn.scenarioBranchInspectionWorkspaceId === workspaceId;
    inspectButton.addEventListener("click", (event) => {
      event.stopPropagation();
      inspectScenarioBranchDetails(workspaceId);
    });
    const openButton = createActionButton(isActiveWhiteboard ? "Already open" : "Reopen branch", "secondary");
    openButton.disabled = isActiveWhiteboard;
    openButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await openWorkspace(workspaceId);
    });
    actions.append(inspectButton, openButton);
    row.append(actions);
  }

  return row;
}

function inspectScenarioBranchDetails(workspaceId) {
  if (!workspaceId) {
    return;
  }
  state.turn.scenarioBranchInspectionWorkspaceId = workspaceId;
  state.surface = openVantageSurface(state.surface);
  scenarioDockEl.open = true;
  persistTurnSnapshot();
  renderViewState();
  renderTurnPanel();
  window.requestAnimationFrame(() => {
    const branchCard = Array.from(
      scenarioLabSectionEl.querySelectorAll("[data-scenario-branch-workspace-id]"),
    ).find((node) => node.dataset.scenarioBranchWorkspaceId === workspaceId);
    if (!branchCard) {
      return;
    }
    branchCard.scrollIntoView({ behavior: "smooth", block: "center" });
    branchCard.focus({ preventScroll: true });
  });
}

function selectConcept(conceptId, { silent = false, source = "user" } = {}) {
  const concept = getConceptById(conceptId);
  if (!concept) {
    if (!silent) {
      pushNotice("Item unavailable", "That concept, memory, or artifact could not be found in review.", "warning");
    }
    return;
  }
  state.selectedConceptId = concept.id;
  state.selectedVaultNoteId = "";
  state.selectionOrigin = source;
  if (isTurnLearnedItem(concept)) {
    setLearnedCorrectionTarget(concept, { persist: false });
  }
  persistTurnSnapshot();
  if (!silent) {
    const label = concept.type === "concept"
      ? "Idea selected"
      : concept.type === "protocol"
        ? "Protocol selected"
        : savedNoteBucket(concept) === "artifact"
          ? "Work product selected"
          : "Note selected";
    pushNotice(label, `${concept.title} is now open in review.`, "info");
  }
  renderMemoryPanel();
  renderTurnPanel();
}

function selectVaultNote(vaultNoteId, { silent = false, source = "user" } = {}) {
  const note = getVaultNoteById(vaultNoteId);
  if (!note) {
    if (!silent) {
      pushNotice("Reference note unavailable", "That reference note could not be found in memory.", "warning");
    }
    return;
  }
  state.selectedVaultNoteId = note.id;
  state.selectedConceptId = "";
  state.selectionOrigin = source;
  persistTurnSnapshot();
  if (!silent) {
    pushNotice("Reference note selected", `${note.title} is now open in review.`, "info");
  }
  renderMemoryPanel();
  renderTurnPanel();
}

function pinSelectedMemoryForNextTurn() {
  const item = getSelectedMemoryItem();
  if (!item) {
    pushNotice("Nothing selected", "Inspect an idea, note, or reference note before pinning it for the next turn.", "info");
    return;
  }
  pinMemoryItemForNextTurn(item);
}

function pinMemoryItemForNextTurn(item) {
  if (!item) {
    return;
  }
  state.pinnedContext = {
    id: item.id,
    kind: item.isVaultNote ? "vault_note" : "concept",
  };
  persistTurnSnapshot();
  renderMemoryPanel();
  renderTurnPanel();
  pushNotice("Context pinned", `${item.title} will stay in pinned context until you clear it.`, "success");
}

function clearPinnedContext({ silent = false } = {}) {
  if (!state.pinnedContext) {
    return;
  }
  state.pinnedContext = null;
  persistTurnSnapshot();
  renderMemoryPanel();
  renderTurnPanel();
  if (!silent) {
    pushNotice("Pinned context cleared", "No library item is pinned for upcoming turns.", "info");
  }
}

function getPinnedMemoryItem() {
  if (!state.pinnedContext?.id) {
    return null;
  }
  return state.pinnedContext.kind === "vault_note"
    ? getVaultNoteById(state.pinnedContext.id)
    : getConceptById(state.pinnedContext.id);
}

function isPinnedMemoryItem(item) {
  if (!item || !state.pinnedContext) {
    return false;
  }
  return state.pinnedContext.id === item.id
    && state.pinnedContext.kind === (item.isVaultNote ? "vault_note" : "concept");
}

function prunePinnedContextIfMissing() {
  if (state.pinnedContext && !getPinnedMemoryItem()) {
    clearPinnedContext({ silent: true });
  }
}

function getSelectedConcept() {
  return getConceptById(state.selectedConceptId);
}

function getSelectedVaultNote() {
  return getVaultNoteById(state.selectedVaultNoteId);
}

function getSelectedMemoryItem() {
  return getSelectedConcept() || getSelectedVaultNote();
}

function getSelectedMemoryId() {
  return state.selectedConceptId || state.selectedVaultNoteId || null;
}

function getPinnedContextIdForChat() {
  return state.pinnedContext?.id || null;
}

function getSelectedMemoryIdForChat() {
  return getPinnedContextIdForChat();
}

function getConceptById(conceptId) {
  return (
    state.turnWorkingMemory.find((concept) => concept.id === conceptId)
    || state.turnConcepts.find((concept) => concept.id === conceptId)
    || state.turnSavedNotes.find((concept) => concept.id === conceptId)
    || state.allConcepts.find((concept) => concept.id === conceptId)
    || state.allSavedNotes.find((concept) => concept.id === conceptId)
    || null
  );
}

function getVaultNoteById(vaultNoteId) {
  return state.allVaultNotes.find((note) => note.id === vaultNoteId) || null;
}

function getVisibleConcepts(query) {
  const concepts = [...state.allConcepts];
  if (!query) {
    return concepts.sort((left, right) => rankConcept(right, "") - rankConcept(left, ""));
  }
  return concepts
    .map((concept) => ({ concept, score: rankConcept(concept, query) }))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || compareConcepts(left.concept, right.concept))
    .map((entry) => entry.concept);
}

function getVisibleVaultNotes(query) {
  const notes = [...state.allVaultNotes];
  if (!query) {
    return notes.sort((left, right) => rankMemoryItem(right, "") - rankMemoryItem(left, ""));
  }
  return notes
    .map((note) => ({ note, score: rankMemoryItem(note, query) }))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || compareMemoryItems(left.note, right.note))
    .map((entry) => entry.note);
}

function getVisibleMemoryItems(query) {
  return {
    concepts: getVisibleConcepts(query),
    savedNotes: getVisibleSavedNotes(query),
    vaultNotes: getVisibleVaultNotes(query),
  };
}

function getVisibleSavedNotes(query) {
  const notes = [...state.allSavedNotes];
  if (!query) {
    return notes.sort((left, right) => rankSavedNote(right, "") - rankSavedNote(left, ""));
  }
  return notes
    .map((note) => ({ note, score: rankSavedNote(note, query) }))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || compareConcepts(left.note, right.note))
    .map((entry) => entry.note);
}

function rankConcept(concept, query) {
  const title = (concept.title || "").toLowerCase();
  const card = (concept.card || "").toLowerCase();
  const body = (concept.body || "").toLowerCase();
  const id = (concept.id || "").toLowerCase();
  const status = (concept.status || "").toLowerCase();
  if (!query) {
    let score = 0;
    if (concept.id === state.selectedConceptId) score += 5;
    if (state.turnConcepts.some((item) => item.id === concept.id)) score += 3;
    if (concept.source === "session") score += 4;
    return score;
  }
  const terms = query
    .toLowerCase()
    .split(/[\s,]+/)
    .map((term) => term.trim())
    .filter(Boolean);
  let score = 0;
  for (const term of terms) {
    if (!term) continue;
    if (id === term) score += 12;
    if (title === term) score += 10;
    if (title.includes(term)) score += 6;
    if (card.includes(term)) score += 4;
    if (body.includes(term)) score += 2;
    if (status.includes(term)) score += 1;
  }
  if (concept.id === state.selectedConceptId) score += 1;
  if (state.turnConcepts.some((item) => item.id === concept.id)) score += 2;
  return score;
}

function rankSavedNote(note, query) {
  const title = (note.title || "").toLowerCase();
  const card = (note.card || "").toLowerCase();
  const body = (note.body || "").toLowerCase();
  const id = (note.id || "").toLowerCase();
  const status = (note.status || "").toLowerCase();
  if (!query) {
    let score = 0;
    if (note.id === state.selectedConceptId) score += 5;
    if (state.turnSavedNotes.some((item) => item.id === note.id)) score += 3;
    if (note.source === "session") score += 4;
    return score;
  }
  const terms = query
    .toLowerCase()
    .split(/[\s,]+/)
    .map((term) => term.trim())
    .filter(Boolean);
  let score = 0;
  for (const term of terms) {
    if (!term) continue;
    if (id === term) score += 12;
    if (title === term) score += 10;
    if (title.includes(term)) score += 6;
    if (card.includes(term)) score += 4;
    if (body.includes(term)) score += 2;
    if (status.includes(term)) score += 1;
  }
  if (note.id === state.selectedConceptId) score += 1;
  if (state.turnSavedNotes.some((item) => item.id === note.id)) score += 2;
  return score;
}

function compareConcepts(left, right) {
  return (left.title || "").localeCompare(right.title || "");
}

function compareMemoryItems(left, right) {
  return compareConcepts(left, right);
}

function rankMemoryItem(item, query) {
  if (item.isVaultNote) {
    const title = (item.title || "").toLowerCase();
    const card = (item.card || "").toLowerCase();
    const body = (item.body || "").toLowerCase();
    const id = (item.id || "").toLowerCase();
    const path = (item.path || item.filename || "").toLowerCase();
    const sourceLabel = (item.sourceLabel || "").toLowerCase();
    const trustLabel = (item.trustLabel || item.trustClass || item.trust || "").toLowerCase();
    if (!query) {
      let score = 0;
      if (item.id === state.selectedVaultNoteId) score += 5;
      if (state.turnVaultNotes.some((note) => note.id === item.id)) score += 3;
      if (item.readOnly) score += 2;
      return score;
    }
    const terms = query
      .toLowerCase()
      .split(/[\s,]+/)
      .map((term) => term.trim())
      .filter(Boolean);
    let score = 0;
    for (const term of terms) {
      if (!term) continue;
      if (id === term) score += 12;
      if (path.includes(term)) score += 10;
      if (title === term) score += 9;
      if (title.includes(term)) score += 6;
      if (card.includes(term)) score += 4;
      if (body.includes(term)) score += 2;
      if (sourceLabel.includes(term)) score += 1;
      if (trustLabel.includes(term)) score += 1;
    }
    if (item.id === state.selectedVaultNoteId) score += 1;
    if (state.turnVaultNotes.some((note) => note.id === item.id)) score += 2;
    return score;
  }
  return rankConcept(item, query);
}

function normalizeConceptList(concepts, source) {
  return concepts
    .map((concept) => normalizeConcept(concept, source))
    .filter((concept) => concept.id);
}

function normalizeMemoryPayload(payload, source) {
  const savedNotes = [];
  const referenceNotes = [];
  const collections = [];
  for (const candidate of [payload].filter(Boolean)) {
    collections.push(
      { items: candidate?.saved_notes, hint: source },
      { items: candidate?.reference_notes, hint: `${source}-vault` },
      { items: candidate?.results, hint: source },
    );
  }
  for (const collection of collections) {
    if (!Array.isArray(collection.items)) {
      continue;
    }
    const normalized = normalizeMemoryList(collection.items, collection.hint);
    savedNotes.push(...normalized.savedNotes);
    referenceNotes.push(...normalized.referenceNotes);
  }
  return {
    savedNotes: dedupeMemoryItems(savedNotes, "saved_note"),
    referenceNotes: dedupeMemoryItems(referenceNotes, "vault_note"),
  };
}

function normalizeMemoryList(items, source) {
  const savedNotes = [];
  const referenceNotes = [];
  for (const item of items) {
    const normalized = normalizeMemoryItem(item, source);
    if (!normalized.id) {
      continue;
    }
    if (normalized.isVaultNote) {
      referenceNotes.push(normalized);
    } else {
      savedNotes.push(normalized);
    }
  }
  return { savedNotes, referenceNotes };
}

function normalizeConcept(concept, source) {
  if (!concept || typeof concept !== "object") {
    return {
      id: "",
      title: "",
      type: "concept",
      card: "",
      body: "",
      status: "active",
      links_to: [],
      comes_from: [],
      source,
    };
  }
  return {
    id: concept.id || concept.filename || concept.title || "",
    title: concept.title || concept.id || concept.filename || "Untitled concept",
    kind: concept.kind || "concept",
    type: concept.type || "concept",
    protocol: normalizeProtocolMetadata(concept),
    card: concept.card || concept.summary || concept.description || "",
    body: concept.body || concept.content || concept.markdown || "",
    status: concept.status || "active",
    links_to: Array.isArray(concept.links_to) ? concept.links_to : Array.isArray(concept.linksTo) ? concept.linksTo : [],
    comes_from: Array.isArray(concept.comes_from) ? concept.comes_from : [],
    derived_from_id: concept.derived_from_id || concept.derivedFromId || null,
    revision_parent_id: concept.revision_parent_id || concept.revisionParentId || null,
    lineage_kind: concept.lineage_kind || concept.lineageKind || (Array.isArray(concept.comes_from) && concept.comes_from.length ? "provenance" : "none"),
    filename: concept.filename || "",
    source: concept.source || source,
    score: concept.score ?? null,
  };
}

function normalizeMemoryItem(item, source) {
  const normalized = normalizeConcept(item, source);
  if (!item || typeof item !== "object") {
    return {
      ...normalized,
      isVaultNote: false,
      readOnly: false,
      readOnlyLabel: "",
      sourceLabel: "",
      trustLabel: "",
    };
  }
  const kind = inferMemoryKind(item, source);
  const isVaultNote = kind === "vault_note";
  const sourceLabel = labelFromValue(
    item.source_label || item.sourceLabel || item.source_name || item.sourceName || item.origin,
    fallbackMemorySourceLabel(item.source || source, isVaultNote),
  );
  const trustLabel = labelFromValue(item.trust_label || item.trustLabel || item.trust_class || item.trustClass || item.trust || item.confidence, "");
  const path = item.path || item.note_path || item.filepath || item.file_path || item.filename || "";
  const body = item.body || item.content || item.markdown || item.text || item.excerpt || item.note_body || normalized.body;
  const card = item.card || item.summary || item.description || item.note_card || item.snippet || item.excerpt || normalized.card;
  const status = item.status || (isVaultNote ? "read-only" : normalized.status);
  const explicitType = String(item.type || item.kind || item.record_kind || "").trim();
  const protocol = normalizeProtocolMetadata(item);
  const scenarioPayload = item.scenario && typeof item.scenario === "object" ? item.scenario : null;
  const scenarioKind = String(item.scenario_kind || scenarioPayload?.scenario_kind || "").trim().toLowerCase();
  const branchIndex = Array.isArray(item.branchIndex)
    ? item.branchIndex
    : Array.isArray(item.branch_index)
      ? item.branch_index
      : Array.isArray(scenarioPayload?.branch_index)
        ? scenarioPayload.branch_index
        : Array.isArray(scenarioPayload?.branchIndex)
          ? scenarioPayload.branchIndex
          : [];
  const branchWorkspaceIds = Array.isArray(item.branchWorkspaceIds)
    ? item.branchWorkspaceIds
    : Array.isArray(item.branch_workspace_ids)
      ? item.branch_workspace_ids
      : Array.isArray(scenarioPayload?.branch_workspace_ids)
        ? scenarioPayload.branch_workspace_ids
        : Array.isArray(scenarioPayload?.branchWorkspaceIds)
          ? scenarioPayload.branchWorkspaceIds
          : [];
  return {
    ...normalized,
    id: normalizeRecordId(item, path || normalized.id),
    kind: isVaultNote ? "vault_note" : String(item.kind || item.record_kind || "saved_note"),
    recordKind: String(item.record_kind || item.kind || item.type || ""),
    title: item.title || item.name || item.label || item.filename || normalized.title || (isVaultNote ? "Untitled reference note" : "Untitled saved note"),
    type: isVaultNote ? "reference note" : explicitType || "saved note",
    protocol,
    protocol_kind: protocol.protocolKind,
    protocolKind: protocol.protocolKind,
    card: card || (isVaultNote ? body.slice(0, 160) : ""),
    body,
    status,
    scope: item.scope || "",
    durability: item.durability || "",
    links_to: Array.isArray(item.links_to) ? item.links_to : Array.isArray(item.linksTo) ? item.linksTo : normalized.links_to,
    comes_from: Array.isArray(item.comes_from) ? item.comes_from : normalized.comes_from,
    derived_from_id: item.derived_from_id || item.derivedFromId || normalized.derived_from_id || null,
    revision_parent_id: item.revision_parent_id || item.revisionParentId || normalized.revision_parent_id || null,
    lineage_kind: item.lineage_kind || item.lineageKind || normalized.lineage_kind || (Array.isArray(item.comes_from) && item.comes_from.length ? "provenance" : "none"),
    filename: item.filename || normalized.filename || "",
    path,
    source: item.source || normalized.source || source,
    sourceLabel,
    trustLabel,
    trustClass: item.trust_class || item.trustClass || "",
    trust: item.trust || "",
    readOnly: isVaultNote || item.read_only === true || item.writable === false,
    readOnlyLabel: item.read_only_label || item.readOnlyLabel || "read-only",
    score: item.score ?? item.rank ?? normalized.score,
    tags: Array.isArray(item.tags) ? item.tags : [],
    provenance: item.provenance || item.source_meta || item.metadata || null,
    recallReason: item.recall_reason || item.recallReason || item.why_recalled || item.whyRecalled || item.user_reason || item.userReason || "",
    recall_reason: item.recall_reason || item.recallReason || item.why_recalled || item.whyRecalled || item.user_reason || item.userReason || "",
    learnedReason: item.learned_reason || item.learnedReason || item.why_learned || item.whyLearned || item.save_reason || item.saveReason || item.rationale || "",
    learned_reason: item.learned_reason || item.learnedReason || item.why_learned || item.whyLearned || item.save_reason || item.saveReason || item.rationale || "",
    whyLearned: item.why_learned || item.whyLearned || item.learned_reason || item.learnedReason || "",
    why_learned: item.why_learned || item.whyLearned || item.learned_reason || item.learnedReason || "",
    scope: item.scope || normalized.scope || "",
    durability: item.durability || normalized.durability || "",
    correctionAffordance: item.correction_affordance || item.correctionAffordance || null,
    correction_affordance: item.correction_affordance || item.correctionAffordance || null,
    debugReason: item.reason || item.debug_reason || item.debugReason || "",
    scenario: scenarioPayload,
    scenarioKind,
    scenario_kind: scenarioKind,
    branchIndex,
    branchWorkspaceIds,
    artifact_lifecycle: item.artifact_lifecycle || item.artifactLifecycle || "",
    artifact_origin: item.artifact_origin || item.artifactOrigin || "",
    libraryBucket: isVaultNote ? "reference" : savedNoteBucket({ kind: item.kind, type: explicitType, path, filename: item.filename || normalized.filename || "" }),
    derivedFromId: item.derived_from_id || item.derivedFromId || normalized.derived_from_id || null,
    revisionParentId: item.revision_parent_id || item.revisionParentId || normalized.revision_parent_id || null,
    lineageKind: item.lineage_kind || item.lineageKind || normalized.lineage_kind || (Array.isArray(item.comes_from) && item.comes_from.length ? "provenance" : "none"),
    artifactLifecycle: item.artifact_lifecycle || item.artifactLifecycle || "",
    artifactOrigin: item.artifact_origin || item.artifactOrigin || "",
    isVaultNote,
  };
}

function shouldShowRecallReason(item, context) {
  if (!item || item.source === "memory_trace") {
    return false;
  }
  if (context === "turn" || context === "reasoning-recall") {
    return true;
  }
  return context === "reasoning-candidate" && item.reasoningStatusLabel === "used for recall";
}

function productVettingNotice(vetting, { recallCount = 0 } = {}) {
  if (!vetting || typeof vetting !== "object" || recallCount > 0) {
    return "";
  }
  if (vetting.none_relevant === true) {
    return "Nothing was pulled in for this turn.";
  }
  return "";
}

function inferMemoryKind(item, source) {
  const explicitKind = String(item.kind || item.type || item.source || "").toLowerCase();
  if (["vault_note", "reference_note", "reference note"].includes(explicitKind)) {
    return "vault_note";
  }
  if (["concept", "saved_note", "saved note"].includes(explicitKind)) {
    return "concept";
  }
  if (item.is_vault_note || item.read_only === true || item.writable === false) {
    return "vault_note";
  }
  if (typeof item.path === "string" && !item.links_to && source !== "session" && source !== "turn") {
    return "vault_note";
  }
  const sourceValue = String(item.source || source || "").toLowerCase();
  if (["vault_note", "vault"].includes(sourceValue)) {
    return "vault_note";
  }
  return "concept";
}

function fallbackMemorySourceLabel(source, isVaultNote) {
  const value = String(source || "").toLowerCase();
  if (value.includes("trace") || value.includes("memory_trace")) {
    return "Memory Trace";
  }
  if (value.includes("turn")) {
    return isVaultNote ? "Turn references" : "Turn context";
  }
  if (value.includes("candidate")) {
    return isVaultNote ? "Considered references" : "Considered context";
  }
  if (value.includes("session")) {
    return isVaultNote ? "Session references" : "Session drafts";
  }
  if (value.includes("catalog")) {
    return isVaultNote ? "Reference notes" : "Library";
  }
  if (value.includes("vault")) {
    return "Reference notes";
  }
  return isVaultNote ? "Reference notes" : "Library";
}

function labelFromValue(value, fallback) {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function dedupeMemoryItems(items, kind) {
  const map = new Map();
  for (const item of items) {
    const key = `${kind}:${item.id}`;
    const existing = map.get(key);
    map.set(key, existing ? { ...existing, ...item } : { ...item });
  }
  return [...map.values()].sort(compareMemoryItems);
}

function mergeConceptCollections(first, second) {
  const map = new Map();
  for (const concept of first) {
    map.set(concept.id, { ...concept });
  }
  for (const concept of second) {
    const existing = map.get(concept.id);
    map.set(concept.id, existing ? { ...existing, ...concept } : { ...concept });
  }
  return [...map.values()].sort(compareConcepts);
}

function rebuildConceptCatalog() {
  state.allConcepts = mergeConceptCollections(state.catalogConcepts, state.sessionConcepts);
  state.allSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.sessionSavedNotes);
  state.allVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.sessionVaultNotes);
  state.allMemoryItems = [...state.allConcepts, ...state.allSavedNotes, ...state.allVaultNotes].sort(compareMemoryItems);
}

function upsertSessionConcept(concept) {
  const normalized = normalizeConcept(concept, "session");
  const index = state.sessionConcepts.findIndex((item) => item.id === normalized.id);
  if (index >= 0) {
    state.sessionConcepts[index] = { ...state.sessionConcepts[index], ...normalized };
  } else {
    state.sessionConcepts.unshift(normalized);
  }
  rebuildConceptCatalog();
}

function upsertSessionSavedNote(item) {
  const normalized = normalizeMemoryItem(item, "session");
  const index = state.sessionSavedNotes.findIndex((savedNote) => savedNote.id === normalized.id);
  if (index >= 0) {
    state.sessionSavedNotes[index] = { ...state.sessionSavedNotes[index], ...normalized };
  } else {
    state.sessionSavedNotes.unshift(normalized);
  }
  rebuildConceptCatalog();
}

function upsertSessionVaultNote(vaultNote) {
  const normalized = normalizeMemoryItem(vaultNote, "session-vault");
  const index = state.sessionVaultNotes.findIndex((item) => item.id === normalized.id);
  if (index >= 0) {
    state.sessionVaultNotes[index] = { ...state.sessionVaultNotes[index], ...normalized };
  } else {
    state.sessionVaultNotes.unshift(normalized);
  }
  rebuildConceptCatalog();
}

function buildLocalConceptFromWorkspace(content, title) {
  const id = slugify(title || inferWorkspaceTitle(content) || "workspace-concept");
  return normalizeConcept(
    {
      id,
      title: title || inferWorkspaceTitle(content) || "Workspace Concept",
      type: "concept",
      card: summarizeText(content),
      body: content,
      status: "session",
      links_to: [],
      comes_from: [state.workspace.workspaceId || "workspace"],
      source: "session",
    },
    "session",
  );
}

function mergeMemoryCollections(first, second) {
  const map = new Map();
  for (const item of first) {
    map.set(item.id, { ...item });
  }
  for (const item of second) {
    const existing = map.get(item.id);
    map.set(item.id, existing ? { ...existing, ...item } : { ...item });
  }
  return [...map.values()].sort(compareMemoryItems);
}

function buildConceptWorkspaceDraft(concept) {
  return [
    "---",
    `id: ${yamlScalar(concept.id)}`,
    `title: ${yamlScalar(concept.title)}`,
    `type: ${yamlScalar(concept.type || "concept")}`,
    `card: ${yamlScalar(concept.card || "")}`,
    `status: ${yamlScalar(concept.status || "active")}`,
    concept.links_to && concept.links_to.length ? `links_to:\n${concept.links_to.map((link) => `  - ${yamlScalar(link)}`).join("\n")}` : "",
    concept.comes_from && concept.comes_from.length ? `comes_from:\n${concept.comes_from.map((item) => `  - ${yamlScalar(item)}`).join("\n")}` : "",
    "---",
    "",
    concept.body || concept.card || `# ${concept.title}`,
    "",
  ]
    .filter(Boolean)
    .join("\n");
}

function summarizeText(text) {
  const cleaned = (text || "").trim().replace(/\s+/g, " ");
  if (!cleaned) {
    return "A concept recorded from the current workspace.";
  }
  const sentence = cleaned.match(/^[^.?!]+[.?!]?/);
  const summary = (sentence ? sentence[0] : cleaned).slice(0, 160);
  return summary.endsWith(".") ? summary : `${summary}.`;
}

function inferWorkspaceTitle(content) {
  const lines = (content || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const heading = lines.find((line) => line.startsWith("# "));
  if (heading) {
    return heading.replace(/^#+\s*/, "").trim();
  }
  return summarizeText(content).replace(/[.?!]$/, "");
}

function describeGraphAction(action) {
  if (!action) {
    return "";
  }
  if (typeof action === "string") {
    return action;
  }
  if (typeof action !== "object") {
    return String(action);
  }
  const rawLabel = action.type || "graph action";
  const label = humanizeActionLabel(rawLabel);
  const target = action.record_title || action.title || action.concept_title || normalizeRecordId(action) || "";
  const suffix = target ? `: ${target}` : "";
  return `${label}${suffix}`;
}

function humanizeActionLabel(value) {
  switch (value) {
    case "create_concept":
      return "Idea created";
    case "create_memory":
      return "Note saved";
    case "create_revision":
      return "Saved item revised";
    case "promote_workspace_to_artifact":
      return "Whiteboard saved as work product";
    case "save_workspace_iteration_artifact":
      return "Work product iteration saved";
    case "open_saved_item_into_workspace":
    case "open_concept_into_workspace":
      return "Opened in whiteboard";
    default:
      return value.replaceAll("_", " ");
  }
}

function createBadge(label, tone) {
  const badge = document.createElement("span");
  badge.className = `badge badge--${tone}`;
  badge.textContent = label;
  return badge;
}

function normalizeEvidenceLabel(label) {
  return String(label || "").trim().toLowerCase();
}

function isWhiteboardStateEvidenceLabel(label) {
  return [
    "whiteboard",
    "prior whiteboard",
    "recall + whiteboard",
    "recall + prior whiteboard",
    "opened in whiteboard",
    "whiteboard decision",
    "whiteboard offer",
    "draft ready",
  ].includes(label);
}

function applyTranscriptEvidenceBadgeClasses(badge, item, evidence = []) {
  const label = normalizeEvidenceLabel(item?.label);
  const hasStrongerCompanion = evidence.some((entry) => entry !== item && entry?.emphasis === "strong");

  if (item?.emphasis === "quiet") {
    badge.classList.add("badge--message-secondary");
  } else if (item?.emphasis === "strong") {
    badge.classList.add("badge--message-strong");
  }

  if (isWhiteboardStateEvidenceLabel(label) && hasStrongerCompanion) {
    badge.classList.add("badge--message-muted");
  }
}

function createMiniMeta(label, value) {
  const item = document.createElement("div");
  item.className = "mini-meta";
  const key = document.createElement("span");
  key.className = "mini-meta__key";
  key.textContent = label;
  const val = document.createElement("span");
  val.className = "mini-meta__value";
  val.textContent = value || "—";
  item.append(key, val);
  return item;
}

function scenarioQuestionText(scenarioLab) {
  return scenarioLab?.question || scenarioLab?.comparison_question || "Scenario branches were created from this turn.";
}

function scenarioLabBranchCount(scenarioLab) {
  if (!scenarioLab || typeof scenarioLab !== "object") {
    return 0;
  }
  if (Array.isArray(scenarioLab.branches) && scenarioLab.branches.length) {
    return scenarioLab.branches.length;
  }
  const comparisonArtifact = scenarioLab.comparisonArtifact
    || (scenarioLab.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"
      ? scenarioLab.comparison_artifact
      : null);
  if (Array.isArray(comparisonArtifact?.branchIndex) && comparisonArtifact.branchIndex.length) {
    return comparisonArtifact.branchIndex.length;
  }
  if (Array.isArray(comparisonArtifact?.branch_index) && comparisonArtifact.branch_index.length) {
    return comparisonArtifact.branch_index.length;
  }
  if (Array.isArray(comparisonArtifact?.branchWorkspaceIds) && comparisonArtifact.branchWorkspaceIds.length) {
    return comparisonArtifact.branchWorkspaceIds.length;
  }
  if (Array.isArray(comparisonArtifact?.branch_workspace_ids) && comparisonArtifact.branch_workspace_ids.length) {
    return comparisonArtifact.branch_workspace_ids.length;
  }
  return 0;
}

function hasScenarioComparisonArtifact(scenarioLab) {
  return Boolean(
    scenarioLab?.comparisonArtifact
    || (scenarioLab?.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"),
  );
}

function buildScenarioLabOutcomeCopy(branchCount, hasArtifact) {
  if (branchCount > 0 && hasArtifact) {
    return `Scenario Lab created ${branchCount} branch${branchCount === 1 ? "" : "es"} and saved a comparison hub.`;
  }
  if (branchCount > 0) {
    return `Scenario Lab created ${branchCount} branch${branchCount === 1 ? "" : "es"} for review.`;
  }
  if (hasArtifact) {
    return "Scenario Lab saved a comparison hub for review.";
  }
  return "Scenario Lab created durable scenario outputs.";
}

function humanizeScenarioLabel(label, fallback = "") {
  const normalized = String(label || "").trim();
  if (!normalized) {
    return fallback;
  }
  return normalized
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function deriveScenarioBranchDetails(branch) {
  return {
    question: firstTruthyValue([
      branch?.comparisonQuestion,
      branch?.comparison_question,
      extractScenarioMetadataValue(branch?.body, "Question"),
    ]),
    confidence: firstTruthyValue([
      branch?.sections?.confidence?.text,
      branch?.confidence,
      extractMarkdownSectionText(branch?.body, "Confidence"),
    ]),
    sharedAssumptions: firstTruthyList([
      branch?.sections?.sharedAssumptions?.items,
      branch?.shared_assumptions,
      extractMarkdownBulletList(branch?.body, "Shared Assumptions"),
    ]),
    preservedAssumptions: firstTruthyList([
      branch?.sections?.preservedAssumptions?.items,
      branch?.preserved_assumptions,
      extractMarkdownBulletList(branch?.body, "Preserved Assumptions"),
    ]),
    changedAssumptions: firstTruthyList([
      branch?.sections?.changedAssumptions?.items,
      branch?.changed_assumptions,
      extractMarkdownBulletList(branch?.body, "Changed Assumptions"),
    ]),
    risks: firstTruthyList([
      branch?.sections?.risks?.items,
      branch?.risks,
      extractMarkdownBulletList(branch?.body, "Risks"),
    ]),
    openQuestions: firstTruthyList([
      branch?.sections?.openQuestions?.items,
      branch?.open_questions,
      extractMarkdownBulletList(branch?.body, "Open Questions"),
    ]),
  };
}

function deriveScenarioArtifactDetails(artifact) {
  return {
    summary: firstTruthyValue([
      artifact?.sections?.summary?.text,
      extractMarkdownSectionText(artifact?.body, "Summary"),
    ]),
    recommendation: firstTruthyValue([
      artifact?.sections?.recommendation?.text,
      artifact?.recommendation,
      extractMarkdownSectionText(artifact?.body, "Recommendation"),
    ]),
    sharedAssumptions: firstTruthyList([
      artifact?.sections?.sharedAssumptions?.items,
      artifact?.shared_assumptions,
      extractMarkdownBulletList(artifact?.body, "Shared Assumptions"),
    ]),
    tradeoffs: firstTruthyList([
      artifact?.sections?.tradeoffs?.items,
      artifact?.tradeoffs,
      extractMarkdownBulletList(artifact?.body, "Tradeoffs"),
    ]),
    nextSteps: firstTruthyList([
      artifact?.sections?.nextSteps?.items,
      artifact?.next_steps,
      extractMarkdownBulletList(artifact?.body, "Next Steps"),
    ]),
    branchIndex: normalizeComparisonBranchIndex(
      artifact?.branchIndex || artifact?.branch_index,
      artifact?.branchWorkspaceIds || artifact?.branch_workspace_ids,
    ),
  };
}

function createScenarioOverviewCard({ label, body = "", items = [], tone = "neutral" }) {
  const card = document.createElement("section");
  card.className = `scenario-lab__overview-card scenario-lab__overview-card--${tone}`;

  const heading = document.createElement("div");
  heading.className = "section-label";
  heading.textContent = label;

  card.append(heading);
  if (body) {
    const text = document.createElement("p");
    text.className = "scenario-lab__overview-copy";
    text.textContent = body;
    card.append(text);
  }
  if (Array.isArray(items) && items.length) {
    card.append(createScenarioList(items));
  }
  return card;
}

function createScenarioSupportCard({ label = "", summary = "", meta = null } = {}) {
  const card = document.createElement("section");
  card.className = "scenario-lab__support-card";

  const heading = document.createElement("div");
  heading.className = "section-label";
  heading.textContent = label || "Details";
  card.append(heading);

  if (summary) {
    const text = document.createElement("p");
    text.className = "scenario-lab__support-copy";
    text.textContent = summary;
    card.append(text);
  }

  if (meta && meta.childNodes.length) {
    card.append(meta.cloneNode(true));
  }

  return card;
}

function createScenarioSectionLead({ label = "", summary = "", metaItems = [] } = {}) {
  const sectionHead = document.createElement("div");
  sectionHead.className = "scenario-lab__section-head";

  const copy = document.createElement("div");
  copy.className = "scenario-lab__section-head-copy";

  const heading = document.createElement("div");
  heading.className = "section-label";
  heading.textContent = label || "Section";
  copy.append(heading);

  if (summary) {
    const text = document.createElement("p");
    text.className = "scenario-lab__section-copy";
    text.textContent = summary;
    copy.append(text);
  }
  sectionHead.append(copy);

  if (Array.isArray(metaItems) && metaItems.length) {
    const meta = document.createElement("div");
    meta.className = "scenario-lab__section-meta";
    for (const item of metaItems) {
      if (!item?.label || !item?.value) {
        continue;
      }
      meta.append(createMiniMeta(item.label, item.value));
    }
    if (meta.childNodes.length) {
      sectionHead.append(meta);
    }
  }

  return sectionHead;
}

function createScenarioTranscriptCard(scenarioLab) {
  const comparisonArtifact = scenarioLab?.comparisonArtifact
    || (scenarioLab?.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"
      ? scenarioLab.comparison_artifact
      : null);
  const artifactDetails = comparisonArtifact ? deriveScenarioArtifactDetails(comparisonArtifact) : null;
  const comparisonBranchRoster = Array.isArray(artifactDetails?.branchIndex) ? artifactDetails.branchIndex : [];
  const branchCount = Array.isArray(scenarioLab?.branches) && scenarioLab.branches.length
    ? scenarioLab.branches.length
    : comparisonBranchRoster.length;
  const artifactId = comparisonArtifact?.id || "";
  const card = document.createElement("section");
  card.className = "message-scenario-card";

  const top = document.createElement("div");
  top.className = "message-scenario-card__top";
  const label = document.createElement("div");
  label.className = "section-label";
  label.textContent = "Scenario Lab";
  const meta = document.createElement("div");
  meta.className = "message-scenario-card__meta";
  if (artifactId) {
    meta.append(createBadge("Comparison hub", "success"));
  }
  if (branchCount) {
    meta.append(createBadge(`${branchCount} ${branchCount === 1 ? "branch" : "branches"}`, "soft"));
  }
  top.append(label, meta);

  const title = document.createElement("p");
  title.className = "message-scenario-card__title";
  title.textContent = scenarioLab?.status === "failed"
    ? "Scenario Lab fallback"
    : scenarioQuestionText(scenarioLab);

  const summary = document.createElement("p");
  summary.className = "message-scenario-card__summary";
  summary.textContent = scenarioLab?.status === "failed"
    ? (scenarioLab?.error?.message || "Scenario Lab could not complete this turn, so the answer stayed in chat instead.")
    : (scenarioLab?.recommendation || scenarioLab?.summary || (artifactId
      ? "Comparison question, recommendation, and the durable hub are ready to inspect."
      : "Scenario branches are ready to inspect."));

  const actions = document.createElement("div");
  actions.className = "message-scenario-card__actions";
  const openScenarioButton = createActionButton("Open Scenario Lab", "primary");
  openScenarioButton.addEventListener("click", () => {
    openVantage({ focus: "scenario" });
  });
  actions.append(openScenarioButton);
  if (artifactId) {
    const inspectArtifactButton = createActionButton("Inspect comparison", "secondary");
    inspectArtifactButton.addEventListener("click", () => {
      inspectScenarioArtifact(artifactId);
    });
    actions.append(inspectArtifactButton);
  }

  card.append(top, title, summary, actions);
  return card;
}

function inspectScenarioArtifact(artifactId) {
  if (!artifactId) {
    return;
  }
  openVantage({ focus: "library" });
  memoryDockEl.open = true;
  selectConcept(artifactId, { silent: true, source: "scenario" });
  renderViewState();
  renderMemoryPanel();
}

function appendScenarioListBlock(parent, label, items) {
  if (!Array.isArray(items) || !items.length) {
    return;
  }
  const block = document.createElement("section");
  block.className = "scenario-lab__list-block";

  const heading = document.createElement("div");
  heading.className = "scenario-lab__list-title";
  heading.textContent = label;

  block.append(heading, createScenarioList(items));
  parent.append(block);
}

function createScenarioList(items) {
  const list = document.createElement("ul");
  list.className = "scenario-lab__list";
  for (const value of items) {
    const entry = document.createElement("li");
    entry.textContent = value;
    list.append(entry);
  }
  return list;
}

function extractMarkdownSectionText(content, heading) {
  const section = extractMarkdownSection(content, heading);
  if (!section) {
    return "";
  }
  return section
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("- "))
    .join(" ")
    .trim();
}

function extractMarkdownBulletList(content, heading) {
  const section = extractMarkdownSection(content, heading);
  if (!section) {
    return [];
  }
  return section
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).trim())
    .filter(Boolean);
}

function extractMarkdownSection(content, heading) {
  if (typeof content !== "string" || !content.trim() || !heading) {
    return "";
  }
  const escapedHeading = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`^## ${escapedHeading}\\s*$([\\s\\S]*?)(?=^##\\s|\\Z)`, "im");
  const match = content.match(pattern);
  return match?.[1]?.trim() || "";
}

function extractScenarioMetadataValue(content, field) {
  if (typeof content !== "string" || !field) {
    return "";
  }
  const escapedField = field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = content.match(new RegExp(`^${escapedField}:\\s*(.+)$`, "im"));
  return match?.[1]?.trim() || "";
}

function firstTruthyList(candidates) {
  for (const candidate of candidates) {
    if (Array.isArray(candidate) && candidate.length) {
      return candidate.map((value) => String(value).trim()).filter(Boolean);
    }
  }
  return [];
}

function firstTruthyValue(candidates) {
  for (const candidate of candidates) {
    const value = String(candidate || "").trim();
    if (value) {
      return value;
    }
  }
  return "";
}

function createActionButton(label, tone) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = tone === "primary" ? "button button--primary" : "button button--secondary";
  button.textContent = label;
  return button;
}

function yamlScalar(value) {
  return JSON.stringify(String(value ?? ""));
}

function slugify(value) {
  return String(value || "")
    .normalize("NFKD")
    .toLowerCase()
    .replace(/['"]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || `concept-${Date.now()}`;
}

function buildWorkspaceNote(payload) {
  if (payload?.mode === "scenario_lab") {
    const branchCount = Array.isArray(payload?.scenario_lab?.branches) ? payload.scenario_lab.branches.length : 0;
    return buildScenarioLabOutcomeCopy(branchCount, hasScenarioComparisonArtifact(payload?.scenario_lab));
  }
  if (payload?.workspace_update?.status === "offered") {
    return payload.workspace_update.summary || "Inspect suggested moving this work into Draft.";
  }
  if (payload?.workspace_update?.status === "draft_ready") {
    return payload.workspace_update.summary || "A whiteboard draft is ready to review before it enters the whiteboard.";
  }
  if (payload?.workspace_update?.summary) {
    return payload.workspace_update.summary;
  }
  if (payload?.graph_action?.type === "open_saved_item_into_workspace" || payload?.graph_action?.type === "open_concept_into_workspace") {
    return "Draft updated from the selected item.";
  }
  if (payload?.graph_action) {
    return `Draft stayed available while Inspect recorded: ${describeGraphAction(payload.graph_action)}.`;
  }
  if ((state.workspace.content || "").trim()) {
    return "The whiteboard stayed separate as the drafting surface for this turn.";
  }
  return "Draft ready as a separate drafting surface.";
}

function pushNotice(title, message, tone = "info") {
  const normalizedTitle = String(title || "").trim();
  const normalizedMessage = String(message || "").trim();
  if (!normalizedTitle && !normalizedMessage) {
    return;
  }
  if (
    state.notice
    && state.notice.title === normalizedTitle
    && state.notice.message === normalizedMessage
    && state.notice.tone === tone
  ) {
    if (state.noticeTimeoutId) {
      window.clearTimeout(state.noticeTimeoutId);
    }
  }
  const notice = {
    id: `${Date.now()}-${++state.noticeCounter}`,
    title: normalizedTitle,
    message: normalizedMessage,
    tone,
  };
  state.notice = notice;
  renderNotices();
  if (state.noticeTimeoutId) {
    window.clearTimeout(state.noticeTimeoutId);
  }
  const timeoutMs = tone === "warning" ? 5600 : 3400;
  state.noticeTimeoutId = window.setTimeout(() => {
    if (state.notice?.id === notice.id) {
      state.notice = null;
      renderNotices();
    }
    state.noticeTimeoutId = null;
  }, timeoutMs);
}

function renderNotices() {
  noticeRailEl.innerHTML = "";
  noticeRailEl.hidden = !state.notice;
  if (!state.notice) {
    return;
  }
  const notice = state.notice;
  const node = document.createElement("article");
  node.className = `notice notice--${notice.tone}`;
  const title = document.createElement("strong");
  title.textContent = notice.title;
  const message = document.createElement("div");
  message.className = "notice-message";
  message.textContent = notice.message;
  node.append(title, message);
  noticeRailEl.appendChild(node);
}

function addMessage(role, text, { evidence = [], scenarioLab = null } = {}) {
  const node = messageTemplate.content.cloneNode(true);
  const article = node.querySelector(".message");
  article.classList.add(role);
  if (Array.isArray(evidence) && evidence.some((item) => item?.label === "Scenario Lab")) {
    article.classList.add("message--scenario-lab");
  }
  node.querySelector(".message-role").textContent = role;
  renderRichText(node.querySelector(".message-body"), text);
  if (Array.isArray(evidence) && evidence.length) {
    const rail = document.createElement("div");
    rail.className = "message-evidence";
    for (const item of evidence) {
      if (!item?.label) {
        continue;
      }
      const badge = createBadge(item.label, item.tone || "soft");
      badge.classList.add("badge--message");
      applyTranscriptEvidenceBadgeClasses(badge, item, evidence);
      rail.append(badge);
    }
    article.append(rail);
  }
  if (role === "assistant" && scenarioLab) {
    article.append(createScenarioTranscriptCard(scenarioLab));
  }
  transcriptEl.appendChild(node);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function setBusy(value) {
  state.busy = value;
  sendButtonEl.disabled = value;
  seedPromptEl.disabled = value;
  whiteboardToggleButtonEl.disabled = value;
  vantageToggleButtonEl.disabled = value;
  closeVantageButtonEl.disabled = value;
  hideWhiteboardButtonEl.disabled = value;
  saveWorkspaceButtonEl.disabled = value;
  promoteWorkspaceButtonEl.disabled = value || !workspaceEditorEl.value.trim();
  pinSelectedContextButtonEl.disabled = value || !getSelectedMemoryItem();
  clearPinnedContextButtonEl.disabled = value || !getPinnedMemoryItem();
  refreshConceptsButtonEl.disabled = value;
  experimentToggleButtonEl.disabled = value;
  clearSearchButtonEl.disabled = value;
  workspaceEditorEl.disabled = value;
  if (value) {
    statusPillEl.textContent = "Working";
  } else {
    renderExperimentStatus({ nexusEnabled: state.nexusEnabled });
  }
  renderViewState();
  renderTurnPanel();
  renderMemoryPanel();
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  const payload = text ? safeParseJson(text) : {};
  return { response, payload };
}

function safeParseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}
