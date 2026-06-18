import os
import struct

class UnityBundle:
    @staticmethod
    def identify(data):
        return data[:7] in (b'UnityWe', b'UnityFS', b'UnityRa')

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_unity")
        os.makedirs(base, exist_ok=True)

        header = data[:8].decode('utf-8', errors='replace')
        with open(os.path.join(base, "header.txt"), 'w') as f:
            f.write(f"Bundle Type: {header}\n")
            f.write(f"Size: {len(data)} bytes\n")

        magic = data[:7]
        if magic == b'UnityFS':
            _parse_unityfs(data, data, base, filename)
        elif magic == b'UnityWe':
            _parse_unityweb(data, base, filename)
        else:
            _dump_chunks(data, data, base, filename)

        print(f"  Unity bundle extracted -> {base}")
        return True


class UnityAssets:
    @staticmethod
    def identify(data):
        if len(data) < 8:
            return False
        return data[0] == 0x06

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_assets")
        os.makedirs(base, exist_ok=True)
        metadata_size = struct.unpack_from('<I', data, 4)[0]
        with open(os.path.join(base, "metadata.txt"), 'w') as f:
            f.write(f"Assets file\n")
            f.write(f"Metadata size: {metadata_size}\n")
            f.write(f"Total size: {len(data)}\n")
        with open(os.path.join(base, "raw_data.bin"), 'wb') as f:
            f.write(data)
        print(f"  Unity assets extracted -> {base}")
        return True


def _parse_unityfs(data, full_data, base, filename):
    info = f"UnityFS bundle: {len(data)} bytes\n"
    cab_dir = os.path.join(base, "cabinet")
    os.makedirs(cab_dir, exist_ok=True)
    cab_count = 0
    for i in range(0, len(data) - 4, 4):
        if data[i:i+4] == b'CAB-':
            end = data.find(b'\x00', i, i + 256)
            if end == -1:
                end = i + 64
            cab_name = data[i:end].decode('utf-8', errors='replace').strip('\x00')
            with open(os.path.join(cab_dir, f"{cab_name}.cab"), 'wb') as f:
                chunk = data[i:i+65536]
                f.write(chunk)
            cab_count += 1
            info += f"  Cabinet: {cab_name}\n"
    with open(os.path.join(base, "bundle_info.txt"), 'w') as f:
        f.write(info)
    print(f"  UnityFS: {cab_count} cabinet(s) found")


def _parse_unityweb(data, base, filename):
    info_path = os.path.join(base, "unityweb_info.txt")
    with open(info_path, 'w') as f:
        f.write("UnityWeb Bundle\n")


def _dump_chunks(data, full_data, base, filename):
    chunks_dir = os.path.join(base, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    for i in range(0, len(data) - 4, 4096):
        chunk = data[i:i+4096]
        fname = os.path.join(chunks_dir, f"chunk_{i//4096:06d}.bin")
        with open(fname, 'wb') as f:
            f.write(chunk)
