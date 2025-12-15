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

# Copyright (c) 2025 Jonathan A. Handler

import importlib
import importlib.util
import os
import types
import sys
import hashlib
from pathlib import Path
from types import ModuleType


class _bootstrap_class:

    def __init__(self, private_config_loc='', private_stem_prepend='', private_stem_append=''):
        self.private_config_loc = private_config_loc
        self.private_stem_prepend = private_stem_prepend
        self.private_stem_append = private_stem_append
        if self.private_stem_prepend is None:
            self.private_stem_prepend = ''
        if self.private_stem_append is None:
            self.private_stem_append = ''

# ---------------------------------------------------------
# Try each location and import whichever exists
# ---------------------------------------------------------
def import_first_existing_module(candidate_paths):
    for mod_path in candidate_paths:
        try:
            return importlib.import_module(mod_path)
        except ModuleNotFoundError:
            continue
    # If we didn't find anything, return None
    return None


# Locate and import bootstrapper.py
# then get variable holding private configs location and return it.
def _get_bootstrap_obj():

    # All possible locations of bootstrapper.py (dotted paths)
    # Paths will be evaluated in order.
    bootstrapper_candidates = [
        "app_source.not_public.secret_no_repo.configs.bootstrapper",
        "app_source.not_public.no_repo.configs.bootstrapper",
        "app_source.not_public.private_repo.configs.bootstrapper"
    ]

    # Get bootstrapper module
    bootstrapper = import_first_existing_module(candidate_paths=bootstrapper_candidates)

    # Extract the required variables
    try:
        private_config_loc = bootstrapper.private_config_loc
    except AttributeError:
        # If fail, hard code and hope everything is in default location
        # in order to maintain backward compatibility
        private_config_loc = 'app_source.not_public.secret_no_repo_content.configs'

    try:
        private_stem_prepend = bootstrapper.private_stem_prepend
    except AttributeError:
        private_stem_prepend = ''

    try:
        private_stem_append = bootstrapper.private_stem_append
    except AttributeError:
        # Maintain backward compatibility
        private_stem_append = '_private'

    bootstrap_obj = _bootstrap_class(
        private_config_loc=private_config_loc
        , private_stem_prepend=private_stem_prepend
        , private_stem_append=private_stem_append
        )

    return bootstrap_obj


# Determine if string passed is a filename yes or no
def is_filename(name: str) -> bool:
    """Return True if the name ends with '.py' (case-insensitive)."""
    return name.lower().endswith('.py')

# Walk up the modules path to find the root (e.g., app_source) and return the absolute path to it.
# REQUIRES that this importer file lives in a path accessible by module dotted pathing from
# the root_name (e.g. app_source).
def find_app_root(root_name:str="app_source") -> Path:
    path = Path(__file__).resolve().parent
    while path.name != root_name:
        init_file = path / "__init__.py"
        if not init_file.exists():
            raise RuntimeError(f"Stopped before finding {root_name}, no __init__.py in {path}")
        path = path.parent
    return path

# If we don't want to error in the event a module doesn't exist, then make a dummy module that
# can be returned.
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

# Given a filename and its parent path, import the file. If file does not exist, return
# a dummy module if requested to do so.
def import_module_from_path(filename: str, parent_path:str, make_dummy_if_not_exists=False) -> ModuleType:
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
    filename_stem = Path(resolved_path_str).stem  # no extension
    short_hash = hashlib.sha256(resolved_path_str.encode()).hexdigest()[:12]
    module_name = f"{filename_stem}_{short_hash}"
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

# Import a module using the bootstrapper to find the parent path.
def bootstrap_import(file_loc_as_filename_or_rel_path: str, make_dummy_if_not_exists=False):

    # Reject any backslashes
    if "\\" in file_loc_as_filename_or_rel_path:
        raise ValueError(
            f"Backslashes are not allowed in module paths: {file_loc_as_filename_or_rel_path!r}. "
            "Use forward slashes '/' only."
        )

    p = Path(file_loc_as_filename_or_rel_path)

    # Reject absolute paths (Unix or Windows)
    if p.is_absolute():
        raise ValueError(
            f"Absolute paths are not allowed: {file_loc_as_filename_or_rel_path!r}. "
            "All paths must be relative to the private config location."
        )

    # Convert to Path
    p = Path(file_loc_as_filename_or_rel_path)

    # Get the bootstrap object
    _bootstrap_obj = _get_bootstrap_obj()

    # Modify stem if the bootstrap object says that all file names need something
    # prepended, appended, or both to the stem of the filename.
    new_stem = _bootstrap_obj.private_stem_prepend + p.stem + _bootstrap_obj.private_stem_append  #

    # Reconstruct the file_loc with modified stem
    new_path = p.with_name(new_stem + p.suffix)

    return import_module_from_path(new_path, _bootstrap_obj.private_config_loc, make_dummy_if_not_exists)
