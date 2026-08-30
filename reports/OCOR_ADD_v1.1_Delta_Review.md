# OCOR ADD v1.1 — Independent Delta Review

## 1. Review Control

| Campo | Valore |
|---|---|
| Review date | 2026-08-30, Europe/Rome |
| Oggetto | `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md` |
| Branch FASE 1 | `fase-1`; STEP 0–7 eseguiti senza accesso a `inputs/supporting/prior/` |
| Commit FASE 1 | `627a2ffb1ddfdfa840f7100898dc1f4fe627422f` — `review: fase 1 — 11 finding, verdetto NOT READY` |
| Branch FASE 2/3 | `main`; prerequisito FASE 1 verificato come file tracciato nel commit sopra |
| Dichiarazione di indipendenza | **La FASE 1 è stata completata e committata prima dell'apertura di `inputs/supporting/prior/`.** Il materiale prior è stato letto soltanto dopo la verifica del commit sul branch `main` |
| Scope | Verifica delta v1.1; chiusura `ARF-001`–`ARF-027`; regressioni; contratti/schema; tracciabilità e scope fence; change control; bozze `DRAFT-A`–`DRAFT-I` |
| Standard/criteri | ISO/IEC/IEEE 42010; IEEE 1016; ISO/IEC/IEEE 12207; C4; formal systems; secure-by-design; fail-safe; least privilege |
| Evidence status | **Invariato:** `E1=0`, `E2=0`, zero requisiti `Verified`; capability `Design Target`; tecnologie `Candidate Implementation` |
| Authority fence | Nessun nuovo `DEC-*`; nessuna approvazione di `DRAFT-*`; nessuna chiusura di `OI-*`, `ASM-*`, `RSK-*`; nessuna capability differita attivata |

Il referto di FASE 1 registra correttamente che il tentativo di commit nella sandbox isolata era fallito per `.git` read-only. Prima dell'ESECUZIONE 2 l'operatore ha committato quegli stessi deliverable nel commit `627a2ff…`; la presenza nel tree del commit e la sequenza di esecuzione sono state verificate prima di leggere il materiale prior.

### Sorgenti e integrità

| Sorgente | SHA-256 / verifica |
|---|---|
| ADD v1.1 | `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` |
| Bozze `DRAFT-A`–`DRAFT-I` | `3336c0948df62564ffecef9c5872bcea2b68a4ec55fc6e08531797d060469bf0` |
| ADD v1.0 superseduto | `1e0fe999d66b0133638293d9568f79fb861636f81bc939e170e7d6fa392d8fed` |
| Review indipendente v1.0 | `13dca8bf94476434cf7a0434809b0d42a57d59dfc8546d363d5ffc29b729d727` |
| `DELTA_MANIFEST.json` | `c45e011fc49cbb4828acc8cb4c7a0579c78a74a973d69dd1069b97db34a704af` |
| `DIFF_v1.0_to_v1.1.patch` | `290fcf9ad98afb3e72f94c422cfaf6e1722ba1283affd7e9a17d650c2c50b70c` |
| `SHA256SUMS` normativo | `PASS`, 8/8 file |
| `SHA256SUMS.prior` | `PASS`, tutti i file prior |

### Controlli tool-backed

| Controllo | Esito | Limite probatorio |
|---|---|---|
| Harness ADD v1.1 | 13 `PASS`, 0 `FAIL`, 1 `NOT_EXECUTED` | Meta-validazione/struttura documentale, non implementazione |
| Harness ADD v1.0 | 10 `PASS`, 2 `FAIL`, 2 `NOT_EXECUTED` | `FAIL`: FSM state-set e tracciabilità. Integrità interna `NOT_EXECUTED` perché il harness cerca `SHA256SUMS` nella directory prior; la verifica esterna `SHA256SUMS.prior` è `PASS` |
| Validazione semantica OpenAPI 3.1 ufficiale | `NOT_EXECUTED` in entrambe le versioni | Il validator ufficiale non è disponibile; il controllo non è dichiarato superato |
| Conformance suite schema | 97 istanze: 96 conformi all'oracolo, 1 `FAIL`; più 1 meta-controllo `PASS` = 98 record runner, 97 `PASS`/1 `FAIL` | Test documentali degli schema embedded; nessun incremento `E1`/`E2` |
| Diff audit | 1.731 righe, 48 hunk confrontati con §8 e manifest | Nessuna modifica architetturale sostanziale totalmente nascosta; due inaccuratezze di locator/control |
| Tracciabilità | Universo core 693/693; indici e crosswalk verificati | Presenza numerica non implica coerenza semantica |

I controlli `NOT_EXECUTED` non sono trattati come `PASS`. Il `PASS` meccanico FSM v1.1 riguarda l'insieme dei 29 nomi di stato, non la bijezione degli archi. Il `PASS` di tracciabilità riguarda presenza/allocazione sintattica, non soddisfacibilità dei requisiti.

### Finalizzazione repository

| Operazione | Esito |
|---|---|
| `git add -A && git commit -m "review: fasi 2 e 3 — verifica di chiusura e verdetto"` | `FAILED` al primo e unico tentativo, prima dello staging: `.git/index.lock: Read-only file system`. Il comando non è stato ripetuto |
| `git push origin main` | `NOT_EXECUTED`: nessun commit locale prodotto e l'ambiente impone il divieto assoluto di rete |

I deliverable FASE 2/3 restano presenti nel worktree sotto `reports/` ma non committati da questa esecuzione.

## 2. Executive Verdict

**`NOT READY FOR DDD`.**

La v1.1 chiude adeguatamente 16 dei 27 finding precedenti; undici hanno stato diverso da `CLOSED`: quattro `PARTIALLY_CLOSED`, sei `CLOSED_WITH_NEW_DEFECT` e uno `OVER_CORRECTED`. La review finale conserva 15 finding: 2 `BLOCKER`, 4 `CRITICAL`, 7 `MAJOR`, 2 `MINOR`; per origine, 8 `NEW_IN_V1.1`, 6 `SURVIVING_FROM_V1.0`, 1 `REGRESSION`.

Il primo blocker è interno all'ADD: la tabella del Governed Context Set dichiara copertura che i contratti non realizzano, incluso `QueryContext` privo di marking. Il secondo è una contraddizione della baseline riprodotta dall'ADD: `FR-095` è `P0/PoC`, ma `ELM-070` è differito e ogni caso positivo AAP viene respinto. Il DDD non ha autorità per scegliere fra questi vincoli.

I quattro critical riguardano binding del Principal, commit canonico accettato senza Human Gate, emissione con contesto stale e algebra marking non conservativa. La suite non trova rami schema insoddisfacibili, ma riproduce un `FAIL` semantico nell'Action Contract. Non risultano promozioni indebite di tecnologie candidate o di evidenza. L'avvio del DDD richiede la chiusura verificata dei P0 indicati nel piano; la review non crea tale evidenza e non modifica `E1=0`, `E2=0` o lo stato `Verified`.

## 3. Findings Register

