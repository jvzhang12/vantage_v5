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
import type { NormalizedTurn, SurfacePayload } from "../types";

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
              <h1>Why this answer?</h1>
            </div>
            <p>Here&apos;s how I interpreted your request and what shaped my response.</p>
          </div>
          <div className="inspection-turn-meta">
            <span>Turn{timestamp.time ? ` · ${timestamp.time}` : ""}</span>
            {timestamp.date ? <small>{timestamp.date}</small> : <small>Latest answer only</small>}
          </div>
        </header>

        <GenerationSummaryStrip receipt={receipt} />

        <div className="inspection-grid">
          <ContextUsedCard items={receipt.contextItems} />
          <ArtifactsSurfacesCard decisions={receipt.surfaceDecisions} />
          <DecisionPathCard receipt={receipt} />
        </div>

        <MemoryActionsWritesCard receipt={receipt} />

        <footer className="inspection-footer">
          <Lock size={13} />
          <span>Vantage explains the reasoning behind the latest answer only.</span>
        </footer>
      </div>
    </section>
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
