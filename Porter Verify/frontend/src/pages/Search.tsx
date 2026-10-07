import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, type CompanySummary } from "../api";
import { StatusBadge } from "../components/StatusBadge";

// Search across already-verified companies. Empty/error/loading states handled.
export function Search() {
  const [q, setQ] = useState("");
  const [state, setState] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<CompanySummary[] | null>(null);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(q.trim(), state.trim() || null);
      setResults(data.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="panel">
        <h2>Company search</h2>
        <form className="row" onSubmit={onSearch}>
          <div style={{ flex: 2 }}>
            <label htmlFor="q">Name contains</label>
            <input
              id="q"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. Acme"
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label htmlFor="st">State</label>
            <input
              id="st"
              value={state}
              onChange={(e) => setState(e.target.value.toUpperCase())}
              placeholder="TX"
              maxLength={2}
              style={{ width: "70px" }}
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}

      {results && (
        <div className="panel">
          {results.length === 0 ? (
            <p className="empty">
              No matches found. Run a live verification from the Home page to add a company.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Legal name</th>
                  <th>State</th>
                  <th>Registration</th>
                  <th>Verification</th>
                </tr>
              </thead>
              <tbody>
                {results.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <Link to={`/company/${c.id}`}>{c.canonical_legal_name}</Link>
                    </td>
                    <td>{c.home_state ?? "—"}</td>
                    <td>{c.status_normalized}</td>
                    <td>
                      <StatusBadge status={c.verification_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </>
  );
}
