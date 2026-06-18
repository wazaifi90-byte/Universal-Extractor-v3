class BaseEngine:
    name = "base"

    def identify(self, data, header_bytes):
        return False

    def extract(self, data, output_dir, filename):
        raise NotImplementedError

    def parse_header(self, data):
        raise NotImplementedError
