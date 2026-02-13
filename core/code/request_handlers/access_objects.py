#  Copyright (c) 2026 Keylog Solutions LLC
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

from dataclasses import dataclass
from typing import FrozenSet
from enum import Enum, auto


# ----------------------------
# Enum for access types
# ----------------------------
class access_type_enum(Enum):
    PUBLIC = auto()
    EVERY_KNOWN_APP_ROLE = auto()
    ALLOW_LIST = auto()
    DENY_LIST = auto()

# ----------------------------
# Base protocol for access spec
# This says anything that has a property of access_type can be treated as an access_spec object.
# ----------------------------
class access_spec_class:
    access_type: access_type_enum

# ----------------------------
# BEGIN Concrete access spec classes
# ----------------------------
@dataclass(frozen=True)
class public_access_class(access_spec_class):
    access_type: access_type_enum = access_type_enum.PUBLIC

@dataclass(frozen=True)
class every_known_app_role_access_class(access_spec_class):
    access_type: access_type_enum = access_type_enum.EVERY_KNOWN_APP_ROLE


@dataclass(frozen=True)
class allow_list_access_class(access_spec_class):
    roles: FrozenSet[str]
    access_type: access_type_enum = access_type_enum.ALLOW_LIST


@dataclass(frozen=True)
class deny_list_access_class(access_spec_class):
    roles: FrozenSet[str]
    access_type: access_type_enum = access_type_enum.DENY_LIST

# ----------------------------
# END Concrete access spec classes
# ----------------------------


# ----------------------------
# Factory helpers (single access class object)
# ----------------------------
class access_class:
    """Factory for creating access spec objects."""

    @staticmethod
    def public() -> public_access_class:
        return public_access_class()

    @staticmethod
    def every_known_app_role() -> every_known_app_role_access_class:
        return every_known_app_role_access_class()

    @staticmethod
    def allow(
            *roles
            ) -> allow_list_access_class:
        roles_set = frozenset(roles)
        return allow_list_access_class(
            roles=roles_set
            )

    @staticmethod
    def deny(
            *roles
            ) -> deny_list_access_class:
        roles_set = frozenset(roles)
        return deny_list_access_class(
            roles=roles_set
            )


