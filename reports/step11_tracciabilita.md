# STEP 11 — Tracciabilità e scope fence

## Esito sintetico

La copertura **numerica dei registri** è completa e riproducibile: l'universo core contiene esattamente 693 identificativi e registri/indici contengono tutte le righe attese senza definizioni duplicate. La matrice ADD §7 alloca tutti gli `ARC`, `BR`, `FR`, `NFR`, `ELM` e `RSK`, 25/26 `CAP` e 181/196 `DEC`. `CAP-026` è esclusa esplicitamente. Delle quindici `DEC` non allocate, tredici sono effettivamente gate/processo; `DEC-173` e `DEC-175` sono invece decisioni sostantive e restano orfane dalla matrice.

La copertura numerica non equivale però a copertura semantica. Il controllo puntuale rileva:

1. una contraddizione della baseline approvata fra `DEC-103`/`FR-095` (`P0/PoC`) e il differimento di `ELM-070` congelato da `DEC-196` e riprodotto dall'ADD: la sola istanza positiva della capability controfattuale è sempre respinta come `CAPABILITY_DEFERRED`;
2. una formulazione di scope introdotta in v1.1 che chiama «differiti» requisiti in realtà `Confermato` con release MVP/Production e afferma, contro `NFR-078`, che nessun `P0` con `DEVE` è differito;
3. due decisioni vincolanti sostantive, `DEC-173` e `DEC-175`, classificate erroneamente come gate e non allocate ad alcun subsystem;
4. un conteggio errato nell'Amendment Log: `AM-13` dichiara 182/196 `DEC`, mentre matrice ed harness danno 181/196.

Lo stato probatorio resta invariato: `E1=0`, `E2=0`, zero requisiti `Verified`. Nessun controllo documentale qui eseguito incrementa l'evidenza.

## Metodo e fonti

Controlli read-only eseguiti su:

- `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md`;
- `OCOR_Requirement_Register_v0.9.md` e `OCOR_Requirement_Traceability_Index_v0.9.md`;
- `OCOR_Decision_Register_v1.0.md` e `OCOR_Decision_Traceability_Index_v1.0.md`;
- `OCOR_Registers_v0.9.md`;
- `OCOR_CAP_ELM_Requirement_Crosswalk_v0.9.md`;
- `reports/verify_report.json`.

Sono stati verificati: progressivi e unicità delle righe primarie; riferimenti fuori range; espansione dei range §7; corrispondenza registro/indice; inversione bidirezionale requisito↔`CAP`/`ELM`; presenza di fonte, acceptance, metodo, stato e release; esistenza degli `EV-*`; trattamento dei rischi; coerenza semantica del fence §1.5/§7.1 con decisioni e requisiti.

Il `PASS` del harness in `reports/verify_report.json:92-160` prova presenza e copertura degli ID nella matrice, non la soddisfacibilità semantica di un requisito allocato.

## Integrità dell'universo normativo

| Famiglia | Righe primarie nel registro | Righe nell'indice/crosswalk | Allocate in ADD §7 | Assenze §7 | Esito |
|---|---:|---:|---:|---|---|
| `DEC` | 196 | 196 | 181 | 13 gate/processo; `DEC-173`, `DEC-175` sostantive | `FAIL` |
| `BR` | 18 | 18 | 18 | nessuna | `PASS` |
| `FR` | 174 | 174 | 174 | nessuna | `PASS` |
| `NFR` | 93 | 93 | 93 | nessuna | `PASS` |
| `ARC` | 23 | 23 | 23 | nessuna | `PASS` |
| `CAP` | 26 | 26 | 25 | `CAP-026`, fuori scope | `PASS` |
| `ELM` | 103 | 103 | 103 | nessuna | `PASS` |
| `RSK` | 60 | 60 | 60 | nessuna | `PASS` |
| **Totale core** | **693** | **693** | n/a | n/a | **PASS** |

Non risultano buchi di progressivo, definizioni primarie duplicate o riferimenti core fuori range. Le tre occorrenze di `DEC-197` nell'ADD (`§1.1`, `§8` e `§8.2`) sono negative/prospettiche e non assegnano una decisione.

