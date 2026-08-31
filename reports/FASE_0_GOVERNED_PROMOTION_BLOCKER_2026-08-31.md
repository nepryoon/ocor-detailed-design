# FASE 0 — Governed baseline promotion hard-gate report

## Esito

**`BLOCKED — DECISION NAMESPACE COLLISION; PROMOTION NOT STARTED`.**

Il gate 0.3 fallisce: `DEC-197`–`DEC-206` risultano già assegnate e approvate nella
baseline ADD v1.2 presente sia sull'HEAD di lavoro sia su `origin/main`; `DEC-207` è
anch'essa approvata come validation closure. Il record autoritativo dichiara
`DEC-208` come prossimo identificativo disponibile. In applicazione dell'istruzione
del Product Owner e di `AGENTS.md`, l'esecuzione si arresta in FASE 0: nessuna nuova
decisione è stata assegnata e le FASI 1–7 non sono state avviate.

## Controllo dell'esecuzione

| Campo | Valore verificato |
|---|---|
| Repository | `nepryoon/ocor-detailed-design` |
| Data | 2026-08-31 |
| Branch | `codex/add-v1-3-lld-v1-1-remediation` |
| HEAD | `44c095ccbc97e314f3f73f8c6fc3debce9c6f712` |
| HEAD atteso | `44c095c` — corrisponde |
| SHA-256 `AGENTS.md` | `1affb0a0f664f5a7010724d7096e4be585cae1d20ba7e2aa6163af7e79850772` |
| Override | presente alle righe 73–76; `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Integrità sorgenti normative | `PASS`, 8/8 digest corrispondenti |
| Harness iniziale | 13 `PASS`, 0 `FAIL`, 1 `NOT_EXECUTED` |
| Controllo non eseguito | validator semantico OpenAPI 3.1 ufficiale non disponibile nel harness; non dichiarato superato |

## 0.1 — Branch, HEAD e autorizzazione

**Esito: `PASS`.**

Il branch e l'HEAD coincidono con quelli prescritti. L'override locale autorizza la
promozione atomica circoscritta dei cinque registri candidati, ADD v1.3 e LLD v1.1,
preservando il fence probatorio e il `NO-GO` runtime del change set. L'override non
autorizza il riuso o la riscrittura di identificativi decisionali già assegnati.

## 0.2 — Cinque registri candidati enumerati dal repository

I cinque oggetti sono identificati dal package
`reports/OCOR_Full_Memory_Atomic_Register_Promotion_Package_v1.0.md`, dalla directory
`reports/governance_candidates/` e dal manifest
`reports/OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS`.

| Registro | Path candidato completo | SHA-256 calcolato |
|---|---|---|
| Requirement Register | `reports/governance_candidates/OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md` | `9ef4e518073a921646713c35e9bf020d167f7f5086853c86859b5d6cbcbe7efb` |
| Requirement Traceability Index | `reports/governance_candidates/OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md` | `a3c3731f757f568ceb1a7fb22f51a65d927596b1aec5d7728554fdd807276170` |
| Decision Register | `reports/governance_candidates/OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md` | `584faf6de508cfd0bf5c165326123a23effafea988d58a69350c2fe2bf67bfc5` |
| Decision Traceability Index | `reports/governance_candidates/OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md` | `110bc0e69276aa39045462f9553849460259d7ed69f0d68d04c6c9ec28e0c6b4` |
| CAP/ELM Requirement Crosswalk | `reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md` | `0b6480d422fbc3e50b65c9ca18af389fd20cbdc5795aeabc047bbf5ab2a21317` |

I digest calcolati coincidono con il manifest candidato. Il gate candidato registrato
in `reports/tests/full_memory_governance_candidate_results.json` è `PASS` con 11/11
controlli, ma questo non supera la collisione del namespace decisionale.

## 0.3 — Verifica repo-wide del progressivo decisionale

**Esito: `FAIL — HARD BLOCKER`.**

### Ref remoti verificati

Il connettore GitHub ha enumerato tutti i nove branch del repository. Gli HEAD ottenuti
dal connettore coincidono con i corrispondenti `refs/remotes/origin/*` locali:

| Branch remoto | HEAD |
|---|---|
| `codex/add-v1-3-lld-v1-1-remediation` | `44c095ccbc97e314f3f73f8c6fc3debce9c6f712` |
| `codex/add-v1.2-approval-readiness` | `503719e99d513571915dd9f74477eb699aec5f1d` |
| `codex/add-v1.2-remediation` | `44dae00effb88941c64d9eb6a831bdbd294b5df8` |
| `codex/irb-add-lld-exhaustive-audit` | `560e15560c0f17f039062dad10e517ebecba480e` |
| `codex/lld-add-v1.2-alignment` | `61f0a321020318432068859b51ff5c1d97d22b82` |
| `codex/ocor-lld-v1.0` | `8970aef3aec669c0b244c3949482030f1247cb55` |
| `codex/validation-closure-v1.2` | `9ddee28a2417dd4015e5170576d80dae9cb12614` |
| `fase-1` | `627a2ffb1ddfdfa840f7100898dc1f4fe627422f` |
| `main` | `098c680615cf8d8b57cd367386bac10d8acdc715` |

### Evidenza autoritativa della collisione

1. `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md` non è vuoto:
   misura 9.320 byte e ha SHA-256
   `35579536a67122700ff09f6be33874163f5872a199f853b557d28c71af9a0eae`.
   Alla riga 19 assegna esplicitamente `DEC-197`–`DEC-206`; alle righe 23–103
   registra ciascuna decisione con status **Approved** ed effective date 2026-08-30.
2. Lo stesso file su HEAD e `origin/main` è lo stesso blob Git
   `b82c361b81c81070bcffb08b01267d677314447f`; quindi la collisione non è confinata
   a un branch laterale.
3. `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.1_APPROVED.md`
   è un registro autoritativo di 170.664 byte, SHA-256
   `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd`, e dichiara
   il delta approvato `DEC-197`–`DEC-206`.
4. `ocor-runtime/docs/governance_dossier/ARA_VALIDATION_CLOSURE_RECORD_v1.0.md`,
   SHA-256 `5baa9e9d204c0e0ca38099b6263bfc4be4b7dcbd274054c24bfaaaff69819e4f`,
   approva `DEC-207` e alla riga 49 dichiara `DEC-208` come prossimo ID libero.
5. Il supplemento autoritativo
   `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.2_VALIDATION_SUPPLEMENT.md`,
   SHA-256 `6347bcbc1575a0fbfe5304aac7c4b0e8f22aef915304e9aae626b880f0767136`,
   registra `DEC-207` con status **Approved** e `DEC-208` come next ID.
6. La scansione dei 102 commit raggiungibili da tutti i ref, escluso il path protetto
   `inputs/supporting/prior/`, trova fra l'altro i commit storici
   `2678fa86b30dc4eed572046fc8c79292483ab779` (record ARA `DEC-197`–`DEC-206`) e
   `1a227836d324cdf678b22b4a9ceefe5f764b7e4d` (registrazione `DEC-207`).

La baseline immutabile in `inputs/normative/` termina correttamente a `DEC-196` nel
proprio cut-off storico, ma non è l'intera cronologia governance del repository. I
record downstream approvati rendono falsa la precondizione repo-wide «`DEC-197` e
successivi liberi».

### Mappatura storica già efficace delle bozze

Il record ARA esistente ha già cessato l'indipendenza delle bozze e ne conserva la
seguente provenance:

| Bozza | Decisione già efficace |
|---|---|
| `DRAFT-A` | `DEC-197` |
| `DRAFT-G` | `DEC-198` |
| `DRAFT-B` | `DEC-199` |
| `DRAFT-C` | `DEC-200` |
| `DRAFT-E` e contenuto safety-control di `DRAFT-I` | `DEC-202` |
| `DRAFT-F` | `DEC-203` |
| `DRAFT-D` e `DRAFT-H` | `DEC-204` |

`DEC-201`, `DEC-205` e `DEC-206` hanno disposizioni ulteriori già efficaci. Creare ora
una nuova mappatura uno-a-uno `DRAFT-A`–`DRAFT-I` → `DEC-197`–`DEC-205` richiederebbe
riusare gli ID e riscrivere decisioni storiche, entrambe operazioni vietate.

## 0.4 — Immutabilità di `inputs/`

**Esito: `PASS`.**

- `git diff HEAD -- inputs` è vuoto;
- `git diff --cached HEAD -- inputs` è vuoto;
- il tree Git `HEAD:inputs` è `60a73de8e47b38e94aeb0e2b8dedc689fab6eb35`;
- `sha256sum -c inputs/normative/SHA256SUMS` restituisce 8/8 `OK`;
- nessuna operazione di promozione è stata eseguita o pianificata contro `inputs/`.

## 0.5 — Stato probatorio e disposition correnti

La lettura repo-wide impone di distinguere il cut-off della baseline dalla successiva
validation closure:

| Oggetto | Stato corrente verificato |
|---|---|
| `E1` globale della baseline | `0`; il decision record ADD v1.2 conserva esplicitamente `E1=0` |
| Evidenza scoped successiva | `DEC-207` stabilisce separatamente `E1_runtime_slice=PRESENT` per la sola revisione e superficie testata; non equivale a `E1` globale né a runtime conformance del change set full-memory |
| `E2` | non stabilita / `0` |
| Requisiti globalmente `Verified` | `0`; `DEC-207` vieta la promozione automatica |
| Capability | restano `Design Target`; `CAP-026` resta `OUT_OF_SCOPE` |
| Tecnologie | TypeDB 3.x, TerminusDB, Jena, Kafka/Strimzi, Temporal/PostgreSQL, Keycloak, SPIRE, OPA, OpenBao, OpenTelemetry, Prometheus, Jaeger e storage S3-compatible/Ceph restano `Candidate Implementation` |
| Capability differite della baseline | non attivate; in particolare `FR-048` ed `ELM-011` restano differiti |
| Full governed agent memory | i cinque snapshot restano candidati; `FGM-01`–`FGM-20` non sono promossi a evidenza; `NO-GO` runtime del change set resta invariato |

La presenza di `E1_runtime_slice=PRESENT` è riportata perché è una decisione già
approvata e successiva al cut-off `E1=0`; ometterla renderebbe inesatta la fotografia
corrente. Non viene usata per elevare alcun requisito o per dichiarare conformance del
change set autorizzato.

## Disposizione di arresto

- Nessun `DEC-*` è stato creato, riutilizzato o modificato.
- Nessuno dei cinque registri candidati è stato promosso.
- ADD v1.3 e LLD v1.1 non sono stati consolidati.
- Nessun manifest o digest autoritativo è stato aggiornato.
- Nessuna pull request è stata aperta.
- L'unica nuova scrittura è il presente report sotto `reports/`.

Per rendere eseguibile una futura promozione serve una nuova disposizione esplicita
dell'autorità che riconcili il change set con la storia già efficace e autorizzi il
prossimo ID realmente libero (`DEC-208` al momento di questa verifica), senza alterare
o riusare `DEC-197`–`DEC-207`. Tale autorizzazione non può essere inferita dall'override
attuale, che non consente di sostituire decisioni storiche.
