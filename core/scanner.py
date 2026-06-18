import os
import json

_signatures = None

def _load_signatures():
    global _signatures
    if _signatures is not None:
        return _signatures
    sig_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signatures.json")
    if os.path.exists(sig_path):
        with open(sig_path, 'r') as f:
            raw = json.load(f)
        _signatures = {}
        for file_type, info in raw.items():
            magics = []
            for m in info["magic"]:
                if m.startswith("0x"):
                    parts = m.split()
                    magics.append(bytes(int(p, 16) for p in parts))
                else:
                    magics.append(m.encode('utf-8'))
            sub = info.get("sub_check")
            _signatures[file_type] = {
                "magics": magics,
                "extension": info.get("extension", ""),
                "engine": info.get("engine", "generic"),
                "sub_check": sub,
            }
    else:
        _signatures = {}
    return _signatures

def identify_file(file_path):
    with open(file_path, 'rb') as f:
        header = f.read(16)
    return _match_header(header)

def identify_bytes(data):
    header = data[:16]
    return _match_header(header)

def _match_header(header):
    sigs = _load_signatures()
    for file_type, info in sigs.items():
        for magic in info["magics"]:
            if header[:len(magic)] == magic:
                sub = info.get("sub_check")
                if sub:
                    if sub.encode() in header[8:16]:
                        return file_type
                    continue
                return file_type
    try:
        import zlib
        zlib.decompress(header, -15)
        return "deflate"
    except:
        pass
    try:
        import zlib
        zlib.decompress(header)
        return "deflate"
    except:
        pass
    return "unknown"

def get_engine_for_type(file_type):
    sigs = _load_signatures()
    if file_type in sigs:
        return sigs[file_type]["engine"]
    return "generic"

def list_signatures():
    sigs = _load_signatures()
    result = []
    for ft, info in sigs.items():
        for magic in info["magics"]:
            display = magic if isinstance(magic, str) else ' '.join(f'0x{b:02X}' for b in magic[:4])
            result.append((ft, display, info["engine"]))
    return result
