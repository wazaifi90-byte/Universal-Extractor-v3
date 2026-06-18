import os
import json
import math
import struct
import zlib
from collections import Counter

_HAS_NUMPY = False
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    pass

FP_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fingerprints.json")

_fingerprint_db = None


class SmartClassifier:
    def __init__(self, db_path=None):
        self.db_path = db_path or FP_DB_PATH
        self.known_signatures = {}
        self.load()

    def load(self):
        if os.path.exists(self.db_path):
            with open(self.db_path) as f:
                data = json.load(f)
                for fmt, vector in data.get("signature_vectors", {}).items():
                    self.known_signatures[fmt] = vector

    def save(self, db):
        with open(self.db_path, "w") as f:
            json.dump(db, f, indent=2)

    def generate_vector(self, data_bytes):
        if not data_bytes:
            return None
        if _HAS_NUMPY:
            arr = np.frombuffer(data_bytes[:4096], dtype=np.uint8)
            counts = np.bincount(arr, minlength=256)
            return (counts / len(arr)).tolist()
        else:
            total = min(len(data_bytes), 4096)
            counts = [0] * 256
            for b in data_bytes[:total]:
                counts[b] += 1
            return [c / total for c in counts]

    def classify(self, data_bytes, threshold=0.15):
        target = self.generate_vector(data_bytes)
        if not target or not self.known_signatures:
            return "unknown", 0.0
        best_match = "unknown"
        min_dist = float('inf')
        t_arr = target if not _HAS_NUMPY else np.array(target)
        for fmt, vector in self.known_signatures.items():
            if _HAS_NUMPY:
                dist = float(np.linalg.norm(np.array(vector) - t_arr))
            else:
                dist = sum(abs(a - b) for a, b in zip(target, vector)) / len(target)
            if dist < min_dist:
                min_dist = dist
                best_match = fmt
        confidence = max(0, 100 * (1 - min_dist))
        if min_dist > threshold:
            return "unknown", round(confidence, 1)
        return best_match, round(confidence, 1)

    def train(self, format_name, data_bytes):
        vector = self.generate_vector(data_bytes)
        if vector is None:
            return
        if format_name in self.known_signatures:
            old = self.known_signatures[format_name]
            self.known_signatures[format_name] = [(a + b) / 2 for a, b in zip(old, vector)]
        else:
            self.known_signatures[format_name] = vector
        db = _load_db()
        db["signature_vectors"] = self.known_signatures
        _save_db_to(db, self.db_path)


def _save_db_to(db, path=None):
    p = path or FP_DB_PATH
    with open(p, "w") as f:
        json.dump(db, f, indent=2)


def _load_db():
    global _fingerprint_db
    if _fingerprint_db is not None:
        return _fingerprint_db
    if os.path.exists(FP_DB_PATH):
        with open(FP_DB_PATH) as f:
            _fingerprint_db = json.load(f)
    else:
        _fingerprint_db = {
            "magic_signatures": {},
            "entropy_ranges": {},
            "known_patterns": {},
            "signature_vectors": {}
        }
    return _fingerprint_db


def _save_db():
    if _fingerprint_db:
        with open(FP_DB_PATH, "w") as f:
            json.dump(_fingerprint_db, f, indent=2)


def _entropy(data):
    if not data:
        return 0
    if _HAS_NUMPY:
        arr = np.frombuffer(data, dtype=np.uint8)
        counts = np.bincount(arr, minlength=256)
        probs = counts[counts > 0] / len(arr)
        return -float(np.sum(probs * np.log2(probs)))
    counts = Counter(data)
    total = len(data)
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log2(p)
    return round(ent, 4)


def _detect_encryption(data):
    scores = {}
    xor_key = _detect_xor_key(data[:256])
    if xor_key is not None:
        scores["xor"] = {"confidence": "medium", "key_candidate": xor_key}
    if data and data[0] == 0 and all(b != 0 for b in data[1:16]):
        scores["encrypted_offset"] = {"confidence": "low", "note": "Starts with null byte"}
    return scores


def _detect_xor_key(data):
    if not data:
        return None
    candidates = Counter()
    common_keys = [0x00, 0xFF, 0xAA, 0x55, 0x01, 0x80, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]
    for key in common_keys:
        decoded = bytes(b ^ key for b in data[:64])
        score = sum(32 <= b < 127 or b in (0, 9, 10, 13) for b in decoded)
        if score > len(decoded) * 0.6:
            candidates[key] = score
    if candidates:
        return candidates.most_common(1)[0][0]
    return None


