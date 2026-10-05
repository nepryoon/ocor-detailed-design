# Escalation record — OCOR-DEV-0049 (repair budget exhausted)

- **Status**: `BLOCKED_REPAIR_BUDGET_EXHAUSTED`
- **Task**: `OCOR-DEV-0049` — Implement PoC deployment observability backup and safe degradation
- **Change set**: `governed/state-sync-ocor-dev-0049-escalation`
- **Fonte**: OCOR-RCCAD v1.0 §8 (harness) — al massimo 2 cicli di riparazione materialmente
  diversi per task; oltre, escalation con diagnosi e azione minima di sblocco.
- **Implementatore della riparazione (ciclo 2)**: Claude Code (Anthropic); **verifier**: Codex
  (OpenAI) — modelli di fornitori diversi in processi separati (decisione PO
  `OCOR-DEV-0049-IMPLEMENTER-CLAUDE`, 2026-10-05).

## Contesto

`OCOR-DEV-0049` ha esaurito il budget ordinario di 2 cicli di riparazione. Tre verdetti
indipendenti `NO_GO`:

- ciclo 0 `OCOR-DEV-0049-884f7b1160b1-0` (head `884f7b1160b1802c0b00faede1ae00743459d7f5`):
  3 finding bloccanti `high` (`VF-001`…`VF-003`): profili Compose/Helm non operativi, inventario
  delle dipendenze non validato, manifest di backup/replay non vincolanti;
- ciclo 1 `OCOR-DEV-0049-2c5a574a5f3a-1` (head `2c5a574a5f3a127ffd9857601bfa9e593b69e604`):
  6 finding bloccanti `high` (`VF-001`…`VF-006`): processo reale non avviato, restore non
  consumato dal gate, telemetria non osservata, backup non durevole fuori fault domain,
  default-deny non applicata, job qualificante non fail-closed;
- ciclo 2 `OCOR-DEV-0049-7fd4f7728801-2` (head `7fd4f77288010b98330f74a4da455fa1b6e9e321`):
  3 finding bloccanti `high` (`VF-001`…`VF-003`), sotto descritti.

I cicli sono stati materialmente diversi (da 3 a 6 a 3 finding), ma tre difetti `high` residui
persistono dopo entrambe le riparazioni: ammissione non fail-closed, default-deny di rete non
enforce, e gate di restore che non verifica il binding di isolamento per item.

## Finding bloccanti (ciclo 2)

### VF-001 — ammissione non fail-closed su scanner indisponibile / restore non verificato (`high`)

`deploy/helm/ocor-poc/compose.profiles.yaml:1069`. Con tutte le dipendenze disponibili, `/readyz`
risponde `503 RESTORE_UNTESTED` ma `/admit?class=mutative` risponde `200 ADMIT`. Dopo corruzione
del solo profilo temporaneo montato, `/readyz` risponde `503 SCANNER_ERROR` ma
`/admit?class=dispatch` continua a rispondere `200 ADMIT`. Il controllo positivo Emergency Stop
risponde invece `503 DENY`: il bypass dipende dalla guardia, non dal mancato raggiungimento del
processo. `Handler.do_GET` usa soltanto `denied_operation_classes`; `scanner error` e restore non
verificato non entrano in `State.faults`. Viola il comportamento fail-closed e il recovery gate
prima della riapertura previsti da LLD §5.3–5.4; i test 0049 provano la readiness senza verificare
queste ammissioni.

### VF-002 — default-deny di rete non enforce: alias tutti equivalenti (`high`)

`deploy/helm/ocor-poc/compose.profiles.yaml:1180`. `GET http://postgresql:8181/v1/policies`
restituisce `200` con la risposta del vero OPA, pur essendo `postgresql:8181` assente da
`isolation.allowedFlows`. Tutti i nomi dei servizi sono alias dello stesso relay (riga 60), che
ascolta su `0.0.0.0` per ogni porta ammessa e seleziona l'upstream dalla sola porta. Qualsiasi
alias raggiunge qualsiasi porta dell'allowlist. Il test `test_default_deny_admits_only_allowlisted_intra_site_flows`
controlla porte totalmente escluse, ma non coppie host/porta incrociate. Il default-deny con soli
flussi esplicitamente ammessi di ADD §6.1 e LLD §5.1 non è rispettato.

