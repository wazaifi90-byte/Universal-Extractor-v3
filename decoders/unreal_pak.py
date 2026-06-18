import os
import struct

PAK_MAGIC = b'\x41\x0E\x00\x00\x00\x00\x00\x00'

class UnrealPak:
    @staticmethod
    def identify(data):
        return len(data) >= 8 and data[:8] == PAK_MAGIC

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_unreal")
        os.makedirs(base, exist_ok=True)

        version = struct.unpack_from('<I', data, 8)[0]
        sub_version = struct.unpack_from('<I', data, 12)[0]
        file_count = struct.unpack_from('<I', data, 16)[0]
        name_offset = struct.unpack_from('<Q', data, 24)[0]

        info = (
            f"Unreal Pak File\n"
            f"Version: {version}\n"
            f"Sub-version: {sub_version}\n"
            f"File count: {file_count}\n"
            f"Name offset: {name_offset}\n"
            f"Total size: {len(data)}\n"
        )

        offset = 32
        extracted = 0
        files_dir = os.path.join(base, "files")
        os.makedirs(files_dir, exist_ok=True)

        while offset < len(data) - 128 and extracted < 50:
            name_len = struct.unpack_from('<I', data, offset)[0]
            if name_len == 0 or name_len > 256:
                offset += 1
                continue
            name_end = offset + 4 + name_len
            raw_name = data[offset+4:name_end]
            raw_name = raw_name.split(b'\x00')[0]
            try:
                entry_name = raw_name.decode('utf-8', errors='replace').strip()
            except:
                offset = name_end
                continue
            if not entry_name:
                offset = name_end
                continue
            entry_offset = struct.unpack_from('<Q', data, name_end)[0]
            entry_size = struct.unpack_from('<Q', data, name_end + 8)[0]
            if entry_size > 0 and entry_size < 100 * 1024 * 1024:
                if entry_offset + entry_size <= len(data):
                    entry_data = data[entry_offset:entry_offset + entry_size]
                    safe_name = entry_name.replace('\\', '_').replace('/', '_').replace('..', '')
                    out_path = os.path.join(files_dir, f"{extracted:04d}_{safe_name}")
                    with open(out_path, 'wb') as f:
                        f.write(entry_data)
                    info += f"  [{extracted}] {entry_name} ({entry_size} bytes)\n"
                    extracted += 1
            offset = name_end + 16

        with open(os.path.join(base, "pak_info.txt"), 'w', encoding='utf-8') as f:
            f.write(info)
        print(f"  Unreal Pak: {extracted} file(s) extracted")
        return True
