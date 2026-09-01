# Riconciliazione `origin/main` vs branch — 2026-08-31

## 1. Verdetto esecutivo

**`STOP AFTER FASE A — NEW DECISION AND BASELINE SUPERSESSION REQUIRED`.**

La baseline autoritativa corrente è ADD v1.2, non v1.3. ADD v1.3 e LLD v1.1
esistono soltanto come candidate sul branch. La loro promozione dipende dal change set
`CC-FULL-GOVERNED-AGENT-MEMORY`, che:

1. deve supersedere esclusivamente la clausola di differimento di `ELM-084` in
   `DEC-196` mediante una nuova decisione;
2. deve usare il prossimo identificativo libero `DEC-208`;
3. modifica la semantica della baseline ADD v1.2 e dei cinque registri approvati;
4. non è riproducibile dai cinque registri autoritativi correnti: i candidati dichiarano
   digest di base diversi da quelli presenti su `origin/main` e i generatori puntano a
   sorgenti `audit-src/` assenti o a fallback con path errato.

Sono quindi vere le stop condition **(a)** e **(b)**. Nessun artefatto normativo è
stato scritto o modificato durante questa riconciliazione.

## 2. Control record

| Campo | Valore verificato |
|---|---|
| Repository | `nepryoon/ocor-detailed-design` |
| Branch locale | `codex/add-v1-3-lld-v1-1-remediation` |
| HEAD locale dopo A.1 | `caa349920d6bff745e74b9458bfbc71df33ebee9` |
| Branch remoto omonimo | `44c095ccbc97e314f3f73f8c6fc3debce9c6f712` |
| `origin/main` verificato anche via connettore GitHub | `098c680615cf8d8b57cd367386bac10d8acdc715` |
| Merge-base | `098c680615cf8d8b57cd367386bac10d8acdc715` |
| Divergenza `origin/main...HEAD` | main-only `0`; branch-only `6` |
| SHA-256 `AGENTS.md` | `1affb0a0f664f5a7010724d7096e4be585cae1d20ba7e2aa6163af7e79850772` |
| Tree `HEAD:inputs` | `60a73de8e47b38e94aeb0e2b8dedc689fab6eb35` |
| Integrità normativa | 8/8 `OK` |

## 3. A.1 — Commit isolato del blocker report

Il report `reports/FASE_0_GOVERNED_PROMOTION_BLOCKER_2026-08-31.md`, SHA-256
`088000119283d1f34f4ab6233ada6f6398fba028290738c060129bdf006f503a`, è stato
committato da solo:

| Commit | Messaggio | File |
|---|---|---|
| `caa349920d6bff745e74b9458bfbc71df33ebee9` | `Record FASE 0 governed promotion blocker` | solo `reports/FASE_0_GOVERNED_PROMOTION_BLOCKER_2026-08-31.md` |

Il commit è locale e non è stato pushato durante la FASE A.

## 4. A.2 — Topologia Git e strategia di allineamento

### 4.1 Commit branch-only

| Commit | Data | Oggetto |
|---|---|---|
| `47724c52d8f88aa5e69d27747904b4d97b7f615c` | 2026-08-31 | Prepare ADD v1.3 and LLD v1.1 alignment candidates |
| `7fbda65655054123c1adeacceab56fa7f18e43e7` | 2026-08-31 | Expand PoC to full governed agent memory |
| `4393cb20cebcde3cea6bfec742867870c687ef42` | 2026-08-31 | Add atomic full-memory register candidate updates |
| `3b26e2ed1de3dcf91f5b7b6c0f06b0f945bacdbc` | 2026-08-31 | Propose governed AGENTS promotion exception |
| `44c095ccbc97e314f3f73f8c6fc3debce9c6f712` | 2026-08-31 | Authorize governed baseline promotion |
| `caa349920d6bff745e74b9458bfbc71df33ebee9` | 2026-08-31 | Record FASE 0 governed promotion blocker |

### 4.2 Strategia proposta

`origin/main` è già antenato di HEAD. Non occorre eseguire merge o rebase per
allineare il branch alla main corrente; un merge di `origin/main` nel branch sarebbe
`Already up-to-date`. Se `main` non avanza, l'integrazione del branch verso main è
topologicamente fast-forwardable. Prima di un futuro push/PR va comunque riverificato
l'HEAD remoto tramite connettore GitHub.

### 4.3 Conflitti attesi file per file

Poiché main ha zero commit esclusivi e tutti i path aggiunti sono assenti al merge-base,
non sono attesi conflitti nello stato verificato:

