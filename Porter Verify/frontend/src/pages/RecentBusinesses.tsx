import { useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  ApiError,
  type RecentBusiness,
  type RecentBusinessFilters,
  type RecentBusinessPagination,
} from "../api";

const STATES = ["CO", "CT", "OR", "OH"];

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function initialFilters(): RecentBusinessFilters {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 30);
  return {
    states: [...STATES],
    formed_from: isoDate(start),
    formed_to: isoDate(end),
    q: "",
    sort_by: "formation_date",
    sort_order: "desc",
    page: 1,
    page_size: 50,
  };
}

export function RecentBusinesses() {
  const [filters, setFilters] = useState<RecentBusinessFilters>(initialFilters);
  const [results, setResults] = useState<RecentBusiness[]>([]);
  const [pagination, setPagination] = useState<RecentBusinessPagination | null>(null);
  const [appliedFilters, setAppliedFilters] = useState<RecentBusinessFilters | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(requestFilters: RecentBusinessFilters) {
    setLoading(true);
    setError(null);
    try {
      const response = await api.recentBusinesses(requestFilters);
      setResults(response.results);
      setPagination(response.pagination);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Cannot reach the Porter API. Check the network connection and try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleState(state: string) {
    setFilters((current) => ({
      ...current,
      states: current.states.includes(state)
        ? current.states.filter((item) => item !== state)
        : [...current.states, state],
    }));
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!filters.formed_from || !filters.formed_to) {
      setError("Choose both the start and end dates.");
      return;
    }
    if (filters.formed_from > filters.formed_to) {
      setError("The start date must be on or before the end date.");
      return;
    }
    const requestFilters = { ...filters, page: 1 };
    setFilters(requestFilters);
    setAppliedFilters(requestFilters);
    setHasSearched(true);
    void load(requestFilters);
  }

  function goToPage(page: number) {
    if (!appliedFilters) return;
    const requestFilters = { ...appliedFilters, page };
    setAppliedFilters(requestFilters);
    void load(requestFilters);
  }

  return (
    <>
      <div className="panel">
        <h1>Recently registered businesses</h1>
        <p className="muted">
          State registration leads from official datasets. Dates and addresses retain their
          source-defined meaning.
        </p>
        <form onSubmit={submit}>
          <div>
            <label htmlFor="business-query">Company name or entity ID</label>
            <input
              id="business-query"
              type="search"
              maxLength={200}
              placeholder="Example: Alpha Freight or 20261732113"
              value={filters.q}
              onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            />
          </div>
          <div className="row">
            <div>
              <label htmlFor="formed-from">Formed from</label>
              <input
                id="formed-from"
                type="date"
                required
                value={filters.formed_from}
                onChange={(event) =>
                  setFilters({ ...filters, formed_from: event.target.value })
                }
              />
            </div>
            <div>
              <label htmlFor="formed-to">Formed to</label>
              <input
                id="formed-to"
                type="date"
                required
                value={filters.formed_to}
                onChange={(event) => setFilters({ ...filters, formed_to: event.target.value })}
              />
            </div>
          </div>

          <div className="row" style={{ marginTop: "1rem" }}>
            <div>
              <label htmlFor="result-sort">Sort results</label>
              <select
                id="result-sort"
                value={`${filters.sort_by}:${filters.sort_order}`}
                onChange={(event) => {
                  const [sort_by, sort_order] = event.target.value.split(":") as [
                    RecentBusinessFilters["sort_by"],
                    RecentBusinessFilters["sort_order"],
                  ];
                  setFilters({ ...filters, sort_by, sort_order });
                }}
              >
                <option value="formation_date:desc">Newest first</option>
                <option value="formation_date:asc">Oldest first</option>
                <option value="legal_name:asc">Company name A-Z</option>
                <option value="legal_name:desc">Company name Z-A</option>
                <option value="entity_id:asc">Entity ID A-Z</option>
                <option value="entity_id:desc">Entity ID Z-A</option>
              </select>
            </div>
            <div>
              <label htmlFor="page-size">Results per page</label>
              <select
                id="page-size"
                value={filters.page_size}
                onChange={(event) =>
                  setFilters({ ...filters, page_size: Number(event.target.value) })
                }
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          <div className="row" style={{ marginTop: "1rem" }}>
            {STATES.map((state) => (
              <label key={state}>
                <input
                  type="checkbox"
                  checked={filters.states.includes(state)}
                  onChange={() => toggleState(state)}
                />{" "}
                {state}
              </label>
            ))}
          </div>

          <div className="row" style={{ marginTop: "1rem" }}>
            <button type="submit" disabled={loading || filters.states.length === 0}>
              {loading ? "Loading…" : "Apply filters"}
            </button>
          </div>
        </form>
        {error && <div className="error">{error}</div>}
      </div>

      <div className="panel">
        <h2>
          Results{pagination ? ` (${pagination.total.toLocaleString()} matching businesses)` : ""}
        </h2>
        {!hasSearched ? (
          <p className="empty">Choose filters and press Apply filters to search.</p>
        ) : loading ? (
          <p className="empty">Searching recent businesses…</p>
        ) : results.length === 0 ? (
          <p className="empty">No businesses matched these filters.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Registration / formation</th>
                <th>Date basis</th>
                <th>State</th>
                <th>Entity ID</th>
                <th>Legal name</th>
                <th>Entity type</th>
                <th>Status</th>
                <th>Jurisdiction</th>
                <th>Principal / business address</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {results.map((business) => (
                <tr key={`${business.state}-${business.entity_id}`}>
                  <td>{business.registration_or_formation_date}</td>
                  <td>{business.date_basis}</td>
                  <td>{business.state}</td>
                  <td>{business.entity_id}</td>
                  <td>{business.legal_name}</td>
                  <td>{business.entity_type ?? "—"}</td>
                  <td>{business.status_raw ?? "—"}</td>
                  <td>{business.jurisdiction ?? "—"}</td>
                  <td>{business.principal_address ?? "—"}</td>
                  <td>
                    <Link to={`/recent/${business.state}/${encodeURIComponent(business.entity_id)}`}>
                      view details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {hasSearched && !loading && pagination && pagination.total_pages > 0 && (
          <div className="row" style={{ marginTop: "1rem", alignItems: "center" }}>
            <button
              type="button"
              disabled={pagination.page <= 1}
              onClick={() => goToPage(pagination.page - 1)}
            >
              Previous
            </button>
            <span>
              Page {pagination.page} of {pagination.total_pages}
            </span>
            <button
              type="button"
              disabled={pagination.page >= pagination.total_pages}
              onClick={() => goToPage(pagination.page + 1)}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </>
  );
}
