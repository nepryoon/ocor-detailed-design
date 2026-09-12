# OCOR Decision Traceability Index v1.6 — append-only continuation

## Configuration control

Incorpora senza modifica `OCOR_Decision_Traceability_Index_v1.5_APPROVED.md` con
SHA-256 `345bdb5ddc9e3efc156faac245a3de5efbfc54221c41f86b311fa4546a7241b9`
e aggiunge esclusivamente `DEC-212`.

| Decisione | Origine | Oggetto | Downstream | Gate | Claim fence |
|---|---|---|---|---|---|
| `DEC-212` | Product Owner mandate / `CC-OCOR-LANGUAGE-POLICY` | Internal implementation language policy and executable gate, distinct from the `DEC-075`/`FR-047`/`FR-048` SDK profile | `AGENTS.md`; `docs/development_methodology/OCOR_LANGUAGE_POLICY.md`; `scripts/validate_language_policy.py`; CI | RED/GREEN, immutable inputs, independent verifier, exact-head CI | `E1=0`; `E2=0`; zero global `Verified`; runtime/PoC/Production `NO-GO` |