| Path | Delta branch | Conflitto atteso |
|---|---|---|
| `AGENTS.md` | modificato | nessuno; main non ha modifiche dopo il merge-base |
| `reports/AGENTS_GOVERNED_PROMOTION_OVERRIDE.patch` | aggiunto | nessuno |
| `reports/FASE_0_GOVERNED_PROMOTION_BLOCKER_2026-08-31.md` | aggiunto | nessuno |
| `reports/OCOR_ADD_v1.3_Candidate.md` | aggiunto | nessuno |
| `reports/OCOR_Change_Control_Full_Governed_Agent_Memory_v1.0.md` | aggiunto | nessuno |
| `reports/OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS` | aggiunto | nessuno |
| `reports/OCOR_Full_Memory_Atomic_Register_Promotion_Package_v1.0.md` | aggiunto | nessuno |
| `reports/OCOR_IRB_ADD_LLD_REMEDIATION_SHA256SUMS` | aggiunto | nessuno |
| `reports/OCOR_IRB_ADD_LLD_Remediation_Closure_v1.0.md` | aggiunto | nessuno |
| `reports/OCOR_LLD_v1.1_Candidate.md` | aggiunto | nessuno |
| `reports/contracts/capability-lease.schema.json` | aggiunto | nessuno |
| `reports/contracts/governed-context.schema.json` | aggiunto | nessuno |
| `reports/contracts/governed-memory-item.schema.json` | aggiunto | nessuno |
| `reports/contracts/ocor-governed-memory.openapi.yaml` | aggiunto | nessuno |
| `reports/contracts/ocor-named-query-gateway.openapi.yaml` | aggiunto | nessuno |
| `reports/contracts/ocor_registry.proto` | aggiunto | nessuno |
| `reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md` | aggiunto | nessuno |
| `reports/governance_candidates/OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md` | aggiunto | nessuno |
| `reports/governance_candidates/OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md` | aggiunto | nessuno |
| `reports/governance_candidates/OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md` | aggiunto | nessuno |
| `reports/governance_candidates/OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md` | aggiunto | nessuno |
| `reports/tests/build_full_memory_governance_candidates.py` | aggiunto | nessuno |
| `reports/tests/build_lld_v1_1_assurance.py` | aggiunto | nessuno |
| `reports/tests/full_memory_governance_candidate_results.json` | aggiunto | nessuno |
| `reports/tests/lld_v1_1_assurance_results.json` | aggiunto | nessuno |
| `reports/tests/materialize_add_contracts.py` | aggiunto | nessuno |
| `reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.json` | aggiunto | nessuno |
| `reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.md` | aggiunto | nessuno |

L'assenza di conflitti Git non implica promuovibilità normativa dei candidati.

## 5. A.3 — Stato autoritativo effettivo su `origin/main`

### 5.1 Baseline architetturale e documenti di governance

| Artefatto | Path | SHA-256 | Stato dichiarato | Commit del contenuto corrente |
|---|---|---|---|---|
| ADD v1.2 | `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md` | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` | **APPROVED BASELINE**, effective 2026-08-30, `DEC-197`–`DEC-206` | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| ARA decision record | `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md` | `35579536a67122700ff09f6be33874163f5872a199f853b557d28c71af9a0eae` | completo; authority Luca Lillo, Product Owner/ARA; effective 2026-08-30; copre `DEC-197`–`DEC-206` | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| Validation closure | `ocor-runtime/docs/governance_dossier/ARA_VALIDATION_CLOSURE_RECORD_v1.0.md` | `5baa9e9d204c0e0ca38099b6263bfc4be4b7dcbd274054c24bfaaaff69819e4f` | **APPROVED VALIDATION CLOSURE**, `DEC-207`; prossimo ID `DEC-208` | `6eb41750eede68a494b23a4c4656ff704dedd210` |
| Verification evidence | `ocor-runtime/VERIFICATION_EVIDENCE_REPORT.md` | `cf57a5a463a10c15e0356cbe1af18d44e0f007423abffb4a9b3423163c1df0b2` | popolato; `E1_runtime_slice=PRESENT`; E2 e global `Verified` non stabiliti | `6eb41750eede68a494b23a4c4656ff704dedd210` |
| Approval manifest | `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVAL_SHA256SUMS` | `8d6b7125ddb77a78efff7521f78634b2f59f03eb2662ae4e6485d4244661dc88` | 7/7 artefatti `OK` nella verifica corrente | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| Validation evidence manifest | `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_VALIDATION_EVIDENCE_SHA256SUMS` | `fde0611b9aa1f950b9c599a3ee3d71d89ac353a21cb40b9e0ebe8efeffbdc073` | tutte le 31 entry `OK` nella verifica corrente | `6eb41750eede68a494b23a4c4656ff704dedd210` |

`OCOR_ADD_v1.2_APPROVED_BASELINE.md` e `ARA_DECISION_RECORD_v1.1.md` erano file
scaffold da 0 byte al commit `ddfa97d1cacec23afdf767702c7c0fd816e66431`; sono stati
popolati rispettivamente a 227.866 e 9.320 byte dal commit
`d76cd30c5eef0e21e53e84dafdb3bfdf21e50187`. Oggi non sono vuoti.

Su `origin/main` non esistono file autoritativi a 0 byte. I soli file vuoti sono sei
`.gitkeep` strutturali.

### 5.2 Versioni ADD e LLD presenti

| Versione | Path | SHA-256 | Stato | Commit corrente/origine |
|---|---|---|---|---|
| ADD v1.1 | `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md` | `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` | sorgente immutabile candidata storica | `e0a24e937e74423adf922058a0d8c5f03228b2b5` |
| ADD v1.2 Candidate | `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md` | `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f` | candidata incorporata per valore; wording candidato superseduto dal control block approvato | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| ADD v1.2 Approved | `ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md` | `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` | baseline autoritativa corrente | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| ADD v1.3 | assente su `origin/main`; candidato branch `reports/OCOR_ADD_v1.3_Candidate.md` | candidato `99f3d17d480eb2b3346524a0820dcdbbedfbe43b091428a86e8677ce8030ed22` | emendamento di 12.036 byte, `PROPOSED`; non baseline consolidata per valore | candidato: `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| LLD v1.0 | `docs/OCOR_LLD_v1.0.md` | `9400d05c4eadc7f36df940d565f35ffe7bdf7d0400b3bf938444d6b9f793025d` | dichiara ADD-aligned, ma audit esaustivo successivo lo classifica **NOT APPROVABLE / NO-GO** | `92de7d20496eed52ad770de01f7148b6217cf80c` |
| LLD v1.1 | assente su `origin/main`; candidato branch `reports/OCOR_LLD_v1.1_Candidate.md` | candidato `1a5d5d448950cadfd09a177a6d91566e878b26a9f8a4cd481cb618ecd1401414` | `PROPOSED — AWAITING GOVERNED DECISION` | candidato: `47724c52d8f88aa5e69d27747904b4d97b7f615c` |

