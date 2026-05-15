import { asArray, asRecord, text } from "./normalizers";
import type { ArtifactAction, SurfacePayload } from "./types";

const SURFACE_LABELS: Record<string, string> = {
  today_briefing: "Today Briefing",
  calendar_day: "Calendar",
  calendar_week: "Calendar Week",
  task_focus: "Task Focus",
  whiteboard: "Whiteboard",
  draft: "Draft",
  inspect: "Vantage",
  scenario_lab: "Scenario Lab",
  library: "Library",
  code_artifact: "Code Artifact",
  chat: "Chat",
};

const ARTIFACT_KIND_LABELS: Record<string, string> = {
  calendar: "Calendar",
  task: "Tasks",
  whiteboard: "Whiteboard",
};

export function surfaceLabel(kind?: string): string {
  const normalized = text(kind);
  return SURFACE_LABELS[normalized] || humanize(normalized || "surface");
}

export function artifactKindLabel(kind?: string): string {
  const normalized = text(kind);
  return ARTIFACT_KIND_LABELS[normalized] || "Artifact";
}

export function artifactActionLabel(action: ArtifactAction): string {
  const kind = artifactKindLabel(action.artifactKind);
  return kind === "Artifact" ? "Proposed update" : `Proposed ${kind.toLowerCase()} update`;
}

function formatDateTime(value: unknown): string {
  const raw = text(value);
  if (!raw) {
    return "";
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return raw;
  }
  return date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function eventLine(event: unknown): string {
  const record = asRecord(event);
  const timeRange = [formatDateTime(record.start), formatDateTime(record.end)].filter(Boolean).join(" - ");
  const details = [text(record.title || "Untitled event"), timeRange, text(record.location)].filter(Boolean);
  return `- ${details.join(" | ")}`;
}

function taskLine(task: unknown): string {
  const record = asRecord(task);
  const details = [
    text(record.title || "Untitled task"),
    record.due_date ? `due ${text(record.due_date)}` : "",
    text(record.priority),
  ].filter(Boolean);
  return `- ${details.join(" | ")}`;
}

export function surfaceToMarkdown(surface: SurfacePayload): string {
  if (surface.kind === "calendar_week") {
    return calendarWeekToMarkdown(surface);
  }
  if (surface.kind === "calendar_day" || surface.kind === "today_briefing") {
    return calendarDayToMarkdown(surface);
  }
  if (surface.kind === "task_focus") {
    return taskFocusToMarkdown(surface);
  }
  return [`# ${surface.title}`, surface.summary].filter(Boolean).join("\n\n");
}

function calendarWeekToMarkdown(surface: SurfacePayload): string {
  const week = asRecord(surface.data.calendar_week);
  const days = asArray(week.days);
  const lines = [
    `# ${surface.title}`,
    surface.summary,
    `Week: ${text(week.start_date)} to ${text(week.end_date)}`,
    "",
  ];
  for (const day of days) {
    const dayRecord = asRecord(day);
    lines.push(`## ${text(dayRecord.date)}`);
    const events = asArray(dayRecord.events);
    lines.push(...(events.length ? events.map(eventLine) : ["- No scheduled events"]));
    lines.push("");
  }
  return lines.join("\n").trim();
}

function calendarDayToMarkdown(surface: SurfacePayload): string {
  const calendar = asRecord(surface.data.calendar);
  const events = asArray(calendar.events);
  const freeBlocks = asArray(calendar.free_blocks);
  const lines = [
    `# ${surface.title}`,
    surface.summary,
    `Date: ${text(surface.data.date || calendar.date)}`,
    "",
    "## Events",
    ...(events.length ? events.map(eventLine) : ["- No scheduled events"]),
    "",
    "## Open Blocks",
    ...(freeBlocks.length
      ? freeBlocks.map((block) => {
        const record = asRecord(block);
        return `- ${formatDateTime(record.start)} - ${formatDateTime(record.end)} (${record.duration_minutes || 0} minutes)`;
      })
      : ["- No open blocks"]),
  ];
  if (surface.kind === "today_briefing") {
    lines.push("", "## Focus Suggestions");
    const suggestions = asArray(surface.data.suggestions);
    lines.push(...(suggestions.length
      ? suggestions.map((item) => {
        const record = asRecord(item);
        return `- ${text(record.task_title)} | ${formatDateTime(record.start)} - ${formatDateTime(record.end)} | ${text(record.reason)}`;
      })
      : ["- No suggestions"]));
  }
  return lines.join("\n").trim();
}

function taskFocusToMarkdown(surface: SurfacePayload): string {
  const tasks = asRecord(surface.data.tasks);
  const groups = asRecord(tasks.groups);
  const lines = [`# ${surface.title}`, surface.summary, `Date: ${text(surface.data.date || tasks.date)}`, ""];
  for (const key of ["must_do_today", "good_next", "can_defer", "unscheduled"]) {
    const title = key.replaceAll("_", " ");
    const items = asArray(groups[key]);
    lines.push(`## ${title}`, ...(items.length ? items.map(taskLine) : ["- None"]), "");
  }
  return lines.join("\n").trim();
}

function humanize(value: string): string {
  return text(value)
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}
