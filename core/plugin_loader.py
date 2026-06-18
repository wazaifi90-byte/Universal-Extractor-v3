import os
import importlib.util
import inspect

def load_plugins(registry, plugins_dir=None):
    if plugins_dir is None:
        plugins_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins")

    if not os.path.exists(plugins_dir):
        return []

    loaded = []
    for fname in sorted(os.listdir(plugins_dir)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        fpath = os.path.join(plugins_dir, fname)
        mod_name = f"plugin_{fname[:-3]}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            for name, obj in inspect.getmembers(mod):
                if name == "register" and callable(obj):
                    obj(registry)
                    loaded.append(fname)

            if not any(callable(obj) for _, obj in inspect.getmembers(mod) if _.startswith('register')):
                for name, obj in inspect.getmembers(mod):
                    if inspect.isclass(obj) and hasattr(obj, 'extract') and hasattr(obj, 'identify'):
                        registry.register_class(obj)
                        loaded.append(fname)

        except Exception as e:
            print(f"  Plugin load error ({fname}): {e}")

    return loaded
