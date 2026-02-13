

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

import app_source.public_repo.core.code.utilities.private_configs_importer as pci
ocs = pci.bootstrap_import(f"other_configs.py", make_dummy_if_not_exists=True)


# When storing params passed to a class initilizer or some other function,
# if the password or API key or other secret is replaced, what should the replacement text be?
# Like '[_PASSWORD_WAS_HERE_]' or something like that.
password_replacer = getattr(ocs, 'password_replacer', '[_PASSWORD_WAS_HERE_]')

#### Example content for my_secrets
# from app_source.public_repo_content.core.core_codebase.prediction.utility_weighting_class_module import utility_weighting_class as uwc
#
# #### Debugging on or off (True or False, True is on, False is off)
# d = False
#
# #### This domain -- change as appropriate
# this_domain = "http://127.0.0.1:5000"
#
# #### Print errors unless otherwise specified?
# default_print_errs = True
#
# #### Write debugging info to log if debugging is on unless otherwise specified?
# default_log_debugging = True
#
# #### Show log messages on stdout unless otherwise specified?
# default_show_log_msgs = False
#
# #### Show progress in stdout unless otherwise specified?
# default_show_progress = False
#
# #### Include progress info in logging unless otherwise specified?
# default_log_progress = False
#
# #### Unique separator string this system should use when replacing content in HTML
# sep = '<archit_sep/>'
# #### Tag precursor for templates
# tag_precursor = 'at_'
#
# #### When replacing content in HTML and formatting as table, what style should it use
# table_class = 'styled-table'

#### Debugging on or off (True or False, True is on, False is off)
d = getattr(ocs, 'd', False)

#### Maximum size of logfile in bytes
max_logfile_bytes = getattr(ocs, 'max_logfile_bytes', 20 * 1024 * 1024) # Default 20 MB

#### This domain -- change as appropriate
this_domain = getattr(ocs, 'this_domain', 'http://127.0.0.1:5000')

#### Print errors unless otherwise specified? -- I think not used.
default_print_errs = getattr(ocs, 'default_print_errs', 'False')

#### Write debugging info to log if debugging is on unless otherwise specified?
default_log_debugging = getattr(ocs, 'default_log_debugging', True)

#### Show log messages on stdout unless otherwise specified?
default_show_log_msgs = getattr(ocs, 'default_show_log_msgs', False)

#### Show progress in stdout unless otherwise specified?
default_show_progress = getattr(ocs, 'default_show_progress', False)

#### Include progress info in logging unless otherwise specified?
default_log_progress = getattr(ocs, 'default_log_progress', False)

#### When replacing content in HTML and formatting as table, what style should it use
table_class = getattr(ocs, 'table_class', 'styled-table')

#### Title of this software to display in UI
sys_title = getattr(ocs, 'sys_title', 'Darth Vecder')

# Separator used when stringing together a list of items into a single string.
sep = getattr(ocs, 'sep', '_sep_')

# Secret key for session management, for use in app.py -- FAIL IF NOT SET!
app_secret_key = ocs.app_secret_key

# Static URL path
static_url_path = getattr(ocs, 'static_url_path', '/static/')

# Dictionary of WSGI ProxyFix parameters to use (excluding the first parameter that the ProxyFix function
# usually expects, since that's the app parameter and app_generator.py should apply that automatically.
wsgi_proxy_fix_params = getattr(ocs, 'wsgi_proxy_fix_params', None)

run_configs_dict = getattr(ocs, 'run_configs_dict', {})

# Each dictionary key below should be a string that may or may not be in the index.html file.
# All instances of that string will be substituted with the string that is the value of the key.
# Each dictionary key below should be a string that may or may not be in the index.html file.
# All instances of that string will be substituted with the string that is the value of the key.
# Should have keys of:
# __dv__gateway_login_url__dv__
# __dv__gateway_logout_url__dv__
index_html_substitutions_dict = getattr(ocs, 'index_html_substitutions_dict', {})
