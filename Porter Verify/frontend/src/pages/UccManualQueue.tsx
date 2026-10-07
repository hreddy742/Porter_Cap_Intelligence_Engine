import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, type UccSearch } from "../api";

export function UccManualQueue() {
  const [rows, setRows] = useState<UccSearch[]>([]);
  const [status, setStatus] = useState<"pending" | "completed">("pending");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(active = true) {
    setError(null);
    setLoading(true);
    api
      .manualUccSearches(status)
      .then((data) => {
        if (active) setRows(data);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.message : "Could not load manual UCC queue.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
  }

  useEffect(() => {
    let active = true;
    void load(active);
    return () => {
      active = false;
    };
  }, [status]);

  return (
    <>
      <div className="panel">
        <h2>Manual UCC queue</h2>
        <p className="muted">
          Review pending source-backed searches and completed manual UCC outcomes for blocked or
          uncovered states.
        </p>
        <div className="row">
          <button
            type="button"
            disabled={status === "pending"}
            onClick={() => setStatus("pending")}
          >
            Pending
          </button>
          <button
            type="button"
            disabled={status === "completed"}
            onClick={() => setStatus("completed")}
          >
            Completed
          </button>
        </div>
      </div>

      {loading && <div className="panel">Loading queue...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && (
        <div className="panel">
          {rows.length === 0 ? (
            <p className="empty">No {status} manual UCC searches.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Requested</th>
                  <th>Company</th>
                  <th>State</th>
                  <th>Requested by</th>
                  <th>Notes</th>
                  {status === "completed" && <th>Outcome</th>}
                  {status === "completed" && <th>Source</th>}
                  {status === "completed" && <th>Completed</th>}
                  <th>Action</th>
                  {status === "pending" && <th>Record outcome</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString()}</td>
                    <td>{row.search_name}</td>
                    <td>{row.state}</td>
                    <td>{row.requested_by_email}</td>
                    <td>{row.notes ?? "-"}</td>
                    {status === "completed" && (
                      <td>{row.outcome?.replace(/_/g, " ") ?? "-"}</td>
                    )}
                    {status === "completed" && (
                      <td>
                        {row.source_url ? (
                          <a href={row.source_url} target="_blank" rel="noreferrer">
                            source
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                    )}
                    {status === "completed" && (
                      <td>
                        {row.completed_at ? new Date(row.completed_at).toLocaleString() : "-"}
                        {row.completed_by_email ? ` by ${row.completed_by_email}` : ""}
                      </td>
                    )}
                    <td>
                      <Link to={`/company/${row.company_id}`}>Open profile</Link>
                    </td>
                    {status === "pending" && (
                      <td>
                        <QueueCompletionForm searchId={row.id} onDone={() => void load()} />
                      </td>
                    )}
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

function QueueCompletionForm({ searchId, onDone }: { searchId: string; onDone: () => void }) {
  const [outcome, setOutcome] = useState("no_matching_filings");
  const [sourceUrl, setSourceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.completeUccSearch(searchId, outcome, sourceUrl.trim(), notes.trim());
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record UCC outcome.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {error && <div className="error">{error}</div>}
      <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
        <option value="no_matching_filings">No matching filings</option>
        <option value="filings_found">Filings found</option>
        <option value="possible_match">Possible match</option>
        <option value="source_unavailable">Source unavailable</option>
      </select>
      <input
        type="url"
        required
        value={sourceUrl}
        onChange={(e) => setSourceUrl(e.target.value)}
        placeholder="Official source URL"
      />
      <input
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes"
      />
      <button type="submit" disabled={busy}>
        {busy ? "Saving..." : "Record"}
      </button>
    </form>
  );
}
