import {
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  Database,
  Eye,
  FileText,
  GitBranch,
  Layers3,
  ListChecks,
  Lock,
  MessageSquare,
  MinusCircle,
  PencilLine,
  Pin,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import type { ReactNode } from "react";
import { buildInspectionReceipt, type ContextUsedItemModel, type InspectionReceipt, type SurfaceDecisionModel } from "../inspectionModel";
import type {
  NormalizedTurn,
  SurfacePayload,
  WorkingMemoryResource,
  WorkingMemoryRoleName,
  WorkingMemoryRoleReference,
  WorkingMemoryView,
} from "../types";

const WORKING_MEMORY_ROLES: Array<{ key: WorkingMemoryRoleName; label: string }> = [
  { key: "answer_context", label: "Answer Context" },
  { key: "recall_context", label: "Recall Context" },
  { key: "protocol_guidance", label: "Protocol Guidance" },
  { key: "surface_to_open", label: "Surface To Open" },
  { key: "pinned_or_continuity_context", label: "Pinned / Continuity Context" },
];

export function VantageInspectionView({
  turn,
  surface,
  onBack,
}: {
  turn: NormalizedTurn | null;
  surface: SurfacePayload | null;
  onBack: () => void;
}) {
  const receipt = buildInspectionReceipt(turn, surface);
  if (!receipt) {
    return <EmptyInspectionState onBack={onBack} />;
  }

  const timestamp = formatTimestamp(receipt.timestamp);
  return (
    <section className="inspection-view" aria-label="Why this answer?">
      <div className="inspection-inner">
        <button className="inspection-back" onClick={onBack} type="button">
          <ChevronLeft size={16} />
          Back to chat
        </button>
        <header className="inspection-header">
          <div>
            <div className="inspection-title-line">
              <Sparkles size={28} />
              <h1>Working Memory</h1>
            </div>
            <p>What Vantage used for the latest response: bounded context, provenance, surface actions, and write summaries.</p>
          </div>
          <div className="inspection-turn-meta">
            <span>Turn{timestamp.time ? ` · ${timestamp.time}` : ""}</span>
            {timestamp.date ? <small>{timestamp.date}</small> : <small>Latest answer only</small>}
          </div>
        </header>

        <GenerationSummaryStrip receipt={receipt} />

        <WorkingMemoryPanel view={turn?.workingMemoryView ?? null} />

        <div className="inspection-grid">
          <ContextUsedCard items={receipt.contextItems} />
          <ArtifactsSurfacesCard decisions={receipt.surfaceDecisions} />
          <DecisionPathCard receipt={receipt} />
        </div>

        <MemoryActionsWritesCard receipt={receipt} />

        <footer className="inspection-footer">
          <Lock size={13} />
          <span>This is grounding evidence and execution context, not hidden chain-of-thought.</span>
        </footer>
      </div>
    </section>
  );
}

function WorkingMemoryPanel({ view }: { view: WorkingMemoryView | null }) {
  if (!view) {
    return (
      <section className="working-memory-panel" aria-label="Working Memory">
        <header>
          <div>
            <h2>Working Memory</h2>
            <p>No Working Memory payload for this turn.</p>
          </div>
          <span>Unavailable</span>
        </header>
      </section>
    );
  }
  const resourcesById = new Map(view.resources.map((resource) => [resource.resourceId, resource]));
  const sentCount = view.resources.filter((resource) => resource.sentToResponseLlm).length;
  const writeCategories = view.executionSummary.writes.categories.length
    ? view.executionSummary.writes.categories
    : ["none"];
  return (
    <section className="working-memory-panel" aria-label="Working Memory">
      <header>
        <div>
          <h2>Working Memory</h2>
          <p>Evidence Vantage used or kept in scope for the latest answer.</p>
        </div>
        <span>{view.schema || "working_memory_view"}</span>
      </header>

      <div className="working-memory-summary" aria-label="Working Memory summary">
        <SummaryStat label="Resources" value={`${view.resources.length}`} />
        <SummaryStat label="Sent to LLM" value={`${sentCount}`} />
        <SummaryStat label="Surface action" value={surfaceSummary(view)} />
        <SummaryStat label="Writes" value={writeCategories.map(humanize).join(" · ")} />
      </div>

      <ExecutionSummary view={view} />

      <div className="working-memory-sections">
        {WORKING_MEMORY_ROLES.map((role) => (
          <WorkingMemoryRoleSection
            key={role.key}
            label={role.label}
            refs={view.roles[role.key] || []}
            resourcesById={resourcesById}
          />
        ))}
      </div>
    </section>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value || "None"}</strong>
    </div>
  );
}

