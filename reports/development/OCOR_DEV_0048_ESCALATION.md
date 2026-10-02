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
