import os
from decoders.image_helper import decode_etc1, decode_pvrtc

def etc1_decode(data, output_dir, filename):
    return decode_etc1(data, 256, 256, output_dir, filename)

def pvrtc_decode(data, output_dir, filename):
    return decode_pvrtc(data, 256, 256, output_dir, filename)
