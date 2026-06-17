import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, type VerifyResponse } from "../api";
import { StatusBadge } from "../components/StatusBadge";

// Home: the entry point — run a verification and jump to the resulting profile.
export function Home() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [state, setState] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerifyResponse | null>(null);

  async function onVerify(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.verify(name.trim(), state.trim() || null));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

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
              placeholder="e.g. Acme Logistics LLC"
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
              placeholder="TX"
              maxLength={2}
              style={{ width: "70px" }}
            />
          </div>
          <button type="submit" disabled={loading || !name.trim()}>
            {loading ? "Verifying…" : "Run verification"}
          </button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="panel">
          <h2>Result</h2>
          <p>
            <StatusBadge status={result.verification_status} />{" "}
            <span className="muted">{result.message}</span>
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