| ID | Severity | Confidence | Origine | ADD locator | Related IDs | Finding | Evidence | Impact | Exact remediation | Disposition |
|---|---|---|---|---|---|---|---|---|---|---|
| `DRF-001` | `BLOCKER` | `HIGH` | `SURVIVING_FROM_V1.0` | §1.4 L115–133; §3.0.1 L306–322; `QueryContext` L910–948; §4.2 L2670–2681; §4.3 L2790–2825; §5.3 L2953–2972; §6.3 L3174–3195 | `ARF-001`, `AM-01`, `DRAFT-A`, `FR-006`, `NFR-006`, `NFR-040` | La tabella GCS dichiara copertura universale che i record non realizzano. | `QueryContext` non dichiara `classification_marking_ref` contro il `✔` a L314; Scenario, Handoff, Security e trace usano `domain`, `domains[]` o omettono campi dichiarati coperti. | Policy, cache, isolamento e audit non possono usare una chiave cross-surface univoca; la prova di chiusura del blocker è falsa. | Definire un record GCS canonico; aggiungere `classification_marking_ref` a `QueryContext`; distinguere `domain_id` singolo da eventuali domain scope; fornire mapping/derivazione attestata per ogni campo e test di inventory su tutte le superfici. | `VALID` |
| `DRF-002` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | §1.4 L131; §3.0.1 L316; §3.2 L574–581, L742–745 | `AM-01`, `DRAFT-A`, `FR-006`, `RSK-006`, `TB-CXT-02` | Il Principal GCS è equiparato al producer dichiarato nel body senza binding al Principal di trasporto. | `producer_principal_ref` è obbligatorio nel payload; le regole boundary non impongono confronto o sostituzione col Principal autenticato. | Impersonificazione del producer, provenance falsa e confused authority all'ingress. | Separare `source_producer_principal_ref` da `effective_principal_id`; derivare il secondo solo dal trasporto; attestare il binding e mettere mismatch in quarantine/deny con Audit Record. | `VALID` |
| `DRF-003` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | §3.7 L2029, L2101–2120, L2185–2253; §5.4 L3007–3014 | `ARF-002`, `ARF-009`, `AM-02`, `AM-09`, `DRAFT-B`, `DRAFT-G`, `FR-150` | Lo schema accetta una mutazione canonica `R1_ANALYZE` con `approval.mode=NONE`. | Fixture negativa `CANONICAL_COMMIT/R1/NONE`: atteso `REJECT`, ottenuto `ACCEPT`. | Il contratto documentale non rende non aggirabile il Human Gate sul writer canonico. Non è un bypass runtime osservato, ma un percorso conforme allo schema. | Nel ramo canonical imporre `risk_class∈{R2_CONTROLLED,R3_HIGH_IMPACT}`, Approval umano, quorum/ruoli coerenti e relativo test negativo obbligatorio. | `VALID` |
| `DRF-004` | `CRITICAL` | `HIGH` | `SURVIVING_FROM_V1.0` | §4.1.1 L2578–2585; `ACT-T12` L2602, `T14` L2604, `T19` L2609, `T29` L2622; §5.4 L3043 | `ARF-006`, `AM-06`, `DRAFT-E`, `FR-162`, `RSK-037`, `RSK-050`, `RSK-054` | Le emissioni non rivalidano l'intera freshness e il retry replica solo parte del dispatch fence. | `T14`/`T29` richiamano solo `G-DISPATCH`; `T19` omette `G-FRESHNESS`, circuit breaker, adapter conformance e deadline. | Un command esterno o commit canonico può essere emesso dopo drift di state, policy, Authority, Approval, release o watermark. | Rivalidare atomicamente `G-FRESHNESS∧G-DISPATCH` a ogni emissione, retry e compensation; confrontare col `GatePackage`; drift ⇒ `INVALIDATED` prima dell'invio. | `VALID` |
| `DRF-005` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | §3.1.1 L359; §5.3 L2953–2991 | `ARF-004`, `ARF-012`, `AM-04`, `AM-12`, `DRAFT-D`, `DRAFT-H`, `OI-021` | Il metamodel ammette `PERMISSION`, ma l'algebra applica sempre operatori da restrizione. | Gli enum consentono `PERMISSION`; §5.3 dichiara caveat/dissemination controls restrizioni e usa union incondizionata. | Uno scheme formalmente valido può ampliare permessi in un derivato e causare leakage cross-compartment. | Fissare `RESTRICTION`, oppure definire operatore per famiglia coerente con la semantica e validare chiusura, associatività, commutatività, idempotenza e monotonia. Lasciare `OI-021` aperta. | `VALID` |
| `DRF-006` | `MINOR` | `HIGH` | `SURVIVING_FROM_V1.0` | §4.1 L2520–2574; §4.1.2 L2589–2624, soprattutto `T22` L2615 e `T27` L2620 | `ARF-018`, `AM-18` | Il claim di bijezione diagramma↔tabella è falso a livello di archi. | Righe aggregate e self-loop non disegnati; soprattutto `T22` salta nominalmente `OUTCOME_PENDING` mentre il diagramma usa `T27`. | Generatori o reviewer possono derivare lifecycle diversi; il harness sovrastima il controllo. | Una riga per arco con source/destination espliciti; correggere `T22`; estendere il harness alle tuple degli archi. | `VALID` |
| `DRF-007` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | `ActionInstance` L2497–2514; `G-FRESHNESS` L2584; `T24/T25` L2617–2618; L2628 | `ARF-007`, `AM-07`, `DRAFT-F`, `FR-163`, `RSK-023` | L'over-correction degli stati indeterminati non definisce adjudication/unblock e usa una conflict key troppo coarse. | Nessun record, Authority, evidenza minima o esito di adjudication; il target identifica solo la classe, non resource/adapter/effect footprint. | Recovery ambiguity e blocco indefinito di azioni indipendenti sullo stesso aggregate. | Introdurre `IndeterminateEffectAdjudication` append-only e `conflict_scope` tipizzata; mantenere fail-closed quando il footprint non è calcolabile. | `VALID` |
| `DRF-008` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | §3.7 L1980–2020, L2149–2181, L2332; §4.1 L2497–2516; `T29–T31` L2622–2624 | `ARF-002`, `ARF-009`, `AM-02`, `AM-09`, `DRAFT-B`, `DRAFT-G`, `FR-149`, `FR-150` | Il binding canonical e l'error model non specificano l'ammissione Claim→CanonicalAssertion. | Booleani dichiarativi senza path nel parameters schema; `minimum_count=0`; nessun mapping per precondition, invariant e revision conflict. | Il DDD dovrebbe inventare binding e rifiuti normativi, andando oltre un dettaglio wire. | Aggiungere field binding tipizzato per Claim/Evidence/Decision/Authority/aggregate/revision; evidence non vuota quando richiesta; mappa deterministica dei reason code `C3`. | `VALID` |
| `DRF-009` | `MAJOR` | `HIGH` | `REGRESSION` | §2.4 L234–260; §2.6 `BA-01` L285 e chiusura L294 | `AM-28`, `NFR-084`, `RSK-013`, `RSK-019` | Il fallback `BA-01` è presentato adapter-only ma cambia il modello di atomicità. | Due commit logici, crash window e ammissione che §2.3 va riscritta; l'invariante già `PASS` sulla sostituibilità scende a `PASS WITH CONDITION`. | Possibile perdita/duplicazione di eventi e adozione senza change control di un'architettura diversa. | Marcare il fallback `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`; rimuovere il claim adapter-only; richiedere failure analysis e revisione di §2.3/§6.2. | `VALID` |
| `DRF-010` | `MINOR` | `HIGH` | `NEW_IN_V1.1` | §1.1 L34; §7 L3259–3274; §8 L3319–3346, `AM-13` L3331 | `DRAFT-A`–`I`, `AM-13`, `UC-01` | I conteggi di document/change control non sono derivati e risultano falsi. | “Sette” contro nove righe `CC=Sì`; `AM-13` dice 182/196 `DEC`, la matrice ne alloca 181 e dopo `DRF-015` ne allocherebbe 183. | Review e authority ricevono una superficie di modifica inesatta. | Sostituire sette→nove; dopo `DRF-015` usare 183/196; generare entrambi i conteggi dalle tabelle e includere §1.1 nel locator del change log. | `VALID` |
| `DRF-011` | `MAJOR` | `MEDIUM` | `NEW_IN_V1.1` | `OCOR_DEC_197_plus_Draft_v0.1.md` L262–264 | `DRAFT-B`, `DRAFT-E`, `DRAFT-F`, `DRAFT-G`, `DRAFT-I` | Il DAG delle bozze non rappresenta tutte le dipendenze della safety chain. | `E` governa `T29` introdotta da `B`; `F` modifica errori dell'Action Contract introdotto da `G`; `E→I` è una dipendenza probabile da confermare. | Un change-set parziale può lasciare dispatch/stop/error contract incoerenti. | Pubblicare un DAG normativo; imporre almeno `B→E` e `F→G`; far decidere esplicitamente all'authority `E→I` e i change-set atomici. | `VALID` |
| `DRF-012` | `BLOCKER` | `HIGH` | `SURVIVING_FROM_V1.0` | §1.5 L142; §4.2 L2757; §7.1 L3286; Decision Register `DEC-103` L120 e `DEC-196` L218; Requirement Register `FR-095` L229 | `FR-095`, `ELM-070`, `DEC-103`, `DEC-196`, `CAP-019` | La baseline congela AAP come `P0/PoC` e contemporaneamente differisce l'unica capability che lo realizza. | L'ADD respinge ogni caso positivo con `CAPABILITY_DEFERRED`; l'acceptance di `FR-095` esercita solo il caso negativo “factual set assente”. | Il DDD dovrebbe scegliere senza autorità fra implementare AAP o violare un requisito P0; una suite solo negativa può dare falso `PASS`. | Change control sulla baseline: o attivare una thin slice AAP con positivo, oppure riclassificare `FR-095` fuori PoC; registrare una decisione autorizzata che confermi o superseda `DEC-103`/`DEC-196`, senza assegnarne qui l'ID, e aggiornare crosswalk/indice. | `SOURCE_LIMITATION` |
| `DRF-013` | `MAJOR` | `HIGH` | `SURVIVING_FROM_V1.0` | §3.3 `Uncertainty` L1054–1062; `ObjectSnapshot` L1077–1122 | `ARF-014`, `AM-14`, `FR-007` | `ObjectSnapshot.required` non impone tutti gli attributi richiesti per ogni risultato. | `link_refs`, `uncertainty`, `explanation_ref` sono proprietà opzionali; `FR-007` richiede relazioni, incertezza e spiegazione per ogni risultato. | Un'istanza priva dei tre campi valida e può falsamente soddisfare l'acceptance di `FR-007`. | Aggiungere i tre campi a `required`; permettere `link_refs:[]`, `Uncertainty.semantics=NONE` e un explanation reference policy-filtered/redacted. | `VALID` |
| `DRF-014` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | §6.1 L3133; §7.1 L3281 | `AM-17`, `ARF-017`, `CAP-024`, `NFR-078` | Lo scope fence confonde “fuori dal PoC” con stato “Differito”. | `NFR-078` è `Confermato`, `P0`, `DEVE`, release MVP; §6.1/§7.1 lo chiama differito e nega che un P0/DEVE sia differito. | Il bootstrap DDD/MVP può perdere un gate P0 o reinterpretare la baseline. | Elencare gli NFR come non inclusi nel profilo PoC ma confermati nelle rispettive release; qualificare il claim come “nessun `P0/PoC` con `DEVE`”. | `VALID` |
| `DRF-015` | `MAJOR` | `HIGH` | `SURVIVING_FROM_V1.0` | §4.3 L2852; §7 L3274; Decision Register `DEC-173` L190, `DEC-175` L192; Traceability Index L266–269 | `ARF-013`, `AM-13`, `FR-166`, `FR-167`, `NFR-082` | Due decisioni sostantive sono classificate come gate e lasciate senza allocazione. | `DEC-173` decide le superfici per ruolo; `DEC-175` documentazione/onboarding/sandbox. §7 le include fra le quindici decisioni “non allocabili”. | Il DDD riceve requisiti derivati senza le decisioni che vincolano UI e conformance kit. | Rimuoverle dall'elenco; allocare `DEC-173` ad Agent Kernel e `DEC-175` a Compiler & Gateway, con eventuale overlap governance; coverage 183/196. | `VALID` |

