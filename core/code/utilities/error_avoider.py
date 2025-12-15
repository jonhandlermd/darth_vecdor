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

import json

def return_str_whether_enum_or_str(item_to_check, enum_class):
    if item_to_check is None:
        return None
    if isinstance(item_to_check, str):
        return item_to_check
    elif isinstance(item_to_check, enum_class):
        return item_to_check.value
    else:
        raise ValueError(
            f"{json.dumps(item_to_check)} must be either None, a string, or an enum object.")