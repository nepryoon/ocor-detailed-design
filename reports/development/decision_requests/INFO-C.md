# Decision request — INFO-C (thread-safety classi in-memory)

- **Status**: `OPEN_PO_DECISION_REQUIRED` (non bloccante)
- **Fonte**: `reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md` (osservazione INFO-C)

## Contesto

Classi in-memory (`c5/operations.py` backpressure RMW, `c8/tool_runtime.py` finestra
TOCTOU sullo stop, stato in-memory di `c5/backbone.py`) presentano finestre di race solo
sotto accesso multi-thread. Il requisito di thread-safety per queste classi di
riferimento non è confermato (le vie reali passano da Kafka/backend).

## Opzioni

1. **Lasciare invariato** — nessun requisito di thread-safety confermato.
2. **Introdurre thread-safety** — richiede conferma normativa del requisito e un REM
   dedicato.

## Raccomandazione motivata

Raccomando l'opzione 1 finché il requisito di thread-safety non è confermato in LLD.
L'opzione 2 è una variazione di comportamento approvato, quindi riservata.

## Impatto

Nessuno sul flusso previsto; eventuale hardening futuro della concorrenza in-memory.

## Task bloccati

Nessuno.
