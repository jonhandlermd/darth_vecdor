

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
# External flask modules
from flask import Blueprint, request
#### g is a special flask variable that is global to an individual request
from flask import g

# This programs modules
import app_source.public_repo.core.code.request_handlers.endpoint_functions as epf
import app_source.public_repo.core.code.request_handlers.access_functions as af
import app_source.public_repo.core.configs.other_configs as oc
import app_source.public_repo.core.code.utilities.web_request_utils as wru
import app_source.public_repo.core.code.utilities.task_manager as tskm
import app_source.public_repo.core.code.utilities.debug as debug

import app_source.public_repo.core.code.request_handlers.front_end_list_getter as felg
import app_source.public_repo.core.code.interactors.support.enums as enums
from app_source.public_repo.core.code.setup.sql_whisperer import sql_whisperer_class as swc
from app_source.public_repo.core.code.request_handlers.access_objects import access_class as accc
from app_source.public_repo.core.code.request_handlers.access_functions import endpoint_meta


##############################
##############################
##############################
##############################
# INSTANTIATE BLUEPRINT
##############################
##############################
##############################
##############################

#### Instantiate Flask blueprint so I don't have to put all this in app.py.
#### Why not? Because then a core piece of code has to live outside of core, which is annoying. Instead,
#### a stub of an application is app.py, which then points here for all the real content.
endpoints = Blueprint('endpoints', __name__)

#### Set this URL domain
this_domain = oc.this_domain

#### What methods are allowed for requests (GET, POST, both?)
## Javascript currently coded to always post
g_allowed_request_methods = ['GET', 'POST']

# Turn on/off debugging
g_d = debug.default_d


@endpoints.before_request
def before_request_func():

    # Get request data into g.req_args
    wru.do_pre_fulfill_request_work(endpoints)

    # Check status of all running tasks
    d = g_d
    if d:
        tskm.print_all_running_threads()


##############################
##############################
##############################
##############################
# HANDLE WEB REQUESTS
##############################
##############################
##############################
##############################


############################################################
# ACCESS PRIMER
#*********** READ THIS! IMPORTANT! *******************#
# NOTE: Protection is only supplemental to the main protection YOU must provide from the web gateway.
# Don't trust this protection!
# This protection TOTALLY TRUSTS the gateway to pass user and roles correctly.
# Use this functionality AT YOUR OWN RISK!
#*****************************************************#
# Anyone can see:
# @endpoint_meta(access=accc.public())
#
# Anyone with any app role at all in this system can see:
# @endpoint_meta(access=accc.every_known_app_role())
#
# Allow list for roles allowed to see, all other known roles denied.
# @endpoint_meta(access=accc.allow('admin', 'standard_user'))

# Deny list for roles denied access, all other known roles allowed.
# @endpoint_meta(access=accc.deny('customer'))

# Decorator must come BEFORE (above) the route decorator. E.g.:
# @endpoint_meta(access=accc.every_known_app_role())
# @endpoints.route('/cancel_task', methods=['POST'])
############################################################

##############################
##############################
# SIMPLE SITE ACCESS WEB REQUESTS
##############################
##############################

#######################
# BEGIN FUNCTION
# Get home page
#######################
@endpoint_meta(access=accc.public())
@endpoints.route('/', methods = g_allowed_request_methods)
def get_home():

    ## This one is okay to not go through auditing
    g.do_not_log = True

    #### If no data request, return empty home page
    return wru.get_html_with_replacers_param(filename='index.html', replacers=oc.index_html_substitutions_dict)


############################
# END FUNCTION
############################



##############################
##############################
# ACCESS INFO REQUESTS
##############################
#############################
@endpoint_meta(access=accc.public())
@endpoints.route('/get_accessible_endpoints', methods=['GET'])
def get_accessible_endpoints():
    return wru.concoct_response('', af.allowed_urls_for_blueprint('endpoints'))


##############################
##############################
# DATA PROCESSING REQUESTS
##############################
#############################

#######################
# BEGIN FUNCTION
# Run requested processing
#######################

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_task_status', methods=['GET'])
def get_task_status():
    task_id = g.req_args['task_id']
    task_status = tskm.get_task_status(task_id)
    debug.debug(f"id: {task_id}, status: {task_status}", d=g_d)
    if not task_status:
        return wru.concoct_response('ERROR: Invalid task ID', '')
    return wru.concoct_response('', task_status)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/cancel_task', methods=['POST'])
def cancel_task():
    task_id = g.req_args['task_id']
    if not task_id:
        msg = 'ERROR: Got request to cancel, but no task ID provided.'
        debug.log(__file__, msg)
        return wru.concoct_response(msg, '')
    success = tskm.cancel_task(task_id)
    return wru.concoct_response('',{'cancelled': success})

