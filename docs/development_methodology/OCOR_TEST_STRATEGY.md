# OCOR test strategy

## TDD evidence protocol

Per logica deterministica: test RED prima del codice con fingerprint del fallimento;
GREEN con minima implementazione; regression mirata; REFACTOR senza variazione di
comportamento; portfolio applicabile completo. L'evidenza JSON registra comando,
exit code, hash del fingerprint e commit. Eccezioni ammesse: generated code,
configurazione dichiarativa, migrazioni e spike disposable; restano obbligatori test
di validazione/accettazione e motivazione nel compliance ledger.

Per comportamento esistente non coperto, il primo passo è un characterization test.

## Technique routing

| Surface | Qualifying assurance |
|---|---|
| Canonical kernel | examples, property tests, differential oracle, determinism |
| Schema/public ports | positive/negative branch conformance and compatibility |
| FSM | all transitions, invalid transitions, stateful properties |
| Saga/lease/fence/outbox/deletion | reference model, faults, bounded model checking |
| Service boundary | consumer/provider contract tests |
| Selected backends | pinned real-service integration; mocks never prove conformance |
| Causal/analytical logic | golden data, metamorphic and reproducibility tests |
| Security/memory | authorization, non-interference, retention/deletion/restore, fail-closed |
| IRB/mission thread | ATDD and full end-to-end qualification |

Copertura lineare è diagnostica, non prova. Sono obbligatori requisiti, invarianti,
guard, 44 transizioni, failure codes e rollback. I package critici adottano soglie di
coverage e mutation non regressive definite nel task prima dell'implementazione.

## Skip, quarantine and mocks

Ogni skip condizionale deve essere inventariato, motivato e reso errore nel job
qualificante. Quarantine di test e mock di boundary obbligatori non sono accettabili
come evidenza. I mock possono esercitare soltanto failure handling locale.
