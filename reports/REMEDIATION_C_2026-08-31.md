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
