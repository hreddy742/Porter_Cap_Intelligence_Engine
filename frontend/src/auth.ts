// Client-side auth state.
//
// Identity is established by a Bearer API key issued by the Porter admin
// (set via PORTER_API_KEYS on the backend).  The key is stored in
// localStorage and sent as Authorization: Bearer <apiKey> on every request.
// The email and role shown in the UI are fetched from GET /auth/me after the
// user enters their key — they are never self-asserted.

export const ROLES = ["sales", "underwriter", "ops", "admin", "compliance"] as const;
export type Role = (typeof ROLES)[number];

export interface CurrentUser {
  email: string;
  role: Role;
  apiKey: string;
}

const STORAGE_KEY = "porter_verify_user";

export function getUser(): CurrentUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CurrentUser;
    // Guard against stale storage that predates the apiKey field.
    if (!parsed.apiKey) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function setUser(user: CurrentUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function clearUser(): void {
  localStorage.removeItem(STORAGE_KEY);
}
