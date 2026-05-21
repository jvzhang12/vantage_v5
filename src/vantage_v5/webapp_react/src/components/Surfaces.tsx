import { CalendarDays, ChevronLeft, ChevronRight, Clock, FileText, ListTodo, Save, Upload, X } from "lucide-react";
import { asArray, asRecord, text } from "../normalizers";
import type { NormalizedTurn, SurfacePayload, WorkspaceState } from "../types";
import { ConfirmDialog, EmptyPanel, MiniActionButton, SourcePill, VantageGlyph } from "./Core";
import { VantageInspectionView } from "./Inspection";

function formatTime(value: unknown): string {
  const raw = text(value);
  if (!raw) {
    return "";
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDate(value: unknown): string {
  const raw = text(value);
  if (!raw) {
    return "";
  }
  const date = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }
  return date.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
}

function minutesLabel(value: unknown): string {
  const minutes = Number(value) || 0;
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    return rest ? `${hours}h ${rest}m` : `${hours}h`;
  }
  return `${minutes}m`;
}

function taskGroups(surface: SurfacePayload) {
  const tasks = asRecord(surface.data.tasks);
  return asRecord(tasks.groups);
}

function TaskGroup({ label, items }: { label: string; items: unknown[] }) {
  return (
    <section className="focus-group">
      <div className="focus-group__heading">
        <span>{label}</span>
        <small>{items.length}</small>
      </div>
      {items.length ? (
        <div className="focus-items">
          {items.map((item, index) => {
            const task = asRecord(item);
            return (
              <article className="focus-item" key={text(task.id) || `${label}-${index}`}>
                <ListTodo size={16} />
                <div>
                  <strong>{text(task.title || "Untitled task")}</strong>
                  <span>{task.due_date ? `Due ${text(task.due_date)}` : text(task.project || "No due date")}</span>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="surface-empty">Nothing here.</p>
      )}
    </section>
  );
}

function EventCard({ event }: { event: unknown }) {
  const record = asRecord(event);
  return (
    <article className="timeline-event">
      <div className="timeline-event__time">
        {formatTime(record.start)} - {formatTime(record.end)}
      </div>
      <div>
        <strong>{text(record.title || "Untitled event")}</strong>
        <span>{text(record.location || record.description || record.calendar_title)}</span>
      </div>
    </article>
  );
}

function OpenBlock({ block, suggestion }: { block: unknown; suggestion?: unknown }) {
  const record = asRecord(block);
  const suggestionRecord = asRecord(suggestion);
  return (
    <article className="timeline-open">
      <div className="timeline-event__time">
        Open · {formatTime(record.start)} - {formatTime(record.end)}
      </div>
      <div>
        <strong>{suggestionRecord.task_title ? `Suggested: ${text(suggestionRecord.task_title)}` : "Open focus window"}</strong>
        <span>{text(suggestionRecord.reason) || `${minutesLabel(record.duration_minutes)} available`}</span>
      </div>
      {suggestionRecord.task_title ? <SourcePill label="Best focus window" /> : null}
    </article>
  );
}

export function SurfaceHost({
  surface,
  latestTurn,
  surfaces,
  workspace,
  view,
  onSurfaceChange,
  onRemoveSurface,
  onWeekShift,
  onWorkspaceChange,
  onSaveWorkspace,
  onPromoteWorkspace,
  onBackToChat,
}: {
  surface: SurfacePayload | null;
  latestTurn: NormalizedTurn | null;
  surfaces: SurfacePayload[];
  workspace: WorkspaceState;
  view: string;
  onSurfaceChange: (surfaceId: string) => void;
  onRemoveSurface: () => void;
  onWeekShift: (direction: -1 | 0 | 1) => void;
  onWorkspaceChange: (content: string) => void;
  onSaveWorkspace: () => void;
  onPromoteWorkspace: () => void;
  onBackToChat: () => void;
}) {
  if (view === "vantage") {
    return <VantageInspectionView onBack={onBackToChat} surface={surface} turn={latestTurn} />;
  }
  if (view === "whiteboard") {
    return (
      <WhiteboardSurface
        workspace={workspace}
        onChange={onWorkspaceChange}
        onPromote={onPromoteWorkspace}
        onSave={onSaveWorkspace}
      />
    );
  }
  if (!surface || view !== "artifact") {
    return null;
  }
  return (
    <section className="surface-stage">
      <div className="surface-stage__chrome">
        <SurfaceSwitcher surfaces={surfaces.length ? surfaces : [surface]} activeId={surface.id} onChange={onSurfaceChange} />
        <button className="surface-remove-button" onClick={onRemoveSurface} type="button">
          <X size={14} />
          Remove artifact
        </button>
      </div>
      {surface.kind === "today_briefing" ? <TodayBriefingSurface surface={surface} /> : null}
      {surface.kind === "calendar_day" ? <CalendarDaySurface surface={surface} /> : null}
      {surface.kind === "calendar_week" ? <CalendarWeekSurface surface={surface} onWeekShift={onWeekShift} /> : null}
      {surface.kind === "task_focus" ? <TaskFocusSurface surface={surface} /> : null}
    </section>
  );
}

function SurfaceSwitcher({
  surfaces,
  activeId,
  onChange,
}: {
  surfaces: SurfacePayload[];
  activeId: string;
  onChange: (surfaceId: string) => void;
}) {
  if (surfaces.length <= 1) {
    return null;
  }
  return (
    <div className="surface-switcher">
      {surfaces.map((surface) => (
        <button
          className={surface.id === activeId ? "is-active" : ""}
          key={surface.id}
          onClick={() => onChange(surface.id)}
          type="button"
        >
          {surface.title}
        </button>
      ))}
    </div>
  );
}

export function TodayBriefingSurface({ surface }: { surface: SurfacePayload }) {
  const calendar = asRecord(surface.data.calendar);
  const events = asArray(calendar.events);
  const freeBlocks = asArray(calendar.free_blocks);
  const suggestions = asArray(surface.data.suggestions);
  const groups = taskGroups(surface);
  return (
    <div className="today-surface">
      <section className="today-left">
        <div className="surface-title-row">
          <div>
            <h2>Today</h2>
            <span>{formatDate(surface.data.date || calendar.date)}</span>
          </div>
          <SourcePill label="Day shape" />
        </div>
        <section className="focus-stack">
          <h3>Focus Stack</h3>
          <TaskGroup label="Must do today" items={asArray(groups.must_do_today)} />
          <TaskGroup label="Good next" items={asArray(groups.good_next)} />
          <TaskGroup label="Can defer" items={asArray(groups.can_defer)} />
        </section>
        <section className="vantage-response-card">
          <div>
            <VantageGlyph compact />
            <span>Vantage response</span>
          </div>
          <p>{surface.summary}</p>
        </section>
      </section>
      <section className="timeline-panel">
        <div className="timeline-panel__top">
          <h3>Timeline</h3>
          <SourcePill label={surface.summary} />
        </div>
        <div className="timeline-list">
          {events.map((event, index) => <EventCard event={event} key={text(asRecord(event).id) || index} />)}
          {freeBlocks.map((block, index) => (
            <OpenBlock block={block} suggestion={suggestions[index]} key={`${text(asRecord(block).start)}-${index}`} />
          ))}
          {!events.length && !freeBlocks.length ? <p className="surface-empty">No calendar data is configured yet.</p> : null}
        </div>
      </section>
    </div>
  );
}

export function CalendarDaySurface({ surface }: { surface: SurfacePayload }) {
  const calendar = asRecord(surface.data.calendar);
  const events = asArray(calendar.events);
  const freeBlocks = asArray(calendar.free_blocks);
  return (
    <section className="single-surface">
      <div className="surface-title-row">
        <div>
          <h2>{surface.title}</h2>
          <span>{formatDate(surface.data.date || calendar.date)}</span>
        </div>
        <CalendarDays size={20} />
      </div>
      <div className="timeline-list">
        {events.map((event, index) => <EventCard event={event} key={text(asRecord(event).id) || index} />)}
        {freeBlocks.map((block, index) => <OpenBlock block={block} key={`${text(asRecord(block).start)}-${index}`} />)}
      </div>
    </section>
  );
}

export function CalendarWeekSurface({ surface, onWeekShift }: { surface: SurfacePayload; onWeekShift: (direction: -1 | 0 | 1) => void }) {
  const week = asRecord(surface.data.calendar_week);
  const days = asArray(week.days);
  return (
    <section className="week-surface">
      <div className="week-toolbar">
        <div>
          <h2>Week</h2>
          <span>{text(week.start_date)} to {text(week.end_date)}</span>
        </div>
        <div>
          <MiniActionButton onClick={() => onWeekShift(-1)} title="Previous week"><ChevronLeft size={18} /></MiniActionButton>
          <MiniActionButton onClick={() => onWeekShift(0)} title="This week"><CalendarDays size={18} /></MiniActionButton>
          <MiniActionButton onClick={() => onWeekShift(1)} title="Next week"><ChevronRight size={18} /></MiniActionButton>
        </div>
      </div>
      <div className="week-grid">
        {days.map((day) => {
          const dayRecord = asRecord(day);
          const events = asArray(dayRecord.events);
          return (
            <article className="week-day" key={text(dayRecord.date)}>
              <header>
                <strong>{formatDate(dayRecord.date).split(",")[0]}</strong>
                <span>{text(dayRecord.date)}</span>
              </header>
              <div>
                {events.length ? events.map((event, index) => {
                  const eventRecord = asRecord(event);
                  return (
                    <section className="week-event" key={text(eventRecord.id) || index}>
                      <Clock size={13} />
                      <span>{formatTime(eventRecord.start)}</span>
                      <strong>{text(eventRecord.title)}</strong>
                    </section>
                  );
                }) : <p className="surface-empty">Open</p>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function TaskFocusSurface({ surface }: { surface: SurfacePayload }) {
  const groups = taskGroups(surface);
  return (
    <section className="single-surface">
      <div className="surface-title-row">
        <div>
          <h2>Today Focus</h2>
          <span>{surface.summary}</span>
        </div>
        <ListTodo size={20} />
      </div>
      <div className="task-grid">
        <TaskGroup label="Must do today" items={asArray(groups.must_do_today)} />
        <TaskGroup label="Good next" items={asArray(groups.good_next)} />
        <TaskGroup label="Can defer" items={asArray(groups.can_defer)} />
        <TaskGroup label="Unscheduled" items={asArray(groups.unscheduled)} />
      </div>
    </section>
  );
}

export function WhiteboardSurface({
  workspace,
  onChange,
  onSave,
  onPromote,
}: {
  workspace: WorkspaceState;
  onChange: (value: string) => void;
  onSave: () => void;
  onPromote: () => void;
}) {
  return (
    <section className="whiteboard-surface">
      <header>
        <div>
          <h2>{workspace.title || "Whiteboard"}</h2>
          <span>{workspace.dirty ? "Unsaved changes" : "Saved"}</span>
        </div>
        <div>
          <button onClick={onSave} type="button"><Save size={16} /> Save</button>
          <button onClick={onPromote} type="button"><Upload size={16} /> Publish</button>
        </div>
      </header>
      <textarea
        aria-label="Whiteboard content"
        onChange={(event) => onChange(event.target.value)}
        placeholder="Draft with Vantage..."
        value={workspace.content}
      />
    </section>
  );
}

export function LibrarySurface() {
  return <EmptyPanel title="Library" body="The React shell is the only product frontend path. Library parity belongs in React; FastAPI serves the generated build and fails loudly when it is missing." />;
}

export function ScenarioLabSurface() {
  return <EmptyPanel title="Scenario Lab" body="Scenario Lab payloads are normalized by the backend and ready for a dedicated React view." />;
}

export function WorkspaceDecision({
  workspace,
  onSave,
}: {
  workspace: WorkspaceState;
  onSave: () => void;
}) {
  if (!workspace.dirty) {
    return null;
  }
  return (
    <ConfirmDialog
      title="Unsaved whiteboard"
      summary="This draft is visible to Vantage as context while the whiteboard is open."
      actions={[{ label: "Save", icon: "save", onClick: onSave }]}
    />
  );
}

export function DraftSurfaceNotice({ turn }: { turn: NormalizedTurn | null }) {
  if (!turn?.workspaceUpdate?.summary) {
    return null;
  }
  return (
    <section className="draft-notice">
      <FileText size={16} />
      <span>{turn.workspaceUpdate.summary}</span>
    </section>
  );
}
