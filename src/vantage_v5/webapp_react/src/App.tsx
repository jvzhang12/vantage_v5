import { useEffect, useMemo, useReducer } from "react";
import {
  createAccount,
  acceptArtifactAction,
  getCalendarWeek,
  getHealth,
  getWorkspace,
  login,
  logout,
  promoteWorkspace,
  rejectArtifactAction,
  saveWorkspace,
  sendChat,
} from "./api";
import { activeSurface, appReducer, initialState } from "./appReducer";
import {
  AppShell,
  ArtifactActionNotice,
  CommandComposer,
  GreetingState,
  LatestAnswerCard,
  LoginScreen,
  NoticeRail,
  TopBar,
} from "./components/Core";
import { DraftSurfaceNotice, SurfaceHost, WorkspaceDecision } from "./components/Surfaces";
import { normalizeSurfacePayloads } from "./normalizers";
import { buildVisibleArtifacts } from "./visibleArtifacts";
import type { SurfacePayload } from "./types";

function isoDateShift(date: string, days: number): string {
  const parsed = new Date(`${date}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return new Date().toISOString().slice(0, 10);
  }
  parsed.setDate(parsed.getDate() + days);
  return parsed.toISOString().slice(0, 10);
}

function calendarWeekSurfaceFromPayload(payload: Record<string, unknown>, date: string): SurfacePayload {
  const surfaces = normalizeSurfacePayloads([
    {
      id: `calendar-week-${String(payload.start_date || date)}`,
      kind: "calendar_week",
      title: "Week",
      summary: `${Number((payload.summary as Record<string, unknown> | undefined)?.event_count || 0)} scheduled events this week`,
      source_refs: [],
      data: {
        date,
        calendar_week: payload,
        suggestions: [],
      },
    },
  ]);
  return surfaces[0];
}

export function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const currentSurface = activeSurface(state);
  const proposedArtifactAction = state.latestTurn?.artifactActions.find((action) => action.status === "proposed") || null;
  const showLatestAnswer = Boolean(state.latestTurn && (state.view === "chat" || state.view === "artifact"));

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        const health = await getHealth();
        if (cancelled) {
          return;
        }
        dispatch({ type: "BOOTSTRAP_HEALTH", payload: health });
        if (health.authenticated) {
          const workspace = await getWorkspace();
          if (!cancelled) {
            dispatch({ type: "SET_WORKSPACE", payload: workspace });
          }
        }
      } catch (error) {
        if (!cancelled) {
          dispatch({ type: "AUTH_ERROR", message: error instanceof Error ? error.message : String(error) });
        }
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const contextLabel = useMemo(() => {
    const artifacts = buildVisibleArtifacts({
      activeSurface: currentSurface,
      workspace: state.workspace,
      view: state.view,
    });
    if (!artifacts.length) {
      return "No visible artifacts";
    }
    return `${artifacts.length} visible artifact${artifacts.length === 1 ? "" : "s"}`;
  }, [currentSurface, state.view, state.workspace]);

  async function handleLogin(username: string, password: string) {
    try {
      const payload = await login(username, password);
      dispatch({ type: "BOOTSTRAP_HEALTH", payload });
      const workspace = await getWorkspace();
      dispatch({ type: "SET_WORKSPACE", payload: workspace });
    } catch (error) {
      dispatch({ type: "AUTH_ERROR", message: error instanceof Error ? error.message : String(error) });
    }
  }

  async function handleCreateAccount(username: string, password: string, accessCode: string) {
    try {
      const payload = await createAccount(username, password, accessCode);
      dispatch({ type: "BOOTSTRAP_HEALTH", payload });
      const workspace = await getWorkspace();
      dispatch({ type: "SET_WORKSPACE", payload: workspace });
    } catch (error) {
      dispatch({ type: "AUTH_ERROR", message: error instanceof Error ? error.message : String(error) });
    }
  }

  async function handleLogout() {
    await logout().catch(() => null);
    dispatch({ type: "LOGOUT" });
  }

  async function handleSubmit() {
    const message = state.composerValue.trim();
    if (!message || state.busy) {
      return;
    }
    dispatch({ type: "CHAT_START" });
    try {
      const visibleArtifacts = buildVisibleArtifacts({
        activeSurface: currentSurface,
        workspace: state.workspace,
        view: state.view,
      });
      const workspaceVisible = state.view === "whiteboard" && state.workspace.content.trim();
      const turn = await sendChat({
        message,
        history: state.history,
        workspaceId: state.workspace.id || undefined,
        workspaceScope: workspaceVisible ? "visible" : "excluded",
        workspaceContent: workspaceVisible ? state.workspace.content : null,
        visibleArtifacts,
      });
      dispatch({ type: "CHAT_SUCCESS", turn });
    } catch (error) {
      dispatch({ type: "CHAT_ERROR", message: error instanceof Error ? error.message : String(error) });
    }
  }

  async function handleSaveWorkspace() {
    try {
      const payload = await saveWorkspace(state.workspace.content, state.workspace.id || undefined);
      dispatch({ type: "WORKSPACE_SAVED", payload });
    } catch (error) {
      dispatch({
        type: "SET_NOTICE",
        title: "Save failed",
        message: error instanceof Error ? error.message : String(error),
        tone: "warning",
      });
    }
  }

  async function handlePromoteWorkspace() {
    try {
      await promoteWorkspace({
        workspaceId: state.workspace.id || undefined,
        title: state.workspace.title,
        content: state.workspace.content,
      });
      dispatch({
        type: "SET_NOTICE",
        title: "Published",
        message: "The whiteboard was promoted into the Library.",
        tone: "success",
      });
    } catch (error) {
      dispatch({
        type: "SET_NOTICE",
        title: "Publish failed",
        message: error instanceof Error ? error.message : String(error),
        tone: "warning",
      });
    }
  }

  async function handleWeekShift(direction: -1 | 0 | 1) {
    const week = currentSurface?.data.calendar_week as Record<string, unknown> | undefined;
    const date = direction === 0
      ? "today"
      : isoDateShift(String(week?.start_date || currentSurface?.data.date || new Date().toISOString().slice(0, 10)), direction * 7);
    try {
      const payload = await getCalendarWeek(date);
      const resolvedDate = direction === 0 ? new Date().toISOString().slice(0, 10) : date;
      dispatch({ type: "UPSERT_SURFACE", surface: calendarWeekSurfaceFromPayload(payload, resolvedDate), active: true });
    } catch (error) {
      dispatch({
        type: "SET_NOTICE",
        title: "Calendar failed",
        message: error instanceof Error ? error.message : String(error),
        tone: "warning",
      });
    }
  }

  function handleSurfaceChange(surfaceId: string) {
    const surface = state.surfacePayloads.find((candidate) => candidate.id === surfaceId);
    if (surface) {
      dispatch({ type: "UPSERT_SURFACE", surface, active: true });
    }
  }

  async function handleArtifactActionApply(actionId: string) {
    dispatch({ type: "CHAT_START" });
    try {
      const result = await acceptArtifactAction(actionId);
      dispatch({ type: "ARTIFACT_ACTION_RESULT", result });
      dispatch({
        type: "SET_NOTICE",
        title: "Calendar updated",
        message: result.assistantMessage || "The calendar change was applied.",
        tone: "success",
      });
    } catch (error) {
      dispatch({ type: "CHAT_ERROR", message: error instanceof Error ? error.message : String(error) });
    }
  }

  async function handleArtifactActionDismiss(actionId: string) {
    dispatch({ type: "CHAT_START" });
    try {
      const result = await rejectArtifactAction(actionId);
      dispatch({ type: "ARTIFACT_ACTION_RESULT", result });
      dispatch({
        type: "SET_NOTICE",
        title: "Calendar unchanged",
        message: "I left the proposed change unapplied.",
        tone: "info",
      });
    } catch (error) {
      dispatch({ type: "CHAT_ERROR", message: error instanceof Error ? error.message : String(error) });
    }
  }

  if (state.auth.checking) {
    return (
      <AppShell>
        <div className="loading-screen">Opening Vantage...</div>
      </AppShell>
    );
  }

  if (state.auth.required && !state.auth.authenticated) {
    return (
      <AppShell>
        <LoginScreen
          allowCreate={state.auth.accountCreationEnabled}
          accountCreationCodeRequired={state.auth.accountCreationCodeRequired}
          error={state.auth.error}
          onCreateAccount={handleCreateAccount}
          onLogin={handleLogin}
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <TopBar
        auth={state.auth}
        onLogout={handleLogout}
        onOpenVantage={() => dispatch({ type: "SET_VIEW", view: "vantage" })}
        onToggleProfile={() => dispatch({ type: "SET_PROFILE_OPEN", open: !state.profileOpen })}
        profileOpen={state.profileOpen}
      />
      <main className={`app-main app-main--${state.view}`}>
        <div className="main-content">
          <SurfaceHost
            latestTurn={state.latestTurn}
            onBackToChat={() => dispatch({ type: "SET_VIEW", view: state.returnView })}
            onPromoteWorkspace={handlePromoteWorkspace}
            onRemoveSurface={() => dispatch({ type: "REMOVE_ACTIVE_ARTIFACT" })}
            onSaveWorkspace={handleSaveWorkspace}
            onSurfaceChange={handleSurfaceChange}
            onWeekShift={handleWeekShift}
            onWorkspaceChange={(content) => dispatch({ type: "UPDATE_WORKSPACE_CONTENT", content })}
            surface={currentSurface}
            surfaces={state.surfacePayloads}
            view={state.view}
            workspace={state.workspace}
          />
          {showLatestAnswer && state.latestTurn ? (
            <LatestAnswerCard turn={state.latestTurn} onInspect={() => dispatch({ type: "SET_VIEW", view: "vantage" })} />
          ) : null}
          {state.view === "chat" && !state.latestTurn ? <GreetingState /> : null}
          {state.view !== "vantage" ? <DraftSurfaceNotice turn={state.latestTurn} /> : null}
          {state.view !== "vantage" ? (
            <ArtifactActionNotice
              action={proposedArtifactAction}
              busy={state.busy}
              onApply={handleArtifactActionApply}
              onDismiss={handleArtifactActionDismiss}
            />
          ) : null}
          {state.view !== "vantage" ? <WorkspaceDecision workspace={state.workspace} onSave={handleSaveWorkspace} /> : null}
        </div>
        {state.view !== "vantage" ? (
          <CommandComposer
            busy={state.busy}
            contextLabel={contextLabel}
            onChange={(value) => dispatch({ type: "SET_COMPOSER", value })}
            onSubmit={handleSubmit}
            value={state.composerValue}
          />
        ) : null}
      </main>
      <NoticeRail notice={state.notice} onClear={() => dispatch({ type: "CLEAR_NOTICE" })} />
    </AppShell>
  );
}
