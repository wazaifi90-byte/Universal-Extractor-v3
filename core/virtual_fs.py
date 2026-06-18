import os
import base64
import io


class VirtualFS:
    def __init__(self, archive_path):
        self.archive_path = archive_path
        self.file_map = {}

    def register_file(self, name, offset, size, file_type=None):
        self.file_map[name] = {
            'offset': offset,
            'size': size,
            'type': file_type or name.split('.')[-1]
        }

    def get_directory_tree(self):
        return list(self.file_map.keys())

    def preview_file(self, filename):
        if filename not in self.file_map:
            return None
        info = self.file_map[filename]
        try:
            with open(self.archive_path, 'rb') as f:
                f.seek(info['offset'])
                data = f.read(info['size'])
                b64 = base64.b64encode(data).decode('utf-8')
                mime = self._mime(info['type'])
                return f"data:{mime};base64,{b64}"
        except Exception as e:
            return None

    def _mime(self, ext):
        types = {
            'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'gif': 'image/gif', 'webp': 'image/webp', 'dds': 'image/dds',
            'bmp': 'image/bmp', 'tga': 'image/tga', 'tiff': 'image/tiff',
            'ogg': 'audio/ogg', 'wav': 'audio/wav', 'mp3': 'audio/mpeg',
            'txt': 'text/plain', 'json': 'application/json', 'xml': 'application/xml',
            'log': 'text/plain', 'html': 'text/html', 'css': 'text/css',
            'js': 'application/javascript', 'bin': 'application/octet-stream'
        }
        return types.get(ext.lower(), 'application/octet-stream')


class UnityBundleFS(VirtualFS):
    def build_index(self, data_bytes):
        idx = 0
        while idx < len(data_bytes) - 32:
            name_len = int.from_bytes(data_bytes[idx:idx+4], 'little')
            if name_len <= 0 or name_len > 256 or idx + name_len > len(data_bytes):
                break
            name = data_bytes[idx+4:idx+4+name_len].decode('utf-8', errors='replace').strip('\x00')
            offset = int.from_bytes(data_bytes[idx+4+name_len:idx+8+name_len], 'little')
            size = int.from_bytes(data_bytes[idx+8+name_len:idx+12+name_len], 'little')
            if size > 0:
                self.register_file(name, offset, size)
            idx += 12 + name_len + 8


class UnrealPakFS(VirtualFS):
    def build_index(self, data_bytes):
        idx = 0
        while idx < len(data_bytes) - 16:
            size = int.from_bytes(data_bytes[idx:idx+4], 'little')
            offset = int.from_bytes(data_bytes[idx+4:idx+8], 'little')
            name_end = data_bytes.find(b'\x00', idx+8)
            if name_end == -1 or name_end > idx + 200:
                break
            name = data_bytes[idx+8:name_end].decode('utf-8', errors='replace')
            if size > 0:
                self.register_file(name, offset, size)
            idx = name_end + 1
