import type { VerificationStatus } from "../api";

// Human-readable labels. Deliberately NOT "sales-ready" — labels reflect only what
// the evidence supports (plan §13).
const LABELS: Record<VerificationStatus, string> = {
  verified: "Verified",
  likely_match: "Likely match",
  needs_review: "Needs review",
  insufficient_evidence: "Insufficient evidence",
  inactive_not_eligible: "Inactive / not eligible",
  risk_flag: "Risk flag",
};

export function StatusBadge({ status }: { status: VerificationStatus | null }) {
  if (!status) return <span className="badge insufficient_evidence">Not verified</span>;
  return <span className={`badge ${status}`}>{LABELS[status]}</span>;
}
