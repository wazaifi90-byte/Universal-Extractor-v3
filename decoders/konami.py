import os
import struct

class KonamiCPK:
    @staticmethod
    def identify(data):
        return data[:4] == b'CPK '

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_cpk")
        os.makedirs(base, exist_ok=True)

        try:
            header_size = struct.unpack_from('<I', data, 4)[0]
            version = struct.unpack_from('<I', data, 8)[0]
            table_offset = struct.unpack_from('<Q', data, 16)[0]
            table_size = struct.unpack_from('<Q', data, 24)[0]
            file_count = struct.unpack_from('<I', data, 40)[0]

            info = (
                f"CRI CPK Container\n"
                f"Version: {version}\n"
                f"Header size: {header_size}\n"
                f"Table offset: 0x{table_offset:X}\n"
                f"Table size: {table_size}\n"
                f"File count: {file_count}\n"
                f"Total size: {len(data)} bytes\n\n"
            )

            files_dir = os.path.join(base, "files")
            os.makedirs(files_dir, exist_ok=True)

            if table_offset > 0 and table_offset < len(data):
                table_data = data[table_offset:table_offset + min(table_size, len(data) - table_offset)]
                entries = _parse_cpk_toc(table_data, len(data))
                info += f"Found {len(entries)} TOC entries\n"
                for i, (name, offset, size) in enumerate(entries[:500]):
                    if offset + size <= len(data) and size > 0:
                        file_data = data[offset:offset + size]
                        safe = name.replace('/', '_').replace('\\', '_').strip()
                        if not safe:
                            safe = f"file_{i:04d}"
                        fpath = os.path.join(files_dir, safe)
                        with open(fpath, 'wb') as f:
                            f.write(file_data)
                        info += f"  [{i}] {name} ({size} bytes)\n"

            with open(os.path.join(base, "cpk_info.txt"), 'w', encoding='utf-8') as f:
                f.write(info)
            print(f"  CRI CPK: {file_count} files -> {base}")
            return True

        except Exception as e:
            print(f"  CPK parse error: {e}")
            return False


class KonamiAFS:
    @staticmethod
    def identify(data):
        return data[:4] == b'AFS\x00'

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_afs")
        os.makedirs(base, exist_ok=True)

        try:
            file_count = struct.unpack_from('<I', data, 4)[0]
            info = f"AFS Archive\nFiles: {file_count}\nSize: {len(data)} bytes\n\n"

            files_dir = os.path.join(base, "files")
            os.makedirs(files_dir, exist_ok=True)

            entries = []
            offset_pos = 8
            for i in range(min(file_count, 1000)):
                if offset_pos + 8 > len(data):
                    break
                f_offset = struct.unpack_from('<I', data, offset_pos)[0]
                f_size = struct.unpack_from('<I', data, offset_pos + 4)[0]
                entries.append((f_offset, f_size))
                offset_pos += 8

            for i, (f_offset, f_size) in enumerate(entries):
                if f_offset + f_size <= len(data):
                    file_data = data[f_offset:f_offset + f_size]
                    fpath = os.path.join(files_dir, f"{i:04d}.bin")
                    with open(fpath, 'wb') as f:
                        f.write(file_data)
                    info += f"  [{i}] offset=0x{f_offset:X} size={f_size}\n"

            with open(os.path.join(base, "afs_info.txt"), 'w') as f:
                f.write(info)
            print(f"  AFS: {file_count} file(s) -> {base}")
            return True

        except Exception as e:
            print(f"  AFS parse error: {e}")
            return False


def _parse_cpk_toc(toc_data, total_size):
    entries = []
    offset = 0
    while offset < len(toc_data) - 16:
        tag = toc_data[offset:offset + 4]
        if tag == b'TOC\x00':
            break
        if tag == b'\x00' * 4:
            offset += 4
            continue
        name_end = toc_data.find(b'\x00', offset)
        if name_end == -1 or name_end - offset > 256:
            offset += 4
            continue
        name = toc_data[offset:name_end].decode('utf-8', errors='replace')
        if not name or len(name) < 1:
            offset = name_end + 1
            continue
        entry_offset = len(toc_data) + offset
        data_start = entry_offset + 16
        if data_start > total_size:
            offset = name_end + 1
            continue
        data_size = min(total_size - data_start, 1024 * 1024)
        entries.append((name, data_start, data_size))
        offset = name_end + 1
        if len(entries) > 1000:
            break
    return entries


def konami_extract(data, output_dir, filename):
    magic = data[:4]
    if magic == b'CPK ':
        return KonamiCPK.extract(data, output_dir, filename)
    elif magic == b'AFS\x00':
        return KonamiAFS.extract(data, output_dir, filename)
    elif magic in (b'KONA', b'ARC\x00'):
        base = os.path.join(output_dir, f"{filename}_konami")
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "raw_archive.bin"), 'wb') as f:
            f.write(data)
        with open(os.path.join(base, "info.txt"), 'w') as f:
            f.write(f"Konami Archive\nMagic: {magic}\nSize: {len(data)}\n")
        print(f"  Konami archive saved -> {base}")
        return True
    else:
        print(f"  Unknown Konami format: {magic}")
        return False
