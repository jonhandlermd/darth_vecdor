

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

####################
####################
####################
# IMPORTS
####################
####################
####################
#### External modules
from flask import Flask
import app_source.public_repo.core.configs.file_locations as fl
import app_source.public_repo.core.configs.other_configs as ocs
# If I dynamically load this next module using importlib (e.g., using a file location from the above module)
# then circular import errors occur. Therefore, to use a custom endpoint module located elsewhere,
# modify the import line below as needed.
# import app_source.public_repo_content.custom.use_cases.endpoint_handling.endpoints as endpoints
# However, when I retried it after moving its location, it appeared to work with importlib.
# Interestingly, cannot use globals()['endpoints'] for this. Must use endpoints = importlib...
import importlib
endpoints = importlib.import_module(f'{fl.endpoint_module}')

# Launch the flask app, identifying the location of the static folder
app = Flask(__name__,
            static_url_path='/static/',
            static_folder= f'{fl.static_loc}')

# used internally for session cookie signing
app.secret_key = ocs.app_secret_key

# Need this with statement to ensure the app_context gets pushed to the blueprint so our g variables work.
with app.app_context():
    # Register the Flask blueprint that provides all our endpoints
    app.register_blueprint(endpoints.endpoints)

# ADJUST THIS CODE AND OR THE app.run PARAMS AS APPROPRIATE,
# OR MOVE TO RUNNING FROM COMMAND LINE, OR DO OTHER APPROACH OR CHANGE AS
# APPROPRIATE.
if __name__ == '__main__':
    # TODO: Remove debug=True, fix allow_unsafe_werkzeug
    app.run(debug=True, port=5001)

