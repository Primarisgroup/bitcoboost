#!/usr/bin/env python3
import struct, time, argparse, hashlib

COIN = 100_000_000
PSZ = "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks"
PUBKEY = bytes.fromhex(
    "04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61de"
    "b649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f"
)

def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def ser_u32(i: int) -> bytes: return struct.pack("<I", i)
def ser_i32(i: int) -> bytes: return struct.pack("<i", i)
def ser_u64(i: int) -> bytes: return struct.pack("<Q", i)

def ser_varint(i: int) -> bytes:
    if i < 0xfd: return struct.pack("<B", i)
    elif i <= 0xffff: return b"\xfd" + struct.pack("<H", i)
    elif i <= 0xffffffff: return b"\xfe" + struct.pack("<I", i)
    else: return b"\xff" + struct.pack("<Q", i)

def bits_to_target(bits: int) -> int:
    n = (bits >> 24) & 0xff
    m = bits & 0x007fffff
    if bits & 0x00800000: m = -m
    return (m >> (8*(3-n))) if n <= 3 else (m << (8*(n-3)))

# --- scriptSig esatto stile Core:
# push 4 bytes: ffff001d, poi push 1 byte: 04, poi il messaggio Times
def script_sig_core():
    msg = PSZ.encode("ascii")
    return b"\x04\xff\xff\x00\x1d\x01\x04" + bytes([len(msg)]) + msg

# scriptPubKey: <65-byte pubkey> OP_CHECKSIG
def script_pubkey_core():
    return bytes([65]) + PUBKEY + b"\xac"

def make_coinbase_tx(reward_sats: int) -> bytes:
    version = ser_i32(1)
    vin_cnt = ser_varint(1)
    prevout = b"\x00"*32 + ser_u32(0xffffffff)
    s = script_sig_core()
    scriptSig = ser_varint(len(s)) + s
    sequence = ser_u32(0xffffffff)
    vout_cnt = ser_varint(1)
    value = ser_u64(reward_sats)
    spk = script_pubkey_core()
    spk_ser = ser_varint(len(spk)) + spk
    locktime = ser_u32(0)
    return version + vin_cnt + prevout + scriptSig + sequence + vout_cnt + value + spk_ser + locktime

def block_header(version:int, prev:bytes, merkle:bytes, ntime:int, nbits:int, nonce:int) -> bytes:
    return ser_i32(version) + prev + merkle[::-1] + ser_u32(ntime) + ser_u32(nbits) + ser_u32(nonce)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=1757832166)
    ap.add_argument("--bits", type=lambda x: int(x,0), default=0x207fffff)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--reward", type=int, default=50*COIN)
    ap.add_argument("--start-nonce", type=int, default=0)
    args = ap.parse_args()

    tx = make_coinbase_tx(args.reward)
    merkle = sha256d(tx)
    print(f"[i] MerkleR(core) = 0x{merkle[::-1].hex()}")

    target = bits_to_target(args.bits)
    prev = b"\x00"*32
    nonce = args.start_nonce

    while True:
        hdr = block_header(args.version, prev, merkle, args.time, args.bits, nonce)
        h = sha256d(hdr)
        if int.from_bytes(h[::-1], "big") <= target:
            print("=== FOUND GENESIS (CORE STYLE) ===")
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
