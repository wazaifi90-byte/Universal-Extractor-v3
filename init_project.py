import os

def create_structure():
    root = "Universal_Extractor"

    folders = [
        f"{root}/core",
        f"{root}/decoders",
        f"{root}/engines",
        f"{root}/plugins",
        f"{root}/tests",
        f"{root}/inputs",
        f"{root}/outputs",
        f"{root}/logs",
        f"{root}/errors",
    ]

    files = [
        f"{root}/main.py",
        f"{root}/config.json",
        f"{root}/signatures.json",
        f"{root}/requirements.txt",
        f"{root}/registry.py",
        f"{root}/core/__init__.py",
        f"{root}/core/scanner.py",
        f"{root}/core/processor.py",
        f"{root}/core/logger.py",
        f"{root}/core/container.py",
        f"{root}/core/validator.py",
        f"{root}/core/preview.py",
        f"{root}/core/plugin_loader.py",
        f"{root}/core/key_scraper.py",
        f"{root}/decoders/__init__.py",
        f"{root}/decoders/deflate.py",
        f"{root}/decoders/lz4_decoder.py",
        f"{root}/decoders/xor_decoder.py",
        f"{root}/decoders/bres_decoder.py",
        f"{root}/decoders/etc1.py",
        f"{root}/decoders/struct_parser.py",
        f"{root}/decoders/image_helper.py",
        f"{root}/decoders/unity.py",
        f"{root}/decoders/unreal_pak.py",
        f"{root}/decoders/cocos2dx.py",
        f"{root}/decoders/gameloft.py",
        f"{root}/decoders/konami.py",
        f"{root}/engines/__init__.py",
        f"{root}/engines/base.py",
        f"{root}/plugins/__init__.py",
        f"{root}/plugins/example_extractor.py",
        f"{root}/tests/__init__.py",
        f"{root}/tests/test_basic.py",
        f"{root}/README_PLUGINS.md",
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"Created folder: {folder}")

    for file in files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                f.write("# auto-generated - run: python main.py --setup\n")
            print(f"Created file: {file}")
        else:
            print(f"Skipped (exists): {file}")

if __name__ == "__main__":
    create_structure()
    print("\n--- Universal Extractor structure ready! ---")
    print("Place files in inputs/, then run: python main.py")
