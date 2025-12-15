

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

import jsonpickle
from jsonpickle.handlers import BaseHandler
from pydantic import BaseModel, create_model
import sys


class pydantic_handler(BaseHandler):
    def flatten(self, obj, data):
        """Convert a Pydantic model into a serializable dictionary."""
        data.update(obj.dict())  # Store fields as a dictionary
        data["py/object"] = obj.__class__.__module__ + "." + obj.__class__.__name__

        # If the model was created dynamically, store its fields separately
        if hasattr(obj.__class__, "__annotations__"):  # All models have annotations
            data["_dynamic_fields"] = obj.__class__.__annotations__

        return data

    def restore(self, data):
        """Restore the Pydantic model, including dynamically created ones."""
        if "py/object" not in data:
            return data  # If there's no type information, just return as-is

        module_path, class_name = data.pop("py/object").rsplit(".", 1)

        # Handle dynamically created models
        if "_dynamic_fields" in data:
            fields = data.pop("_dynamic_fields")
            cls = create_model(class_name, **{k: (v, ...) for k, v in fields.items()})
        else:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)

        return cls(**data)  # Convert back to Pydantic model


# Register the handler globally for Pydantic models
jsonpickle.handlers.register(BaseModel, pydantic_handler)

def jsonpickle_dumps(payload):
    return jsonpickle.dumps(payload)

def jsonpickle_loads(payload):
    return jsonpickle.loads(payload)

# Collect all of an object's properties as a dictionary of key-value pairs, even if the property's value is dynamically generated when accessed.
# Note that this does not serialize any of the values.
def obj_to_dict(obj):
    tdict = {}

    # Get all properties
    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        # If it's a property, then execute the getter to get the value.
        if isinstance(attr, property):
            tdict[attr_name] = attr.fget(obj)  # Call the getter to get the value

    return tdict