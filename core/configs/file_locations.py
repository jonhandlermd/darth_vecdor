

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

import os
import app_source.public_repo.core.code.utilities.private_configs_importer as pci
fl = pci.bootstrap_import(f"file_locations.py", make_dummy_if_not_exists=True)

##########################
# Automatically identify base path
##########################
# Import the root package package dynamically
root_package = getattr(fl, 'root_package', __import__('app_source'))

# Get the path to the root package
base = getattr(fl, 'base', os.path.abspath(os.path.dirname(root_package.__file__)).replace('\\', '/') + '/')

public_repo_loc = getattr(fl, 'public_repo_loc', f'{base}public_repo/')
not_public_repo_loc = getattr(fl, 'not_public_repo_loc', f'{base}not_public/')
private_repo_loc = getattr(fl, 'private_repo_loc', f'{not_public_repo_loc}private_repo/')
no_repo_loc = getattr(fl, 'no_repo_loc', f'{not_public_repo_loc}no_repo/')

#### Location of static and HTML directories
# Location of static directory
static_loc = getattr(fl, 'static_loc', f'{public_repo_loc}core/static/')
# Location of html directory
html_loc = getattr(fl, 'html_loc', f'{public_repo_loc}core/html/')
# Location of custom directory
custom_loc = getattr(fl, 'custom_loc', f'{public_repo_loc}custom/')
custom_package = getattr(fl, 'custom_package', 'app_source.public_repo.custom')

# Location of endpoint handling code
endpoint_module = getattr(fl, 'endpoint_module', f'{custom_package}.endpoints')
# socket_module = getattr(fl, 'socket_module', f'{custom_package}.sockets') # I think not used

#### Data source location if data is stored as a file
# data_loc = getattr(fl, 'data_loc', f'{no_repo_loc}data/') # I think not used

#### Debugging info -- all these are required
## all these are required ##
debugging_directory = getattr(fl, 'debugging_directory', f'{no_repo_loc}debugging/')
## These must be inside the debugging directory -- but you can rename the files
errors_filepath = f'{debugging_directory}errors.xml'
debug_filepath = f'{debugging_directory}errors.xml'
progress_filepath = f'{debugging_directory}errors.xml'

# Plugins path
plugins_path = getattr(fl, 'plugins_path', f'app_source.public_repo.core.code.interactors.plugins.')

# Setup SQLs path
setup_sqls_path = getattr(fl, 'setup_sqls_path', f'{custom_loc}setup_sqls/')
private_setup_sqls_path = getattr(fl, 'private_setup_sqls_path', f'{private_repo_loc}/private_setup_sqls/')
sql_state_path = getattr(fl, 'sql_state_path', f'{private_setup_sqls_path}/sql_states/')
sql_deprecated_path = getattr(fl, 'sql_deprecated_path', f'{private_setup_sqls_path}/deprecated_sqls/')
sql_failed_path =  getattr(fl, 'sql_failed_path', f'{private_setup_sqls_path}/failed_sqls/')


#### model paths
model_path = getattr(fl, 'model_path', f'{no_repo_loc}models/')
dl_path = getattr(fl, 'dl_path', f'{model_path}downloaded_models/')
saved_models_path = getattr(fl, 'saved_models_path', f'{model_path}saved_models/')
ft_models_path = getattr(fl, 'ft_models_path', f'{model_path}fine_tuned_models/')



