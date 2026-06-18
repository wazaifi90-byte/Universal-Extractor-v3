import os
import sys
import json
import math
import time
import struct
from collections import Counter

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CUR_DIR)
sys.path.insert(0, ROOT_DIR)

from ai.fingerprint import train_from_sample, _load_db, format_list, fingerprint_file
from core.scanner import identify_file

MODEL_PATH = os.path.join(CUR_DIR, "model_data.json")


def batch_train(directory, label=None):
    results = {"trained": 0, "errors": 0, "samples": []}
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            ft = label or identify_file(fpath)
            with open(fpath, 'rb') as f:
                header = f.read(64)
            ent = _entropy(header)
            results["samples"].append({
                "file": fname,
                "type": ft,
                "entropy": ent,
                "size": os.path.getsize(fpath)
            })
            train_from_sample(fpath, ft)
            results["trained"] += 1
        except Exception as e:
            results["errors"] += 1
    _save_model(results)
    return results


def _entropy(data):
    if not data:
        return 0
    counts = Counter(data)
    total = len(data)
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log2(p)
    return round(ent, 4)


def _save_model(results):
    db = _load_db()
    model = {
        "trained_samples": results["trained"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "entropy_ranges": db.get("entropy_ranges", {}),
        "total_supported": 0,
    }
    _, total = format_list()
    model["total_supported"] = total
    with open(MODEL_PATH, "w") as f:
        json.dump(model, f, indent=2)
    print(f"Model saved: {results['trained']} samples, {total} formats supported")


def show_model():
    if not os.path.exists(MODEL_PATH):
        print("No trained model found. Run batch_train() first.")
        return
    with open(MODEL_PATH) as f:
        model = json.load(f)
    print(f"\n{'='*50}")
    print(f"  AI Model Summary")
    print(f"{'='*50}")
    print(f"  Trained samples: {model.get('trained_samples', 0)}")
    print(f"  Total formats:   {model.get('total_supported', 0)}")
    print(f"  Last training:   {model.get('timestamp', 'N/A')}")
    print(f"\n  Entropy ranges by type:")
    for ft, r in sorted(model.get("entropy_ranges", {}).items()):
        print(f"    {ft:20s}: {r['min']:.3f} - {r['max']:.3f} [{r['count']} samples]")
    print(f"{'='*50}")


def auto_classify(file_path):
    result = fingerprint_file(file_path)
    print(f"\nFile: {os.path.basename(file_path)}")
    print(f"  Size:    {result['size']} bytes")
    print(f"  Entropy: {result['entropy']}")
    print(f"  Magic:   {result['magic_bytes']}")
    if result["is_compressed"]:
        print(f"  Compressed: yes")
    if result["suggested_formats"]:
        print(f"  Suggested formats: {', '.join(result['suggested_formats'][:5])}")
    if result["encryption"]:
        for enc_type, info in result["encryption"].items():
            print(f"  Encryption: {enc_type} ({info.get('confidence', 'N/A')})")
    if result.get("archive_hint"):
        print(f"  Archive hint: {result['archive_hint']}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Training & Classification Tool")
    parser.add_argument("--train", metavar="DIR", help="Train on all files in directory")
    parser.add_argument("--label", metavar="TYPE", help="Force label for training (optional)")
    parser.add_argument("--classify", metavar="FILE", help="Classify a single file")
    parser.add_argument("--info", action="store_true", help="Show model info")
    args = parser.parse_args()

    if args.train:
        results = batch_train(args.train, args.label)
        print(f"Trained: {results['trained']}, Errors: {results['errors']}")
    elif args.classify:
        auto_classify(args.classify)
    elif args.info:
        show_model()
    else:
        print("Use --train DIR, --classify FILE, or --info")
