import os
import json

XOR_COMMON_KEYS = [0x00, 0xFF, 0xAA, 0x55, 0xCC, 0x33, 0x11, 0x88, 0x66, 0x99, 0x4C, 0x73, 0x2A, 0x5A, 0x7E, 0x3C, 0x1A, 0x6B, 0x0F, 0xF0, 0x58, 0xA7, 0xCD, 0x12, 0x87, 0x9B, 0x2F, 0xE4, 0xD3, 0xB6]
_user_key = None

def set_key(key):
    global _user_key
    _user_key = key

def xor_decode(data, output_dir, filename):
    if _user_key is not None:
        key = _user_key
        print(f"  XOR using user key=0x{key:02X}")
    else:
        key = _detect_key(data)
        if key == 0:
            db_key = _lookup_key_db(data)
            if db_key is not None:
                key = db_key
                print(f"  XOR using DB key=0x{key:02X}")
        else:
            print(f"  XOR detected key=0x{key:02X}")

    xored = bytes(b ^ key for b in data)
    out_path = os.path.join(output_dir, f"{filename}.xor_0x{key:02X}")
    with open(out_path, 'wb') as f:
        f.write(xored)
    print(f"  XOR decoded -> {os.path.basename(out_path)}")
    return True

def xor_stream(in_path, output_dir, filename, chunk_size=65536):
    if _user_key is not None:
        key = _user_key
    else:
        with open(in_path, 'rb') as f:
            head = f.read(64)
        key = _detect_key(head)
        if key == 0:
            with open(in_path, 'rb') as f:
                data = f.read(4096)
            db_key = _lookup_key_db(data)
            if db_key is not None:
                key = db_key
    out_path = os.path.join(output_dir, f"{filename}.xor_0x{key:02X}")
    with open(in_path, 'rb') as src, open(out_path, 'wb') as dst:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            dst.write(bytes(b ^ key for b in chunk))
    print(f"  XOR stream decoded (key=0x{key:02X}) -> {os.path.basename(out_path)}")
    return True

def _detect_key(data):
    if len(data) < 4:
        return 0x00
    for key in XOR_COMMON_KEYS:
        test = bytes(b ^ key for b in data[:64])
        text_count = sum(1 for b in test if 0x20 <= b <= 0x7E or b in (0x0A, 0x0D, 0x09))
        if text_count > 32:
            return key
    freq = {}
    for b in data[:4096]:
        freq[b] = freq.get(b, 0) + 1
    if freq:
        most_common = max(freq, key=freq.get)
        return most_common ^ 0x20
    return 0x00

def _lookup_key_db(data):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "key_db.json")
    if not os.path.exists(db_path):
        return None
    try:
        with open(db_path, 'r') as f:
            db = json.load(f)
        for exe_name, info in db.items():
            for k in info.get("keys", []):
                if k.get("type") == "xor_byte":
                    val = k["value"]
                    test = bytes(b ^ val for b in data[:32])
                    text = sum(1 for b in test if 0x20 <= b <= 0x7E)
                    if text > 16:
                        return val
                elif k.get("type") == "xor_multi":
                    mk = bytes(k["value"])
                    test = bytes(data[i] ^ mk[i % len(mk)] for i in range(min(32, len(data))))
                    text = sum(1 for b in test if 0x20 <= b <= 0x7E)
                    if text > 16:
                        return mk[0]
    except:
        pass
    return None

def xor_with_key(data, key):
    return bytes(b ^ key for b in data)
