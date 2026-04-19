import {
  deriveWhiteboardDecisionPresentation,
  hasPendingWorkspaceDecision,
  isWhiteboardFocused,
  shouldHideChatWorkspaceUpdate,
  workspaceUpdateHasDraft,
} from "./whiteboard_decisions.mjs?v=20260416-wave1-semantics";
import {
  buildMemoryTraceSummary,
  buildChatTurnEvidence,
  buildGuidedInspectionSummary,
  buildReasoningPathInspection,
  describeResponseModeLabel,
  deriveTurnGrounding,
  deriveWhiteboardLifecycle,
} from "./product_identity.mjs?v=20260419-working-memory-scope";
import {
  buildWorkspaceContextPayload,
  shouldCarryPendingWorkspaceUpdate,
} from "./chat_request.mjs?v=20260419-reasoning-path";
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
} from "./surface_state.mjs?v=20260419-reasoning-path";
import {
  buildWorkspaceSnapshot,
  shouldPreserveUnsavedWorkspace,
} from "./workspace_state.mjs?v=20260419-reasoning-path";
import {
  buildTurnPanelGroundingCopy,
} from "./turn_panel_grounding.mjs?v=20260419-reasoning-path";
import {
  normalizeLearnedItems,
  normalizeRecordId,
  normalizeResponseMode,
  normalizeScenarioLabPayload,
  normalizeTurnPayload,
  normalizeTurnInterpretation,
  normalizeWorkspaceUpdate,
} from "./turn_payloads.mjs?v=20260419-reasoning-path";

const shellEl = document.getElementById("shell");
const transcriptEl = document.getElementById("transcript");
const composerEl = document.getElementById("composer");
const messageInputEl = document.getElementById("messageInput");
const chatSurfaceTitleEl = document.getElementById("chatSurfaceTitle");
const chatSurfaceSubtitleEl = document.getElementById("chatSurfaceSubtitle");
const sendButtonEl = document.getElementById("sendButton");
const seedPromptEl = document.getElementById("seedPrompt");
const startExperimentButtonEl = document.getElementById("startExperimentButton");
const endExperimentButtonEl = document.getElementById("endExperimentButton");
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
const workspaceDockLabelEl = document.getElementById("workspaceDockLabel");
const answerDockLabelEl = document.getElementById("answerDockLabel");
const scenarioDockLabelEl = document.getElementById("scenarioDockLabel");
const memoryDockLabelEl = document.getElementById("memoryDockLabel");
const workspaceEditorEl = document.getElementById("workspaceEditor");
const workspaceTitleEl = document.getElementById("workspaceTitle");
const workspaceMetaEl = document.getElementById("workspaceMeta");
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
const turnActionsEl = document.getElementById("turnActions");
const turnReasoningPathSectionEl = document.getElementById("turnReasoningPathSection");
const turnReasoningPathSummaryEl = document.getElementById("turnReasoningPathSummary");
const turnReasoningPathMetaEl = document.getElementById("turnReasoningPathMeta");
const turnReasoningPathRailEl = document.getElementById("turnReasoningPathRail");
const turnReasoningPathDetailEl = document.getElementById("turnReasoningPathDetail");
const turnNoticeEl = document.getElementById("turnNotice");
const turnTraceNoticeEl = document.getElementById("turnTraceNotice");
const workspaceUpdatePanelEl = document.getElementById("workspaceUpdatePanel");
const workspaceUpdateLabelEl = document.getElementById("workspaceUpdateLabel");
const workspaceUpdateSummaryEl = document.getElementById("workspaceUpdateSummary");
const workspaceUpdateActionsEl = document.getElementById("workspaceUpdateActions");
const scenarioLabSectionEl = document.getElementById("scenarioLabSection");
const turnWorkingMemoryListEl = document.getElementById("turnWorkingMemoryList");
const turnTraceListEl = document.getElementById("turnTraceList");
const turnLearnedListEl = document.getElementById("turnLearnedList");
const rememberButtonEl = document.getElementById("rememberButton");
const dontSaveButtonEl = document.getElementById("dontSaveButton");
const showRelatedButtonEl = document.getElementById("showRelatedButton");
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
const messageTemplate = document.getElementById("messageTemplate");

const samplePrompt = "A small team is preparing to launch a new software product with limited time and budget. Create three scenario branches: conservative rollout, focused MVP launch, and aggressive feature launch. Compare tradeoffs, risks, and next steps, then recommend one.";
const LEGACY_TURN_SNAPSHOT_KEY = "vantage-v5-turn-snapshot";
const TURN_SNAPSHOT_VERSION = 7;
const COMPOSER_WHITEBOARD_MODES = new Set(["auto", "offer"]);

let hasLoadedHealth = false;

const state = {
  busy: false,
  mode: "fallback",
  nexusEnabled: false,
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
  turnReasoningPathStageKey: "candidate-context",
  candidateConcepts: [],
  candidateSavedNotes: [],
  candidateTraceNotes: [],
  candidateVaultNotes: [],
  pinnedContext: null,
  selectedConceptId: "",
  selectedVaultNoteId: "",
  selectionOrigin: "bootstrap",
  memoryQuery: "",
  notices: [],
  noticeCounter: 0,
  workspace: {
    workspaceId: "",
    scope: "durable",
    title: "Whiteboard",
    content: "",
    savedContent: "",
    dirty: false,
    pinnedToChat: false,
    lifecycle: "ready",
    note: "Whiteboard ready as a separate drafting surface.",
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
    graphAction: null,
    scenarioLab: null,
    interpretation: null,
    memoryIntent: "idle",
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
    interpretation: null,
    memoryIntent: "idle",
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
  state.turnReasoningPathStageKey = "candidate-context";
  state.candidateConcepts = [];
  state.candidateSavedNotes = [];
  state.candidateTraceNotes = [];
  state.candidateVaultNotes = [];
  state.pinnedContext = null;
  state.selectedConceptId = "";
  state.selectedVaultNoteId = "";
  state.selectionOrigin = "bootstrap";
  state.pendingWhiteboardDecision = null;
  state.workspace.lifecycle = "ready";
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
        turnReasoningPathStageKey: state.turnReasoningPathStageKey,
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
        turnReasoningPathStageKey: state.turnReasoningPathStageKey,
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
    state.surface = normalizeSurfaceState(snapshot.surface || snapshot.view || {});
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
      workspaceUpdate: restoredWorkspaceUpdate,
      vetting: snapshot.turn?.vetting || null,
      graphAction: snapshot.turn?.graphAction || null,
      scenarioLab: snapshot.turn?.scenarioLab || null,
      interpretation: normalizeTurnInterpretation(snapshot.turn?.interpretation || null),
      memoryIntent: snapshot.turn?.memoryIntent || "idle",
    };
    state.selectedConceptId = snapshot.selectedConceptId || "";
    state.selectedVaultNoteId = snapshot.selectedVaultNoteId || "";
    state.selectionOrigin = snapshot.selectionOrigin || "bootstrap";
    state.turnConcepts = Array.isArray(snapshot.turnConcepts) ? snapshot.turnConcepts : [];
    state.turnSavedNotes = Array.isArray(snapshot.turnSavedNotes) ? snapshot.turnSavedNotes : [];
    state.turnVaultNotes = Array.isArray(snapshot.turnVaultNotes) ? snapshot.turnVaultNotes : [];
    state.turnWorkingMemory = Array.isArray(snapshot.turnWorkingMemory) ? snapshot.turnWorkingMemory : [];
    state.turnTraceNotes = Array.isArray(snapshot.turnTraceNotes) ? snapshot.turnTraceNotes : [];
    state.turnMemoryTraceRecord = snapshot.turnMemoryTraceRecord && typeof snapshot.turnMemoryTraceRecord === "object"
      ? snapshot.turnMemoryTraceRecord
      : null;
    state.turnLearned = Array.isArray(snapshot.turnLearned) ? snapshot.turnLearned : [];
    state.turnReasoningPathStageKey = snapshot.turnReasoningPathStageKey || "candidate-context";
    state.candidateConcepts = Array.isArray(snapshot.candidateConcepts) ? snapshot.candidateConcepts : [];
    state.candidateSavedNotes = Array.isArray(snapshot.candidateSavedNotes) ? snapshot.candidateSavedNotes : [];
    state.candidateTraceNotes = Array.isArray(snapshot.candidateTraceNotes) ? snapshot.candidateTraceNotes : [];
    state.candidateVaultNotes = Array.isArray(snapshot.candidateVaultNotes) ? snapshot.candidateVaultNotes : [];
    state.pinnedContext = snapshot.pinnedContext && typeof snapshot.pinnedContext === "object"
      ? {
          id: snapshot.pinnedContext.id || "",
          kind: snapshot.pinnedContext.kind || "concept",
        }
      : null;
    state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.turnConcepts);
    state.catalogConcepts = mergeConceptCollections(state.catalogConcepts, state.candidateConcepts);
    state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.turnSavedNotes);
    state.catalogSavedNotes = mergeMemoryCollections(state.catalogSavedNotes, state.candidateSavedNotes);
    state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.turnVaultNotes);
    state.catalogVaultNotes = mergeMemoryCollections(state.catalogVaultNotes, state.candidateVaultNotes);
    rebuildConceptCatalog();
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

