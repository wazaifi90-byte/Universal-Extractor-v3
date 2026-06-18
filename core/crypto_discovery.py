import numpy as np


class CryptoDiscovery:
    @staticmethod
    def find_xor_key_length(data_bytes, max_key_len=64):
        if len(data_bytes) < max_key_len * 2:
            return None
        arr = np.frombuffer(data_bytes[:8192], dtype=np.uint8)
        best_lag = 0
        max_corr = 0
        for lag in range(1, max_key_len + 1):
            corr = float(np.mean(arr[:-lag] == arr[lag:]))
            if corr > max_corr:
                max_corr = corr
                best_lag = lag
        return best_lag if max_corr > 0.08 else None

    @staticmethod
    def crack_xor_key(data_bytes, key_len):
        arr = np.frombuffer(data_bytes, dtype=np.uint8)
        key = []
        for i in range(key_len):
            nth_bytes = arr[i::key_len]
            most_common = int(np.bincount(nth_bytes).argmax())
            key.append(most_common)
        return bytes(key)

    @staticmethod
    def discover_and_decrypt(data_bytes):
        key_len = CryptoDiscovery.find_xor_key_length(data_bytes)
        if key_len:
            key = CryptoDiscovery.crack_xor_key(data_bytes, key_len)
            arr = np.frombuffer(data_bytes, dtype=np.uint8)
            key_arr = np.frombuffer(key * (len(data_bytes) // key_len + 1), dtype=np.uint8)[:len(data_bytes)]
            decrypted = np.bitwise_xor(arr, key_arr).tobytes()
            return decrypted, key
        return None, None

    @staticmethod
    def detect_encryption(data_bytes):
        if len(data_bytes) < 16:
            return None
        ent = _entropy_np(data_bytes[:1024])
        result = {"entropy": round(ent, 2)}
        if ent > 7.5:
            result["likely"] = "encrypted_or_compressed"
        elif ent > 6.0:
            result["likely"] = "possibly_encoded"
        else:
            result["likely"] = "raw_or_text"
        key_len = CryptoDiscovery.find_xor_key_length(data_bytes)
        if key_len:
            result["xor_detected"] = True
            result["key_length"] = key_len
            key = CryptoDiscovery.crack_xor_key(data_bytes[:4096], key_len)
            result["key_candidate"] = key.hex()
        else:
            result["xor_detected"] = False
        return result


def _entropy_np(data):
    if not data:
        return 0
    arr = np.frombuffer(data, dtype=np.uint8)
    counts = np.bincount(arr, minlength=256)
    probs = counts[counts > 0] / len(arr)
    return -float(np.sum(probs * np.log2(probs)))
