


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


# For secrets, like passwords, keys, or anything else, use whatever secure approach is best. Do not assume
# the code shown here is necessarily the best approach or code.

##########################
# Automatically identify base path
##########################
import os
# Import the root package package dynamically
root_package = __import__('app_source')
# Get the path to the root package
base = os.path.abspath(os.path.dirname(root_package.__file__))
base = base.replace('\\', '/') + '/'

##########################
# External item
##########################
model_path = "/Users/YourUser/Path/To/YourLocal/gen_ai_models/"


##########################
# Major sections of code
##########################
public_repo_loc = f'{base}public_repo/'
not_public_repo_loc = f'{base}not_public/'
private_repo_loc = f'{not_public_repo_loc}private_repo/'
no_repo_loc = f'{not_public_repo_loc}no_repo/'


##########################
# Required directory location variables
##########################
# Location of static directory
static_loc = f'{public_repo_loc}core/static/'
# Location of html directory
html_loc = f'{public_repo_loc}core/html/'
# Location of custom directory
custom_loc = f'{public_repo_loc}custom/'


#######################
# Required location of endpoint handling
#######################
custom_package = 'app_source.public_repo.custom'
endpoint_module = f'{custom_package}.endpoints'


##########################
# Other directories, files, and/or configs
##########################
## DEBUGGING ##
## all these are required ##
debugging_directory = f'{no_repo_loc}debugging/'
## These must be inside the debugging directory -- I don't think used with new debugging.
errors_filepath = f'{debugging_directory}errors.xml'
debug_filepath = f'{debugging_directory}errors.xml'
progress_filepath = f'{debugging_directory}errors.xml'

# Plugins path
plugins_path = f'app_source.public_repo.core.code.interactors.plugins.'

# Setup SQLs path
setup_sqls_path = f'{custom_loc}setup_sqls/'
private_setup_sqls_path = f'{private_repo_loc}/private_setup_sqls/'
sql_state_path = f'{private_setup_sqls_path}/sql_states/'
sql_deprecated_path = f'{private_setup_sqls_path}/deprecated_sqls/'
sql_failed_path =  f'{private_setup_sqls_path}/failed_sqls/'


#### model paths
dl_path = f'{model_path}downloaded_models/'
saved_models_path = f'{model_path}saved_models/'
ft_models_path = f'{model_path}fine_tuned_models/'

