import { useEffect, useState } from "react";
import { api, ApiError, type UccCoverageState } from "../api";

const LABELS: Record<UccCoverageState["status"], string> = {
  bulk_loaded: "Bulk loaded",
  targeted_public_search: "Targeted public search",
  manual_required: "Manual required",
  blocked: "Blocked",
  not_started: "Not started",
};

export function UccCoverage() {
  const [states, setStates] = useState<UccCoverageState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .uccCoverage()
      .then((data) => {
        if (active) setStates(data.states);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.message : "Could not load UCC coverage.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <div className="panel">
        <h2>UCC coverage</h2>
        <p className="muted">
          Current state-by-state UCC source status. This separates loaded bulk data from targeted
          public search and blocked/manual states.
        </p>
      </div>

      {loading && <div className="panel">Loading coverage...</div>}
      {error && <div className="error">{error}</div>}

      {!loading && !error && (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>State</th>
                <th>Status</th>
                <th>Records</th>
                <th>Last refresh</th>
                <th>Source</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {states.map((item) => (
                <tr key={item.state}>
                  <td>{item.state}</td>
                  <td>{LABELS[item.status]}</td>
                  <td>{item.record_count.toLocaleString()}</td>
                  <td>{item.last_refresh ? new Date(item.last_refresh).toLocaleString() : "-"}</td>
                  <td>
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      Source
                    </a>
                  </td>
                  <td>{item.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
