import os
import struct

def bres_parse(data, output_dir, filename):
    if data[:4] != b'BRES':
        print(f"  Not a valid BRES file")
        return False

    try:
        base = os.path.join(output_dir, f"{filename}_bres")
        os.makedirs(base, exist_ok=True)

        bom = struct.unpack_from('>H', data, 4)[0]
        big_endian = (bom == 0xFEFF)
        endian_fmt = '>' if big_endian else '<'
        num_sections = struct.unpack_from(f'{endian_fmt}I', data, 8)[0]
        header_size = struct.unpack_from(f'{endian_fmt}I', data, 12)[0]
        version = struct.unpack_from(f'{endian_fmt}I', data, 16)[0]

        info = (
            f"BRES Container\n"
            f"Endian: {'Big' if big_endian else 'Little'}\n"
            f"Sections: {num_sections}\n"
            f"Header: {header_size} bytes\n"
            f"Version: {version}\n"
            f"File size: {len(data)} bytes\n\n"
            f"Sections:\n"
        )

        offset = header_size
        sections_dir = os.path.join(base, "sections")
        os.makedirs(sections_dir, exist_ok=True)

        for i in range(min(num_sections, 200)):
            if offset + 24 > len(data):
                break
            sec_magic = data[offset:offset + 4]
            if sec_magic == b'\x00' * 4:
                offset += 4
                continue
            sec_size = struct.unpack_from(f'{endian_fmt}I', data, offset + 4)[0]
            sec_id = struct.unpack_from(f'{endian_fmt}I', data, offset + 8)[0]
            sec_data_offset = struct.unpack_from(f'{endian_fmt}I', data, offset + 12)[0]
            sec_data_size = struct.unpack_from(f'{endian_fmt}I', data, offset + 16)[0]

            if sec_data_offset > len(data) or sec_data_size > len(data):
                offset += sec_size if sec_size > 0 else 4
                continue

            info += f"  [{i}] {sec_magic.decode('utf-8','replace')} "
            info += f"id={sec_id} "
            info += f"data_offset={sec_data_offset} "
            info += f"data_size={sec_data_size}\n"

            if sec_data_offset + sec_data_size <= len(data) and sec_data_size > 0:
                sec_data = data[sec_data_offset:sec_data_offset + sec_data_size]
                magic_str = sec_magic.decode('utf-8', 'replace').strip('\x00')
                section_path = os.path.join(sections_dir, f"{i:04d}_{magic_str}.bin")
                with open(section_path, 'wb') as f:
                    f.write(sec_data)

            offset += sec_size if sec_size > 0 else 24

        with open(os.path.join(base, "bres_info.txt"), 'w', encoding='utf-8') as f:
            f.write(info)
        print(f"  BRES parsed: {num_sections} section(s) -> {base}")
        return True

    except Exception as e:
        print(f"  BRES parse error: {e}")
        return False
