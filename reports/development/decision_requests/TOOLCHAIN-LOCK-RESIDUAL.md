# Decision request — TOOLCHAIN-LOCK-RESIDUAL (git risolto; typescript 7.0.2 → TOOLCHAIN-LOCK-TYPESCRIPT)

- **Status**: `RESOLVED` (parte `git`); parte `typescript`/`node` trasferita a
  `TOOLCHAIN-LOCK-TYPESCRIPT` (`OPEN_PO_DECISION_REQUIRED`)
- **Fonte**: change set `governed/toolchain-lock-update` (ri-acquisizione governata di
  `infra/toolchain.lock.json` autorizzata dal Product Owner il 2026-10-01)

## Risoluzione (2026-10-01)

La parte `git` è stata risolta con PR #147 (`e74afa6…`): la voce `git` di
`infra/toolchain.lock.json` è passata da `2.55.0` (digest `c1bc685b…` della macchina precedente)
a `2.53.0` (pacchetto Ubuntu ufficiale, oggetto misurato = binario installato `/usr/bin/git`,
digest `5516c9f3…`), con provenienza verificata (`apt-cache policy git` → archive.ubuntu.com
resolute/main; `dpkg -s git` → `1:2.53.0-1ubuntu1`, Ubuntu Developers), valore precedente,
host e data registrati. I controlli di verifica del lock restano invariati.

La parte `typescript`/`node` resta aperta ed è trasferita alla decision request
`TOOLCHAIN-LOCK-TYPESCRIPT`.

## Contesto

Il change set `governed/toolchain-lock-update` ri-acquisisce le voci divergenti di
`infra/toolchain.lock.json` (decisione PO 2026-10-01). Per `node` (20.20.2), `gh`
(2.99.0) e `docker` (29.7.2) l'`integrity` è stato aggiornato al digest del **binario
installato** derivato dall'artefatto ufficiale verificato; `uv` (0.12.5) era già corretto.
Due voci **non** sono ri-acquisibili con le condizioni imposte (versione invariata +
digest verificato contro checksum ufficiale):

### git 2.55.0

- Il progetto git **non pubblica binari Linux ufficiali**: distribuisce solo sorgenti
  (kernel.org) con checksum del tarball, non del binario. Il binario installato è
  compilato dalla distribuzione (non riproducibile).
- L'`integrity` attuale `c1bc685b…` è il digest del binario della **macchina precedente**
  (git 2.55.0 costruito localmente) e non è verificabile contro alcun checksum ufficiale.
- Sulla macchina attuale è installato `git 2.53.0` (digest `5516c9f3…`).

### typescript (tsc) 7.0.2

- `tsc` è **indisponibile** sulla macchina attuale; la sua installazione richiede `node`
  (in corso di ri-allineamento in questo stesso change set) e `npm`.
- L'`integrity` attuale `2219f428…` è il digest dell'installazione della macchina
  precedente e non è riproducibile senza una specifica chiara dell'artefatto misurato
  (pacchetto npm `typescript@7.0.2` / binario nativo / altro).

## Opzioni

1. **git**: passare il pin dall'`integrity` del binario al digest del **tarball sorgente
   ufficiale** (kernel.org), dichiarando `provider`/oggetto misurato di conseguenza; oppure
   ammettere un binario compilato localmente (digest non riproducibile); oppure rilassare
   a pin di sola versione. Ciascuna è una variazione della policy approvata.
2. **tsc**: dopo l'installazione di `node` 20.20.2, installare `typescript@7.0.2` da npm e
   registrare il digest del binario effettivo (`bin/tsc`), dichiarando l'oggetto misurato;
   oppure pin di sola versione / pacchetto npm.

## Raccomandazione motivata

Per `git`: pin del digest del tarball sorgente ufficiale come oggetto misurato (riproducibile
dalle sorgenti ufficiali) oppure, se il PO preferisce non variare la semantica del lock,
conferma esplicita del pin di sola versione. Per `tsc`: differire la ri-acquisizione a dopo
l'installazione di `node` 20.20.2 (prerequisito), quindi registrare il digest di `bin/tsc`
dal pacchetto npm ufficiale `typescript@7.0.2`.

## Impatto

Le due voci restano con i valori della macchina precedente. Il preflight
`scripts/preflight_environment.py --require-ready` continuerà a segnalare `git`
(`version mismatch` / `executable integrity mismatch`) e `typescript` (`command
unavailable`) finché non saranno risolte. Non blocca la ri-acquisizione di `node`/`gh`/
`docker`/`uv` né la verifica indipendente di `OCOR-DEV-REM-0015` se il verifier accetta
la ri-acquisizione parziale; in caso contrario blocca la sigillatura dell'evidenza dei
task che richiedono l'intera toolchain conforme.

## Task bloccati

- `OCOR-DEV-REM-0015`, `OCOR-DEV-REM-0016` (verifica indipendente/evidenza) — solo se il
  verifier esige la toolchain **integrale** conforme.
