# Escalation record — OCOR-DEV-0049 (repair budget exhausted)

- **Status corrente**: `AWAITING_AUTHORIZED_CLAUDE_REPAIR`
- **Disposition storica ciclo 2**: `BLOCKED_REPAIR_BUDGET_EXHAUSTED`, superseded dalla decisione PO `OCOR-DEV-0049-REPAIR-CLAUDE-AUTO` (2026-10-05).
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

## 2026-10-05 — Decisione PO e verdetto ciclo 3

La decisione `OCOR-DEV-0049-REPAIR-CLAUDE-AUTO` supera l’escalation della PR #168 e autorizza fino a tre ulteriori riparazioni (cicli 3, 4, 5), esclusivamente Claude Code (Anthropic), con verifier Codex (OpenAI). Il budget ordinario resta 2 per gli altri task. Il testo precedente descrive la disposition storica del ciclo 2; non è il blocco corrente.

Verdetto `OCOR-DEV-0049-02ac643eb3c7-3`, HEAD `02ac643eb3c770361f2f1b67eb0f4ab2bc049097`, creato `2026-10-05T20:09:14.995625Z`: **NO_GO**. SHA-256 del file esterno: `2c860eb6e1bcbeb809125754058bcbda62c7a53cc5f2cedf16d17e650f781f60`. Il task remoto coincide con l’HEAD verificato. Nessun controllo `not_executed` nel verdetto.

### VF-001 — ciclo 3 (`high`, BLOCKER)

Riferimento: `deploy/helm/ocor-poc/compose.profiles.yaml:938`.

latest_valid_receipt verifica firma e digest del manifest, ma non collega manifest.release/profile_digest al profilo corrente. Riproduzione sul codice dell'HEAD richiesto e su OpenBao reale: python3 /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/run.py receipt-pinned ocor-runtime/.venv/bin/python /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/reproduce_receipt.py (worktree detached e ambiente ripristinati secondo il mandato). Il controllo con release ocor-poc-0.2.0 passa. Cambiando solo la release del profilo in ocor-poc-independent-unrestored-release, mantenendo la receipt firmata e il manifest di ocor-poc-0.2.0, /readyz restituisce 200 READY, POST /reopen 200 e /admit?class=mutative 200 ADMIT. Digest corrente e digest del manifest differiscono (e2985ec8... contro d28a8daa...). Prova: /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/logs/receipt-pinned.log, SHA-256 b023cc2e2db8e87dea42e7da85b262072ade4c2af8c9eb0bf9d1f3b851597615. Viola il criterio negativo del task sul restore non testato e la release fence di ADD §6.3/§6.5 e FR-156; il test di drift attuale copre solo il cambiamento del file dopo startup.

Azione richiesta a Claude Code: Prima di assegnare RESTORE_TESTED, verificare che la recovery point e la receipt siano compatibili e vincolate alla release, al digest del profilo e ai pin correnti; un mismatch deve negare readiness e riapertura e mantenere DENY per le operazioni governate. Aggiungere casi live positivi/negativi di riavvio con receipt della release/profilo precedente in entrambi i carrier e rigenerare l'evidenza candidata sul nuovo HEAD, senza cambiare inputs o claim fence.

### VF-002 — ciclo 3 (`high`, BLOCKER)

Riferimento: `deploy/helm/ocor-poc/compose.profiles.yaml:926`.

Il consumer usa soltanto receipt.outcome == PASSED e non controlla i risultati della recovery_gate. Nello stesso riproduttore indipendente, dopo il controllo positivo, una copia della receipt viene resa internamente incoerente: outcome resta PASSED ma recovery_gate.gcs.pass è false e tenant_mismatch contiene m1. La copia è firmata nuovamente dal vero OpenBao transit con la chiave del PoC autorizzato: il test controlla la semantica del consumer di una receipt firmata, senza mock o bypass della firma. Il manifest firmato e il relativo digest restano corretti. /readyz, POST /reopen e /admit?class=mutative restituiscono ancora 200, e la mutazione è ADMIT. Prova: /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/logs/receipt-pinned.log (SHA-256 b023cc2e2db8e87dea42e7da85b262072ade4c2af8c9eb0bf9d1f3b851597615); comando come VF-001. LLD §5.4 richiede GCS/marking e gli altri controlli del recovery gate prima di riaprire traffico; una firma autentica non rende coerente un record con gate fallito. La suite del task non include questo caso negativo del consumer.

