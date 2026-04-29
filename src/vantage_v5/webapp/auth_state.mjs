const LOGIN_PATH = "/api/login";

export function normalizeRequestPath(path) {
  const rawPath = String(path || "").trim();
  if (!rawPath) {
    return "";
  }
  try {
    return new URL(rawPath, "http://vantage.local").pathname;
  } catch {
    return rawPath.split("?")[0] || rawPath;
  }
}

export function shouldHandleAuthChallenge({ path = "", status = 0 } = {}) {
  return Number(status) === 401 && normalizeRequestPath(path) !== LOGIN_PATH;
}

export function authChallengeMessage(payload = {}) {
  const detail = typeof payload?.detail === "string" ? payload.detail.trim() : "";
  if (detail && detail !== "Authentication required.") {
    return detail;
  }
  return "Your Vantage session expired. Sign in again to continue.";
}