L'audit autoritativo di allineamento è
`reports/OCOR_IRB_ADD_LLD_Exhaustive_Alignment_Audit_v1.0.md`, SHA-256
`fe0b85b4ec5f349e8f7961880f710fc30241a50f50ec55e0792dacaa4db6ad1a`, commit
`098c680615cf8d8b57cd367386bac10d8acdc715`: ADD 285/285, LLD 0/285,
sette `BLOCKER` e undici `MAJOR` complessivi nell'audit narrativo.

### 5.3 Cinque registri autoritativi

| Registro | Path su main | SHA-256 | Stato | Commit |
|---|---|---|---|---|
| Requirement Register | `ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Register_v1.0_APPROVED.md` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | autoritativo ADD v1.2; 285 requisiti, zero global `Verified` | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| Requirement Traceability Index | `ocor-runtime/docs/governance_dossier/registers/OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | autoritativo; 285/285, E1=0/E2=0 al cut-off | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| Decision Register | `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Register_v1.1_APPROVED.md` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | autoritativo; `DEC-001`–`DEC-206` | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| Decision Traceability Index | `ocor-runtime/docs/governance_dossier/registers/OCOR_Decision_Traceability_Index_v1.1_APPROVED.md` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | autoritativo; storico 196/196 più trace `DEC-197`–`DEC-206` | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |
| CAP/ELM Crosswalk | `ocor-runtime/docs/governance_dossier/registers/OCOR_CAP_ELM_Requirement_Crosswalk_v1.0_APPROVED.md` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | autoritativo; CAP 26/26, ELM 103/103; `ELM-084` ancora differito | `d76cd30c5eef0e21e53e84dafdb3bfdf21e50187` |

`DEC-207` è correttamente separata nel supplemento
`registers/OCOR_Decision_Register_v1.2_VALIDATION_SUPPLEMENT.md`, SHA-256
`6347bcbc1575a0fbfe5304aac7c4b0e8f22aef915304e9aae626b880f0767136`, commit
`6eb41750eede68a494b23a4c4656ff704dedd210`.

Il manifest di approvazione dei cinque registri e dei due documenti di controllo passa
7/7. La consistenza di questa baseline non rende però coerente ADD↔LLD: l'audit main
misura 0/285 allocazioni LLD.

### 5.4 Provenienza non valida dei cinque candidati full-memory

I file candidati sono integri rispetto ai propri manifest, ma non derivano in modo
riproducibile dai registri autoritativi correnti:

| Registro | Digest base dichiarato dal candidato | Digest autoritativo su main | Esito |
|---|---|---|---|
| Requirement Register | `87c11271ed5193d24ca6e782378c9e779c42c2e7b4a93ef7630f825de78be991` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | `MISMATCH` |
| Requirement Traceability Index | `f604bc963bd7006eb02f1524e741c7859e1a8c4b2e050568f6ce812a50f1b080` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | `MISMATCH` |
| Decision Register | `b3f380362da89da202aed9c8dfa4868367661d41ab3590295bafab51bbceccb9` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | `MISMATCH` |
| Decision Traceability Index | `cabffb130078209a25c4c7ac66d6bdc8500fa009bd0897d9612f5fbd13e330e1` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | `MISMATCH` |
| CAP/ELM Crosswalk | `dbe1590ed72d21d56144b40f4543ef1f0de61f781d9fceb004c5500942cc2b80` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | `MISMATCH` |

Nessuno dei cinque digest dichiarati è presente nella cronologia dei corrispondenti
path autoritativi. Inoltre:

- `build_full_memory_governance_candidates.py` cerca prima
  `audit-src/<registro>` e poi
  `ocor-runtime/docs/governance_dossier/<registro>`;
- `build_lld_v1_1_assurance.py` usa la stessa impostazione per Requirement Register e
  Requirement Traceability Index;
- `audit-src/` non esiste nel repository;
- i registri reali sono sotto `ocor-runtime/docs/governance_dossier/registers/`, path
  che i due generatori non considerano.

Pertanto gli esiti 11/11 e 55/55 consegnati sono snapshot integri ma **non
riproducibili dalla baseline corrente**. Non sono stati rieseguiti in FASE A perché
scrivono candidate, matrici, risultati e manifest, attività vietata nella fase
read-only.

### 5.5 Contratti su main

L'ADD v1.2 approvato incorpora normativamente i contratti della tabella seguente. Per
ciascuna riga il contenitore autoritativo è
`ocor-runtime/docs/governance_dossier/OCOR_ADD_v1.2_APPROVED_BASELINE.md`, SHA-256
`c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f`, commit
`d76cd30c5eef0e21e53e84dafdb3bfdf21e50187`; non esiste un file standalone approvato
separato.

| Contratto incorporato | Versione |
|---|---|
| JSON Schema Signed Canonical IR | `urn:ocor:schema:signed-canonical-ir:1.0` |
| JSON Schema Canonical Ingestion Envelope | `urn:ocor:schema:canonical-ingestion-envelope:1.2` |
| JSON Schema MCP Tool Contract | `urn:ocor:schema:mcp-tool-contract:1.2` |
| JSON Schema Action Type Contract | `urn:ocor:schema:action-type-contract:1.1` |
| JSON Schema Event Subscription Contract | `urn:ocor:schema:event-subscription-contract:1.1` |
| Named Query Gateway | OpenAPI `3.1.0`, API `1.2.0` |
| Function/Model Registry | Proto3, package `ocor.registry.v1` |

I file runtime, validati da `DEC-207` come superficie implementativa scoped, sono:

| Path | Versione/ID | SHA-256 | Stato | Commit |
|---|---|---|---|---|
| `ocor-runtime/schemas/ocor.openapi.yaml` | OpenAPI 3.1.0, API 1.2.0 | `daccb53edc6ce6cfebf0fbe659e46bea6f47ecfea94051e7ab3e9c7ecf44c006` | runtime compatibility surface | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/ocor_runtime.proto` | Proto3, `ocor.runtime.v1` | `7bb683461be95f49cf984ca8acdb818ea7fdce18962fee519b1d28b07c9733b0` | runtime compatibility surface | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/action.schema.json` | `/v1.2/action.schema.json` | `f44dc78c3b5939f6a9fac8a331c037fb141149fb73ecb968b0e480d427781d7c` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/agent-response.schema.json` | `/v1.2/agent-response.schema.json` | `73e59a096398ff14a7842229312f1d2b81811203f6f1de271547791834c9b316` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/capability-lease.schema.json` | `/v1.2/capability-lease.schema.json` | `555bd93af8097b2fdaecb740c72b76db74a2510b64cabdeb6b26adeea0c0e34c` | runtime schema; non uguale al record chiuso ADD secondo l'audit | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/evidence.schema.json` | `/v1.2/evidence.schema.json` | `02adccfc18acac3b18848c1f5c6589434551a7d905f38128280addc94ccfe090` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/identity-record.schema.json` | `/v1.2/identity-record.schema.json` | `0dfaa16d6ffbfe605c2d8db48977cf2d959eebcf3c994b8b7c1aed22e4b2d74b` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/marking-scheme-definition.schema.json` | `/v1.2/marking-scheme-definition.schema.json` | `793cd7925cd92dc80215488be71d7eb0f6bc770055cea03358d2ef836b4c8bba` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/outbox-event.schema.json` | `/v1.2/outbox-event.schema.json` | `cbf92d486a79489b6bda0bdc2fc2cfcd57978602b3275b3d879546466382e0d0` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |
| `ocor-runtime/schemas/semantic-envelope.schema.json` | `/v1.2/semantic-envelope.schema.json` | `f0b689a66ca9b22901c9f6288b771e6126d3008a29e4a53d156a60d797a7e48d` | runtime schema | `ddfa97d1cacec23afdf767702c7c0fd816e66431` |

I file standalone approvati dichiarati dall'LLD v1.0
`schemas/openapi/ocor-named-query-gateway.openapi.yaml` e
`schemas/proto/ocor_registry.proto` non esistono su main. Il branch materializza
candidate byte-identiche ai blocchi ADD:

| Path candidato | SHA-256 | Stato | Commit |
|---|---|---|---|
| `reports/contracts/ocor-named-query-gateway.openapi.yaml` | `652403f5aab29312452f9814a0fe87f74b6a142c361de415c4d79b3b8406e03e` | OpenAPI 3.1.0 / API 1.2.0, candidato | `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| `reports/contracts/ocor_registry.proto` | `7de0aa5f592a013f2f067866ce6dbb27c1ecbffefcc14eb3a0e0d959bfc24694` | Proto3 `ocor.registry.v1`, candidato | `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| `reports/contracts/governed-context.schema.json` | `04671e932f7378c34b07fc01881755c7c5af66787ef2f6a3ca2da5bd86c22a88` | record ADD v1.2 materializzato, candidato | `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| `reports/contracts/capability-lease.schema.json` | `d16951ad374f33138541370d55d0cd474ae0672ae3fa0a134d0a10ae030ddf0e` | record ADD materializzato, candidato | `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| `reports/contracts/governed-memory-item.schema.json` | `8d0167be6467a8cfb4e41e4c7cc1e8f207b578456238a7da41f7a4da091e47b5` | full-memory 1.0, non approvato | `47724c52d8f88aa5e69d27747904b4d97b7f615c` |
| `reports/contracts/ocor-governed-memory.openapi.yaml` | `526caa147715aaffc6d4003889db1111e50d6cd17cd9fc61dbfad28f58343d9b` | OpenAPI 3.1.0 / API 1.0.0 full-memory, non approvato | `7fbda65655054123c1adeacceab56fa7f18e43e7` |

### 5.6 Stato probatorio e validator `NOT_EXECUTED`

- baseline architecture cut-off: `E1=0`, `E2=0`, zero requisiti globalmente
  `Verified`;
- `DEC-207`: `E1_runtime_slice=PRESENT` soltanto per revisione e superficie testata;
- capability: `Design Target`; tecnologie: `Candidate Implementation`;
- `FR-048` ed `ELM-011` restano differiti;
- full-memory resta `NO-GO` e `FGM-01`–`FGM-20` non sono evidence approvate.

Il harness corrente riporta:

```text
OpenAPI — validazione semantica con validator ufficiale: NOT_EXECUTED
```

Il controllo è identificato e non viene contato come `PASS`. Il tentativo read-only di
caricare il validator nella `.venv` prescritta è fallito con
`ModuleNotFoundError: No module named 'openapi_spec_validator'`; l'installazione è
vietata. Separatamente, `DEC-207` ha già accettato l'esecuzione governata e pinned di
`openapi-spec-validator==0.9.0`: profilo, OpenAPI embedded ADD e OpenAPI runtime
risultano 3/3 `PASS` nella GitHub Actions run `33334792715`. Il risultato storico non
trasforma il `NOT_EXECUTED` dell'harness corrente in `PASS`.

## 6. A.4 — Mappatura effettiva `DRAFT-*` / decisioni

La premessa “nove bozze = nove decisioni più una decima” non descrive la mappatura
effettiva: due coppie di draft sono state consolidate in decisioni uniche e tre
decisioni non provengono direttamente da una bozza.

| Decisione | Change set / origine | Draft ratificati | Disposizione |
|---|---|---|---|
| `DEC-197` | `CC-GCS` | `DRAFT-A` | Governed Context Set |
| `DEC-198` | `CC-ACTION-EVENT-CONTRACTS` | `DRAFT-G` | baseline contratti ACTION/EVENT |
| `DEC-199` | `CC-CANONICAL-PATH` | `DRAFT-B` | unico percorso di mutazione canonica |
| `DEC-200` | `CC-SINGLE-WRITER-BRANCH-SCOPE` | `DRAFT-C` | single writer, branch scope e relay |
| `DEC-201` | `CC-BA01-ALTERNATIVE`, da `DRF-009` / `BA-01` | nessuno | atomicità state+revision+idempotency+outbox; nessun fallback implicito |
| `DEC-202` | `CC-EMISSION-FENCE` | `DRAFT-E` e contenuto safety-control di `DRAFT-I` | EMISSION-FENCE e CapabilityLease temporale |
| `DEC-203` | `CC-INDETERMINATE-ADJUDICATION` | `DRAFT-F` | adjudication degli effetti indeterminati |
| `DEC-204` | `CC-MARKING-ALGEBRA` | `DRAFT-D` e `DRAFT-H` | algebra marking fail-closed |
| `DEC-205` | `CC-FR095-SCOPE`, da `DRF-012` | nessuno | `FR-095` P0/MVP; `ELM-070` differito |
| `DEC-206` | `CC-DEC-ALLOCATION`, da `DRF-015` / `V12-AM-13` | nessuno | alloca `DEC-173` ad Agent Kernel e `DEC-175` a Compiler & Gateway; separa 183 decisioni subsystem/programme da 13 document/programme e preserva coverage 196/196 |

`DEC-206` è quindi la decima decisione numerica del range, ma non l'unica decisione
non derivata da un draft.

## 7. A.5 — Stato di chiusura `ARF-001`–`ARF-027`

Il control block della baseline approvata supersede gli stati `PROPOSED` e
`PENDING_CHANGE_CONTROL` conservati nel testo incorporato. Nessun `ARF-*` resta aperto
come finding documentale ADD. Quando non esiste una DEC dedicata, la chiusura deriva
dall'incorporazione dell'emendamento non-CC nella baseline approvata sotto l'insieme
ARA `DEC-197`–`DEC-206`; non viene inventata una decisione puntuale.

| Finding | Trattamento normativo | Autorità di chiusura | Stato corrente |
|---|---|---|---|
| `ARF-001` | GCS completo e binding Principal | `DEC-197` | `CLOSED` |
| `ARF-002` | canonical mutation path | `DEC-199` con dipendenza da `DEC-198` | `CLOSED` |
| `ARF-003` | single writer / branch scope | `DEC-200` | `CLOSED` |
| `ARF-004` | conservative join e rinomina dissemination controls | `DEC-204` | `CLOSED` |
| `ARF-005` | quorum, ruoli ed Evidence non vuoti | `DEC-198` | `CLOSED` |
| `ARF-006` | guardie dispatch/emission atomiche | `DEC-202` | `CLOSED` |
| `ARF-007` | indeterminate outcomes e adjudication | `DEC-203` | `CLOSED` |
| `ARF-008` | completamento `Problem` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-009` | contratti ACTION/EVENT e replay bounded | `DEC-198` | `CLOSED` |
| `ARF-010` | irreversibility/retry/effect-tier constraints | `DEC-198` | `CLOSED` |
| `ARF-011` | vocabolario `CapabilityDisposition` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-012` | `MarkingSchemeDefinition` | `DEC-204` | `CLOSED`; `OI-021` resta aperta |
| `ARF-013` | coverage e allocazione decisionale globale | `DEC-206` | `CLOSED` |
| `ARF-014` | `ObjectSnapshot` completo | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-015` | corrispondenza viste C4 | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-016` | CapabilityLease distinto da `ELM-080` | `DEC-202` | `CLOSED` |
| `ARF-017` | scope esplicito `CAP-024` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-018` | bijezione diagramma/tabella FSM | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-019` | vincolo CDC bidirezionale | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-020` | `compartments[]` uniforme | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-021` | semantica `*_marking_ref` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-022` | validity temporale policy bundle | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED`; `OI-016` resta aperta |
| `ARF-023` | collegamenti `EV-*` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-024` | precedenza reason code causali | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-025` | `Problem.detail` / `instance` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-026` | no effect estimate in `ABSTAIN` | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |
| `ARF-027` | `ModelResult.oneof` obbligatorio | baseline ADD v1.2; nessuna DEC dedicata | `CLOSED` |