Le decisioni omesse da §7 sono esattamente `DEC-028`, `DEC-029`, `DEC-037`, `DEC-059`, `DEC-068`, `DEC-088`, `DEC-098`, `DEC-109`, `DEC-121`, `DEC-149`, `DEC-171`, `DEC-173`, `DEC-175`, `DEC-193`, `DEC-196`.

Tredici sono gate, mandato di processo o freeze. Due non lo sono:

- `DEC-173`, Decision Register riga 190, decide le superfici per ruolo e genera `FR-166`/`FR-167`; il Requirement Traceability Index righe 266-267 le alloca a `CLI/IDE`, `Operational UI`, `Admin/Audit UI`, e lo stesso ADD §4.3 riga 2852 traccia `DEC-173` sull'Agent Kernel;
- `DEC-175`, Decision Register riga 192, decide documentazione, onboarding e sandbox e genera `NFR-082`; il Requirement Traceability Index riga 269 la alloca alle stesse superfici.

I requisiti derivati compaiono nella riga §7 «Compiler & Gateway», ma le decisioni vincolanti che ne determinano la soluzione sono assenti. La frase §7 riga 3274 che qualifica tutte e quindici come «decisioni di gate di processo» è quindi falsa. `DEC-173` va allocata almeno ad «Agent Kernel», coerentemente con la tracciabilità già presente in §4.3; `DEC-175` almeno a «Compiler & Gateway», dove `NFR-082` è già allocato, con eventuale sovrapposizione «Programme & Evidence Governance» per il conformance kit.

### Conteggio `DEC` incoerente nel log

- ADD §7, righe 3259-3274, e harness: 181/196 allocate; tredici esclusioni sono motivate, due sono sostantive e non allocate.
- ADD §8, riga 3331, `AM-13`: «`DEC` 129/196 → 182/196».

Il valore riproducibile dello stato corrente è **181/196**. Dopo la necessaria allocazione di `DEC-173` e `DEC-175`, il valore sarebbe **183/196**, con tredici esclusioni di processo. `182/196` non descrive né lo stato corrente né quello corretto e rende inesatta l'evidenza dichiarata per la chiusura di `ARF-013`.

## Requisiti, capability, elementi e rischi

### Requisiti e indici

- 285/285 righe `BR`/`FR`/`NFR` sono presenti una sola volta sia nel Requirement Register sia nel Requirement Traceability Index.
- 285/285 hanno fonte, acceptance, metodo, stato e release non vuoti.
- Gli acceptance criteria e i metodi sono preservati semanticamente nell'indice; le differenze osservate sono solo rimozioni di backtick tipografici.
- Ogni requisito dell'indice è collegato ad almeno una `CAP-*` o `ELM-*` esistente.

### `CAP`/`ELM` e crosswalk

Il crosswalk contiene 26/26 `CAP` e 103/103 `ELM`, ciascuna con almeno un requisito esistente. Le 428 relazioni dirette del crosswalk (141 `CAP`→requisito e 287 `ELM`→requisito) sono tutte presenti nel Requirement Traceability Index.

Per le 103 `ELM` le due viste coincidono esattamente. Per le 26 `CAP`, l'indice aggiunge 950 associazioni contestuali/cross-cutting rispetto alle associazioni dirette del crosswalk, ma non ne elimina alcuna. Non emerge quindi una capability senza requisito o un elemento senza fonte; resta opportuno distinguere in futuro «requisito direttamente realizzante» da «capability contestuale», soprattutto per `CAP-026`, che nell'indice compare come contesto di 34 requisiti ma nel crosswalk ha i quattro requisiti diretti `BR-013`, `FR-021`, `NFR-050`, `NFR-089`.

### Rischi

Le 60 righe `RSK-*` hanno stato, origine e trattamento/mitigazione testuale. Il Decision Traceability Index richiama tutte le 60. La colonna §7 «Rischi mitigati» non promuove il loro stato: il preambolo §7 limita la presenza a un'allocazione di design e §8.2 conserva gli stati del Risk Register. Non risultano rischi senza trattamento né chiusure implicite.

## Verifica rigorosa dello scope fence

