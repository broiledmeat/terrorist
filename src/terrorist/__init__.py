import sys
import os
import importlib.util
from pathlib import Path
import pkgutil
import toml
from typing import Dict


__all__ = ('init', 'config')


config: Dict = {}


def init():
    global config

    user_config_path = Path.home().joinpath('.terrorist.toml')
    if user_config_path.is_file():
        config = toml.load(user_config_path)

    from . import builtins
    builtins.init()

    _init_python()


def import_path(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def import_all_in_package(package):
    path = pkgutil.extend_path(package.__path__, package.__name__)
    for _, name, _ in pkgutil.walk_packages(path=path, prefix=f'{package.__name__}.'):
        __import__(name)


def _init_python():
    python_config = config.get('python', {})

    # Python search paths
    paths = python_config.get('paths', None)
    if isinstance(paths, list):
        for path in paths:
            sys.path.append(path)

    # Python module import names
    imports = python_config.get('imports', None)
    if isinstance(imports, list):
        for name in imports:
            __import__(name)

    # File paths to import
    import_paths = python_config.get('import_paths', None)
    if isinstance(import_paths, list):
        for path in import_paths:
            path = os.path.expandvars(os.path.expanduser(path))

            if os.path.isfile(path):
                name = os.path.splitext(os.path.basename(path))[0]
                import_path(name, path)

            elif os.path.dirname(path):
                name = os.path.basename(path)
                init_path = os.path.join(path, '__init__.py')
                if os.path.isfile(init_path):
                    package = import_path(name, init_path)
                    import_all_in_package(package)
                else:
                    raise ImportError(f'Tried to import directory "{path}", but it had no "__init__.py".')
