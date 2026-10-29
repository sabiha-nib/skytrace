// Pure rules shared with the Python implementation. overallStatus mirrors hypotheses.overall (HYPO-1) and is
// parity-tested for every combination of statuses (tests/unit/test_static_preview.py).

export const STATUSES = ["consistent", "contradicted", "inconclusive", "not_tested", "evidence_unavailable", "incompatible"];
export const OVERALL_RULE = "any contradicted test → contradicted; else any consistent test → consistent so far; else all untested → untested; else inconclusive";

export function overallStatus(statuses) {
  if (statuses.includes("contradicted")) return "contradicted";
  if (statuses.includes("consistent")) return "consistent so far";
  if (statuses.every((s) => ["not_tested", "evidence_unavailable", "incompatible"].includes(s))) return "untested";
  return "inconclusive";
}
