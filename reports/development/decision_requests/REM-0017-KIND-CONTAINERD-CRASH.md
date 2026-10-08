# REM-0017-KIND-CONTAINERD-CRASH

Status: OPEN_PO_DECISION_REQUIRED — limitata a un eventuale cambio del profilo
qualificante/immagine o a modifiche di 0049; diagnosi entro DEC-211 resta autonoma.

## Evidenza riproducibile e confine del blocco

Nel candidato immutabile `df444af855e884d7783612b302e008b90105fe13`, sul nodo
`kindest/node:v1.33.1@sha256:050072256b9a903bd914c0b2866828150cb229cea0efe5892e2b644d5dd3b34f`,
containerd è terminato due volte con `code=dumped, status=11/SEGV`:

- 2026-10-08T13:15:00Z: prima FULL locale,1490 PASS/1 FAIL/zero skip,
  errore del job backup manuale Helm (seal255), containerd riavviato alle13:15:01Z.
- 2026-10-08T14:59:57Z: nuova FULL dopo reset/bootstrap/health,1379 PASS
  parziali e112 casi NOT_EXECUTED. Journal: RunPodSandbox del backup manuale,
  EOF CRI e SIGSEGV; riavvio systemd alle14:59:58Z. Il nuovo supervisore ha
  sospeso immediatamente il gruppo pytest posseduto, acquisito statistiche/journal
  e interrotto la campagna. Non è un PASS. Teardown senza risorse OCOR residue.

Un ulteriore run intermedio è stato interrotto a1379 PASS per un errore del
supervisore sulla normale inizializzazione kubelet (PID241->749,NRestarts0,
stop pulito prima del collegamento alla retebootstrap). Quel difetto è corretto
con casi positivi/negativi; il monitor mantiene il rigetto dei crash anche durante
l'avvio e dei cambi PID/ActiveState dopo l'ammissione. Non viene confuso col SIGSEGV.

La FULL del branch REM sul codice finale ha1101 PASS/zero skip/error/fail,
424.337s. Il primo HEAD CI sorgente `fe82366151c424c7f5b51e994ef7c585d6920763`
ha13/13 check verdi: il candidato ha1491 PASS/zero skip in4200.959s,196 casi0048
più390 casi0049, teardownzero. È evidenza sorgente storica, non dell'HEAD successivo.
La causa profonda del SIGSEGV non è stabilita: non è provata una responsabilità
del prodotto, della concorrenza dei backup, né una specifica correzione upstream.
Journal, JUnit, transizioni runtime e raw log con hash sono nel record WIP
`reports/assurance/OCOR-DEV-REM-0017-RCCAD/repair-1-archive.json` e relativo `.log`.
Il journal conservato documenta il segnale; non è un backtrace completo del core.

## Opzioni e raccomandazione

1. Diagnosi bounded nel solo ambiente disposable: riproduttore del sandbox/backup
   e acquisizione del backtrace prima del teardown; tentare soltanto configurazioni
   dentro DEC-211 con le stesse versioni e gli stessi byte approvati. Questa parte
   non richiede nuova autorizzazione, ma nessun run fallito è qualificante.
2. Se serve un'immagine/versione diversa del nodo/runtime, autorizzare esplicitamente
   un change set governato separato e la sua riqualifica, senza sostituire tecnologie
   né indebolire i criteri. Nessun nuovo valore del lock o override è eseguito ora.
3. Se la correzione richiede modificare 0049, occorre una nuova decisione:
   il ciclo8 è concluso e il mandato corrente vieta un ciclo9.

Raccomandazione: prima diagnosi1, poi eventuale decisione2 fondata su backtrace e
confronto di ambienti. Nessuna ripetizione della FULL nelle stesse condizioni.
Non aumentare75/45 minuti, escludere casi o trattare restart/OOM come tollerati.

## Impatto e lavoro pronto

REM-0017 resta OPEN/WIP e non si richiede il sigillo con qualifica locale incompleta.
PR169draft e PR176 restano aperte; il GO indipendente già acquisito per0049 non
viene riscritto. G6/G7 e integrazione0049 restano soggetti alle dipendenze esistenti.
G5 è pronto:0050 e successivi raggiungibili possono proseguire. La riacquisizione
locale Fuseki già autorizzata resta un'unità governata distinta dopo il Dockerfile.
E1=0,E2=0,zero Verified; nessuna modifica inputs/ o promozione di claim.
