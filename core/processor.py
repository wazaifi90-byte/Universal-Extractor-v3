import os
import json
import tempfile
import shutil
import uuid
import urllib.parse
import webbrowser
import time
from registry import registry
from core.scanner import identify_bytes
from core.validator import hash_file, validate_file
from core.i18n import t
from core.database import init_db, log_operation, update_signature, get_summary

MAX_CHAIN_DEPTH = 5

VALIDATABLE_TYPES = {"png", "jpeg", "gif", "bmp", "tga", "dds", "webp", "ogg", "wav"}


class ChainSession:
    def __init__(self, base_output_dir):
        self.session_id = uuid.uuid4().hex[:8]
        self.temp_dir = os.path.join(tempfile.gettempdir(), f"uextract_{self.session_id}")
        self.final_dir = base_output_dir
        self.before_files = set()

    def __enter__(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        self.before_files = self._files()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _files(self):
        if not os.path.exists(self.temp_dir):
            return set()
        return set(os.listdir(self.temp_dir))

    def new_files(self):
        return self._files() - self.before_files


_db_inited = False


def _ensure_db():
    global _db_inited
    if not _db_inited:
        try:
            init_db()
            _db_inited = True
        except:
            pass


def process_file(file_path, file_type, output_dir, error_dir, config=None):
    _ensure_db()
    filename = os.path.basename(file_path)
    enable_hash = True
    enable_val = True
    if config:
        s = config.get("settings", {})
        enable_hash = s.get("enable_hashing", True)
        enable_val = s.get("enable_validation", True)

    start_time = time.time()
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    ok = False
    reason = None

    try:
        before_final = _list_files(output_dir)
        with open(file_path, 'rb') as f:
            data = f.read()

        with ChainSession(output_dir) as session:
            ok = _run_pipeline(data, file_type, filename, session, 0, output_dir, error_dir, config)
            if ok:
                _flush_temp(session, output_dir)

        if ok:
            new_files = _list_files(output_dir) - before_final
            _finalize_outputs(new_files, file_type, filename, output_dir, enable_hash, enable_val)
            duration = int((time.time() - start_time) * 1000)
            try:
                log_operation(filename, file_type, file_size, "success", duration_ms=duration)
            except:
                pass
            return True
        return False

    except Exception as e:
        reason = str(e)
        print(f"  Error: {reason}")
        _write_error_log(error_dir, filename, reason)
        _move_to_error(file_path, error_dir, filename)
        if _should_search(config):
            _web_search_error(filename, file_type, reason, config)
        duration = int((time.time() - start_time) * 1000)
        try:
            log_operation(filename, file_type, file_size, "failed", error_message=reason, duration_ms=duration)
        except:
            pass
        return False

    except Exception as e:
        reason = str(e)
        print(f"  Error processing embedded data: {reason}")
        if _should_search(config):
            _web_search_error(filename, file_type, reason, config)
        return False


def _run_pipeline(data, file_type, filename, session, depth, output_dir, error_dir, config):
    if depth > MAX_CHAIN_DEPTH:
        fallback = os.path.join(session.temp_dir, f"{filename}.depth{MAX_CHAIN_DEPTH}")
        with open(fallback, 'wb') as f:
            f.write(data)
        return True

    decoder = registry.get(file_type)
    if not decoder:
        reason = f"No decoder: {file_type}"
        _write_error_log(error_dir, filename, reason)
        _move_to_error(None, error_dir, filename, data)
        if _should_search(config):
            _web_search_error(filename, file_type, reason, config)
        return False

    if depth > 0:
        indent = "  " * depth
        print(f"{indent}[chain d={depth}] {filename} ({file_type})")

    input_hash = _quick_hash(data)

    decoder(data, session.temp_dir, filename)

    new_files = session.new_files()
    if not new_files and data:
        fallback = os.path.join(session.temp_dir, filename)
        with open(fallback, 'wb') as f:
            f.write(data)
        new_files = session.new_files()

    for fname in new_files:
        fpath = os.path.join(session.temp_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) == 0:
            continue

        with open(fpath, 'rb') as f:
            chunk = f.read(16)
        new_type = identify_bytes(chunk)

        output_hash = _quick_hash_file(fpath)

        h_status = ""
        try:
            if input_hash and output_hash and input_hash != output_hash and depth > 0:
                h_status = f" [hash mismatch: {input_hash[:8]} != {output_hash[:8]}]"
        except:
            pass

        if new_type and new_type != file_type and new_type != "unknown":
            with open(fpath, 'rb') as f:
                new_data = f.read()
            if depth == 0:
                print(f"  -> chain: {file_type} -> {new_type}")
            _run_pipeline(new_data, new_type, fname, session, depth + 1,
                          output_dir, error_dir, config)
        elif new_type in VALIDATABLE_TYPES:
            valid, msg = _validate_final(fpath, new_type, file_type, h_status)
            if not valid and valid is not None:
                reason = f"Validation failed: {msg}"
                _write_error_log(error_dir, fname, reason)
                _move_to_error(None, error_dir, f"corrupt_{fname}", open(fpath, 'rb').read())
                os.remove(fpath)
                print(f"  CORRUPT: {fname} -> {msg}")
                if _should_search(config):
                    _web_search_error(fname, new_type, msg, config)
                return False

    return True


def _flush_temp(session, output_dir):
    if not os.path.exists(session.temp_dir):
        return
    for fname in os.listdir(session.temp_dir):
        src = os.path.join(session.temp_dir, fname)
        if os.path.isfile(src) and os.path.getsize(src) > 0:
            dst = os.path.join(output_dir, fname)
            try:
                shutil.copy2(src, dst)
            except:
                pass


def _list_files(directory):
    if not os.path.exists(directory):
        return set()
    return set(os.listdir(directory))


def _finalize_outputs(new_files, file_type, orig_name, output_dir, enable_hash, enable_val):
    for fname in sorted(new_files):
        fpath = os.path.join(output_dir, fname)
        if not os.path.exists(fpath) or os.path.getsize(fpath) == 0:
            continue
        hash_val = None
        if enable_hash:
            hash_val = hash_file(fpath)
        valid = None
        valid_msg = "no check"
        if enable_val:
            valid, valid_msg = validate_file(fpath, file_type)
        parts = []
        if hash_val:
            parts.append(f"hash={hash_val[:12]}..")
        if valid is True:
            parts.append("OK")
        elif valid is False:
            parts.append(f"CORRUPT: {valid_msg}")
        if parts:
            print(f"  {fname}: [{' | '.join(parts)}]")


def _should_search(config):
    if config is None:
        return False
    return config.get("auto_search_on_error", False)


def _get_search_sites(config):
    if config is None:
        return []
    return config.get("search_sites", [])


def _web_search_error(filename, file_type, reason, config=None):
    sites = _get_search_sites(config)
    core_query = f"{file_type} {filename} decode error {reason}"

    if sites:
        site_filters = " OR ".join(f"site:{s}" for s in sites)
        query = f"({core_query}) ({site_filters})"
    else:
        query = core_query

    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    print(f"  Searching developer sites for solutions...")
    try:
        webbrowser.open(url)
    except:
        pass
    print(f"  Open: {url}")


def _write_error_log(error_dir, filename, reason):
    log_path = os.path.join(error_dir, f"{filename}.error.json")
    try:
        with open(log_path, 'w') as f:
            json.dump({"file": filename, "error": reason}, f, indent=2)
    except:
        pass


def _move_to_error(file_path, error_dir, filename, data=None):
    dst = os.path.join(error_dir, filename)
    if data is not None:
        with open(dst, 'wb') as f:
            f.write(data)
    elif file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as src, open(dst, 'wb') as f:
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                f.write(chunk)


def _quick_hash(data):
    try:
        import xxhash
        return xxhash.xxh64(data).hexdigest()
    except:
        try:
            import hashlib
            return hashlib.md5(data).hexdigest()
        except:
            return None


def _quick_hash_file(fpath):
    try:
        import xxhash
        h = xxhash.xxh64()
        with open(fpath, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except:
        try:
            import hashlib
            h = hashlib.md5()
            with open(fpath, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except:
            return None


def _validate_final(fpath, new_type, file_type, h_status=""):
    if new_type in VALIDATABLE_TYPES:
        from core.validator import validate_file
        return validate_file(fpath, new_type)
    return None, "no check"