startExperimentButtonEl.addEventListener("click", async () => {
  await startExperiment();
});

endExperimentButtonEl.addEventListener("click", async () => {
  await endExperiment();
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

rememberButtonEl.addEventListener("click", () => {
  state.turn.memoryIntent = "remember";
  renderTurnPanel();
  pushNotice("Next-turn memory set", "The next turn will be marked to remember.", "success");
});

dontSaveButtonEl.addEventListener("click", () => {
  state.turn.memoryIntent = "skip";
  renderTurnPanel();
  pushNotice("Next-turn memory set", "The next turn will be marked not to save.", "warning");
});

showRelatedButtonEl.addEventListener("click", () => {
  const selectedMemory = getSelectedMemoryItem();
  const seed = state.turn.userMessage || state.turn.assistantMessage || selectedMemory?.title || state.workspace.title;
  memorySearchEl.value = seed;
  state.memoryQuery = seed;
  renderMemoryPanel();
  const visible = getVisibleMemoryItems(seed);
  if (visible.concepts.length) {
    selectConcept(visible.concepts[0].id, { silent: true, source: "user" });
  } else if (visible.savedNotes.length) {
    selectConcept(visible.savedNotes[0].id, { silent: true, source: "user" });
  } else if (visible.vaultNotes.length) {
    selectVaultNote(visible.vaultNotes[0].id, { silent: true, source: "user" });
  }
  pushNotice("Related notes opened", "The library is filtered now so you can inspect related notes immediately.", "info");
  openVantage({ focus: "library" });
  memoryDockEl.open = true;
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

boot();

async function boot() {
  await loadHealth();
  restoreTurnSnapshot();
  await loadWorkspace({ preserveDirty: true });
  await loadConceptCatalog({ silent: true });
  renderComposerMode();
  renderViewState();
  if (!transcriptEl.children.length) {
    addMessage("system", "Ready. Chat naturally. Open Vantage when you want guided inspection, and bring up the whiteboard when you want a shared draft.");
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
  if (preserveDirty && state.workspace.dirty) {
    state.workspace.note = "Kept the unsaved whiteboard draft in place.";
    persistTurnSnapshot();
    renderWorkspaceMeta();
    return;
  }
  try {
    const { payload } = await fetchJson("/api/workspace");
    const applied = applyWorkspacePayload(payload || {}, { preserveDirty });
    state.workspace.note = applied
      ? payload?.scope === "experiment"
        ? "Temporary experiment whiteboard loaded."
        : "Whiteboard loaded from disk."
      : "Kept the unsaved whiteboard draft in place instead of replacing it with the last saved whiteboard.";
    persistTurnSnapshot();
  } catch (error) {
    state.workspace.note = error instanceof Error ? error.message : "Whiteboard unavailable.";
    workspaceMetaEl.textContent = state.workspace.note;
    pushNotice("Whiteboard unavailable", state.workspace.note, "warning");
  }
  renderWorkspaceMeta();
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
    return;
  }
  const canProceed = await confirmExperimentTransition("end the experiment");
  if (!canProceed) {
    return;
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
  } catch (error) {
    pushNotice("Could not end experiment", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

function renderExperimentStatus({ nexusEnabled } = { nexusEnabled: false }) {
  if (state.mode === "offline") {
    statusPillEl.textContent = "Offline";
  } else if (state.experiment.active) {
    statusPillEl.textContent = nexusEnabled
      ? state.mode === "openai" ? "OpenAI + Lab + Library" : "Fallback + Lab + Library"
      : state.mode === "openai" ? "OpenAI + Lab" : "Fallback + Lab";
    experimentBadgeEl.textContent = `Experiment mode. Temporary notes stay only in this session${state.experiment.savedNoteCount ? ` • ${state.experiment.savedNoteCount} temporary notes` : ""}.`;
  } else {
    statusPillEl.textContent = nexusEnabled
      ? state.mode === "openai" ? "OpenAI + Library" : "Fallback + Library"
      : state.mode === "openai" ? "OpenAI" : "Fallback";
    experimentBadgeEl.textContent = "Durable mode. Notes persist unless you start an experiment.";
  }
  startExperimentButtonEl.disabled = state.busy || state.experiment.active;
  endExperimentButtonEl.disabled = state.busy || !state.experiment.active;
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

  closeVantageButtonEl.textContent = surface.returnSurface === "whiteboard" ? "Back to whiteboard" : "Back to chat";
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
}

function buildVantageSummary() {
  const grounding = currentTurnGrounding();
  return buildGuidedInspectionSummary({
    responseMode: grounding.responseMode,
    scenarioLab: state.turn.scenarioLab,
    recallCount: grounding.recallCount,
    learnedCount: grounding.learnedCount,
    libraryCount: state.allConcepts.length + state.allSavedNotes.length + state.allVaultNotes.length,
    pinnedTitle: getPinnedMemoryItem()?.title || "",
  });
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
  const vantageOpen = surface.current === "vantage";
  const whiteboardFocused = isWhiteboardFocused(surface);

  if (chatSurfaceTitleEl) {
    chatSurfaceTitleEl.textContent = whiteboardFocused ? "Chat" : "Chat first.";
  }
  if (chatSurfaceSubtitleEl) {
    chatSurfaceSubtitleEl.hidden = whiteboardFocused;
    chatSurfaceSubtitleEl.textContent = whiteboardFocused
      ? "Keep the conversation moving here while the whiteboard stays center stage for drafting."
      : "Ask naturally. Open Vantage when you want to inspect the turn path or the library. Bring up the whiteboard when you want a shared draft.";
  }
  if (experimentBadgeEl) {
    experimentBadgeEl.hidden = whiteboardFocused;
  }
  seedPromptEl.hidden = whiteboardFocused;
  startExperimentButtonEl.hidden = whiteboardFocused;
  endExperimentButtonEl.hidden = whiteboardFocused;
  whiteboardToggleButtonEl.hidden = whiteboardFocused;
  statusPillEl.hidden = whiteboardFocused;
  vantageToggleButtonEl.textContent = whiteboardFocused ? "Open Vantage" : vantageButtonLabel(surface);
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
    return "Back to whiteboard";
  }
  const workspaceUpdate = state.turn.workspaceUpdate;
  if (workspaceUpdate?.status === "draft_ready") {
    return "Review draft";
  }
  if (workspaceUpdate?.status === "offered") {
    return workspaceUpdateHasDraft(workspaceUpdate) ? "Review draft" : "Open whiteboard";
  }
  if ((state.workspace.content || "").trim()) {
    return "Resume draft";
  }
  return "Whiteboard";
}

function vantageButtonLabel(surface) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current !== "vantage") {
    return "Vantage";
  }
  return normalized.returnSurface === "whiteboard" ? "Back to whiteboard" : "Close Vantage";
}

async function confirmExperimentTransition(actionLabel) {
  if (!state.workspace.dirty) {
    return true;
  }
  pushNotice("Saving whiteboard", `Saving the current whiteboard before you ${actionLabel}.`, "info");
  await saveWorkspace();
  if (state.workspace.dirty) {
    pushNotice("Whiteboard still unsaved", `The whiteboard could not be saved, so ${actionLabel} was cancelled.`, "warning");
    return false;
  }
  return true;
}

function applyWorkspacePayload(payload, { preserveDirty = false } = {}) {
  if (shouldPreserveUnsavedWorkspace({
    currentWorkspace: state.workspace,
    incomingWorkspace: payload,
    preserveDirty,
  })) {
    return false;
  }
  state.workspace.workspaceId = payload?.workspace_id || "";
  state.workspace.scope = payload?.scope || state.workspace.scope || "durable";
  state.workspace.title = payload?.title || "Whiteboard";
  state.workspace.content = payload?.content || "";
  state.workspace.savedContent = state.workspace.content;
  state.workspace.dirty = false;
  state.workspace.lifecycle = state.workspace.workspaceId ? "saved_whiteboard" : "ready";
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
    const selectedContextId = getSelectedMemoryIdForChat();
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
        selected_record_id: selectedContextId,
        memory_intent: state.turn.memoryIntent,
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
    graphAction: payload.graph_action || null,
    scenarioLab: normalizedTurnPayload.scenarioLab,
    interpretation: normalizeTurnInterpretation(payload.turn_interpretation),
    memoryIntent: "idle",
  };
  state.turnReasoningPathStageKey = "candidate-context";
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
    const branchCount = Array.isArray(payload.scenario_lab?.branches) ? payload.scenario_lab.branches.length : 0;
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
      message: `${errorMessage} Vantage answered in chat instead.`,
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
  if (payload.workspace_update?.summary) {
    const offer = ["offered", "draft_ready"].includes(payload.workspace_update?.status);
    notices.push({
      title: offer ? "Whiteboard ready" : "Whiteboard updated",
      message: payload.workspace_update.summary,
      tone: offer ? "info" : "success",
    });
  }
  if (payload.graph_action) {
    notices.push({
      title: "Saved action",
      message: describeGraphAction(payload.graph_action),
      tone: "success",
    });
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
      notices.push({
        title: isConcept ? "Concept added" : savedNoteBucket(savedItem) === "artifact" ? "Artifact added" : "Memory added",
        message: isConcept
          ? `${savedItem.title} was added to the concept KB.`
          : `${savedItem.title} was added to the durable library.`,
        tone: "success",
      });
      renderMemoryPanel();
    }
  }
  for (const note of notices) {
    pushNotice(note.title, note.message, note.tone);
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
    state.workspace.note = "Saved whiteboard written to disk.";
    workspaceTitleEl.textContent = state.workspace.title;
    persistTurnSnapshot();
    renderWorkspaceMeta();
    pushNotice("Whiteboard saved", `${state.workspace.title} was written to disk.`, "success");
    if (payload?.artifact_snapshot) {
      const snapshot = normalizeMemoryItem(payload.artifact_snapshot, "session");
      if (snapshot.id) {
        upsertSessionSavedNote(snapshot);
        rebuildConceptCatalog();
        renderMemoryPanel();
      }
    }
    if (payload?.graph_action) {
      pushNotice("Artifact iteration saved", describeGraphAction(payload.graph_action), "success");
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
          title: "Whiteboard unchanged",
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
      title: "Whiteboard unchanged",
      message: "The pending draft was left in review and the current whiteboard was kept as-is.",
      tone: "info",
    });
  }
}

async function openConceptIntoWorkspace(conceptId) {
  const concept = getConceptById(conceptId);
  if (!concept) {
    pushNotice("Item unavailable", "That concept, memory, or artifact is not in the local catalog.", "warning");
    return;
  }
  if (state.workspace.dirty) {
    queueWhiteboardDecision({
      kind: "open_record",
      targetId: concept.id,
      targetLabel: concept.title,
      targetTypeLabel: concept.type === "concept" ? "concept" : itemInspectorLabel(concept).toLowerCase(),
    });
    return;
  }
  await performOpenConceptIntoWorkspace(conceptId);
}

async function performOpenConceptIntoWorkspace(conceptId) {
  const concept = getConceptById(conceptId);
  if (!concept) {
    pushNotice("Item unavailable", "That concept, memory, or artifact is not in the local catalog.", "warning");
    return;
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
        note: `Opened ${concept.title}.`,
        markDirty: false,
      });
      persistTurnSnapshot();
      pushNotice("Whiteboard opened", `${concept.title} was loaded into the whiteboard.`, "success");
      clearWhiteboardDecision();
      revealWhiteboard();
      return;
    }

    const draft = buildConceptWorkspaceDraft(concept);
    applyWorkspaceDraft(draft, concept.title, {
      note: `Draft opened from ${concept.title}. Save to keep it.`,
      markDirty: true,
    });
    persistTurnSnapshot();
    pushNotice("Whiteboard opened", `${concept.title} is now in the whiteboard as a draft.`, "success");
    clearWhiteboardDecision();
    revealWhiteboard();
  } catch (error) {
    pushNotice("Open failed", error instanceof Error ? error.message : String(error), "warning");
  } finally {
    setBusy(false);
  }
}

