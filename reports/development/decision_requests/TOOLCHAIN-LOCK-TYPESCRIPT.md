# Decision request — TOOLCHAIN-LOCK-TYPESCRIPT (tsc 7.0.2 e node 20.20.2 vs 24.21.0)

- **Status**: `OPEN_PO_DECISION_REQUIRED`
- **Fonte**: change set `governed/toolchain-lock-residual-git` (risoluzione della parte `git` di
  `TOOLCHAIN-LOCK-RESIDUAL`, autorizzata dal Product Owner il 2026-10-01)

## Contesto

La parte `git` di `TOOLCHAIN-LOCK-RESIDUAL` è stata risolta con PR #147 (`e74afa6…`): la voce
`git` di `infra/toolchain.lock.json` è ora `2.53.0` (pacchetto Ubuntu ufficiale, oggetto misurato
= binario installato, digest `5516c9f3…`). Restano due divergenze della toolchain **host** rispetto
al lock, che la decisione `TOOLCHAIN-LOCK-RESIDUAL` **non** autorizza a variare.

### typescript (tsc) 7.0.2

- `tsc` non è installato sulla macchina attuale (`command unavailable`). La voce del lock è
  `7.0.2` con `integrity` `2219f428…` (digest di `bin/tsc` da `typescript@7.0.2` npm, acquisito in
  isolamento in un change set precedente).
- La sua installazione richiede `node`; il verifier indipendente lo acquisisce in isolamento e
  conferma la corrispondenza (cycle-2: 8/9 voci coincidono dopo acquisizione isolata).

### node 20.20.2 vs 24.21.0

- La voce del lock è `node` `20.20.2` (`integrity` `62954886…`, binario ufficiale con firma GPG
  verificata, registrato da `TOOLCHAIN-LOCK-UPDATE`).
- La toolchain **host** di questa macchina espone `node v24.21.0` (`/usr/bin/node`), diverso dal
  lock. Il verifier indipendente acquisisce `node` 20.20.2 in isolamento e conferma la
  corrispondenza.

## Opzioni

1. **Allineamento host senza variazione di versione del lock** (DEC-211, nessuna decisione
   richiesta): installare in ambiente isolato `node` 20.20.2 e `typescript@7.0.2` (`bin/tsc`) e
   usare quell'ambiente per i gate locali dell'implementatore; il lock resta invariato.
2. **Variazione del lock** (richiede decisione): registrare `node` 24.21.0 e/o `tsc` come oggetto
   misurato host, con motivazione e valore precedente — **non** autorizzata da
   `TOOLCHAIN-LOCK-RESIDUAL`.

## Raccomandazione motivata

Opzione 1: allineamento host isolato senza variazione del lock. Il verifier già conferma che le
voci coincidono in isolamento; l'unico impatto è sull'ambiente locale dell'implementatore. Nessuna
variazione della semantica del lock né dei controlli di verifica.

## Impatto

Non bloccante per la verifica indipendente di `OCOR-DEV-REM-0015`/`REM-0016` (il verifier
acquisisce `node`/`tsc` in isolamento). Il preflight locale
`scripts/preflight_environment.py --require-ready` continua a segnalare `typescript`
(`command unavailable`) e `node` (`version mismatch`) finché l'ambiente host non è allineato.

## Task bloccati

Nessuno.
