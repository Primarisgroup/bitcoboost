# BitcoBoost Mainnet Launch — Checklist

> **Versione**: 1.0
> **Data creazione**: 9 maggio 2026
> **Branch Git**: `mainnet-launch-redesign` (in `/home/ubuntu/bitcoboost-src/`)
> **Stato**: pre-launch readiness, codice pronto al 95%

Questo documento è la **checklist operativa** per arrivare al lancio pubblico della mainnet di BitcoBoost. Ogni voce è scritta in modo che chiunque (compreso un futuro Massimiliano dimenticato dei dettagli) possa eseguirla.

---

## ✅ COSA È GIÀ FATTO

### Codice della chain (sorgenti C++)
- ✅ Hard fork al lancio: nuovo genesis + reset chain (Modo B)
- ✅ Algoritmo PoW: X16RV2 sempre attivo dal blocco 0 (anti-ASIC, GPU-friendly)
- ✅ powLimit Bitcoin-style (`00000000ffff...`): chain difendibile da 51% attack
- ✅ Slow start del block reward (1 BB primi 1000 blocchi, 10 BB blocchi 1001-2000, 50 BB poi)
- ✅ Difficulty retarget veloce primi 2016 blocchi (ogni 144 invece di 2016)
- ✅ Founder Reward 5% per Primaris Group SRLS, blocchi 2001-210000 (~4 anni)
- ✅ Fix CVE-2010-5139 (value overflow) verificato presente
- ✅ Fix CVE-2018-17144 (duplicate inputs) verificato presente
- ✅ Magic bytes nuovi `0xBB 0x07 0x14 0x57` (chain non si confonde con quella vecchia)
- ✅ DNS seed reali nel codice: `seed1.bitcoboost.com`, `seed2.bitcoboost.com`, `seed3.bitcoboost.com`
- ✅ Address prefixes BB mantenuti (PUBKEY=25, SCRIPT=85, WIF=153, bech32 "bb")
- ✅ Build di `bitcoind` 278 MB funzionante (exit OK su `--version`/`--help`)

### Infrastruttura VPS
- ✅ Firewall UFW attivo (22, 80, 443, 3333, 38210)
- ✅ Servizi insicuri spenti (`bb_mym` con SHA-256)
- ✅ Pool-node come `ubuntu` invece che `root`
- ✅ JWT_SECRET fail-fast (no fallback random silenzioso)
- ✅ CORS ristretto a domini bitcoboost.com
- ✅ RPC credentials forti (32 byte di entropia per password)
- ✅ Swap 4 GB
- ✅ Nginx blocca `*.bak`, `.git/`, `*.env`, archivi sparsi
- ✅ Backup automatico DB Postgres (giornaliero, retention 7gg)
- ✅ Backup automatico chain (settimanale, retention 4 settimane)
- ✅ Tutti i timer dashboard funzionanti (6 JSON live)
- ✅ Schema DB Postgres uniforme (tutto owner `bb_app`)

### Frontend
- ✅ NET allineato a chainparams (pubKeyHash 25, scriptHash 85, wif 153, bip32 BB)
- ✅ Rate limit `/api/users/resolve` (10/min)
- ✅ Onclick inline rimossi (CSP-ready, no XSS via attributo HTML)
- ✅ WIF in memoria volatile (no più localStorage)
- ✅ Privacy Policy, Terms of Service, Cookie Policy + cookie banner GDPR

---

## 🚧 COSA MANCA PRIMA DEL LANCIO PUBBLICO

### 🔴 CRITICO (bloccante per il lancio)

#### 1. Generare il genesis block reale
**Cosa**: il `chainparams.cpp` ha placeholder `nNonce = 0` e `nTime = 1762086400`. Vanno computati i valori reali al momento del lancio.

**Come** (script Python da scrivere):
1. Aggiornare `nTime` al timestamp del lancio reale (es. `date +%s`)
2. Loop su `nNonce` da 0 a 2^32, computando per ogni valore l'hash X16RV2 del block header
3. Stop quando l'hash è sotto `powLimit` (`0x1d00ffff` target)
4. Tempo stimato: 5-30 minuti su CPU moderna (perché difficoltà bassa al genesis)

