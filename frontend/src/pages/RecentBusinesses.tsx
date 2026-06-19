import { useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  ApiError,
  type RecentBusiness,
  type RecentBusinessFilters,
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
  };
}

export function RecentBusinesses() {
  const [filters, setFilters] = useState<RecentBusinessFilters>(initialFilters);
  const [results, setResults] = useState<RecentBusiness[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.recentBusinesses(filters);
      setResults(response.results);
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
    setHasSearched(true);
    void load();
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
        <h2>Results</h2>
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
      </div>
    </>
  );
}
