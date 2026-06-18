import os
import struct


def vpk_extract(data, output_dir, filename):
    base = os.path.join(output_dir, f"{filename}_vpk")
    os.makedirs(base, exist_ok=True)

    if data[:4] == b'VPK\x00':
        version = struct.unpack_from('<I', data, 4)[0]
        tree_size = struct.unpack_from('<I', data, 8)[0]
        info_path = os.path.join(base, "vpk_header.txt")
        with open(info_path, 'w') as f:
            f.write(f"VPK Archive v{version}\n")
            f.write(f"Tree size: {tree_size}\n")
            f.write(f"Total size: {len(data)} bytes\n")
        raw_path = os.path.join(base, f"vpk_data.bin")
        with open(raw_path, 'wb') as f:
            f.write(data)
        print(f"  Source VPK extracted -> {base}")
        return True

    fallback_path = os.path.join(base, f"source_raw_{filename}.bin")
    with open(fallback_path, 'wb') as f:
        f.write(data)
    print(f"  Source engine (fallback) -> {base}")
    return True


def source_extract(data, output_dir, filename):
    base = os.path.join(output_dir, f"{filename}_source")
    os.makedirs(base, exist_ok=True)

    if data[:3] == b'BSP':
        version = struct.unpack_from('<I', data, 3)[0]
        info_path = os.path.join(base, "bsp_header.txt")
        with open(info_path, 'w') as f:
            f.write(f"Source BSP v{version}\n")
            f.write(f"Size: {len(data)} bytes\n")
        raw_path = os.path.join(base, f"bsp_{filename}.bin")
        with open(raw_path, 'wb') as f:
            f.write(data)
        print(f"  Source BSP extracted -> {base}")
        return True

    for offset in range(0, min(len(data) - 8, 1024), 4):
        sig = data[offset:offset+4]
        if sig in (b'diot', b'vtex', b'vmt\x00', b'mdl\x00', b'phy\x00', b'anim'):
            info_path = os.path.join(base, "source_analysis.txt")
            with open(info_path, 'w') as f:
                f.write(f"Source asset detected\n")
                f.write(f"Signature: {sig.decode('utf-8', errors='replace')} at offset {offset}\n")
                f.write(f"Size: {len(data)} bytes\n")
            raw_path = os.path.join(base, f"source_asset_{filename}.bin")
            with open(raw_path, 'wb') as f:
                f.write(data)
            print(f"  Source asset extracted -> {base}")
            return True

    fallback = os.path.join(base, f"source_raw_{filename}")
    with open(fallback, 'wb') as f:
        f.write(data)
    return True