**Output**: un `nNonce` valido, un `genesis.GetHash()` valido, un `genesis.hashMerkleRoot` valido.

#### 2. Generare l'address Primaris Group SRLS
**Cosa**: il `validation.cpp` riga `BBFounderReward::GetFounderAddress()` ritorna un placeholder `"bb1qFOUNDER_ADDRESS_PLACEHOLDER_REPLACE_BEFORE_LAUNCH"`.

**Come**:
1. Avviare `bitcoind` con la nuova chain (datadir vuoto)
2. `bitcoin-cli getnewaddress "founder-primaris" bech32`
3. Output: indirizzo `bb1q...`
4. **CRITICO**: salvare la chiave privata (WIF) di quell'address **fuori dalla VPS**, in 2-3 luoghi sicuri (password manager + USB cifrata + cassetta di sicurezza)
5. Sostituire il placeholder in `validation.cpp`

#### 3. Riattivare le 2 asserzioni di sicurezza
**Cosa**: in `chainparams.cpp` ho lasciato 2 commenti `// [BB-LAUNCH] assert genesis hash DISABLED` e `// [BB-LAUNCH] assert merkle root DISABLED`.

**Come** (dopo aver fatto i punti 1+2):
```cpp
assert(consensus.hashGenesisBlock == uint256S("0x...valore_calcolato_in_punto_1..."));
assert(genesis.hashMerkleRoot == uint256S("0x...valore_calcolato_in_punto_1..."));
```

#### 4. Ricompilazione finale binario di lancio
Dopo i punti 1-3, `cd /home/ubuntu/bitcoboost-src/src && make -j4 bitcoind`. ~5 minuti. Verificare `--version` non crashi.

#### 5. 2-3 VPS aggiuntive per seed nodes
**Cosa**: oggi ho solo un nodo isolato. Per una vera rete servono almeno 2-3 nodi sempre online che facciano discovery dei nuovi peer.

**Come**:
1. Comprare 2-3 VPS Hetzner/Contabo (~5 €/mese ciascuna, target: 2 GB RAM, 40 GB disco)
2. Su ognuna: installare Ubuntu 24, copiarci il `bitcoind` compilato
3. Configurare datadir, far girare con `-listen=1 -dnsseed=0`
4. Registrare DNS A records:
   - `seed1.bitcoboost.com` → IP VPS 1
   - `seed2.bitcoboost.com` → IP VPS 2
   - `seed3.bitcoboost.com` → IP VPS 3 (opzionale)

#### 6. Implementare wallet cifrato server-side (FRONT-1b)
**Cosa**: oggi il WIF vive solo in memoria. Se l'utente ricarica la pagina, lo perde. Il DB ha già `user_wallet_secrets` pronto, manca il codice client.

**Come** (1-2 ore):
1. UI: bottone "Salva wallet sul server" dopo creazione wallet
2. JS: chiede password all'utente, deriva chiave con PBKDF2 (almeno 100k iterazioni), cifra WIF con AES-GCM
3. POST `/api/wallet/secret` con `{enc_wif, kdf_salt, kdf_iter, enc_iv}`
4. Al login, GET `/api/wallet/secret`, chiede password, decifra WIF, lo carica in memoria

### 🟠 GRAVE (importante ma non bloccante per il day-1)

#### 7. Code-signing Authenticode per il binario Windows
**Cosa**: `bitcoboost-miner-win64.zip` è non firmato. Windows mostra SmartScreen "Editore sconosciuto" → molti utenti chiudono qui.

**Come**:
1. Acquistare un certificato Authenticode (~200-500 €/anno) da fornitori come SSL.com, DigiCert, Sectigo
2. Per Code Signing OV (Organization Validation): serve documentazione di Primaris Group SRLS (P.IVA, atto costitutivo, ecc.)
3. Una volta ricevuto il certificato, firmare gli .exe con `signtool` (Windows) o `osslsigncode` (Linux)

