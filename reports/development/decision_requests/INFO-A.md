# Decision request — INFO-A (idempotenza C5)

- **Status**: `OPEN_PO_DECISION_REQUIRED` (non bloccante)
- **Fonte**: `reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md` (osservazione INFO-A)

## Contesto

`c5/backbone.py` usa uno short-circuit «solo chiave» per il replay identico richiesto
da `test_a_replayed_idempotency_key_is_a_safe_no_op_...`. Rilevare il conflitto «stessa
chiave / payload diverso» (come fa C3) sarebbe un invariante più forte, oggi non
richiesto.

## Opzioni

1. **Lasciare invariato** — comportamento intenzionale documentato; nessun cambio.
2. **Irrobustire** — rilevare «stessa chiave / payload diverso» come conflitto (invariante
   più forte, da decidere in sede normativa).

## Raccomandazione motivata

Raccomando l'opzione 1 (nessun intervento) in assenza di un requisito normativo che
imponga l'invariante più forte. L'opzione 2 è una variazione semantica e va confermata.

## Impatto

Nessuno sul flusso previsto; eventuale irrobustimento futuro dell'idempotenza C5.

## Task bloccati

Nessuno.
