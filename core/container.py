import os
import struct
from core.scanner import identify_bytes, _load_signatures

CARVER_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': ('png', 8),
    b'\xff\xd8\xff': ('jpeg', 3),
    b'GIF87a': ('gif', 6),
    b'GIF89a': ('gif', 6),
    b'RIFF': ('riff', 4),
    b'PK\x03\x04': ('zip', 4),
    b'PK\x05\x06': ('zip', 4),
    b'PK\x07\x08': ('zip', 4),
    b'\x1f\x8b': ('gzip', 2),
    b'BZh': ('bzip2', 3),
    b'\x78\x9c': ('deflate', 2),
    b'\x78\xda': ('deflate', 2),
    b'\x78\x01': ('deflate', 2),
    b'\x04\x22\x4d\x18': ('lz4', 4),
    b'\x28\xb5\x2f\xfd': ('zstd', 4),
    b'UnityWeb': ('unity_bundle', 8),
    b'UnityFS': ('unity_bundle', 7),
    b'UnityRa': ('unity_bundle', 7),
    b'GDPC': ('godot_pck', 4),
    b'Yaz0': ('yaz0', 4),
    b'Yay0': ('yaz0', 4),
    b'PSAR': ('psarc', 4),
    b'BINK': ('bink', 4),
    b'BIKi': ('bink', 4),
    b'FSB4': ('fsb', 4),
    b'FSB5': ('fsb', 4),
    b'BKHD': ('wwise_bnk', 4),
    b'OggS': ('ogg', 4),
    b'fLaC': ('flac', 4),
    b'DDS ': ('dds', 4),
    b'CPK ': ('konami_cpk', 4),
    b'KONAMI': ('konami_arc', 6),
    b'VPK\x00': ('source_vpk', 4),
    b'RPA\x02': ('renpy_rpa', 4),
    b'RPA\x03': ('renpy_rpa', 4),
    b'RGSS': ('rgss', 4),
    b'BRES': ('bres', 4),
}

FOOTER_SIGNATURES = {
    b'IEND': ('png', 4),
    b'\x00\x00\x00\x00\x00\x00\x00\x00': ('jpeg_end', 8),
}


def _find_all_matches(data, sig_bytes, min_offset=0):
    matches = []
    offset = min_offset
    while offset < len(data):
        pos = data.find(sig_bytes, offset)
        if pos == -1:
            break
        matches.append(pos)
        offset = pos + 1
    return matches


def _estimate_size(data, offset, file_type):
    sample = data[offset:offset + 64]

    if file_type == 'png':
        if len(data) >= offset + 24:
            w = struct.unpack_from('>I', data, offset + 16)[0]
            h = struct.unpack_from('>I', data, offset + 20)[0]
            estimated = (w * h * 4) + offset + 100
            if offset + 8 < len(data):
                iend_pos = data.find(b'IEND', offset + 8)
                if iend_pos != -1:
                    return iend_pos + 8 - offset
            return min(estimated - offset, len(data) - offset)

    elif file_type == 'jpeg':
        end_pos = data.find(b'\xff\xd9', offset + 2)
        if end_pos != -1:
            return end_pos + 2 - offset

    elif file_type == 'zip':
        for marker in (b'PK\x05\x06', b'PK\x07\x08'):
            pos = data.rfind(marker, offset)
            if pos != -1 and pos > offset:
                return pos + len(marker) - offset

    elif file_type == 'gzip':
        if data[offset + 3] & 0x1C:
            pass
        if len(data) >= offset + 10:
            isize = struct.unpack_from('<I', data, len(data) - 4)[0]
            return min(len(data) - offset, 10 + 65536)

    elif file_type == 'riff':
        if len(data) >= offset + 8:
            chunk_size = struct.unpack_from('<I', data, offset + 4)[0]
            return min(chunk_size + 8, len(data) - offset)

    elif file_type == 'deflate':
        return min(64 * 1024, len(data) - offset)

    elif file_type in ('lz4', 'zstd', 'bzip2'):
        return min(1024 * 1024, len(data) - offset)

    elif file_type == 'ogg':
        next_page = data.find(b'OggS', offset + 4)
        if next_page != -1:
            return next_page - offset

    return min(512 * 1024, len(data) - offset)


def extract_nested(data, output_dir, base_name, depth=0):
    if depth > 5:
        sub_dir = os.path.join(output_dir, f"{base_name}_nested")
        os.makedirs(sub_dir, exist_ok=True)
        fallback = os.path.join(sub_dir, f"depth_limit_{base_name}")
        with open(fallback, 'wb') as f:
            f.write(data)
        return

    sub_dir = os.path.join(output_dir, f"{base_name}_nested")
    os.makedirs(sub_dir, exist_ok=True)

    found = []
    for sig_bytes, (ft, sig_len) in CARVER_SIGNATURES.items():
        matches = _find_all_matches(data, sig_bytes)
        for pos in matches:
            size = min(_estimate_size(data, pos, ft), len(data) - pos)
            if size < 16:
                continue
            if any(abs(pos - f[0]) < 8 for f in found):
                continue
            found.append((pos, ft, size))

    found.sort(key=lambda x: x[0])

    used_ranges = []
    for idx, (pos, ft, size) in enumerate(found):
        overlap = False
        for r_start, r_end in used_ranges:
            if pos < r_end and (pos + size) > r_start:
                overlap = True
                break
        if overlap:
            continue

        chunk = data[pos:pos + size]
        fname = f"{base_name}_carved{idx:03d}_{ft}"
        fpath = os.path.join(sub_dir, fname)
        with open(fpath, 'wb') as f:
            f.write(chunk)
        used_ranges.append((pos, pos + size))

        if len(chunk) > 64:
            extract_nested(chunk, sub_dir, fname, depth + 1)


def quick_carve(data, output_dir, base_name):
    extract_nested(data, output_dir, base_name, depth=0)
