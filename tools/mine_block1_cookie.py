import os, json, http.client, base64, struct, hashlib

# === CONFIG ===
DATADIR = r"D:\bitcoboost\bb_main_boost7"   # <-- il datadir che hai avviato
RPC_HOST = "127.0.0.1"
RPC_PORT = 38211
PAYOUT_ADDRESS = "BPuswuxQwH2gcSzEkx9Pdwuz49XcdXdzq4"  # cambia se vuoi

ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def read_cookie(datadir):
    with open(os.path.join(datadir, ".cookie"), "r", encoding="utf-8") as f:
        return f.read().strip()  # "user:token"

def b58decode_check(s):
    s = s.encode() if isinstance(s, str) else s
    num = 0
    for c in s:
        num = num * 58 + ALPHABET.index(c)
    full = num.to_bytes(25, 'big')
    vh160 = full[:-4]
    chk = full[-4:]
    if hashlib.sha256(hashlib.sha256(vh160).digest()).digest()[:4] != chk:
        raise ValueError("Bad base58 checksum")
    return vh160  # version(1) + hash160(20)

def p2pkh_scriptpubkey(addr):
    vh160 = b58decode_check(addr)
    h160 = vh160[1:21]
    return b"\x76\xa9\x14" + h160 + b"\x88\xac"  # DUP HASH160 <20> h160 EQUALVERIFY CHECKSIG

def hash256(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def varint(n):
    if n < 0xfd: return struct.pack("<B", n)
    if n <= 0xffff: return b"\xfd" + struct.pack("<H", n)
    if n <= 0xffffffff: return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)

def le32(i): return struct.pack("<I", i)
def le64(i): return struct.pack("<Q", i)

def bits_to_target(bits):
    exp = bits >> 24
    mant = bits & 0xFFFFFF
    return mant * (1 << (8*(exp-3)))

def rpc(method, params=None):
    if params is None: params = []
    payload = json.dumps({"jsonrpc":"1.0","id":"bb","method":method,"params":params})
    cookie = read_cookie(DATADIR)  # "user:token"
    auth = base64.b64encode(cookie.encode()).decode()
    conn = http.client.HTTPConnection(RPC_HOST, RPC_PORT, timeout=30)
    headers = {"Authorization":"Basic "+auth, "Content-Type":"application/json"}
    conn.request("POST","/",payload,headers)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    j = json.loads(data.decode())
    if j.get("error"):
        raise RuntimeError(j["error"])
    return j["result"]

def make_coinbase_tx(value_sats, message=b"/BB/"):
    tx = b""
    tx += le32(1)                # version
    tx += varint(1)              # vin count
    tx += b"\x00"*32 + b"\xff"*4 # prevout (coinbase)
    # scriptSig: solo messaggio (BIP34 non attivo alle prime altezze)
    tx += varint(len(message)) + message
    tx += b"\xff"*4              # sequence
    tx += varint(1)              # vout count
    tx += le64(value_sats)       # value
    spk = p2pkh_scriptpubkey(PAYOUT_ADDRESS)
    tx += varint(len(spk)) + spk # scriptPubKey
    tx += le32(0)                # locktime
    return tx

def build_header_and_cb(tpl):
    version = tpl["version"]
    prevhash = bytes.fromhex(tpl["previousblockhash"])[::-1]
    curtime = tpl["curtime"]
    bits_hex = tpl["bits"]; bits = int(bits_hex, 16)
    cb_value = tpl["coinbasevalue"]

    cb = make_coinbase_tx(cb_value)
    merkle = hash256(cb)  # solo coinbase

    header = b""
    header += le32(version)
    header += prevhash
    header += merkle[::-1]
    header += le32(curtime)
    header += le32(bits)
    header += le32(0)  # nonce placeholder
    return header, cb, bits

def mine(header, target):
    nonce = 0
    while nonce <= 0xffffffff:
        h = header[:-4] + le32(nonce)
        d = hash256(h)
        if int.from_bytes(d[::-1], 'big') <= target:
            return nonce, d
        nonce += 1
    raise RuntimeError("nonce not found")

def main():
    tpl = rpc("getblocktemplate", [ {"rules":["legacy"]} ])
    header, cb, bits = build_header_and_cb(tpl)
    target = bits_to_target(bits)
    nonce, bhash = mine(header, target)
    header_final = header[:-4] + le32(nonce)
    block = header_final + varint(1) + cb
    print(f"[BB] prev={tpl['previousblockhash']}")
    print(f"[BB] bits={tpl['bits']} target=0x{target:064x}")
    print(f"[BB] nonce={nonce} hash={bhash[::-1].hex()}")
    res = rpc("submitblock", [block.hex()])
    print(f"[BB] submitblock result: {res}")

if __name__ == "__main__":
    main()
