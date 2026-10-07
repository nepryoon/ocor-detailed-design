# GITHUB-HOSTED-RUNNER-AVAILABILITY — PR #170, runner hosted indisponibile

- Status: `OPEN_EXTERNAL_CONDITION_REQUIRED`; nessuna variazione semantica proposta.
- Osservazione: `2026-10-05T20:48:36Z`; HEAD CI `8e48303e404a78de26f5e58b351ae505f0c9b1cd`.
- PR: https://github.com/nepryoon/ocor-detailed-design/pull/170

## Contesto ed evidenza

La prima esecuzione ha cancellato sette job senza assegnazione di runner; `mandatory-gates` ha rifiutato correttamente risultati `abandoned`. Eseguito un solo rerun dei cinque workflow interessati (run 37368557539, 37368557542, 37368557572, 37368557624, 37368557752). Anche il secondo tentativo ha cancellato `validation-closure`, `supply-chain`, `type-and-lint-gate` e `integration-postgresql`, con zero step eseguiti e annotazione GitHub «The job was not acquired by Runner of type hosted even after multiple attempts». Il check RCCAD è ancora in esecuzione nell’osservazione finale; non dichiarato PASS. Gli altri risultati sono conservati in `EXECUTION_STATE.json.state_sync_ci`. Non è una prova di errore del prodotto o di insufficienza dello stack REM-0017: i job non sono partiti.

Raw observation: `~/.ocor-codex/state-sync-0049-cycle3/ci-final-observation.json`, SHA-256 `72d2fa04f759559764e476608facad3eba93a9009692f5982a73cfea9ac71a59`. Annotazioni del rerun: `ci-retry-annotations.json`, SHA-256 `1fcc2ca6edbb6d546aea792a2145bb249b1fd27b90d44c35f1889637016e410a`. Tentativi: `ci-rerun-once.json`; log prima esecuzione `ci-failed.log`.

## Opzioni e raccomandazione

1. Attendere il ripristino della capacità hosted e rivalidare l’HEAD finale con tutti i 13 check SUCCESS: opzione raccomandata, nessuna nuova decisione architetturale o spesa.
2. Se il blocco persiste, sottoporre al Product Owner una proposta separata di capacità CI alternativa e del relativo budget/scope; nessuna modifica di runner o acquisto eseguita qui.

Nessun terzo rerun nelle medesime condizioni, nessun bypass, `--admin`, esclusione o modifica di workflow/ruleset/soglie. La nuova scrittura documentale registra il blocco; eventuali run automatici sul commit di handoff non costituiscono un merge autorizzato né un PASS.

## Impatto

PR #170 aperta, state sync non mergiato; `origin/main` resta 25ee8e3bea7cf5e88630df06cb44a2fc35159494. Bloccata solo l’integrazione soggetta a questi check. La riparazione 0049 resta a Claude Code, ciclo 4 da 02ac643eb3c770361f2f1b67eb0f4ab2bc049097, verifier Codex. Lo stop `TERMINAL_BLOCKED` del loop deriva dalla decisione OCOR-DEV-0049-REPAIR-CLAUDE-AUTO; 0050 resta pronto. E1/E2/Verified, inputs e tutti i claim NO-GO invariati.

## 2026-10-06 — Aggiornamento al verdetto ciclo 4

HEAD precedente PR #170 `c1efbfd7f348036673f9c34419f62b3edfdace78`: solo contract SUCCESS, gli altri check richiesti CANCELLED. Confermata l’annotazione hosted-runner indisponibile del check RCCAD con zero step. Osservazione raw `~/.ocor-codex/state-sync-0049-cycle4/ci-before.json`, SHA-256 `316cba9f1f97d697d2643e934c9c0b354adae04baa24e9a5658c3cfe9d5fbe8b`; annotazioni `ci-before-annotations.json`, SHA-256 `09671db917abb658e0e25d2db8d13070debb441f3d7c2bd1dcb3e78731d3dfa0`. Nessun nuovo rerun.

La riparazione ciclo 4 ha prodotto NO_GO (`OCOR-DEV-0049-aefabf91777d-4`); l’ultimo ciclo 5 resta autorizzato a Claude Code da `aefabf91777d311b95cad0c60de0ffa61357ea19`, verifier Codex. Lo state sync dei cicli 3/4 resta su PR #170; il suo eventuale merge richiede i check verdi sull’HEAD finale. Nessuna variazione di capacità/risorse a pagamento o workflow.

## 2026-10-06 — Condizione esterna risolta

Status corrente: `RESOLVED_EXTERNAL_CONDITION`. Nessuna decisione PO o variazione di runner/budget è stata necessaria. Tutti i 13 check richiesti SUCCESS su PR #170 HEAD `bda5fb1294398c43f0ee37b915896e669c1745f0` (osservazione `2026-10-06T00:03:28.126548Z`, run 37391068857, 37391068870, 37391068871, 37391069169, 37391069581, 37391070279). Raw `~/.ocor-codex/state-sync-0049-cycle4/ci-source-green.json`, SHA-256 `a62916010830d4689c8c6522268550c0a804357a0daad89bfb6a60417e901769`. Le osservazioni precedenti restano storiche. Il nuovo commit finale documentale richiede nuovi check verdi sull’HEAD esatto prima del merge; non è ancora dichiarato integrato in questa scrittura. Il passaggio a Claude Code ciclo 5 resta obbligatorio.