| Elemento | Baseline/requirement | Disposizione ADD | Esito |
|---|---|---|---|
| `FR-048` | Requirement Register riga 137: `P2/Deferred`, stato `Differito`, release `Future` | §7.1 riga 3280: profilo non incluso, build → `CAPABILITY_DEFERRED` | `PASS` — differimento esplicito e verificabile |
| hardening `CAP-024` | Crosswalk riga 35: 11 `NFR`; release PoC/MVP/Production distinte | §6.1 riga 3133 e §7.1 riga 3281 enumerano correttamente i cinque `NFR` PoC attivi | `PASS WITH DEFECT` — vedi sotto: `NFR-078` e uso improprio di «differiti» |
| `ELM-011` | `FR-024`, `NFR-019`; `DEC-196` la differisce | §2.4, §3.3, §5.3 e §7.1 disabilitano vector/index/embedding nel PoC | `PASS` — il thin slice non include il profilo vector; nessun claim di supporto |
| `ELM-015` | `FR-024`, `FR-133`, `NFR-042`; `DEC-196` la differisce | §5.1 mantiene il materiale segreto fuori da IR/graph/log/export e fallisce chiuso su reference non risolvibile | `PASS` — il controllo PoC non attiva il profilo semantico completo |
| `ELM-035` | `FR-032` thin slice/MVP completo; `FR-080` PoC | §3.5/§4.1/§7.1 ammettono un solo percorso compensativo bounded e non una Saga generale | `PASS` — la slice PoC è esplicita e non promette Saga completa |
| `ELM-049` | `FR-037` thin slice; `FR-135` Production | §5.3/§7.1 applicano purpose minimo su dati sintetici senza claim compliance | `PASS` — il profilo privacy/retention reale resta correttamente fuori PoC |
| `ELM-070` | `DEC-103` e `FR-095`: controfattuale AAP `P0/PoC`; `DEC-196` la differisce | §4.2 riga 2757 e §7.1 riga 3286 respingono ogni esecuzione positiva come `CAPABILITY_DEFERRED`, pur allocando `FR-086`–`FR-105` | **`FAIL — SOURCE_LIMITATION`** — contraddizione della baseline; l'allocazione sintattica non soddisfa `FR-095` |
| `ELM-080` | `FR-038` PoC thin slice/MVP completo; `DEC-196` la differisce | §4.3.1/§5.2 distinguono budget/quota, `CapabilityLease` e reservation semantica | `PASS` — nessun controllo safety dipende dall'elemento differito |
| `ELM-084` | `DEC-116`, `FR-118`, `FR-119` sono `P0/PoC`; `DEC-196` differisce l'elemento | §4.3.1 usa contesto effimero ricostruibile, senza memoria persistente generale | `PASS WITH CONDITION` — ogni eventuale `MemoryItem` effimero resta soggetto ai campi e ai negative test di `FR-118/119`; la struttura concreta è `DDD_DETAIL`, non autorizzazione a ometterli |
| `ELM-091` | `FR-168` PoC; mapping/migrazione completi in release successive | §7.1 mantiene solo W3C dichiarato e fixture circoscritte, senza equivalenza Palantir | `PASS` |
| `CAP-026` | Crosswalk: requisiti di profile/claim, non replica funzionale completa; `DEC-196` out of scope | §1.5/§7.1: fuori container/release profile e fuori coverage claim | `PASS` |

### `CAP-024`: stato e release non vanno confusi

ADD §6.1 e §7.1 chiamano «differiti» `NFR-060`, `NFR-061`, `NFR-064`, `NFR-074`, `NFR-078` e `NFR-071`. Nel Requirement Register queste righe sono tutte `Confermato`; le prime cinque appartengono a MVP/Production salvo `NFR-071`, che è `P0/PoC` con `DOVREBBE` e valore governato da `OI-008`/`ASM-010`.

In particolare, `NFR-078` (Requirement Register riga 398) è `P0`, usa `DEVE` e ha release `MVP`. Ne consegue che la frase §6.1/§7.1 «senza che ciò differisca alcun requisito P0 con obbligo DEVE» è falsa se letta senza il qualificatore **PoC**. L'intento ricostruibile è non includere il requisito nel profilo PoC, non cancellarne il carattere `P0/MVP`; il testo attuale può però farlo perdere al bootstrap del DDD MVP.

