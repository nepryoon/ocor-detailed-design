# OCOR Definition of Done

Un task è `DONE` soltanto se tutte le condizioni applicabili sono vere:

- criteri positivi, negativi e rollback sono eseguibili e verdi;
- evidenza RED/GREEN/REFACTOR esiste o l'eccezione ammessa è motivata;
- traceability normativa punta a codice, test ed evidenza immutabile;
- integrazioni obbligatorie usano servizi reali pinned;
- fitness, security, recovery e regression gate passano senza skip qualificanti;
- il verifier indipendente non lascia finding bloccanti;
- documentazione, procedure operative, backlog, state e handoff concordano;
- evidenza machine-readable contiene commit, ambiente, comandi, risultati e hash.

La piattaforma è `COMPLETE` soltanto con G0–G7 chiusi, BA01–BA08 e FGM01–FGM20
qualificati, 44 transizioni coperte, mission thread completo, 285 requisiti tracciati a
evidenza passante, memoria/deletion/recovery qualificate, zero critical/high aperti,
riproduzione clean-environment e final verifier indipendente. In assenza di una sola
condizione, i claim restano `NO-GO`.
