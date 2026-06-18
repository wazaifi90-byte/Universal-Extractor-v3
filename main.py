import os
import sys
import json
import time
import argparse
import concurrent.futures
from core.scanner import identify_file, list_signatures
from core.processor import process_file
from core.preview import preview_file
from core.logger import Logger
from core.key_scraper import scrape_exe, scrape_directory, suggest_key_for_file
from core.i18n import t, load_language, current_lang, available_languages
from core.database import init_db as init_stats_db, get_stats, log_operation
from decoders.xor_decoder import set_key as set_xor_key

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich import box
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


def _console():
    return Console() if _HAS_RICH else None


def _auto_delete(config, input_dir, files):
    if config.get("settings", {}).get("auto_delete_input"):
        for fname in files:
            try:
                os.remove(os.path.join(input_dir, fname))
            except:
                pass


class UniversalExtractor:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = Logger(self.config["paths"]["log_dir"])
        self._running = False
        self._apply_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            "active_mode": "auto",
            "paths": {
                "input_dir": "inputs",
                "output_dir": "outputs",
                "log_dir": "logs",
                "error_dir": "errors"
            },
            "settings": {
                "scan_interval_seconds": 2,
                "auto_delete_input": False,
                "process_subdirectories": True,
                "extract_nested": True,
                "xor_key": None,
                "stream_chunk_size": 1048576,
                "race_wait_seconds": 2,
                "enable_hashing": True,
                "enable_validation": True,
                "parallel": False,
                "max_workers": 4
            }
        }

    def _apply_config(self):
        xor_key = self.config.get("settings", {}).get("xor_key")
        if xor_key is not None:
            set_xor_key(xor_key)
            self.logger.log(f"XOR key set from config: 0x{xor_key:02X}")

    def _ensure_dirs(self):
        for key in ["input_dir", "output_dir", "log_dir", "error_dir"]:
            path = self.config["paths"][key]
            if not os.path.exists(path):
                os.makedirs(path)

    def _wait_for_file_ready(self, file_path):
        wait = self.config.get("settings", {}).get("race_wait_seconds", 2)
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(wait)
            size2 = os.path.getsize(file_path)
            return size1 == size2
        except:
            return False

    def process_single(self, file_path):
        filename = os.path.basename(file_path)
        self.logger.log(f"Processing: {filename}")
        if not self._wait_for_file_ready(file_path):
            self.logger.log(f"File size unstable, skipping: {filename}")
            print(f"  Skipped (size unstable): {filename}")
            return False
        file_type = identify_file(file_path)
        print(f"  Type: {file_type}")
        self.logger.log(f"Detected type: {file_type}")
        result = process_file(
            file_path,
            file_type,
            self.config["paths"]["output_dir"],
            self.config["paths"]["error_dir"],
            self.config
        )
        if result:
            self.logger.log(f"Success: {filename}")
            if self.config.get("settings", {}).get("auto_delete_input"):
                try:
                    os.remove(file_path)
                    self.logger.log(f"Deleted: {filename}")
                except Exception as e:
                    self.logger.log(f"Delete failed: {filename} - {e}")
        else:
            self.logger.log(f"Failed: {filename}")
        return result

    def scan_inputs(self):
        input_dir = self.config["paths"]["input_dir"]
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        if not files:
            return 0
        parallel = self.config.get("settings", {}).get("parallel", False)
        max_workers = self.config.get("settings", {}).get("max_workers", 4)

        if parallel and len(files) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(self.process_single, os.path.join(input_dir, f)): f for f in files}
                concurrent.futures.wait(futs)
            _auto_delete(self.config, input_dir, files)
            return len(files)

        for fname in files:
            self.process_single(os.path.join(input_dir, fname))
        _auto_delete(self.config, input_dir, files)
        return len(files)

    def watch(self):
        self._ensure_dirs()
        self._running = True
        interval = self.config["settings"]["scan_interval_seconds"]
        self.logger.log(f"Watching {self.config['paths']['input_dir']}/ every {interval}s...")
        banner = f"""
{'='*55}
  Universal Extractor v3.0
  Input:   {os.path.abspath(self.config['paths']['input_dir'])}/
  Output:  {os.path.abspath(self.config['paths']['output_dir'])}/
  Errors:  {os.path.abspath(self.config['paths']['error_dir'])}/
  Interval: {interval}s | Ctrl+C to stop
{'='*55}"""
        print(banner)
        while self._running:
            try:
                count = self.scan_inputs()
                if count > 0:
                    self.logger.log(f"Round processed: {count} file(s)")
                time.sleep(interval)
            except KeyboardInterrupt:
                break
        print("\nStopped.")

    def stop(self):
        self._running = False

    def show_info(self):
        sigs = list_signatures()
        from registry import registry
        decoders = registry.list_modes()
        print(f"\n{'='*55}")
        print(f"  Universal Extractor v3.0")
        print(f"{'='*55}")
        print(f"  Signatures: {len(sigs)}")
        print(f"  Decoders:   {len(decoders)}")
        print(f"\nRegistered formats ({len(sigs)}):")
        for ft, magic, engine in sigs:
            dec_avail = "yes" if ft in decoders else "no"
            status = "+" if dec_avail == "yes" else "-"
            print(f"  [{status}] {ft:20s} {magic:25s} [{engine}]")
        cfg = self.config.get("settings", {})
        print(f"\nSettings:")
        print(f"  XOR key:         {'auto-detect' if cfg.get('xor_key') is None else '0x' + format(cfg['xor_key'], '02X')}")
        print(f"  Stream chunk:    {cfg.get('stream_chunk_size', 1048576)} bytes")
        print(f"  Race wait:       {cfg.get('race_wait_seconds', 2)}s")
        print(f"  Auto delete:     {cfg.get('auto_delete_input', False)}")
        print(f"  Extract nested:  {cfg.get('extract_nested', True)}")
        print(f"  Hashing:         {cfg.get('enable_hashing', True)}")
        print(f"  Validation:      {cfg.get('enable_validation', True)}")
        print(f"  Parallel:        {cfg.get('parallel', False)} ({cfg.get('max_workers', 4)} workers)")
        print()


