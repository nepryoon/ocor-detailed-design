# OCOR — Revisione completa del codice (2026-09-15)

Revisione indipendente, tool-backed, dell'intero codice della repository richiesta
prima di proseguire con lo sviluppo. Eseguita in modalità di revisione: scritture
limitate a `reports/`, `inputs/` immutabile, nessun incremento dello stato probatorio.

- Baseline commit: `b1eefb3` (HEAD di `main`; PR #126, state-sync fino a `OCOR-DEV-0047`).
- Branch di lavoro: `cursor/code-review-remediation-1935`.
- Verdetto meccanico: **nessuna anomalia bloccante** nei gate imposti dal repository con la
  toolchain corretta. L'audit manuale registra alcune osservazioni **latenti** (sotto),
  tutte riservate a un change set di remediation governato — non corrette qui, per le
  ragioni di governance in §5.

## 1. Toolchain di revisione (pin scoperti e verificati)

| Strumento | Versione richiesta dal repo | Note |
|---|---|---|
| Python | `3.12.11` (esatto) | `ocor-runtime/.python-version`; fornito da `uv` |
| uv | `0.12.5` | `ocor-runtime/devcontainer.json`, CI `astral-sh/setup-uv` |
| Node.js | `20.20.2` (esatto) | CI `setup-node`; **obbligatorio** per l'oracolo JCS di `test_ocor_dev_0007` |
| PostgreSQL | 16 | `OCOR_LIVE_POSTGRES_DSN=postgresql://ocor:ocor@127.0.0.1:5432/ocor` |
| Stack servizi | Docker `deploy/bootstrap/compose.yaml` | TerminusDB, TypeDB, Jena/Fuseki, Kafka, OPA, Keycloak, OpenBao, SPIRE, Qdrant |

Nota metodologica importante: con Node errato (es. `v22`) `test_ocor_dev_0007` (AFF-005)
fallisce **per pin di versione dell'oracolo**, non per difetto di codice. Con Node
`20.20.2` la suite passa (51/51). Questo è un vincolo d'ambiente, non un'anomalia.

## 2. Gate meccanici eseguiti

| Gate | Comando | Esito |
|---|---|---|
| Integrità sorgenti | `sha256sum -c inputs/normative/SHA256SUMS` | PASS (8/8) |
| Harness ADD | `scripts/verify.py` | PASS 14 / FAIL 0 / NOT_EXECUTED 0 |
| Lint (gate imposto) | `ruff check .` | All checks passed |
| Type gate | `mypy` (strict) | Success, 67 file |
| Fitness AFF-005 | `test_ocor_dev_0007.py` (Node 20.20.2) | 51 passed |
| Fitness AFF-001..010 | task tests + `validate_rccad.py` + `validate_ocor_development_plan.py` | exit 0 (vedi §2.1) |
| Language policy | `validate_language_policy.py` + `test_validate_language_policy` | PASS |
| Change scope | `validate_ocor_change_scope.py` | PASS (immutable surfaces untouched) |
| Suite governance `reports/tests/` | rccad, backlog-parity, tooling-policy, bootstrap-lock, generate-contracts-refs, benchmark-harness | tutte PASS |
| Suite runtime | `pytest ocor-runtime/tests/` (toolchain completa + Postgres) | 765 passed; residui = solo servizi Docker (vedi §2.2) |

### 2.1 Falsi positivi chiariti (non anomalie)

- **`validate_ocor_development_plan.py` verdetto `FAIL`**: il conteggio riporta 1 `FAIL` +
  2 `NOT_EXECUTED`, ma l'**exit code è 0**. Il `FAIL` è il check contestuale
  «authorized planning-only diff», significativo solo in una PR di modifica del piano;
  i 2 `NOT_EXECUTED` sono `markdownlint`/`mmdc` non disponibili (correttamente non
  promossi a PASS). Non è un difetto di codice.
- **`ruff format --check`**: segnala 181 file «da riformattare», ma il repository impone
  solo `ruff check` (lint), non `ruff format`. Nessuna anomalia: riformattare sarebbe una
  modifica di massa non governata.
- **`pytest reports/tests/` (come directory)**: genera un `INTERNALERROR` perché
  `reports/tests/test_schema_conformance.py` — artefatto storico congelato,
  content-addressed e già in `extend-exclude` di ruff — chiama `sys.exit()` a livello di
  import. Va invocato con i target puntuali usati in CI, non come suite. Non è un difetto
  del codice attivo.

### 2.2 Controlli NON eseguiti localmente (marcati NOT EXECUTED, non superati)

Tutti i test residui non passati in locale dipendono dallo stack Docker e falliscono in
**fail-closed corretto** (connessione rifiutata / `docker` assente): campagne reali su
TerminusDB, TypeDB, Jena/Fuseki, Kafka, OpenBao e i test `docker compose` di
`OCOR-DEV-0006`. In CI (`ocor-poc-ci`, `ocor-rccad`) questi girano contro i servizi reali
e risultano verdi sull'ultima integrazione (`latest_ci_evidence`: 13/13). Non sono
anomalie di codice; restano NOT EXECUTED in questa revisione locale.

## 3. Audit manuale del codice

Superficie: 69 moduli Python (~16.8k LOC) in `ocor-runtime/src` e `scripts`, più
`ocor-runtime/tools` e l'SDK TypeScript. Nessun `TODO/FIXME/HACK`, nessun
`eval/exec/os.system/shell=True/pickle`. Tutti i blocchi `except Exception:` esaminati
sono pattern fail-closed corretti (cleanup risorsa poi `raise`). Ledger dei finding
candidati (verificati contro codice, test e flusso dati reale):

| ID | Area / file:riga | Descrizione | Severità | Raggiungibilità reale | Disposition |
|---|---|---|---|---|---|
| RVW-01 | `c4/typedb_adapter.py` `read`/`_lookup_fact` (~213), `apply_commit` (~195–202) | `fact_id`/`commit_id`/`payload` interpolati in literal TypeQL senza escape | MEDIUM | Write-path riceve solo URN/digest canonici (`rebuild.py:125` → non sfruttabile); read-path `fact_id` viene da `NamedQueryRequest.parameters` (esterno) e non è validato a livello di charset nell'adapter | RESERVED → REM (richiede TypeDB reale + revisione contratto parametri C2) |
| RVW-02 | `c4/jena_adapter.py` (~144, 167–177) | `resource_id` inserito in IRI/quple SPARQL senza escape/validazione | MEDIUM | Analoga a RVW-01; provenienza tipicamente URN | RESERVED → REM (richiede Jena/Fuseki reale) |
| RVW-03 | `c6/safety.py` `BreakGlassController.authorize` (270–282) | `authorize()` non ri-valida gli `approvers` contro `IdentityRegistry`; il doppio controllo è solo in `grant()` | LOW–MEDIUM | Il `grant` è l'artefatto già autorizzato; ripetere la validazione all'uso è difesa-in-profondità | RESERVED (semantica C6 approvata; conferma normativa prima di intervenire) |
| RVW-04 | `c1/frontend.py` (201–203) | `execution_owner` non-`str`/non-iterabile → `TypeError` invece di `C1Diagnostic` | LOW | Raggiungibile con documento DSL malformato (`"execution_owner": 42`) | RESERVED → REM (robustezza fail-closed; tocca evidenza C1 sigillata) |
| RVW-05 | `scripts/validate_rccad.py` `git_changed()` (56–66) | Non considera le modifiche **staged** (`git diff --cached`); il precheck locale d'immutabilità può non vedere edit staged-only di `inputs/` | LOW | Compensato in CI (`git diff --exit-code <base> -- inputs/`) e da `validate_ocor_change_scope.py` (che unisce `git status --porcelain`) | RESERVED → REM (hardening validator) |

### Osservazioni informative (non difetti nel flusso previsto)

- **INFO-A — idempotenza C5 (`c5/backbone.py`)**: lo short-circuit «solo chiave» è il
  comportamento **intenzionale** per il replay identico richiesto da
  `test_a_replayed_idempotency_key_is_a_safe_no_op_...`. Rilevare il conflitto
  «stessa chiave / payload diverso» (come fa C3) sarebbe un invariante più forte, oggi
  non richiesto: eventuale irrobustimento va deciso in sede normativa.
- **INFO-B — `sdk/typescript/src/cli/canonicalize.ts`**: usa `JSON.parse` (che deduplica
  le chiavi) mentre il kernel Python `load_i_json` rifiuta le chiavi duplicate. Non
  raggiungibile tramite la suite di conformità (il lato Python non emette JSON con chiavi
  duplicate); il file è esplicitamente «test-support tooling, not a generated contract».
  Possibile allineamento I-JSON, non un difetto nel flusso attuale.
- **INFO-C — concorrenza classi in-memory** (`c5/operations.py` backpressure RMW,
  `c8/tool_runtime.py` finestra TOCTOU sullo stop, stato in-memory di `c5/backbone.py`):
  presentano finestre di race **solo** sotto accesso multi-thread. Il requisito di
  thread-safety per queste classi di riferimento non è confermato; da chiarire in sede
  normativa prima di qualunque intervento (le vie reali passano da Kafka/backend).

## 4. Immutabilità e stato probatorio

- `inputs/` **invariato** (`git diff --quiet -- inputs/` = clean; SHA256SUMS OK).
- Fence probatorio invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance = NOT_ESTABLISHED`, `PoC`/`Production` = `NO-GO`. Questa revisione
  **non** promuove evidenza né claim.

## 5. Perché nessuna correzione automatica unilaterale

Tutti i finding di §3 ricadono in almeno una delle categorie che la governance del
repository (AGENTS.md, `OCOR-RCCAD v1.0`, DEC-210/211/212) vieta di correggere con una
modifica autonoma «a tappeto»:

1. **Evidenza sigillata content-addressed**: ogni modulo `ocor-runtime/src` ha evidenza
   `reports/evidence/G*/OCOR-DEV-*.json` con digest del sorgente; modificarlo invaliderebbe
   evidenza già verificata in modo indipendente e integrata.
2. **Semantica approvata** (C4/C5/C6): «nessuna modifica semantica senza nuova decisione».
   RVW-03 e INFO-A/-C riguardano invarianti che potrebbero essere **intenzionali**;
   «correggerli» senza conferma normativa rischia di rompere comportamento corretto.
3. **Validazione con backend reali**: RVW-01/-02 (e le vie C5) sono verificabili solo con
   TypeDB/Jena/Kafka reali (stack Docker), non disponibili in questa revisione locale.
4. **Autorizzazione per-change-set**: la deroga di implementazione richiede un change set
   **identificato** con criteri eseguibili e gate riproducibili, non un mandato generico
   «correggi tutte le anomalie».

Correzioni eseguite qui, alla cieca, violerebbero questi vincoli e non sarebbero
verificabili. La strada corretta è un change set di remediation governato per ciascun
item confermato.

## 6. Raccomandazioni (task di remediation proposti — id da assegnare dal processo)

In ordine di priorità, come `OCOR-DEV-REM-*` governati (RED/GREEN, verifica indipendente,
CI con backend reali, ri-sigillo evidenza):

1. **REM (RVW-01/-02)** — Escape/validazione dei literal TypeQL e degli IRI SPARQL negli
   adapter C4, con caso negativo per identificatori/payload contenenti metacaratteri;
   validare la superficie parametri di `NamedQueryRequest` a livello di contratto C2.
2. **REM (RVW-04)** — `c1/frontend.py`: emettere un `C1Diagnostic` deterministico per
   `execution_owner` di tipo non ammesso, con caso positivo e negativo.
3. **REM (RVW-05)** — `validate_rccad.py`: includere `git diff --cached` in `git_changed()`
   per chiudere la finestra staged-only nel precheck locale d'immutabilità.
4. **Chiarimento normativo** (RVW-03, INFO-A, INFO-C) — confermare in LLD l'intento su:
   ri-validazione identità in `BreakGlass.authorize`, rilevamento conflitto idempotenza
   C5, requisito di thread-safety delle classi di riferimento. Solo dopo, eventuale REM.

Nessuno di questi item è bloccante per la ripresa dello sviluppo su `OCOR-DEV-0048`; sono
irrobustimenti/chiarimenti latenti, non regressioni.

## 7. Addendum — remediation implementate (2026-09-15)

Su mandato esplicito del Product Owner ("procedi autonomamente come consigliato"), i tre
finding correggibili in autonomia sono stati implementati come change set di remediation
governati (TDD RED→GREEN, gate locali verdi, `inputs/` invariato, fence probatorio
invariato). Sono **candidati** — non sigillati: il seal e il merge restano subordinati a
verifica indipendente e CI verde sull'HEAD esatto.

| Change set | Finding | File | TDD (RED→GREEN) | Assurance |
|---|---|---|---|---|
| `OCOR-DEV-REM-0010` | RVW-01/-02 | `c4/typedb_adapter.py`, `c4/jena_adapter.py` | `a12857a`→`bd1c00e` | `reports/assurance/OCOR-DEV-REM-0010-RCCAD/` |
| `OCOR-DEV-REM-0011` | RVW-04 | `c1/frontend.py` | `75e1ffd`→`a252096` | `reports/assurance/OCOR-DEV-REM-0011-RCCAD/` |
| `OCOR-DEV-REM-0012` | RVW-05 | `scripts/validate_rccad.py` | `da482c5`→`64db341` | `reports/assurance/OCOR-DEV-REM-0012-RCCAD/` |

Gate locali al tip: `verify.py` 14/0, `ruff`, `mypy --strict`, language-policy,
change-scope, `validate_rccad` `PASS_LOCAL_PRECHECK`; suite runtime **778 passed** (era
765; +13 test REM) con i soli residui dipendenti da Docker (`NOT EXECUTED` in locale,
validati in CI). I fix `RVW-01/-02` sono no-op per gli input URN/digest dei chiamanti
sigillati, quindi non alterano le suite reali C4.

**Non** implementati (restano riservati, richiedono chiarimento normativo prima di
qualunque intervento): `RVW-03` (semantica break-glass C6), `INFO-A` (idempotenza C5),
`INFO-C` (thread-safety delle classi di riferimento).

Nota d'integrazione: il check CI `ocor-delivery-activation` che invoca
`validate_ocor_change_scope --branch` fallisce unicamente perché il nome branch
`cursor/…` non corrisponde al pattern governato (`task/`/`governed/`); i gate sostanziali
(rccad, poc-ci, regressione runtime, language policy) validano il contenuto. Il merge
avviene via branch `governed/`, come per la PR #126.
