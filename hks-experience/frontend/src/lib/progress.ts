// Client-side "where was I" convenience only -- the backend session cookie
// is the real resume mechanism (reconciled against actual cluster state on
// every /api/steps call). This just remembers the last step id so the
// Welcome screen can offer "Continue where you left off" even if the
// backend session cookie didn't survive (different device, cleared
// cookies, etc).
const KEY = "hks-experience-last-step";

export function getLastStep(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setLastStep(stepId: string): void {
  try {
    localStorage.setItem(KEY, stepId);
  } catch {
    // localStorage unavailable (private browsing etc) -- resume just won't work, not fatal
  }
}
