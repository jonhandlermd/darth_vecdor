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
import keyring as kr

# For secrets, like passwords, keys, or anything else, use whatever secure approach is best. Do not assume
# the code shown here is necessarily the best approach or code.

#### Debugging on or of
d = False

#### Max logfile size in bytes
max_logfile_bytes = 20 * 1024 * 1024 # Default 20 MB

# This is text that will be stored in place of password in database so that  password
# is not stored in database. Do NOT put a real password here.
password_replacer = '[_PASSWORD_WAS_HERE_]'

#### This domain -- change as appropriate
this_domain = "http://127.0.0.1:5000"

#### Print errors unless otherwise specified?
default_print_errs = True

#### Write debugging info to log if debugging is on unless otherwise specified?
default_log_debugging = True

#### Show log messages on stdout unless otherwise specified?
default_show_log_msgs = False

#### Show progress in stdout unless otherwise specified?
default_show_progress = False

#### Include progress info in logging unless otherwise specified?
default_log_progress = False

#### When replacing content in HTML and formatting as table, what style should it use
table_class = 'styled-table'

#### Name of this program
sys_title = 'Darth Vecder'

# Separator string
sep = '_sep_'

# Used to sign session ids. Use whatever secure way to do this that is best. Do not assume
# this is necessarily the best approach.
app_secret_key = kr.get_password('dv_app_secret_key', 'dv')

# Static URL path
static_url_path = '/static/'

# Dictionary of WSGI ProxyFix parameters to use (excluding the first parameter that the ProxyFix function
# usually expects, since that's the app parameter and app_generator.py should apply that automatically.
wsgi_proxy_fix_params = None

run_configs_dict = {
    'debug': True
    , 'port': 5001
    }

# Each dictionary key below should be a string that may or may not be in the index.html file.
# All instances of that string will be substituted with the string that is the value of the key.
# Each dictionary key below should be a string that may or may not be in the index.html file.
# All instances of that string will be substituted with the string that is the value of the key.
# Should have keys of:
# __dv__gateway_login_url__dv__
# __dv__gateway_logout_url__dv__
index_html_substitutions_dict = {
    '__dv__gateway_login_url__dv__': '',
    '__dv__gateway_logout_url__dv__': ''
    }