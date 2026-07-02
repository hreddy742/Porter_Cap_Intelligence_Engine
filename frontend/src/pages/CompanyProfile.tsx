import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError, type Profile, type UccSearch } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { getUser } from "../auth";

// Company profile: the verified truth in one place — identity, score panel,
// evidence timeline, and (for underwriters) a review decision panel.
export function CompanyProfile() {
  const { companyId } = useParams<{ companyId: string }>();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    try {
      setProfile(await api.profile(companyId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  if (loading) return <div className="panel">Loading…</div>;
  if (error) return <div className="error">{error}</div>;
  if (!profile) return <div className="empty">No profile.</div>;

  const { company, registrations, agents, officers, latest_run, scores, evidence, ucc_searches } = profile;
  const canReview = ["underwriter", "admin"].includes(getUser().role);

  return (
    <>
      <div className="panel">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <h2 style={{ marginBottom: "0.25rem" }}>{company.canonical_legal_name}</h2>
            <span className="muted">
              {company.home_state ?? "—"} · registration: {company.status_normalized}
            </span>
          </div>
          <StatusBadge status={company.verification_status} />
        </div>
      </div>

      <div className="panel">
        <h2>Registrations</h2>
        {registrations.length === 0 ? (
          <p className="empty">No registration records.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>State</th>
                <th>Entity ID</th>
                <th>Type</th>
                <th>Formed</th>
                <th>Address</th>
                <th>Mailing</th>
                <th>Jurisdiction</th>
                <th>Source</th>
                <th>Raw status</th>
                <th>Normalized</th>
              </tr>
            </thead>
            <tbody>
              {registrations.map((r) => (
                <tr key={`${r.state}-${r.state_entity_id}`}>
                  <td>{r.state}</td>
                  <td>{r.state_entity_id}</td>
                  <td>{r.entity_type ?? "—"}</td>
                  <td>{r.formation_date ?? "—"}</td>
                  <td>{r.principal_address ?? "—"}</td>
                  <td>{r.mailing_address ?? "—"}</td>
                  <td>{r.jurisdiction ?? "—"}</td>
                  <td>
                    {r.source_record_url ? (
                      <a href={r.source_record_url} target="_blank" rel="noreferrer">record</a>
                    ) : "—"}
                  </td>
                  <td>{r.status_raw ?? "—"}</td>
                  <td>{r.status_normalized}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Registered agent</h2>
        {agents.length === 0 ? (
          <p className="empty">No registered agent on record.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Address</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a, i) => (
                <tr key={i}>
                  <td>{a.agent_name ?? "—"}</td>
                  <td>{a.agent_address ?? "— (restricted)"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Confidence score</h2>
        {scores.length === 0 ? (
          <p className="empty">No score components yet.</p>
        ) : (
          <table>
            <tbody>
              {scores.map((s) => (
                <tr key={s.component}>
                  <td style={{ width: "30%" }}>{s.component.replace(/_/g, " ")}</td>
                  <td style={{ width: "30%" }}>
                    <div className="bar">
                      <span style={{ width: `${Math.round(s.value * 100)}%` }} />
                    </div>
                  </td>
                  <td className="muted">{s.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Officers</h2>
        {officers.length === 0 ? (
          <p className="empty">
            No officers shown (either none published, or restricted for your role).
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Title</th>
                <th>OFAC screened</th>
              </tr>
            </thead>
            <tbody>
              {officers.map((o) => (
                <tr key={o.name}>
                  <td>{o.name}</td>
                  <td>{o.title ?? "—"}</td>
                  <td>{o.screened_ofac == null ? "—" : o.screened_ofac ? "HIT" : "clear"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Evidence timeline</h2>
        {evidence.length === 0 ? (
          <p className="empty">No evidence captured yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Captured</th>
                <th>Type</th>
                <th>SHA-256</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.captured_at).toLocaleString()}</td>
                  <td>{e.type}</td>
                  <td title={e.sha256} className="muted">
                    {e.sha256.slice(0, 12)}…
                  </td>
                  <td>
                    {e.source_url ? (
                      <a href={e.source_url} target="_blank" rel="noreferrer">
                        link
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!["sales", "ops"].includes(getUser().role) && (
        <UccSearchPanel
          companyId={company.id}
          homeState={company.home_state}
          searches={ucc_searches}
          canManage={canReview}
          onDone={load}
        />
      )}

      {canReview && latest_run && <ReviewPanel runId={latest_run.id} />}
    </>
  );
}

function UccSearchPanel({
  companyId,
  homeState,
  searches,
  canManage,
  onDone,
}: {
  companyId: string;
  homeState: string | null;
  searches: UccSearch[];
  canManage: boolean;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createSearch() {
    if (!homeState) return;
    setBusy(true);
    setError(null);
    try {
      await api.createUccSearch(companyId, homeState);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create UCC search.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h2>UCC search coverage</h2>
          <p className="muted">Exact-name state searches. An outcome is not a legal conclusion.</p>
        </div>
        {canManage && (
          <button type="button" disabled={busy || !homeState} onClick={createSearch}>
            {busy ? "Creating…" : `Create ${homeState ?? "state"} search`}
          </button>
        )}
      </div>
      {error && <div className="error">{error}</div>}
      {searches.length === 0 ? (
        <p className="empty">No UCC search coverage recorded.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>State</th>
              <th>Exact name</th>
              <th>Status</th>
              <th>Outcome</th>
              <th>Source</th>
              <th>Requested</th>
              {canManage && <th>Action</th>}
            </tr>
          </thead>
          <tbody>
            {searches.map((search) => (
              <tr key={search.id}>
                <td>{search.state}</td>
                <td>{search.search_name}</td>
                <td>{search.status}</td>
                <td>{search.outcome?.replace(/_/g, " ") ?? "—"}</td>
                <td>
                  {search.source_url ? (
                    <a href={search.source_url} target="_blank" rel="noreferrer">source</a>
                  ) : "—"}
                </td>
                <td>{new Date(search.created_at).toLocaleString()}</td>
                {canManage && (
                  <td>
                    {search.status === "pending" ? (
                      <UccCompletionForm searchId={search.id} onDone={onDone} />
                    ) : "Recorded"}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function UccCompletionForm({ searchId, onDone }: { searchId: string; onDone: () => void }) {
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
      setError(err instanceof ApiError ? err.message : "Failed to complete UCC search.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {error && <div className="error">{error}</div>}
      <select aria-label="UCC search outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
        <option value="no_matching_filings">No matching filings</option>
        <option value="filings_found">Filings found</option>
        <option value="possible_match">Possible match</option>
        <option value="source_unavailable">Source unavailable</option>
      </select>
      <input
        aria-label="Official source URL"
        type="url"
        required
        value={sourceUrl}
        onChange={(e) => setSourceUrl(e.target.value)}
        placeholder="Official source URL"
      />
      <input
        aria-label="UCC search notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (optional)"
      />
      <button type="submit" disabled={busy}>{busy ? "Saving…" : "Record outcome"}</button>
    </form>
  );
}

function ReviewPanel({ runId }: { runId: string }) {
  const [decision, setDecision] = useState("approved");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.review(runId, decision, reason.trim());
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record decision.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>Review decision</h2>
      {done && <p className="muted">Decision recorded.</p>}
      {error && <div className="error">{error}</div>}
      <form className="row" onSubmit={submit}>
        <div>
          <label htmlFor="decision">Decision</label>
          <select id="decision" value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="needs_more_info">Needs more info</option>
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label htmlFor="reason">Reason</label>
          <input
            id="reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Rationale (recorded in the audit trail)"
            style={{ width: "100%" }}
          />
        </div>
        <button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Record decision"}
        </button>
      </form>
    </div>
  );
}
