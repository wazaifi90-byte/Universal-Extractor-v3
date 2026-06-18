import os


def yaz0_decode(data, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.decoded")
    try:
        if data[:4] != b'Yaz0' and data[:4] != b'Yay0':
            fallback = os.path.join(output_dir, filename)
            with open(fallback, 'wb') as f:
                f.write(data)
            return True
        dec_size = int.from_bytes(data[4:8], 'big')
        src = data[16:]
        result = bytearray()
        i = 0
        while len(result) < dec_size and i < len(src):
            code_byte = src[i]
            i += 1
            if i >= len(src):
                break
            for bit in range(8):
                if len(result) >= dec_size:
                    break
                if i >= len(src):
                    break
                if code_byte & (0x80 >> bit):
                    result.append(src[i])
                    i += 1
                else:
                    if i + 1 >= len(src):
                        break
                    lo = src[i]
                    hi = src[i + 1]
                    i += 2
                    offset = ((hi & 0xF0) << 4) | lo
                    length = (hi & 0x0F) + 2
                    if offset == 0:
                        break
                    for _ in range(length):
                        if len(result) >= dec_size:
                            break
                        if offset <= len(result):
                            result.append(result[-offset])
                        else:
                            result.append(0)
                    if i >= len(src):
                        break
        if len(result) > dec_size:
            result = result[:dec_size]
        elif len(result) < dec_size:
            result.extend(b'\x00' * (dec_size - len(result)))
        with open(out_path, 'wb') as f:
            f.write(result)
        print(f"  Yaz0/Yay0 decoded -> {os.path.basename(out_path)} ({len(result)} bytes)")
        return True
    except Exception as e:
        print(f"  Yaz0 error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True


def yaz0_decompress(data):
    try:
        if data[:4] not in (b'Yaz0', b'Yay0'):
            return data
        dec_size = int.from_bytes(data[4:8], 'big')
        src = data[16:]
        result = bytearray()
        i = 0
        while len(result) < dec_size and i < len(src):
            code_byte = src[i]
            i += 1
            if i >= len(src):
                break
            for bit in range(8):
                if len(result) >= dec_size:
                    break
                if i >= len(src):
                    break
                if code_byte & (0x80 >> bit):
                    result.append(src[i])
                    i += 1
                else:
                    if i + 1 >= len(src):
                        break
                    lo = src[i]
                    hi = src[i + 1]
                    i += 2
                    offset = ((hi & 0xF0) << 4) | lo
                    length = (hi & 0x0F) + 2
                    if offset == 0:
                        break
                    for _ in range(length):
                        if len(result) >= dec_size:
                            break
                        if offset <= len(result):
                            result.append(result[-offset])
                        else:
                            result.append(0)
        return bytes(result[:dec_size])
    except:
        return data
