import os
import re
import json
import struct

KEY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "key_db.json")

COMMON_XOR_KEYS = [
    0x00, 0xFF, 0xAA, 0x55, 0xCC, 0x33, 0x11, 0x88, 0x66, 0x99,
    0x4C, 0x73, 0x2A, 0x5A, 0x7E, 0x3C, 0x1A, 0x6B, 0x0F, 0xF0,
    0x58, 0xA7, 0xCD, 0x12, 0x87, 0x9B, 0x2F, 0xE4, 0xD3, 0xB6,
]

COMMON_MULTI_KEYS = [
    bytes([0xAA, 0x55]),
    bytes([0xCC, 0x33]),
    bytes([0x12, 0x34, 0x56, 0x78]),
    bytes([0xDE, 0xAD, 0xBE, 0xEF]),
    bytes([0x89, 0xAB, 0xCD, 0xEF]),
    bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF]),
    bytes([0xFE, 0xDC, 0xBA, 0x98, 0x76, 0x54, 0x32, 0x10]),
    bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]),
    bytes([0x2A, 0x2A, 0x2A, 0x2A]),
    bytes([0x4C, 0x6F, 0x76, 0x65]),
]


def load_key_db():
    if os.path.exists(KEY_DB_PATH):
        try:
            with open(KEY_DB_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_key_db(db):
    with open(KEY_DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)


def scrape_exe(filepath):
    results = []
    filename = os.path.basename(filepath)
    if not filename.lower().endswith(('.exe', '.dll', '.bin', '.so', '.dylib')):
        return results

    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except:
        return results

    file_hash = _quick_hash(data)

    for key_byte in COMMON_XOR_KEYS:
        count = data.count(bytes([key_byte]))
        if count > 100:
            results.append({
                "type": "xor_byte",
                "value": key_byte,
                "hex": f"0x{key_byte:02X}",
                "occurrences": count,
                "confidence": _confidence(count, len(data)),
            })

    for mk in COMMON_MULTI_KEYS:
        count = data.count(mk)
        if count > 5:
            results.append({
                "type": "xor_multi",
                "value": list(mk),
                "hex": ' '.join(f'0x{b:02X}' for b in mk),
                "occurrences": count,
                "confidence": _confidence(count * len(mk), len(data)),
            })

    for match in _find_repeated_bytes(data):
        results.append(match)

    near_strings = _scan_near_strings(data)
    for ks in near_strings:
        if not any(r['hex'] == ks['hex'] for r in results):
            results.append(ks)

    regions = _find_key_regions(data)
    for r in regions:
        if not any(res['hex'] == r['hex'] for res in results):
            results.append(r)

    sorted_results = sorted(results, key=lambda x: x['confidence'], reverse=True)

    if sorted_results:
        db = load_key_db()
        if filename not in db:
            db[filename] = {
                "hash": file_hash,
                "size": len(data),
                "keys": sorted_results[:5],
            }
            save_key_db(db)

    return sorted_results


def scrape_directory(dirpath):
    all_results = {}
    for root, _, files in os.walk(dirpath):
        for fname in files:
            if fname.lower().endswith(('.exe', '.dll', '.bin', '.so', '.dylib')):
                fpath = os.path.join(root, fname)
                keys = scrape_exe(fpath)
                if keys:
                    all_results[fname] = keys
    return all_results


def _quick_hash(data):
    try:
        import hashlib
        return hashlib.md5(data[:4096]).hexdigest()
    except:
        return str(len(data))


def _confidence(count, total_size):
    ratio = count / max(total_size, 1)
    if ratio > 0.05:
        return "high"
    elif ratio > 0.01:
        return "medium"
    return "low"


def _find_repeated_bytes(data):
    results = []
    for byte_val in range(1, 256):
        pattern = bytes([byte_val]) * 4
        idx = 0
        hits = 0
        while True:
            idx = data.find(pattern, idx)
            if idx == -1:
                break
            hits += 1
            idx += 4
        if hits > 2:
            results.append({
                "type": "repeated_pattern",
                "value": byte_val,
                "hex": f"0x{byte_val:02X} (x4+)",
                "occurrences": hits,
                "confidence": "medium",
            })
            if len(results) > 10:
                break
    return results


def _scan_near_strings(data):
    results = []
    keywords = [b'key', b'xor', b'decrypt', b'cipher', b'encode',
                b'Gameloft', b'gameloft', b'GL', b'CRYPT']
    for kw in keywords:
        idx = 0
        while True:
            idx = data.find(kw, idx)
            if idx == -1:
                break
            start = max(0, idx - 32)
            end = min(len(data), idx + len(kw) + 32)
            region = data[start:end]
            for byte_val in range(1, 256):
                c = region.count(bytes([byte_val]))
                if c > 5:
                    results.append({
                        "type": "near_string",
                        "value": byte_val,
                        "hex": f"0x{byte_val:02X}",
                        "near": kw.decode('ascii', errors='replace'),
                        "occurrences": c,
                        "confidence": "medium",
                    })
                    break
            idx += len(kw)
    return results


def _find_key_regions(data):
    results = []
    chunk_size = 256
    for offset in range(0, len(data) - chunk_size, chunk_size):
        chunk = data[offset:offset + chunk_size]
        freq = {}
        for b in chunk:
            freq[b] = freq.get(b, 0) + 1
        if freq:
            most_common = max(freq, key=freq.get)
            if most_common != 0 and freq[most_common] > chunk_size // 2:
                results.append({
                    "type": "dominant_byte_region",
                    "value": most_common,
                    "hex": f"0x{most_common:02X}",
                    "offset": f"0x{offset:X}",
                    "occurrences": freq[most_common],
                    "confidence": "medium",
                })
    seen = set()
    unique = []
    for r in results:
        if r['hex'] not in seen:
            seen.add(r['hex'])
            unique.append(r)
    return unique[:5]


def suggest_key_for_file(test_filepath):
    with open(test_filepath, 'rb') as f:
        head = f.read(64)
    from decoders.xor_decoder import _detect_key
    detected = _detect_key(head)
    if detected != 0:
        return detected, "auto_detect"

    db = load_key_db()
    for exe_name, info in db.items():
        for k in info.get("keys", []):
            if k.get("type") == "xor_byte":
                return k["value"], f"from_db:{exe_name}"

    return None, None
