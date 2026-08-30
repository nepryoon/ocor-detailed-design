# STEP 4 — Governed Context Set e algebra dei marking

## Veridicità della tabella §3.0.1

La tabella non è veritiera per tutte le superfici dichiarate. I tre contratti formali sincroni sono coerenti sulla maggior parte dei campi, ma i record testuali che §3.0.1 marca con `✔` non usano il nome e la cardinalità normativa, oppure non contengono affatto il campo.

| Campo | Superficie dichiarata `✔` | Testo effettivo | Esito |
|---|---|---|---|
| `domain_id` | `HandoffEnvelope` §4.3 | `domain` (§4.3, riga ADD 2811) | `FAIL` |
| `domain_id` | `SecurityContext` §5.3 | `domains[]` (§5.3, riga 2956) | `FAIL` |
| `domain_id` | Osservabilità §6.3 | `domain` (riga 3181 circa) | `FAIL` |
| `domain_id` | `ScenarioRunSpec` §4.2, soggetto al claim generale di §1.4 | `domain`, non `domain_id` | `FAIL` |
| `principal_id` | `HandoffEnvelope` §4.3 | `sender_principal` e `recipient_principal`, nessun mapping normativo al Principal effettivo | `AMBIGUO` |
| `principal_id`, `actor_chain`, `correlation_id` | `ScenarioRunSpec` §4.2, che dichiara di realizzare il set | Assenti dalla lista dei campi | `FAIL` |

La §3.0.3 vieta espressamente forme alternative e la §1.4 rende il set normativo per chiamate, eventi, log e artefatti derivati. Non è quindi una mera preferenza lessicale: generatori, cache key, policy input e audit non possono assumere una struttura univoca. Il difetto invalida la prova usata da `AM-01` per sostenere la chiusura di un precedente `BLOCKER`.

Classificazione: `DRF-001`, `BLOCKER`, confidence `HIGH`, locator §3.0.1/§3.0.3, §4.2, §4.3, §5.3, §6.3; related `AM-01`, `DRAFT-A`, `FR-006`, `NFR-006`, `NFR-040`, `TB-CXT-05`.

Remediation esatta: sostituire `domain`/`domains[]` con `domain_id` dove il GCS richiede il singolo dominio effettivo; se una lista di domain scope serve alla Delegation, conservarla con un nome distinto e definire la derivazione del singolo `domain_id`. Aggiungere i campi mancanti o una regola di derivazione attestata, campo per campo, a Scenario e Handoff. Rigenerare la tabella da un inventory machine-readable e aggiungere conformance fixture per tutte le sei superfici più Scenario/Event.

## Origine di `principal_id` nell'Ingestion Envelope

La scelta di non accettare `principal_id` e `actor_chain` come asserzioni libere del chiamante è corretta in linea di principio. La realizzazione dell'envelope, però, non la attua in modo coerente:

- §1.4 e §3.0.1 dicono che `principal_id` deriva dal transport security context e non è mai asserito dal body;
- §3.0.1 marca il campo come realizzato tramite `integrity.producer_principal_ref`;
- §3.2 rende `integrity.producer_principal_ref` un campo obbligatorio del payload JSON chiuso;
- le regole runtime di §3.2 elencano i campi assegnati o verificati dal trusted ingress boundary, ma non includono `producer_principal_ref` fra quelli sostituiti o vincolati al Principal autenticato.

Un caller può quindi presentare un `producer_principal_ref` sintatticamente valido per un Principal diverso; lo schema lo accetta e il testo non impone il confronto con il transport binding. Inoltre “producer della sorgente” e “Principal effettivo della chiamata” possono essere identità diverse e non devono essere collassate senza una relazione attestata.

Classificazione: `DRF-002`, `CRITICAL`, confidence `HIGH`, locator §3.0.1 e §3.2; related `AM-01`, `DRAFT-A`, `FR-006`, `RSK-006`, `TB-CXT-02`, `TB-CXT-05`.

Remediation esatta: distinguere `source_producer_principal_ref` (asserzione della sorgente, se necessaria) da `effective_principal_id` derivato dal trasporto; non consentire al payload di impostare il secondo. Specificare che il boundary sovrascrive/crea l'attestazione e verifica l'eventuale producer dichiarato contro il binding autorizzato, con mismatch ⇒ `POLICY_DENIED`/quarantine e Audit Record.

## Calcolabilità e monotonia del marking

`levels`, `dominance_relation`, `join_rule=LATTICE_JOIN`, elemento massimo e comportamento sugli incomparabili sono sufficienti a rendere calcolabile il join della **classification level**, a condizione che lo scheme concreto passi una validazione di reticolo. Il costrutto non definisce però un'algebra coerente per tutte le famiglie:

- §3.1.1 consente `caveat_semantics` e `dissemination_control_semantics ∈ {RESTRICTION, PERMISSION}`;
- §5.3 dichiara incondizionatamente `caveats`, `mandatory_markings` e `dissemination_controls` come restrizioni e applica l'unione;
- lo stesso §5.3 afferma che l'operatore dipende dalla semantica dichiarata nello scheme.

Uno scheme valido con `dissemination_control_semantics=PERMISSION` è dunque ammesso dal metamodello ma processato dalla formula di unione per restrizioni. Per insiemi di permessi, l'unione amplia l'accesso e non è monotona in senso conservativo. `incomparable_behavior=MOST_RESTRICTIVE` è inoltre nominato ma non definisce come costruire il valore massimo per label/caveat non ordinati.

Classificazione: `DRF-005`, `CRITICAL`, confidence `HIGH`, locator §3.1.1 e §5.3; related `AM-04`, `AM-12`, `DRAFT-D`, `DRAFT-H`, `FR-131`, `NFR-006`, `OI-021`.

Remediation esatta, scegliendo una sola semantica:

1. se queste famiglie sono sempre restrizioni, sostituire entrambi gli enum con `const: RESTRICTION` e rimuovere il claim di variabilità; oppure
2. se possono essere permessi, definire per ogni famiglia `combination_operator ∈ {UNION,INTERSECTION,LATTICE_JOIN}`, vincolarlo alla semantica e applicarlo nella formula; aggiungere l'ordine o la funzione `most_restrictive` per valori incomparabili.

In entrambi i casi il validator dello scheme deve verificare chiusura, associatività, commutatività, idempotenza, esistenza del join e monotonia. La tassonomia concreta resta correttamente aperta sotto `OI-021`; correggere l'algebra non la chiude implicitamente.

## Valutazione delle due assenze deliberate

- `principal_id` e `actor_chain` assenti dai body sincroni Query/Invocation: scelta corretta, perché derivati dal trasporto e dalla Delegation verificata.
- Assenza senza un campo attestato nel contesto di esecuzione o senza mapping nei record derivati: non corretta. “Derivato” non significa “inesistente”; deve essere disponibile a policy, audit, cache key e trace.

Conclusione: la razionalizzazione è valida per i request body sincroni, ma viene estesa oltre il suo campo di applicazione e non sana le omissioni/mappature incoerenti sopra elencate.
