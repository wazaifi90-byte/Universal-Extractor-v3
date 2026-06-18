import os
import struct


def renpy_extract(data, output_dir, filename):
    base = os.path.join(output_dir, f"{filename}_renpy")
    os.makedirs(base, exist_ok=True)

    if data[:4] in (b'RPA\x02', b'RPA\x03', b'RPA\x01'):
        version = data[3]
        info_path = os.path.join(base, "rpa_info.txt")
        with open(info_path, 'w') as f:
            f.write(f"Ren'Py Archive v{version}\n")
            f.write(f"Size: {len(data)} bytes\n")

        key = 0
        if data[:4] == b'RPA\x03':
            key = struct.unpack_from('<I', data, 4)[0] if len(data) > 8 else 0
            with open(info_path, 'a') as f:
                f.write(f"Key: 0x{key:08X}\n")

        raw_path = os.path.join(base, "rpa_data.bin")
        if key:
            decoded = bytes(b ^ ((key >> (i * 8)) & 0xFF) if key else b for i, b in enumerate(data))
            with open(raw_path, 'wb') as f:
                f.write(decoded)
        else:
            with open(raw_path, 'wb') as f:
                f.write(data)
        print(f"  Ren'Py RPA extracted -> {base}")
        return True

    fallback = os.path.join(base, f"renpy_raw_{filename}")
    with open(fallback, 'wb') as f:
        f.write(data)
    print(f"  Ren'Py (fallback) -> {base}")
    return True