Correzione esatta raccomandata: sostituire «Restano differiti ...» con «Non appartengono al profilo PoC e restano requisiti `Confermato` delle rispettive release: `NFR-060`, `NFR-061` Production; `NFR-064`, `NFR-074`, `NFR-078` MVP. `NFR-071` resta target PoC candidato governato da `OI-008` e `ASM-010`». Qualificare l'ultima frase come «nessun requisito `P0/PoC` con obbligo `DEVE` è differito».

### `ELM-070`: requisito positivo reso ineseguibile

La catena è testualmente precisa:

1. Decision Register riga 120, `DEC-103`: OCOR implementa intervento e controfattuale come operazioni SCM distinte; `FR-095` è `P0/PoC`.
2. Requirement Register riga 229 e Requirement Traceability Index riga 147: `CounterfactualQuery` deve richiedere il factual set e registrare abduction, action e prediction; mapping diretto a `ELM-070`.
3. Crosswalk riga 112: `ELM-070` è realizzata da `FR-035` e `FR-095`.
4. Decision Register riga 218, `DEC-196`: congela contemporaneamente i 284 requisiti `Confermato` e il differimento di `ELM-070`.
5. ADD §4.2 riga 2757 e §7.1 riga 3286: una richiesta completa e positiva viene sempre respinta come `CAPABILITY_DEFERRED`.

Il criterio di accettazione di `FR-095` testa soltanto il caso negativo «factual set mancante». Quel negativo può passare anche se nessun caso positivo è eseguibile. La copertura §7 è pertanto nominale: il requisito resta semanticamente orfano.

La chiusura richiede change control sulla baseline, scegliendo una sola disposizione:

- attivare nel PoC una thin slice AAP con almeno un caso positivo e mantenere `FR-095 P0/PoC`; oppure
- mantenere `ELM-070` differita, riclassificare formalmente `FR-095` fuori PoC e registrare tramite change control una decisione autorizzata che confermi o superseda `DEC-103`/la disposizione congelata da `DEC-196`, senza assegnarne qui l'ID; aggiornare Crosswalk e Requirement Traceability Index.

Il DDD non può scegliere fra le due senza autorità di change control.

## Acceptance criteria ed evidenze

### Completezza strutturale

- 285/285 requisiti hanno acceptance criterion e metodo non vuoti.
- 35/35 `EV-*` esistono nell'Evidence/Experiment Register.
- I 27 `EV-*` citati da ADD §7.2 esistono tutti e sono coerenti per area.
- Ogni riga §7.2 dichiara `NOT RUN — E1=0/E2=0`; nessun test è presentato come già eseguito.

Non risultano evidenze richieste ma inesistenti.

### Criteri non ancora valutabili

Due `NFR P0/PoC` conservano valori `TBD` nei criteri:

- `NFR-007`, Requirement Register riga 54: tolleranza stocastica da determinare;
- `NFR-009`, riga 61: soglie analitiche, portabilità, completezza e performance da determinare.

Entrambe le righe dichiarano owner, metodo e blocco del PoC acceptance gate; quindi l'assenza di valore non è presentata come evidenza né come `PASS`. Tuttavia la frase dello stesso registro a riga 367 — «Nessun NFR usa `TBD` come metrica corrente» — è fattualmente contraddetta dalle due righe. `OI-008` governa le soglie del gate, ma non rende oggi valutabili i due criteri. Classificazione: `SOURCE_LIMITATION`, non finding ADD; devono restare `NOT EVALUABLE` fino al congelamento dei valori.

`NFR-071` è un ulteriore target candidato `P0/PoC`: il valore `p95<50 ms` è scritto nel requisito, mentre `OI-008`/`ASM-010` mantengono aperto il congelamento delle soglie. L'ADD lo tratta correttamente come target, non come risultato osservato; il gate resta non valutabile con `E1=0`.

### Riferimenti non atomici nella sorgente

Il Requirement Register e il relativo indice contengono due shorthand non conformi alla sintassi atomica degli ID:

- riga 343 / indice riga 234: `OI-022/004`;
- riga 347 / indice riga 238: `NFR-065/008`.

