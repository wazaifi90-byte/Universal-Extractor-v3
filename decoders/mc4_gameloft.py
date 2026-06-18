import os
import struct
import zlib


class MC4Gameloft:
    type_name = "mc4_gameloft"

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_mc4")
        os.makedirs(base, exist_ok=True)
        results = []
        idx = 0
        total = 0
        TYPE_MAP = {
            b"RIFF": ".wav", b"OggS": ".ogg", b"BRES": ".bres",
            b"BMP ": ".bmp", b"PVR!": ".pvr", b"DDS ": ".dds",
        }
        while idx < len(data) - 30:
            if data[idx : idx + 2] != b"PK":
                idx += 1
                continue
            sig = data[idx : idx + 4]
            if sig not in (b"PK\x03\x04", b"PK\x01\x02", b"PK\x05\x06"):
                idx += 1
                continue
            if sig == b"PK\x05\x06":
                break
            if sig == b"PK\x01\x02":
                idx += 46
                continue
            comp_sz = struct.unpack_from("<I", data, idx + 18)[0]
            fn_len = struct.unpack_from("<H", data, idx + 26)[0]
            extra_len = struct.unpack_from("<H", data, idx + 28)[0]
            if fn_len <= 0 or fn_len > 260:
                idx += 2
                continue
            fn_bytes = data[idx + 30 : idx + 30 + fn_len]
            fn_str = fn_bytes.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            data_start = idx + 30 + fn_len + extra_len
            data_end = data_start + comp_sz
            if data_end > len(data):
                break
            raw = data[data_start:data_end]
            base_name = os.path.splitext(fn_str)[0] if fn_str else f"file_{total}"
            decomp = _decompress_obfs(raw)
            ext = _detect_ext(decomp, TYPE_MAP)
            out_name = f"{base_name}{ext}"
            out_path = os.path.join(base, out_name)
            directory = os.path.dirname(out_path)
            os.makedirs(directory, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(decomp)
            results.append(out_name)
            total += 1
            idx = data_end
        return results


def _decompress_obfs(data):
    if len(data) < 10:
        return data
    try:
        return zlib.decompress(data[8:], -zlib.MAX_WBITS)
    except Exception:
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except Exception:
            return data


def _detect_ext(raw, type_map):
    if len(raw) >= 4:
        sig = raw[:4]
        if sig in type_map:
            return type_map[sig]
        if sig[:3] in (b"FWS", b"CWS"):
            return ".swf"
        if sig[:3] == b"Gam" or sig[:3] == b"GAM":
            return ".gameloft"
        if sig[:3] == b"ID3":
            return ".mp3"
    if len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xF0) == 0xF0:
        return ".mp3"
    if len(raw) and raw[0] == 0x23:
        return ".shader"
    if len(raw) >= 8 and raw[:4] == b"\x89PNG":
        return ".png"
    if len(raw) >= 2 and raw[:2] == b"\xFF\xD8":
        return ".jpg"
    return ".bin"
