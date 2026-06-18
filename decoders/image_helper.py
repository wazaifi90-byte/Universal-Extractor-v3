import os
import struct

def save_raw_image(data, width, height, bpp, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.{width}x{height}.raw")
    with open(out_path, 'wb') as f:
        f.write(data)
    return out_path

def try_convert_to_png(raw_path, width, height, mode='RGBA'):
    try:
        from PIL import Image
        img = Image.frombytes(mode, (width, height), open(raw_path, 'rb').read())
        png_path = raw_path.replace('.raw', '.png')
        if png_path == raw_path:
            png_path = raw_path + '.png'
        img.save(png_path)
        return png_path
    except ImportError:
        print("  PIL not installed. Run: pip install Pillow")
        return None
    except Exception as e:
        print(f"  Image conversion error: {e}")
        return None

def decode_etc1(data, width, height, output_dir, filename):
    out_path = os.path.join(output_dir, f"{filename}.etc1.raw")
    with open(out_path, 'wb') as f:
        f.write(data)
    return try_convert_to_png(out_path, width, height, 'RGBA')

def decode_pvrtc(data, width, height, output_dir, filename, is_2bpp=False):
    out_path = os.path.join(output_dir, f"{filename}.pvrtc.raw")
    with open(out_path, 'wb') as f:
        f.write(data)
    return try_convert_to_png(out_path, width, height, 'RGBA')

def decode_dxt(data, width, height, output_dir, filename, dxt_type=1):
    try:
        from PIL import Image
        blocks_x = (width + 3) // 4
        blocks_y = (height + 3) // 4
        pixels = bytearray(width * height * 4)
        for by in range(blocks_y):
            for bx in range(blocks_x):
                block_offset = (by * blocks_x + bx) * 8
                if block_offset + 8 > len(data):
                    break
                c0 = struct.unpack_from('<H', data, block_offset)[0]
                c1 = struct.unpack_from('<H', data, block_offset + 2)[0]
                bits = struct.unpack_from('<I', data, block_offset + 4)[0]
                colors = _dxt_color_table(c0, c1, dxt_type)
                for py in range(4):
                    for px in range(4):
                        idx = (bits >> (2 * (py * 4 + px))) & 3
                        r, g, b, a = colors[idx]
                        ix = (by * 4 + py) * width + (bx * 4 + px)
                        if ix * 4 + 3 < len(pixels):
                            pixels[ix * 4:ix * 4 + 4] = bytes([r, g, b, a])
        out_path = os.path.join(output_dir, f"{filename}.dxt.png")
        img = Image.frombytes('RGBA', (width, height), bytes(pixels))
        img.save(out_path)
        return out_path
    except ImportError:
        print("  PIL not installed")
        return None
    except Exception as e:
        print(f"  DXT decode error: {e}")
        return None

def _dxt_color_table(c0, c1, dxt_type):
    r0 = (c0 >> 11) & 0x1F
    g0 = (c0 >> 5) & 0x3F
    b0 = c0 & 0x1F
    r1 = (c1 >> 11) & 0x1F
    g1 = (c1 >> 5) & 0x3F
    b1 = c1 & 0x1F
    c0_rgb = (r0 * 8, g0 * 4, b0 * 8, 255)
    c1_rgb = (r1 * 8, g1 * 4, b1 * 8, 255)
    if c0 > c1 or dxt_type == 1:
        c2_rgb = ((2 * r0 + r1) * 4, (2 * g0 + g1) * 2, (2 * b0 + b1) * 4, 255)
        c3_rgb = ((2 * r1 + r0) * 4, (2 * g1 + g0) * 2, (2 * b1 + b0) * 4, 255)
        return [c0_rgb, c1_rgb, c2_rgb, c3_rgb]
    else:
        c2_rgb = ((r0 + r1) * 4, (g0 + g1) * 2, (b0 + b1) * 4, 255)
        c3_rgb = (0, 0, 0, 0)
        return [c0_rgb, c1_rgb, c2_rgb, c3_rgb]