I finding successivi `IALLD-*` non riaprono implicitamente gli `ARF-*`; sono un
registro distinto e governano il gap LLD/full-memory.

## 8. Source limitations preservate

La fonte tracciata è
`inputs/supporting/prior/OCOR_ADD_Critical_Review_v1.0.md`, SHA-256
`13dca8bf94476434cf7a0434809b0d42a57d59dfc8546d363d5ffc29b729d727`, commit
`eae86ce96e0a2ecb014683e6474f65381bd6f4aa`. La restrizione di `AGENTS.md` vieta
l'apertura di `inputs/supporting/prior/` durante la FASE 1; questa verifica appartiene
alla distinta FASE A e non ha scritto in `inputs/`.

| ID | Limitazione registrata | Verifica sul repository corrente | Stato di riconciliazione |
|---|---|---|---|
| `SL-01` | IRB v1.0 (`4cf1071c…`), Context Pack v1.0 (`16578fdc…`), Prompt Master (`3b8bd82e…`) e manifest IRB v1.0 (`1950e71e…`) non erano inclusi nel pacchetto | Nessun artefatto tracciato con quei digest/nome soddisfa la catena completa; i cinque registri approvati non sostituiscono le sorgenti citate | **OPEN / PRESERVED** |
| `SL-02` | corpus baseline v0.9 (`7cc54e10…`) e manifest v0.9 (`eec4132e…`) citati da `DEC-196` assenti | I digest restano citati nei registri, ma i due payload content-addressed non sono presenti | **OPEN / PRESERVED** |
| `SL-03` | record completi `GAP-18-002`–`GAP-18-011` e `GAP-COV-001`–`GAP-COV-014` assenti | Gli ID compaiono nella disposition di `DEC-196`, non come record verificabili completi | **OPEN / PRESERVED** |
| `SL-04` | nessun artefatto eseguibile, fixture, build o telemetria nel pacchetto di review | Oggi esistono implementazione e una slice di evidenza governata da `DEC-207`; ciò non stabilisce implementabilità globale, prestazioni o comportamento completo dei backend | **REGISTERED; NOT CLOSED** — contesto storico parzialmente superato, claim globale ancora vietato |

