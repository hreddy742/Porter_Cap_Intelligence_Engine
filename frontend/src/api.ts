// Typed API client for the Porter Verify backend.
//
// One small fetch wrapper attaches the auth headers and surfaces clean errors.
// Types mirror the backend Pydantic schemas (kept deliberately in sync).

import { getUser } from "./auth";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type VerificationStatus =
  | "verified"
  | "likely_match"
  | "needs_review"
  | "insufficient_evidence"
  | "inactive_not_eligible"
  | "risk_flag";

export interface VerifyResponse {
  run_id: string;
  run_status: string;
  verification_status: VerificationStatus | null;
  company_id: string | null;
  match_confidence: number | null;
  message: string;
}

export interface CompanySummary {
  id: string;
  canonical_legal_name: string;
  home_state: string | null;
  status_normalized: string;
  verification_status: VerificationStatus | null;
  match_confidence: number | null;
}

export interface RecentBusiness {
  state: string;
  entity_id: string;
  legal_name: string;
  entity_type: string | null;
  registration_or_formation_date: string;
  date_basis: string;
  status_raw: string | null;
  jurisdiction: string | null;
  principal_address: string | null;
  source_record_url: string;
  domestic_signal: boolean;
  active_signal: boolean;
  nonprofit_signal: boolean;
  relevant_entity_signal: boolean;
}

export interface RecentBusinessFilters {
  states: string[];
  formed_from: string;
  formed_to: string;
}

export interface Registration {
  state: string;
  state_entity_id: string;
  entity_type: string | null;
  formation_date: string | null;
  principal_address: string | null;
  mailing_address: string | null;
  jurisdiction: string | null;
  source_record_url: string | null;
  status_raw: string | null;
  status_normalized: string;
}

export interface RegisteredAgent {
  agent_name: string | null;
  agent_address: string | null;
}

export interface Officer {
  name: string;
  title: string | null;
  screened_ofac: boolean | null;
}

export interface ScoreComponent {
  component: string;
  value: number;
  weight: number;
  explanation: string | null;
}

export interface Run {
  id: string;
  status: string;
  verification_status: VerificationStatus | null;
  company_id: string | null;
  match_confidence: number | null;
  risk_score: number | null;
  score_version: string | null;
  started_at: string;
  finished_at: string | null;
}

export const TERMINAL_RUN_STATUSES = ["completed", "failed", "source_unavailable"];

export interface Evidence {
  id: string;
  type: string;
  sha256: string;
  source_url: string | null;
  captured_at: string;
}

export interface UccSearch {
  id: string;
  company_id: string;
  state: string;
  search_name: string;
  status: "pending" | "completed";
  outcome:
    | "filings_found"
    | "no_matching_filings"
    | "possible_match"
    | "source_unavailable"
    | null;
  source_url: string | null;
  notes: string | null;
  requested_by_email: string;
  completed_by_email: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface Profile {
  company: CompanySummary;
  registrations: Registration[];
  agents: RegisteredAgent[];
  officers: Officer[];
  latest_run: Run | null;
  scores: ScoreComponent[];
  evidence: Evidence[];
  ucc_searches: UccSearch[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const user = getUser();
  const requestInit = {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Email": user.email,
      "X-User-Role": user.role,
      ...(init.headers ?? {}),
    },
  };
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, requestInit);
  } catch {
    await new Promise((resolve) => window.setTimeout(resolve, 300));
    try {
      resp = await fetch(`${API_BASE}${path}`, requestInit);
    } catch {
      throw new ApiError(0, `Cannot reach the Porter API at ${API_BASE}.`);
    }
  }
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* keep generic message */
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export const api = {
  verify: (name: string, state: string | null) =>
    request<VerifyResponse>("/verify", {
      method: "POST",
      body: JSON.stringify({ name, state: state || null }),
    }),
  search: (q: string, state: string | null) => {
    const params = new URLSearchParams({ q });
    if (state) params.set("state", state);
    return request<{ results: CompanySummary[] }>(`/companies?${params.toString()}`);
  },
  recentBusinesses: (filters: RecentBusinessFilters) => {
    const params = new URLSearchParams({
      states: filters.states.join(","),
      formed_from: filters.formed_from,
      formed_to: filters.formed_to,
    });
    return request<{ results: RecentBusiness[]; filters: RecentBusinessFilters }>(
      `/recent-businesses?${params.toString()}`,
    );
  },
  recentBusiness: (state: string, entityId: string) =>
    request<RecentBusiness>(
      `/recent-businesses/${encodeURIComponent(state)}/${encodeURIComponent(entityId)}`,
    ),
  getRun: (runId: string) =>
    request<{ run: Run; scores: ScoreComponent[]; evidence: Evidence[] }>(`/runs/${runId}`),
  profile: (companyId: string) => request<Profile>(`/companies/${companyId}/profile`),
  review: (runId: string, decision: string, reason: string) =>
    request<{ id: string; run_id: string; decision: string }>(`/review/${runId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, reason: reason || null }),
    }),
  createUccSearch: (companyId: string, state: string) =>
    request<UccSearch>(`/companies/${companyId}/ucc-searches`, {
      method: "POST",
      body: JSON.stringify({ state }),
    }),
  completeUccSearch: (searchId: string, outcome: string, sourceUrl: string, notes: string) =>
    request<UccSearch>(`/ucc-searches/${searchId}/complete`, {
      method: "POST",
      body: JSON.stringify({ outcome, source_url: sourceUrl, notes: notes || null }),
    }),
};
