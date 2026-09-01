# OCOR Autonomous Development Activation Report

## Verdict finale

La baseline di planning è integrata e `OCOR-DEV-0001` è `COMPLETE`. Tutti i gate
controllabili localmente e i due sealing check della PR #11 sono `PASS`. Il verdetto
è `ACTIVATION COMPLETE — EXTERNAL PROTECTION BLOCKER`: la protezione effettiva di
`main` resta `BLOCKED_EXTERNAL_AUTHORITY` per il piano GitHub corrente.

Questo referto non stabilisce runtime conformance, E1, E2, PoC-GO o Production
readiness. Non è stato eseguito alcun task successivo a `OCOR-DEV-0001`.

## Baseline e PR #10

| Controllo | Risultato | Evidenza |
|---|---|---|
| PR di planning | `MERGED_AND_VERIFIED` | PR #10, head `e7b8c976ed4261c7b7cbf330409d4a09fac18db5` |
| CI di planning | `PASS` | run `33555053000`, job osservato `validation-closure` |
| Merge su `main` | `PASS` | `dd4ff9ddb3009f1fc9ad7aea06807a83145c63bc` |
| Diff non autorizzato | `0` | nessuna modifica runtime, `inputs/`, ADD o LLD nella PR #10 |
| Planning validator | `PASS` | 37 `PASS`, 0 `FAIL`; i due tool opzionali erano storicamente `NOT_EXECUTED` |

## OCOR-DEV-0001

| Acceptance criterion | Risultato | Evidenza |
|---|---|---|
| `inputs/` e baseline approvate immutabili | `PASS` | tree prima/dopo `60a73de8e47b38e94aeb0e2b8dedc689fab6eb35` |
| Identificativi del task ledger stabili | `PASS` | `validate_ocor_change_scope.py`; 69 task unici e ordinati |
| Fixture negativa su `inputs/` rifiutata | `PASS` | `test_immutable_path_guard_rejects_negative_fixture` |
| `SKIPPED`/`UNAVAILABLE`/`NOT_EXECUTED` non promossi | `PASS` | test parametrico del runner e validatore evidenze |
| Ownership e isolamento worktree | `PASS` | collision test, `.ocor/` esclusa da Git, branch `task/<ID>-<slug>` |
| Retry e recovery limitati | `PASS` | budget massimo 2; recovery non riapre retry esauriti |
| Gate e dipendenze | `PASS` | schema, DAG aciclico, hard/soft ordering e gate barrier |
| Red CI impedisce la promozione del runner | `PASS` | test `test_red_ci_and_absent_required_context_block_promotion` |
| Manifest task content-addressed | `PASS` | `reports/evidence/G0/MANIFEST.json` |

Rollback: arrestare il dispatch; creare revert commit per i commit di attivazione;
ripristinare lock e workflow precedenti; rieseguire i manifest precedenti. Non sono
presenti migrazioni dati.

## Baseline Python e PostgreSQL

La collection failure è stata riprodotta con `uv sync --frozen --extra test`:
`ModuleNotFoundError: psycopg`. La causa era la divergenza tra `pyproject.toml` e la
workflow, che installava separatamente `psycopg[binary]==3.2.10`. Il test extra ora
contiene `psycopg[binary]==3.2.10` e `rdflib==7.1.4`; `uv.lock` è aggiornato e la
workflow usa solo il sync frozen.

Servizio qualificante locale: immagine
`postgres:16@sha256:33f923b05f64ca54ac4401c01126a6b92afe839a0aa0a52bc5aeb5cc958e5f20`,
server PostgreSQL `16.14`. Risultati:

- suite PostgreSQL: 5 `PASS`, 0 `FAIL`, 0 `SKIPPED`, 0 `NOT_EXECUTED`;
- suite completa: 129 `PASS`, 0 `FAIL`, 0 `SKIPPED`, 0 `XFAIL`, 0 `NOT_EXECUTED`;
- collection errors: 0.

Questi risultati sono regression e activation evidence; non sono evidenza di runtime
conformance globale.

