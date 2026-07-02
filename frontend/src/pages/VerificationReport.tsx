import { useMemo, useState } from "react";
import {
  api,
  ApiError,
  type OfacResponse,
  type RegistryVerifyResponse,
  type UccCoverageState,
  type UccLookupResponse,
} from "../api";
import { getUser } from "../auth";

type ReportState = {
  registry: RegistryVerifyResponse | null;
  ofac: OfacResponse | null;
  ucc: UccLookupResponse | null;
  coverage: UccCoverageState | null;
};

const COVERAGE_LABELS: Record<UccCoverageState["status"], string> = {
  bulk_loaded: "Automated bulk coverage",
  targeted_public_search: "Live public source available",
  manual_required: "Manual UCC search required",
  blocked: "Automated access blocked",
  not_started: "Not covered yet",
};

export function VerificationReport() {
  const [company, setCompany] = useState("");
  const [state, setState] = useState("");
  const [loading, setLoading] = useState(false);
  const [manualLoading, setManualLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [manualCreated, setManualCreated] = useState(false);
  const [report, setReport] = useState<ReportState | null>(null);
  const normalizedState = state.trim().toUpperCase();
  const user = getUser();
  const canCreateManualSearch = ["underwriter", "ops", "admin"].includes(user.role);

  const summary = useMemo(() => {
    if (!report) return null;
    const issues: string[] = [];
    if (!report.registry?.verified) issues.push("Business registry not verified");
    if (report.ofac && !report.ofac.clear) issues.push("OFAC match requires review");
    if (report.ucc?.has_active_ucc) issues.push("Active UCC filing found");
    if (report.ucc?.ucc_exit_signal) issues.push("Recent UCC exit signal found");
    if (!report.coverage || ["blocked", "manual_required", "not_started"].includes(report.coverage.status)) {
      issues.push("Manual UCC search required for this state");
    }
    if (issues.length === 0) return "Ready for underwriting review: no automated red flags found.";
    return `Review required: ${issues.join("; ")}.`;
  }, [report]);

  async function runReport(e: React.FormEvent) {
    e.preventDefault();
    if (!company.trim() || !normalizedState) return;
    setLoading(true);
    setError(null);
    setNotice(null);
    setWarnings([]);
    setManualCreated(false);
    setReport(null);
    try {
      const nextWarnings: string[] = [];
      let selectedCoverage: UccCoverageState | null = null;
      try {
        const coverageResponse = await api.uccCoverage();
        selectedCoverage =
          coverageResponse.states.find((item) => item.state === normalizedState) ?? null;
      } catch (err) {
        nextWarnings.push(messageFromError(err, "UCC coverage could not be loaded."));
      }

      const [registryResult, ofacResult, uccResult] = await Promise.allSettled([
        api.registryVerify(company.trim(), normalizedState),
        api.ofac(company.trim()),
        api.uccLookup(company.trim(), normalizedState),
      ]);
      if (registryResult.status === "rejected") {
        nextWarnings.push(messageFromError(registryResult.reason, "Business registry lookup failed."));
      }
      if (ofacResult.status === "rejected") {
        nextWarnings.push(messageFromError(ofacResult.reason, "OFAC screening failed."));
      }
      if (uccResult.status === "rejected") {
        nextWarnings.push(messageFromError(uccResult.reason, "UCC lookup failed."));
      }
      if (
        registryResult.status === "rejected" &&
        ofacResult.status === "rejected" &&
        uccResult.status === "rejected"
      ) {
        throw new Error("All report sources failed.");
      }
      setWarnings(nextWarnings);
      setReport({
        registry: registryResult.status === "fulfilled" ? registryResult.value : null,
        ofac: ofacResult.status === "fulfilled" ? ofacResult.value : null,
        ucc: uccResult.status === "fulfilled" ? uccResult.value : null,
        coverage: selectedCoverage,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification report failed.");
    } finally {
      setLoading(false);
    }
  }

  async function createManualSearch() {
    if (!company.trim() || !normalizedState) return;
    setManualLoading(true);
    setError(null);
    setNotice(null);
    try {
      const order = await api.createManualUccSearch({
        company: company.trim(),
        state: normalizedState,
        notes: report?.coverage?.notes ?? "Manual UCC search required from verification report.",
      });
      setNotice(`Manual UCC search created for ${order.search_name} / ${order.state}.`);
      setManualCreated(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Manual UCC search request failed.");
    } finally {
      setManualLoading(false);
    }
  }

  return (
    <>
      <div className="panel">
        <h2>Verification report</h2>
        <p className="muted">
          One reviewer view for business registry, OFAC, UCC coverage, and source-backed next steps.
        </p>
        <form className="row" onSubmit={runReport}>
          <div style={{ flex: 2 }}>
            <label htmlFor="report-company">Business name</label>
            <input
              id="report-company"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="e.g. WALMART"
              required
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label htmlFor="report-state">State</label>
            <input
              id="report-state"
              value={state}
              onChange={(event) => setState(event.target.value.toUpperCase())}
              placeholder="CO"
              maxLength={2}
              required
              style={{ width: "70px" }}
            />
          </div>
          <button type="submit" disabled={loading || !company.trim() || !normalizedState}>
            {loading ? "Building..." : "Build report"}
          </button>
        </form>
      </div>

      {notice && <div className="panel">{notice}</div>}
      {error && <div className="error">{error}</div>}
      {warnings.length > 0 && (
        <div className="notice">
          <strong>Partial report</strong>
          {warnings.map((warning) => (
            <p className="muted" key={warning}>
              {warning}
            </p>
          ))}
        </div>
      )}

      {report && (
        <>
          <div className="panel">
            <h2>Reviewer summary</h2>
            <p>{summary}</p>
            {report.coverage &&
              ["blocked", "manual_required", "not_started"].includes(report.coverage.status) &&
              canCreateManualSearch && (
                <button type="button" disabled={manualLoading || manualCreated} onClick={createManualSearch}>
                  {manualCreated
                    ? "Manual UCC request created"
                    : manualLoading
                      ? "Creating..."
                      : "Create manual UCC request"}
                </button>
              )}
          </div>

          <div className="kpis">
            <Metric label="Registry" value={report.registry?.verified ? "Verified" : "Not verified"} />
            <Metric label="OFAC" value={report.ofac?.clear ? "Clear" : "Review"} />
            <Metric label="Active UCC" value={report.ucc?.has_active_ucc ? "Found" : "None found"} />
            <Metric
              label="UCC coverage"
              value={report.coverage ? COVERAGE_LABELS[report.coverage.status] : "Not mapped"}
            />
          </div>

          <RegistryPanel registry={report.registry} />
          <OfacPanel ofac={report.ofac} />
          <UccPanel ucc={report.ucc} coverage={report.coverage} />
        </>
      )}
    </>
  );
}

function RegistryPanel({ registry }: { registry: RegistryVerifyResponse | null }) {
  return (
    <div className="panel">
      <h2>Business registry</h2>
      {!registry ? (
        <p className="empty">No registry result.</p>
      ) : (
        <table>
          <tbody>
            <Row label="Verified" value={registry.verified ? "Yes" : "No"} />
            <Row label="Confidence" value={`${Math.round(registry.confidence * 100)}%`} />
            <Row label="Status" value={registry.status ?? "-"} />
            <Row label="Entity type" value={registry.entity_type ?? "-"} />
            <Row label="Formation date" value={registry.formation_date ?? "-"} />
            <Row label="Address" value={registry.address ?? "-"} />
            <Row
              label="Officers"
              value={registry.officers.length > 0 ? registry.officers.join(", ") : "-"}
            />
            <tr>
              <td>Source</td>
              <td>
                {registry.source_url ? (
                  <a href={registry.source_url} target="_blank" rel="noreferrer">
                    Official record
                  </a>
                ) : (
                  "-"
                )}
              </td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}

function OfacPanel({ ofac }: { ofac: OfacResponse | null }) {
  return (
    <div className="panel">
      <h2>OFAC screening</h2>
      {!ofac ? (
        <p className="empty">No OFAC result.</p>
      ) : ofac.clear ? (
        <p>Clear. No OFAC match found for this company name.</p>
      ) : (
        <table>
          <tbody>
            <Row label="Result" value="Review required" />
            <Row label="Match name" value={ofac.match?.match_name ?? "-"} />
            <Row label="Match type" value={ofac.match?.match_type ?? "-"} />
            <Row
              label="Score"
              value={ofac.match ? `${Math.round(ofac.match.score * 100)}%` : "-"}
            />
            <Row label="Program" value={ofac.match?.program ?? "-"} />
          </tbody>
        </table>
      )}
    </div>
  );
}

function UccPanel({
  ucc,
  coverage,
}: {
  ucc: UccLookupResponse | null;
  coverage: UccCoverageState | null;
}) {
  return (
    <div className="panel">
      <h2>UCC review</h2>
      {coverage ? (
        <div className="notice">
          <strong>{COVERAGE_LABELS[coverage.status]}</strong>
          <p className="muted">
            {coverage.record_count.toLocaleString()} record(s). {coverage.notes}
          </p>
          <a href={coverage.source_url} target="_blank" rel="noreferrer">
            Source
          </a>
        </div>
      ) : (
        <div className="notice">
          <strong>State not mapped.</strong>
          <p className="muted">Treat UCC results as incomplete until a manual or approved source search is done.</p>
        </div>
      )}
      {!ucc ? (
        <p className="empty">No UCC lookup result.</p>
      ) : (
        <>
          <div className="kpis">
            <Metric label="Active filings" value={ucc.has_active_ucc ? "Yes" : "No"} />
            <Metric label="Exit signal" value={ucc.ucc_exit_signal ? "Yes" : "No"} />
            <Metric label="Signal" value={ucc.signal_strength} />
          </div>
          {ucc.active_filings.length === 0 ? (
            <p className="empty">No active filings found in currently connected sources.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Filed</th>
                  <th>Secured party</th>
                  <th>Lender type</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {ucc.active_filings.map((filing, index) => (
                  <tr key={`${filing.secured_party ?? "unknown"}-${index}`}>
                    <td>{filing.filing_date ?? "-"}</td>
                    <td>{filing.secured_party ?? "Not shown by source"}</td>
                    <td>{filing.lender_type}</td>
                    <td>{filing.match_confidence == null ? "-" : `${filing.match_confidence}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi">
      <span className="l">{label}</span>
      <div className="n">{value}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td style={{ width: "30%" }}>{label}</td>
      <td>{value}</td>
    </tr>
  );
}

function messageFromError(err: unknown, fallback: string) {
  return err instanceof ApiError || err instanceof Error ? err.message : fallback;
}
