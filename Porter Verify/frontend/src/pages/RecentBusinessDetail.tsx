import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type RecentBusiness } from "../api";

export function RecentBusinessDetail() {
  const { state, entityId } = useParams<{ state: string; entityId: string }>();
  const [business, setBusiness] = useState<RecentBusiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!state || !entityId) return;
    api.recentBusiness(state, entityId)
      .then(setBusiness)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to load business record."),
      );
  }, [state, entityId]);

  if (error) return <div className="error">{error}</div>;
  if (!business) return <div className="panel">Loading business record…</div>;

  return (
    <>
      <div className="panel">
        <Link to="/recent">← Back to recent businesses</Link>
        <h1>{business.legal_name}</h1>
        <p className="muted">Official state registration record</p>
      </div>
      <div className="panel">
        <table>
          <tbody>
            <tr><th>State</th><td>{business.state}</td></tr>
            <tr><th>Entity ID</th><td>{business.entity_id}</td></tr>
            <tr><th>Entity type</th><td>{business.entity_type ?? "—"}</td></tr>
            <tr>
              <th>Registration / formation date</th>
              <td>{business.registration_or_formation_date}</td>
            </tr>
            <tr><th>Date basis</th><td>{business.date_basis}</td></tr>
            <tr><th>Status</th><td>{business.status_raw ?? "—"}</td></tr>
            <tr><th>Jurisdiction</th><td>{business.jurisdiction ?? "—"}</td></tr>
            <tr>
              <th>Principal / business address</th>
              <td>{business.principal_address ?? "—"}</td>
            </tr>
            <tr><th>Domestic signal</th><td>{business.domestic_signal ? "Yes" : "No"}</td></tr>
            <tr><th>Active signal</th><td>{business.active_signal ? "Yes" : "No"}</td></tr>
            <tr>
              <th>Relevant entity signal</th>
              <td>{business.relevant_entity_signal ? "Yes" : "No"}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="panel">
        <h2>Official evidence</h2>
        <p className="muted">
          The external source is raw state data and may appear as JSON.
        </p>
        <a href={business.source_record_url} target="_blank" rel="noreferrer">
          Open raw official source data
        </a>
      </div>
    </>
  );
}