## Markdown e Mermaid

- `markdownlint-cli2 0.18.1` (`markdownlint 0.38.0`): 6 file, 0 errori, `PASS`.
- `@mermaid-js/mermaid-cli 11.12.0`: DAG renderizzato, digest SVG temporaneo
  `46122760912c3508ce2c605b21c025ccae133f0eb520653a4358a53c3ea6735c`, `PASS`.

Il primo render Mermaid ha rilevato il blocco AppArmor dei namespace Chromium. Il
secondo tentativo ha usato `--no-sandbox` esclusivamente nel renderer usa-e-getta;
nessun controllo repository, CI o runtime è stato indebolito.

## Protezione di main

L'identità GitHub `nepryoon` dispone di permission `admin`, ma il repository è
privato e GitHub risponde HTTP 403 sia per classic protection sia per rulesets:
`Upgrade to GitHub Pro or make this repository public to enable this feature.`
La query read-only di `branches/main` conferma `protected=false` e nessun required
check effettivo. Il contesto osservato dalla CI verde è `validation-closure`; non sono
stati inventati nomi di check.

Stato: `BLOCKED_EXTERNAL_AUTHORITY`. Comando di continuazione dopo l'abilitazione
della funzione sul piano GitHub:

```bash
gh api --method PUT repos/nepryoon/ocor-detailed-design/branches/main/protection \
  --input reports/planning/OCOR_MAIN_PROTECTION_REQUEST.json
```

La request è materializzata in `OCOR_MAIN_PROTECTION_REQUEST.json` con i soli
contesti effettivamente osservati: `delivery-activation` e `validation-closure`.
Il runner consente push e PR espliciti; il merge resta disabilitato e viene comunque
rifiutato quando `main` non è protetto.

## Runner persistente

Il runner è `scripts/ocor_autonomous_delivery.py`. Il default è read-only e
non crea state. Le mutazioni richiedono `--execute`; push, PR e merge richiedono
anche opt-in distinti e configurazione abilitata. Lo state volatile e resumable è
`.ocor/delivery/state.json`, escluso da Git.

Copertura del subset runner: 20 `PASS`. Sono verificati parsing/schema, DAG cycle,
dependency readiness, gate barrier, retry exhaustion, recovery, ownership collision,
dry-run non mutante, red CI, risultati non eseguiti, stop-after-task e
stop-after-gate. Il dry-run reale seleziona senza mutazioni
`OCOR-DEV-0002` e `OCOR-DEV-0004`; `--next` restituisce `OCOR-DEV-0002`.
Nessuno dei due è stato eseguito.

## Evidenza e comandi

```bash
uv sync --project ocor-runtime --frozen --extra test
OCOR_LIVE_POSTGRES_DSN='postgresql://ocor:ocor@127.0.0.1:55432/ocor' \
  uv run --project ocor-runtime --frozen pytest -q ocor-runtime/tests/
uv run --project ocor-runtime --frozen pytest -q \
  ocor-runtime/tests/tasks/test_ocor_dev_0001.py
ocor-runtime/.venv/bin/python scripts/ocor_autonomous_delivery.py --validate
ocor-runtime/.venv/bin/python scripts/ocor_autonomous_delivery.py --dry-run
ocor-runtime/.venv/bin/python scripts/ocor_autonomous_delivery.py --next
ocor-runtime/.venv/bin/python scripts/validate_runtime_evidence.py \
  --task OCOR-DEV-0001 --non-skipped --manifest reports/evidence/G0/MANIFEST.json
```

Il commit valutato dal manifest è
`8599c2426819d5b614e193fe9a8f97431a97dee8`. La PR di attivazione è
`https://github.com/nepryoon/ocor-detailed-design/pull/11`; i run verdi osservati
del primo ciclo sono `33558417453` e `33558417500`; i sealing run verdi sono
`33558754033` (`validation-closure`) e `33558753936`
(`delivery-activation`). Il final material commit è
`a2150bebb48b6240e3ae96324907584ed3a4c9d4`.
