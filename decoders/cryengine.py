import os
import struct


def cryengine_extract(data, output_dir, filename):
    base = os.path.join(output_dir, f"{filename}_cryengine")
    os.makedirs(base, exist_ok=True)

    if len(data) < 8:
        return False

    magic = data[:4]
    if magic == b'\x00\x00\x00\x00':
        chunk_type = data[4:8].decode('utf-8', errors='replace')
        info_path = os.path.join(base, "cry_info.txt")
        with open(info_path, 'w') as f:
            f.write(f"CryEngine Chunk\n")
            f.write(f"Type: {chunk_type}\n")
            f.write(f"Size: {len(data)} bytes\n")
        raw_path = os.path.join(base, f"chunk_{filename}.bin")
        with open(raw_path, 'wb') as f:
            f.write(data)
        print(f"  CryEngine chunk extracted -> {base}")
        return True

    if len(data) >= 16:
        for offset in range(0, min(len(data) - 8, 4096), 4):
            try:
                sig = data[offset:offset+4].decode('utf-8', errors='replace')
                if sig in ('Chunks', 'Types', 'BoneM', 'NodeC', 'Mesh ', 'Scene'):
                    info_path = os.path.join(base, "cry_analysis.txt")
                    with open(info_path, 'w') as f:
                        f.write(f"CryEngine asset detected\n")
                        f.write(f"Signature: {sig} at offset {offset}\n")
                        f.write(f"Size: {len(data)} bytes\n")
                    raw_path = os.path.join(base, f"cryasset_{filename}.bin")
                    with open(raw_path, 'wb') as f:
                        f.write(data)
                    print(f"  CryEngine asset extracted -> {base}")
                    return True
            except:
                pass

    fallback = os.path.join(base, f"cry_raw_{filename}.bin")
    with open(fallback, 'wb') as f:
        f.write(data)
    print(f"  CryEngine (fallback) -> {base}")
    return True
