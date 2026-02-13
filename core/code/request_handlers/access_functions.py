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
import ipaddress
from types import MappingProxyType
from typing import cast
from flask import g, abort, current_app, request

from app_source.public_repo.core.code.request_handlers.access_objects import (
    access_spec_class
    , access_type_enum
    )

import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.configs.access_configs as ac


def endpoints_for_blueprint(app, blueprint_name: str) -> set[str]:
    prefix = blueprint_name + "."
    return {
        endpoint
        for endpoint in app.view_functions
        if endpoint.startswith(prefix)
    }


def validate_blueprint_endpoints(app, blueprint_name: str, required_view_attr:str="_ks_endpoint_meta"):
    for endpoint, view in app.view_functions.items():
        if endpoint.startswith(blueprint_name + "."):
            if not hasattr(view, required_view_attr):
                raise RuntimeError(
                    f"{endpoint} missing required endpoint decorating"
                    )


def freeze_dict_of_sets(
    d: dict[str, set[str]]
) -> MappingProxyType:
    return MappingProxyType({
        k: frozenset(v)
        for k, v in d.items()
    })

# Is this dev mode:
def is_dev_mode():
    if current_app.config.get("ENV") == "production":
        return False
    if current_app.debug or current_app.config.get("ENV") == "production":
        return True
    return False

# Was this started from main?
def is_started_from_name_is_main():
    return current_app.config.get("_ks_started_from_name_is_main", False)

# Localhost check
def is_local_request():
    addr = request.remote_addr
    if not addr:
        return False
    try:
        ip = ipaddress.ip_address(addr)
        return ip.is_loopback
    except ValueError:
        return False


# Build list of app role names this user is a member of.
def get_user_app_roles(header_passed_roles:list):

    temp_user_app_role_names:set[str] = set()
    for ac_role in current_app.ks_all_app_role_names:
        header_roles_mappings_to_app_role = current_app.ks_all_app_roles_dict[ac_role]
        if header_roles_mappings_to_app_role.intersection(header_passed_roles):
            temp_user_app_role_names.add(ac_role)
    user_app_roles = frozenset(temp_user_app_role_names)

    # Return list of app role names this user is a member of
    return user_app_roles


# Function for the endpoint_meta decorator
def endpoint_meta(*, access:access_spec_class):
    # Make sure they passed an access object
    if access is None:
        msg = "endpoint_meta requires an access specification"
        debug.log(__file__, msg)
        raise ValueError(msg)

    def decorator(fn):
        fn._ks_endpoint_meta = {"access": access}
        return fn

    return decorator


def get_user_and_user_app_roles_into_flask_g():
    # Map headers
    header_passed_roles = []
    g.user = None
    for hdr, key in ac.header_mapper.items():
        value = request.headers.get(hdr)
        if value:
            # If multiple keys mapped to user, which would be a bad thing, take the first.
            if key == "user" and g.user is None:
                g.user = value.strip()
            elif key == "roles":

                # Split comma-separated list of roles/groups
                # If multiple keys mapped to roles, then append what we got now to what we already have.
                header_passed_roles.extend(v.strip() for v in value.split(","))

    # Convert the passed roles we received in headers to user app roles set
    g.user_app_roles = get_user_app_roles(header_passed_roles=header_passed_roles)


