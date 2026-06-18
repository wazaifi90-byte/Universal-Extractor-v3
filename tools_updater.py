import os
import sys
import subprocess
import json
import shutil
import tempfile
import zipfile
from datetime import datetime

TOOLS = ["rich", "lz4", "Pillow", "xxhash"]
PLUGINS_DIR = "plugins"
BACKUP_DIR = "backup_tools"
VERSION_FILE = "tools_version.json"
CONFIG_FILE = "config.json"
MANIFEST_FILE = "updates.json"

LANG_DIR = "lang"

REMOTE_FILES = {
    "signatures.json": "signatures.json",
    "config.json": "config.json",
    "decoders": "decoders/",
    "plugins": "plugins/",
    "core": "core/",
    "engines": "engines/",
    "lang": "lang/",
    "main.py": "main.py",
    "registry.py": "registry.py",
}


def _load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except:
        return {}


def _get_remote_url():
    cfg = _load_config()
    return cfg.get("update", {}).get("remote_url") or os.environ.get("UEXTRACT_REMOTE_URL")


def _http_get(url, timeout=30):
    try:
        import urllib.request
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.read(), r.getcode()
    except:
        return None, None


def _fetch_json(url):
    data, code = _http_get(url)
    if code == 200 and data:
        try:
            return json.loads(data.decode("utf-8")), code
        except:
            return None, code
    return None, code


MENU_OPTIONS = [
    ("1", "Check installed tools", "cmd_check", []),
    ("2", "Install/upgrade tools (rich, lz4, Pillow, xxhash)", "cmd_install", ["all"]),
    ("3", "Update all tools via pip", "cmd_update", []),
    ("4", "Show tool versions", "cmd_status", []),
    ("5", "Backup project files", "cmd_backup", []),
    ("6", "Restore from backup", "cmd_restore", []),
    ("7", "Full self-check", "cmd_self_check", []),
    ("8", "Set remote update URL", "cmd_set_remote_interactive", []),
    ("9", "Check remote for updates", "cmd_check_remote", []),
    ("10", "Fetch & apply remote updates", "cmd_fetch", []),
    ("11", "Download & extract update ZIP", "cmd_fetch_zip", []),
    ("12", "Switch language", "cmd_lang_interactive", []),
    ("0", "Exit", None, []),
]


