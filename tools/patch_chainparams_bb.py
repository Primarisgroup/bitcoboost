# -*- coding: utf-8 -*-
import re, sys, pathlib

SRC = pathlib.Path(r"D:\bitcoboost\src\chainparams.cpp")

# === Valori del tuo genesis (dalla Fase 1) ===
GEN_TIME  = 1757832166
GEN_BITS  = 0x207fffff
GEN_NONCE = 2
GEN_HASH  = "2d0f0826e7fdafbb268711cc2dcf1afc45003406893a764cc4fa2acf964566a0"
GEN_MERKLE= "dd2491673e44cb74a87a11d93b35bdd96a529b2e4669ddb3cbd84a94c521284a"

# === Scelte BitcoBoost ===
MSG = (0xB1,0x74,0xC0,0xB0)   # magic bytes
PORT = 38200                  # P2P port
HRP  = "bb"                   # Bech32 HRP
# Base58 prefixes (diversi da BTC)
PUBKEY_ADDRESS = 25
SCRIPT_ADDRESS = 85
SECRET_KEY     = 153
EXT_PUB = [0x04, 0x5B, 0xE4, 0x9A]
EXT_SEC = [0x04, 0x5B, 0xE4, 0xA3]

def fail(msg):
    print("[ERRORE]", msg)
    sys.exit(1)

def replace_once(text, pattern, repl, flags=re.DOTALL):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n == 0:
        print("[!] Pattern non trovato, nessuna sostituzione:\n", pattern[:120], "...")
    return new, n

if not SRC.exists():
    fail(f"File non trovato: {SRC}")

code = SRC.read_text(encoding="utf-8", errors="ignore")

# Limitiamo le modifiche alla sola classe CMainParams (dal costruttore fino all'inizio di CTestNetParams)
m_start = re.search(r"class\s+ CMainParams\b.*?\{.*?CMainParams::CMainParams\s*\(\s*\)\s*\{", code, re.DOTALL)
if not m_start:
    fail("Inizio CMainParams non trovato.")
start_idx = m_start.start()

m_block = re.search(r"CMainParams::CMainParams\s*\(\s*\)\s*\{", code[start_idx:], re.DOTALL)
if not m_block:
    fail("Costruttore CMainParams non trovato.")
cons_start = start_idx + m_block.start()

# fine: prima di CTestNetParams (o fine file)
m_end = re.search(r"\bclass\s+ CTestNetParams\b", code[cons_start:], re.DOTALL)
cons_end = cons_start + (m_end.start() if m_end else len(code)-cons_start)

segment = code[cons_start:cons_end]

# 1) Sostituisci il blocco genesis + assert
pat_genesis = r"genesis\s*=\s*CreateGenesisBlock\([^;]*?;\s*\)\s*;\s*consensus\.hashGenesisBlock\s*=\s*genesis\.GetHash\(\)\s*;\s*assert\([^;]+?\);\s*assert\([^;]+?\);"
new_genesis = (
    f"genesis = CreateGenesisBlock(\n"
    f"    /* nTime    */ {GEN_TIME},\n"
    f"    /* nNonce   */ {GEN_NONCE},\n"
    f"    /* nBits    */ 0x{GEN_BITS:08x},\n"
    f"    /* nVersion */ 1,\n"
    f"    /* reward   */ 50 * COIN\n"
    f");\n"
    f"consensus.hashGenesisBlock = genesis.GetHash();\n"
    f"assert(consensus.hashGenesisBlock == uint256S(\"{GEN_HASH}\"));\n"
    f"assert(genesis.hashMerkleRoot == uint256S(\"{GEN_MERKLE}\"));"
)
segment, _ = replace_once(segment, pat_genesis, new_genesis)

# 2) Magic bytes
for i, b in enumerate(MSG):
    pat = rf"pchMessageStart\[{i}\]\s*=\s*0x[0-9a-fA-F]+;"
    rep = f"pchMessageStart[{i}] = 0x{b:02x};"
    segment, _ = replace_once(segment, pat, rep, flags=re.MULTILINE)

# 3) Porta P2P
segment, _ = replace_once(segment, r"nDefaultPort\s*=\s*\d+\s*;", f"nDefaultPort = {PORT};", flags=re.MULTILINE)

# 4) Disattiva seeds/DNS
if "vSeeds.clear();" not in segment:
    segment += "\nvSeeds.clear();\nvFixedSeeds.clear();\n"
else:
    segment, _ = replace_once(segment, r"vSeeds\.clear\(\)\s*;\s*vFixedSeeds\.clear\(\)\s*;", "vSeeds.clear();\nvFixedSeeds.clear();", flags=re.DOTALL)

# 5) HRP Bech32
segment, _ = replace_once(segment, r'bech32_hrp\s*=\s*"[a-z0-9]+"', f'bech32_hrp = "{HRP}"', flags=re.MULTILINE)

# 6) Base58 prefixes
def set_prefix(segment, name, val):
    pat = rf"base58Prefixes\[{name}\]\s*=\s*[^;]+;"
    if isinstance(val, int):
        rep = f'base58Prefixes[{name}] = std::vector<unsigned char>(1, {val});'
    else:
        rep = f'base58Prefixes[{name}] = {{' + ", ".join(f"0x{x:02X}" for x in val) + "};"
    return replace_once(segment, pat, rep, flags=re.DOTALL)[0]

segment = set_prefix(segment, "PUBKEY_ADDRESS", PUBKEY_ADDRESS)
segment = set_prefix(segment, "SCRIPT_ADDRESS", SCRIPT_ADDRESS)
segment = set_prefix(segment, "SECRET_KEY",     SECRET_KEY)
segment = set_prefix(segment, "EXT_PUBLIC_KEY", EXT_PUB)
segment = set_prefix(segment, "EXT_SECRET_KEY", EXT_SEC)

# 7) powLimit facile + azzera assumevalid/minwork (sicurezza su chain nuova)
segment, _ = replace_once(segment, r'consensus\.powLimit\s*=\s*uint256S\("[0-9a-fA-F]+"\)\s*;',
                          'consensus.powLimit = uint256S("7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");',
                          flags=re.MULTILINE)
segment, _ = replace_once(segment, r'consensus\.nMinimumChainWork\s*=\s*uint256S\("[0-9a-fA-F]+"\)\s*;',
                          'consensus.nMinimumChainWork = uint256S("00");', flags=re.MULTILINE)
segment, _ = replace_once(segment, r'consensus\.defaultAssumeValid\s*=\s*uint256S\("[0-9a-fA-F]+"\)\s*;',
                          'consensus.defaultAssumeValid = uint256S("00");', flags=re.MULTILINE)

# Rimonta il file
new_code = code[:cons_start] + segment + code[cons_end:]
backup = SRC.with_suffix(".cpp.bak")
backup.write_text(code, encoding="utf-8")
SRC.write_text(new_code, encoding="utf-8")

print("[OK] Patch applicata a CMainParams.")
print(f"[OK] Backup creato: {backup}")
