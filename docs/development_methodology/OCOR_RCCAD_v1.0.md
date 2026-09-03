# OCOR-RCCAD v1.0

## Status and scope

`DEC-210` adotta Risk-Driven, Contract-First, Continuous-Assurance Development come
raffinamento esecutivo del lifecycle approvato G0–G7. Non cambia IRB, ADD, LLD,
decisioni architetturali, tecnologie obbligatorie o semantica dei gate.

## Normative precedence

IRB approvato → ADD approvato → LLD approvato → decisioni approvate → contratti,
schema e registri normativi → piano/backlog approvati → RCCAD → implementazione →
interpretazione fail-closed. Ogni conflitto è registrato nell'iteration log; una
variazione semantica richiede una nuova decisione governata.

## Iteration protocol

1. Rileggere istruzioni, manifest, digest normativo, execution state e handoff.
2. Verificare HEAD, worktree, evidenze, CI e blocker senza fidarsi di report stantii.
3. Selezionare esattamente un task pronto o una singola ipotesi di rischio.
4. Creare branch/worktree isolato e criteri positivi, negativi e di rollback.
5. Eseguire RED, GREEN e REFACTOR dove il comportamento è deterministico.
6. Applicare ATDD, contract, property/model-based, fault e real-backend test secondo
   `OCOR_TEST_STRATEGY.md`.
7. Eseguire regression, security e architecture fitness functions.
8. Far verificare diff ed evidenza da un contesto indipendente; l'accordo non
   sostituisce la prova eseguibile.
9. Correggere ogni finding bloccante, sigillare gli hash e aggiornare stato/handoff.
10. Integrare solo su gate verdi e selezionare automaticamente il prossimo task.

## Risk-first walking skeleton

Il coordinatore identifica nel DAG il minimo insieme di rischi abilitanti. Appena
chiuso, consegna una thin vertical slice C1–C8; spike indipendenti continuano senza
bloccare il cammino se le dipendenze lo consentono. Il codice di spike è eliminabile e
non entra nei path di produzione senza reimplementazione o qualifica completa.

## Evidence fence

Piani, review, mock, skip e sostituti non producono conformance. Ogni controllo non
eseguito è `NOT_EXECUTED`. L'adozione RCCAD mantiene `E1=0`, `E2=0`, zero requisiti
globalmente `Verified` e tutti i `NO-GO` correnti.