I riferimenti verosimilmente intesi sono rispettivamente `OI-022`, `OI-004` e `NFR-065`, `NFR-008`, tutti esistenti. La seconda metà non è però risolvibile da un parser di ID. Classificazione: `MINOR`, `SOURCE_LIMITATION`; normalizzare in due ID completi separati.

## Finding candidati per la riconciliazione

| ID locale | Severity | Confidence | Locator | Disposition | Finding | Impatto | Remediation esatta |
|---|---|---|---|---|---|---|---|
| `S11-01` | `BLOCKER` | `HIGH` | Decision Register `DEC-103` riga 120 e `DEC-196` riga 218; Requirement Register `FR-095` riga 229; Crosswalk `ELM-070` riga 112; ADD §4.2 riga 2757, §7.1 riga 3286 | `SOURCE_LIMITATION` | La baseline congela simultaneamente `FR-095 P0/PoC` e il differimento della sola capability che lo realizza; l'ADD alloca il requisito ma respinge ogni caso positivo. | Il DDD dovrebbe decidere senza autorità se implementare AAP nel PoC o violare un requisito P0; una suite solo negativa darebbe un falso `PASS`. | Change control: attivare una thin slice positiva AAP oppure riclassificare `FR-095`; registrare una decisione che confermi o superseda `DEC-103`/la disposizione di `DEC-196`, senza assegnarne qui l'ID, e aggiornare Crosswalk/indice. |
| `S11-02` | `MAJOR` | `HIGH` | ADD §6.1 riga 3133, §7.1 riga 3281; Requirement Register `NFR-078` riga 398 | `VALID` | Il testo chiama `NFR-078` «differito» e afferma che nessun `P0` con `DEVE` è differito, ma `NFR-078` è `P0`, usa `DEVE` ed è `Confermato/MVP`. | Ambiguità fra esclusione dal PoC e rimozione dal profilo MVP; possibile perdita di un gate P0 nel DDD. | Conservare `NFR-078` come `Confermato P0/MVP`; parlare di «non incluso nel PoC» e qualificare la frase come `P0/PoC`. |
| `S11-03` | `MAJOR` | `HIGH` | ADD §4.3 riga 2852, §7 riga 3274; Decision Register `DEC-173` riga 190 e `DEC-175` riga 192; Requirement Traceability Index righe 266-269 | `VALID` | `DEC-173` e `DEC-175` sono decisioni sostantive su UI/role surfaces, documentazione, onboarding e sandbox, ma §7 le classifica come gate e non le alloca. | Il DDD riceve i requisiti derivati senza la tracciabilità alle decisioni che vincolano superfici e conformance kit; la chiusura di `ARF-013` non è completa. | Rimuoverle dall'elenco non allocabile; aggiungere `DEC-173` ad «Agent Kernel» (già tracciata in §4.3) e `DEC-175` a «Compiler & Gateway»; coverage risultante 183/196. |
| `S11-04` | `MINOR` | `HIGH` | ADD §7 righe 3259-3274; §8 `AM-13` riga 3331; harness `reports/verify_report.json:92-160` | `VALID` | `AM-13` dichiara 182/196 `DEC` allocate; il numero riproducibile corrente è 181/196 e quello corretto dopo `S11-03` è 183/196. | Il log non descrive né lo stato corrente né la copertura richiesta per chiudere `ARF-013`. | Dopo l'allocazione di `DEC-173` e `DEC-175`, sostituire `182/196` con `183/196` e mantenere l'elenco delle tredici decisioni di processo non allocate. |

Le anomalie `TBD` e gli shorthand ID restano source limitations documentate, non sono promosse a finding ADD autonomi. Tutti gli altri target del fence risultano deliberatamente governati o legittimamente demandati al DDD nei limiti sopra indicati.

## Conclusione STEP 11

L'integrità dei registri passa, ma la tracciabilità ADD non è un `PASS`: `S11-01` richiede riconciliazione di baseline prima che il DDD possa trattare `FR-095`; `S11-02` richiede una correzione di scope wording per preservare `NFR-078 P0/MVP`; `S11-03` alloca due decisioni sostantive omesse; `S11-04` corregge il conteggio di chiusura. I controlli su progressivi, crosswalk, rischi ed evidenze non hanno rilevato altri orfani o promozioni di stato.