# ////////// RELS POPULATOR ITEMS //////////////
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_populator_orchestration_names', methods = g_allowed_request_methods)
def get_rels_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='rels_populator')

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_populator_orchestration_json', methods = g_allowed_request_methods)
def get_rel_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='rels_populator', orchestrator_name=g.req_args['id'])

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/populate_rels', methods = g_allowed_request_methods)
def populate_rels():
    return epf.launch_trackable_populator('rels_populator', 'populate_rels')

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_adjudicator_types', methods = g_allowed_request_methods)
def get_adjudicator_types():
    results = enums.get_enum_vals('adjudicator_type_class')
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_code_selector_types', methods = g_allowed_request_methods)
def get_code_selector_types():
    results = enums.get_enum_vals('code_selector_type_class')
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_beceptivity_src_types', methods = g_allowed_request_methods)
def get_beceptivity_src_types():
    results = enums.get_enum_vals('beceptivity_src_type_class')
    return wru.concoct_response('', results)


#/////////// CUSTOM TABLE POPULATOR ITEMS //////////////
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_custom_table_populator_orchestration_names', methods = g_allowed_request_methods)
def get_custom_table_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='custom_table_populator')

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_custom_table_populator_orchestration_json', methods = g_allowed_request_methods)
def get_custom_table_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='custom_table_populator', orchestrator_name=g.req_args['id'])

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_custom_table', methods = g_allowed_request_methods)
def populate_custom_table():
    return epf.launch_trackable_populator('custom_table_populator', 'populate_custom_table')


# ////////// TERMINOLOGY POPULATOR ITEMS //////////////
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_terminology_populator_orchestration_names', methods = g_allowed_request_methods)
def get_terminology_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='terminology_populator')

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_terminology_populator_orchestration_json', methods = g_allowed_request_methods)
def get_terminology_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='terminology_populator', orchestrator_name=g.req_args['id'])

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_terminology_from_query', methods = g_allowed_request_methods)
def populate_terminology():
    return epf.launch_trackable_populator('terminology_populator', 'populate_terminology')


# ////////// CODE SET POPULATOR ITEMS //////////////
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_set_populator_orchestration_names', methods = g_allowed_request_methods)
def get_code_set_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='code_set_populator')

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_set_populator_orchestration_json', methods = g_allowed_request_methods)
def get_code_set_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='code_set_populator', orchestrator_name=g.req_args['id'])

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_code_set_from_query', methods = g_allowed_request_methods)
def populate_code_set():
    debug.debug("Got to populate code set from query", d=g_d)
    return epf.launch_trackable_populator('code_set_populator', 'populate_code_set')


# ////////// CODE SET MATCHER ITEMS //////////////
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_matcher_orchestration_names', methods = g_allowed_request_methods)
def get_code_matcher_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='code_set_match_populator')

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_matcher_orchestration_json', methods = g_allowed_request_methods)
def get_code_matcher_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='code_set_match_populator', orchestrator_name=g.req_args['id'])

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_code_set_matches', methods = g_allowed_request_methods)
def populate_code_set_matches():
    debug.debug("Got to populate code set matches", d=g_d)
    return epf.launch_trackable_populator('code_set_match_populator', 'populate_rel_code_matches')

# /////////// QUERY HELPER ITEMS ////////////////
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_embedder_info', methods = g_allowed_request_methods)
def get_embedder_info():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_embedder_info(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_rp_info', methods = g_allowed_request_methods)
def get_rp_info():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_rp_info(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_rcmp_info', methods = g_allowed_request_methods)
def get_rcmp_info():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_rcmp_info(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)


# ////////// OTHER FRONT END ITEMS //////////////
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_expansion_styles', methods = g_allowed_request_methods)
def get_expansion_styles():
    results = felg.get_expansion_styles()
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_code_set_names', methods = g_allowed_request_methods)
def get_code_set_names():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_code_set_names(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_terminology_names', methods = g_allowed_request_methods)
def get_terminology_names():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_terminology_names(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_llm_config_names', methods = g_allowed_request_methods)
def get_llm_config_names():
    results = felg.get_llm_configs()
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_relationship_populator_ids_and_names', methods = g_allowed_request_methods)
def get_relationship_populator_ids_and_names():
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_relationship_populator_ids_and_names(enhanced_db_obj=enhanced_db_obj)
    return wru.concoct_response('', results)

@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_of_rel_populator/')
@endpoints.route('/get_rels_of_rel_populator/<rel_populator>', methods = g_allowed_request_methods)
def get_rels_of_rel_populator(rel_populator=None):
    if not rel_populator:
        return wru.concoct_response('', [])
    enhanced_db_obj = epf.set_up_db()
    results = felg.get_rels_of_rel_populator(enhanced_db_obj=enhanced_db_obj, rel_populator=rel_populator)
    return wru.concoct_response('', results)


############################
# END FUNCTION
############################

# Always run the SQL whisperer to see if anything needs to be done or could be enhanced.
init_enhanced_db_obj = epf.set_up_db()
sql_whisperer_obj = swc(init_enhanced_db_obj, dry_run=False)
sql_whisperer_obj.run()