async function openWorkspace(workspaceId) {
  if (!workspaceId) {
    pushNotice("Whiteboard unavailable", "That scenario branch does not have a whiteboard id.", "warning");
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
    state.workspace.note = `Opened scenario branch ${payload?.title || workspaceId}.`;
    persistTurnSnapshot();
    renderWorkspaceMeta();
    pushNotice("Whiteboard opened", `${payload?.title || workspaceId} is now the active whiteboard.`, "success");
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
  state.workspace.note = note || "Whiteboard updated.";
  workspaceTitleEl.textContent = state.workspace.title;
  workspaceEditorEl.value = content;
  renderWorkspaceMeta();
}

function startFreshWorkspaceDraft(content, title, { note, markDirty = true } = {}) {
  const nextTitle = title || inferWorkspaceTitle(content) || "Whiteboard Draft";
  const nextWorkspaceId = slugify(nextTitle || "whiteboard-draft");
  state.workspace.workspaceId = nextWorkspaceId;
  state.workspace.title = nextTitle;
  state.workspace.content = content;
  state.workspace.savedContent = markDirty ? "" : content;
  state.workspace.dirty = markDirty || content !== state.workspace.savedContent;
  state.workspace.lifecycle = state.workspace.dirty ? "transient_draft" : "saved_whiteboard";
  state.workspace.note = note || "Started a fresh whiteboard draft.";
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
  state.workspace.title = "Whiteboard";
  state.workspace.content = "";
  state.workspace.savedContent = "";
  state.workspace.dirty = false;
  state.workspace.lifecycle = "ready";
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
      note: "Opened this draft as a fresh whiteboard. Save it when you're ready.",
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
    ? "Draft appended from this turn. Save the whiteboard when you're ready."
    : "Draft pulled into the whiteboard from this turn. Save the whiteboard when you're ready.";

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
    state.workspace.note = "Whiteboard ready. Continue there to draft this work product.";
    renderWorkspaceMeta();
    return;
  }

  if (!workspaceUpdateHasDraft(state.turn.workspaceUpdate)) {
    prepareWorkspaceForWhiteboardOffer();
  }
  revealWhiteboard();
  state.workspace.note = "Opening the whiteboard so we can draft this work product together.";
  renderWorkspaceMeta();

  setBusy(true);
  try {
    const selectedContextId = getSelectedMemoryIdForChat();
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
        selected_record_id: selectedContextId,
        memory_intent: state.turn.memoryIntent,
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
    pushNotice("Whiteboard accept failed", error instanceof Error ? error.message : String(error), "warning");
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
      note: "Draft opened as a fresh whiteboard from this turn. Save it when you're ready.",
      markDirty: true,
    });
  } else {
    const nextTitle = workspaceUpdate.title || state.workspace.title;
    applyWorkspaceDraft(workspaceUpdate.content, nextTitle, {
      note: "Draft pulled into the whiteboard from this turn. Save the whiteboard when you're ready.",
      markDirty: true,
    });
  }
  state.turn.workspaceUpdate = {
    ...workspaceUpdate,
    decision: "applied",
  };
  pushNotice("Whiteboard drafted", "The accepted draft was pulled into the whiteboard for editing.", "success");
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
  state.workspace.note = state.workspace.dirty ? "Transient draft with unsaved changes." : "Saved whiteboard.";
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
  renderWhiteboardDecisionPanel();
  renderSurfaceStatus();
}