function ExecutionSummary({ view }: { view: WorkingMemoryView }) {
  const surface = view.executionSummary.surface;
  const writes = view.executionSummary.writes;
  const writeCategories = writes.categories.length ? writes.categories : ["none"];
  return (
    <section className="working-memory-execution" aria-label="Working Memory execution summary">
      <div>
        <span>Surface</span>
        <p>{surfaceSummary(view)}</p>
        {surface.targetResourceId ? <small>{surface.targetResourceId}</small> : null}
      </div>
      <div>
        <span>Write / proposal ledger</span>
        <div className="working-memory-chip-row">
          {writeCategories.map((category) => (
            <span className="working-memory-chip" key={category}>{humanize(category)}</span>
          ))}
        </div>
        {writes.effectAgreement ? <small>{humanize(writes.effectAgreement)}</small> : null}
      </div>
    </section>
  );
}

function WorkingMemoryRoleSection({
  label,
  refs,
  resourcesById,
}: {
  label: string;
  refs: WorkingMemoryRoleReference[];
  resourcesById: Map<string, WorkingMemoryResource>;
}) {
  return (
    <section className="working-memory-role">
      <header>
        <h3>{label}</h3>
        <span>{refs.length}</span>
      </header>
      {refs.length ? (
        <div className="working-memory-resource-list">
          {refs.map((ref) => (
            <WorkingMemoryResourceRow
              key={`${label}-${ref.resourceId}`}
              refItem={ref}
              resource={resourcesById.get(ref.resourceId) || null}
            />
          ))}
        </div>
      ) : (
        <p className="working-memory-empty">No resources in this role.</p>
      )}
    </section>
  );
}

function WorkingMemoryResourceRow({
  refItem,
  resource,
}: {
  refItem: WorkingMemoryRoleReference;
  resource: WorkingMemoryResource | null;
}) {
  const title = resource?.title || refItem.title || refItem.resourceId;
  const kind = resource?.kind || resource?.type || refItem.kind || "resource";
  const source = provenanceLabel(resource);
  const summary = resource?.excerpt || resource?.summary || "";
  const chips = resourceChips(resource, refItem);
  return (
    <article className="working-memory-resource">
      <div className="working-memory-resource__top">
        <div>
          <strong>{title}</strong>
          <span>{humanize(kind)}{source ? ` · ${source}` : ""}</span>
        </div>
        <code>{refItem.resourceId}</code>
      </div>
      {summary ? <p>{summary}</p> : <p className="working-memory-muted">No excerpt available.</p>}
      <div className="working-memory-chip-row" aria-label={`${title} flags`}>
        {chips.map((chip) => <span className="working-memory-chip" key={chip}>{chip}</span>)}
      </div>
    </article>
  );
}

function GenerationSummaryStrip({ receipt }: { receipt: InspectionReceipt }) {
  const icons = [MessageSquare, Target, Layers3, Lock, Sparkles];
  return (
    <section className="generation-strip" aria-label="Generation summary">
      {receipt.summaryColumns.map((column, index) => {
        const Icon = icons[index] || Sparkles;
        return (
          <article className="summary-column" key={column.key}>
            <div>
              <Icon size={17} />
              <span>{column.label}</span>
            </div>
            <strong>{column.value}</strong>
            {column.detail ? <small>{column.detail}</small> : null}
          </article>
        );
      })}
    </section>
  );
}

