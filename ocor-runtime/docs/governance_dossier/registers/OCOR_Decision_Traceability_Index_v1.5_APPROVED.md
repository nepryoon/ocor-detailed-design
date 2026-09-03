# OCOR Decision Traceability Index v1.5 — append-only continuation

## Configuration control

Incorpora senza modifica `OCOR_Decision_Traceability_Index_v1.4_APPROVED.md` con
SHA-256 `78092ba4ca892db2d7f20114812fe2b6f5042c6652588dc57b5b73e77d2d75e0`
e aggiunge esclusivamente `DEC-211`.

| Decisione | Origine | Oggetto | Downstream | Gate | Claim fence |
|---|---|---|---|---|---|
| `DEC-211` | Product Owner mandate / `CC-AUTONOMOUS-TOOLING-INFRASTRUCTURE-BOOTSTRAP` | Autonomous tooling and disposable infrastructure policy | `AGENTS.md`; `infra/`; `deploy/bootstrap/`; `scripts/`; backlog/DAG; CI | manifest schemas, RED/GREEN, immutable inputs, independent verifier, exact-head CI | `E1=0`; `E2=0`; zero global `Verified`; runtime/PoC/Production `NO-GO` |
