# OCOR development methodology

Questa directory contiene la baseline di processo `OCOR-RCCAD v1.0`, adottata da
`DEC-210`. Il manifest machine-readable `methodology.json` è l'indice canonico; non
sostituisce il backlog, il DAG o i registri normativi esistenti.

- `OCOR_RCCAD_v1.0.md`: lifecycle e loop operativo.
- `OCOR_TEST_STRATEGY.md`: tecniche di assurance e protocollo TDD.
- `OCOR_ARCHITECTURE_FITNESS_FUNCTIONS.md`: regole bloccanti eseguibili.
- `OCOR_DEFINITION_OF_DONE.md`: condizioni cumulative di completamento.
- `OCOR_MODEL_OPERATING_PROFILE.md`: routing e fingerprint del modello/ambiente.
- `methodology.schema.json`: contratto JSON del manifest.
- `OCOR_LANGUAGE_POLICY.md`: linguaggio di implementazione autorizzato per ogni
  area del progetto, versioni pinnate e soglie di migrazione (`DEC-212`), distinto
  dal profilo degli SDK generati (`DEC-075`/`FR-047`/`FR-048`). Applicato fail-closed
  da `scripts/validate_language_policy.py`.

Lo stato volatile ma durevole è soltanto in `reports/development/`; le evidenze di
gate restano in `reports/evidence/`.