function ContextUsedCard({ items }: { items: ContextUsedItemModel[] }) {
  return (
    <InspectionCard icon={<ListChecks size={17} />} title="Context Used">
      <div className="context-used-list">
        {items.map((item) => <ContextUsedItem item={item} key={item.id} />)}
      </div>
    </InspectionCard>
  );
}

function ContextUsedItem({ item }: { item: ContextUsedItemModel }) {
  const Icon = contextIcon(item.type);
  return (
    <article className="context-used-item">
      <div className="context-used-item__icon">
        <Icon size={17} />
      </div>
      <div>
        <span>{item.type}</span>
        <strong>{item.title}</strong>
        <p>{item.description}</p>
      </div>
      <aside>Why: {item.why}</aside>
    </article>
  );
}

function ArtifactsSurfacesCard({ decisions }: { decisions: SurfaceDecisionModel[] }) {
  const opened = decisions.filter((decision) => decision.opened);
  const notOpened = decisions.filter((decision) => !decision.opened);
  return (
    <InspectionCard icon={<Layers3 size={17} />} title="Artifacts & Surfaces">
      <SurfaceDecisionGroup label="Opened" decisions={opened} />
      <SurfaceDecisionGroup label="Not opened" decisions={notOpened} />
    </InspectionCard>
  );
}

function SurfaceDecisionGroup({ label, decisions }: { label: string; decisions: SurfaceDecisionModel[] }) {
  if (!decisions.length) {
    return null;
  }
  return (
    <section className="surface-decision-group">
      <h3>{label}</h3>
      <div>
        {decisions.map((decision) => <SurfaceDecisionItem decision={decision} key={decision.id} />)}
      </div>
    </section>
  );
}

function SurfaceDecisionItem({ decision }: { decision: SurfaceDecisionModel }) {
  return (
    <article className={decision.opened ? "surface-decision is-open" : "surface-decision"}>
      <div className="surface-decision__status">
        {decision.opened ? <CheckCircle2 size={16} /> : <MinusCircle size={16} />}
      </div>
      <div>
        <div className="surface-decision__top">
          <strong>{decision.name}</strong>
          <span>{decision.mode}</span>
        </div>
        <p>{decision.reason}</p>
        {decision.detail ? <small>{decision.detail}</small> : null}
      </div>
    </article>
  );
}

function DecisionPathCard({ receipt }: { receipt: InspectionReceipt }) {
  return (
    <InspectionCard icon={<GitBranch size={17} />} title="Decision Path">
      <ol className="decision-path-list">
        {receipt.decisionPath.map((step, index) => (
          <li className="decision-path-step" key={step.id}>
            <div className="decision-path-step__index">{index + 1}</div>
            <div>
              <strong>{step.label}</strong>
              <p>{step.value}</p>
              {step.detail ? <small>{step.detail}</small> : null}
            </div>
          </li>
        ))}
      </ol>
    </InspectionCard>
  );
}

function MemoryActionsWritesCard({ receipt }: { receipt: InspectionReceipt }) {
  const writes = receipt.writes;
  return (
    <section className="writes-card">
      <header>
        <Database size={17} />
        <h2>Memory / Actions / Writes</h2>
      </header>
      <div className="writes-grid">
        <WriteColumn icon={<ShieldCheck size={15} />} label="Saved memory" values={writes.savedMemory} />
        <WriteColumn icon={<ListChecks size={15} />} label="Updated tasks" values={writes.updatedTasks} />
        <WriteColumn icon={<CalendarDays size={15} />} label="Edited calendar" values={writes.editedCalendar} />
        <WriteColumn icon={<FileText size={15} />} label="Created artifact" values={writes.createdArtifacts} />
        <WriteColumn icon={<PencilLine size={15} />} label="Draft writes" values={writes.draftWrites} />
        <WriteColumn icon={<Lock size={15} />} label="Mode this turn" values={[writes.mode]} />
        <WriteColumn icon={<Pin size={15} />} label="Assumptions" values={writes.assumptions} />
      </div>
    </section>
  );
}

