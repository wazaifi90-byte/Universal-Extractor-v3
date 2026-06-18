import os


class ConflictManager:
    @staticmethod
    def get_unique_path(target_path, mode='rename'):
        if not os.path.exists(target_path) or mode == 'overwrite':
            return target_path
        if mode == 'skip':
            return None
        base, ext = os.path.splitext(target_path)
        counter = 1
        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    @staticmethod
    def safe_write(data, output_dir, filename, mode='rename'):
        target = os.path.join(output_dir, filename)
        final_path = ConflictManager.get_unique_path(target, mode)
        if final_path:
            with open(final_path, 'wb') as f:
                f.write(data)
            return final_path
        return None