### VF-003 — gate di restore non verifica tenant/compartment per item (`high`)

`deploy/helm/ocor-poc/compose.profiles.yaml:1500`. I metadati PostgreSQL autorevoli di `m1` hanno
`tenant-a/c1`; prima del backup il payload del vero Qdrant è impostato a `tenant-b/c2` con
`governed_context_digest` non vuoto. Backup cifrato e firmato dal vero OpenBao, restore su
PostgreSQL/Qdrant isolati: `exit 0`, `outcome PASSED`, `recovery_gate.gcs.pass=true`. La lettura
dell'indice ripristinato conferma `tenant-b/c2`, diverso dai metadati. Il gate GCS verifica
soltanto che `tenant_id` e digest siano non vuoti; non verifica il binding per item né il
compartment. Il gate di LLD §5.4 e il blocco del projection drift di ADD Part II §2.13 non
rilevano questa incoerenza di isolamento.

## Azione minima di sblocco

1. **VF-001**: bloccare le ammissioni governate/mutative/dispatch quando il controllo di sicurezza
   è indisponibile o il restore è non verificato/fallito, e applicare la riapertura governata
   prevista dal profilo; conservare le degradazioni esplicitamente autorizzate. Aggiungere casi
   operativi positivi e negativi per `SCANNER_ERROR`, `RESTORE_UNTESTED`, receipt invalid/fallita ed
   egress aperto, verificando le decisioni oltre `/readyz`.
2. **VF-002**: enforzare le coppie destinazione/porta dichiarate, con indirizzi o proxy distinti e
   senza listener comuni che rendano tutti gli alias equivalenti. Verificare operativamente la
   coppia ammessa `opa:8181` e negare `postgresql:8181`, `qdrant:5432` e le altre coppie non
   dichiarate; mantenere i controlli positivi e negativi di egress.
3. **VF-003**: confrontare per ogni item il tenant e il compartimento della proiezione con i
   metadati autorevoli, rivalidando anche marking e binding GCS secondo i contratti. Qualsiasi
   mismatch deve produrre receipt `FAILED` e materialisation `BLOCKED`. Aggiungere test con scope
   coerente e mismatch per singolo item, osservando sia receipt sia stato dei servizi ripristinati.

L'esecuzione di una terza riparazione eccede il budget di 2 cicli del harness (OCOR-RCCAD §8):
richiede l'autorizzazione esplicita del Product Owner o una disposition governata alternativa.

## Impatto

`OCOR-DEV-0049` è marcato `BLOCKED_REPAIR_BUDGET_EXHAUSTED`. Task che dipendono transitivamente da
`OCOR-DEV-0049`: `OCOR-DEV-0059`, `OCOR-DEV-0060`, `OCOR-DEV-0063`, `OCOR-DEV-0064`,
`OCOR-DEV-0066`. Restano eseguibili `OCOR-DEV-0050` (hard_dependencies soddisfatte, non dipende da
`OCOR-DEV-0049`) e il suo downstream, oltre a `OCOR-DEV-REM-0017` (CI-0048-REAL-BACKEND), che è la
prossima azione.

## Task bloccati

`OCOR-DEV-0049` e, transitivamente, `OCOR-DEV-0059`, `OCOR-DEV-0060`, `OCOR-DEV-0063`,
`OCOR-DEV-0064`, `OCOR-DEV-0066`.

## Claim fence

Invarato: `E1=0`, `E2=0`, zero requisiti `Verified`, `runtime_conformance` `NOT_ESTABLISHED`,
`PoC`/`Production` `NO-GO`. `inputs/` invariato. L'evidenza di `OCOR-DEV-0049` resta
`CANDIDATE_PENDING_INDEPENDENT_VERIFICATION` (non sigillata).
