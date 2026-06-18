import os
import struct


def psarc_extract(data, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.psarc_info")
    try:
        if data[:4] not in (b'PSAR', b'\x50\x53\x41\x52'):
            fallback = os.path.join(output_dir, filename)
            with open(fallback, 'wb') as f:
                f.write(data)
            return True
        version = struct.unpack_from('<I', data, 4)[0]
        hdr_size = struct.unpack_from('<I', data, 8)[0]
        unk = struct.unpack_from('<I', data, 12)[0]
        blk_size = struct.unpack_from('<I', data, 16)[0]
        file_count = struct.unpack_from('<I', data, 20)[0] if version >= 2 else 0
        info = f"PSARC v{version}\nHeader size: {hdr_size}\nBlock size: {blk_size}\nFiles: {file_count}\n"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(info)
        print(f"  PSARC parsed: v{version}, {blk_size}B blocks, ~{file_count} files")
        toc = data[hdr_size:]
        entries = []
        for i in range(min(file_count, 100)):
            if i * 32 + 32 > len(toc):
                break
            name_len = toc[i * 32]
            fname = toc[i * 32 + 1:i * 32 + 1 + name_len]
            foffset = struct.unpack_from('<Q', toc, i * 32 + 16)[0]
            fsize = struct.unpack_from('<Q', toc, i * 32 + 24)[0]
            entries.append({
                "name": fname.decode('utf-8', errors='replace'),
                "offset": foffset,
                "size": fsize
            })
        if entries:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(info)
                for e in entries:
                    f.write(f"  {e['name']:40s} offset={e['offset']:10d} size={e['size']:10d}\n")
            for e in entries[:10]:
                fstart = hdr_size + e['offset']
                fend = fstart + e['size']
                if fend <= len(data) and e['size'] < 10485760:
                    fpath = os.path.join(output_dir, e['name'])
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)
                    with open(fpath, 'wb') as f:
                        f.write(data[fstart:fend])
                    print(f"    Extracted: {e['name']} ({e['size']} bytes)")
        return True
    except Exception as e:
        print(f"  PSARC error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True
