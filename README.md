# BitcoBoost

BitcoBoost is a public, permissionless **proof-of-work cryptocurrency**. It is a
fork of [Bitcoin Core](https://github.com/bitcoin/bitcoin) 27.1, with its own
network, mining algorithm, and emission schedule.

- **Website:** https://bitcoboost.com
- **Block explorer:** https://explorer.bitcoboost.com

## Key facts

- **Proof of work:** X16RV2 (CPU- and GPU-mineable)
- **Maximum supply:** 21,000,000 BB
- **Fair launch — slow start:** no premine. The block reward starts low and ramps up:
  - blocks 1–1,000: **1 BB**
  - blocks 1,001–2,000: **10 BB**
  - blocks 2,001 onward: **50 BB**, halving every 210,000 blocks (first halving at block 212,001)
- **Founder reward:** 5% of the block reward on blocks 2,001–209,999 (the remaining 95% goes to the miner)
- **Addresses:** native SegWit, bech32 `bb1q…`

## Verify the fair launch yourself

Everything is in this source code — you don't have to trust anyone:

- **Emission schedule (slow start + halving):** `GetBlockSubsidy()` in `src/validation.cpp`
- **21,000,000 cap:** `MAX_MONEY` in `src/consensus/amount.h`
- **Network parameters and seeds:** `src/kernel/chainparams.cpp`
- **No premine:** the genesis block plus the emission schedule above

You can also confirm the live chain on the public explorer.

## Build

BitcoBoost builds like Bitcoin Core. See the platform build guides in `doc/`
(for example `doc/build-unix.md`, `doc/build-windows.md`).

## Run a node and mine

The node connects to the network automatically through the public DNS seeds
(`seed1`/`seed2`/`seed3.bitcoboost.com`, P2P port 38210). You can mine with any
X16RV2-capable miner (`cpuminer-opt` for CPU, `WildRig` for GPU), either solo
(via `getblocktemplate`) or through a pool. A step-by-step guide is available on
the website.

## License

BitcoBoost is released under the **MIT License**, the same as Bitcoin Core. See
`COPYING`. BitcoBoost is a derivative work of Bitcoin Core; all upstream
copyrights are retained.

## Disclaimer

BitcoBoost is experimental software provided "as is", without warranty of any
kind. Use at your own risk.