## 4. Closure Verification

| `ARF-*` | Severità originale | `AM-*` dichiarato | Stato | Evidenza | Nuovo difetto? |
|---|---|---|---|---|---|
| `ARF-001` | `BLOCKER` | `AM-01` | `PARTIALLY_CLOSED` | I cinque campi envelope sono presenti (§3.2 L468–516), ma la copertura universale §3.0.1 L306–322 è falsa: `QueryContext` manca del marking e più superfici non realizzano i mapping dichiarati. | `DRF-001`, `DRF-002` |
| `ARF-002` | `BLOCKER` | `AM-02` | `CLOSED_WITH_NEW_DEFECT` | Il percorso `C6→C3` e `T29–T31` esiste; il nuovo schema accetta canonical commit senza Human Gate e non lega i campi di admission (§3.7 L1980–2200). | `DRF-003`, `DRF-008` |
| `ARF-003` | `BLOCKER` | `AM-03` | `CLOSED` | `main` resta writer scope di `C3`; fork `C7` isolato e senza outbox pubblicabile (§2.4 L238; §2.5 L265, L274). | No |
| `ARF-004` | `CRITICAL` | `AM-04` | `CLOSED_WITH_NEW_DEFECT` | La formula restriction è corretta; il nuovo enum `PERMISSION` contraddice l'operatore incondizionato (§3.1.1 L359; §5.3 L2983–2991). | `DRF-005` |
| `ARF-005` | `CRITICAL` | `AM-05` | `CLOSED` | Quorum/role e dual control sono vincolati nei rami MCP (L1670–1781); test positivi e negativi `PASS`. | No |
| `ARF-006` | `CRITICAL` | `AM-06` | `PARTIALLY_CLOSED` | Stop epoch/audit sono in `G-DISPATCH`; `T14/T29` la rivalidano. `T19` usa un subset e nessuna emissione rivalida `G-FRESHNESS` (L2584–2609). | `DRF-004` |
| `ARF-007` | `CRITICAL` | `AM-07` | `OVER_CORRECTED` | Terminalità/escalation esistono, ma adjudication e conflict footprint non sono modellati (L2497–2514, L2617–2628). | `DRF-007` |
| `ARF-008` | `MAJOR` | `AM-08` | `CLOSED` | `Problem` include campi e reason code mancanti; `served`/`deferred_element` sono condizionalmente richiesti (L1195–1258). | No |
| `ARF-009` | `MAJOR` | `AM-09` | `CLOSED_WITH_NEW_DEFECT` | I contratti `ACTION`/`EVENT` esistono; l'Action Contract nuovo introduce `DRF-003/008`. | `DRF-003`, `DRF-008` |
| `ARF-010` | `MAJOR` | `AM-10` | `CLOSED` | MCP impone retry, irreversibilità, unknown outcome e coerenza effect↔tier (L1490–1828). | No |
| `ARF-011` | `MAJOR` | `AM-11` | `CLOSED` | Le quattro disposition capability sono separate nel testo e nel metamodel (§2.4 L246–260; L360). | No |
| `ARF-012` | `MAJOR` | `AM-12` | `CLOSED_WITH_NEW_DEFECT` | Scheme, resolution e join ora esistono; l'enum `PERMISSION` nuovo rende l'algebra incoerente. `OI-021` resta aperta. | `DRF-005` |
| `ARF-013` | `MAJOR` | `AM-13` | `CLOSED_WITH_NEW_DEFECT` | `ARC/BR/FR/NFR` hanno copertura piena; l'estensione alle `DEC` classifica falsamente `DEC-173/175` come gate e dichiara 182 anziché 181/183. | `DRF-015`, `DRF-010` |
| `ARF-014` | `MAJOR` | `AM-14` | `PARTIALLY_CLOSED` | I campi sono dichiarati, ma `ObjectSnapshot.required` omette `link_refs`, `uncertainty`, `explanation_ref` richiesti da `FR-007` (L1077–1122). | No: residuo `DRF-013` |
| `ARF-015` | `MAJOR` | `AM-15` | `CLOSED` | Il C4 include gli archi prima mancanti, incluso `C6→C3` (L172–186). | No |
| `ARF-016` | `MAJOR` | `AM-16` | `CLOSED` | `CapabilityLease`, writer fencing e `ELM-080` sono distinti e il target stop non dipende dall'elemento differito (L2921–2936). | No |
| `ARF-017` | `MAJOR` | `AM-17` | `CLOSED_WITH_NEW_DEFECT` | `NFR-072/079` sono inclusi nella slice PoC, chiudendo l'omissione originaria; lo stesso testo nuovo chiama però `NFR-078` differito e nega che un P0/`DEVE` sia differito (§6.1 L3133; §7.1 L3281). | `DRF-014` |
| `ARF-018` | `MINOR` | `AM-18` | `PARTIALLY_CLOSED` | I 29 stati coincidono, ma non gli archi; `T22` e `T27` descrivono percorsi non equivalenti (L2615, L2620). | `DRF-006` |
| `ARF-019` | `MINOR` | `AM-19` | `CLOSED` | Il ramo `CDC_CHANGE→CDC` è simmetrico e passa i casi positivi/negativi (L614–637). | No |
| `ARF-020` | `MINOR` | `AM-20` | `CLOSED` | `compartments[]` è plurale con `minItems:1`/unicità nelle superfici indicate (§3.0.3 L333–335). | No |
| `ARF-021` | `MINOR` | `AM-21` | `CLOSED` | Marking inline/ref/SecurityContext hanno una risoluzione fail-closed unica (§3.0.2 L324–331). | No |
| `ARF-022` | `MINOR` | `AM-22` | `CLOSED` | Validità policy bundle e comportamento edge su snapshot scaduto sono espliciti (L2868; L2966–2974; L3201). | No |
| `ARF-023` | `MINOR` | `AM-23` | `CLOSED` | §3.9 e §7.2 collegano ogni criterio a `EV-*`; tutti restano `NOT RUN`. | No |
| `ARF-024` | `MINOR` | `AM-24` | `CLOSED` | `OUT_OF_DISTRIBUTION` e `OUTSIDE_VALIDITY_ENVELOPE` sono separati e hanno precedenza normativa (L2728–2743). | No |
| `ARF-025` | `MINOR` | `AM-25` | `CLOSED` | Il profilo ristretto RFC 9457 e il divieto di membri arbitrari sono dichiarati (L1195–1204). | No |
| `ARF-026` | `OBSERVATION` | `AM-26` | `CLOSED` | `ABSTAIN` esclude strutturalmente effect estimate/quantità prescrittive (L2700–2745). | No |
| `ARF-027` | `OBSERVATION` | `AM-27` | `CLOSED` | Admission applicativa impone esattamente un ramo `ModelResult`, compensando il limite proto3 (L1452–1476). | No |

