import os


def lzss_decode(data, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.decoded")
    try:
        result = bytearray()
        i = 0
        while i < len(data):
            flag = data[i]
            i += 1
            if i >= len(data):
                break
            for bit in range(8):
                if i >= len(data):
                    break
                if flag & (1 << bit):
                    if i + 1 < len(data):
                        result.append(data[i])
                        i += 1
                else:
                    if i + 1 < len(data):
                        lo = data[i]
                        hi = data[i + 1] if i + 1 < len(data) else 0
                        offset = ((hi & 0xF0) << 4) | lo
                        length = (hi & 0x0F) + 3
                        i += 2
                        for _ in range(length):
                            if offset > 0 and offset <= len(result):
                                result.append(result[-offset])
                            else:
                                result.append(0)
        with open(out_path, 'wb') as f:
            f.write(result)
        print(f"  LZSS decoded -> {os.path.basename(out_path)} ({len(result)} bytes)")
        return True
    except Exception as e:
        print(f"  LZSS error: {e}")
        out_path2 = os.path.join(output_dir, filename)
        with open(out_path2, 'wb') as f:
            f.write(data)
        return True
