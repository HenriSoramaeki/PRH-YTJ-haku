/** HTTP Basic -header tähän istuntoon (sessionStorage). Tyhjä = ei autentikointia. */

const AUTH_KEY = "ek-ict-authorization";

export function getAuthHeaders(): Record<string, string> {
  try {
    const a = sessionStorage.getItem(AUTH_KEY);
    if (a) return { Authorization: a };
  } catch {
    /* private mode */
  }
  return {};
}

export function setSessionBasicAuth(user: string, password: string): void {
  const token = btoa(unescape(encodeURIComponent(`${user}:${password}`)));
  sessionStorage.setItem(AUTH_KEY, `Basic ${token}`);
}

export function clearSessionBasicAuth(): void {
  try {
    sessionStorage.removeItem(AUTH_KEY);
  } catch {
    /* ignore */
  }
}

export function hasSessionBasicAuth(): boolean {
  try {
    return Boolean(sessionStorage.getItem(AUTH_KEY));
  } catch {
    return false;
  }
}
