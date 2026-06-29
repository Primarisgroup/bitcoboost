#!/usr/bin/env python3
import struct, argparse, hashlib

COIN = 100_000_000
PSZ = "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks"
PUBKEY = bytes.fromhex(
    "04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61de"
    "b649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f"
)

def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def u32(i): return struct.pack("<I", i)
def i32(i): return struct.pack("<i", i)
def u64(i): return struct.pack("<Q", i)
def varint(i):
    if i < 0xfd: return struct.pack("<B", i)
    if i <= 0xffff: return b"\xfd"+struct.pack("<H", i)
    if i <= 0xffffffff: return b"\xfe"+struct.pack("<I", i)
    return b"\xff"+struct.pack("<Q", i)

def scriptSig_core_exact():
    # ESATTO come in Core: 04ffff001d0104 <len(msg)> <msg_bytes>
    msg = PSZ.encode("ascii")
    return bytes.fromhex("04ffff001d0104") + bytes([len(msg)]) + msg

def scriptPubKey_core():
    # <65-byte pubkey> OP_CHECKSIG
    return bytes([65]) + PUBKEY + b"\xac"

def coinbase_tx(reward):
    ver = i32(1)
    vin_cnt = varint(1)
    prevout = b"\x00"*32 + u32(0xffffffff)
    ss = scriptSig_core_exact()
    scriptSig = varint(len(ss)) + ss
    seq = u32(0xffffffff)
    vout_cnt = varint(1)
    value = u64(reward)
    spk = scriptPubKey_core()
    spk_ser = varint(len(spk)) + spk
    locktime = u32(0)
    return ver + vin_cnt + prevout + scriptSig + seq + vout_cnt + value + spk_ser + locktime

def header(version, prev, merkle, ntime, nbits, nonce):
    return i32(version) + prev + merkle[::-1] + u32(ntime) + u32(nbits) + u32(nonce)

def bits_to_target(bits):
    n = (bits >> 24) & 0xff
    m = bits & 0x007fffff
    if bits & 0x00800000: m = -m
    if n <= 3: return m >> (8 * (3 - n))
    return m << (8 * (n - 3))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=1757832166)
    ap.add_argument("--bits", type=lambda x:int(x,0), default=0x207fffff)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--reward", type=int, default=50*COIN)
    ap.add_argument("--start-nonce", type=int, default=0)
    args = ap.parse_args()

    tx = coinbase_tx(args.reward)
    merkle = sha256d(tx)
    print(f"[i] MerkleR(exact) = 0x{merkle[::-1].hex()}")

    target = bits_to_target(args.bits)
    prev = b"\x00"*32
    nonce = args.start_nonce
    while True:
        h = sha256d(header(args.version, prev, merkle, args.time, args.bits, nonce))
        if int.from_bytes(h[::-1], "big") <= target:
            print("=== FOUND GENESIS (CORE EXACT) ===")
            print(f"nTime   = {args.time}")
            print(f"nBits   = 0x{args.bits:08x}")
            print(f"nNonce  = {nonce}")
            print(f"Hash    = 0x{h[::-1].hex()}")
            print(f"Merkle  = 0x{merkle[::-1].hex()}")
            return
        nonce = (nonce + 1) & 0xffffffff
        if nonce == 0:
            args.time += 1

if __name__ == "__main__":
    main()
