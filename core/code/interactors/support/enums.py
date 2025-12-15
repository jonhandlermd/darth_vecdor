

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

from enum import Enum
import sys


######### ENUM CLASSES #############

class case_change(Enum):
    lower = 'lower'
    upper = 'upper'
    none = 'none'

class vec_type_class(Enum):
    cls = 'cls'
    mean = 'mean'

class code_selector_type_class(Enum):
    terminology = 'terminology'
    code_set = 'code_set'
    rel = 'rel'


class beceptivity_src_type_class(Enum):
    llm_response = 'llm_response'
    query = 'query'
    llm_2nd_response = 'llm_2nd_response'
    is_pure_beceptivity = 'is_pure_beceptivity'


class adjudicator_type_class(Enum):
    vote = 'vote'
    avg = 'avg'
    sum = 'sum'
    categorical = 'categorical'

# Get enum values from any module, defaulting to the current module
def get_enum_vals(enum_name, enums=sys.modules[__name__]):
    enum_cls = getattr(enums, enum_name, None)
    if enum_cls is None:
        raise ValueError(f"No class named '{enum_name}' in module enums")
    if not issubclass(enum_cls, Enum):
        raise TypeError(f"'{enum_name}' is not an Enum")
    return [member.value for member in enum_cls]
