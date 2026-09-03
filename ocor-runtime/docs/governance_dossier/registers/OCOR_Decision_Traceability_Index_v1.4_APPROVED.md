# OCOR Decision Traceability Index v1.4 — append-only continuation

## Configuration control

Questo indice incorpora senza modifica
`OCOR_Decision_Traceability_Index_v1.3_APPROVED.md` con SHA-256
`a8952aadb4c4ae53af7f31c606cd853bd041562d18b13c5f55776e7053772905` e aggiunge
esclusivamente la tracciabilità `DEC-210`. In caso di digest diverso l'indice è
invalido.

| Decisione | Origine | Oggetto | Artefatti downstream | Evidenza / gate | Claim fence |
|---|---|---|---|---|---|
| `DEC-210` | Product Owner mandate / `CC-RCCAD-METHODOLOGY-ADOPTION` | Development-process methodology; refinement, non architecture semantics | `AGENTS.md`; `PLANS.md`; `docs/development_methodology/`; `reports/development/`; `.github/workflows/ocor-rccad.yml` | `reports/tests/rccad_tdd_evidence.json`; independent verifier; pinned CI | `E1=0`; `E2=0`; zero global `Verified`; runtime/PoC/Production `NO-GO` |
