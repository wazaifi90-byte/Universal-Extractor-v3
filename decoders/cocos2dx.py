import os
import struct

COCO_MAGICS = {
    b'CCB2': "CCB2",
    b'CCBA': "CCBA",
}

class Cocos2dx:
    @staticmethod
    def identify(data):
        return data[:4] in COCO_MAGICS

    @staticmethod
    def extract(data, output_dir, filename):
        base = os.path.join(output_dir, f"{filename}_cocos")
        os.makedirs(base, exist_ok=True)

        magic = data[:4].decode('utf-8', errors='replace')
        info = f"Cocos2d-x File\nMagic: {magic}\nSize: {len(data)} bytes\n"

        if data[:4] == b'CCB2':
            info += "Type: CSB (Scene/Node)\n"
        elif data[:4] == b'CCBA':
            info += "Type: Animation\n"

        with open(os.path.join(base, "cocos_info.txt"), 'w') as f:
            f.write(info)

        with open(os.path.join(base, "raw.bin"), 'wb') as f:
            f.write(data)

        print(f"  Cocos2d-x parsed: {magic}")
        return True
