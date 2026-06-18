import os
import sys
from core.scanner import list_signatures, get_engine_for_type
from core.plugin_loader import load_plugins

_decoders = {}
_plugin_loaded = False


def _init():
    global _plugin_loaded
    from decoders.deflate import deflate_decode
    from decoders.lz4_decoder import lz4_decode
    from decoders.xor_decoder import xor_decode
    from decoders.bres_decoder import bres_parse
    from decoders.etc1 import etc1_decode, pvrtc_decode
    from decoders.unity import UnityBundle, UnityAssets
    from decoders.unreal_pak import UnrealPak
    from decoders.cocos2dx import Cocos2dx
    from decoders.gameloft import Gameloft
    from decoders.mc4_gameloft import MC4Gameloft
    from decoders.konami import konami_extract
    from decoders.image_helper import decode_dxt
    from decoders.lzss import lzss_decode
    from decoders.yaz0 import yaz0_decode
    from decoders.audio_utils import raw_to_wav, msf_decode, xma_to_wav, genh_decode
    from decoders.godot import godot_pck_extract
    from decoders.psarc import psarc_extract
    from decoders.cryengine import cryengine_extract
    from decoders.source_engine import vpk_extract, source_extract
    from decoders.renpy import renpy_extract
    from decoders.rpgmaker import rgss_extract

    _decoders.update({
        "deflate": deflate_decode,
        "lz4": lz4_decode,
        "lzma": _std_identity,
        "gzip": _std_identity,
        "zip": _std_identity,
        "zstd": _std_identity,
        "bzip2": _std_identity,
        "lzo": _std_identity,
        "lzss": lzss_decode,
        "bres": bres_parse,
        "etc1": etc1_decode,
        "pvrtc": pvrtc_decode,
        "yaz0": yaz0_decode,
        "psarc": psarc_extract,
        "xpr0": _std_identity,
        "unity_bundle": _unity_bundle_wrap,
        "unity_assets": _unity_assets_wrap,
        "unreal_pak": _unreal_pak_wrap,
        "unreal_uexp": _std_identity,
        "cocos2d": _cocos2d_wrap,
        "godot_pck": godot_pck_extract,
        "gameloft_archive": _gameloft_wrap,
        "gameloft_pak": _gameloft_wrap,
        "gameloft_tex": _gameloft_wrap,
        "gameloft_sh": _gameloft_wrap,
        "mc4_gameloft": _mc4_wrap,
        "konami_cpk": _konami_wrap,
        "konami_afs": _konami_wrap,
        "konami_arc": _konami_wrap,
        "png": _identity,
        "jpeg": _identity,
        "gif": _identity,
        "bmp": _identity,
        "tga": _identity,
        "tiff": _identity,
        "ico": _identity,
        "webp": _identity,
        "ogg": _identity,
        "wav": _identity,
        "mp3": _identity,
        "flac": _identity,
        "riff": _identity,
        "dds": _identity,
        "gtf": _identity,
        "astc": _identity,
        "ktx": _identity,
        "fsb": _identity,
        "wwise_bnk": _std_identity,
        "wwise_wem": _std_identity,
        "bink": _identity,
        "xma": xma_to_wav,
        "crx": _identity,
        "rl7": _identity,
        "sqex_pak": _std_identity,
        "rpgmvp": _identity,
        "msf": msf_decode,
        "genh": genh_decode,
        "cryengine": cryengine_extract,
        "cryengine_chunk": cryengine_extract,
        "source_vpk": vpk_extract,
        "source_bsp": source_extract,
        "source_asset": source_extract,
        "renpy_rpa": renpy_extract,
        "rgss": rgss_extract,
        "rgd": rgss_extract,
    })

    if not _plugin_loaded:
        class _FakeReg:
            def register_type(self, n, f): _decoders[n] = f
            def register_class(self, cls):
                if hasattr(cls, 'type_name'): _decoders[cls.type_name] = cls.extract
                elif hasattr(cls, 'extract'): _decoders[cls.__name__.lower()] = cls.extract
        plugins = load_plugins(_FakeReg())
        if plugins:
            print(f"  Loaded {len(plugins)} plugin(s): {', '.join(plugins)}")
        _plugin_loaded = True


def _identity(data, output_dir, filename):
    out_path = os.path.join(output_dir, filename)
    with open(out_path, 'wb') as f:
        f.write(data)
    print(f"  Copied as-is -> {os.path.basename(out_path)} ({len(data)} bytes)")
    return True


def _std_identity(data, output_dir, filename):
    out_path = os.path.join(output_dir, filename)
    with open(out_path, 'wb') as f:
        f.write(data)
    return True


def _unity_bundle_wrap(data, output_dir, filename):
    return UnityBundle.extract(data, output_dir, filename)


def _unity_assets_wrap(data, output_dir, filename):
    return UnityAssets.extract(data, output_dir, filename)


def _unreal_pak_wrap(data, output_dir, filename):
    return UnrealPak.extract(data, output_dir, filename)


def _cocos2d_wrap(data, output_dir, filename):
    return Cocos2dx.extract(data, output_dir, filename)


def _gameloft_wrap(data, output_dir, filename):
    return Gameloft.extract(data, output_dir, filename)


def _mc4_wrap(data, output_dir, filename):
    return MC4Gameloft.extract(data, output_dir, filename)


def _konami_wrap(data, output_dir, filename):
    return konami_extract(data, output_dir, filename)


class Registry:
    def __init__(self):
        _init()

    def get(self, mode):
        return _decoders.get(mode)

    def register_type(self, name, func):
        _decoders[name] = func

    def register_class(self, cls):
        if hasattr(cls, 'type_name'):
            _decoders[cls.type_name] = cls.extract
        elif hasattr(cls, 'extract'):
            _decoders[cls.__name__.lower()] = cls.extract

    def list_modes(self):
        return list(_decoders.keys())

    def list_with_engines(self):
        sigs = list_signatures()
        result = []
        for ft, magic, engine in sigs:
            found = "yes" if ft in _decoders else "no"
            result.append((ft, magic, engine, found))
        return result


registry = Registry()
