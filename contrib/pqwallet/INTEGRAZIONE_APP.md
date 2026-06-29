# Integrare il quantum-safe (bb1z) nell'app Electron — piano

App: `bitcoboost-miner` (Electron, JS), in `/root/b2b/bb-miner-app/`.
Oggi: portafoglio non-custodial con 12 parole (BIP39) → 1 chiave → indirizzo **bb1q** (P2WPKH),
via `bitcoinjs-lib`. Mina, riceve, invia (`wallet.js` + IPC `invio:invia`).

## Punto critico — RISOLTO
Serve ML-DSA in JavaScript. Libreria scelta: **`@noble/post-quantum`** (v0.6.1), seria e verificata.
**Provato (4 giugno 2026):** una firma ML-DSA-44 creata in JS è **accettata dal verificatore C++ del
nodo** (pk 1312, sig 2420, contesto "BitcoBoost-bb1z-v2" → VALIDA). Quindi l'app può firmare e la rete accetta.

### API esatta (da usare nell'app)
```js
import { ml_dsa44 } from '@noble/post-quantum/ml-dsa.js';
const keys = ml_dsa44.keygen(seed32);                              // {publicKey:1312, secretKey:2560}
const ctx  = new TextEncoder().encode('BitcoBoost-bb1z-v2');
const sig  = ml_dsa44.sign(msg32, keys.secretKey, { context: ctx }); // 2420 byte
const ok   = ml_dsa44.verify(sig, msg32, keys.publicKey, { context: ctx });
```
Nota: dentro Electron (Chromium) `crypto` esiste già; solo in Node puro va aggiunto
`globalThis.crypto = require('node:crypto').webcrypto`.

## Disegno (idea chiave: una sola frase di backup)
La chiave ML-DSA si ricava in modo **deterministico dalle stesse 12 parole**, così il backup resta la
frase di sempre (niente file di chiavi gigante):
- seme BIP39 → (come ora) chiave ECDSA sul percorso BIP84;
- `mldsa_seed = SHA256(seme_bip39 ‖ "bb1z-mldsa-v2")` (32 byte) → `ml_dsa44.keygen(mldsa_seed)`.
- `program = SHAKE256(ecdsa_pub(33) ‖ mldsa_pub(1312))` (32 byte).
- indirizzo bb1z = bech32m versione 2, prefisso "bb": `bitcoin.address.toBech32(program, 2, 'bb')`.

## Cosa toccare nell'app
1. **wallet.js**: aggiungere `indirizzoBB1Z(frase)` e `firmaBB1Z({frase, utxos, dest, importo, fee})`.
   - sighash per input: `tx.hashForWitnessV0(i, scriptCode=OP_2<program>, valoreSat, SIGHASH_ALL)`
     (con `bitcoin.Transaction`, non PSBT — la v2 è custom).
   - firma ECDSA (tiny-secp256k1) + ML-DSA (noble) sullo stesso sighash; witness a 4 elementi
     `[ecdsa_sig+01, ecdsa_pub, mldsa_sig, mldsa_pub]`; `tx.toHex()`.
2. **main.js**: IPC per mostrare l'indirizzo bb1z, per scoprire gli incassi
   (`scantxoutset start ["raw(5220<program>)"]` via RPC) e per inviare (`sendrawtransaction`).
3. **preload.js** + **renderer/index.html**: opzione "indirizzo quantum-safe" e relativo invio.

## Verifica obbligatoria a ogni passo
Confrontare gli output JS con lo strumento di riferimento `bb-pqwallet` e con il nodo:
indirizzo identico, e spesa firmata accettata da `sendrawtransaction` su regtest.

## Dipendenze da aggiungere al package.json
`@noble/post-quantum`, `@noble/hashes` (per SHAKE256). secp256k1/bech32m già presenti via bitcoinjs-lib.

---

## AGGIORNAMENTO (4 giugno 2026) — modulo `bb1z.mjs` SCRITTO e VALIDATO
Il modulo JavaScript è pronto e provato contro il nodo regtest:
- `indirizzoBB1Z(frase, network, hrp)` → indirizzo bb1z; il nodo lo riconosce (isvalid, witness v2,
  scriptPubKey combaciante).
- `firmaBB1Z({frase, network, utxos, destScriptHex, importoSat, feeSat})` → transazione firmata
  (ECDSA + ML-DSA, witness a 4 elementi, anche **multi-input** con resto al proprio indirizzo);
  trasmessa con `sendrawtransaction` e **accettata dal nodo**.
