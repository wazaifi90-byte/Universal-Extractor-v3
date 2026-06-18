import os


WAV_HEADER_FMT = b'RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'


def _make_wav_header(data_size, sample_rate=22050, channels=1):
    hdr = bytearray(WAV_HEADER_FMT)
    data_size_bytes = (data_size).to_bytes(4, 'little')
    hdr[4:8] = (36 + data_size).to_bytes(4, 'little')
    hdr[24:28] = sample_rate.to_bytes(4, 'little')
    hdr[28:32] = (sample_rate * channels * 2).to_bytes(4, 'little')
    hdr[40:44] = data_size_bytes
    return bytes(hdr)


def raw_to_wav(data, output_dir, filename, sample_rate=22050, channels=1):
    out_path = os.path.join(output_dir, f"{filename}.wav")
    try:
        wav = _make_wav_header(len(data), sample_rate, channels) + data
        with open(out_path, 'wb') as f:
            f.write(wav)
        print(f"  WAV created -> {os.path.basename(out_path)} ({len(wav)} bytes)")
        return True
    except Exception as e:
        print(f"  WAV error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True


def msf_decode(data, output_dir, filename):
    import struct
    try:
        if len(data) < 8:
            raise ValueError("too small")
        magic, hdr_size = struct.unpack_from('<4sI', data)
        if magic != b'MSF\x00':
            raise ValueError(f"not MSF: {magic}")
        if len(data) < hdr_size + 8:
            raise ValueError(f"header says {hdr_size} but data too small")
        body = data[hdr_size:]
        return raw_to_wav(body, output_dir, filename)
    except Exception as e:
        print(f"  MSF error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True


def xma_to_wav(data, output_dir, filename):
    try:
        if len(data) < 8:
            raise ValueError("too small")
        body = data[8:] if data[:4] == b'XMA3' or data[:4] == b'XMA2' else data
        return raw_to_wav(body, output_dir, filename, sample_rate=44100, channels=2)
    except Exception as e:
        print(f"  XMA error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True


def genh_decode(data, output_dir, filename):
    try:
        if data[:4] != b'GENH':
            fallback = os.path.join(output_dir, filename)
            with open(fallback, 'wb') as f:
                f.write(data)
            return True
        body_start = int.from_bytes(data[4:8], 'little') + 8
        body = data[body_start:] if body_start < len(data) else data[8:]
        return raw_to_wav(body, output_dir, filename)
    except Exception as e:
        print(f"  GENH error: {e}")
        fallback = os.path.join(output_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        return True
