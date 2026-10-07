// Typed API client for the Porter Verify backend.
//
// One small fetch wrapper attaches the auth headers and surfaces clean errors.
// Types mirror the backend Pydantic schemas (kept deliberately in sync).

import { getUser, type CurrentUser } from "./auth";

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

export interface RegistryVerifyResponse {
  verified: boolean;
  confidence: number;
  status: string | null;
  entity_type: string | null;
  formation_date: string | null;
  address: string | null;
  officers: string[];
  source_url: string | null;
  ofac_clear: boolean;
}

export interface OfacMatch {
  match_name: string;
  match_type: "exact" | "partial" | "alias";
  score: number;
  program: string | null;
}

export interface OfacResponse {
  company: string;
  clear: boolean;
  match: OfacMatch | null;
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
  q: string;
  sort_by: "formation_date" | "legal_name" | "entity_id" | "state";
  sort_order: "asc" | "desc";
  page: number;
  page_size: number;
}

export interface RecentBusinessPagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
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

export interface UccActiveFiling {
  secured_party: string | null;
  filing_date: string | null;
  collateral: string | null;
  lender_type: string;
  is_factoring: boolean;
  is_mca: boolean;
  status: string | null;
  acquisition_method: string | null;
  match_confidence: number | null;
}

export interface UccTerminatedFiling {
  secured_party: string | null;
  filing_date: string | null;
  termination_date: string | null;
  lender_type: string;
  days_since_exit: number | null;
  acquisition_method: string | null;
  match_confidence: number | null;
}

export interface UccLookupResponse {
  has_active_ucc: boolean;
  active_filings: UccActiveFiling[];
  terminated_filings: UccTerminatedFiling[];
  ucc_exit_signal: boolean;
  days_since_exit: number | null;
  previous_factor: string | null;
  signal_strength: "HOT" | "WARM" | "NONE";
}

export interface UccPublicSearchResponse {
  state: string;
  company: string;
  supported: boolean;
  imported_count: number;
  message: string;
  lookup: UccLookupResponse;
}

export interface UccCoverageState {
  state: string;
  status:
    | "bulk_loaded"
    | "targeted_public_search"
    | "manual_required"
    | "blocked"
    | "not_started";
  record_count: number;
  last_refresh: string | null;
  source_url: string;
  notes: string;
}

export interface UccManualSearchRequest {
  company: string;
  state: string;
  notes: string | null;
}

export interface UccCoverageResponse {
  states: UccCoverageState[];
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
  const authHeader = user?.apiKey ? { Authorization: `Bearer ${user.apiKey}` } : {};
  const requestInit = {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
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
  registryVerify: (company: string, state: string) => {
    const params = new URLSearchParams({ company, state });
    return request<RegistryVerifyResponse>(`/verify?${params.toString()}`);
  },
  ofac: (company: string) => {
    const params = new URLSearchParams({ company });
    return request<OfacResponse>(`/ofac?${params.toString()}`);
  },
  search: (q: string, state: string | null) => {
    const params = new URLSearchParams({ q });
    if (state) params.set("state", state);
    return request<{ results: CompanySummary[] }>(`/companies?${params.toString()}`);
  },
  uccLookup: (company: string, state: string | null) => {
    const params = new URLSearchParams({ company });
    if (state) params.set("state", state);
    return request<UccLookupResponse>(`/ucc?${params.toString()}`);
  },
  uccPublicSearch: (company: string, state: string) =>
    request<UccPublicSearchResponse>("/ucc/public-search", {
      method: "POST",
      body: JSON.stringify({ company, state }),
    }),
  uccCoverage: () => request<UccCoverageResponse>("/ucc/coverage"),
  createManualUccSearch: (payload: UccManualSearchRequest) =>
    request<UccSearch>("/ucc/manual-searches", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  manualUccSearches: (status: "pending" | "completed" = "pending") =>
    request<UccSearch[]>(`/ucc/manual-searches?status=${status}`),
  recentBusinesses: (filters: RecentBusinessFilters) => {
    const params = new URLSearchParams({
      states: filters.states.join(","),
      formed_from: filters.formed_from,
      formed_to: filters.formed_to,
      q: filters.q,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
      page: String(filters.page),
      page_size: String(filters.page_size),
    });
    return request<{
      results: RecentBusiness[];
      filters: Omit<RecentBusinessFilters, "page" | "page_size">;
      pagination: RecentBusinessPagination;
    }>(
      `/recent-businesses?${params.toString()}`,
    );
  },
  recentBusiness: (state: string, entityId: string) =>
    request<RecentBusiness>(
      `/recent-businesses/${encodeURIComponent(state)}/${encodeURIComponent(entityId)}`,
    ),
  getRun: (runId: string) =>
    request<{ run: Run; scores: ScoreComponent[]; evidence: Evidence[] }>(`/runs/${runId}`),
  me: () => request<CurrentUser>("/auth/me"),
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