# Enforcement logic
def enforce_endpoint_access(
            passed_blueprint=None,
            passed_access=None,
            passed_endpoint=None):

    all_none = passed_blueprint is None and passed_access is None and passed_endpoint is None
    all_passed = passed_blueprint is not None and passed_access is not None and passed_endpoint is not None

    # Only can be legit if all_none OR all_passed, nothing in between.
    if not all_none and not all_passed:
        msg = "enforce_endpoint_access did not receive legit params (all or none)"
        debug.log(__file__, msg)
        raise Exception(msg)

    # This only applies to blueprint endpoints
    # Ignore requests not in our sensitive blueprint(s)
    if all_passed and passed_blueprint != 'endpoints':
        return True, ''
    elif all_none and request.blueprint != 'endpoints':
        return True, ''

    # Populate flask g (g.user and g.user_app_roles
    get_user_and_user_app_roles_into_flask_g()


    # If we weren't passed info we need, then we need to get the info we need
    # from the request and Flask info
    if all_none:

        # Make sure desired g variable was populated and is not empty.
        # Shouldn't be needed, but make sure
        if not getattr(g, 'ks_endpoint_view', None):
            msg = f"Endpoint view variable not populated."
            debug.log(__file__, msg)
            raise Exception(msg)

        meta = getattr(g.ks_endpoint_view, "_ks_endpoint_meta", None)

        # No metadata → ERROR!
        if meta is None:
            msg = f"Endpoint {g.ks_endpoint_view} has no access metadata"
            debug.log(__file__, msg)
            raise RuntimeError(msg)

        # meta MUST have an access key as our decorator enforces it.
        # But, if for any reason it doesn't, let it error -- don't protect from this with a "get"!
        access_obj = cast(access_spec_class, meta["access"])

    else:
        access_obj = passed_access

    # If the access type is public, then allow (don't abort).
    if access_obj.access_type is access_type_enum.PUBLIC:
        return True, ''

    # If admin_override and all admin override requirements are met, then let them in.
    if (getattr(current_app, 'ks_admin_override_enabled', False)
            and is_local_request()
            and is_dev_mode()
            and is_started_from_name_is_main()
            ):
        return True, ''

    # If we didn't receive any roles from the gateway that map to any app roles, we have a problem! Abort!
    if not g.user_app_roles:
        msg = "No user roles provided that map to any app roles"
        debug.log(__file__, f"{msg}")
        return False, msg

    # Handle if this is an all known roles-type endpoint
    if access_obj.access_type is access_type_enum.EVERY_KNOWN_APP_ROLE:
        # we previously checked to make sure the user had some known role,
        # so if they made it this far, then allow.
        return True, ''
    elif access_obj.access_type is access_type_enum.ALLOW_LIST:
        # Does at least one of the user_app_roles appear in the access_obj set of roles?
        if g.user_app_roles.intersection(access_obj.roles):
            return True, ''
        else:
            msg = f"This function ({passed_endpoint}) not allowed given this user's app roles."
            debug.log(__file__, msg)
            return False, msg
    elif access_obj.access_type is access_type_enum.DENY_LIST:
        # Does at least one of the user_app_roles appear in the access_obj set of roles?
        if g.user_app_roles.intersection(access_obj.roles):
            msg = f"This function ({passed_endpoint}) is denied given this user's app roles."
            debug.log(__file__, msg)
            return False, msg
        else:
            return True, ''
    else:
        msg = "A failure of endpoint access enforcement has occurred."
        debug.log(__file__, msg)
        raise Exception(msg)

    # I don't think I need this, but just in case.
    return True, ''


def allowed_urls_for_blueprint(blueprint_name):
    """
    Returns a set of URL paths like:
      {
        "/get_code_matcher_orchestration_names",
        "/populate_code_set_matches",
      }
    """

    allowed_urls = set()

    for rule in current_app.url_map.iter_rules():
        # Only endpoints belonging to this blueprint
        if not rule.endpoint.startswith(f"{blueprint_name}."):
            continue

        view_fn = current_app.view_functions.get(rule.endpoint)
        if view_fn is None:
            continue

        meta = getattr(view_fn, "_ks_endpoint_meta", None)
        # No metadata → ERROR!
        if meta is None:
            msg = f"Endpoint {view_fn} has no access metadata"
            debug.log(__file__, msg)
            raise RuntimeError(msg)

        # meta MUST have an access key as our decorator enforces it.
        # But, if for any reason it doesn't, let it error -- don't protect from this with a "get"!
        access_obj = cast(access_spec_class, meta["access"])

        # Decide policy for missing metadata
        if access_obj is None:
            continue  # or treat as denied

        is_allowed, msg = enforce_endpoint_access(
            passed_blueprint=blueprint_name,
            passed_access=access_obj,
            passed_endpoint=rule.endpoint
        )

        if is_allowed:
            # rule.rule is the *relative* URL path
            allowed_urls.add(rule.rule)

    return list(allowed_urls)



