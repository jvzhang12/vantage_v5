export type ViewKind = "chat" | "whiteboard" | "vantage" | "artifact" | "library" | "scenario_lab";

export type SurfaceKind =
  | "today_briefing"
  | "calendar_day"
  | "calendar_week"
  | "task_focus"
  | "whiteboard"
  | "draft"
  | "inspect"
  | "library"
  | "scenario_lab";

export interface HealthPayload {
  status?: string;
  auth_required?: boolean;
  authenticated?: boolean;
  account_creation_enabled?: boolean;
  account_creation_code_required?: boolean;
  multi_user?: boolean;
  model?: string;
  model_provider?: string;
  mode?: string;
  user?: { id?: string } | null;
  workspace_id?: string | null;
  model_auth?: Record<string, unknown>;
  openai_key?: Record<string, unknown>;
  experiment?: Record<string, unknown>;
}

export interface WorkspacePayload {
  workspace_id?: string;
  id?: string;
  title?: string;
  content?: string | null;
  scope?: string;
  graph_action?: unknown;
  artifact_snapshot?: unknown;
}

export interface ChatHistoryItem {
  user_message: string;
  assistant_message: string;
}

export interface SourceRef {
  id?: string;
  title?: string;
  source?: string;
  kind?: string;
  label?: string;
}

export interface SurfacePayload {
  id: string;
  kind: SurfaceKind;
  title: string;
  summary: string;
  sourceRefs: SourceRef[];
  data: Record<string, unknown>;
}

export interface SurfaceInvocationSurface {
  kind: string;
  role: string;
  reason: string;
  status: string;
}

export interface SurfaceInvocation {
  intent: string;
  primarySurface: string;
  supportingSurfaces: string[];
  surfaces: SurfaceInvocationSurface[];
  writeBehavior: string;
  reason: string;
  confidence: number | null;
  dataSources: string[];
  trigger: string;
  policyVersion: string;
}

export interface AnswerBasis {
  kind: string;
  label: string;
  summary: string;
  hasFactualGrounding: boolean;
  sources: string[];
  counts: Record<string, number>;
}

export interface ResponseMode {
  kind: string;
  label: string;
  groundingMode: string;
  contextSources: string[];
  recallCount: number;
  note: string;
}

export interface RecallItem {
  id: string;
  title: string;
  source: string;
  type: string;
  card: string;
  reason: string;
}

export interface WorkspaceUpdate {
  type: string;
  status: string;
  proposalKind: string;
  summary: string;
  title: string;
  content: string;
  decision: string;
  persisted: boolean;
}

export interface ArtifactAction {
  id: string;
  artifactKind: string;
  operation: string;
  status: "proposed" | "accepted" | "rejected" | "failed" | string;
  summary: string;
  targetRefs: SourceRef[];
  payload: Record<string, unknown>;
  preview: Record<string, unknown>;
  warnings: string[];
  requiresConfirmation: boolean;
  sourceRefs: SourceRef[];
}

export interface ContextBudgetRow {
  key: string;
  label: string;
  status: string;
  displayStatus: string;
  detail: string;
  count: number | null;
  scope: string;
}

export interface ContextBudget {
  label: string;
  summary: string;
  rows: ContextBudgetRow[];
  counts: Record<string, number>;
  contextSources: string[];
}

export interface ActivityStep {
  id: string;
  type: string;
  label: string;
  status: string;
  summary: string;
  createdAt: string;
}

export interface ActivityPayload {
  mode: string;
  kind: string;
  status: string;
  summary: string;
  steps: ActivityStep[];
  recallCount: number;
  learnedCount: number;
  createdRecordId: string;
  graphActionType: string;
  workspaceUpdateStatus: string;
}

export interface SemanticFrame {
  userGoal: string;
  taskType: string;
  followUpType: string;
  targetSurface: string;
  confidence: number;
  needsClarification: boolean;
  clarificationPrompt: string | null;
  commitments: string[];
  signals: Record<string, unknown>;
}

export interface SemanticPolicy {
  semanticAction: string;
  actionLabel: string;
  needsClarification: boolean;
  clarificationPrompt: string | null;
  status: string;
  reason: string;
  confidence: number;
  blocking: boolean;
  signals: Record<string, unknown>;
}

export interface NormalizedTurn {
  userMessage: string;
  assistantMessage: string;
  mode: string;
  timestamp: string;
  answerBasis: AnswerBasis;
  responseMode: ResponseMode;
  recallItems: RecallItem[];
  learnedItems: RecallItem[];
  memoryTraceRecord: RecallItem | null;
  surfaceInvocation: SurfaceInvocation | null;
  surfacePayloads: SurfacePayload[];
  activeSurfaceId: string | null;
  artifactActions: ArtifactAction[];
  workspaceUpdate: WorkspaceUpdate | null;
  contextBudget: ContextBudget | null;
  activity: ActivityPayload | null;
  turnInterpretation: Record<string, unknown> | null;
  semanticFrame: SemanticFrame | null;
  semanticPolicy: SemanticPolicy | null;
  visibleArtifacts: Record<string, unknown>[];
  metaAction: Record<string, unknown> | null;
  graphAction: Record<string, unknown> | null;
  createdRecord: Record<string, unknown> | null;
  stageProgress: ActivityStep[];
  raw: Record<string, unknown>;
}

export interface WorkspaceState {
  id: string;
  title: string;
  content: string;
  scope: string;
  dirty: boolean;
  pinnedToChat: boolean;
}

export interface AuthState {
  checking: boolean;
  required: boolean;
  authenticated: boolean;
  accountCreationEnabled: boolean;
  accountCreationCodeRequired: boolean;
  userId: string;
  modelLabel: string;
  error: string;
}

export interface Notice {
  id: number;
  title: string;
  message: string;
  tone: "info" | "success" | "warning";
}

export interface AppState {
  auth: AuthState;
  view: ViewKind;
  returnView: ViewKind;
  composerValue: string;
  busy: boolean;
  profileOpen: boolean;
  history: ChatHistoryItem[];
  latestTurn: NormalizedTurn | null;
  activeSurfaceId: string | null;
  surfacePayloads: SurfacePayload[];
  workspace: WorkspaceState;
  notice: Notice | null;
}

export type JsonRecord = Record<string, unknown>;