Restano inoltre verificabili queste limitazioni downstream:

- l'artefatto aggregato `OCOR_Initial_Requirements_Baseline_v1.0.md` richiamato dalla
  governance non è presente; l'audit usa i cinque snapshot approvati (`IALLD-018`);
- `NFR-007`/`NFR-009` conservano soglie non congelate e restano `NOT EVALUABLE`;
- alcuni shorthand di ID nei registri non sono riferimenti atomici;
- il validator OpenAPI non è importabile nella `.venv` corrente, pur esistendo la
  distinta evidenza governata accettata da `DEC-207`;
- `audit-src/`, usato come sorgente dai generatori del branch, non è nel repository.

Nessuna limitazione è dichiarata risolta per plausibilità.

## 9. A.6 — GAP TABLE

| Deliverable | Stato su main | Stato atteso | Gap residuo | Azione | Autorizzata da override? |
|---|---|---|---|---|---|
| ADD v1.3 | Assente. Candidata branch `reports/OCOR_ADD_v1.3_Candidate.md`, SHA `99f3d17d…ed22`, commit `47724c5`; è un emendamento `PROPOSED`, non un testo consolidato per valore. | Baseline v1.3 completa, versionata, digest-pinned e con supersession circoscritta. | Richiede ratifica di `CC-FULL-GOVERNED-AGENT-MEMORY`, nuova `DEC-208`, rigenerazione dai registri correnti e consolidamento dell'intera ADD. | Presentare `DEC-208`; dopo approvazione, consolidare senza modificare ADD v1.2 storica. | **Sì come scope, NO all'esecuzione autonoma prima della presentazione DEC-208** — stop (a),(b). |
| LLD v1.1 | Assente. Candidata `reports/OCOR_LLD_v1.1_Candidate.md`, SHA `1a5d5d44…1414`, commit `47724c5`; stato `PROPOSED`. | LLD v1.1 completa e coerente con la baseline efficace. | Dipende da ADD v1.3/DEC-208; assurance 55/55 non riproducibile dalle sorgenti presenti; 283/285 full e FR-118/119 conditional. | Correggere source resolution, rigenerare matrice da main, rieseguire assurance e consolidare solo dopo DEC-208. | **Sì come scope, bloccata dalla nuova decisione**. |
| Baseline approvata non vuota | `OCOR_ADD_v1.2_APPROVED_BASELINE.md`, 227.866 byte, SHA `c3f432ae…38b84f`, commit `d76cd30`. | Almeno una baseline autoritativa non vuota. | Nessuno per v1.2. | Nessuna. | N/A. |
| ARA decision record completo | ARA v1.1 SHA `35579536…0eae`, commit `d76cd30`, copre 197–206; closure v1.0 SHA `5baa9e9d…e4f`, commit `6eb4175`, copre 207. | Storia 197–207 immutabile; eventuale nuova disposizione separata. | Per full-memory manca una decisione; prossimo ID `DEC-208`. | Non modificare 197–207; presentare nuovo record DEC-208. | **Sì solo dopo presentazione e conferma dell'autorità**. |
| Verification evidence report veritiero | Popolato, SHA `cf57a5a4…f0b2`, commit `6eb4175`; distingue E1 scoped, E2 e global Verified. Contiene due sequenze letterali `\n`, difetto solo di rendering. | Evidenza scoped senza overclaim. | Nessun gap semantico; difetto editoriale minore. | Eventuale normalizzazione editoriale in un change set downstream, senza cambiare claim. | Sì, ma non necessaria per sbloccare. |
| Coerenza dei cinque registri | Cinque snapshot v1.2 approvati e manifest 7/7 `OK`. Cinque candidati full-memory integri 11/11 rispetto a sorgenti off-tree, ma tutti i digest base divergono da main. | Snapshot full-memory derivati dai cinque registri correnti, mutuamente coerenti e legati a DEC-208. | Provenienza e riproducibilità fallite; entry decisionale ancora `UNASSIGNED`. | Correggere generatori, rigenerare tutti e cinque da main, verificare diff/ID/ref, poi promuovere atomicamente sotto DEC-208. | **Sì come scope, bloccata da DEC-208 e stop (b)**. |
| Tracciabilità bidirezionale ADD↔LLD | Audit main SHA `fe0b85b4…ad1a`: ADD 285/285, LLD 0/285, `NO-GO`. Matrice candidata SHA `cb38b20f…b5a1c`: 285 righe ma assurance non riproducibile e 2 conditional. | 285/285 bidirezionale, zero conditional/gap, generata da baseline effettiva. | Non soddisfatta su main né promuovibile dal candidato corrente. | Rigenerare dopo registri/ADD DEC-208 e verificare programmaticamente. | **Sì come scope, bloccata dalla nuova decisione**. |
| Manifest e digest | Main approval manifest SHA `8d6b7125…1dc88` 7/7 `OK`; validation manifest SHA `fde0611b…c073` tutte entry `OK`; candidate remediation manifest SHA `0740b03f…fce0` tutte entry `OK`. | Manifest finali per artefatti consolidati e provenienza verificata. | Integrità byte dei candidati sì; lineage verso main no; manifest finali v1.3/LLD assenti. | Rigenerare dopo la ricostruzione dai sorgenti correnti. | Sì, dipendente da DEC-208. |
| Allineamento contratti alle DEC approvate | Contratti normativi incorporati in ADD; runtime bundle distinto; due file pubblici standalone assenti su main. Il branch materializza copie candidate. Memory schema/API sono non approvati. | Contratti approvati materializzati; nuovi contratti full-memory versionati sotto la decisione pertinente. | Named-query/registry materializzabili dalla ADD; memory schema/API richiedono DEC-208; capability runtime non equivale al record ADD secondo audit. | Materializzare i due contratti già approvati; promuovere quelli memory soltanto con DEC-208; conformance bidirezionale. | Parzialmente sì; la porzione full-memory è bloccata da DEC-208. |
| Chiusura ARF residui | `ARF-001`–`ARF-027` tutti `CLOSED` nella baseline approvata; mapping sopra. | Nessun ARF documentale riaperto implicitamente. | Nessuno. Gli `IALLD-*` restano distinti. | Nessuna modifica alle DEC storiche. | N/A. |
| Source limitations | `SL-01`–`SL-04` sono registrate nel prior review, SHA `13dca8bf…729d727`, commit `eae86ce`; §8 ne verifica lo stato. Gli artefatti di `SL-01`–`SL-03` restano assenti; `SL-04` non è chiudibile globalmente con la sola slice `DEC-207`. | Quattro limitazioni preservate, con fonte, senza falsa risoluzione. | Nessun gap di registrazione; restano gap sostanziali di fonte/evidenza. | Mantenerle esplicite nelle versioni successive; non ricostruire i payload mancanti e non promuovere la slice runtime a evidenza globale. | **Sì** per preservazione/reporting; **no** alla ricostruzione per plausibilità. |
| Harness / validator | Harness corrente 13 PASS, 0 FAIL, 1 NOT_EXECUTED; validator assente nella `.venv`. DEC-207 conserva un run pinned 3/3 PASS distinto. | 0 FAIL e ogni NOT_EXECUTED nominato/spiegato. | Criterio di spiegazione soddisfatto; nessun nuovo run possibile senza installazione vietata. | Non contare lo skip come PASS; preservare evidenza DEC-207 separata. | Sì per reporting; installazione non autorizzata. |
| CI / PR | Main ha run governato `33334792715` success; il commit locale A.1 non è pushato e non ha CI. | CI sul change set finale e PR verso main. | Non eseguibile prima della decisione e della rigenerazione dei candidati. | Dopo autorizzazione: commit per deliverable, push, PR, attendere check. | Sì solo dopo superamento dello stop gate. |

