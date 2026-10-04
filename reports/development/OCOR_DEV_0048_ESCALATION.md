# Escalation record — OCOR-DEV-0048 (repair budget exhausted)

- **Status**: `BLOCKED_REPAIR_BUDGET_EXHAUSTED`
- **Task**: `OCOR-DEV-0048` — integrazione di sicurezza a backend reale (OPA, Keycloak,
  SPIFFE/SPIRE, OpenBao, mTLS)
- **Change set**: `governed/state-sync-ocor-dev-0048-escalation`
- **Fonte**: OCOR-RCCAD v1.0 §8 (harness) — al massimo 2 cicli di riparazione materialmente
  diversi per task; oltre, escalation con diagnosi e azione minima di sblocco.

## Contesto

`OCOR-DEV-0048` ha esaurito il budget di 2 cicli di riparazione materialmente diversi. Tre
verdetti indipendenti `NO_GO`:

- ciclo 0 `OCOR-DEV-0048-587e4a8485c4-0` (head `587e4a84…`): 8 finding (`VF-001`…`VF-008`);
- ciclo 1 `OCOR-DEV-0048-de9e7cd429f6-1` (head `de9e7cd4…`): 7 finding (`VF-001`…`VF-007`);
- ciclo 2 `OCOR-DEV-0048-eda08db30ca2-2` (head `eda08db3…`): 2 finding bloccanti `high`.

I cicli di riparazione sono stati materialmente diversi (da 8 a 7 a 2 finding), ma i due
finding `high` residui persistono dopo entrambe le riparazioni.

## Finding bloccanti (ciclo 2)

### VF-001 — bypass della finestra temporale via offset timezone (`high`)

La serializzazione firmata usa `strftime` con `Z` senza conversione UTC (anche
`SignedDelegation:626`), mentre i guard confrontano gli istanti `datetime` con il loro offset.
Riproduzione verificata dal verifier indipendente su OPA reale: `DELEGATION_EXPIRED` diventa
`ACCEPTED` alterando solo `tzinfo` a `UTC-02:00`; il bundle con `expires_at=…+00:00` è respinto
con `POLICY_BUNDLE_WINDOW_INVALID`, ma sostituendo soltanto l'offset con `-02:00` (payload e
firma invariati) `install_policy` lo accetta e OPA restituisce `PERMIT`. Contraddice
ADD v1.3 §§5.1–5.2 (finestra verificata a ogni decisione e impossibilità per il grantee di
estenderla).

### VF-002 — delega non cablata nel percorso Keycloak→OPA (`high`)

Il criterio del task richiede che i servizi reali impongano anche la delegazione. I sette casi
`test_valid_signed_delegation_*` / `test_*delegation*` chiamano unicamente
`_sign_delegation`/`verify_signed_delegation`; la fixture `principal` autentica il delegatee ma
non esercita una delega Keycloak→OPA. `test_revoked_delegation_fails_closed` passa `revoked=True`
dall'interno del test, senza revoca autorevole osservata al boundary. `verify_signed_delegation`
non è invocato da alcun provider: `authenticate:847–866` deriva solo una `actor_chain` dal JWT e
`evaluate:1090` confronta insiemi di attori, senza consumare il grant o la sua revoca.
Contraddice ADD v1.3 §5.2 regole 4–5 e il primo `acceptance_criteria` del task.

## Azione minima di sblocco

1. **VF-001**: usare per firma ed enforcement gli stessi istanti canonici UTC con la stessa
   precisione, oppure rifiutare rappresentazioni temporali non canoniche; correggere entrambe le
   `signing_payload`. Aggiungere controlli positivi e negativi che distinguano offset equivalenti
   dallo spostamento dell'istante, e dimostrino su OPA reale il rigetto del riuso di bundle/deleghe
   scaduti con offset alterato.
2. **VF-002**: collegare la validazione del grant e del suo stato di revoca al percorso
   obbligatorio dei provider autorizzati. Aggiungere una richiesta delegata valida che raggiunga i
   backend reali e controlli negativi sulla stessa operazione per grant assente, scaduto, revocato,
   fuori scope/purpose e chain alterata, senza mock del boundary.
3. Richiedere una terza verifica indipendente su
   `task/OCOR-DEV-0048-integrate-opa-keycloak-spiffe-openbao-mtls`
   (head `eda08db30ca20c722a1cc11d25e4b34d7c590227`).