def _detect_archive_structure(data):
    if len(data) < 16:
        return None
    try:
        toc_entries = struct.unpack_from("<I", data[4:8])[0]
        if 1 <= toc_entries <= 100000 and len(data) > toc_entries * 32:
            return {"type": "archive", "entries": toc_entries, "confidence": "low"}
    except:
        pass
    return None


def analyze(data, file_path=None):
    result = {
        "size": len(data),
        "entropy": _entropy(data[:1024]),
        "entropy_full": _entropy(data) if len(data) < 1048576 else None,
        "magic_bytes": data[:16].hex(),
        "has_null_header": data[:4] == b'\x00\x00\x00\x00' if data else False,
        "is_compressed": False,
        "suggested_formats": [],
        "encryption": None,
    }

    try:
        zlib.decompress(data[:256], -15)
        result["is_compressed"] = True
        result["suggested_formats"].append("raw_deflate")
    except:
        pass

    try:
        import lz4.block
        lz4.block.decompress(data[:256])
        result["is_compressed"] = True
        result["suggested_formats"].append("lz4")
    except:
        pass

    if data[:4] == b'\x89PNG':
        result["suggested_formats"].append("png")
    elif data[:2] == b'\xFF\xD8':
        result["suggested_formats"].append("jpeg")
    elif data[:4] == b'RIFF':
        if b'WAVE' in data[:16]:
            result["suggested_formats"].append("wav")
        elif b'WEBP' in data[:16]:
            result["suggested_formats"].append("webp")
        else:
            result["suggested_formats"].append("riff")
    elif data[:4] == b'OggS':
        result["suggested_formats"].append("ogg")
    elif data[:4] == b'DDS ':
        result["suggested_formats"].append("dds")
    elif data[:3] == b'GIF':
        result["suggested_formats"].append("gif")
    elif data[:4] in (b'Unity', b'\x55\x6E\x69\x74'):
        result["suggested_formats"].append("unity_bundle")
    elif data[:4] == b'CPK ':
        result["suggested_formats"].append("konami_cpk")

    enc = _detect_encryption(data)
    if enc:
        result["encryption"] = enc

    arch = _detect_archive_structure(data)
    if arch:
        result["suggested_formats"].append("archive")
        result["archive_hint"] = arch

    return result


def train_from_sample(file_path, label):
    db = _load_db()
    with open(file_path, 'rb') as f:
        header = f.read(64)
    ent = _entropy(header)
    if label not in db["entropy_ranges"]:
        db["entropy_ranges"][label] = {"min": ent, "max": ent, "count": 1}
    else:
        r = db["entropy_ranges"][label]
        r["min"] = min(r["min"], ent)
        r["max"] = max(r["max"], ent)
        r["count"] += 1
    _save_db()


def analyze_with_ai(data):
    classifier = SmartClassifier()
    label, confidence = classifier.classify(data)
    ent = _entropy(data[:1024])
    features = {
        "entropy": round(ent, 2),
        "null_ratio": round(data.count(0) / max(len(data), 1), 4),
        "printable_ratio": round(sum(1 for b in data[:256] if 32 <= b <= 126) / max(len(data[:256]), 1), 4),
    }
    return {
        "ai_label": label,
        "ai_confidence": confidence,
        "features": features
    }


def fingerprint_file(file_path):
    with open(file_path, 'rb') as f:
        data = f.read(4096)
    result = analyze(data, file_path)
    db = _load_db()
    ent = result["entropy"]
    for label, r in db.get("entropy_ranges", {}).items():
        if r["min"] <= ent <= r["max"]:
            if label not in result["suggested_formats"]:
                result["suggested_formats"].append(f"ml:{label}")
    result["file_path"] = file_path
    return result


def format_list():
    FMT_GROUPS = {
        "compression": ["deflate", "lz4", "lzma", "gzip", "zip", "zstd", "bzip2", "lzo", "lzss"],
        "image": ["png", "jpeg", "gif", "bmp", "tga", "webp", "dds", "astc", "ktx", "gtf", "pvrtc", "etc1", "tiff", "ico", "pcx"],
        "audio": ["ogg", "wav", "mp3", "flac", "aac", "xma", "fsb", "wwise_wem", "wwise_bnk", "bink"],
        "game_engine": ["unity_bundle", "unity_assets", "unreal_pak", "unreal_uexp", "cocos2d", "gameloft_archive", "gameloft_pak", "gameloft_tex", "gameloft_sh", "konami_cpk", "konami_afs", "konami_arc", "godot_pck", "rpgmaker_archive"],
        "console": ["bres", "yaz0", "psarc", "xpr0"],
        "other": ["riff", "crx", "rl7", "sqex_pak", "rpgmvp", "xor"]
    }
    count = sum(len(v) for v in FMT_GROUPS.values())
    return FMT_GROUPS, count
