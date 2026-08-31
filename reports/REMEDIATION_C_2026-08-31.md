# OCOR — Remediation FASE C — 2026-08-31

## 1. Control record e scope fence

| Campo | Valore |
|---|---|
| Branch | `codex/add-v1-3-lld-v1-1-remediation` |
| Baseline sorgente | `origin/main@098c680615cf8d8b57cd367386bac10d8acdc715` |
| Change set esaminato | `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Disposizione | remediation di riproducibilità e lineage; **nessuna promozione** |
| Stato full-memory | **NO-GO invariato** |
| Evidence fence | `E1=0`, `E2=0`, zero requisiti globalmente `Verified`; `E1_runtime_slice=PRESENT` confinato a `DEC-207` |
| Tree `inputs/` atteso e verificato all'avvio | `60a73de8e47b38e94aeb0e2b8dedc689fab6eb35` |

`DEC-197`–`DEC-207`, ADD v1.2, i cinque registri approvati e i relativi manifest
restano immutabili. ADD v1.3, LLD v1.1 e i contratti full-memory non sono oggetto di
promozione in questa esecuzione.

## 2. C.1 — Difetto di derivazione e pipeline corretta

### 2.1 Pipeline effettiva prima della correzione

Il generatore `reports/tests/build_full_memory_governance_candidates.py` applicava la
stessa risoluzione a tutti e cinque i registri: cercava prima
`audit-src/<nome-file>` e poi
`ocor-runtime/docs/governance_dossier/<nome-file>`. Il secondo path ometteva la
directory obbligatoria `registers/`; non esisteva quindi alcun fallback valido nel
repository.

| Candidato | Trasformazione | Input atteso dal codice storico | Output |
|---|---|---|---|
| Requirement Register v1.1 | sostituzione esatta righe `FR-118`/`FR-119`, header candidato | `audit-src/OCOR_Requirement_Register_v1.0_APPROVED.md` | `reports/governance_candidates/OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md` |
| Requirement Traceability Index v1.1 | sostituzione esatta righe `FR-118`/`FR-119`, header candidato | `audit-src/OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md` | `reports/governance_candidates/OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md` |
| Decision Register v1.2 | copia completa, header e proposta senza ID assegnato | `audit-src/OCOR_Decision_Register_v1.1_APPROVED.md` | `reports/governance_candidates/OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md` |
| Decision Traceability Index v1.2 | copia completa, header e trace proposta senza ID assegnato | `audit-src/OCOR_Decision_Traceability_Index_v1.1_APPROVED.md` | `reports/governance_candidates/OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md` |
| CAP/ELM Crosswalk v1.1 | sostituzione esatta riga `ELM-084`, header candidato | `audit-src/OCOR_CAP_ELM_Requirement_Crosswalk_v1.0_APPROVED.md` | `reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md` |

Il generatore downstream `reports/tests/build_lld_v1_1_assurance.py` ripeteva la
ricerca `audit-src/` per Requirement Register, RTI e ADD; anche i fallback dei due
registri omettevano `registers/`.

### 2.2 Provenienza di `audit-src/`

La determinazione è basata sulla cronologia completa, non su un'ipotesi:

- `git log --all --full-history -- audit-src` non restituisce commit;
- nessun tree raggiungibile da `git rev-list --all` contiene un path `audit-src/`;
- `.gitignore` contiene soltanto `.venv/`, `__pycache__/` e `*.pyc`: `audit-src/`
  non è mai stato escluso;
- non esiste una sorgente o destinazione di rename con quel path nella cronologia;
- il fallback storico non poteva risolversi perché i registri sono sotto
  `governance_dossier/registers/`.

Il run rappresentato dal risultato committato poteva quindi risolversi soltanto su
copie staging locali e non tracciate in `audit-src/`. I digest consentono di
ricostruire la differenza byte esatta: ogni copia staging era il corrispondente file
autoritativo più **un secondo LF terminale**.

| Registro | SHA-256 storico `audit-src` | SHA-256 `origin/main` | SHA-256 main + un LF | Diagnosi |
|---|---|---|---|---|
| Requirement Register | `87c11271ed5193d24ca6e782378c9e779c42c2e7b4a93ef7630f825de78be991` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | `87c11271ed5193d24ca6e782378c9e779c42c2e7b4a93ef7630f825de78be991` | un LF extra |
| Requirement Traceability Index | `f604bc963bd7006eb02f1524e741c7859e1a8c4b2e050568f6ce812a50f1b080` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | `f604bc963bd7006eb02f1524e741c7859e1a8c4b2e050568f6ce812a50f1b080` | un LF extra |
| Decision Register | `b3f380362da89da202aed9c8dfa4868367661d41ab3590295bafab51bbceccb9` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | `b3f380362da89da202aed9c8dfa4868367661d41ab3590295bafab51bbceccb9` | un LF extra |
| Decision Traceability Index | `cabffb130078209a25c4c7ac66d6bdc8500fa009bd0897d9612f5fbd13e330e1` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | `cabffb130078209a25c4c7ac66d6bdc8500fa009bd0897d9612f5fbd13e330e1` | un LF extra |
| CAP/ELM Crosswalk | `dbe1590ed72d21d56144b40f4543ef1f0de61f781d9fceb004c5500942cc2b80` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | `dbe1590ed72d21d56144b40f4543ef1f0de61f781d9fceb004c5500942cc2b80` | un LF extra |

### 2.3 Correzione applicata

La pipeline ora:

1. usa esclusivamente
   `ocor-runtime/docs/governance_dossier/registers/<nome-file>` per i cinque registri;
2. richiede che ogni input sia un file regolare;
3. legge gli stessi byte da `origin/main:<path>` e rifiuta una working copy diversa;
4. registra nei risultati `source_ref`, commit, path e SHA-256;
5. include nel candidato il lineage `origin/main@<commit>:<path>`;
6. solleva `FileNotFoundError` o `RuntimeError` con path/ref espliciti: non esiste più
   alcuna lista di fallback.

La medesima regola è stata applicata alle tre sorgenti autoritative del generatore
assurance downstream; ADD usa il proprio path nel dossier, mentre RR e RTI usano
obbligatoriamente `registers/`.

Il test negativo con register root inesistente termina intenzionalmente con:

```text
FileNotFoundError: required authoritative register is missing: /definitely-missing/ocor-registers/OCOR_Requirement_Register_v1.0_APPROVED.md
```

Esito C.1: **PASS** — sorgenti univoche, byte verificati contro main, errore rumoroso
su input assente o divergente.

## 3. C.2 — Riancoraggio dei digest-base

I cinque candidati sono stati rigenerati con
`reports/tests/build_full_memory_governance_candidates.py` a partire da
`origin/main@098c680615cf8d8b57cd367386bac10d8acdc715`. Il generatore ha concluso
11 controlli `PASS`, 0 `FAIL`. Il delta dei cinque documenti è limitato al lineage
dell'header e alla rimozione del LF staging eccedente; la disposizione proposta resta
non approvata e senza identificativo assegnato.

| Candidato | Digest-base precedente | Digest-base atteso (`origin/main`) | Digest-base dopo rigenerazione | Esito |
|---|---|---|---|---|
| Requirement Register v1.1 | `87c11271ed5193d24ca6e782378c9e779c42c2e7b4a93ef7630f825de78be991` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | `MATCH` |
| Requirement Traceability Index v1.1 | `f604bc963bd7006eb02f1524e741c7859e1a8c4b2e050568f6ce812a50f1b080` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | `MATCH` |
| Decision Register v1.2 | `b3f380362da89da202aed9c8dfa4868367661d41ab3590295bafab51bbceccb9` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | `MATCH` |
| Decision Traceability Index v1.2 | `cabffb130078209a25c4c7ac66d6bdc8500fa009bd0897d9612f5fbd13e330e1` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | `MATCH` |
| CAP/ELM Crosswalk v1.1 | `dbe1590ed72d21d56144b40f4543ef1f0de61f781d9fceb004c5500942cc2b80` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | `MATCH` |

Digest dei candidati rigenerati:

| Candidato | SHA-256 output |
|---|---|
| Requirement Register v1.1 | `df1e36a6ef2cbb92bee236f262858ac37f2989d369e0e1f4731268308e70887e` |
| Requirement Traceability Index v1.1 | `bb747a84d3183370e11747249b6f85bcf6d55e530950bdcb9d699b634b633eac` |
| Decision Register v1.2 | `c14d8eba0532f6a65e514d206e79156ce17fa75c0b9078f5529fead987f32ee4` |
| Decision Traceability Index v1.2 | `f14b824e20155c2639908eda0d0d0454747954ba8fdc0965e788f0222edc6ab1` |
| CAP/ELM Crosswalk v1.1 | `1e74f8d7f7a7a119c1431ae00319c457f85fff3cdc4e40f82aa3c77127a019c3` |

Il manifest candidato rigenerato verifica 6/6 entry `OK`; viene consolidato con la
catena di lineage al punto C.4. Nessun manifest approvato è stato modificato.

Esito C.2: **PASS** — 5/5 digest-base coincidono byte per byte con `origin/main`.

## 4. C.3 — Riproducibilità da due clone puliti

Il verificatore `reports/tests/verify_full_memory_reproducibility.py` ha creato due
clone temporanei indipendenti del repository GitHub, ha importato il commit candidato
`d86c7e07a4e2a8bdc7412390ca0a9013eb1d8e62` in detached HEAD e ha verificato in
entrambi `origin/main=098c680615cf8d8b57cd367386bac10d8acdc715` prima di eseguire il
generatore. I clone erano clean prima della generazione.

Un primo setup basato sul clone del repository locale è stato respinto prima di
generare output: avrebbe rimappato `origin/main` sul branch locale `main`, fermo a
`ddfa97d1cacec23afdf767702c7c0fd816e66431`. Il verificatore definitivo clona il vero
origin GitHub e usa il repository locale soltanto per importare il commit non ancora
pushato; in questo modo il ref autoritativo non viene ridefinito.

Ambiente del run: Python `3.14.4`, Git `2.53.0`. Il generatore non incorpora timestamp,
path assoluti o enumerazioni non ordinate: commit sorgente e path sono relativi e
fissi, l'ordine dei cinque registri è dichiarato nel codice e il manifest è ordinato.

| Output confrontato | Clone 1 SHA-256 | Clone 2 SHA-256 | Workspace SHA-256 | Byte-identico |
|---|---|---|---|---|
| CAP/ELM Crosswalk candidate | `1e74f8d7f7a7a119c1431ae00319c457f85fff3cdc4e40f82aa3c77127a019c3` | `1e74f8d7f7a7a119c1431ae00319c457f85fff3cdc4e40f82aa3c77127a019c3` | `1e74f8d7f7a7a119c1431ae00319c457f85fff3cdc4e40f82aa3c77127a019c3` | `YES` |
| Decision Register candidate | `c14d8eba0532f6a65e514d206e79156ce17fa75c0b9078f5529fead987f32ee4` | `c14d8eba0532f6a65e514d206e79156ce17fa75c0b9078f5529fead987f32ee4` | `c14d8eba0532f6a65e514d206e79156ce17fa75c0b9078f5529fead987f32ee4` | `YES` |
| Decision Traceability candidate | `f14b824e20155c2639908eda0d0d0454747954ba8fdc0965e788f0222edc6ab1` | `f14b824e20155c2639908eda0d0d0454747954ba8fdc0965e788f0222edc6ab1` | `f14b824e20155c2639908eda0d0d0454747954ba8fdc0965e788f0222edc6ab1` | `YES` |
| Requirement Register candidate | `df1e36a6ef2cbb92bee236f262858ac37f2989d369e0e1f4731268308e70887e` | `df1e36a6ef2cbb92bee236f262858ac37f2989d369e0e1f4731268308e70887e` | `df1e36a6ef2cbb92bee236f262858ac37f2989d369e0e1f4731268308e70887e` | `YES` |
| Requirement Traceability candidate | `bb747a84d3183370e11747249b6f85bcf6d55e530950bdcb9d699b634b633eac` | `bb747a84d3183370e11747249b6f85bcf6d55e530950bdcb9d699b634b633eac` | `bb747a84d3183370e11747249b6f85bcf6d55e530950bdcb9d699b634b633eac` | `YES` |
| Candidate results JSON | `4f6edf4320af0fc262ab31728d655f375a9886281c0da6cbdf6a8961371fc309` | `4f6edf4320af0fc262ab31728d655f375a9886281c0da6cbdf6a8961371fc309` | `4f6edf4320af0fc262ab31728d655f375a9886281c0da6cbdf6a8961371fc309` | `YES` |
| Candidate SHA256SUMS | `52f9006aa0ceb2c56cb7f15f290e6568e449f783bdc62760be71e06b5d343a0d` | `52f9006aa0ceb2c56cb7f15f290e6568e449f783bdc62760be71e06b5d343a0d` | `52f9006aa0ceb2c56cb7f15f290e6568e449f783bdc62760be71e06b5d343a0d` | `YES` |

Risultato macchina:
`reports/tests/full_memory_reproducibility_results.json`, SHA-256
`1b8a796b7eda4b75df4d725d551d3f224801bf8ae776d406798f5227e2fca36a`.

Esito C.3: **PASS** — 7/7 output byte-identici fra i due clone e rispetto al
workspace.

## 5. C.4 — Lineage registri main → candidati

La catena è registrata sia negli header dei cinque candidati sia nel risultato macchina
`reports/tests/full_memory_governance_candidate_results.json`. Il punto di origine è
univoco: `origin/main@098c680615cf8d8b57cd367386bac10d8acdc715`. Il trasformatore è
`reports/tests/build_full_memory_governance_candidates.py`, SHA-256
`376eddea2c62367405e2128e756967662c6f9285dedf1d76de9f5a17d58ace79`, introdotto
nella sua forma strict-source dal commit `3ad0fdce7d3d8b6829c665acfa6e1a596fa59538`.

| Input autoritativo e SHA-256 | Trasformazione dichiarata | Output candidato e SHA-256 |
|---|---|---|
| `registers/OCOR_Requirement_Register_v1.0_APPROVED.md` — `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` | sostituzione univoca righe `FR-118`/`FR-119`; header lineage | `reports/governance_candidates/OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md` — `df1e36a6ef2cbb92bee236f262858ac37f2989d369e0e1f4731268308e70887e` |
| `registers/OCOR_Requirement_Traceability_Index_v1.0_APPROVED.md` — `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` | sostituzione univoca righe `FR-118`/`FR-119`; header lineage | `reports/governance_candidates/OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md` — `bb747a84d3183370e11747249b6f85bcf6d55e530950bdcb9d699b634b633eac` |
| `registers/OCOR_Decision_Register_v1.1_APPROVED.md` — `521e328e76d9723d7ad035684df49c0183c754f8029f20c522a744b4d2a5f7dd` | copia integrale; header lineage; append proposta `UNASSIGNED` | `reports/governance_candidates/OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md` — `c14d8eba0532f6a65e514d206e79156ce17fa75c0b9078f5529fead987f32ee4` |
| `registers/OCOR_Decision_Traceability_Index_v1.1_APPROVED.md` — `e6b4f45d96c323c44fb09370dc2396b8bd73ff7de1e2c0632a1f551b5dfe7d5a` | copia integrale; header lineage; append trace proposta `UNASSIGNED` | `reports/governance_candidates/OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md` — `f14b824e20155c2639908eda0d0d0454747954ba8fdc0965e788f0222edc6ab1` |
| `registers/OCOR_CAP_ELM_Requirement_Crosswalk_v1.0_APPROVED.md` — `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` | sostituzione univoca riga `ELM-084`; header lineage | `reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md` — `1e74f8d7f7a7a119c1431ae00319c457f85fff3cdc4e40f82aa3c77127a019c3` |

Tutti i path input della tabella hanno prefisso completo
`ocor-runtime/docs/governance_dossier/`. Il result JSON, SHA-256
`4f6edf4320af0fc262ab31728d655f375a9886281c0da6cbdf6a8961371fc309`, registra
commit, path, cinque digest-base, cinque digest output e 11/11 controlli `PASS`.

Il manifest candidato
`reports/OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS`, SHA-256
`52f9006aa0ceb2c56cb7f15f290e6568e449f783bdc62760be71e06b5d343a0d`, contiene i
cinque output e il result JSON; `sha256sum -c` restituisce 6/6 `OK`.

I manifest approvati non sono stati toccati e coincidono con `origin/main`:

| Manifest approvato | SHA-256 workspace | SHA-256 `origin/main` | Esito |
|---|---|---|---|
| `OCOR_ADD_v1.2_APPROVAL_SHA256SUMS` | `8d6b7125ddb77a78efff7521f78634b2f59f03eb2662ae4e6485d4244661dc88` | `8d6b7125ddb77a78efff7521f78634b2f59f03eb2662ae4e6485d4244661dc88` | `MATCH` |
| `OCOR_ADD_v1.2_VALIDATION_EVIDENCE_SHA256SUMS` | `fde0611b9aa1f950b9c599a3ee3d71d89ac353a21cb40b9e0ebe8efeffbdc073` | `fde0611b9aa1f950b9c599a3ee3d71d89ac353a21cb40b9e0ebe8efeffbdc073` | `MATCH` |

Esito C.4: **PASS** — lineage completo e verificabile; manifest candidato 6/6;
manifest approvati immutati.

## 6. C.5 — Harness e validator OpenAPI 3.1

Il test inizialmente `NOT_EXECUTED` era nominato:

```text
OpenAPI — validazione semantica con validator ufficiale
```

La causa era duplice: `openapi_spec_validator` non era importabile dalla `.venv` root
e `scripts/verify.py` registrava comunque lo skip in modo hard-coded dopo la sola
risoluzione strutturale dei `$ref`.

Il pin governato preesistente è stato riutilizzato senza modificarlo:

| Controllo dipendenza | Valore |
|---|---|
| Package | `openapi-spec-validator==0.9.0` |
| Lock | `ocor-runtime/uv.lock`, SHA-256 `7cfe389e1d12995bcac6ee1ce0356c7054724b2eee03401c41bb2650ce859c69` |
| Wheel SHA-256 pinnato | `222fecffc7714f6d0a6ad62c0e4b66cc2b7dbfafb7b93acfc6c308abbdb51af8` |
| Sdist SHA-256 pinnato | `6d648cff6490ebb799dcfe273792f2941c050158854c721f086599d845da78b8` |
| Profilo | `OCOR_OPENAPI_VALIDATION_PROFILE_v1.0.md`, SHA-256 `bb9658a81477ac3eeae321f25788120acefacab9b514b32c9d964c180b8e32f7` |

L'ambiente CI è stato ricostruito con `uv sync --frozen --extra test`; la `.venv` root
ha ricevuto lo stesso pin. Il primo run nell'ambiente CI minimale ha correttamente
eseguito OpenAPI ma mostrato `Turtle/RDF — parsing: NOT_EXECUTED`, perché il workflow
aggiunge `rdflib` in un passo separato. Dopo aver applicato lo stesso pin CI
`rdflib==7.1.4`, il run finale non contiene skip. Lo stato intermedio non è contato
come `PASS`.

Il harness ora:

- importa `openapi-spec-validator` soltanto al punto di esecuzione;
- verifica versione installata, versione nel lock e wheel SHA-256 nel lock;
- produce `FAIL` su pin/lock divergente o validazione fallita;
- produce `NOT_EXECUTED` con eccezione esplicita soltanto se il package manca;
- esegue `validate(document)` sul blocco OpenAPI 3.1 estratto.

Esiti finali:

| Esecuzione | PASS | FAIL | NOT_EXECUTED | Evidenza |
|---|---:|---:|---:|---|
| `./.venv/bin/python3 scripts/verify.py --json` | 14 | 0 | 0 | `reports/verify_report.json`, SHA-256 `9d929ffaf37714ed93bad08e5468dcbaba8b958a1d5ce431f6a7d79ca538107e` |
| C.5 validator profile + ADD v1.1 + ADD v1.2 embedded + runtime OpenAPI | 4 | 0 | 0 | `reports/tests/c5_openapi_validation_results.json`, SHA-256 `c43e3d55c1ae771c76d34c06826ac29e56becad8444e7614ff1f2446d687dfe8` |

Il runner C.5 è `reports/tests/validate_openapi_remediation_c.py`, SHA-256
`a051f97186bdcca4e12007ebb0f95900e8e535c2da1e8ac922abbbe5dfae069c`. Registra
`repo:///ocor-runtime/schemas/ocor.openapi.yaml` evitando un path assoluto dipendente
dal runner; il resolver usa il file URI reale soltanto durante la validazione.

Gli artefatti storici `validate_openapi_governed.py` e
`openapi_31_validation_results.json` sono rimasti ai digest approvati
`1c4639a9…ecbe3` e `75778277…0dca`; il manifest di validation evidence approvato passa
integralmente senza essere aggiornato.

Esito C.5: **PASS** — validator ufficiale eseguito con pin e digest verificati; harness
14 `PASS`, 0 `FAIL`, 0 `NOT_EXECUTED`.
