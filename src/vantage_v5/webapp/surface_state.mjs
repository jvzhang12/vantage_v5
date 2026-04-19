export const SURFACE_CHAT = "chat";
export const SURFACE_WHITEBOARD = "whiteboard";
export const SURFACE_VANTAGE = "vantage";

const VALID_SURFACES = new Set([
  SURFACE_CHAT,
  SURFACE_WHITEBOARD,
  SURFACE_VANTAGE,
]);

function normalizeSurface(value, fallback = SURFACE_CHAT) {
  const normalized = String(value || "").trim().toLowerCase();
  return VALID_SURFACES.has(normalized) ? normalized : fallback;
}

export function normalizeSurfaceState(surface = {}) {
  const legacyVantageOpen = surface?.vantageOpen === true;
  const legacyWhiteboardVisible = surface?.whiteboardVisible === true;

  let current = normalizeSurface(surface?.current, "");
  if (!current) {
    if (legacyVantageOpen) {
      current = SURFACE_VANTAGE;
    } else if (legacyWhiteboardVisible) {
      current = SURFACE_WHITEBOARD;
    } else {
      current = SURFACE_CHAT;
    }
  }

  let returnSurface = normalizeSurface(surface?.returnSurface, "");
  if (!returnSurface) {
    returnSurface = (
      current === SURFACE_VANTAGE
      && (legacyWhiteboardVisible || (legacyVantageOpen && legacyWhiteboardVisible))
    )
      ? SURFACE_WHITEBOARD
      : SURFACE_CHAT;
  }

  if (current !== SURFACE_VANTAGE) {
    returnSurface = SURFACE_CHAT;
  }
  if (returnSurface === SURFACE_VANTAGE) {
    returnSurface = SURFACE_CHAT;
  }

  return {
    current,
    returnSurface,
  };
}

export function isWhiteboardFocused(surface = {}) {
  return normalizeSurfaceState(surface).current === SURFACE_WHITEBOARD;
}

export function hasWhiteboardActiveContext(surface = {}) {
  return isWhiteboardFocused(surface);
}

export function revealWhiteboardSurface(surface = {}) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current === SURFACE_WHITEBOARD) {
    return normalized;
  }
  return toggleWhiteboardSurface(normalized);
}

export function hideWhiteboardSurface(surface = {}) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current === SURFACE_WHITEBOARD) {
    return toggleWhiteboardSurface(normalized);
  }
  if (
    normalized.current === SURFACE_VANTAGE
    && normalized.returnSurface === SURFACE_WHITEBOARD
  ) {
    return {
      current: SURFACE_CHAT,
      returnSurface: SURFACE_CHAT,
    };
  }
  return normalized;
}

export function openVantageSurface(surface = {}) {
  const normalized = normalizeSurfaceState(surface);
  return {
    current: SURFACE_VANTAGE,
    returnSurface: normalized.current === SURFACE_WHITEBOARD
      ? SURFACE_WHITEBOARD
      : SURFACE_CHAT,
  };
}

export function closeVantageSurface(surface = {}) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current !== SURFACE_VANTAGE) {
    return normalized;
  }
  if (normalized.returnSurface === SURFACE_WHITEBOARD) {
    return {
      current: SURFACE_WHITEBOARD,
      returnSurface: SURFACE_CHAT,
    };
  }
  return {
    current: SURFACE_CHAT,
    returnSurface: SURFACE_CHAT,
  };
}

export function toggleWhiteboardSurface(surface = {}) {
  const normalized = normalizeSurfaceState(surface);
  if (normalized.current === SURFACE_WHITEBOARD) {
    return {
      current: SURFACE_CHAT,
      returnSurface: SURFACE_CHAT,
    };
  }
  if (
    normalized.current === SURFACE_VANTAGE
    && normalized.returnSurface === SURFACE_WHITEBOARD
  ) {
    return {
      current: SURFACE_WHITEBOARD,
      returnSurface: SURFACE_CHAT,
    };
  }
  return {
    current: SURFACE_WHITEBOARD,
    returnSurface: SURFACE_CHAT,
  };
}

export function buildTurnSnapshotKey({
  scope = "durable",
  experimentSessionId = "",
  workspaceId = "",
} = {}) {
  const normalizedScope = String(scope || "").trim().toLowerCase() || "durable";
  const normalizedSession = String(experimentSessionId || "").trim() || "durable";
  const normalizedWorkspace = String(workspaceId || "").trim() || "default";
  return `vantage-v5-turn-snapshot::${normalizedScope}::${normalizedSession}::${normalizedWorkspace}`;
}

export function buildScopedTurnSnapshotKey({
  scope = "durable",
  experimentSessionId = "",
} = {}) {
  const normalizedScope = String(scope || "").trim().toLowerCase() || "durable";
  const normalizedSession = String(experimentSessionId || "").trim() || "durable";
  return `vantage-v5-turn-snapshot::${normalizedScope}::${normalizedSession}::active`;
}