L'esecuzione di una terza riparazione eccede il budget di 2 cicli del harness (OCOR-RCCAD §8):
richiede l'autorizzazione esplicita del Product Owner o una disposition governata alternativa.

## Impatto

`OCOR-DEV-0048` è marcato `BLOCKED_REPAIR_BUDGET_EXHAUSTED`. Tutti i 21 task residui
(`OCOR-DEV-0049`…`OCOR-DEV-0069`) dipendono transitivamente da `OCOR-DEV-0048`: nessun lavoro
eseguibile resta nel backlog. Stato terminale `TERMINAL_BLOCKED` in attesa della disposition del
Product Owner.

## Task bloccati

`OCOR-DEV-0048` e, transitivamente, `OCOR-DEV-0049`…`OCOR-DEV-0069`.

## Claim fence

Invarato: `E1=0`, `E2=0`, zero requisiti `Verified`, `runtime_conformance` `NOT_ESTABLISHED`,
`PoC`/`Production` `NO-GO`. `inputs/` invariato. L'evidenza di `OCOR-DEV-0048` resta
`CANDIDATE_PENDING_INDEPENDENT_VERIFICATION` (non sigillata).

## Disposition (Product Owner, 2026-10-02)

Il Product Owner ha autorizzato **UN SOLO** terzo ciclo di riparazione con decisione
`OCOR-DEV-0048-REPAIR-3` (2026-10-02), in deroga puntuale al budget di 2 cicli (OCOR-RCCAD §8).
Il budget resta 2 per ogni altro task.

- **Ambito**: esclusivamente `VF-001` e `VF-002` del verdetto `OCOR-DEV-0048-eda08db30ca2-2`,
  secondo l'"Azione minima di sblocco" sopra.
- **Branch**: `task/OCOR-DEV-0048-integrate-opa-keycloak-spiffe-openbao-mtls`, a partire da head
  `eda08db30ca20c722a1cc11d25e4b34d7c590227`, senza riscrivere ciò che è già stato accettato.
- **Vincolo VF-002**: `verify_signed_delegation` e lo stato di revoca devono essere consumati nel
  percorso obbligatorio dei provider, con una richiesta delegata valida sui backend reali e i
  negativi sulla stessa operazione (grant assente, scaduto, revocato, fuori scope/purpose, chain
  alterata), senza mock del boundary.
- **Divieto**: indebolire test, gate o criteri di accettazione per ottenere il GO.

### Esito della riparazione (ciclo 3)

- Head del branch: `7f2fff555621424c8c89764aba16810f038ef509` (2 commit su `eda08db3…`):
  `fix(OCOR-DEV-0048): VF-001 canonical UTC bundle signing + VF-002 delegation grant/revocation
  enforced at the policy boundary` e `evidence(OCOR-DEV-0048): regenerate G4 evidence with 50
  qualifying cases`.
- `VF-001`: istanti canonici UTC con identica precisione usati per firma ed enforcement
  (`signing_payload` corretto in entrambi i percorsi); aggiunti 2 casi di finestra
  (`BUNDLE-OFFSET-EQUIVALENT-STABLE`, `BUNDLE-OFFSET-SHIFTED-REJECTED`).
- `VF-002`: `verify_signed_delegation` e lo stato di revoca consumati da
  `OpaPolicyDecisionProvider.evaluate`; aggiunti 7 casi sulla stessa operazione
  (`DELEGATED-REQUEST-{VALID-PERMIT, ABSENT-GRANT, EXPIRED, REVOKED, OUT-OF-SCOPE, OUT-OF-PURPOSE,
  ALTERED-CHAIN}`) sui backend reali, senza mock del boundary.
- Gate locali verdi: `50 passed` su `test_ocor_dev_0048.py` (stack `ocor-bootstrap` reale),
  `ruff check` e `mypy --strict` puliti, `validate_runtime_evidence.py` `PASS`,
  `validate_rccad.py` `PASS_LOCAL_PRECHECK`, `validate_language_policy.py`,
  `validate_ocor_change_scope.py` e `validate_evidence_input_drift.py` verdi, `sha256sum` normativo
  `PASS`.
- Richiesta di verifica indipendente: `OCOR-DEV-0048-7f2fff555621-3` (`TASK_EVIDENCE`,
  `repair_cycle: 3`).

### Verdetto indipendente (ciclo 3): `NO_GO`

