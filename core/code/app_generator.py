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

#### External modules
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
import argparse
import sys
import app_source.public_repo.core.configs.file_locations as fl
import app_source.public_repo.core.configs.other_configs as ocs
import app_source.public_repo.core.configs.access_configs as ac
import app_source.public_repo.core.code.request_handlers.access_functions as af
# If I dynamically load this next module using importlib (e.g., using a file location from the above module)
# then circular import errors occur. Therefore, to use a custom endpoint module located elsewhere,
# modify the import line below as needed.
# import app_source.public_repo_content.custom.use_cases.endpoint_handling.endpoints as endpoints
# However, when I retried it after moving its location, it appeared to work with importlib.
# Interestingly, cannot use globals()['endpoints'] for this. Must use endpoints = importlib...
import importlib

run_configs_dict = ocs.run_configs_dict

def generate_app(**kwargs):

    # Create the flask app, identifying the location of the static folder
    app = Flask(__name__,
                static_url_path= f'{ocs.static_url_path}',
                static_folder= f'{fl.static_loc}'
                )

    # Used for session cookie signing
    app.secret_key = ocs.app_secret_key

    # Handle proxy if needed
    # Next line ensures that wsgi_proxy_fix_params BOTH exists as a variable
    # AND is not None or an empty dictionary.
    if getattr(ocs, 'wsgi_proxy_fix_params', None):
        app.wsgi_app = ProxyFix(app.wsgi_app, **ocs.wsgi_proxy_fix_params)

    # Generate immutable role-based variables for use by app
    # By doing it here once, don't have to redo it on every session or request.
    app.ks_all_app_role_names = frozenset(ac.roles.keys())
    app.ks_all_app_roles_dict = af.freeze_dict_of_sets(ac.roles)

    # Need this with statement to ensure the app_context gets pushed to the blueprint so our g variables work.
    with app.app_context():
        # Import the endpoints
        endpoints = importlib.import_module(f'{fl.endpoint_module}')
        # Register the Flask blueprint that provides all our endpoints
        app.register_blueprint(endpoints.endpoints)
        af.validate_blueprint_endpoints(app,"endpoints", '_ks_endpoint_meta')

    return app


# Admin override CLI logic
def determine_admin_override(app):
    # If we already have set this variable, then return
    if hasattr(app, 'ks_admin_override_enabled'):
        return

    # Start out assumign the override is false.
    app.ks_admin_override_enabled = False
    if app.config.get('_ks_started_from_name_is_main', False) and ac.offer_run_as_admin:
        print("\n⚠️  RUN IN ADMIN MODE? ⚠️")
        print("Give unrestricted access to ALL endpoints? (should only work on localhost)")
        confirmation_resp = 'YES'
        response = input(f"Type EXACTLY '{confirmation_resp}' to continue: ").strip()
        if response == confirmation_resp:
            app.ks_admin_override_enabled = True
            print("Running in admin mode")
        else:
            print("Not running in admin mode.")

    # All done!
    return