| Stato | Totale |
|---|---:|
| `CLOSED` | 16 |
| `PARTIALLY_CLOSED` | 4 |
| `CLOSED_WITH_NEW_DEFECT` | 6 |
| `OVER_CORRECTED` | 1 |
| `NOT_CLOSED` | 0 |
| **Totale** | **27** |

## 5. Regression Audit

La review v1.0 riepiloga 38 `PASS`, ma le sue tabelle ne contengono 46: gli otto `PASS` di §4.1 “Separazione epistemica” sono omessi dal totale. Per riconciliare il mandato sono riportati qui i 38 di §4.2–§4.6; gli otto ulteriori sono stati comunque ricontrollati e restano `PASS`. Sul set di 38, dopo il controllo cross-register: **36 `PASS`, 1 `PASS WITH CONDITION`, 1 `FAIL`, 0 `NOT EVALUABLE`**. Il solo stato peggiorato dalla v1.1 è `DRF-009`; `DRF-012` è un falso `PASS` preesistente, non una regressione.

| # | Gruppo | Invariante già `PASS` | Esito v1.1 | Evidenza v1.1 | Regressione |
|---:|---|---|---|---|---|
| 1 | Consistenza | Transazione locale State Delta + Outbox | `PASS` | §2.3 L224–232; §6.2 L3139–3140 | No; target non verificato resta dichiarato |
| 2 | Consistenza | Assenza di 2PC/XA | `PASS` | §1.3 L99; `C3` L202; §6.2 L3137 | No |
| 3 | Consistenza | Assenza di ACID globale | `PASS` | §1.3 L99; §4.1 L2518 | No |
| 4 | Consistenza | Assenza di triple-write sincrono | `PASS` | §1.3 L99; §6.2 L3137 | No |
| 5 | Consistenza | Assenza di multi-master | `PASS` | §1.3 L99; §6.2 L3137, L3170 | No |
| 6 | Consistenza | At-least-once delivery | `PASS` | `C5` L204; §2.5 L267; §3.2 L747–748 | No |
| 7 | Consistenza | Idempotency e fencing | `PASS` | `C3/C5` L202–204; `G-DISPATCH` L2585; `MutationFence` L3152–3167 | No |
| 8 | Consistenza | Ordering limitato alla partition key | `PASS` | `C5` L204; §3.2 L748; §3.8 L2392–2395 | No |
| 9 | Consistenza | Watermark e facts atomicamente visibili | `PASS` | §2.3 L231; §6.2 L3143; `BA-02` L286 | No; proprietà ancora da provare |
| 10 | Consistenza | Nessun reverse-write dalle proiezioni | `PASS` | §2.3 L232; §6.2 L3145 | No |
| 11 | Adapter | Triade come reference adapter sostituibili | `PASS WITH CONDITION` | §2.4 L234–260; `BA-01` L285; claim L294 | **Sì — `DRF-009`** |
| 12 | Adapter | Nessun dialect nei contratti pubblici | `PASS` | §1.4 L110; §3 L300; §3.8 L2346 | No |
| 13 | Adapter | Nessun backend ID/schema fisico nei contratti | `PASS` | §1.4 L110; `Namespace` L350; §3.8 L2346 | No |
| 14 | Adapter | Dialect confinati agli adapter privati | `PASS` | §2.4 L246–260; §4.2 L2668 | No |
| 15 | Agents | Agente come Principal distinto | `PASS` | §1.2 L74; §4.3.1 L2841; §5.1 L2867 | No |
| 16 | Agents | Assenza di credenziali datastore | `PASS` | §4.3 L2763; §5.2 L2943 | No |
| 17 | Agents | Capability allow-list | `PASS` | `TB-CXT-03` L107; §4.3.1 L2844; `G-AUTHORITY` L2581 | No |
| 18 | Agents | Delegation bounded | `PASS` | §5.2 L2893–2918, L2938–2942 | No |
| 19 | Agents | Prompt/Goal/Message/Memory/tool output tainted | `PASS` | §2.5 L270; §4.3.1 L2843 | No |
| 20 | Agents | Nessuna Authority derivata dal prompt | `PASS` | §1.3 L87; §4.3.1 L2843; §3.5 L1867 | No |
| 21 | Agents | Handoff tipizzati e mediati | `PASS` | §4.3 L2763, L2778–2826 | No; `DRF-001` non elimina la mediazione |
| 22 | Agents | Challenger indipendente | `PASS` | §4.3 L2784; §4.3.1 L2847 | No |
| 23 | Agents | Dissent non sopprimibile | `PASS` | §4.3 L2784–2785; §4.3.1 L2847 | No |
| 24 | Agents | Critical Dissent bloccante per High-Impact | `PASS` | §4.3 L2837, L2850 | No; il bypass schema è `DRF-003` distinto |
| 25 | Causal | Identify-or-abstain | `PASS` | §4.2 L2684–2726 | No |
| 26 | Causal | Validity envelope | `PASS` | §4.2 L2689–2691, L2732–2743 | No |
| 27 | Causal | `ABSTAIN` se non identificabile | `PASS` | §4.2 L2687–2690; `NOT_IDENTIFIED` L2730 | No |
| 28 | Causal | Nessun effect estimate in `ABSTAIN` | `PASS` | §4.2 L2700–2745 | No |
| 29 | Causal | Isolamento copy-on-write | `PASS` | §4.2 L2657–2668, L2682 | No |
| 30 | Causal | Nessun commit `main` dal runtime causale | `PASS` | `C7` L206; L2753–2755 | No |
| 31 | Causal | `do(X) ≠ Action` | `PASS` | §4.2 L2698 | No |
| 32 | Causal | `ELM-070` correttamente differito nell'ADD | `FAIL` | §1.5 L142 e §4.2 L2757 contro `DEC-103`/`FR-095 P0/PoC` e freeze `DEC-196` | No regressione: falso positivo già presente in v1.0; `DRF-012` |
| 33 | Action | Pre-admission failure | `PASS` | §4.1 L2495 | No |
| 34 | Action | Famiglia `ACT-T01`–`T23` | `PASS` | §4.1.2 L2589–2624; harness `T01–T31` contigua | No |
| 35 | Action | `ACT-T21a/b/c` presenti | `PASS` | L2612–2614 | No |
| 36 | Action | ACK distinto dal successo | `PASS` | `T15` L2605; L2630 | No |
| 37 | Action | Nessun retry cieco | `PASS` | `T19` L2609; L2630 | No nel senso stretto; incompletezza guardie in `DRF-004` |
| 38 | Action | Compensation come nuova azione governata | `PASS` | `T21` L2611; L2632 | No |

Gli otto `PASS` aggiuntivi di §4.1 — separazioni epistemiche, Receipt/ExecutionResult, ExecutionResult/Outcome, Recommendation/Decision, Approval/Decision, Decision/ActionIntent, ActionIntent/ActionCommand e Intervention/Action — restano tutti `PASS`. Il miglioramento del harness v1.1 su FSM e tracciabilità è strutturale e non costituisce evidenza di implementazione.

## 6. Contract and Schema Verification

La suite estrae gli schema direttamente dall'ADD, usa JSON Schema Draft 2020-12 con format checking e risolve i `$ref` locali degli OpenAPI component schema. Il numero “rami” è quello `if/then` del harness; sono state esercitate anche le alternative `oneOf`. Un `PASS` sintattico non prevale sui vincoli normativi cross-contract.

