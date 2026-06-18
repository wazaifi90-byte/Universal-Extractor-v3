import os
import json

_translations = {}
_current_lang = "en"


def load_language(lang_code="en"):
    global _translations, _current_lang
    lang_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lang", f"{lang_code}.json")
    if os.path.exists(lang_path):
        with open(lang_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _translations = data.get("strings", {})
            _current_lang = lang_code
            return True
    _translations = {}
    _current_lang = "en"
    return False


def t(key, default=None):
    return _translations.get(key, default if default else key)


def current_lang():
    return _current_lang


def available_languages():
    lang_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lang")
    langs = []
    if os.path.exists(lang_dir):
        for f in sorted(os.listdir(lang_dir)):
            if f.endswith(".json"):
                path = os.path.join(lang_dir, f)
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    langs.append({
                        "code": data.get("lang_code", f[:-5]),
                        "name": data.get("lang_name", f[:-5])
                    })
    return langs


load_language("en")
