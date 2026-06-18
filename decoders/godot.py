import os
import struct


def godot_pck_extract(data, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.pck_info")
    try:
        if data[:4] != b'GDPC':
            fallback = os.path.join(output_dir, filename)
            with open(fallback, 'wb') as f:
                f.write(data)
            return True
        pck_version = struct.unpack_from('<I', data, 4)[0]
        res_count = struct.unpack_from('<I', data, 8)[0]
        if pck_version >= 2:
            res_count = struct.unpack_from('<I', data, 12)[0]
        info = f"Godot PCK v{pck_version}\nFiles: {res_count}\n"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(info)
        print(f"  Godot PCK parsed: {res_count} files")
        return True
    except Exception as e:
        print(f"  Godot error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True