| Schema | Rami condizionali | Positivi | Negativi | Campi richiesti ma non dichiarati | Esito |
|---|---:|---:|---:|---|---|
| `signed-canonical-ir:1.0` | 0 | 1 | 1 | Nessuno | `PARSED`; `STRUCTURAL REVIEW ONLY` per assenza di rami |
| `canonical-ingestion-envelope:1.1` | 4 | 11 | 9 | Nessun mismatch sintattico `required`/`properties`; il binding Principal resta semanticamente incompleto (`DRF-002`) | `PARSED`; cross-boundary review `FAIL` su authority binding |
| `mcp-tool-contract:1.1` | 11 | 11 | 13 | Nessuno | `PARSED`; tutti i rami codificati soddisfacibili |
| `action-type-contract:1.0` | 9 | 9 | 11 | Nessun mismatch sintattico; mancano binding normativi Claim/Evidence/Decision/revision | **`FAIL`**: caso safety canonical `R1/NONE` accettato; `DRF-003/008` |
| `event-subscription-contract:1.0` | 0 | 1 | 4 | Nessuno | `PARSED`; `STRUCTURAL REVIEW ONLY` per assenza di rami; nessun finding autonomo |
| OpenAPI 1.1.0 | 3 | 15 | 11 | `QueryContext.classification_marking_ref` è assente dalle properties; `ObjectSnapshot.link_refs`, `uncertainty`, `explanation_ref` sono dichiarati ma non in `required` | **`FAIL`** nella review semantica; component schema `PARSED`; validator OpenAPI ufficiale `NOT_EXECUTED` |

Le colonne della tabella contano **97 istanze**: 48 positive e 49 negative; 96 sono conformi all'oracolo e 1 fallisce. Il runner aggiunge un meta-controllo `suite/conteggio if/then` con esito `PASS`: totale machine-readable **98 record**, 97 `PASS` e 1 `FAIL`. Zero rami risultano insoddisfacibili. Lo scan automatico `RV-01` trova correttamente zero chiavi elencate in `required` ma assenti da `properties`; non può rilevare obblighi semantici omessi sia da `required` sia dalle properties, né campi dichiarati ma indebitamente opzionali.

### Caso fallito riprodotto

L'istanza `action-type-contract` con `target=CANONICAL_COMMIT`, `effect_class=CANONICAL_COMMIT`, binding formalmente completo, `risk_class=R1_ANALYZE` e `approval.mode=NONE` viene accettata. §4.1 e §5.4 richiedono invece lo stesso Human Gate del percorso esterno e almeno `R2_CONTROLLED`. Il ramo è soddisfacibile, ma fail-open: è l'opposto della classe RV-01.

### Valutazione dei due contratti nuovi

`event-subscription-contract:1.0` è adeguato al livello ADD: subscription/cursor logici, at-least-once, deduplica su `event_id`, ordering per chiave, filtri nominati, marking e replay policy-aware; nessun topic, offset fisico o backend ID.

`action-type-contract:1.0` copre identità, versioni, digest, effect/risk, approval, timeout, retry, idempotenza, irreversibilità e compensation, ma non è safety-complete. `target=CANONICAL_COMMIT` non basta a specificare l'ammissione di una Claim: il DDD dovrebbe inventare i field binding e il mapping dei rifiuti `C3`, e lo schema non impone il gate umano. Questi non sono semplici dettagli wire.

## 7. Delta Surface Review

| Superficie | Valutazione |
|---|---|
| §2.6 Backend Assumption Register | Positivo: rende esplicite otto assunzioni, test e `NO-GO`, senza promuovere backend. Negativo: `BA-01` propone una riprogettazione di atomicità come fallback adapter-only (`DRF-009`). Le altre sette assunzioni sono ragionevoli target da verificare. |
| §3.0–§3.0.4 | Il consolidamento di context, marking, naming e versioning è necessario. La tabella GCS contiene falsi `✔`, incluso il marking assente da QueryContext (`DRF-001`), e il Principal ingest è authority-ambiguous (`DRF-002`). Il version bump è dichiarato correttamente. |
| §3.1.1 / §5.3 marking | Il join della classification è calcolabile per scheme validi a semantica restriction. L'ammissione di `PERMISSION` senza operatori coerenti rompe la monotonia conservativa (`DRF-005`). `OI-021` non è chiusa. |
| §3.7 Action Type | Tutti i nove rami sono soddisfacibili. Il target canonical consente bypass del gate e lascia binding/error model incompleti (`DRF-003/008`). |
| §3.8 Event Subscription | Adeguato e backend-neutral; nessun finding autonomo. Il binding delivery→GCS resta soggetto alla correzione trasversale `DRF-001`. |
| §4.1 FSM | Set di stati e famiglia `ACT-T` migliorati. Bijezione edge-level ancora falsa (`DRF-006`), freshness non rivalidata alle emissioni (`DRF-004`), adjudication/footprint indeterminati (`DRF-007`). |
| §4.2 Causal | Identify-or-abstain, isolamento overlay e `do(X)≠Action` restano corretti. Lo scope fence AAP riproduce però la contraddizione `FR-095`/`ELM-070` (`DRF-012`). |
| §4.3 Multi-agent | Prompt non autorevole, typed handoff e dissent sono ben governati. La forma dei campi GCS resta incoerente; il DAG decisionale esterno è incompleto (`DRF-001/011`). |
| §5.1–§5.5 Security | Separation of duties, lease di sicurezza, break-glass e stop sono concettualmente solidi. Restano le finestre freshness e il binding Principal. Nessun claim di conformance security osservata è accettato. |
| §6–§7 | Evidence fence e universo 693 sono preservati. `NFR-078` è descritto con stato improprio (`DRF-014`); due decisioni sostantive sono non allocate (`DRF-015`); `ObjectSnapshot` non rende verificabile `FR-007` (`DRF-013`). |
| §8 Amendment Log | La superficie è ampia e i difetti self-reported sono utilmente documentati. Il claim “tutti chiusi” non regge; conteggi e locator non sono pienamente accurati (`DRF-010`). |

Non sono emersi ulteriori bypass di single-writer, branch contamination, reverse-write delle proiezioni, prompt-derived authority o claim exactly-once. Le capability differite restano tali; la mancanza di evidenza correttamente dichiarata non è stata classificata come difetto.

## 8. Decision Draft Assessment

Queste sono raccomandazioni all'authority competente, non approvazioni della review.

| Draft | Necessità e scope | Dipendenze / criterio | Raccomandazione |
|---|---|---|---|
| `DRAFT-A` | Decisione necessaria; razionale corretto, ma mapping GCS e origine Principal incompleti. | Chiudere `DRF-001/002`; fixture per ogni superficie e ogni campo. | **`REVISE`** |
| `DRAFT-B` | Pipeline unica è scelta architetturale valida; scope insufficiente su risk floor e binding canonical. | Dipende da G ed E; negativo `CANONICAL_COMMIT/R1/NONE` obbligatorio. | **`REVISE`** |
| `DRAFT-C` | Single-writer/branch/relay sono proporzionati e verificabili; non chiude `OI-020`. | Forbidden-write e fork/outbox testabili. | **Raccomandare approvazione tramite change control** |
| `DRAFT-D` | Correzione union/intersection necessaria; la parametrizzazione contraddice il metamodel. | Dipende da H; golden test per ogni semantica ammessa. | **`REVISE`**, consolidare con H |
| `DRAFT-E` | Punto di serializzazione stop/dispatch necessario; manca freshness e copertura retry/compensation. | Dipende dal percorso B; rapporto con I da rendere esplicito. | **`REVISE`** |
| `DRAFT-F` | Terminalità necessaria; scope eccessivo sul target coarse e incompleto sull'adjudication. | Dipende dall'Action Contract G; test su azioni indipendenti. | **`REVISE`** |
| `DRAFT-G` | Nuovi kind contract necessari; Event adeguato, Action non safety-complete. | Dipendenza reciproca con B; chiudere `DRF-003/008`. | **`REVISE`** |
| `DRAFT-H` | Scheme necessario senza decidere la tassonomia; algebra non coerente su tutti i valori. | Dipende da D; non chiude `OI-021`. | **`REVISE`**, consolidare con D |
| `DRAFT-I` | Distinzione CapabilityLease/ELM-080 corretta e necessaria. | Criterio di stop indipendente dalla revoca push è verificabile. | **Raccomandare approvazione tramite change control** |

Il DAG normativo deve includere almeno `B→E` e `F→G`; l'authority deve decidere espressamente se `E→I` è vincolante e quali change-set siano atomici. Nessuna bozza viene qui approvata, ritirata o trasformata in decisione di baseline.

## 9. Traceability and Scope-Fence Audit

### Integrità e allocazione

