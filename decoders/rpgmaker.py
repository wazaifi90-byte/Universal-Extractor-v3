import os
import struct


def rgss_extract(data, output_dir, filename):
    base = os.path.join(output_dir, f"{filename}_rgss")
    os.makedirs(base, exist_ok=True)

    if data[:4] == b'RGSS':
        version = struct.unpack_from('<I', data, 4)[0] if len(data) > 8 else 0
        info_path = os.path.join(base, "rgss_info.txt")
        with open(info_path, 'w') as f:
            f.write(f"RGSS Archive v{version}\n")
            f.write(f"Size: {len(data)} bytes\n")
        raw_path = os.path.join(base, f"rgss_data.bin")
        with open(raw_path, 'wb') as f:
            f.write(data)
        print(f"  RPG Maker RGSS extracted -> {base}")
        return True

    for offset in range(0, min(len(data) - 4, 4096), 1):
        if data[offset:offset+4] == b'RGSS':
            version = struct.unpack_from('<I', data, offset + 4)[0] if len(data) > offset + 8 else 0
            info_path = os.path.join(base, "rgss_embedded.txt")
            with open(info_path, 'w') as f:
                f.write(f"RGSS Archive (embedded at offset {offset})\n")
                f.write(f"Version: {version}\n")
                f.write(f"Total size: {len(data)} bytes\n")
            raw_path = os.path.join(base, f"rgss_embedded.bin")
            chunk = data[offset:]
            with open(raw_path, 'wb') as f:
                f.write(chunk)
            print(f"  RPG Maker RGSS (embedded) extracted -> {base}")
            return True

    if data[:4] == b'RGD\x00':
        info_path = os.path.join(base, "rgd_header.txt")
        with open(info_path, 'w') as f:
            f.write(f"RPG Maker RGD\nSize: {len(data)} bytes\n")
        raw_path = os.path.join(base, f"rgd_data.bin")
        with open(raw_path, 'wb') as f:
            f.write(data)
        print(f"  RPG Maker RGD extracted -> {base}")
        return True

    fallback = os.path.join(base, f"rpg_raw_{filename}")
    with open(fallback, 'wb') as f:
        f.write(data)
    print(f"  RPG Maker (fallback) -> {base}")
    return True