function renderTurnPanel() {
  const scenarioLab = state.turn.scenarioLab;
  const scenarioLabFailed = scenarioLab?.status === "failed";
  const scenarioBranchCount = Array.isArray(scenarioLab?.branches) ? scenarioLab.branches.length : 0;
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
  const nextTurnIntent = state.turn.memoryIntent || "idle";
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

  turnTitleEl.textContent = "What Influenced This Response?";
  if (scenarioLab && !scenarioLabFailed && !recallCount && !learnedCount) {
    turnMetaEl.textContent = hasGroundedContext || isBestGuess
      ? `Scenario Lab • Grounding: ${groundingCopy.groundingLabel}`
      : "Scenario Lab ran separately for this turn";
  } else {
    turnMetaEl.textContent = groundingCopy.metaText;
  }
  answerDockLabelEl.textContent = groundingCopy.answerDockLabel;
  turnIntentEl.textContent = groundingCopy.turnIntentLabel;
  turnActionsEl.hidden = false;

  const notes = [];
  if (scenarioLab && !scenarioLabFailed) {
    notes.push(
      scenarioBranchCount
        ? `Scenario Lab ran separately and produced ${scenarioBranchCount} branch${scenarioBranchCount === 1 ? "" : "es"}. Open the Scenario Lab panel for the recommendation, branch tradeoffs, and ${hasScenarioComparisonArtifact(scenarioLab) ? "saved comparison artifact" : "branch details"}.`
        : "Scenario Lab ran separately for this turn. Open the Scenario Lab panel to inspect its recommendation and branches.",
    );
  }
  if (responseMode.note) {
    notes.push(responseMode.note);
  }
  if (scenarioLabFailed) {
    const errorMessage = scenarioLab?.error?.message || "Scenario Lab could not complete this turn.";
    notes.push(`${errorMessage} Vantage answered in chat instead.`);
  }
  if (state.turn.vetting?.rationale) {
    notes.push(state.turn.vetting.rationale);
  }
  if (learnedCount) {
    notes.push(`Learned ${learnedCount} new item${learnedCount === 1 ? "" : "s"} after the answer.`);
  } else if (state.turn.graphAction) {
    notes.push(describeGraphAction(state.turn.graphAction));
  }
  turnNoticeEl.textContent = notes.filter(Boolean).join(" ")
    || "Recall, response path, and Learned items for the last turn will appear here once a response is available.";

  renderReasoningPathPanel(reasoningPath, interpretation);
  renderWorkspaceUpdatePanel(workspaceUpdate, { hidden: Boolean(scenarioLab && !scenarioLabFailed) });
  renderMemoryTracePanel();
  renderWhiteboardDecisionPanel();
  updateNextTurnIntentButtons(nextTurnIntent);
  renderScenarioLabPanel(scenarioLab);
  renderMemoryGroup(
    turnWorkingMemoryListEl,
    state.turnWorkingMemory,
    "turn",
    "No recalled items were selected for this turn.",
  );
  renderMemoryGroup(
    turnLearnedListEl,
    state.turnLearned,
    "learned",
    "Nothing new was learned from this turn.",
  );
  renderSurfaceStatus();
}

