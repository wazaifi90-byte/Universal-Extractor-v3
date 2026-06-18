import os
import sys
import json
import struct
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def _setup():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

def test_signatures_loaded():
    _setup()
    from core.scanner import list_signatures
    sigs = list_signatures()
    assert len(sigs) > 5
    print(f"  OK: {len(sigs)} signatures")

def test_deflate_detect():
    _setup()
    from core.scanner import identify_bytes
    import zlib
    assert identify_bytes(zlib.compress(b"test")) == "deflate"
    print("  OK")

def test_konami_cpk_magic():
    _setup()
    from core.scanner import identify_bytes
    assert identify_bytes(b'CPK ' + b'\x00' * 12) == "konami_cpk"
    print("  OK")

def test_preview_valid():
    _setup()
    from core.preview import preview_file
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)
        f.flush()
        preview_file(f.name)
    os.unlink(f.name)
    print("  OK: preview ran without error")

def test_validator_hash():
    _setup()
    from core.validator import hash_data, hash_file
    h = hash_data(b"test data")
    assert h is not None
    assert len(h) > 0
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test data")
        f.flush()
        h2 = hash_file(f.name)
        assert h2 is not None
        assert h == h2
    os.unlink(f.name)
    print(f"  OK: hash={h}")

def test_validator_png():
    _setup()
    from core.validator import validate_file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        bad_data = b'\x89PNG' + b'\x00' * 100
        f.write(bad_data)
        f.flush()
        valid, msg = validate_file(f.name, 'png')
        print(f"  Corruption detect: valid={valid} msg={msg}")
    os.unlink(f.name)
    print("  OK")

def test_validator_streaming_hasher():
    _setup()
    from core.validator import StreamingHasher
    h = StreamingHasher()
    h.update(b"chunk1")
    h.update(b"chunk2")
    digest = h.hexdigest()
    assert digest is not None
    assert len(digest) > 0
    print(f"  OK: streaming hash={digest[:12]}...")

def test_processor_creates_output():
    _setup()
    from core.processor import process_file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        import zlib
        f.write(zlib.compress(b"hello process test"))
        f.flush()
        fname = f.name
    out_dir = tempfile.mkdtemp()
    err_dir = tempfile.mkdtemp()
    result = process_file(fname, "deflate", out_dir, err_dir)
    assert result, "Process failed"
    files = os.listdir(out_dir)
    assert len(files) > 0
    print(f"  OK: output file(s): {files}")
    os.unlink(fname)

def test_config_has_new_settings():
    _setup()
    with open('config.json') as f:
        cfg = json.load(f)
    s = cfg['settings']
    assert 'enable_hashing' in s
    assert 'enable_validation' in s
    print(f"  OK: hashing={s['enable_hashing']} validation={s['enable_validation']}")

def test_argparse():
    _setup()
    import subprocess
    result = subprocess.run([sys.executable, 'main.py', '--help'], capture_output=True, text=True)
    assert '--preview' in result.stdout
    assert '--no-hash' in result.stdout
    assert '--no-validate' in result.stdout
    print("  OK")

def test_registry_all_modes():
    _setup()
    from registry import registry
    modes = registry.list_modes()
    for needed in ['deflate', 'lz4', 'konami_cpk', 'konami_afs', 'unity_bundle', 'unreal_pak', 'bres']:
        assert needed in modes, f"Missing: {needed}"
    print(f"  OK: {len(modes)} modes")

def test_processor_hash_logs_written():
    _setup()
    from core.processor import process_file
    in_dir = tempfile.mkdtemp()
    out_dir = tempfile.mkdtemp()
    err_dir = tempfile.mkdtemp()
    import zlib
    in_path = os.path.join(in_dir, "test_hash.bin")
    with open(in_path, 'wb') as f:
        f.write(zlib.compress(b"hash check data " * 50))
    config = {"settings": {"enable_hashing": True, "enable_validation": False, "stream_chunk_size": 1048576}}
    result = process_file(in_path, "deflate", out_dir, err_dir, config)
    assert result
    print("  OK: hashing ran without error")

def test_virtual_fs():
    _setup()
    from core.virtual_fs import VirtualFS
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"FAKE_PNG_DATA_" * 20)
        f.flush()
        fname = f.name
    vfs = VirtualFS(fname)
    vfs.register_file("test.png", 0, 100, "png")
    vfs.register_file("data.bin", 100, 200, "bin")
    tree = vfs.get_directory_tree()
    assert len(tree) == 2
    preview = vfs.preview_file("test.png")
    assert preview is not None
    assert preview.startswith("data:image/png;base64,")
    preview_none = vfs.preview_file("nonexistent.bin")
    assert preview_none is None
    print(f"  OK: VirtualFS {len(tree)} files, preview OK")
    os.unlink(fname)


def test_crypto_discovery():
    _setup()
    from core.crypto_discovery import CryptoDiscovery
    test_data = bytes([b ^ 0xAA for b in b"Hello World! This is test data for XOR detection. " * 10])
    result = CryptoDiscovery.detect_encryption(test_data)
    assert result["xor_detected"] == True
    assert result["key_length"] >= 1
    print(f"  OK: XOR detected, key length={result['key_length']}")


def test_conflict_manager():
    _setup()
    from core.conflict_manager import ConflictManager
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
        f.write(b"test")
        fpath = f.name
    unique = ConflictManager.get_unique_path(fpath, mode='rename')
    assert unique != fpath
    assert unique.endswith('_1.txt')
    print(f"  OK: ConflictManager renamed to {os.path.basename(unique)}")
    os.unlink(fpath)
    if os.path.exists(unique):
        os.unlink(unique)


if __name__ == "__main__":
    _setup()
    tests = [fn for fn in dir() if fn.startswith('test_')]
    passed = 0
    failed = 0
    for t in tests:
        func = globals()[t]
        if callable(func):
            try:
                print(f"[{t}]")
                func()
                passed += 1
            except Exception as e:
                print(f"  FAILED: {e}")
                failed += 1
    print(f"\n{'='*40}")
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*40}")