#### 8. Whitepaper conforme MiCA
**Cosa**: documento tecnico-economico pubblico, art. 6 MiCA conforme.

**Come**:
1. Strutturare in capitoli: emittente, descrizione progetto, tecnologia, diritti degli holder, rischi, risk warning, ecc.
2. Far revisionare da avvocato MiCA prima di pubblicare
3. Hosting su `bitcoboost.com/whitepaper.pdf`

#### 9. Backup off-site
**Cosa**: oggi i backup DB e chain sono **sulla stessa VPS**. Se la VPS muore, perdi anche i backup.

**Come**:
1. **Opzione A** — bucket S3/B2: configurare AWS o Backblaze B2, script `aws s3 sync` schedulato
2. **Opzione B** — seconda VPS o NAS: rsync con SSH key da una macchina di tua proprietà che pulla i backup ogni notte
3. Cifrare i backup off-site con `gpg` per protezione aggiuntiva

#### 10. Versione inglese del sito
**Cosa**: sito attualmente solo in italiano. Lancio internazionale richiede inglese.

**Come**: tradurre `/`, `/app/`, `/how-to-mine/`, `/network/`, `/roadmap/`, `/downloads/`, `/privacy/`, `/termini/`, `/cookie/`. Pubblicare a `bitcoboost.com/en/...` o usare lingua-detection.

### 🟡 MEDIO

#### 11. Pulire archivio `.bak` da 1.8 GB
**Cosa**: `/root/bb_archive_20260509/` contiene i 206 `.bak` che ho archiviato stamattina. Lascia 1.8 GB di disco impegnati.

**Come**: dopo qualche settimana di stabilità, `rm -rf /root/bb_archive_20260509/`

#### 12. Tradurre i miner Windows in inglese
Stesso ragionamento del sito.

#### 13. Aggiungere checkpoint reali nel codice
Dopo qualche mese di vita della chain, aggiungere checkpoint hardcoded in `chainparams.cpp` (es. ogni 5.000 blocchi) per accelerare la sincronizzazione di nodi nuovi.

---

## 📋 ASPETTI LEGALI E FISCALI (Fase 4)

### Da affrontare con avvocato MiCA prima del lancio

- [ ] **Memo riassuntivo per avvocato**: prepararlo basato sul `bitcoboost_analisi_completa.md` + questo documento
- [ ] **Analisi MiCA art. 4 par. 3 lett. b** (esenzione mining-only): è applicabile a BitcoBoost?
- [ ] **Status CASP**: la piattaforma `bitcoboost.com` esercita custodia (`user_wallet_secrets`) e trasferimento (`/api/tx/send`) → autorizzazione CASP necessaria?
- [ ] **Periodo transitorio MiCA**: scade 1° luglio 2026 (~7 settimane dal momento della redazione di questo documento)
- [ ] **Registrazione OAM** Italia per VASP (Registro degli Operatori in Valute Virtuali)
- [ ] **Privacy policy**: revisione legale delle bozze pubblicate su `/privacy/`
- [ ] **Terms of Service**: revisione legale delle bozze pubblicate su `/termini/`
- [ ] **KYC**: implementare KYC sopra €1.000 per CASP (Onfido, Sumsub, Veriff sono provider mainstream)

### Da affrontare con commercialista

- [ ] **Founder Reward → Primaris Group SRLS**: come iscrivere a bilancio? IRES 24% sui crypto-asset come ricavi?
- [ ] **Distribuzione personale**: se vuoi prelevare, dividendo (26%) o stipendio amministratore?
- [ ] **Fair value**: la valutazione fiscale del founder reward al 31 dicembre di ogni anno
- [ ] **IVA**: i servizi forniti da Primaris SRLS (custodia, mining pool) sono IVA-esenti come servizi finanziari? Da verificare
- [ ] **Mining personale**: i tuoi guadagni dal mining personale (non founder reward) sono "redditi diversi" ex art. 67 TUIR (26%, soglia non imponibile €2.000/anno)

