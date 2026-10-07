# OCOR-DEV-0049-REPAIR-BUDGET — RESOLVED_BY_PO_DECISION

## Contesto

Il verdetto `OCOR-DEV-0049-b40aa8a6908b-5` del 2026-10-06 è `NO_GO` sull’HEAD
`b40aa8a6908b02d95cdf8138200f99f2e8aea8b1`. Il ciclo 5, interrotto e ripreso secondo
STACK-HYGIENE, è concluso ed esaurisce tutti i cicli autorizzati. Nessuna sesta riparazione
è autorizzata. Dettagli, fingerprint del verdetto e controlli non eseguiti nel record
`reports/development/OCOR_DEV_0049_ESCALATION.md` e nello stato.

## Diagnosi e opzioni

1. Conservare 0049 bloccato e proseguire con REM-0017, poi 0050 e i task pronti indipendenti.
2. Nuovo mandato PO circoscritto a VF-001 del ciclo 5 e riqualificazione integrale; l’agente non
   lo presume né lo esegue. La creazione concorrente dello snapshot sul Qdrant pinned può dare
   HTTP 500: serve retry bounded o serializzazione, fail-closed e teardown, test deterministico
   del ramo e positivi/negativi real-backend. VF-002 richiede ambiente con extra test e lint.

## Raccomandazione e impatto

Conservare subito il blocco di 0049; priorità operativa REM-0017 come già decisa. Un’eventuale
ripresa di 0049 richiede decisione PO esplicita e verifica indipendente nuova, senza indebolire
alcun criterio. Bloccati 0049 e transitivamente 0059 e tutti i task 0060–0069 (chiusura del DAG ricalcolata). REM-0017 resta
prerequisito di tutto G6; 0050 resta pronto.

Implementatore riparazioni: Claude Code (Anthropic). Verifier finale: Claude Code
(claude-opus-5-5), fallback autorizzato del 2026-10-06, stesso modello delle riparazioni in
processo e contesto separati. Implementazione originale di un altro modello; implementatore
loop Codex (OpenAI). Nessuna sigillatura o promozione di E1/E2/Verified/claim.

## 2026-10-07 — RESOLVED_BY_PO_DECISION; ciclo 6 concluso

Il mandato `OCOR-DEV-0049-REPAIR-6` del 2026-10-07 risolve la richiesta precedente autorizzando un solo sesto ciclo Claude Code da b40aa8a6908b02d95cdf8138200f99f2e8aea8b1. Le sezioni precedenti descrivono il contesto storico del ciclo 5, non lo stato corrente.

Il verdetto `OCOR-DEV-0049-d0ac80a9d1d6-6` (d0ac80a9d1d603ca19ddbb2d5291e252b3d6ae2b, SHA-256 934e0f032daa67c0f6abee6e379c4569c0394c5e3b0c28dce05d799c005fc18c) è NO_GO: VF-001 medium bloccante per ordinamento seal/replay divergente dei tombstone; VF-002 low per copertura positiva journal-ahead. Nessun ciclo 7 autorizzato. Il task resta bloccato per budget; non viene chiesto implicitamente un nuovo ciclo. La decisione impone CONTINUE con REM-0017, poi 0050 e task indipendenti. Un futuro mandato PO è condizione necessaria soltanto per riaprire 0049. Dettagli ed esiti NOT_EXECUTED conservati nell’escalation.

Riparazioni e verifier: Claude Code in processi/contesti separati (stesso modello; fallback); loop implementatore Codex. Nessuna sigillatura o promozione di claim.
