"""
Example plugin for Universal Extractor.
Copy this file to plugins/ and implement register(registry).

Your register() function will be called automatically at startup.
Use registry.register_type("name", function) to add decoders.
"""


def register(registry):
    registry.register_type("example_custom", example_decode)
    print("  [Plugin] example_custom decoder registered")


def example_decode(data, output_dir, filename):
    import os
    out_path = os.path.join(output_dir, f"{filename}.example")
    with open(out_path, 'wb') as f:
        f.write(data)
    print(f"  [Plugin] Example: wrote {os.path.basename(out_path)}")
    return True