---

## 🚀 ORDINE OPERATIVO SUGGERITO PER IL LANCIO

1. **Settimane 1-2**: backup off-site (#9), wallet cifrato server-side (#6), versione inglese (#10)
2. **Settimane 3-4**: comprare e configurare VPS seed (#5), code signing certificato (#7)
3. **Settimane 5-6**: whitepaper bozza (#8), consulenza con avvocato MiCA (Fase 4), commercialista
4. **Settimana 7**: revisione finale documenti legali, decisione data lancio
5. **Settimana 8 — Lancio**:
   - Generare genesis nonce (#1)
   - Generare address founder reward Primaris SRLS (#2)
   - Riattivare assert (#3)
   - Compilare binari finali (#4)
   - Avviare seed nodes
   - Pubblicare annuncio su BitcoinTalk, Reddit r/CryptoCurrency, etc.
   - Iniziare il mining "forte" tu (Decisione 5: fino all'arrivo della community)

---

## 📦 INVENTARIO REPO E COMMIT GIT

### Repo: `/home/ubuntu/bitcoboost-src/` (codice C++ del fork Bitcoin Core 27.1)
Branch attivo: `mainnet-launch-redesign`

```
e34317c  fix(chain): aggiunge checkpoint placeholder per evitare segfault
050940f  feat(chain): mainnet launch redesign
30b110f  docs: design document mainnet launch (decisioni progettuali)
0457eb8  Bitcoboost: import X16RV2 algo + custom modifications (pre-launch state)
03ccdc3  Bitcoboost Core – initial source import (fork of Bitcoin Core v27.1.0)
```

File chiave:
- `CHAIN_DESIGN.md` — decisioni progettuali (LEGGI PER PRIMO se qualcuno riprende il lavoro)
- `src/kernel/chainparams.cpp` — riscritto: nuovo genesis, powLimit, magic, seed
- `src/validation.cpp` — slow start + founder reward
- `src/pow.cpp` — retarget veloce
- `src/primitives/block.cpp` — X16RV2 sempre attivo
- `src/consensus/params.h` — nFastRetarget*

### Repo: `/var/www/bitcoboost-app/` (backend Express + Postgres)
Branch: `main`
```
c420dac  backend: FRONT-7 rate limit su /api/users/resolve
37aec4e  Initial commit - import stato 9 maggio 2026
```

### Repo: `/var/www/bitcoboost-site/` (frontend statico)
Branch: `main`
```
26f76ef  frontend: FRONT-1 WIF in memoria volatile + FRONT-4 privacy/cookie/terms
09dc484  frontend: FRONT-2 NET allineato a BB + FRONT-3 onclick inline rimossi
59c128e  Initial commit - import stato 9 maggio 2026
```

### Documenti di riferimento
- `bitcoboost_analisi_completa.md` — analisi tecnica completa pre-lavori (creato 9 maggio 2026)
- `CHAIN_DESIGN.md` — decisioni progettuali (in `bitcoboost-src/`)
- `LAUNCH_CHECKLIST.md` — questo documento

### Credenziali sensibili (NON committare in Git)
- `/root/b2b/rpc_creds_new.txt` — RPC credentials nodi (mode 600, solo root)
- `/root/b2b/fileserver.token` — Token di accesso al fileserver
- `/etc/bitcoboost/bb_app.env` — DB password, JWT secret, Resend API key

### Backup automatici
- `/root/bb_backups/postgres/*.sql.gz` — DB giornaliero (retention 7gg)
- `/root/bb_backups/chain/*.tar.gz` — Chain settimanale (retention 4 settimane)
- `/root/bb_archive_20260509/` — File `.bak` storici archiviati il 9 maggio 2026 (1.8 GB, cancellabili dopo qualche settimana)

---

*Documento maintained-by: Massimiliano Cescon, fondatore. Qualsiasi modifica significativa va aggiornata qui.*
