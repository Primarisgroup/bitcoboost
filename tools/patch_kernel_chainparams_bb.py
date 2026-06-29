# -*- coding: utf-8 -*-
# Patch "mirato" per D:\bitcoboost\src\kernel\chainparams.cpp (MAIN only)
# Modifica:
#  - genesis MAIN -> (1757832166, 2, 0x207fffff, 1, 50*COIN)
#  - assert hashGenesisBlock MAIN
#  - magic bytes MAIN -> b1 74 c0 b0
#  - bech32_hrp MAIN -> "bb"
#  - nDefaultPort MAIN -> 38200
#  - seeds MAIN -> clear
import re, sys, pathlib

src_path = pathlib.Path(r"D:\bitcoboost\src\kernel\chainparams.cpp")
if not src_path.exists():
    print("[ERRORE] File non trovato:", src_path)
    sys.exit(1)

txt = src_path.read_text(encoding="utf-8", errors="ignore")

# --- Trova i blocchi MAIN e TESTNET per limitare la patch ---
# MAIN: riconosciuto dai magic bytes standard di Bitcoin main
m_main = re.search(r"pchMessageStart\[0\]\s*=\s*0x[fF]9;.*?pchMessageStart\[3\]\s*=\s*0x[dD]9;", txt, re.S)
if not m_main:
    print("[ERRORE] Non trovo il blocco MAIN (pchMessageStart f9 be b4 d9).")
    sys.exit(1)
main_start, main_end = m_main.span()
# Estendiamo fine MAIN fino all'inizio del prossimo set di magic (testnet) o fine file
m_next_magic = re.search(r"pchMessageStart\[0\]\s*=\s*0x[0-9a-fA-F]+;", txt[main_end:], re.S)
main_region_end = main_end + (m_next_magic.start() if m_next_magic else 0)
if not m_next_magic:
    # fallback: se non troviamo altri magic, usa una finestra più ampia dopo il main
    main_region_end = min(len(txt), main_end + 5000)

main_region = txt[main_start:main_region_end]
orig_main = main_region

changes = 0

# 1) Magic bytes MAIN -> b1 74 c0 b0
replacements_magic = {
    r"pchMessageStart\[0\]\s*=\s*0x[0-9a-fA-F]+;": "pchMessageStart[0] = 0xb1;",
    r"pchMessageStart\[1\]\s*=\s*0x[0-9a-fA-F]+;": "pchMessageStart[1] = 0x74;",
    r"pchMessageStart\[2\]\s*=\s*0x[0-9a-fA-F]+;": "pchMessageStart[2] = 0xc0;",
    r"pchMessageStart\[3\]\s*=\s*0x[0-9a-fA-F]+;": "pchMessageStart[3] = 0xb0;",
}
for pat, rep in replacements_magic.items():
    main_region, n = re.subn(pat, rep, main_region, count=1, flags=re.M)
    changes += n

# 2) genesis MAIN: sostituisci la riga "genesis = CreateGenesisBlock(...main...)"
gen_pat = r"genesis\s*=\s*CreateGenesisBlock\(\s*1231006505\s*,\s*2083236893\s*,\s*0x1d00ffff\s*,\s*1\s*,\s*50\s*\*\s*COIN\s*\)\s*;"
gen_new = "genesis = CreateGenesisBlock(1757832166, 2, 0x207fffff, 1, 50 * COIN);"
main_region, n = re.subn(gen_pat, gen_new, main_region, count=1)
changes += n

# 3) consensus.hashGenesisBlock assert MAIN
assert_pat = r'assert\s*\(\s*consensus\.hashGenesisBlock\s*==\s*uint256S\("\s*0x[0-9a-fA-F]+"\s*\)\s*\)\s*;'
assert_new = 'assert(consensus.hashGenesisBlock == uint256S("0x2d0f0826e7fdafbb268711cc2dcf1afc45003406893a764cc4fa2acf964566a0"));'
main_region, n = re.subn(assert_pat, assert_new, main_region, count=1)
changes += n

# 4) bech32_hrp MAIN -> "bb"
main_region, n = re.subn(r'bech32_hrp\s*=\s*"[a-z0-9]+"', 'bech32_hrp = "bb"', main_region, count=1)
changes += n

# 5) nDefaultPort MAIN -> 38200 (se presente nel blocco)
main_region, n = re.subn(r"nDefaultPort\s*=\s*\d+\s*;", "nDefaultPort = 38200;", main_region, count=1)
changes += n

# 6) Seeds MAIN -> clear
# Rimuove le righe vSeeds.emplace_back(...) nel main, e impone clear()
main_region = re.sub(r'^\s*vSeeds\.emplace_back\(.*?\);\s*$', '', main_region, flags=re.M)
if "vSeeds.clear();" not in main_region:
    main_region += "\n    vSeeds.clear();\n    vFixedSeeds.clear();\n"
else:
    # garantisci anche vFixedSeeds.clear();
    if "vFixedSeeds.clear();" not in main_region:
        main_region = main_region.replace("vSeeds.clear();", "vSeeds.clear();\n    vFixedSeeds.clear();")

if main_region == orig_main:
    print("[ATTENZIONE] Nessuna modifica applicata al blocco MAIN (pattern non trovati?).")
else:
    # Rimonta il file
    new_txt = txt[:main_start] + main_region + txt[main_region_end:]
    backup = src_path.with_suffix(".cpp.bak")
    backup.write_text(txt, encoding="utf-8")
    src_path.write_text(new_txt, encoding="utf-8")
    print("[OK] Patch MAIN applicata. Modifiche:", changes)
    print("[OK] Backup creato:", backup)