def run_once(args):
    app = UniversalExtractor(args.config)
    app._ensure_dirs()
    count = app.scan_inputs()
    if count == 0:
        print("No files found in inputs/")
    else:
        print(f"Processed {count} file(s)")


def run_watch(args):
    app = UniversalExtractor(args.config)
    try:
        app.watch()
    except KeyboardInterrupt:
        app.stop()


def run_setup(args):
    app = UniversalExtractor(args.config)
    app._ensure_dirs()
    print("Directories created. Place files in inputs/ and run.")


def run_info(args):
    app = UniversalExtractor(args.config)
    app.show_info()


def run_single(args):
    app = UniversalExtractor(args.config)
    app._ensure_dirs()
    if not args.file:
        print("Error: --file is required with --single")
        return
    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}")
        return
    print(f"Processing single file: {args.file}")
    app.process_single(args.file)


def run_preview(args):
    app = UniversalExtractor(args.config)
    if not args.file:
        print("Error: --file is required with --preview")
        return
    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}")
        return
    preview_file(args.file)


def run_scrape_keys(args):
    fpath = args.scrape_keys
    if not os.path.exists(fpath):
        print(f"Error: file not found: {fpath}")
        return
    print(f"\nScanning: {fpath}")
    keys = scrape_exe(fpath)
    if keys:
        print(f"\nFound {len(keys)} potential key(s):")
        print(f"  {'Type':20s} {'Value':20s} {'Confidence':10s} {'Hits':>6s}")
        print(f"  {'-'*20} {'-'*20} {'-'*10} {'-'*6}")
        for k in keys[:10]:
            print(f"  {k['type']:20s} {k['hex']:20s} {k['confidence']:10s} {k['occurrences']:6d}")
        best = keys[0]
        print(f"\n  Suggested key: {best['hex']} ({best['type']})")
    else:
        print("  No potential keys found.")


