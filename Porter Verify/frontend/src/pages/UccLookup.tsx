import { useEffect, useState } from "react";
import { api, ApiError, type UccCoverageState, type UccLookupResponse } from "../api";
import { getUser } from "../auth";

const STATUS_LABELS: Record<UccCoverageState["status"], string> = {
  bulk_loaded: "Bulk data loaded",
  targeted_public_search: "Live public search available",
  manual_required: "Manual search required",
  blocked: "Automated access blocked",
  not_started: "Not started",
};

export function UccLookup() {
  const [company, setCompany] = useState("");
  const [state, setState] = useState("");
  const [coverage, setCoverage] = useState<UccCoverageState[]>([]);
  const [loading, setLoading] = useState(false);
  const [publicSearchLoading, setPublicSearchLoading] = useState(false);
  const [manualSearchLoading, setManualSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [result, setResult] = useState<UccLookupResponse | null>(null);
  const normalizedState = state.trim().toUpperCase();
  const user = getUser();
  const selectedCoverage = coverage.find((item) => item.state === normalizedState);
  const canRunPublicSearch = selectedCoverage?.status === "targeted_public_search";
  const canCreateManualSearch = ["underwriter", "ops", "admin"].includes(user.role);
  const needsManualSearch =
    Boolean(normalizedState) &&
    (!selectedCoverage ||
      ["blocked", "manual_required", "not_started"].includes(selectedCoverage.status));

  useEffect(() => {
    let active = true;
    api
      .uccCoverage()
      .then((data) => {
        if (active) setCoverage(data.states);
      })
      .catch(() => {
        if (active) setCoverage([]);
      });
    return () => {
      active = false;
    };
  }, []);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!company.trim()) return;
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      setResult(await api.uccLookup(company.trim(), normalizedState || null));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "UCC lookup failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onPublicSearch() {
    if (!company.trim() || !normalizedState) return;
    setPublicSearchLoading(true);
    setError(null);
    setNotice(null);
    try {
      const data = await api.uccPublicSearch(company.trim(), normalizedState);
      setResult(data.lookup);
      setNotice(data.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Public UCC source search failed.");
    } finally {
      setPublicSearchLoading(false);
    }
  }

  async function onManualSearch() {
    if (!company.trim() || !normalizedState) return;
    setManualSearchLoading(true);
    setError(null);
    setNotice(null);
    try {
      const order = await api.createManualUccSearch({
        company: company.trim(),
        state: normalizedState,
        notes: selectedCoverage?.notes ?? "State is not covered by automated UCC search.",
      });
      setNotice(`Manual UCC search created for ${order.search_name} / ${order.state}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Manual UCC search request failed.");
    } finally {
      setManualSearchLoading(false);
    }
  }

  return (
    <>
      <div className="panel">
        <h2>UCC lookup</h2>
        <p className="muted">
          Searches loaded UCC filings by debtor name. Public-search states may show summary-only
          fields when full secured-party detail is not free.
        </p>
        <form className="row" onSubmit={onSearch}>
          <div style={{ flex: 2 }}>
            <label htmlFor="ucc-company">Company name</label>
            <input
              id="ucc-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. WALMART"
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label htmlFor="ucc-state">State</label>
            <input
              id="ucc-state"
              value={state}
              onChange={(e) => setState(e.target.value.toUpperCase())}
              placeholder="NJ"
              maxLength={2}
              style={{ width: "70px" }}
            />
          </div>
          <button type="submit" disabled={loading || !company.trim()}>
            {loading ? "Searching..." : "Search UCC"}
          </button>
          <button
            type="button"
            disabled={publicSearchLoading || !company.trim() || !canRunPublicSearch}
            onClick={onPublicSearch}
            title={
              canRunPublicSearch
                ? "Search the live public state source and import matching results."
                : "Live public-source search currently supports ID and NJ."
            }
          >
            {publicSearchLoading ? "Searching source..." : "Search public source"}
          </button>
          {needsManualSearch && canCreateManualSearch && (
            <button
              type="button"
              disabled={manualSearchLoading || !company.trim()}
              onClick={onManualSearch}
            >
              {manualSearchLoading ? "Creating request..." : "Create manual UCC request"}
            </button>
          )}
        </form>
        <p className="muted">
          Check coverage before interpreting empty results. A state with no loaded or searchable
          source is not evidence that no UCC exists.
        </p>
        {normalizedState && (
          <CoverageNotice coverage={selectedCoverage} state={normalizedState} />
        )}
      </div>

      {notice && <div className="panel">{notice}</div>}
      {error && <div className="error">{error}</div>}

      {result && (
        <>
          <div className="panel">
            <h2>Summary</h2>
            <div className="kpis">
              <Metric label="Active UCC" value={result.has_active_ucc ? "Yes" : "No"} />
              <Metric label="Exit signal" value={result.ucc_exit_signal ? "Yes" : "No"} />
              <Metric label="Signal strength" value={result.signal_strength} />
              <Metric
                label="Days since exit"
                value={result.days_since_exit == null ? "-" : String(result.days_since_exit)}
              />
            </div>
            {result.previous_factor && (
              <p className="muted">Previous factor/lender: {result.previous_factor}</p>
            )}
          </div>

          <div className="panel">
            <h2>Active filings</h2>
            {result.active_filings.length === 0 ? (
              <p className="empty">No active filings found for this search.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Filed</th>
                    <th>Secured party</th>
                    <th>Lender type</th>
                    <th>Collateral / source note</th>
                    <th>Provenance</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {result.active_filings.map((filing, index) => (
                    <tr key={`${filing.secured_party ?? "unknown"}-${index}`}>
                      <td>{filing.filing_date ?? "-"}</td>
                      <td>{filing.secured_party ?? "Not shown by source"}</td>
                      <td>{filing.lender_type}</td>
                      <td>{filing.collateral ?? "-"}</td>
                      <td>{filing.acquisition_method ?? "BULK_OR_API"}</td>
                      <td>{filing.match_confidence == null ? "-" : `${filing.match_confidence}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="panel">
            <h2>Terminated filings</h2>
            {result.terminated_filings.length === 0 ? (
              <p className="empty">No terminated filings found for this search.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Filed</th>
                    <th>Terminated</th>
                    <th>Secured party</th>
                    <th>Lender type</th>
                    <th>Days since exit</th>
                    <th>Provenance</th>
                  </tr>
                </thead>
                <tbody>
                  {result.terminated_filings.map((filing, index) => (
                    <tr key={`${filing.secured_party ?? "unknown"}-${index}`}>
                      <td>{filing.filing_date ?? "-"}</td>
                      <td>{filing.termination_date ?? "-"}</td>
                      <td>{filing.secured_party ?? "Not shown by source"}</td>
                      <td>{filing.lender_type}</td>
                      <td>{filing.days_since_exit ?? "-"}</td>
                      <td>{filing.acquisition_method ?? "BULK_OR_API"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}

function CoverageNotice({
  coverage,
  state,
}: {
  coverage: UccCoverageState | undefined;
  state: string;
}) {
  if (!coverage) {
    return (
      <div className="notice">
        <strong>{state}: Not covered yet.</strong>
        <p className="muted">
          This state is not in the current UCC coverage map. Treat results as incomplete and use a
          manual search or approved source.
        </p>
      </div>
    );
  }

  return (
    <div className="notice">
      <strong>
        {coverage.state}: {STATUS_LABELS[coverage.status]}
      </strong>
      <p className="muted">
        {coverage.record_count.toLocaleString()} record(s)
        {coverage.last_refresh ? `, refreshed ${new Date(coverage.last_refresh).toLocaleString()}` : ""}
        . {coverage.notes}
      </p>
      <a href={coverage.source_url} target="_blank" rel="noreferrer">
        View source
      </a>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <span className="l">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