function renderReasoningPathPanel(reasoningPath, interpretation, { hidden = false } = {}) {
  turnReasoningPathSectionEl.hidden = hidden || !reasoningPath?.visible;
  turnReasoningPathMetaEl.innerHTML = "";
  turnReasoningPathRailEl.innerHTML = "";
  if (turnReasoningPathSectionEl.hidden || !reasoningPath) {
    return;
  }

  turnReasoningPathSummaryEl.textContent = reasoningPath.summary
    || "Vantage assembled a compact path for this turn.";

  const pathMode = interpretation?.mode ? humanizeInterpretationMode(interpretation.mode) : "Chat";
  turnReasoningPathMetaEl.append(
    createMiniMeta("Path", pathMode),
  );
  if (interpretation?.resolvedWhiteboardMode) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Whiteboard", humanizeInterpretationWhiteboardMode(interpretation.resolvedWhiteboardMode)),
    );
  }
  if (typeof interpretation?.confidence === "number" && Number.isFinite(interpretation.confidence) && interpretation.confidence > 0) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Confidence", `${Math.round(interpretation.confidence * 100)}%`),
    );
  }
  if (interpretation?.preserveSelectedRecord === true) {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Continuity", "Preserved selected context"),
    );
  }
  if (interpretation?.whiteboardModeSource === "composer") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Decision source", "Composer"),
    );
  } else if (interpretation?.whiteboardModeSource === "request") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Decision source", "User request"),
    );
  } else if (interpretation?.whiteboardModeSource === "interpreter") {
    turnReasoningPathMetaEl.append(
      createMiniMeta("Decision source", "Interpreter"),
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
    ? "Whiteboard Offer"
    : "Whiteboard Draft Ready";
  workspaceUpdateSummaryEl.textContent = workspaceUpdate.summary || (
    workspaceUpdate.status === "offered"
      ? "Vantage suggested continuing this work in the whiteboard."
      : "A whiteboard draft is ready for review."
  );

  if (workspaceUpdate.status === "offered") {
    const draftButton = createActionButton(
      workspaceUpdateHasDraft(workspaceUpdate) ? "Review in whiteboard" : "Open whiteboard",
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

  const applyButton = createActionButton("Apply to whiteboard", "primary");
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

  whiteboardDecisionLabelEl.textContent = presentation.label || "Whiteboard Decision";
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

function updateNextTurnIntentButtons(intent) {
  const mapping = [
    [rememberButtonEl, intent === "remember"],
    [dontSaveButtonEl, intent === "skip"],
    [showRelatedButtonEl, false],
  ];
  for (const [button, active] of mapping) {
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
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

  const heroMeta = document.createElement("div");
  heroMeta.className = "scenario-lab__hero-meta";

  if (scenarioLab.status === "failed") {
    scenarioDockLabelEl.textContent = "Fallback";
    heroSummary.textContent = scenarioLab.reason
      || "Scenario Lab was selected for this turn but could not complete.";
    heroMeta.append(createBadge("fallback", "warm"));

    const errorLabel = document.createElement("div");
    errorLabel.className = "section-label";
    errorLabel.textContent = "Failure";

    const errorNotice = document.createElement("div");
    errorNotice.className = "turn-notice turn-notice--decision scenario-lab__why";
    errorNotice.textContent = scenarioLab.error?.message
      ? `${scenarioLab.error.message} Vantage answered in chat instead.`
      : "Scenario Lab could not complete, so Vantage answered in chat instead.";

    const fallbackLabel = document.createElement("div");
    fallbackLabel.className = "section-label";
    fallbackLabel.textContent = "Fallback";

    const fallbackNotice = document.createElement("div");
    fallbackNotice.className = "turn-notice turn-notice--decision scenario-lab__grounding";
    fallbackNotice.textContent = "Vantage returned a normal chat answer instead of scenario branches.";

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
  const confidence = typeof scenarioLab.navigator?.confidence === "number"
    ? `Navigator confidence: ${Math.round(scenarioLab.navigator.confidence * 100)}%.`
    : "";
  const comparisonArtifact = scenarioLab.comparisonArtifact
    || (scenarioLab.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"
      ? scenarioLab.comparison_artifact
      : null);
  const artifactDetails = comparisonArtifact ? deriveScenarioArtifactDetails(comparisonArtifact) : null;
  const sharedAssumptions = scenarioLab.sharedAssumptions || artifactDetails?.sharedAssumptions || [];
  const tradeoffs = scenarioLab.tradeoffs || artifactDetails?.tradeoffs || [];
  const nextSteps = scenarioLab.nextSteps || artifactDetails?.nextSteps || [];
  const summary = [
    scenarioLab.summary || "Scenario Lab ran as a separate reasoning mode for this turn.",
    "Alternate branches stay separate from the turn context and surface here as a comparison-first review.",
    confidence,
  ].filter(Boolean).join(" ");
  const recommendation = scenarioLab.recommendation
    || artifactDetails?.recommendation
    || "A recommendation was not returned for this Scenario Lab run.";

  heroSummary.textContent = summary;
  const branchCount = Array.isArray(scenarioLab.branches) ? scenarioLab.branches.length : 0;
  scenarioDockLabelEl.textContent = branchCount
    ? `${branchCount} ${branchCount === 1 ? "branch" : "branches"} ready`
    : comparisonArtifact
      ? "Comparison ready"
      : "Scenario review";
  heroMeta.append(createBadge("Reasoning mode", "accent"));
  heroMeta.append(createBadge(branchCount ? `${branchCount} ${branchCount === 1 ? "branch" : "branches"}` : "No branches", "soft"));
  if (typeof scenarioLab.navigator?.confidence === "number") {
    heroMeta.append(createBadge(`${Math.round(scenarioLab.navigator.confidence * 100)}% confidence`, "soft"));
  }
  if (comparisonArtifact) {
    heroMeta.append(createBadge("Comparison artifact", "success"));
  }

  const overviewGrid = document.createElement("div");
  overviewGrid.className = "scenario-lab__overview-grid";
  overviewGrid.append(
    createScenarioOverviewCard({
      label: "Comparison question",
      body: scenarioQuestionText(scenarioLab),
      tone: "question",
    }),
  );
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
  whyLabel.className = "section-label";
  whyLabel.textContent = "Why Scenario Lab ran";

  const whyNotice = document.createElement("div");
  whyNotice.className = "turn-notice turn-notice--decision scenario-lab__why";
  whyNotice.textContent = navigatorReason || "Scenario Lab ran because this turn asked for alternate branches or comparative planning.";

  const groundingSectionLabelEl = document.createElement("div");
  groundingSectionLabelEl.className = "section-label";
  groundingSectionLabelEl.textContent = "Grounding";

  const groundingNotice = document.createElement("div");
  groundingNotice.className = "turn-notice turn-notice--decision scenario-lab__grounding";
  groundingNotice.textContent = responseModeNote
    || (hasGroundedContext
      ? `Grounded by ${currentGroundingLabel}.`
      : isBestGuess
        ? "No grounded context was used for this Scenario Lab turn."
        : "Grounding details were not returned for this Scenario Lab turn.");

  const groundingMeta = document.createElement("div");
  groundingMeta.className = "scenario-lab__grounding-meta";
  groundingMeta.append(
    createMiniMeta("grounding", currentGroundingLabel),
    createMiniMeta("recall", String(recallCount)),
    createMiniMeta("learned", String(learnedCount)),
  );

  const recommendationLabel = document.createElement("div");
  recommendationLabel.className = "section-label";
  recommendationLabel.textContent = "Recommendation";

  const recommendationNotice = document.createElement("div");
  recommendationNotice.className = "turn-notice scenario-lab__recommendation";
  recommendationNotice.textContent = recommendation;

  const recommendationMeta = document.createElement("div");
  recommendationMeta.className = "scenario-lab__grounding-meta";
  if (tradeoffs.length) {
    recommendationMeta.append(createMiniMeta("tradeoffs", String(tradeoffs.length)));
  }
  if (nextSteps.length) {
    recommendationMeta.append(createMiniMeta("next steps", String(nextSteps.length)));
  }
  if (comparisonArtifact?.branch_workspace_ids?.length) {
    recommendationMeta.append(createMiniMeta("branches linked", String(comparisonArtifact.branch_workspace_ids.length)));
  }

  const branchLabel = document.createElement("div");
  branchLabel.className = "section-label";
  branchLabel.textContent = "Branch paths";

  const branchList = document.createElement("div");
  branchList.className = "concept-list compact";

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
  artifactLabel.textContent = "Comparison artifact";

  const artifactList = document.createElement("div");
  artifactList.className = "concept-list compact";
  if (comparisonArtifact) {
    artifactList.appendChild(createScenarioArtifactCard(comparisonArtifact));
  } else {
    const empty = document.createElement("div");
    empty.className = "empty-note";
    empty.textContent = "No comparison artifact was saved for this turn.";
    artifactList.appendChild(empty);
  }

  scenarioLabSectionEl.append(
    hero,
    overviewGrid,
    whyLabel,
    whyNotice,
    groundingSectionLabelEl,
    groundingNotice,
    groundingMeta,
    recommendationLabel,
    recommendationNotice,
    recommendationMeta,
    branchLabel,
    branchList,
    artifactLabel,
    artifactList,
  );
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
    : `${totalConcepts} concepts · ${totalMemories} memories · ${totalArtifacts} artifacts · ${totalVaultNotes} references`;
  conceptsSummaryEl.textContent = `Concepts: ${visibleConcepts.length}`;
  memoriesSummaryEl.textContent = `Memories: ${visibleMemories.length}`;
  artifactsSummaryEl.textContent = `Artifacts: ${visibleArtifacts.length}`;
  vaultNotesSummaryEl.textContent = `References: ${visibleVaultNotes.length}`;
  conceptsHintEl.textContent = query
    ? "Filtered knowledge concepts"
    : state.experiment.active
      ? "Temporary experiment concepts first, then durable concepts"
      : "Durable reasoning concepts";
  memoriesHintEl.textContent = query
    ? "Filtered continuity notes"
    : state.experiment.active
      ? "Temporary experiment memories first, then durable memories"
      : "Durable continuity notes";
  artifactsHintEl.textContent = query
    ? "Filtered work products and snapshots"
    : state.experiment.active
      ? "Temporary experiment artifacts first, then durable artifacts"
      : "Durable work products and snapshots";
  vaultNotesHintEl.textContent = query ? "Filtered read-only reference notes" : "Read-only reference notes";
  memoryDockLabelEl.textContent = `${totalItems} items`;

  renderMemoryGroup(
    conceptListEl,
    visibleConcepts,
    "memory",
    query ? "No concepts matched that search. Try a title, phrase, or id." : "No concepts found yet.",
  );
  renderMemoryGroup(
    memoryListEl,
    visibleMemories,
    "memory",
    query ? "No memories matched that search. Try a title, phrase, or id." : "No memories found yet.",
  );
  renderMemoryGroup(
    artifactListEl,
    visibleArtifacts,
    "memory",
    query ? "No artifacts matched that search. Try a title, phrase, or id." : "No artifacts found yet.",
  );
  renderMemoryGroup(
    vaultNoteListEl,
    visibleVaultNotes,
    "memory",
    query ? "No reference notes matched that search. Try a path, label, or excerpt." : "No reference notes found yet.",
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
    ? `${pinnedItem.title} is pinned as next-turn context until you clear it.`
    : "Selection only opens something in review. Pin an item here to keep it in the next-turn context.";
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
    empty.textContent = "Select something in the library to review it here. Selection alone does not change next-turn context.";
    conceptInspectorEl.appendChild(empty);
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "inspector-shell";
  if (item.isVaultNote) {
    wrap.classList.add("inspector-shell--vault");
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

  const summary = document.createElement("p");
  summary.className = "inspector-summary";
  summary.textContent = item.card || (item.isVaultNote
    ? "This reference note has no excerpt yet."
    : item.type === "concept"
      ? "This concept has no summary card yet."
      : savedNoteBucket(item) === "artifact"
        ? "This artifact has no summary card yet."
        : "This memory has no summary card yet.");

  const body = document.createElement("div");
  body.className = "inspector-body";
  const bodyLabel = document.createElement("div");
  bodyLabel.className = "inspector-body-label";
  bodyLabel.textContent = item.isVaultNote ? "Reference note excerpt" : itemInspectorLabel(item);
  const bodyText = document.createElement("pre");
  bodyText.className = "inspector-pre";
  bodyText.textContent = item.body || (item.isVaultNote
      ? "Full reference note text is not available in this build. The memory panel has loaded the read-only excerpt."
      : item.type === "concept"
        ? "Full concept text is not available in this build. The inspector has loaded the summary card and current excerpt."
        : savedNoteBucket(item) === "artifact"
          ? "Full artifact text is not available in this build. The inspector has loaded the current summary card and excerpt."
          : "Full memory text is not available in this build. The inspector has loaded the current summary card and excerpt.");
  body.append(bodyLabel, bodyText);

  const footer = document.createElement("div");
  footer.className = "inspector-actions";
  const pinButton = createActionButton(
    isPinnedMemoryItem(item) ? "Unpin context" : "Pin as context",
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
  if (!item.isVaultNote) {
    const openButton = createActionButton("Open into workspace", "primary");
    openButton.addEventListener("click", async () => {
      await openConceptIntoWorkspace(item.id);
    });
    footer.append(openButton, pinButton, relatedButton);
  } else {
    footer.append(pinButton, relatedButton);
  }

  wrap.append(header, meta, summary, body, footer);
  conceptInspectorEl.appendChild(wrap);
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

function itemTypeLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "memory trace";
  }
  if (item?.isVaultNote) {
    return "reference";
  }
  if (item?.type === "concept") {
    return "concept";
  }
  return savedNoteBucket(item) === "artifact" ? "artifact" : "memory";
}

function itemInspectorLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "Memory Trace";
  }
  if (item?.isVaultNote) {
    return "Reference note";
  }
  if (item?.type === "concept") {
    return "Concept";
  }
  return savedNoteBucket(item) === "artifact" ? "Artifact" : "Memory";
}

function itemSourceSectionLabel(item) {
  if (item?.source === "memory_trace" || item?.type === "memory_trace") {
    return "Memory Trace";
  }
  if (item?.isVaultNote) {
    return item.sourceLabel || "Reference Notes";
  }
  if (item?.type === "concept") {
    return "Concept KB";
  }
  if (item?.source === "session") {
    return savedNoteBucket(item) === "artifact" ? "Staged artifact" : "Staged memory";
  }
  return savedNoteBucket(item) === "artifact" ? "Artifacts" : "Memories";
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

  const summary = document.createElement("p");
  summary.className = "concept-card-text";
  summary.textContent = item.card || (item.isVaultNote
    ? "No reference note excerpt available."
    : item.source === "memory_trace" || item.type === "memory_trace"
      ? "No memory trace summary available."
    : item.type === "concept"
      ? "No concept card available."
      : "No saved note card available.");

  const meta = document.createElement("div");
  meta.className = "concept-meta-row";
  if (context === "turn") {
    meta.append(createBadge("used this turn", "accent"));
  } else if (context === "reasoning-candidate") {
    meta.append(
      createBadge(
        item.reasoningStatusLabel || "candidate",
        item.reasoningStatusLabel === "selected into recall" ? "accent" : "soft",
      ),
    );
  } else if (context === "reasoning-recall") {
    meta.append(createBadge("selected into recall", "accent"));
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
  }
  if (isPinnedMemoryItem(item)) {
    meta.append(createBadge("pinned context", "success"));
  }
  if (item.isVaultNote) {
    meta.append(createBadge("read-only", "warm"));
  } else if (item.type === "concept" && item.source !== "session") {
    meta.append(createBadge("concept kb", "accent"));
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
  if ((item.links_to || []).length) {
    meta.append(createBadge(`${item.links_to.length} links`, "soft"));
  }

  const actions = document.createElement("div");
  actions.className = "concept-actions";
  const inspectButton = createActionButton("Inspect", "secondary");
  inspectButton.addEventListener("click", (event) => {
    event.stopPropagation();
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
    && item.source !== "memory_trace"
    && context !== "reasoning-candidate"
    && context !== "reasoning-recall";
  if (canOpenItem) {
    const openButton = createActionButton("Open", "primary");
    openButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await openConceptIntoWorkspace(item.id);
    });
    actions.append(openButton, inspectButton);
  } else {
    actions.append(inspectButton);
  }

  article.addEventListener("click", () => {
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

  article.append(top, title, summary, meta, actions);
  return article;
}

function createConceptCard(concept, context) {
  return createMemoryCard(concept, context);
}

function createScenarioBranchCard(branch) {
  const detailsModel = deriveScenarioBranchDetails(branch);
  const isActiveWhiteboard = state.workspace.workspaceId === branch.workspace_id;
  const article = document.createElement("article");
  article.className = "concept-card concept-card--turn scenario-lab__branch-card";
  if (isActiveWhiteboard) {
    article.classList.add("scenario-lab__branch-card--active");
  }

  const top = document.createElement("div");
  top.className = "concept-header";
  const type = document.createElement("span");
  type.className = "concept-type";
  type.textContent = "scenario branch";
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
  if (isActiveWhiteboard) {
    meta.append(createBadge("active whiteboard", "success"));
  }
  if (branch.confidence) {
    meta.append(createBadge(branch.confidence, "soft"));
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
    details.append(createMiniMeta("confidence", detailsModel.confidence));
  }
  if (branch.riskSummary || branch.risk_summary) {
    details.append(createMiniMeta("headline risk", branch.riskSummary || branch.risk_summary));
  }
  details.append(createMiniMeta("revisit action", isActiveWhiteboard ? "Already active in whiteboard" : "Reopen this branch in the whiteboard"));

  const signals = document.createElement("div");
  signals.className = "scenario-lab__signal-grid";
  appendScenarioListBlock(signals, "Shared assumptions", detailsModel.sharedAssumptions);
  appendScenarioListBlock(signals, "Preserved assumptions", detailsModel.preservedAssumptions);
  appendScenarioListBlock(signals, "Changed assumptions", detailsModel.changedAssumptions);
  appendScenarioListBlock(signals, "Risks", detailsModel.risks);
  appendScenarioListBlock(signals, "Open questions", detailsModel.openQuestions);

  const actions = document.createElement("div");
  actions.className = "concept-actions scenario-lab__card-actions";
  const openButton = createActionButton(isActiveWhiteboard ? "Already active in whiteboard" : "Revisit in whiteboard", "primary");
  openButton.disabled = isActiveWhiteboard;
  openButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await openWorkspace(branch.workspace_id);
  });
  actions.append(openButton);

  const actionHint = document.createElement("p");
  actionHint.className = "scenario-lab__action-hint";
  actionHint.textContent = isActiveWhiteboard
    ? "This branch is already the current whiteboard."
    : "Revisit opens this branch as the active whiteboard without pinning it into future turns.";

  article.append(top, title, summary, meta);
  if (details.children.length) {
    article.append(details);
  }
  if (signals.children.length) {
    article.append(signals);
  }
  article.append(actionHint, actions);
  return article;
}

function createScenarioArtifactCard(artifact) {
  const linkedBranchCount = Array.isArray(artifact?.branchWorkspaceIds)
    ? artifact.branchWorkspaceIds.length
    : Array.isArray(artifact?.branch_workspace_ids)
      ? artifact.branch_workspace_ids.length
      : 0;
  const item = normalizeMemoryItem(artifact, "scenario-artifact");
  const detailsModel = deriveScenarioArtifactDetails(item);
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
  type.textContent = "saved comparison";
  const id = document.createElement("span");
  id.className = "concept-id";
  id.textContent = isSelected ? "Open in review" : "Ready for review";
  top.append(type, id);

  const title = document.createElement("h3");
  title.className = "concept-title";
  title.textContent = item.title || "Scenario Comparison";

  const summary = document.createElement("p");
  summary.className = "concept-card-text";
  summary.textContent = item.card || detailsModel.summary || "Saved comparison ready to inspect or open in the whiteboard.";

  const meta = document.createElement("div");
  meta.className = "concept-meta-row";
  meta.append(createBadge("learned this turn", "success"));
  meta.append(createBadge("comparison artifact", "accent"));
  if (linkedBranchCount) {
    meta.append(createBadge(`${linkedBranchCount} branches linked`, "soft"));
  }
  if (item.status) {
    meta.append(createBadge(item.status, "soft"));
  }

  const lifecycle = document.createElement("div");
  lifecycle.className = "scenario-lab__artifact-lifecycle";
  lifecycle.textContent = isSelected
    ? "This artifact is open in review now. Inspecting it does not pin it into future turns."
    : "Saved this turn and ready for revisit. Open it in the whiteboard to continue from the comparison artifact, or inspect it in review.";

  const signals = document.createElement("div");
  signals.className = "scenario-lab__signal-grid";
  appendScenarioListBlock(signals, "Shared assumptions", detailsModel.sharedAssumptions);
  appendScenarioListBlock(signals, "Tradeoffs", detailsModel.tradeoffs);
  appendScenarioListBlock(signals, "Next steps", detailsModel.nextSteps);

  const actions = document.createElement("div");
  actions.className = "concept-actions scenario-lab__card-actions";
  const openButton = createActionButton("Open in whiteboard", "primary");
  openButton.addEventListener("click", async (event) => {
    event.stopPropagation();
    await openConceptIntoWorkspace(item.id);
  });
  const inspectButton = createActionButton(isSelected ? "Inspecting in review" : "Inspect in review", "secondary");
  inspectButton.disabled = isSelected;
  inspectButton.addEventListener("click", (event) => {
    event.stopPropagation();
    selectConcept(item.id);
  });
  actions.append(openButton, inspectButton);

  article.addEventListener("click", () => {
    selectConcept(item.id);
  });

  article.append(top, title, summary, meta, lifecycle);
  if (signals.children.length) {
    article.append(signals);
  }
  article.append(actions);
  return article;
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
  persistTurnSnapshot();
  if (!silent) {
    const label = concept.type === "concept"
      ? "Concept selected"
      : savedNoteBucket(concept) === "artifact"
        ? "Artifact selected"
        : "Memory selected";
    pushNotice(label, `${concept.title} is now open in review.`, "info");
  }
  renderMemoryPanel();
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
}

function pinSelectedMemoryForNextTurn() {
  const item = getSelectedMemoryItem();
  if (!item) {
    pushNotice("Nothing selected", "Inspect a concept, saved note, or reference note before pinning it for the next turn.", "info");
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
  pushNotice("Context pinned", `${item.title} will stay in pinned context until you clear it.`, "success");
}

function clearPinnedContext({ silent = false } = {}) {
  if (!state.pinnedContext) {
    return;
  }
  state.pinnedContext = null;
  persistTurnSnapshot();
  renderMemoryPanel();
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

function getSelectedMemoryIdForChat() {
  return state.pinnedContext?.id || null;
}

function getConceptById(conceptId) {
  return (
    state.allConcepts.find((concept) => concept.id === conceptId)
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
    card: concept.card || concept.summary || concept.description || "",
    body: concept.body || concept.content || concept.markdown || "",
    status: concept.status || "active",
    links_to: Array.isArray(concept.links_to) ? concept.links_to : Array.isArray(concept.linksTo) ? concept.linksTo : [],
    comes_from: Array.isArray(concept.comes_from) ? concept.comes_from : [],
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
  return {
    ...normalized,
    id: normalizeRecordId(item, path || normalized.id),
    kind: isVaultNote ? "vault_note" : String(item.kind || item.record_kind || "saved_note"),
    recordKind: String(item.record_kind || item.kind || item.type || ""),
    title: item.title || item.name || item.label || item.filename || normalized.title || (isVaultNote ? "Untitled reference note" : "Untitled saved note"),
    type: isVaultNote ? "reference note" : explicitType || "saved note",
    card: card || (isVaultNote ? body.slice(0, 160) : ""),
    body,
    status,
    links_to: Array.isArray(item.links_to) ? item.links_to : Array.isArray(item.linksTo) ? item.linksTo : normalized.links_to,
    comes_from: Array.isArray(item.comes_from) ? item.comes_from : normalized.comes_from,
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
    libraryBucket: isVaultNote ? "reference" : savedNoteBucket({ kind: item.kind, type: explicitType, path, filename: item.filename || normalized.filename || "" }),
    isVaultNote,
  };
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
    return isVaultNote ? "Turn reference notes" : "Turn durable notes";
  }
  if (value.includes("candidate")) {
    return isVaultNote ? "Candidate reference notes" : "Candidate durable notes";
  }
  if (value.includes("session")) {
    return isVaultNote ? "Session reference notes" : "Session durable notes";
  }
  if (value.includes("catalog")) {
    return isVaultNote ? "Reference notes" : "Durable notes";
  }
  if (value.includes("vault")) {
    return "Reference notes";
  }
  return isVaultNote ? "Reference notes" : "Durable notes";
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
      return "Concept created";
    case "create_memory":
      return "Memory saved";
    case "create_revision":
      return "Durable note revised";
    case "promote_workspace_to_artifact":
      return "Whiteboard saved as artifact";
    case "save_workspace_iteration_artifact":
      return "Artifact iteration saved";
    case "open_concept_into_workspace":
      return "Whiteboard opened from saved item";
    default:
      return value.replaceAll("_", " ");
  }
}

function labelForIntent(intent) {
  switch (intent) {
    case "remember":
      return "Next turn will be marked to remember.";
    case "skip":
      return "Next turn will be marked not to save.";
    case "related":
      return "Related notes are open in the library.";
    default:
      return "Idle";
  }
}

function createBadge(label, tone) {
  const badge = document.createElement("span");
  badge.className = `badge badge--${tone}`;
  badge.textContent = label;
  return badge;
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

function hasScenarioComparisonArtifact(scenarioLab) {
  return Boolean(
    scenarioLab?.comparisonArtifact
    || (scenarioLab?.comparison_artifact && typeof scenarioLab.comparison_artifact === "object"),
  );
}

function buildScenarioLabOutcomeCopy(branchCount, hasArtifact) {
  if (branchCount > 0 && hasArtifact) {
    return `Scenario Lab created ${branchCount} branch${branchCount === 1 ? "" : "es"} and saved a comparison artifact.`;
  }
  if (branchCount > 0) {
    return `Scenario Lab created ${branchCount} branch${branchCount === 1 ? "" : "es"} for review.`;
  }
  if (hasArtifact) {
    return "Scenario Lab saved a comparison artifact for review.";
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

function createScenarioTranscriptCard(scenarioLab) {
  const branchCount = Array.isArray(scenarioLab?.branches) ? scenarioLab.branches.length : 0;
  const artifactId = scenarioLab?.comparisonArtifact?.id || scenarioLab?.comparison_artifact?.id || "";
  const card = document.createElement("section");
  card.className = "message-scenario-card";

  const top = document.createElement("div");
  top.className = "message-scenario-card__top";
  const label = document.createElement("div");
  label.className = "section-label";
  label.textContent = "Scenario Lab";
  const meta = document.createElement("div");
  meta.className = "message-scenario-card__meta";
  if (branchCount) {
    meta.append(createBadge(`${branchCount} ${branchCount === 1 ? "branch" : "branches"}`, "soft"));
  }
  if (artifactId) {
    meta.append(createBadge("Saved comparison", "success"));
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
    ? (scenarioLab?.error?.message || "Scenario Lab could not complete this turn, so Vantage answered in chat instead.")
    : (scenarioLab?.recommendation || scenarioLab?.summary || (artifactId
      ? "Scenario branches and a saved comparison are ready to inspect."
      : "Scenario branches are ready to inspect."));

  const actions = document.createElement("div");
  actions.className = "message-scenario-card__actions";
  const openScenarioButton = createActionButton("Open Scenario Lab", "primary");
  openScenarioButton.addEventListener("click", () => {
    openVantage({ focus: "scenario" });
  });
  actions.append(openScenarioButton);
  if (artifactId) {
    const inspectArtifactButton = createActionButton("Inspect in Library", "secondary");
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
    return payload.workspace_update.summary || "Vantage suggested moving this work product into the whiteboard.";
  }
  if (payload?.workspace_update?.status === "draft_ready") {
    return payload.workspace_update.summary || "A whiteboard draft is ready to review before it changes the whiteboard.";
  }
  if (payload?.workspace_update?.summary) {
    return payload.workspace_update.summary;
  }
  if (payload?.graph_action?.type === "open_concept_into_workspace") {
    return "Whiteboard updated from the selected item.";
  }
  if (payload?.graph_action) {
    return `Whiteboard stayed available while Vantage recorded: ${describeGraphAction(payload.graph_action)}.`;
  }
  if ((state.workspace.content || "").trim()) {
    return "The whiteboard stayed separate as the drafting surface for this turn.";
  }
  return "Whiteboard ready as a separate drafting surface.";
}

function pushNotice(title, message, tone = "info") {
  const notice = {
    id: `${Date.now()}-${++state.noticeCounter}`,
    title,
    message,
    tone,
  };
  state.notices.unshift(notice);
  state.notices = state.notices.slice(0, 5);
  renderNotices();
  window.setTimeout(() => {
    state.notices = state.notices.filter((item) => item.id !== notice.id);
    renderNotices();
  }, 5000);
}

function renderNotices() {
  noticeRailEl.innerHTML = "";
  for (const notice of state.notices) {
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
}

function addMessage(role, text, { evidence = [], scenarioLab = null } = {}) {
  const node = messageTemplate.content.cloneNode(true);
  const article = node.querySelector(".message");
  article.classList.add(role);
  if (Array.isArray(evidence) && evidence.some((item) => item?.label === "Scenario Lab")) {
    article.classList.add("message--scenario-lab");
  }
  node.querySelector(".message-role").textContent = role;
  node.querySelector(".message-body").textContent = text;
  if (Array.isArray(evidence) && evidence.length) {
    const rail = document.createElement("div");
    rail.className = "message-evidence";
    for (const item of evidence) {
      if (!item?.label) {
        continue;
      }
      const badge = createBadge(item.label, item.tone || "soft");
      badge.classList.add("badge--message");
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
  rememberButtonEl.disabled = value;
  dontSaveButtonEl.disabled = value;
  showRelatedButtonEl.disabled = value;
  pinSelectedContextButtonEl.disabled = value || !getSelectedMemoryItem();
  clearPinnedContextButtonEl.disabled = value || !getPinnedMemoryItem();
  refreshConceptsButtonEl.disabled = value;
  startExperimentButtonEl.disabled = value || state.experiment.active;
  endExperimentButtonEl.disabled = value || !state.experiment.active;
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
