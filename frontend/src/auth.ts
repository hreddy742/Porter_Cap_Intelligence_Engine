// MVP auth boundary on the client side.
//
// Production auth is SSO (the backend reads identity from a gateway). For the MVP
// the user picks an identity + role here, which the API client sends as headers
// the backend's RBAC boundary enforces. This makes role-based behavior demoable
// without standing up SSO. Replace with a real session/token when SSO lands.

export const ROLES = ["sales", "underwriter", "ops", "admin", "compliance"] as const;
export type Role = (typeof ROLES)[number];

export interface CurrentUser {
  email: string;
  role: Role;
}

const STORAGE_KEY = "porter_verify_user";

const DEFAULT_USER: CurrentUser = { email: "dana@portercap.net", role: "sales" };

export function getUser(): CurrentUser {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return DEFAULT_USER;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return DEFAULT_USER;
  }
}

export function setUser(user: CurrentUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}
