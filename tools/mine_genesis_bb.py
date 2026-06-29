#!/usr/bin/env python3
import struct, time, argparse, hashlib

COIN = 100_000_000

def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def ser_u32(i: int) -> bytes:
    return struct.pack("<I", i)

def ser_u64(i: int) -> bytes:
    return struct.pack("<Q", i)

def ser_varint(i: int) -> bytes:
    if i < 0xfd:
        return struct.pack("<B", i)
    elif i <= 0xffff:
        return b"\xfd" + struct.pack("<H", i)
    elif i <= 0xffffffff:
        return b"\xfe" + struct.pack("<I", i)
    else:
        return b"\xff" + struct.pack("<Q", i)

def bits_to_target(bits: int) -> int:
    n = (bits >> 24) & 0xff
    m = bits & 0x007fffff
    if bits & 0x00800000:
        m = -m
    if n <= 3:
        return m >> (8 * (3 - n))
    else:
        return m << (8 * (n - 3))

def coinbase_tx(coinbase_msg: bytes, reward_sats: int) -> bytes:
    version = ser_u32(1)
    vin_cnt = ser_varint(1)
    prevout = b"\x00" * 32 + ser_u32(0xffffffff)  # coinbase
    scriptSig = ser_varint(len(coinbase_msg)) + coinbase_msg
    sequence = ser_u32(0xffffffff)
    vout_cnt = ser_varint(1)
    value = ser_u64(reward_sats)  # 50 BTC in satoshi (uint64)
    spk = b"\x76\xa9\x14" + (b"\x00" * 20) + b"\x88\xac"  # P2PKH a 20 zeri
    spk_ser = ser_varint(len(spk)) + spk
    locktime = ser_u32(0)
    return version + vin_cnt + prevout + scriptSig + sequence + vout_cnt + value + spk_ser + locktime

def header(version: int, prev: bytes, merkle: bytes, ntime: int, nbits: int, nonce: int) -> bytes:
    assert len(prev) == 32 and len(merkle) == 32
    return ser_u32(version) + prev + merkle[::-1] + ser_u32(ntime) + ser_u32(nbits) + ser_u32(nonce)

def main():
    ap = argparse.ArgumentParser(description="Mine BitcoBoost genesis block")
    ap.add_argument("--message", default="BitcoBoost genesis by Massimiliano - 2025-09-14")
    ap.add_argument("--time", type=int, default=int(time.time()))
    ap.add_argument("--bits", type=lambda x: int(x, 0), default=0x207fffff)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--reward", type=int, default=50*COIN)
    ap.add_argument("--start-nonce", type=int, default=0)
    args = ap.parse_args()

    msg = args.message.encode("utf-8")
    tx = coinbase_tx(msg, args.reward)
    txid = sha256d(tx)
    merkle = txid  # single-tx merkle
    prev = b"\x00" * 32
    target = bits_to_target(args.bits)

    print(f"[i] nTime={args.time} nBits=0x{args.bits:08x} startNonce={args.start_nonce}")
    print(f"[i] MerkleR = 0x{merkle[::-1].hex()}")

    nonce = args.start_nonce
    best = (1 << 256) - 1
    best_hash = None
    best_nonce = nonce

    while nonce <= 0xffffffff:
        hdr = header(args.version, prev, merkle, args.time, args.bits, nonce)
        h = sha256d(hdr)
        h_int = int.from_bytes(h[::-1], "big")
        if h_int <= target:
            print("=== FOUND GENESIS ===")
            print(f"nTime   = {args.time}")
            print(f"nBits   = 0x{args.bits:08x}")
            print(f"nNonce  = {nonce}")
            print(f"Hash    = 0x{h[::-1].hex()}")
            print(f"Merkle  = 0x{merkle[::-1].hex()}")
            return
        nonce += 1

if __name__ == "__main__":
    main()