function WriteColumn({ icon, label, values }: { icon: ReactNode; label: string; values: string[] }) {
  return (
    <article className="write-column">
      <div>
        {icon}
        <span>{label}</span>
      </div>
      {(values.length ? values : ["None"]).map((value, index) => <p key={`${label}-${index}`}>{value}</p>)}
    </article>
  );
}

function InspectionCard({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="inspection-card">
      <header>
        {icon}
        <h2>{title}</h2>
      </header>
      {children}
    </section>
  );
}

export function EmptyInspectionState({ onBack }: { onBack: () => void }) {
  return (
    <section className="inspection-view" aria-label="Empty Vantage inspection">
      <div className="inspection-inner inspection-inner--empty">
        <button className="inspection-back" onClick={onBack} type="button">
          <ChevronLeft size={16} />
          Back to chat
        </button>
        <div className="empty-inspection-state">
          <Eye size={24} />
          <h1>Ask Vantage something first.</h1>
          <p>This view will explain the latest answer.</p>
        </div>
      </div>
    </section>
  );
}

export function InspectionSkeleton() {
  return (
    <section className="inspection-view" aria-label="Loading Vantage inspection">
      <div className="inspection-inner">
        <div className="inspection-skeleton inspection-skeleton--header" />
        <div className="inspection-skeleton inspection-skeleton--strip" />
        <div className="inspection-grid">
          <div className="inspection-skeleton inspection-skeleton--card" />
          <div className="inspection-skeleton inspection-skeleton--card" />
          <div className="inspection-skeleton inspection-skeleton--card" />
        </div>
      </div>
    </section>
  );
}

function contextIcon(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes("calendar") || normalized.includes("date")) {
    return CalendarDays;
  }
  if (normalized.includes("task")) {
    return ListChecks;
  }
  if (normalized.includes("visible") || normalized.includes("whiteboard")) {
    return Eye;
  }
  if (normalized.includes("protocol")) {
    return ShieldCheck;
  }
  if (normalized.includes("pinned")) {
    return Pin;
  }
  return Database;
}

function surfaceSummary(view: WorkingMemoryView): string {
  const surface = view.executionSummary.surface;
  const mode = humanize(surface.mode || "none");
  const targetSurface = humanize(surface.surface || "chat");
  if (!surface.mode || surface.mode === "none") {
    return "No surface action";
  }
  if (surface.mode === "open_only") {
    return `Open-only ${targetSurface}`;
  }
  return `${mode} ${targetSurface}`.trim();
}

function provenanceLabel(resource: WorkingMemoryResource | null): string {
  if (!resource) {
    return "";
  }
  const provenance = resource.provenance;
  return firstNonEmpty(
    provenance.sourceLabel,
    provenance.source,
    provenance.scope,
    provenance.durability,
  );
}

function resourceChips(resource: WorkingMemoryResource | null, refItem: WorkingMemoryRoleReference): string[] {
  const chips: string[] = [];
  if (resource?.flags.selected) {
    chips.push("Selected");
  }
  if (resource?.flags.visible) {
    chips.push("Visible");
  }
  if (resource?.flags.pinned) {
    chips.push("Pinned");
  }
  const sentToLlm = resource?.sentToResponseLlm ?? refItem.sentToResponseLlm;
  if (sentToLlm === true) {
    chips.push("Sent to LLM");
  } else if (sentToLlm === false) {
    chips.push("Not sent to LLM");
  }
  if (resource?.influence.uiSurfaceAction) {
    chips.push("Surface action");
  }
  if (resource?.influence.writeOrProposalDecision) {
    chips.push("Write/proposal");
  }
  return chips.length ? chips : ["Context"];
}

function firstNonEmpty(...values: Array<string | undefined | null>): string {
  for (const value of values) {
    const candidate = String(value || "").trim();
    if (candidate) {
      return candidate;
    }
  }
  return "";
}

function humanize(value: string): string {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatTimestamp(value: string): { time: string; date: string } {
  if (!value) {
    return { time: "", date: "" };
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { time: "", date: value };
  }
  return {
    time: date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
    date: date.toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" }),
  };
}