def _run_pip(args):
    cmd = [sys.executable, "-m", "pip"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.returncode == 0, r.stdout + r.stderr
    except Exception as e:
        return False, str(e)


def cmd_check(args):
    missing = []
    for t in TOOLS:
        try:
            __import__(t.replace("-", "_"))
            print(f"  {t}: installed")
        except ImportError:
            print(f"  {t}: MISSING")
            missing.append(t)
    if not missing:
        print("  All optional tools are installed.")
    return missing


def cmd_install(args):
    target = args[0] if args else TOOLS
    if target == ["all"]:
        target = TOOLS
    ok, out = _run_pip(["install", "--upgrade"] + target)
    if ok:
        print(f"  Installed/upgraded: {', '.join(target)}")
    else:
        print(f"  pip failed:\n{out}")
    _save_version(target)
    return ok


def cmd_update(args):
    ok, out = _run_pip(["install", "--upgrade"] + TOOLS)
    if ok:
        print(f"  Updated: {', '.join(TOOLS)}")
    else:
        print(f"  pip failed:\n{out}")
    _save_version(TOOLS)
    return ok


def cmd_status(args):
    for t in TOOLS:
        try:
            mod = __import__(t.replace("-", "_"))
            ver = getattr(mod, "__version__", "?")
            print(f"  {t}: {ver}")
        except ImportError:
            print(f"  {t}: not installed")


def cmd_backup(args):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for root, dirs, files in os.walk("."):
        rel = os.path.relpath(root, ".")
        if rel.startswith(BACKUP_DIR) or rel.startswith("__pycache__") or rel.startswith("."):
            continue
        for f in files:
            if f.endswith((".py", ".json", ".md")):
                src = os.path.join(root, f)
                dst_rel = os.path.relpath(src, ".")
                dst = os.path.join(BACKUP_DIR, dst_rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
    print(f"  Backed up to {BACKUP_DIR}/")
    return True


def cmd_restore(args):
    if not os.path.exists(BACKUP_DIR):
        print("  No backup found.")
        return False
    count = 0
    for root, dirs, files in os.walk(BACKUP_DIR):
        for f in files:
            src = os.path.join(root, f)
            rel = os.path.relpath(src, BACKUP_DIR)
            dst = os.path.join(".", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    print(f"  Restored {count} files from {BACKUP_DIR}/")
    return True


def cmd_self_check(args):
    print("  Python:", sys.version.split()[0])
    print(f"  Platform: {sys.platform}")
    print(f"  Project: {os.path.abspath('.')}")
    url = _get_remote_url()
    if url:
        print(f"  Remote: {url}")
    else:
        print("  Remote: not configured (set update.remote_url in config.json)")
    missing = cmd_check(args)
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:
            v = json.load(f)
        print(f"  Last update: {v.get('updated', 'never')}")
    if missing:
        print(f"  Run: python tools_updater.py install {' '.join(missing)}")
    return True


def cmd_fetch(args):
    url = _get_remote_url()
    if not url:
        print("  No remote URL configured.")
        print("  Set update.remote_url in config.json or UEXTRACT_REMOTE_URL env var.")
        return False

    manifest_url = url.rstrip("/") + "/" + MANIFEST_FILE
    print(f"  Fetching manifest: {manifest_url}")

    manifest, code = _fetch_json(manifest_url)
    if not manifest:
        print(f"  Failed to fetch manifest (HTTP {code})")
        print("  Expected URL to point to a directory containing updates.json")
        return False

    files = manifest.get("files", {})
    if not files:
        print("  Manifest is empty or malformed.")
        return False

    print(f"  Found {len(files)} remote file(s)")
    downloaded = 0
    skipped = 0
    errors = 0

    local_ver = _load_local_versions()

    for rel_path, info in files.items():
        dest = rel_path.replace("/", os.sep)
        parent = os.path.dirname(dest) or "."
        os.makedirs(parent, exist_ok=True)

        remote_ver = info.get("version", info.get("hash", ""))
        local_v = local_ver.get(rel_path)
        if local_v and local_v == remote_ver:
            skipped += 1
            continue

        file_url = url.rstrip("/") + "/" + rel_path.replace(os.sep, "/")
        print(f"    Downloading {rel_path}...", end="")
        data, code = _http_get(file_url)
        if code != 200 or not data:
            print(f" FAILED (HTTP {code})")
            errors += 1
            continue

        with open(dest, "wb") as f:
            f.write(data)
        print(f" OK")
        local_ver[rel_path] = remote_ver
        downloaded += 1

    _save_local_versions(local_ver)
    print(f"  Done: {downloaded} downloaded, {skipped} up-to-date, {errors} errors")
    return errors == 0


def cmd_check_remote(args):
    url = _get_remote_url()
    if not url:
        print("  No remote URL configured.")
        return False

    manifest_url = url.rstrip("/") + "/" + MANIFEST_FILE
    print(f"  Checking remote: {manifest_url}")
    manifest, code = _fetch_json(manifest_url)
    if not manifest:
        print(f"  Failed to fetch manifest (HTTP {code})")
        return False

    files = manifest.get("files", {})
    if not files:
        print("  Remote manifest is empty.")
        return False

    local_ver = _load_local_versions()
    outdated = []
    new = []
    for rel_path, info in files.items():
        remote_ver = info.get("version", info.get("hash", ""))
        local_v = local_ver.get(rel_path)
        if not local_v:
            new.append(rel_path)
        elif local_v != remote_ver:
            outdated.append((rel_path, local_v, remote_ver))

    if new:
        print(f"  New files ({len(new)}):")
        for f in new:
            print(f"    + {f}")
    if outdated:
        print(f"  Updates available ({len(outdated)}):")
        for f, old_v, new_v in outdated:
            print(f"    ~ {f}  ({old_v} -> {new_v})")
    if not new and not outdated:
        print("  All files up-to-date.")
    return True


def cmd_lang(args):
    langs = []
    if os.path.exists(LANG_DIR):
        for f in os.listdir(LANG_DIR):
            if f.endswith(".json"):
                code = f[:-5]
                try:
                    with open(os.path.join(LANG_DIR, f)) as lf:
                        data = json.load(lf)
                    name = data.get("lang_name", code)
                except:
                    name = code
                langs.append((code, name))

    if not args:
        current = _load_config().get("language", "en")
        print(f"  Current language: {current}")
        print(f"  Available languages ({len(langs)}):")
        for code, name in langs:
            mark = " <--" if code == current else ""
            print(f"    {code}  {name}{mark}")
        print(f"  Usage: python tools_updater.py lang <code>")
        return True

    target = args[0]
    codes = [c for c, n in langs]
    if target not in codes:
        print(f"  Language '{target}' not found. Available: {', '.join(codes)}")
        return False

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
    except:
        cfg = {}
    cfg["language"] = target
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)
    print(f"  Language switched to '{target}'")
    return True


def cmd_set_remote(args):
    if not args:
        print("  Usage: python tools_updater.py set-remote <URL>")
        return False
    new_url = args[0]
    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
    except:
        cfg = {}
    if "update" not in cfg:
        cfg["update"] = {}
    cfg["update"]["remote_url"] = new_url
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)
    print(f"  Remote URL set to: {new_url}")
    return True


def cmd_fetch_zip(args):
    url = _get_remote_url()
    if not url:
        print("  No remote URL configured.")
        return False

    zip_url = url.rstrip("/") + "/" + (args[0] if args else "update.zip")
    print(f"  Downloading {zip_url}...")
    data, code = _http_get(zip_url)
    if code != 200 or not data:
        print(f"  Failed (HTTP {code})")
        return False

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        tmp.write(data)
        tmp.close()
        with zipfile.ZipFile(tmp.name, "r") as z:
            z.extractall(".")
        print(f"  Extracted {len(zipfile.ZipFile(tmp.name, 'r').namelist())} files")
    except Exception as e:
        print(f"  Error extracting zip: {e}")
        return False
    finally:
        os.unlink(tmp.name)
    return True


def _load_local_versions():
    try:
        with open(VERSION_FILE) as f:
            data = json.load(f)
        return data.get("files", {})
    except:
        return {}


def _save_local_versions(files):
    data = {
        "updated": datetime.now().isoformat(),
        "python": sys.version.split()[0],
        "files": files
    }
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE) as f:
                old = json.load(f)
            data["tools"] = old.get("tools", {})
        except:
            pass
    with open(VERSION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _save_version(tools):
    versions = {}
    for t in tools:
        try:
            mod = __import__(t.replace("-", "_"))
            versions[t] = getattr(mod, "__version__", "?")
        except ImportError:
            versions[t] = None
    data = {}
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE) as f:
                data = json.load(f)
        except:
            pass
    data["updated"] = datetime.now().isoformat()
    data["python"] = sys.version.split()[0]
    data["tools"] = versions
    with open(VERSION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _run_cmd(name, args_list):
    fn = {
        "cmd_check": cmd_check,
        "cmd_install": cmd_install,
        "cmd_update": cmd_update,
        "cmd_status": cmd_status,
        "cmd_backup": cmd_backup,
        "cmd_restore": cmd_restore,
        "cmd_self_check": cmd_self_check,
        "cmd_set_remote": cmd_set_remote,
        "cmd_set_remote_interactive": cmd_set_remote_interactive,
        "cmd_check_remote": cmd_check_remote,
        "cmd_fetch": cmd_fetch,
        "cmd_fetch_zip": cmd_fetch_zip,
        "cmd_lang": cmd_lang,
        "cmd_lang_interactive": cmd_lang_interactive,
    }.get(name)
    if fn:
        fn(args_list)


def cmd_menu(args):
    while True:
        print()
        print("=" * 54)
        print("  Universal Extractor – Update Manager")
        print("=" * 54)
        for key, label, fn, _ in MENU_OPTIONS:
            print(f"  [{key}] {label}")
        print("-" * 54)
        choice = input("  Choose an option (0-12): ").strip()

        if choice == "0":
            print("  Goodbye.")
            break

        matched = None
        for key, label, fn_name, fn_args in MENU_OPTIONS:
            if key == choice and fn_name:
                matched = (fn_name, fn_args)
                break

        if not matched:
            print("  Invalid choice.")
            continue

        fn_name, fn_args = matched
        print()
        _run_cmd(fn_name, fn_args)
        print()
        input("  Press Enter to continue...")

    return True


def cmd_lang_interactive(args):
    langs = []
    if os.path.exists(LANG_DIR):
        for f in sorted(os.listdir(LANG_DIR)):
            if f.endswith(".json"):
                code = f[:-5]
                try:
                    with open(os.path.join(LANG_DIR, f)) as lf:
                        data = json.load(lf)
                    name = data.get("lang_name", code)
                except:
                    name = code
                langs.append((code, name))

    if not langs:
        print("  No language files found.")
        return False

    current = _load_config().get("language", "en")
    print("  Available languages:")
    for i, (code, name) in enumerate(langs, 1):
        mark = " <-- current" if code == current else ""
        print(f"  [{i}] {code}  {name}{mark}")
    print("  [0] Cancel")

    try:
        choice = input("  Choose: ").strip()
        n = int(choice)
        if n == 0:
            return True
        if 1 <= n <= len(langs):
            target = langs[n - 1][0]
            return cmd_lang([target])
        print("  Invalid choice.")
    except:
        print("  Invalid choice.")
    return False


def cmd_set_remote_interactive(args):
    current = _get_remote_url() or "(not set)"
    print(f"  Current remote URL: {current}")
    new_url = input("  Enter new URL (or Enter to cancel): ").strip()
    if not new_url:
        return True
    return cmd_set_remote([new_url])


def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog="tools_updater",
        description="Update and manage Universal Extractor – local tools + remote updates"
    )
    parser.add_argument("command", nargs="?", default="menu",
                        choices=["menu", "check", "install", "update", "status",
                                 "backup", "restore", "self-check",
                                 "fetch", "check-remote", "set-remote",
                                 "fetch-zip", "lang"],
                        help="Command to run (default: check)")
    parser.add_argument("args", nargs="*", help="Extra arguments for command")
    ns = parser.parse_args()

    cmds = {
        "menu": cmd_menu,
        "check": cmd_check,
        "install": cmd_install,
        "update": cmd_update,
        "status": cmd_status,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "self-check": cmd_self_check,
        "fetch": cmd_fetch,
        "check-remote": cmd_check_remote,
        "set-remote": cmd_set_remote,
        "fetch-zip": cmd_fetch_zip,
        "lang": cmd_lang,
    }

    fn = cmds.get(ns.command)
    if fn:
        fn(ns.args)


if __name__ == "__main__":
    main()