def run_scrape_dir(args):
    dpath = args.scrape_dir
    if not os.path.isdir(dpath):
        print(f"Error: directory not found: {dpath}")
        return
    print(f"\nScanning directory: {dpath}")
    results = scrape_directory(dpath)
    if results:
        print(f"\nFound keys in {len(results)} file(s):")
        for fname, keys in sorted(results.items()):
            best = keys[0] if keys else None
            if best:
                print(f"  {fname:30s} -> {best['hex']:20s} ({best['confidence']})")
    else:
        print("  No keys found in any file.")


def run_web(args):
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from web_app.app import run_web
        port = args.web_port or 5000
        host = args.web_host or "127.0.0.1"
        print(f"Starting Web Dashboard at http://{host}:{port}")
        print("Press Ctrl+C to stop.")
        run_web(host=host, port=port)
    except ImportError as e:
        print(f"Error starting web dashboard: {e}")
        print("Make sure Flask is installed: pip install flask")


def run_ai_classify(args):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ai.train_ai import auto_classify
        auto_classify(args.ai_classify)
    except ImportError as e:
        print(f"Error: {e}")


def run_ai_train(args):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ai.train_ai import batch_train
        results = batch_train(args.ai_train, args.label)
        print(f"Trained: {results['trained']}, Errors: {results['errors']}")
    except ImportError as e:
        print(f"Error: {e}")


def run_ai_info(args):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ai.train_ai import show_model
        show_model()
    except ImportError as e:
        print(f"Error: {e}")


def _run_stats():
    try:
        init_stats_db()
        stats = get_stats()
        print(f"\n{'='*40}")
        print(f"  {t('app_name')} - {t('complete')}")
        print(f"{'='*40}")
        print(f"  {t('done')}: {stats['success']}")
        print(f"  {t('failed')}: {stats['failed']}")
        print(f"  Total: {stats['total']}")
        if stats.get('by_type'):
            print(f"\n  {t('scanning')}:")
            for r in stats['by_type']:
                print(f"    {r['file_type'] or 'unknown'}: {r['c']}")
        print()
    except Exception as e:
        print(f"Error loading stats: {e}")


def _run_languages():
    langs = available_languages()
    print(f"\n{t('app_name')} - {t('config_loaded')}")
    print(f"  {t('language_switched')}:")
    for l in langs:
        current = " <--" if l['code'] == current_lang() else ""
        print(f"    {l['code']:10s} {l['name']}{current}")
    print()


def run_fingerprint(args):
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from ai.fingerprint import fingerprint_file, format_list
        groups, total = format_list()
        if args.fingerprint and args.fingerprint != '__list__':
            result = fingerprint_file(args.fingerprint)
            print(f"\nFile: {os.path.basename(args.fingerprint)}")
            print(f"  Size:    {result['size']} bytes")
            print(f"  Entropy: {result['entropy']}")
            print(f"  Magic:   {result['magic_bytes']}")
            if result["is_compressed"]:
                print(f"  Compressed: yes")
            if result["suggested_formats"]:
                print(f"  Suggested: {', '.join(result['suggested_formats'][:5])}")
            if result.get("encryption"):
                for enc_type, info in result["encryption"].items():
                    print(f"  Encryption: {enc_type} ({info.get('confidence', 'N/A')})")
        else:
            print(f"\nFormat Groups ({total} total):")
            for group, fmts in groups.items():
                print(f"  {group}: {', '.join(fmts)}")
    except ImportError as e:
        print(f"Error: {e}")


def main_cli():
    import sys
    sys.argv = sys.argv  # use sys.argv as-is
    _entry()

