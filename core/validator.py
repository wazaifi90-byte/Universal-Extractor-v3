import os
import json

_HASH = None

def _get_hasher():
    global _HASH
    if _HASH is not None:
        return _HASH
    try:
        import xxhash
        _HASH = xxhash.xxh64
        return _HASH
    except ImportError:
        try:
            import hashlib
            _HASH = lambda: hashlib.md5()
            return _HASH
        except:
            _HASH = False
            return None

def hash_file(filepath):
    hasher_fn = _get_hasher()
    if not hasher_fn:
        return None
    h = hasher_fn()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def hash_data(data):
    hasher_fn = _get_hasher()
    if not hasher_fn:
        return None
    h = hasher_fn()
    h.update(data)
    return h.hexdigest()

class StreamingHasher:
    def __init__(self):
        hasher_fn = _get_hasher()
        self._h = hasher_fn() if hasher_fn else None

    def update(self, chunk):
        if self._h:
            self._h.update(chunk)

    def hexdigest(self):
        return self._h.hexdigest() if self._h else None

    def algorithm(self):
        if self._h is None:
            return "none"
        name = type(self._h).__name__
        if "xxhash" in name or "xxh" in name:
            return "xxh64"
        return name


def validate_image(filepath):
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            img.verify()
        return True, "ok"
    except ImportError:
        return None, "PIL not installed"
    except Exception as e:
        return False, str(e)


def validate_file(filepath, file_type):
    ext = filepath.lower()
    if file_type in ("png", "jpeg", "gif", "bmp", "tga", "dds",
                     "pvrtc", "etc1", "webp", "tga"):
        return validate_image(filepath)
    return None, "no validator"


def make_output_report(output_dir, filename, file_type, hash_val, valid, valid_msg):
    report = {
        "file": filename,
        "type": file_type,
        "hash": hash_val,
        "hash_algorithm": "xxh64" if hash_val and len(hash_val) == 16 else "md5" if hash_val else "none",
        "valid": valid,
        "validation_message": valid_msg,
    }
    report_path = os.path.join(output_dir, f"{filename}.report.json")
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
    except:
        pass
    return report_path
