import os
import struct
from core.scanner import identify_file

def preview_file(file_path):
    filename = os.path.basename(file_path)
    size = os.path.getsize(file_path)
    file_type = identify_file(file_path)

    print(f"\n{'-'*50}")
    print(f"  File:   {filename}")
    print(f"  Size:   {_fmt_size(size)}")
    print(f"  Type:   {file_type}")

    if size == 0:
        print("  Status: empty file")
        print(f"{'-'*50}\n")
        return

    with open(file_path, 'rb') as f:
        header = f.read(64)

    _show_type_info(file_type, header, size)

    print(f"{'-'*50}\n")


def _show_type_info(file_type, header, size):
    if file_type == "png":
        if len(header) >= 24:
            w = struct.unpack_from('>I', header, 16)[0]
            h = struct.unpack_from('>I', header, 20)[0]
            print(f"  Image:  {w}x{h} PNG")
    elif file_type == "jpeg":
        print(f"  Image:  JPEG")
    elif file_type == "dds":
        if len(header) >= 16:
            hd = header[12:16]
            w = struct.unpack_from('<I', header, 12)[0]
            h = struct.unpack_from('<I', header, 16)[0]
            px = header[24]
            print(f"  Image:  {w}x{h} DDS (pixel={px})")
    elif file_type == "konami_cpk":
        if len(header) >= 44:
            ver = struct.unpack_from('<I', header, 8)[0]
            cnt = struct.unpack_from('<I', header, 40)[0]
            print(f"  CPK:    v{ver}, ~{cnt} files")
    elif file_type == "konami_afs":
        if len(header) >= 8:
            cnt = struct.unpack_from('<I', header, 4)[0]
            print(f"  AFS:    {cnt} files")
    elif file_type == "unreal_pak":
        if len(header) >= 20:
            ver = struct.unpack_from('<I', header, 8)[0]
            cnt = struct.unpack_from('<I', header, 16)[0]
            print(f"  PAK:    v{ver}, ~{cnt} files")
    elif file_type == "unity_bundle":
        sig = header[:7].decode('utf-8', errors='replace')
        print(f"  Unity:  {sig}")
    elif file_type == "bres":
        if len(header) >= 12:
            import json
            cnt = struct.unpack_from('>I', header, 8)[0]
            print(f"  BRES:   {cnt} sections")
    elif file_type == "ogg":
        print(f"  Audio:  Ogg Vorbis")
    elif file_type == "wav" or file_type == "riff":
        print(f"  Audio:  WAV/RIFF")
    elif file_type == "zip":
        print(f"  Archive: ZIP")
    elif file_type == "gzip":
        print(f"  Archive: GZip")
    elif file_type == "lz4":
        print(f"  Compressed: LZ4")
    elif file_type == "deflate":
        print(f"  Compressed: DEFLATE")
    elif file_type == "unknown":
        _show_hex(header)
    else:
        print(f"  Engine: {file_type}")


def _show_hex(header):
    hex_str = ' '.join(f'{b:02X}' for b in header[:16])
    ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in header[:16])
    print(f"  RAW:    {hex_str}")
    print(f"  ASCII:  {ascii_str}")


def _fmt_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size/1024:.1f} KB"
    elif size < 1024**3:
        return f"{size/1024**2:.1f} MB"
    else:
        return f"{size/1024**3:.2f} GB"
