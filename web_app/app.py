import os
import sys
import json
import time
import threading
import glob
import functools
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file, Response, abort

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CUR_DIR)
sys.path.insert(0, ROOT_DIR)

from core.logger import Logger
from core.scanner import identify_file, list_signatures, _load_signatures
from registry import registry
from core.processor import process_file
from decoders.xor_decoder import set_key as set_xor_key
from ai.fingerprint import SmartClassifier, analyze_with_ai, _entropy
from core.virtual_fs import VirtualFS, UnityBundleFS, UnrealPakFS
from core.crypto_discovery import CryptoDiscovery
from core.conflict_manager import ConflictManager

app = Flask(__name__,
    static_folder=os.path.join(CUR_DIR, 'static'),
    static_url_path='/static')

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['SECRET_KEY'] = os.urandom(24).hex()

_config = None
_config_path = os.path.join(ROOT_DIR, "config.json")
_logger = None
_processing = False
_watch_thread = None
_watch_active = False

API_TOKENS = set()
_RATE_LIMIT = {}
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 30


def require_token(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token', request.args.get('token', ''))
        if API_TOKENS and token not in API_TOKENS:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def rate_limit(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or 'unknown'
        now = datetime.now()
        if ip in _RATE_LIMIT:
            count, window_start = _RATE_LIMIT[ip]
            if now - window_start > timedelta(seconds=_RATE_LIMIT_WINDOW):
                _RATE_LIMIT[ip] = (1, now)
            elif count >= _RATE_LIMIT_MAX:
                return jsonify({"error": "Rate limit exceeded"}), 429
            else:
                _RATE_LIMIT[ip] = (count + 1, window_start)
        else:
            _RATE_LIMIT[ip] = (1, now)
        return f(*args, **kwargs)
    return decorated


def validate_upload(file_storage):
    if not file_storage:
        return False, "No file"
    filename = file_storage.filename
    if not filename:
        return False, "Empty filename"
    safe = os.path.basename(filename)
    if safe != filename:
        return False, "Invalid path"
    allowed = {'.bin', '.dat', '.pak', '.unity3d', '.assets', '.uasset', '.uexp',
        '.cpk', '.afs', '.arc', '.pck', '.csb', '.lz4', '.zlib', '.gz', '.zip', '.zst',
        '.bz2', '.lzo', '.lzss', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tga', '.tiff',
        '.webp', '.dds', '.astc', '.ktx', '.gtf', '.pvr', '.etc1', '.bres', '.yaz0', '.yay0',
        '.psarc', '.xpr', '.ogg', '.wav', '.mp3', '.flac', '.xma', '.fsb', '.wem', '.bnk',
        '.bik', '.crx', '.rl7', '.pack', '.mvp', '.msf', '.genh', '.ico', '.pcx', '.riff',
        '.gltx', '.glsh', '.glpk', '.cry', '.vpk', '.bsp', '.rpa', '.rgss', '.rgd', '.model',
        '.cga', '.chr'}
    ext = os.path.splitext(safe)[1].lower()
    if ext not in allowed:
        return False, f"Extension {ext} not allowed"
    return True, safe


def _load_config():
    global _config
    if os.path.exists(_config_path):
        with open(_config_path) as f:
            _config = json.load(f)
    else:
        _config = {
            "active_mode": "auto",
            "paths": {"input_dir": "inputs", "output_dir": "outputs", "log_dir": "logs", "error_dir": "errors"},
            "settings": {
                "scan_interval_seconds": 2, "auto_delete_input": False,
                "process_subdirectories": True, "extract_nested": True,
                "xor_key": None, "stream_chunk_size": 1048576,
                "race_wait_seconds": 2, "enable_hashing": True, "enable_validation": True,
                "parallel": False, "max_workers": 4
            },
            "update": {"remote_url": None, "branch": "main", "auto_check": False},
            "language": "en", "auto_search_on_error": True,
            "search_sites": ["stackoverflow.com", "github.com", "reddit.com", "gamedev.net", "zenhax.com", "forum.xentax.com"]
        }


def _ensure_dirs():
    if not _config:
        return
    for key in ["input_dir", "output_dir", "log_dir", "error_dir"]:
        path = os.path.join(ROOT_DIR, _config["paths"][key])
        if not os.path.exists(path):
            os.makedirs(path)


_load_config()
_ensure_dirs()
_logger = Logger(os.path.join(ROOT_DIR, _config["paths"]["log_dir"]))


@app.route("/")
def index():
    return render_template("index.html", config=_config)


@app.route("/api/status")
def api_status():
    inputs = []
    in_dir = os.path.join(ROOT_DIR, _config["paths"]["input_dir"])
    if os.path.exists(in_dir):
        for fname in os.listdir(in_dir):
            fpath = os.path.join(in_dir, fname)
            if os.path.isfile(fpath):
                ft = identify_file(fpath)
                inputs.append({"name": fname, "size": os.path.getsize(fpath), "type": ft})
    outputs = []
    out_dir = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
    if os.path.exists(out_dir):
        for fname in os.listdir(out_dir):
            fpath = os.path.join(out_dir, fname)
            if os.path.isfile(fpath):
                outputs.append({"name": fname, "size": os.path.getsize(fpath)})
    sigs = list_signatures()
    return jsonify({
        "inputs": inputs,
        "outputs": outputs,
        "signatures": len(sigs),
        "decoders": len(registry.list_modes()),
        "processing": _processing,
        "watching": _watch_active,
        "input_dir": _config["paths"]["input_dir"],
        "output_dir": _config["paths"]["output_dir"]
    })


@app.route("/api/signatures")
def api_signatures():
    raw = _load_signatures()
    serializable = {}
    for ft, info in raw.items():
        serializable[ft] = {
            "magic": [' '.join(f'0x{b:02X}' for b in m) if isinstance(m, bytes) else str(m) for m in info.get("magics", [])],
            "extension": info.get("extension", ""),
            "engine": info.get("engine", "generic"),
            "sub_check": info.get("sub_check"),
        }
    return jsonify(serializable)


@app.route("/api/decoders")
def api_decoders():
    modes = registry.list_modes()
    result = []
    sigs = _load_signatures()
    for m in sorted(modes):
        engine = "generic"
        if m in sigs:
            engine = sigs[m].get("engine", "generic")
        elif any(m.startswith(p) for p in ["unity_", "unreal_", "cocos", "gameloft_", "konami_"]):
            engine = m.split("_")[0]
        result.append({"name": m, "engine": engine})
    return jsonify(result)


@app.route("/api/logs")
def api_logs():
    log_dir = os.path.join(ROOT_DIR, _config["paths"]["log_dir"])
    logs = []
    if os.path.exists(log_dir):
        for fname in sorted(os.listdir(log_dir), reverse=True)[:20]:
            fpath = os.path.join(log_dir, fname)
            if os.path.isfile(fpath):
                with open(fpath) as f:
                    content = f.read()
                logs.append({"file": fname, "content": content[:2000]})
    return jsonify(logs)


UPLOAD_ALLOWED_EXTENSIONS = {'.bin', '.dat', '.pak', '.unity3d', '.assets', '.uasset', '.uexp',
    '.cpk', '.afs', '.arc', '.pck', '.csb', '.lz4', '.zlib', '.gz', '.zip', '.zst',
    '.bz2', '.lzo', '.lzss', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tga', '.tiff',
    '.webp', '.dds', '.astc', '.ktx', '.gtf', '.pvr', '.etc1', '.bres', '.yaz0', '.yay0',
    '.psarc', '.xpr', '.ogg', '.wav', '.mp3', '.flac', '.xma', '.fsb', '.wem', '.bnk',
    '.bik', '.crx', '.rl7', '.pack', '.mvp', '.msf', '.genh', '.ico', '.pcx', '.riff',
    '.gltx', '.glsh', '.glpk', '.rl7', '.xpr0'}


@app.route("/api/upload", methods=["POST"])
@rate_limit
def api_upload():
    if _processing:
        return jsonify({"status": "error", "message": "Already processing"})
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file sent"})
    file = request.files['file']
    valid, result = validate_upload(file)
    if not valid:
        return jsonify({"status": "error", "message": result}), 400
    process_now = request.form.get('process', 'false') == 'true'
    save_to = request.form.get('save_to', 'default')
    in_dir = os.path.join(ROOT_DIR, _config["paths"]["input_dir"])
    os.makedirs(in_dir, exist_ok=True)
    safe_name = result
    save_path = os.path.join(in_dir, safe_name)
    file.save(save_path)
    ft = identify_file(save_path)
    result = {"file": safe_name, "size": os.path.getsize(save_path), "type": ft, "status": "uploaded"}
    result["save_to"] = save_to
    result["save_dir"] = ""
    if process_now:
        out_dir = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
        err_dir = os.path.join(ROOT_DIR, _config["paths"]["error_dir"])
        ok = process_file(save_path, ft, out_dir, err_dir, _config)
        result["status"] = "ok" if ok else "failed"
        if ok:
            target = _resolve_save_dir(save_to)
            # create subfolder with file name
            base_name = os.path.splitext(safe_name)[0]
            target_sub = os.path.join(target, base_name)
            os.makedirs(target_sub, exist_ok=True)
            _copy_outputs_to(out_dir, target_sub)
            result["save_dir"] = target_sub
        if _config.get("settings", {}).get("auto_delete_input"):
            try:
                os.remove(save_path)
            except:
                pass
    return jsonify(result)


@app.route("/api/process", methods=["POST"])
def api_process():
    global _processing
    if _processing:
        return jsonify({"status": "error", "message": "Already processing"})
    data = request.get_json() or {}
    files = data.get("files", [])
    save_to = data.get("save_to", "default")
    _processing = True
    try:
        in_dir = os.path.join(ROOT_DIR, _config["paths"]["input_dir"])
        out_dir = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
        err_dir = os.path.join(ROOT_DIR, _config["paths"]["error_dir"])
        target_base = _resolve_save_dir(save_to) if save_to != "default" else None
        results = []
        for fname in files:
            fpath = os.path.join(in_dir, fname)
            if not os.path.exists(fpath):
                results.append({"file": fname, "status": "not_found"})
                continue
            ft = identify_file(fpath)
            ok = process_file(fpath, ft, out_dir, err_dir, _config)
            save_dir = ""
            if ok and target_base:
                base_name = os.path.splitext(fname)[0]
                target_sub = os.path.join(target_base, base_name)
                os.makedirs(target_sub, exist_ok=True)
                _copy_outputs_to(out_dir, target_sub)
                save_dir = target_sub
            results.append({"file": fname, "type": ft, "status": "ok" if ok else "failed", "save_dir": save_dir})
        return jsonify({"status": "done", "results": results})
    finally:
        _processing = False


@app.route("/api/config", methods=["GET", "PUT"])
def api_config():
    global _config
    if request.method == "PUT":
        updates = request.get_json() or {}
        if "settings" in updates:
            _config["settings"].update(updates["settings"])
        if "paths" in updates:
            _config["paths"].update(updates["paths"])
        if "active_mode" in updates:
            _config["active_mode"] = updates["active_mode"]
        if "language" in updates:
            _config["language"] = updates["language"]
        with open(_config_path, "w") as f:
            json.dump(_config, f, indent=4)
        _ensure_dirs()
        xor_key = _config.get("settings", {}).get("xor_key")
        if xor_key is not None:
            set_xor_key(xor_key)
        return jsonify({"status": "saved", "config": _config})
    return jsonify(_config)


_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = SmartClassifier()
    return _classifier


@app.route("/api/ai-analyze", methods=["POST"])
@rate_limit
def api_ai_analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    data = file.read(4096)
    if not data:
        return jsonify({"error": "Empty file"}), 400
    clf = _get_classifier()
    label, confidence = clf.classify(data)
    ent = _entropy(data[:1024])
    null_ratio = round(data.count(0) / max(len(data), 1), 4)
    printable = sum(1 for b in data[:256] if 32 <= b <= 126) / max(len(data[:256]), 1)
    return jsonify({
        "label": label,
        "confidence": confidence,
        "entropy": round(ent, 2),
        "null_ratio": null_ratio,
        "printable_ratio": round(printable, 4),
        "size": len(data)
    })


@app.route("/api/crypto-analyze", methods=["POST"])
@rate_limit
def api_crypto_analyze():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    data = file.read(8192)
    if not data:
        return jsonify({"error": "Empty file"}), 400
    result = CryptoDiscovery.detect_encryption(data)
    decrypted, key = CryptoDiscovery.discover_and_decrypt(data)
    if key:
        result["key_hex"] = key.hex()
        result["key_length"] = len(key)
    else:
        result["key_hex"] = None
        result["key_length"] = 0
    return jsonify(result)


@app.route("/api/virtual/list", methods=["POST"])
@rate_limit
def api_virtual_list():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    data = file.read(65536)
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    if ext in ('.unity3d', '.assets'):
        vfs = UnityBundleFS(None)
    elif ext in ('.pak', '.uasset'):
        vfs = UnrealPakFS(None)
    else:
        vfs = VirtualFS(None)
    vfs.build_index(data)
    tree = vfs.get_directory_tree()
    return jsonify({"files": tree[:200], "total": len(tree)})


@app.route("/api/plugins")
def api_plugins():
    reg_path = os.path.join(ROOT_DIR, "plugins_registry.json")
    if os.path.exists(reg_path):
        with open(reg_path) as f:
            data = json.load(f)
        installed = _list_installed_plugins()
        for p in data.get("plugins", []):
            p["installed"] = p.get("id") + ".py" in installed
        return jsonify(data)
    return jsonify({"plugins": [], "version": "1.0"})


def _list_installed_plugins():
    plugins_dir = os.path.join(ROOT_DIR, "plugins")
    if not os.path.exists(plugins_dir):
        return set()
    return {f for f in os.listdir(plugins_dir) if f.endswith('.py') and f != '__init__.py'}


@app.route("/api/plugins/install", methods=["POST"])
def api_plugins_install():
    data = request.get_json() or {}
    plugin_id = data.get("id")
    if not plugin_id:
        return jsonify({"status": "error", "message": "No plugin ID"}), 400
    reg_path = os.path.join(ROOT_DIR, "plugins_registry.json")
    if not os.path.exists(reg_path):
        return jsonify({"status": "error", "message": "No registry"}), 400
    with open(reg_path) as f:
        reg = json.load(f)
    plugin = None
    for p in reg.get("plugins", []):
        if p["id"] == plugin_id:
            plugin = p
            break
    if not plugin:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
    url = plugin.get("repo", "")
    if not url:
        return jsonify({"status": "error", "message": "No download URL"}), 400
    try:
        import urllib.request
        resp = urllib.request.urlopen(url, timeout=30)
        if resp.getcode() != 200:
            return jsonify({"status": "error", "message": f"HTTP {resp.getcode()}"}), 502
        code = resp.read()
        plugins_dir = os.path.join(ROOT_DIR, "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        dest = os.path.join(plugins_dir, f"{plugin_id}.py")
        with open(dest, "wb") as f:
            f.write(code)
        _hot_reload_plugins()
        return jsonify({"status": "ok", "message": f"Installed {plugin['name']}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/plugins/uninstall", methods=["POST"])
def api_plugins_uninstall():
    data = request.get_json() or {}
    plugin_id = data.get("id")
    if not plugin_id:
        return jsonify({"status": "error", "message": "No plugin ID"}), 400
    dest = os.path.join(ROOT_DIR, "plugins", f"{plugin_id}.py")
    if os.path.exists(dest):
        os.remove(dest)
        _hot_reload_plugins()
        return jsonify({"status": "ok", "message": f"Uninstalled {plugin_id}"})
    return jsonify({"status": "error", "message": "Not installed"}), 404


def _hot_reload_plugins():
    try:
        from core.plugin_loader import load_plugins
        from registry import _decoders, _plugin_loaded
        _plugin_loaded = False
        class _FakeReg:
            def register_type(self, n, f): _decoders[n] = f
            def register_class(self, cls):
                if hasattr(cls, 'type_name'): _decoders[cls.type_name] = cls.extract
                elif hasattr(cls, 'extract'): _decoders[cls.__name__.lower()] = cls.extract
        loaded = load_plugins(_FakeReg())
        if loaded:
            print(f"  Hot-reloaded plugins: {', '.join(loaded)}")
    except Exception as e:
        print(f"  Hot-reload error: {e}")


@app.route("/api/check-update")
def api_check_update():
    try:
        import urllib.request
        import json
        remote = "https://api.github.com/repos/universal-extractor/universal-extractor/releases/latest"
        req = urllib.request.Request(remote, headers={"User-Agent": "Universal-Extractor/3.0", "Accept": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15)
        if resp.getcode() == 200:
            release = json.loads(resp.read())
            remote_ver = release.get("tag_name", "").lstrip("v")
            local_ver = "3.0.0"
            try:
                from pyproject import version as _v
                local_ver = _v
            except:
                try:
                    with open(os.path.join(ROOT_DIR, "pyproject.toml")) as f:
                        for line in f:
                            if line.strip().startswith("version"):
                                local_ver = line.split("=")[1].strip().strip('"').strip("'")
                                break
                except:
                    pass
            has_update = remote_ver != local_ver if remote_ver else False
            return jsonify({
                "has_update": has_update,
                "local_version": local_ver,
                "remote_version": remote_ver or "unknown",
                "release_url": release.get("html_url", ""),
                "release_body": (release.get("body") or "")[:500]
            })
        return jsonify({"has_update": False, "local_version": "3.0.0", "remote_version": "", "release_url": ""})
    except Exception as e:
        return jsonify({"has_update": False, "error": str(e)})


@app.route("/api/stats")
def api_stats():
    try:
        from core.database import get_stats, init_db
        init_db()
        return jsonify(get_stats())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/errors")
def api_errors():
    err_dir = os.path.join(ROOT_DIR, _config["paths"]["error_dir"])
    errors = []
    if os.path.exists(err_dir):
        for fname in sorted(os.listdir(err_dir), reverse=True)[:50]:
            fpath = os.path.join(err_dir, fname)
            if os.path.isfile(fpath):
                errors.append({"file": fname, "size": os.path.getsize(fpath)})
    return jsonify(errors)


@app.route("/api/download/<path:filename>")
def api_download(filename):
    out_dir = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
    fpath = os.path.join(out_dir, filename)
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return jsonify({"error": "not found"}), 404


@app.route("/api/watch", methods=["POST"])
def api_watch():
    global _watch_active, _watch_thread
    data = request.get_json() or {}
    action = data.get("action", "stop")
    if action == "start" and not _watch_active:
        _watch_active = True
        _watch_thread = threading.Thread(target=_watch_loop, daemon=True)
        _watch_thread.start()
        return jsonify({"status": "watching"})
    _watch_active = False
    return jsonify({"status": "stopped"})


def _watch_loop():
    global _processing
    interval = _config.get("settings", {}).get("scan_interval_seconds", 2)
    in_dir = os.path.join(ROOT_DIR, _config["paths"]["input_dir"])
    out_dir = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
    err_dir = os.path.join(ROOT_DIR, _config["paths"]["error_dir"])
    while _watch_active:
        if os.path.exists(in_dir):
            for fname in os.listdir(in_dir):
                if not _watch_active:
                    return
                fpath = os.path.join(in_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                _processing = True
                ft = identify_file(fpath)
                process_file(fpath, ft, out_dir, err_dir, _config)
                _processing = False
                if _config.get("settings", {}).get("auto_delete_input"):
                    try:
                        os.remove(fpath)
                    except:
                        pass
        time.sleep(interval)


DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
DEFAULT_SAVE_DIR = os.path.join(DESKTOP, "Extracted")


def _resolve_save_dir(save_to):
    if not save_to or save_to == "default":
        return os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
    if save_to == "desktop":
        path = DEFAULT_SAVE_DIR
    elif save_to.startswith("desktop:"):
        sub = save_to.split(":", 1)[1].strip("/\\")
        path = os.path.join(DESKTOP, sub) if sub else DEFAULT_SAVE_DIR
    else:
        path = save_to
    if not os.path.isabs(path):
        path = os.path.join(DESKTOP, path)
    os.makedirs(path, exist_ok=True)
    return path


def _copy_outputs_to(src_dir, dst_dir, filename_hint=""):
    if src_dir == dst_dir:
        return dst_dir
    if not os.path.exists(src_dir):
        return dst_dir
    count = 0
    for fname in os.listdir(src_dir):
        fpath = os.path.join(src_dir, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
            dst = os.path.join(dst_dir, fname)
            try:
                import shutil
                shutil.copy2(fpath, dst)
                count += 1
            except:
                pass
    return dst_dir


@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    data = request.get_json() or {}
    folder = data.get("folder", "")
    if not folder:
        folder = os.path.join(ROOT_DIR, _config["paths"]["output_dir"])
    elif folder == "desktop":
        folder = DEFAULT_SAVE_DIR
    elif folder.startswith("desktop:"):
        sub = folder.split(":", 1)[1].strip("/\\")
        folder = os.path.join(DESKTOP, sub) if sub else DEFAULT_SAVE_DIR
    elif not os.path.isabs(folder):
        folder = os.path.join(ROOT_DIR, folder)
    if os.path.exists(folder):
        try:
            os.startfile(folder)
            return jsonify({"status": "opened", "folder": folder})
        except:
            pass
    return jsonify({"status": "error", "folder": folder})


@app.route("/api/languages")
def api_languages():
    from core.i18n import available_languages, current_lang
    return jsonify({"languages": available_languages(), "current": current_lang()})

@app.route("/api/language/set", methods=["POST"])
def api_language_set():
    data = request.get_json() or {}
    code = data.get("code", "en")
    from core.i18n import load_language, t
    ok = load_language(code)
    if not ok:
        return jsonify({"status": "error", "message": f"Language '{code}' not found"}), 400
    resp = jsonify({"status": "ok", "lang": code, "message": t("language_switched", code)})
    resp.set_cookie("lang", code, max_age=365*24*3600)
    return resp

def run_web(host="127.0.0.1", port=5000, debug=False):
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    print(f"Web Dashboard: http://{host}:{port}")
    run_web(host, port)
