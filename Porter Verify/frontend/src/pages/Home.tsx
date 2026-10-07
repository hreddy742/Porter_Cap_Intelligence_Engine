import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, TERMINAL_RUN_STATUSES, type Run } from "../api";
import { StatusBadge } from "../components/StatusBadge";

// Home: start an async verification, poll the run until it finishes, then show the
// result and a link to the company profile. Mirrors the backend's async (poll) flow.
export function Home() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [state, setState] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Run | null>(null);

  async function pollRun(runId: string): Promise<Run> {
    // Poll up to ~60s (live lookups can be slow); the backend run is the source of truth.
    for (let attempt = 0; attempt < 60; attempt++) {
      const { run } = await api.getRun(runId);
      if (TERMINAL_RUN_STATUSES.includes(run.status)) return run;
      await new Promise((r) => setTimeout(r, 1000));
    }
    throw new Error("Verification is taking longer than expected. Check back shortly.");
  }

  async function onVerify(e: React.FormEvent) {
    e.preventDefault();
    setStatus("running");
    setError(null);
    setResult(null);
    try {
      const started = await api.verify(name.trim(), state.trim() || null);
      setResult(await pollRun(started.run_id));
      setStatus("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setStatus("error");
    }
  }

  const running = status === "running";

  return (
    <>
      <div className="panel">
        <h2>Verify a business</h2>
        <p className="muted">
          Search a business by legal name and state. The system fetches the registration
          record, screens it, and produces an evidence-backed status for internal review.
        </p>
        <form className="row" onSubmit={onVerify}>
          <div style={{ flex: 2 }}>
            <label htmlFor="name">Business name</label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Rock Ridge Condominiums, Inc. (CO) or Acme Logistics LLC (TX)"
              required
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label htmlFor="state">State</label>
            <input
              id="state"
              value={state}
              onChange={(e) => setState(e.target.value.toUpperCase())}
              placeholder="CO"
              maxLength={2}
              style={{ width: "70px" }}
            />
          </div>
          <button type="submit" disabled={running || !name.trim()}>
            {running ? "Verifying…" : "Run verification"}
          </button>
        </form>
        {running && <p className="muted">Verification running — polling for the result…</p>}
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="panel">
          <h2>Result</h2>
          <p>
            <StatusBadge status={result.verification_status} />{" "}
            <span className="muted">run {result.status}</span>
          </p>
          {result.match_confidence != null && (
            <p className="muted">Match confidence: {result.match_confidence.toFixed(2)}</p>
          )}
          {result.company_id ? (
            <button onClick={() => navigate(`/company/${result.company_id}`)}>
              Open company profile
            </button>
          ) : (
            <p className="empty">No company record was created for this result.</p>
          )}
        </div>
      )}
    </>
  );
}