## 10. Valutazione tassativa delle stop condition

| Condizione | Esito | Evidenza |
|---|---|---|
| (a) il gap richiede una nuova `DEC-208+` | **VERA** | il candidate Decision Register dichiara `DECISION ID UNASSIGNED`; la disposizione supersede la clausola `ELM-084` di `DEC-196`; `DEC-208` è il prossimo ID libero |
| (b) il gap richiede di modificare un artefatto approvato | **VERA** | ADD v1.3 e i cinque registri cambiano la baseline semantica ADD v1.2; la modifica deve avvenire tramite nuove versioni, senza riscrivere i file storici |
| (c) l'azione necessaria esce dalle cinque azioni dell'override | **FALSA per il gap eseguibile** | preservare `SL-01`–`SL-04` nel consolidato e nei report è in scope; ricostruire i payload assenti non è necessario né autorizzato e non viene proposto come azione |
| (d) main e branch divergono su un path autoritativo corrente | **FALSA sui path autoritativi** | il diff branch modifica solo `AGENTS.md` e aggiunge file sotto `reports/`; dossier, `docs/OCOR_LLD_v1.0.md`, runtime schemas e `inputs/` sono identici a main. Esiste però una divergenza di provenance fra candidati e digest autoritativi, già bloccante. |

## 11. Disposizione finale della FASE A

- `DEC-197`–`DEC-207` non sono state modificate, consolidate o rinumerate.
- `DEC-208` non è stata creata né assegnata.
- Nessun file sotto `inputs/` è stato modificato.
- Nessun artefatto normativo, registro, contratto, manifest o dossier è stato scritto.
- Nessun merge, rebase, push o PR è stato eseguito.
- La FASE B non è iniziata.

Per riprendere serve una disposizione del Product Owner dopo esame della GAP TABLE che:

1. autorizzi o rigetti espressamente `DEC-208` per
   `CC-FULL-GOVERNED-AGENT-MEMORY`;
2. confermi che i cinque candidati vadano rigenerati dai digest correnti di main.

Le `SL-01`–`SL-04` hanno già una fonte tracciata e restano preservate; gli artefatti
mancanti che esse descrivono non vengono ricostruiti per inferenza.
