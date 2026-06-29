import os, json, http.client, base64, struct, hashlib, time

# === CONFIG ===
DATADIR = r"D:\bitcoboost\bb_main_boost7"
RPC_HOST = "127.0.0.1"
RPC_PORT = 38211
PAYOUT_ADDRESS = "BQtaQLBGt5JycnqzCv2H3g1xgaX63oMr4C"

ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def read_cookie(datadir):
    with open(os.path.join(datadir, ".cookie"), "r", encoding="utf-8") as f:
        return f.read().strip()

def rpc(method, params=None):
    if params is None: params = []
    payload = json.dumps({"jsonrpc":"1.0","id":"bb","method":method,"params":params})
    cookie = read_cookie(DATADIR)
    auth = base64.b64encode(cookie.encode()).decode()
    conn = http.client.HTTPConnection(RPC_HOST, RPC_PORT, timeout=30)
    headers = {"Authorization":"Basic "+auth, "Content-Type":"application/json"}
    conn.request("POST","/",payload,headers)
    resp = conn.getresponse(); data = resp.read(); conn.close()
    j = json.loads(data.decode())
    if j.get("error"): raise RuntimeError(j["error"])
    return j["result"]

def b58decode_check(s):
    s = s.encode() if isinstance(s, str) else s
    num = 0
    for c in s: num = num * 58 + ALPHABET.index(c)
    full = num.to_bytes(25, 'big')
    vh160, chk = full[:-4], full[-4:]
    if hashlib.sha256(hashlib.sha256(vh160).digest()).digest()[:4] != chk:
        raise ValueError("Bad base58 checksum")
    return vh160

def p2pkh_scriptpubkey(addr):
    vh160 = b58decode_check(addr); h160 = vh160[1:21]
    return b"\x76\xa9\x14" + h160 + b"\x88\xac"

def hash256(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def varint(n):
    if n < 0xfd: return struct.pack("<B", n)
    if n <= 0xffff: return b"\xfd" + struct.pack("<H", n)
    if n <= 0xffffffff: return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)

le32 = lambda x: struct.pack("<I", x)
le64 = lambda x: struct.pack("<Q", x)

def bits_to_target(bits):
    exp = bits >> 24; mant = bits & 0xFFFFFF
    return mant * (1 << (8*(exp-3)))

def encode_scriptnum(n:int)->bytes:
    neg = n<0; n = -n if neg else n
    b = bytearray()
    while n: b.append(n & 0xff); n >>= 8
    if not b: b.append(0)
    if b[-1] & 0x80: b.append(0x80 if neg else 0x00)
    elif neg: b[-1] |= 0x80
    return bytes(b)

def coinbase_scriptsig(height:int, message=b"/BB/") -> bytes:
    h_bytes = encode_scriptnum(height)
    ss  = bytes([len(h_bytes)]) + h_bytes
    L = len(message)
    ss += (bytes([L]) + message) if L <= 75 else (b"\x4c"+bytes([L])+message)
    return ss

def make_coinbase_tx(value_sats, height=1, message=b"/BB/"):
    tx  = le32(1)
    tx += varint(1)
    tx += b"\x00"*32 + b"\xff"*4
    ss  = coinbase_scriptsig(height, message)
    tx += varint(len(ss)) + ss
    tx += b"\xff"*4
    tx += varint(1)
    tx += le64(value_sats)
    spk = p2pkh_scriptpubkey(PAYOUT_ADDRESS)
    tx += varint(len(spk)) + spk
    tx += le32(0)
    return tx

def main():
    prevhash = rpc("getblockhash", [0])
    hdr = rpc("getblockheader", [prevhash, True])
    prev_time = int(hdr["time"])
    bits_hex = hdr["bits"]; bits = int(bits_hex, 16)
    target = bits_to_target(bits)

    version = 1
    prev_le = bytes.fromhex(prevhash)[::-1]
    curtime = max(prev_time + 1, int(time.time()))

    COIN = 100_000_000
    cb = make_coinbase_tx(50 * COIN, height=1, message=b"/BB/")
    txid = hash256(cb)[::-1].hex()
    merkle = hash256(cb)

    print(f"[BB] prev={prevhash}")
    print(f"[BB] bits={bits_hex} target=0x{target:064x}")
    print(f"[BB] coinbase_txid={txid}")
    print(f"[BB] merkle_be={merkle.hex()}")
    print(f"[BB] merkle_le={merkle[::-1].hex()}")

    # ⬇️ DIFFERENZA: metto merkle **senza reverse** nell'header
    header  = le32(version) + prev_le + merkle + le32(curtime) + le32(bits) + le32(0)

    # mine
    nonce = 0
    while nonce <= 0xffffffff:
        d = hash256(header[:-4] + le32(nonce))
        if int.from_bytes(d[::-1], 'big') <= target:
            break
        nonce += 1
    if nonce > 0xffffffff: raise RuntimeError("Nonce not found")

    header_final = header[:-4] + le32(nonce)
    block = header_final + varint(1) + cb
    print(f"[BB] nonce={nonce} blockhash={hash256(header_final)[::-1].hex()}")

    res = rpc("submitblock", [block.hex()])
    print(f"[BB] submitblock result: {res}")

if __name__ == "__main__":
    main()

