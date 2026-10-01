# Decision request — TOOLCHAIN-LOCK-UPDATE (toolchain lock identity on the new dev machine)

- **Status**: `OPEN_PO_DECISION_REQUIRED` (bloccante)
- **Fonte**: verdetto indipendente `OCOR-DEV-REM-0015-92e194e2965f-1` (finding `VF-001`)

## Contesto

`infra/toolchain.lock.json` registra versioni e digest SHA-256 degli strumenti host
(`docker` 29.7.2, `git` 2.55.0, `gh` 2.99.0, `node` 20.20.2, `uv` 0.12.5, oltre a
`python` 3.12.11, `ruff` 0.13.1, `tsc` 7.0.2, `java` 21.0.8+9) acquisiti sulla macchina
di sviluppo precedente (`acquired_at: 2026-09-03`). Sulla macchina attuale la toolchain
host differisce: `git` 2.53.0, `docker` 29.8.2, `uv` 0.12.21, `gh` versione diversa,
`tsc` non installato. Inoltre il binario ufficiale di `node` 20.20.2 (archivio verificato
contro `SHASUMS256.txt` di nodejs.org) ha SHA-256 `62954886…`, diverso dal digest nel
lock `4446eb8e…`: il digest registrato non è riproducibile dalle sorgenti ufficiali.

Il verifier indipendente ha marcato `NO_GO` la verifica dell'evidenza di
`OCOR-DEV-REM-0015` (finding `VF-001`, severity medium): la suite completa passa
(905/905, zero skip), il fix `git_changed()` è corretto, ma non è possibile attestare la
riproduzione con la toolchain approvata. `DEC-211` e
`OCOR_AUTONOMOUS_TOOLING_POLICY.md` richiedono pin di versione e digest nel lock.

L'autorizzazione Product Owner del 2026-10-01 sulla **identità dell'immagine Fuseki**
copre soltanto `infra/services.lock.json` e non si estende implicitamente a
`infra/toolchain.lock.json` (come rilevato esplicitamente dal verifier in `VF-001`).

## Opzioni

1. **Autorizzare la ri-acquisizione governata di `infra/toolchain.lock.json` sulla
   macchina attuale** — come per Fuseki: registrare versioni/digest effettivi della
   toolchain locale (con host, data, motivazione "cambio della macchina di sviluppo" e
   valori precedenti), previa verifica di sorgenti e digest di ogni strumento. Il
   controllo di identità fail-closed nello script di verifica resta invariato.
2. **Fornire la toolchain esatta pinned** — rendere disponibile un ambiente con versioni
   e digest identici a quelli nel lock. Non attuabile per `node`: il digest nel lock non
   corrisponde al binario ufficiale, quindi non riproducibile dalle sorgenti ufficiali.
3. **Rilassare la policy del lock** — ammettere il solo pin di versione senza digest.
   È una variazione della policy approvata, quindi riservata.

## Raccomandazione motivata

Raccomando l'opzione 1: coerente con la decisione Fuseki già presa, mantiene intatto il
controllo di identità fail-closed (nessuna modifica al codice di verifica) e riallinea il
lock alla realtà della nuova macchina con tracciabilità completa (valori precedenti,
motivazione, host, data).

## Impatto

Blocca la **sigillatura dell'evidenza** (verifica indipendente) di `OCOR-DEV-REM-0015`,
`OCOR-DEV-REM-0016` e di tutti i task residui del backlog (`OCOR-DEV-0048`…`OCOR-DEV-0069`)
alla loro fase di integrazione. Le fasi di implementazione e le remediation che non
richiedono verifica indipendente (R3) restano eseguibili.

## Task bloccati

- `OCOR-DEV-REM-0015`, `OCOR-DEV-REM-0016` (integrazione/verifica)
- `OCOR-DEV-0048`…`OCOR-DEV-0069` (fase di integrazione/verifica)
