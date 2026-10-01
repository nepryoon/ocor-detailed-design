# Decision request — RVW-03 (BreakGlass authorize re-validation)

- **Status**: `OPEN_PO_DECISION_REQUIRED` (non bloccante)
- **Fonte**: `reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md` (finding RVW-03)

## Contesto

`c6/safety.py` `BreakGlassController.authorize` (~righe 270–282) non ri-valida gli
`approvers` contro `IdentityRegistry`; il doppio controllo è presente soltanto in
`grant()`. Il `grant` è l'artefatto già autorizzato: ripetere la validazione all'uso
sarebbe difesa-in-profondità, non un requisito dell'architettura approvata.

## Opzioni

1. **Lasciare invariato** — `grant()` resta l'unico punto di doppio controllo; nessun
   cambio semantico a C6.
2. **Ri-validare in `authorize()`** — difesa-in-profondità aggiuntiva, richiede conferma
   normativa (variazione semantica della semantica break-glass approvata).

## Raccomandazione motivata

Raccomando l'opzione 1 (nessun intervento) finché non arriva una conferma normativa
esplicita in LLD: la semantica C6 è approvata e `grant` è l'artefatto autorizzato.
L'opzione 2 è legittima ma è una variazione di comportamento approvato, quindi riservata.

## Impatto

Difesa-in-profondità sul break-glass C6; nessun task del backlog dipende da questa
decisione.

## Task bloccati

Nessuno.
