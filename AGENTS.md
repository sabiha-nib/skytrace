# AGENTS.md — rules for any agent working on SKYTRACE

1. Retrieve and organise observations only through `skytrace.archive` (it handles timeouts, retries, caching, provenance, OFFLINE=1).
2. Measurements come only from `skytrace.science` functions. Never compute or estimate a scientific number in prose.
3. Every reported result must trace to logged events with provenance (`skytrace.report.Investigation`).
4. Keep rejected observations and failed steps visible; do not delete or soften them.
5. Label data origin truthfully: live, cache, fixture, synthetic.
6. New external calls need an explicit timeout, bounded size, and a test of their failure path.
7. Offline mode must keep working; test it with sockets blocked (`no_network` fixture), not just the env var.
8. New code ships with tests and a doc update (`docs/REQUIREMENT_TRACEABILITY.md` status changes need evidence).
9. Secrets only via environment variables; never in code, logs, fixtures or the frontend.
10. Do not call a candidate a discovery.