| Famiglia | Registro/indice | Allocata in ADD §7 | Esito |
|---|---:|---:|---|
| `DEC` | 196 | 181 | `FAIL`: 13 esclusioni di processo legittime; `DEC-173/175` sostantive e orfane |
| `BR` | 18 | 18 | `PASS` |
| `FR` | 174 | 174 | `PASS` numerico; `FR-095` semanticamente insoddisfacibile nel profilo |
| `NFR` | 93 | 93 | `PASS` numerico; wording `NFR-078` difettoso |
| `ARC` | 23 | 23 | `PASS` |
| `CAP` | 26 | 25 | `PASS`: `CAP-026` esplicitamente out of scope |
| `ELM` | 103 | 103 | `PASS` numerico |
| `RSK` | 60 | 60 | `PASS`; tutte le righe hanno trattamento e stato preservato |
| **Core** | **693** | n/a | **`PASS` per unicità/presenza** |

Non risultano buchi di progressivo, definizioni primarie duplicate o ID core fuori range. Le 285 righe `BR/FR/NFR` hanno fonte, acceptance, metodo, stato e release; 26/26 `CAP` e 103/103 `ELM` hanno requisiti; le 428 relazioni dirette del crosswalk sono preservate nell'indice. Tutti i 27 `EV-*` citati da §7.2 esistono e restano `NOT RUN`.

### Scope fence rigoroso

| Elemento | Esito | Motivo |
|---|---|---|
| `FR-048` | `PASS` | Unico requisito formalmente `Differito/Future`; build del profilo → `CAPABILITY_DEFERRED`. |
| hardening `CAP-024` | `PASS WITH DEFECT` | Slice PoC enumerata; `NFR-078` è però `Confermato P0/MVP`, non “Differito” (`DRF-014`). |
| `ELM-011` | `PASS` | Vector/index/embedding disabilitati; nessun claim di supporto. |
| `ELM-015` | `PASS` | Profilo semantico completo differito; secret material resta fuori da IR/graph/log/export. |
| `ELM-035` | `PASS` | Un solo percorso bounded; nessuna Saga generale promessa. |
| `ELM-049` | `PASS` | Purpose minimo su dati sintetici; nessun claim privacy/compliance. |
| `ELM-070` | **`FAIL — SOURCE_LIMITATION`** | `FR-095 P0/PoC` richiede AAP, ma ogni positivo è respinto (`DRF-012`). |
| `ELM-080` | `PASS` | Budget/quota, CapabilityLease e reservation semantica distinti. |
| `ELM-084` | `PASS WITH CONDITION` | Contesto effimero ammesso; un eventuale MemoryItem deve comunque soddisfare `FR-118/119`. |
| `ELM-091` | `PASS` | Solo mapping W3C/fixture circoscritti; nessuna equivalenza generale. |
| `CAP-026` | `PASS` | Fuori container e coverage claim; non attivata. |

`NFR-007` e `NFR-009` conservano soglie `TBD`: sono `NOT EVALUABLE`, non falsi `PASS`, e restano source limitation prima del PoC gate. Gli shorthand `OI-022/004` e `NFR-065/008` nei registri non sono atomici; vanno normalizzati, ma non sono promossi a finding ADD autonomi.

## 10. Undocumented Changes

Il diff v1.0→v1.1 contiene 48 hunk. Tutte le modifiche architetturali sostanziali sono riconducibili a §8 e/o al `DELTA_MANIFEST`; non emerge un cambiamento architetturale totalmente nascosto.

| Deviazione | Evidenza | Disposizione |
|---|---|---|
| `UC-01` — §1.1 non presente nei locator `AM-*` | I primi due hunk cambiano document control e aggiungono “Sette emendamenti”, mentre nove righe hanno `CC=Sì`. | Assorbita in `DRF-010`; aggiungere §1.1 al change log e correggere il conteggio. |
| `UC-02` — locator `AM-02` incompleto | §2.2 cambia `C3` specificando la request emessa da `C6`; la sostanza è descritta da `AM-02`, ma §2.2 non è nel locator. | Errore di locator, non modifica nascosta; aggiungere §2.2 ad `AM-02`. Nessun finding autonomo. |

Il version bump, le rinumerazioni e i rinforzi dell'evidence fence non sono stati contati come scelte architetturali autonome. Nessuna conclusione di questo audit incrementa l'evidenza.

## 11. Prioritised Remediation Plan

### `P0 — before DDD`

| Voce | Finding | Owner role | Documento | Change control | Verifica di chiusura |
|---|---|---|---|---|---|
| Risolvere la contraddizione `FR-095`/`ELM-070` con una delle due disposizioni autorizzate. | `DRF-012` | Requirements Authority + Architecture Review Board | Decision/Requirement Register, Crosswalk, ADD §1.5/§4.2/§7.1 | **Sì** — varia la baseline o la slice PoC | Almeno un positivo AAP `ACCEPT`, oppure `FR-095` formalmente fuori PoC; nessuna suite solo-negativa |
| Definire il GCS canonico e il binding trusted del Principal su tutte le superfici. | `DRF-001`, `DRF-002` | Principal Enterprise Architect + Zero-Trust Security Architect | ADD §1.4, §3.0.1, schema coinvolti | **Sì** — contratti normativi | Inventory machine-readable 11×superfici; fixture positive/negative; mismatch producer/Principal ⇒ deny/quarantine |
| Rendere il canonical commit non aggirabile e semanticamente bindato. | `DRF-003`, `DRF-008` | Distributed Systems Architect + Contract Verification Engineer | ADD §3.7, §4.1, §5.4 | **Sì** | `R1/NONE` rifiutato; field path risolti; evidence/Decision/revision e rifiuti `C3` testati |
| Rivalidare freshness e dispatch a ogni emissione. | `DRF-004` | Distributed Systems Architect + Multi-Agent Safety Architect | ADD §4.1.1/§4.1.2 | **Sì** | Concurrency fixtures su drift di state/policy/Authority/Approval/release/watermark per `T14/T19/T29` |
| Chiudere l'algebra marking su tutto lo spazio ammesso. | `DRF-005` | Semantic/Ontology Architect + Zero-Trust Architect | ADD §3.1.1/§5.3 | **Sì** | Property tests di chiusura, associatività, commutatività, idempotenza e monotonia; `OI-021` preservata |
| Rendere `FR-007` verificabile per ogni risultato. | `DRF-013` | Contract Verification Engineer | ADD §3.3 OpenAPI | **Sì** — schema pubblico | Negativi senza `link_refs`, `uncertainty` o `explanation_ref` tutti rifiutati |
| Correggere release/scope e allocare le decisioni sostantive. | `DRF-014`, `DRF-015` | Requirements Authority + V&V Lead | ADD §6.1/§7/§7.1; registri se necessario | **Sì** | `NFR-078` resta `Confermato P0/MVP`; `DEC-173/175` allocate; conteggi rigenerati |
| Correggere il DAG prima di sottoporre le bozze. | `DRF-011` | Change Control Authority | Documento `DRAFT-A`–`I` | **Sì** | Topological validation; nessun sottoinsieme approvabile lascia una dipendenza non approvata |

### `P1 — during DDD bootstrap`

| Voce | Finding | Owner role | Documento | Change control | Verifica di chiusura |
|---|---|---|---|---|---|
| Definire adjudication append-only e conflict footprint. | `DRF-007` | Action Safety Architect | ADD §4.1; poi DDD Action Engine | **Sì** per la semantica ADD; no per dettagli interni conformi | State-model test: azioni indipendenti non bloccate; footprint ignoto fail-closed; storico immutabile |
| Rendere diagramma/tabella edge-equivalent. | `DRF-006` | Architecture Modeler + V&V Lead | ADD §4.1; harness | **Sì** per il testo normativo | Confronto automatico tuple `(source,event,destination)` senza mismatch |
| Confinare `BA-01` a alternativa non selezionabile senza nuova analisi. | `DRF-009` | Distributed Systems Architect | ADD §2.6/§6.2; ADR DDD soltanto dopo autorizzazione | **Sì** per correggere/classificare §2.6; ulteriore change control e failure analysis prima di ogni adozione | Crash-window model e failure suite; nessun claim adapter-only |
| Correggere conteggi e locator derivati. | `DRF-010` | Configuration Manager | ADD §1.1/§8; manifest | **Sì** come parte del change-set | Conteggi generati: 9 righe `CC=Sì`, 183/196 `DEC` dopo `DRF-015`; diff↔locator completo |

### `P2 — before implementation`

