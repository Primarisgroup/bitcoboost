#!/usr/bin/env python3
import json, subprocess, struct, hashlib, sys, argparse

CLI = r"D:\bitcoboost\src\bitcoin-cli.exe"
A_DATADIR = r"D:\bitcoboost\bb_nodeA"
A_CONF    = r"D:\bitcoboost\emptyA.conf"
RPC_HOST  = "127.0.0.1"
RPC_PORT  = "39211"

DEFAULT_MINER_ADDRESS = "bb1qjdvgy0lrm5gvdvu06qjw8kmd2cadwjmkxzuatu"
DEFAULT_BLOCKS = 1

def u32_le(x): return struct.pack("<I", x)
def u64_le(x): return struct.pack("<Q", x)
def varint(n):
    if n < 0xfd: return bytes([n])
    if n <= 0xffff: return b"\xfd"+struct.pack("<H", n)
    if n <= 0xffffffff: return b"\xfe"+struct.pack("<I", n)
    return b"\xff"+struct.pack("<Q", n)
def dsha256(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def bits_to_target(bits_hex):
    b = bytes.fromhex(bits_hex); exp = b[0]; mant = int.from_bytes(b[1:], "big")
    return mant << (8*(exp-3))

def cli_json(*args):
    base = [CLI, "-rpcconnect="+RPC_HOST, "-rpcport="+RPC_PORT, "-datadir="+A_DATADIR, "-conf="+A_CONF]
    out = subprocess.check_output(base + list(args))
    return json.loads(out.decode("utf-8"))
def cli_text(*args):
    base = [CLI, "-rpcconnect="+RPC_HOST, "-rpcport="+RPC_PORT, "-datadir="+A_DATADIR, "-conf="+A_CONF]
    out = subprocess.check_output(base + list(args))
    return out.decode("utf-8").strip()

def get_scriptpubkey(addr):
    info = cli_json("getaddressinfo", addr)
    spk_hex = info.get("scriptPubKey")
    if not spk_hex: raise RuntimeError("scriptPubKey non trovato per l'indirizzo")
    return bytes.fromhex(spk_hex)

def encode_bip34_height(h):
    res = bytearray(); v = h
    while v > 0: res.append(v & 0xff); v >>= 8
    if len(res)==0: res = bytearray(b"\x00")
    if res[-1] & 0x80: res.append(0x00)
    return bytes(res)

def build_coinbase_tx(height, coinbase_value_sats, miner_spk):
    version = u32_le(2)
    prevout = bytes.fromhex("00"*32) + struct.pack("<I", 0xffffffff)
    height_bytes = encode_bip34_height(height)
    # allunghiamo la scriptsig con un OP_0 per evitare bad-cb-length
    script = bytes([len(height_bytes)]) + height_bytes + b"\x00"
    scriptsig = varint(len(script)) + script
    sequence = struct.pack("<I", 0xffffffff)
    vin = prevout + scriptsig + sequence

    vout = u64_le(coinbase_value_sats) + varint(len(miner_spk)) + miner_spk
    locktime = struct.pack("<I", 0)
    tx = version + varint(1) + vin + varint(1) + vout + locktime
    txid = dsha256(tx)[::-1].hex()
    return tx, txid

def mine_one(addr):
    gbt = cli_json("getblocktemplate", '{"rules":["segwit"]}')
    prev = bytes.fromhex(gbt["previousblockhash"])[::-1]
    ver  = gbt.get("version", 1)
    curtime = gbt["curtime"]
    bits_hex = gbt["bits"]
    target_int = bits_to_target(bits_hex)
    bits_field = bytes.fromhex(bits_hex)[::-1]
    height = gbt["height"]
    coinbase_value = gbt["coinbasevalue"]

    miner_spk = get_scriptpubkey(addr)
    coinbase_tx, coinbase_txid_hex = build_coinbase_tx(height, coinbase_value, miner_spk)
    merkle = bytes.fromhex(coinbase_txid_hex)[::-1]

    header = u32_le(ver) + prev + merkle + struct.pack("<I", curtime) + bits_field
    nonce = 0; best = None
    while nonce <= 0xffffffff:
        hdr = header + u32_le(nonce)
        h = dsha256(hdr)[::-1]; hv = int.from_bytes(h, "big")
        if best is None or hv < best: best = hv
        if hv <= target_int:
            block = hdr + varint(1) + coinbase_tx
            res = cli_text("submitblock", block.hex())
            return {"found": True, "nonce": nonce, "hash": h.hex(), "submit_result": res}
        nonce += 1
    return {"found": False, "best": hex(best) if best else None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=int, default=DEFAULT_BLOCKS, help="quanti blocchi minare")
    ap.add_argument("--address", type=str, default=DEFAULT_MINER_ADDRESS, help="indirizzo di payout")
    args = ap.parse_args()

    print(f"[miner] start address={args.address} blocks={args.blocks}")
    for i in range(args.blocks):
        r = mine_one(args.address)
        print(f"[miner] round {i+1}: {r}")
        if not r.get("found"): sys.exit(1)
    best = cli_text("getbestblockhash")
    hgt  = cli_json("getblockcount")
    bals = cli_json("getbalances")
    print("[miner] besthash:", best)
    print("[miner] height:", hgt)
    print("[miner] balances:", json.dumps(bals, indent=2))

if __name__ == "__main__":
    main()