Richiesta `OCOR-DEV-0048-7f2fff555621-3` (`TASK_EVIDENCE`, `repair_cycle: 3`) eseguita dal verifier
indipendente sull'HEAD esatto `7f2fff555621424c8c89764aba16810f038ef509` (suite completa `955 passed`
sullo stack reale, `ruff`/`mypy` puliti, backend reali OPA/Keycloak/OpenBao/SPIRE healthy). Verdetto
`NO_GO` con 2 finding bloccanti `high`, diversi dai precedenti:

- **VF-001** (`high`) — `ocor-runtime/src/ocor_runtime/security/control_plane.py:1212`: la rivalidazione
  della finestra della delega usa l'istante conservato nella richiesta (`request.at`) anziché l'istante
  corrente attendibile del boundary. Una delega scaduta genera comunque `PERMIT` perché `request.at`
  precede `grant.expires_at` (riproduzione `test_delegation_time.py`, raw `command-019.log`).
  Contraddice ADD v1.3 §5.1 (catena scaduta ⇒ `DENY`) e il criterio fail-closed/FR-128.
- **VF-002** (`high`) — `ocor-runtime/src/ocor_runtime/security/control_plane.py:1259-1261`:
  `PolicyDecision.valid_until` è fissato a una durata di 300 secondi limitata solo dal bundle; la
  scadenza della delega non limita il `PERMIT`, quindi una decisione delegata sopravvive alla propria
  Authority. Contraddice ADD v1.3 §5.1/§5.2 e l'autorità limitata dalla `Delegation` (FR-128).

Azione di correzione indicata dal verifier: rivalidare la finestra al tempo corrente del boundary e
limitare `valid_until` alla scadenza canonica del grant, con positivi/negativi dedicati
(`DELEGATION_EXPIRED` / `POLICY_DECISION_EXPIRED` per la ragione corretta). **Non eseguita**: la
decisione `OCOR-DEV-0048-REPAIR-3` autorizza un solo terzo ciclo e vieta ulteriori riparazioni.

### Stato (finale)

`OCOR-DEV-0048` è terminale: `BLOCKED_REPAIR_BUDGET_EXHAUSTED`. Il ciclo 3 (head
`7f2fff555621424c8c89764aba16810f038ef509`) è stato verificato indipendente `NO_GO`; per la decisione
`OCOR-DEV-0048-REPAIR-3` non è consentita alcuna ulteriore riparazione. Tutti i 21 task residui
(`OCOR-DEV-0049`…`OCOR-DEV-0069`) restano bloccati transitivamente. L'evidenza di `OCOR-DEV-0048`
resta `CANDIDATE_PENDING_INDEPENDENT_VERIFICATION` (non sigillata). Nessun lavoro di backlog eseguibile
resta: stato terminale `TERMINAL_BLOCKED`.

## Claim fence

Invarato: `E1=0`, `E2=0`, zero requisiti `Verified`, `runtime_conformance` `NOT_ESTABLISHED`,
`PoC`/`Production` `NO-GO`. `inputs/` invariato. L'evidenza di `OCOR-DEV-0048` resta
`CANDIDATE_PENDING_INDEPENDENT_VERIFICATION` (non sigillata).

## Ripresa autorizzata — OCOR-DEV-0048-REPAIR-4-CODEX (2026-10-03)

Il PO autorizza un solo quarto ciclo Codex dalla base `7f2fff555621424c8c89764aba16810f038ef509`. Il divieto terminale del ciclo 3 è superseduto per questo change set; la storia sopra resta invariata.

Implementazione VF-001/VF-002 e classe temporale completata come candidato su `c6cbcd3282161aafd404e73bec49acffb1ffb011`: 76 casi task passanti (26 nuovi), suite runtime `981 passed`, reports CI `82 passed`, zero skip qualificanti. Tempo corrente del boundary prima/dopo I/O e validità limitate all'intersezione delle autorità verificate. Evidenza non sigillata; richiesta `OCOR-DEV-0048-c6cbcd328216-4` (`repair_cycle: 4`).

Implementatore della riparazione e verifier usano lo stesso modello in contesti separati; nessuna diversità di modello dichiarata. Verifica esterna pendente. Con nuovo `NO_GO`: nessuna riparazione ulteriore, `TERMINAL_BLOCKED`. Nessun merge in questa sessione. Claim fence invariato.