| Voce | Owner role | Documento/artefatto | Change control | Verifica di chiusura |
|---|---|---|---|---|
| Integrare nel compiler tutte le fixture negative/positive della review, incluse GCS, `FR-007`, canonical gate, marking e AAP. | Contract Verification Engineer | Conformance suite generata | No se aderente all'ADD corretto | Zero failure rispetto all'oracolo; almeno un positivo per ogni ramo/capability attiva |
| Eseguire il validator OpenAPI 3.1 ufficiale e fissarne versione/configurazione. | V&V Lead | Build pipeline | No | Controllo oggi `NOT_EXECUTED` diventa eseguito con report firmato; gli errori non sono soppressi |
| Selezionare backend solo dopo i test `BA-01`–`BA-08`; mantenere profilo dipendente `NO-GO` in caso contrario. | Adapter Owners + V&V Lead | Backend conformance reports | Sì se un fallback cambia invarianti | Ogni assunzione ha esito e trace; nessuna feature candidata trattata come disponibile per presunzione |

### `P3 — before PoC acceptance`

| Voce | Owner role | Documento/artefatto | Change control | Verifica di chiusura |
|---|---|---|---|---|
| Congelare soglie `NFR-007`, `NFR-009`, `NFR-071` secondo le authority/open issue esistenti e preregistrare workload. | Product/Requirements Authority + V&V Lead | Requirement/Evidence registers | Sì se cambia requisito | Nessun criterio `TBD`; gate separati e non compensabili |
| Eseguire `EV-*`, failure injection, red-team, recovery, portability e performance senza promuovere claim prima dell'esito. | Independent V&V + Security Red Team | Evidence packages | No per esecuzione; sì per variazione baseline | Evidenze firmate; stato aggiornato soltanto dall'authority; zero bypass P0 |

## 12. Proposed Exact Amendments

Le proposte seguenti sono patch testuali per il change control; non modificano il documento sotto esame e non costituiscono approvazione.

### PA-01 — Governed Context Set (`DRF-001`)

**Sezione:** §3.0.1 e OpenAPI `QueryContext`.

**Testo attuale problematico:** la tabella marca `classification_marking` come `✔ (*_ref)` per QueryContext, ma lo schema L910–948 non contiene il campo; altre superfici usano `domain`/`domains[]` contro il `domain_id` dichiarato.

**Testo sostitutivo preciso:**

> Ogni superficie elencata realizza gli undici campi del Governed Context Set mediante il mapping machine-readable allegato. `domain_id` è il singolo dominio effettivo della richiesta o del record; eventuali insiemi di domain scope si chiamano `authorized_domain_scopes` e non lo sostituiscono. Un mapping assente, ambiguo o non risolvibile produce `DENY`/quarantine, non default permissivi.

Nel `QueryContext.required` aggiungere `classification_marking_ref`; nelle properties aggiungere:

```yaml
classification_marking_ref:
  type: string
  pattern: '^urn:sha256:[0-9a-f]{64}$'
```

Uniformare Scenario/Handoff/trace a `domain_id`; in `SecurityContext` aggiungere `domain_id` separato da `authorized_domain_scopes[]`. Aggiungere mapping attestati per Principal, actor chain e correlation nelle superfici che non li trasportano letteralmente.

**Conseguenze di tracciabilità:** `ARF-001`, `AM-01`, `DRAFT-A`, `FR-006`, `NFR-006`, `NFR-040`; nessun nuovo ID.

### PA-02 — Principal effettivo e producer (`DRF-002`)

**Sezione:** §3.0.1 riga `principal_id`; §3.2 regole runtime.

**Testo attuale problematico:** `principal_id` è realizzato da `integrity.producer_principal_ref`, pur essendo dichiarato derivato dal transport security context.

**Testo sostitutivo preciso:**

> `effective_principal_id` è creato esclusivamente dal trusted ingress boundary a partire da mTLS/workload identity e token verificato; non è un campo del payload. `integrity.producer_principal_ref` è rinominato semanticamente `source_producer_principal_ref` e descrive la provenienza dichiarata della sorgente. Il boundary verifica che il Principal effettivo sia autorizzato ad attestare quel producer e registra entrambi. Mismatch, binding assente o attestazione non verificabile ⇒ quarantine e Audit Record; il producer dichiarato non amplia mai Authority.

**Conseguenze:** aggiorna GCS mapping, ingestion fixtures, provenance e `DRAFT-A`; preserva gli ID esistenti.

### PA-03 — Gate del canonical commit (`DRF-003`)

**Sezione:** §3.7 ramo `target=CANONICAL_COMMIT`.

**Testo sostitutivo preciso:**

> Per `target=CANONICAL_COMMIT`, `risk_class` DEVE essere `R2_CONTROLLED` o `R3_HIGH_IMPACT`. `approval.mode=NONE` è vietato. `R2_CONTROLLED` richiede almeno un approvatore umano indipendente; `R3_HIGH_IMPACT` richiede dual control con almeno due approvatori e ruoli conformi a §5.4. Ogni violazione rende il contratto non pubblicabile.

Codificare gli stessi vincoli nel `then` JSON Schema e aggiungere il negativo `CANONICAL_COMMIT/R1_ANALYZE/NONE`.

**Conseguenze:** `AM-02`, `AM-09`, `DRAFT-B/G`, `FR-150`, Action compiler suite.

### PA-04 — Binding e rifiuti canonical (`DRF-008`)

**Sezione:** §3.7 `canonical_commit_binding`, `evidence_requirements`, `error_codes`.

**Testo sostitutivo preciso:** rendere obbligatori per ogni operazione canonical:

```yaml
operation: {enum: [ADMIT_CLAIM, COMMIT_AGGREGATE]}
decision_ref_parameter_path: {type: string, minLength: 1}
authority_ref_parameter_path: {type: string, minLength: 1}
aggregate_ref_parameter_path: {type: string, minLength: 1}
expected_revision_parameter_path: {type: string, minLength: 1}
```

Per `operation=ADMIT_CLAIM` — o quando `produced_assertion_class=CanonicalAssertion` — rendere inoltre obbligatori:

```yaml
claim_parameter_path: {type: string, minLength: 1}
evidence_set_parameter_path: {type: string, minLength: 1}
```

> Ogni path DEVE risolversi in un campo obbligatorio del `parameters_schema`; per `ADMIT_CLAIM` l'evidence set è non vuoto. Merge, split, retraction e altre classi dichiarano binding specifici coerenti con la propria operazione e non sono costrette a fingere una Claim. I rifiuti `C3` sono mappati senza perdita a `PRECONDITION_FAILED`, `INVARIANT_VIOLATION` o `REVISION_CONFLICT`; nessuno viene collassato in successo o retry implicito.

**Conseguenze:** `FR-149/150`, `T29–T31`, `DRAFT-B/G`, error fixtures.

### PA-05 — Rivalidazione all'emissione (`DRF-004`)

**Sezione:** §4.1.2 `ACT-T14`, `ACT-T19`, `ACT-T29` e ogni emissione compensation.

**Testo sostitutivo preciso:**

> Immediatamente prima di ogni emissione fisica e nello stesso critical section dell'acquisizione del fencing/delivery token, il runtime rivalida `G-FRESHNESS ∧ G-DISPATCH` contro il `GatePackage` congelato. Qualsiasi drift di canonical revision, policy digest, Authority, Approval set, ontology/model release, adapter binding o watermark produce `INVALIDATED` e nessun invio. `ACT-T19` richiama integralmente le due guardie; non ne replica un sottoinsieme.

**Conseguenze:** `ARF-006`, `AM-06`, `DRAFT-E`, `FR-162`, concurrency suite.

### PA-06 — Algebra marking (`DRF-005`)

**Sezione:** §3.1.1 `MarkingSchemeDefinition` e §5.3.

**Testo sostitutivo preciso, opzione minima coerente con le formule esistenti:**

```yaml
caveat_semantics: {const: RESTRICTION}
dissemination_control_semantics: {const: RESTRICTION}
```

> Caveat, mandatory marking e dissemination control sono restrizioni e si combinano per unione; purpose e altri permessi si combinano per intersezione. Il validator dello scheme verifica reticolo, chiusura e monotonia. La tassonomia concreta resta sotto `OI-021`.

Se l'authority vuole conservare `PERMISSION`, deve invece definire un `combination_operator` tipizzato per famiglia e sostituire le formule incondizionate: le due opzioni non possono coesistere.

**Conseguenze:** `AM-04/12`, `DRAFT-D/H`, `FR-131`, marking property tests; nessuna chiusura di `OI-021`.

### PA-07 — FSM edge-level (`DRF-006`)

**Sezione:** §4.1/§4.1.2.

**Testo sostitutivo preciso:**

> La tabella è la normal form degli archi: ogni riga contiene un solo `source_state`, un evento, una guardia, un effetto e un solo `destination_state`. Self-loop e no-transition sono rappresentati esplicitamente. Il diagramma è generato da tale tabella e il harness confronta tuple di archi, non soli nomi di stato.

