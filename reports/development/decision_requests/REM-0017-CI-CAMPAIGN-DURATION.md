# REM-0017-CI-CAMPAIGN-DURATION

Status: OPEN_PO_DECISION_REQUIRED (non bloccante per run entro il tetto vigente).

## Contesto e misura

La decisione `REM-0017-CI-CAMPAIGN-BUDGET` del 2026-10-07 impone una nuova
richiesta quando una FULL supera 60 minuti; il tetto resta 75 minuti.
Il 2026-10-08T13:41:40Z, il run GitHub Actions `37778117899`, job
`conditional-infrastructure-0049`, sullo SHA sorgente
`fe82366151c424c7f5b51e994ef7c585d6920763`, mostra lo step FULL del candidato
immutabile `df444af855e884d7783612b302e008b90105fe13` ancora in corso:
inizio step 12:39:26Z, durata osservata 3734 s (62m14s).
È una misura dello step tuttora attivo, non un risultato finale o un PASS
pytest. La durata della campagna e i conteggi finali saranno acquisiti dal raw
artifact appena disponibili. Osservazione API conservata nel raw del candidato
REM; nessun incremento di E1/E2/Verified o claim.

La campagna locale iniziale del medesimo candidato è durata 2463.71 s, con
1490 PASS, 1 FAIL e zero skip. È fallita nel job Helm durante un SIGSEGV e
riavvio di containerd nel nodo kind, documentato a 13:15:00Z; non qualifica
il REM. Dopo diagnosi e teardown è stato avviato un solo retry con stack
ricreato e supervisore che osserva anche containerd/kubelet dentro i nodi
OCOR. Questo controllo non cambia il codice né l'evidenza sigillata di 0049.

## Opzioni e raccomandazione

1. Conservare 75 minuti e ottimizzare soltanto provisioning/esecuzione entro
   DEC-211, senza cambiare versioni, tecnologie, casi o criteri. Raccomandata:
   acquisire prima durata finale, risorse e teardown della campagna osservata.
2. Autorizzare una futura variazione del budget soltanto con una decisione
   esplicita, dopo misure riproducibili. Nessuna variazione è eseguita ora.

## Impatto

Nessun test viene escluso, saltato, deselezionato o marcato. La soglia resta
4500 s; su restart/OOM il supervisore interrompe e raccoglie diagnostica.
Un run oltre il tetto o non verde non qualifica REM-0017. La richiesta non
blocca G5; l'integrazione del REM e di 0049 richiede comunque campagne valide,
verifica indipendente e CI verde sull'HEAD esatto. Nessun ciclo9 di 0049.

## Esito acquisito del primo run sorgente

Il raw artifact `ocor-conditional-0049-b31ebdab58d077274e9534bbf3cd5d4aad5b51ed`
(artifact ID11553834543, run37778117899, PR head fe823) riporta durata FULL
**4200.959 s (70m01s)**, `po_decision_required=true`,1491 PASS e zero
FAIL/ERROR/skip. JUnit:0048=196 casi,0049=390 casi; teardown senza
container,volumi o reti residui. Hash SHA256 campaign_result.json: `b37995903b1e24dbcd3b47696b4da98658a4aef2dd41025433bb8e93333c0db3`.
La richiesta resta OPEN: il run è entro75 minuti ma oltre60. Il verde
di questa sorgente non qualifica le successive modifiche del ricevitore
e del monitor Kubernetes; è necessaria la CI dell'HEAD finale.

## Misura aggiuntiva 2026-10-09 — HEAD `bc811afc2bc30023cd64051a638c632263760ecc`

Run `37799916094` (OCOR governance and validation closure, PR169), job
`conditional-infrastructure-0049`: step FULL del candidato immutabile
`df444af855e884d7783612b302e008b90105fe13` 15:23:00Z–16:36:47Z; artifact
`ocor-conditional-0049-aac82eacc7dd8c52b81f65713ab4bbef705979a8` (ID
11563824886), `campaign_result.json` SHA256
`5e8b1cba4780efaf21c9b28ecd72e4f7eb6a8644d7fdfe8f01f3ccf363e76fdb`:
`status=PASS`, 1491 test, zero failure/error/skip, durata **4425.920 s
(73m46s)**, `po_decision_required=true`. Margine sul tetto vigente di 4500 s:
74 s. Le due misure CI disponibili (4200.959 s e 4425.920 s) crescono e
restano entro il tetto ma oltre i 60 minuti: la richiesta resta OPEN.
Nessun tetto modificato, nessun caso escluso o saltato. Un run CI che superi
4500 s è FAIL e non qualifica REM-0017; in quel caso si registra la misura
e si prosegue con il lavoro G5 pronto, senza aumentare il budget.
Registrato da Claude Code (implementatore di riserva del loop).
