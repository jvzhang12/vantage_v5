import {
  ArrowUp,
  CalendarDays,
  Check,
  ChevronDown,
  Eye,
  FileText,
  ListTodo,
  Lock,
  LogOut,
  Save,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { artifactActionLabel } from "../capabilities";
import type { AppState, ArtifactAction, NormalizedTurn, Notice } from "../types";
import { VantageMark } from "./VantageMark";

export function VantageGlyph({
  compact = false,
  size,
}: {
  compact?: boolean;
  size?: number | string;
}) {
  return <VantageMark className="vantage-glyph" size={size || (compact ? 18 : 32)} />;
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell min-h-screen overflow-hidden bg-graphite text-ivory">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(127,231,240,0.055),transparent_34%)]" />
      <div className="relative flex min-h-screen flex-col">{children}</div>
    </div>
  );
}

export function TopBar({
  auth,
  profileOpen,
  onOpenVantage,
  onToggleProfile,
  onLogout,
}: {
  auth: AppState["auth"];
  profileOpen: boolean;
  onOpenVantage: () => void;
  onToggleProfile: () => void;
  onLogout: () => void;
}) {
  return (
    <header className="topbar">
      <button className="topbar-vantage" onClick={onOpenVantage} type="button" title="Open Vantage">
        <VantageGlyph compact />
        <span>Vantage</span>
      </button>
      <div className="relative">
        <button className="profile-button" onClick={onToggleProfile} type="button">
          <UserRound size={18} />
          <span>Profile</span>
          <ChevronDown size={14} />
        </button>
        {profileOpen ? (
          <div className="profile-menu">
            <div className="profile-menu__meta">
              <span>{auth.userId || "Local user"}</span>
              <small>{auth.modelLabel || "Model status unknown"}</small>
            </div>
            <button onClick={onLogout} type="button">
              <LogOut size={15} />
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

export function GreetingState() {
  return (
    <section className="greeting-block" aria-label="Vantage greeting">
      <h1>
        Hi, I&apos;m <span>Vantage.</span>
      </h1>
      <p>
        Ask me about your day, priorities, drafts, decisions, or anything you want to work through.
      </p>
      <p>I&apos;ll keep the view quiet unless useful context should come into focus.</p>
    </section>
  );
}

export function CommandComposer({
  value,
  busy,
  contextLabel,
  onChange,
  onSubmit,
}: {
  value: string;
  busy: boolean;
  contextLabel?: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }
  return (
    <form className="composer-wrap" onSubmit={handleSubmit}>
      <div className="composer-shell">
        <div className="composer-icon">
          <VantageGlyph size={32} />
        </div>
        <input
          aria-label="Ask Vantage"
          autoComplete="off"
          disabled={busy}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask Vantage..."
          value={value}
        />
        <button className="composer-context" type="button" title={contextLabel || "Visible context"}>
          <Sparkles size={16} />
        </button>
        <button className="send-button" disabled={busy || !value.trim()} type="submit" title="Send">
          <ArrowUp size={20} />
        </button>
      </div>
      <div className="privacy-line">
        <Lock size={13} />
        <span>Your data stays private and secure.</span>
      </div>
    </form>
  );
}

export function LatestAnswerCard({
  turn,
  onInspect,
}: {
  turn: NormalizedTurn;
  onInspect: () => void;
}) {
  const sourceLabel = turn.answerBasis.label || turn.responseMode.label || "Intuitive Answer";
  return (
    <section className="latest-answer" aria-label="Latest Vantage answer">
      <div className="latest-answer__top">
        <VantageGlyph compact />
        <span>{new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>
      </div>
      <p>{turn.assistantMessage}</p>
      <div className="latest-answer__meta">
        <SourcePill label={sourceLabel} />
        {turn.surfacePayloads.length || turn.visibleArtifacts.length ? <SourcePill label="Used artifacts" /> : null}
        <button onClick={onInspect} type="button">Vantage</button>
      </div>
    </section>
  );
}

export function SourcePill({ label }: { label: string }) {
  return <span className="source-pill">{label}</span>;
}

export function NoticeRail({ notice, onClear }: { notice: Notice | null; onClear: () => void }) {
  if (!notice) {
    return null;
  }
  return (
    <aside className={`notice-rail notice-rail--${notice.tone}`}>
      <div>
        <strong>{notice.title}</strong>
        <p>{notice.message}</p>
      </div>
      <button onClick={onClear} type="button">Dismiss</button>
    </aside>
  );
}

export function ConfirmDialog({
  title,
  summary,
  actions,
}: {
  title: string;
  summary: string;
  actions: Array<{ label: string; icon?: "save" | "check"; onClick: () => void }>;
}) {
  return (
    <section className="confirm-dialog">
      <div>
        <h3>{title}</h3>
        <p>{summary}</p>
      </div>
      <div>
        {actions.map((action) => (
          <button key={action.label} onClick={action.onClick} type="button">
            {action.icon === "save" ? <Save size={15} /> : <Check size={15} />}
            {action.label}
          </button>
        ))}
      </div>
    </section>
  );
}

export function ArtifactActionNotice({
  actions,
  busy,
  onApply,
  onDismiss,
}: {
  actions: ArtifactAction[];
  busy: boolean;
  onApply: (actionId: string) => void;
  onDismiss: (actionId: string) => void;
}) {
  const proposedActions = actions.filter((action) => action.status === "proposed");
  if (!proposedActions.length) {
    return null;
  }
  return (
    <div className="artifact-action-stack" aria-label="Proposed artifact actions">
      {proposedActions.map((action) => (
        <section className="artifact-action-card" key={action.id}>
          <div className="artifact-action-card__icon">
            {action.artifactKind === "task" ? <ListTodo size={17} /> : <CalendarDays size={17} />}
          </div>
          <div>
            <span>{artifactActionLabel(action)}</span>
            <p>{action.summary}</p>
            {action.warnings.length ? <small>{action.warnings.join(" ")}</small> : null}
          </div>
          <div className="artifact-action-card__actions">
            <button disabled={busy} onClick={() => onDismiss(action.id)} type="button">
              <X size={14} />
              Dismiss
            </button>
            <button disabled={busy} onClick={() => onApply(action.id)} type="button">
              <Check size={14} />
              Apply
            </button>
          </div>
        </section>
      ))}
    </div>
  );
}

export function LoginScreen({
  accountCreationCodeRequired = false,
  allowCreate = false,
  error,
  onCreateAccount,
  onLogin,
}: {
  accountCreationCodeRequired?: boolean;
  allowCreate?: boolean;
  error: string;
  onCreateAccount?: (username: string, password: string, accessCode: string) => void;
  onLogin: (username: string, password: string) => void;
}) {
  const [mode, setMode] = useState<"login" | "create">("login");
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const username = String(data.get("username") || "");
    const password = String(data.get("password") || "");
    const accessCode = String(data.get("accessCode") || "");
    if (mode === "create" && onCreateAccount) {
      onCreateAccount(username, password, accessCode);
    } else {
      onLogin(username, password);
    }
  }
  return (
    <main className="auth-screen">
      <div className="auth-card">
        <VantageGlyph />
        <h1>Vantage</h1>
        <p>{mode === "create" ? "Create your local Vantage account." : "Sign in to continue to your local assistant workspace."}</p>
        <form onSubmit={handleSubmit}>
          <input name="username" placeholder="Username" autoComplete="username" />
          <input name="password" placeholder="Password" type="password" autoComplete={mode === "create" ? "new-password" : "current-password"} />
          {mode === "create" && accountCreationCodeRequired ? (
            <input name="accessCode" placeholder="Access code" type="password" autoComplete="one-time-code" required />
          ) : null}
          <button type="submit">{mode === "create" ? "Create account" : "Sign in"}</button>
        </form>
        {allowCreate ? (
          <button className="auth-mode-switch" onClick={() => setMode(mode === "create" ? "login" : "create")} type="button">
            {mode === "create" ? "Back to sign in" : "Create account"}
          </button>
        ) : null}
        {error ? <p className="auth-error">{error}</p> : null}
      </div>
    </main>
  );
}

export function MiniActionButton({
  children,
  onClick,
  title,
}: {
  children: ReactNode;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button className="mini-action" onClick={onClick} title={title} type="button">
      {children}
    </button>
  );
}

export function EmptyPanel({ icon = "file", title, body }: { icon?: "file" | "eye"; title: string; body: string }) {
  return (
    <section className="empty-panel">
      {icon === "eye" ? <Eye size={22} /> : <FileText size={22} />}
      <h2>{title}</h2>
      <p>{body}</p>
    </section>
  );
}