Sostituire l'origine di `ACT-T22` con `OUTCOME_PENDING`; mantenere `ACT-T27` come unico arco `EXECUTION_CONFIRMED→OUTCOME_PENDING`.

**Conseguenze:** `ARF-018`, `AM-18`, harness FSM; nessun cambiamento di evidence status.

### PA-08 — Indeterminate adjudication (`DRF-007`)

**Sezione:** §4.1.1/§4.1.2.

**Testo sostitutivo preciso:**

> Ogni `EXECUTION_INDETERMINATE` o `COMPENSATION_INDETERMINATE` può essere seguito, senza riscrivere lo stato terminale, da un record append-only `IndeterminateEffectAdjudication` contenente `action_instance_ref`, `conflict_scope`, `adjudicator_principal_id`, `authority_ref`, `evidence_refs[1..*]`, `outcome∈{CONFIRMED,FAILED,UNRESOLVED_ACCEPTED_RISK}`, timestamp e audit ref. L'adjudication non trasforma il passato in successo e può soltanto autorizzare una nuova ActionInstance. `conflict_scope` identifica resource/adapter/effect domain; se non calcolabile, il blocco resta fail-closed.

**Conseguenze:** `AM-07`, `DRAFT-F/G`, `FR-163`, Action record model.

### PA-09 — `BA-01` (`DRF-009`)

**Sezione:** §2.6 riga `BA-01` e paragrafo conclusivo.

**Testo sostitutivo preciso:**

> Il fallback a due commit è `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`, non adapter substitution. Resta `NO-GO` per il profilo corrente finché non sono approvate la revisione di §2.3/§6.2, la failure analysis delle crash window e le prove di perdita/duplicazione/recovery. Nessun fallback che modifica un invariante cross-container è qualificato adapter-only.

**Conseguenze:** `AM-28`, `NFR-084`, `RSK-013/019`; ripristina il precedente invariante di sostituibilità senza presumere feature backend.

### PA-10 — Conteggi e change log (`DRF-010`)

**Sezione:** §1.1, §8 `AM-02`, `AM-13`.

**Testo sostitutivo preciso:** sostituire “Sette emendamenti” con “Nove emendamenti”; aggiungere §2.2 ai locator di `AM-02`; dopo PA-14 sostituire `DEC 129/196 → 182/196` con `DEC 129/196 → 183/196` e dichiarare tredici decisioni di processo non allocate. I conteggi devono essere generati dalle righe, non duplicati manualmente.

**Conseguenze:** Document Control, manifest, `AM-02/13`; nessun nuovo `DEC-*`.

### PA-11 — DAG delle bozze (`DRF-011`)

**Sezione:** nota finale del documento bozze.

**Testo sostitutivo preciso:**

> Dipendenze normative minime: `B→G`, `B→E`, `D→H`, `F→G`. L'authority decide prima del voto se `E→I` è vincolante; la decisione e il razionale sono registrati. Una bozza non può essere approvata se una sua dipendenza non è approvata nello stesso change-set o in uno precedente.

**Conseguenze:** solo governance delle nove bozze; nessuna approvazione implicita.

### PA-12 — Conflitto AAP (`DRF-012`)

**Sezioni:** baseline registri e ADD §1.5/§4.2/§7.1. L'authority deve scegliere esattamente una alternativa.

**Alternativa A — mantenere `FR-095 P0/PoC`:**

> `ELM-070` è rimossa formalmente dall'elenco degli elementi interamente differiti per il profilo PoC. Il profilo PoC attiva una thin slice `CounterfactualQuery` AAP per almeno un SCM sintetico pin-nato; ogni capability oltre il perimetro enumerato della thin slice è dichiarata separatamente fuori scope. La conformance suite include un caso positivo completo e il negativo senza factual set.

**Alternativa B — mantenere `ELM-070` interamente differita:**

> `FR-095` è rimosso dal profilo PoC e assegnato alla release in cui `ELM-070` viene attivata. Nel PoC ogni `CounterfactualQuery` restituisce `CAPABILITY_DEFERRED`; nessun criterio PoC dichiara AAP soddisfatta.

**Conseguenze:** registrare tramite change control una decisione autorizzata che confermi o superseda `DEC-103` e, ove necessario, la disposizione congelata da `DEC-196`, senza assegnarne qui l'ID. Aggiornare coerentemente Requirement Register/Index, `CAP-019`, crosswalk `ELM-070`, §7 e acceptance suite. Questa review non sceglie l'alternativa e non modifica in place una decisione approvata.

### PA-13 — Completezza `ObjectSnapshot` (`DRF-013`)

**Sezione:** §3.3 `ObjectSnapshot.required`.

**Testo sostitutivo preciso:** aggiungere:

```yaml
- link_refs
- uncertainty
- explanation_ref
```

> `link_refs` può essere un array vuoto; assenza di incertezza si esprime con `Uncertainty.semantics=NONE`; `explanation_ref` resta risolvibile e policy-filtered, con redazioni dichiarate in `ServedContext`.

**Conseguenze:** `ARF-014`, `AM-14`, `FR-007`, OpenAPI negative fixtures.

### PA-14 — Scope `CAP-024` e decisioni (`DRF-014/015`)

**Sezione:** §6.1, §7, §7.1.

**Testo sostitutivo preciso:**

> Non appartengono al profilo PoC e restano requisiti `Confermato` delle rispettive release: `NFR-060`/`061` Production; `NFR-064`/`074`/`078` MVP. `NFR-071` resta target PoC candidato governato da `OI-008`/`ASM-010`. Nessun requisito `P0/PoC` con obbligo `DEVE` è differito.

Rimuovere `DEC-173` e `DEC-175` dalla lista delle decisioni non allocabili; aggiungere `DEC-173` alla riga Agent Kernel e `DEC-175` a Compiler & Gateway, con overlap Programme & Evidence Governance se motivato. Dichiarare 183/196 `DEC` allocate e tredici esclusioni di processo.

**Conseguenze:** `AM-13/17`, `ARF-013/017`, `FR-166/167`, `NFR-078/082`; preserva stato e release dei registri.

## 13. Final Gate

### Decisione

**`NOT READY FOR DDD`**.

| Dimensione | Conteggio |
|---|---:|
| `BLOCKER` | 2 |
| `CRITICAL` | 4 |
| `MAJOR` | 7 |
| `MINOR` | 2 |
| `OBSERVATION` | 0 |
| **Totale** | **15** |

| Origine | Conteggio |
|---|---:|
| `NEW_IN_V1.1` | 8 |
| `SURVIVING_FROM_V1.0` | 6 |
| `REGRESSION` | 1 |
| **Totale** | **15** |

### Blocker residui

1. `DRF-001`: il GCS non ha una realizzazione cross-contract univoca e la tabella che ne sostiene la copertura è falsa.
2. `DRF-012`: la baseline impone e differisce contemporaneamente AAP nel PoC; la scelta richiede authority/change control, non DDD.

### Condizioni minime per avviare il DDD

- chiusura verificata di entrambi i `BLOCKER` e dei quattro `CRITICAL`;
- definizione ADD-level del binding canonical (`DRF-008`) e correzione di `FR-007`, scope e decision allocation (`DRF-013`–`015`);
- revisione delle bozze secondo il DAG corretto e decisione dell'authority competente, senza approvazione implicita da questa review;
- rerun della suite con positivi e negativi per GCS, AAP, canonical commit, marking e ObjectSnapshot, senza failure rispetto all'oracolo;
- nuova baseline/document version con conteggi e locator rigenerati; nessun uso di fallback `BA-01` finché resta `NO-GO`.

### Elementi legittimamente demandati al DDD

Restano correttamente di livello DDD: layout interno di moduli/classi e storage privati dietro SPI; wire binding generati una volta fissati i semantic field path; implementazione concreta di adapter e reconciliation; indici/cache/topic privati; parametri temporali e capacità dopo preregistrazione; UI concreta entro le role surfaces; dettagli dell'adjudication purché rispettino record, authority, esiti e conflict semantics fissati dall'ADD; fixture e automazione di build. Il DDD non può invece inventare authority, risk floor, scope di baseline, marking algebra o semantica Claim→CanonicalAssertion.

### Stato probatorio finale

La review è documentale e **non incrementa** l'evidenza. Lo stato resta `E1=0`, `E2=0`, zero requisiti `Verified`; tutte le evidence target restano `NOT RUN` salvo future esecuzioni governate. Nessuna tecnologia candidata è dichiarata conforme, nessuna semantica `exact` è trattata come risultato osservato e nessuna capability differita è attivata.