def _entry():
    parser = argparse.ArgumentParser(
        description="Universal Extractor v3.0 - Multi-engine game file extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Watch inputs/ folder
  python main.py --once             Process all files in inputs/ once
  python main.py --once --parallel  Process files in parallel
  python main.py --single file.bin  Process one specific file
  python main.py --preview file.bin Quick header info without extraction
  python main.py --info             Show all supported formats (58+)
  python main.py --setup            Create required directories
  python main.py --web              Start web dashboard at http://127.0.0.1:5000
  python main.py --web --port 8080  Web dashboard on custom port
  python main.py --ai-classify file.bin  Classify with AI fingerprint
  python main.py --ai-train ./samples/   Train AI on sample files
  python main.py --fingerprint file.bin  Analyze file signature
  python main.py --fingerprint          List all format groups
  python main.py --scrape-keys game.exe  Scrape XOR keys from exe
  python main.py --scrape-dir ./game/    Scrape keys from all exe in dir
        """
    )
    parser.add_argument('--config', default='config.json', help='Config file path (default: config.json)')
    parser.add_argument('--once', action='store_true', help='Process files once and exit')
    parser.add_argument('--watch', action='store_true', help='Watch inputs/ folder (default)')
    parser.add_argument('--setup', action='store_true', help='Create required directories')
    parser.add_argument('--info', action='store_true', help='Show supported signatures and settings')
    parser.add_argument('--single', metavar='FILE', help='Process a single file')
    parser.add_argument('--preview', metavar='FILE', help='Preview file header info without extraction')
    parser.add_argument('--parallel', action='store_true', help='Process files in parallel')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers (default: 4)')
    parser.add_argument('--scrape-keys', metavar='FILE', help='Scrape XOR keys from an exe/dll file')
    parser.add_argument('--scrape-dir', metavar='DIR', help='Scrape XOR keys from all exe/dll in a directory')
    parser.add_argument('--no-hash', action='store_true', help='Disable file hashing')
    parser.add_argument('--no-validate', action='store_true', help='Disable output validation')
    parser.add_argument('--web', action='store_true', help='Start web dashboard')
    parser.add_argument('--web-host', default='127.0.0.1', help='Web dashboard host (default: 127.0.0.1)')
    parser.add_argument('--web-port', type=int, default=5000, help='Web dashboard port (default: 5000)')
    parser.add_argument('--ai-classify', metavar='FILE', help='Classify file with AI fingerprint analysis')
    parser.add_argument('--ai-train', metavar='DIR', help='Train AI model on files in directory')
    parser.add_argument('--ai-info', action='store_true', help='Show AI model info')
    parser.add_argument('--fingerprint', metavar='FILE', nargs='?', const='__list__', help='Analyze file fingerprint, or list format groups')
    parser.add_argument('--lang', default=None, help='Set language (en, ar)')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    parser.add_argument('--languages', action='store_true', help='List available languages')

    args = parser.parse_args()

    if args.lang:
        if load_language(args.lang):
            print(f"[{t('config_loaded')}] {t('language_switched')} {args.lang}")
        else:
            print(f"Language not found: {args.lang}")
            sys.exit(1)

    if args.parallel or args.workers != 4 or args.no_hash or args.no_validate:
        if os.path.exists(args.config):
            cfg = json.load(open(args.config))
            if args.parallel:
                cfg['settings']['parallel'] = True
            if args.workers != 4:
                cfg['settings']['max_workers'] = args.workers
            if args.no_hash:
                cfg['settings']['enable_hashing'] = False
            if args.no_validate:
                cfg['settings']['enable_validation'] = False
            json.dump(cfg, open(args.config, 'w'), indent=4)

    if args.setup:
        run_setup(args)
    elif args.info:
        run_info(args)
    elif args.once:
        run_once(args)
    elif args.single:
        run_single(args)
    elif args.scrape_keys:
        run_scrape_keys(args)
    elif args.scrape_dir:
        run_scrape_dir(args)
    elif args.preview:
        run_preview(args)
    elif args.web:
        run_web(args)
    elif args.ai_classify:
        run_ai_classify(args)
    elif args.ai_train:
        run_ai_train(args)
    elif args.ai_info:
        run_ai_info(args)
    elif args.fingerprint:
        run_fingerprint(args)
    elif args.stats:
        _run_stats()
    elif args.languages:
        _run_languages()
    else:
        run_watch(args)


if __name__ == "__main__":
    _entry()