Azione richiesta a Claude Code: Validare struttura, versione e coerenza della receipt firmata prima di usarla: tutti i controlli obbligatori della recovery_gate devono essere presenti e avere pass strettamente true; gate mancanti, falsi o malformati devono produrre un reason code specifico, readiness negata, /reopen rifiutato e admission DENY. Aggiungere controlli live con receipt validamente firmate positive e negative per ciascun gate, preservando il fence G4/G6 già approvato e rigenerando soltanto l'evidenza candidata.

### VF-003 — ciclo 3 (`medium`, BLOCKER)

Riferimento: `ocor-runtime/tests/tasks/test_ocor_dev_0049.py:1446`.

Il test qualificante Helm assume che il catalogo contenga esattamente un recovery point dopo il backup manuale, mentre il CronJob resta attivo con schedule */15 * * * *. Nella suite completa sull'HEAD richiesto il job manuale è completato ma l'asserzione len(...) == 1 fallisce con due recovery point reali, rp-20261005T194504Z-35d8c606 e rp-20261005T194509Z-c8eb6135, al confine delle 19:45 UTC. La configurazione consente un backup pianificato durante il test: il requisito sul catalogo totale dipende dall'orario, non dal successo del job sotto verifica. Prova: /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/logs/full-suite.log, SHA-256 43c00284efb1fc965d7c452d804bcabee2113228b138b12da2882f979c0fbc0d; JUnit /tmp/ocor-verify-OCOR-DEV-0049-02ac643eb3c7-3/full-suite.xml. La run mirata aveva passato lo stesso test fuori da tale intersezione. I quattro fallimenti separati per DEPENDENCY_DOWN:fuseki sono diagnosticati e trattati come OOM dello stack, non come questo finding. Riproduzione: avviare la suite Helm sullo stack reale in modo che il backup manuale si sovrapponga a un tick del CronJob, conservando lo schedule approvato. La seconda suite completa, dopo il ripristino di Fuseki e fuori dalla sovrapposizione osservata, ha 1192 PASS e zero skip (full-suite-retry.log, SHA-256 3d8ee16d82ef2d96f136b6966637434151b5fce07095aab105e44bd217c0e832): ciò non elimina la race riprodotta nella prima run.

Azione richiesta a Claude Code: Correlare il recovery point, il manifest e la receipt al job effettivamente verificato, senza assumere la cardinalità totale del catalogo; mantenere il controllo del vault esterno e delle firme. Aggiungere un caso operativo con backup pianificato e manuale concorrenti e verificare entrambi i manifest, senza skip, ignore o quarantine. La campagna qualificante deve essere riproducibile anche al confine del tick CronJob.

Restano **due** cicli autorizzati: prossimo `repair_cycle=4`, poi al massimo 5. Aggiornare `~/.ocor-codex/audit_0049.md`, correggere tutti i finding del verdetto più recente senza riscrivere ciò che è già accettato, riacquisire ogni campo candidato dall’HEAD finale e richiedere verifica Codex. Esauriti i tre ulteriori cicli con `NO_GO`: escalation e `TERMINAL_BLOCKED`.

Il loop implementato da Codex esegue soltanto questa sincronizzazione; termina con `TERMINAL_BLOCKED` e `next_action` «ciclo di riparazione Claude Code su OCOR-DEV-0049», come imposto dalla decisione, pur restando pronto 0050 e aperta REM-0017. Non è una dichiarazione di indisponibilità dell’intero backlog. PR #169 concorrente non modificata; REM-0017 resta prioritario dopo la fase 0049 e obbligatorio prima di G6. Evidenza 0049 candidata, non sigillata; `inputs/`, E1/E2/Verified e claim fence invariati.
