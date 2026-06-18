import zlib
import os

def deflate_decode(data, output_dir, filename):
    try:
        decompressed = zlib.decompress(data, -15)
    except:
        try:
            decompressed = zlib.decompress(data)
        except Exception as e:
            print(f"  Deflate error: {e}")
            return False
    out_path = os.path.join(output_dir, f"{filename}.decompressed")
    with open(out_path, 'wb') as f:
        f.write(decompressed)
    print(f"  Deflated -> {os.path.basename(out_path)} ({len(decompressed)} bytes)")
    return True
