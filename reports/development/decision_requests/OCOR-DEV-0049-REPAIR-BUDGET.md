# OCOR-DEV-0049-REPAIR-BUDGET — OPEN_PO_DECISION_REQUIRED

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