- ML-DSA derivato dalla stessa frase (seme = SHA256(seme_bip39 ‖ "bb1z-mldsa-v2")).
- SHAKE256 e SHA256 presi da `node:crypto` (quindi **non** serve `@noble/hashes`).
- File: `bb-miner-app/bb1z.mjs` (già copiato nella cartella dell'app, non ancora collegato).

### Resta solo il "cablaggio" (nessuna logica crittografica nuova)
1. `package.json` dell'app: aggiungere `@noble/post-quantum` e fare `npm install`.
2. `main.js`: handler IPC per (a) mostrare l'indirizzo bb1z, (b) scoprire gli incassi
   (`scantxoutset` via RPC), (c) inviare (`firmaBB1Z` → `sendrawtransaction`). Caricare il modulo
   con `await import('./bb1z.mjs')` (è ESM).
3. `preload.js` + `renderer/index.html`: opzione "indirizzo/invio quantum-safe".
4. In Electron `globalThis.crypto` esiste già; in Node puro va aggiunto il polyfill webcrypto.

---

## CABLAGGIO COMPLETATO (4 giugno 2026) — da provare su desktop
Modificata la copia dell'app sul server (`/root/b2b/bb-miner-app/`), tutto **additivo** e con backup
(`*.bak.prebb1z`); il flusso classico bb1q è intatto.
- `main.js`: caricatore del modulo + 3 handler (`bb1z:indirizzo`, `bb1z:saldo`, `bb1z:invia`). Sintassi OK.
- `preload.js`: esposti `bb1zIndirizzo`, `bb1zSaldo`, `bb1zInvia`.
- `package.json`: aggiunta `@noble/post-quantum` (installata).
- `renderer/index.html`: due pulsanti aggiuntivi — "Indirizzo quantum-safe" (principale) e
  "Invia in modalità quantum-safe" (schermata invio). Il bb1z è quindi **un'opzione in più**, non sostituisce il bb1q.
- Il modulo `bb1z.mjs` si carica correttamente nell'app con le dipendenze installate.

### Stato verifica
- **Backend**: logica validata fuori da Electron (indirizzo riconosciuto dal nodo, spesa accettata).
- **Interfaccia**: scritta ma **non ancora vista** (il server è senza schermo).

### Come provarla (serve un desktop con schermo)
Il server non ha interfaccia grafica, quindi i pulsanti vanno visti facendo girare l'app su un PC:
1. Copiare la cartella `bb-miner-app` (senza `node_modules`) sul PC Windows con Node installato.
2. Nella cartella: `npm install` poi `npm start` (avvia Electron in sviluppo), col nodo `bitcoboostd` in `bin/`.
3. Sbloccare il portafoglio → compaiono i due nuovi pulsanti. Provare: mostra indirizzo bb1z,
   ricevere un po' di BB su quell'indirizzo, poi "Invia in modalità quantum-safe".
In alternativa si rigenera l'installer Windows dalla sorgente aggiornata (passo più pesante).

---

## INSTALLER WINDOWS QUANTUM-SAFE — COSTRUITO (4 giugno 2026)
- Nodo Windows ricompilato dal ramo `feat-pq-mldsa` (mingw): `bitcoboostd.exe` 15 MB, contiene la
  regola PQ (CheckHybridSignature) e la correzione di relay. Cross-compilazione verificata (PE32+ x64).
- App reimpacchettata con `electron-packager` (senza wine, assemblaggio manuale): pacchetto portatile ZIP.
- **Download (prova):** https://bitcoboost.com/downloads/BitcoBoostMiner-windows-PQ-TEST.zip
  SHA256 `f8230f8043cf7a9b35fe6351dcc6c96f58a0925e141b87f048e48d0ccee9dd3b` (~146 MB).
- Avvio: scompattare lo ZIP, eseguire `BitcoBoostMiner.exe` (Windows avviserà che è non firmato → "Esegui comunque").
  Non c'è icona/metadati personalizzati (servirebbe wine o una build su Windows; cosmetico).

### Cosa si può provare subito (sicuro)
- L'app si avvia, il flusso classico bb1q funziona, compaiono i pulsanti "Indirizzo quantum-safe" e
  "Invia in modalità quantum-safe", l'indirizzo bb1z viene mostrato.

### ⚠️ AVVERTENZA CRITICA prima di usare bb1z sulla rete vera
La regola PQ è di **consenso**. I nodi-seme attuali girano ancora il nodo **vecchio** (senza PQ): per loro
un'uscita v2 è "spendibile-da-chiunque", quindi una spesa bb1z **non verrebbe propagata** e, peggio,
PQ-nodi e vecchi-nodi potrebbero **divergere** (split della catena). Conclusione: il bb1z va attivato
**su tutta la rete insieme** — ricompilando seme + nodi dal ramo `feat-pq-mldsa` — idealmente al
**rilancio pulito da blocco 0** già previsto. Fino ad allora: provare bb1z solo in locale/regtest.
