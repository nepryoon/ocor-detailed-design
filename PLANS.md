# OCOR execution plans

`docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json` resta il backlog
autoritativo e `docs/development_plan/OCOR_DEPENDENCY_DAG.mmd` resta il DAG
autoritativo. Questo file non duplica task o stato.

L'esecuzione è governata da `OCOR-RCCAD v1.0` e riprende da
`reports/development/EXECUTION_STATE.json`. Per ogni iterazione: riconciliare HEAD e
gate, selezionare un solo task dependency-ready, lavorare in un branch/worktree
isolato, produrre evidenza RED/GREEN/REFACTOR o la relativa eccezione, far verificare
il change set in contesto indipendente e integrare soltanto con tutti i gate verdi.

Ordine di lettura: `AGENTS.md`, `docs/development_methodology/methodology.json`,
execution state, model handoff, backlog task e riferimenti normativi associati.

Stato probatorio globale: `E1=0`, `E2=0`; runtime conformance, PoC-GO e Production
readiness restano `NO-GO` finché i rispettivi gate governati non sono chiusi.
