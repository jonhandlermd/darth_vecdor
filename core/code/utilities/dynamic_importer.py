#  Copyright (c) 2025 Keylog Solutions LLC
#
#  ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import importlib.util
import os
import types
import uuid
import importlib.util
import sys
import hashlib
from pathlib import Path
from types import ModuleType

# import app_source.public_repo.core.code.utilities.debug as debug

def is_filename(name: str) -> bool:
    """Return True if the name ends with '.py' (case-insensitive)."""
    return name.lower().endswith('.py')


def find_app_root(root_name:str="app_source") -> Path:
    path = Path(__file__).resolve().parent
    while path.name != root_name:
        init_file = path / "__init__.py"
        if not init_file.exists():
            raise RuntimeError(f"Stopped before finding {root_name}, no __init__.py in {path}")
        path = path.parent
    return path


def make_dummy_module(name: str, original_path:str) -> types.ModuleType:
    """
    Create a dummy module with a unique name and fake file attribute.

    The module is cached in sys.modules to ensure consistent behavior on repeated imports.
    """
    if name not in sys.modules:
        dummy_module = types.ModuleType(name)
        # Set dummy module's __file__ attribute to string indicating it's a dummy
        # but not a real path so it makes no attempt to load from disk.
        # Yes, it will error if some downstream system tries to load it, but it should
        # error in that case.
        dummy_module.__file__ = f"<dummy {name}>"
        dummy_module.__original_path__ = original_path
        dummy_module.__is_dummy__ = True  # Custom attribute to indicate it's a dummy
        sys.modules[name] = dummy_module
    else:
        dummy_module = sys.modules[name]
    return dummy_module


def import_module_from_path(filename: str, parent_path, make_dummy_if_not_exists=False) -> ModuleType:
    """
    Import a Python module from a relative or absolute path, caching it
    in sys.modules under a deterministic name based on the absolute resolved path.

    If the file doesn't exist or can't be imported, raises an appropriate exception.
    """
    input_path = Path(parent_path) / filename

    # Resolve to absolute path and normalize
    if not input_path.is_absolute():
        # Want app_root_parent to be one level above app_source
        # because input_path, if absolute, is relative to app_source and starts with app_source.
        app_root_parent = find_app_root().parent
        input_path =  app_root_parent/ input_path
    resolved_path = input_path.resolve(strict=False)

    # Intelligently normalize case where safe and appropriate to enable appropriate
    # comparisons.
    resolved_path = Path(os.path.normcase(str(resolved_path)))
    resolved_path_str = str(resolved_path)

    # Generate a consistent module name from the absolute path
    filename = Path(resolved_path_str).stem  # no extension
    short_hash = hashlib.sha256(resolved_path_str.encode()).hexdigest()[:12]
    module_name = f"{filename}_{short_hash}"
    # module_name = f"loaded_module_{hashlib.sha256(resolved_path_str.encode()).hexdigest()}"

    if resolved_path.is_symlink():
        try:
            target = resolved_path.resolve(strict=True)
            if not target.is_file():
                if make_dummy_if_not_exists:
                    return make_dummy_module(module_name, resolved_path_str)
                raise FileNotFoundError(f"Symlink target {target} is not a file.")
        except FileNotFoundError:
            if make_dummy_if_not_exists:
                return make_dummy_module(module_name, resolved_path_str)
            raise FileNotFoundError(f"Symlink {resolved_path_str} does not point to a valid file.")
    elif not resolved_path.is_file():
        if make_dummy_if_not_exists:
            return make_dummy_module(module_name, resolved_path_str)
        raise FileNotFoundError(f"File {resolved_path_str} does not exist or is not a file.")

    # Check if the module is already loaded
    if module_name in sys.modules:
        return sys.modules[module_name]

    # Load the module
    spec = importlib.util.spec_from_file_location(module_name, resolved_path_str)
    if spec is None or spec.loader is None:
        # If the spec is None, it means the file is not a valid Python module.
        if make_dummy_if_not_exists:
            # If we are allowed to make a dummy module, do so.
            # This is useful for cases where the file is not a valid Python module,
            # but we still want to return something.
            return make_dummy_module(module_name, resolved_path_str)
        raise ImportError(f"Cannot import module from {resolved_path_str}: No valid spec found.")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    # If the module really exists as a real file, but it fails to import, then
    # there's an actual bug, so raise the error.
    except Exception as e:
        msg = f"Failed to import module from {resolved_path_str}\nError was {e}"
        # debug.log(__file__, msg)
        raise ImportError(msg)

    sys.modules[module_name] = module
    return module

