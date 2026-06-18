import os

def lz4_decode(data, output_dir, filename):
    try:
        import lz4.frame
        decompressed = lz4.frame.decompress(data)
    except ImportError:
        print("  lz4 not installed. Run: pip install lz4")
        return False
    except Exception:
        try:
            import lz4.block
            decompressed = lz4.block.decompress(data, uncompressed_size=len(data) * 20)
        except:
            try:
                import lz4
                decompressed = lz4.LZ4_uncompress(data)
            except:
                print("  LZ4: all methods failed")
                return False
    out_path = os.path.join(output_dir, f"{filename}.lz4_out")
    with open(out_path, 'wb') as f:
        f.write(decompressed)
    print(f"  LZ4 decompressed -> {os.path.basename(out_path)} ({len(decompressed)} bytes)")
    return True
