import os
import struct

class Gameloft:
    @staticmethod
    def identify(data):
        return data[:4] in (b'GLPK', b'GLTX', b'GLSH', b'GAMEDATA')

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_gameloft")
        os.makedirs(base, exist_ok=True)

        magic = data[:4]
        info = f"Gameloft Archive\nMagic: {magic}\nSize: {len(data)} bytes\n"

        try:
            if magic == b'GLPK':
                num_files = struct.unpack_from('<I', data, 4)[0]
                info += f"Package with {num_files} file(s)\n"
                offset = 8
                for i in range(min(num_files, 500)):
                    if offset + 4 > len(data):
                        break
                    name_len = struct.unpack_from('<I', data, offset)[0]
                    if name_len == 0 or name_len > 128:
                        offset += 1
                        continue
                    name = data[offset+4:offset+4+name_len].split(b'\x00')[0]
                    name = name.decode('utf-8', errors='replace')
                    offset += 4 + name_len
                    if offset + 8 > len(data):
                        break
                    f_size = struct.unpack_from('<I', data, offset)[0]
                    f_offset_off = offset + 8
                    if f_offset_off + 4 > len(data):
                        break
                    f_offset = struct.unpack_from('<I', data, f_offset_off)[0]
                    f_data = data[f_offset:f_offset + f_size]
                    fname = f"{i:04d}_{name}"
                    fpath = os.path.join(base, fname)
                    with open(fpath, 'wb') as f:
                        f.write(f_data)
                    info += f"  [{i}] {name} ({f_size} bytes)\n"
                    offset = f_offset_off + 4

            elif magic == b'GLTX':
                info += "Texture archive\n"
                with open(os.path.join(base, "texture_data.bin"), 'wb') as f:
                    f.write(data)

            else:
                with open(os.path.join(base, "unknown_data.bin"), 'wb') as f:
                    f.write(data)

        except Exception as e:
            info += f"Error during extraction: {e}\n"

        with open(os.path.join(base, "gameloft_info.txt"), 'w', encoding='utf-8') as f:
            f.write(info)
        print(f"  Gameloft archive processed -> {base}")
        return True
