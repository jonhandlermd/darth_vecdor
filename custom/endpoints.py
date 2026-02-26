

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

# *****************************
# *****************************
# *****************************
# IMPORTS
# *****************************
# *****************************
# *****************************
# External flask modules
from flask import Blueprint
#### g is a special flask variable that is global to an individual request
from flask import g

# This programs modules
import app_source.public_repo.core.code.request_handlers.endpoint_functions as epf
import app_source.public_repo.core.code.request_handlers.access_functions as af
import app_source.public_repo.core.configs.other_configs as oc
import app_source.public_repo.core.code.utilities.web_request_utils as wru
import app_source.public_repo.core.code.utilities.debug as debug
from app_source.public_repo.core.code.request_handlers.access_objects import access_class as accc
from app_source.public_repo.core.code.request_handlers.access_functions import endpoint_meta


# *****************************
# *****************************
# *****************************
# *****************************
# INSTANTIATE BLUEPRINT
# *****************************
# *****************************
# *****************************
# *****************************

# Instantiate Flask blueprint so I don't have to put all this in app.py.
# Why not? Because then a core piece of code has to live outside of core, which is annoying. Instead,
# a stub of an application is app.py, which then points here for all the real content.
endpoints = Blueprint('endpoints', __name__)
# What methods are allowed for requests (GET, POST, both?)
# Last I looked, Javascript coded to always post
g_allowed_request_methods = ['GET', 'POST']
# Turn on/off debugging
g_d = debug.default_d


# *****************************
# *****************************
# BEFORE/AFTER REQUESTS
# *****************************
# *****************************

# Before request handling
@endpoints.before_request
def before_request_func():
    epf.before_request_func(endpoints=endpoints, d=g_d)


# *****************************
# *****************************
# *****************************
# *****************************
# HANDLE WEB REQUESTS
# *****************************
# *****************************
# *****************************
# *****************************


# *****************************
# *****************************
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
# *****************************
# *****************************


# *****************************
# *****************************
# SIMPLE SITE ACCESS WEB REQUESTS
# *****************************
# *****************************

# Get home page
@endpoint_meta(access=accc.public())
@endpoints.route('/', methods = g_allowed_request_methods)
def get_home():
    g.do_not_log = True # This one is okay to not go through auditing
    return wru.get_html_with_replacers_param(filename='index.html', replacers=oc.index_html_substitutions_dict)


# *****************************
# *****************************
# ACCESS INFO REQUESTS
# *****************************
# *****************************

# Return endpoints accessible by this role(s), e.g., to decide what a menu should show vs. hide.
@endpoint_meta(access=accc.public())
@endpoints.route('/get_accessible_endpoints', methods=['GET'])
def get_accessible_endpoints():
    return wru.concoct_response('', af.allowed_urls_for_blueprint('endpoints'))


# *****************************
# *****************************
# TASK TRACKING ENDPOINTS
# *****************************
# *****************************

# Get Task Status for whatever is processing
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_task_status', methods=['GET'])
def get_task_status():
    return epf.get_task_status()


# Cancel task that is processing
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/cancel_task', methods=['POST'])
def cancel_task():
    return epf.cancel_task()


# *****************************
# TERMINOLOGY POPULATOR ENDPOINTS
# *****************************

# Get terminology populator orchestration names (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_terminology_populator_orchestration_names', methods = g_allowed_request_methods)
def get_terminology_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='terminology_populator')


# Get terminology populator orchestration names (e.g., to use in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_terminology_populator_orchestration_json', methods = g_allowed_request_methods)
def get_terminology_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='terminology_populator', orchestrator_name=g.req_args['id'])

# Actually populate the terminology from a query
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_terminology_from_query', methods = g_allowed_request_methods)
def populate_terminology():
    return epf.launch_trackable_populator('terminology_populator', 'populate_terminology')


# *****************************
# *****************************
# CODE SET POPULATOR ENDPOINTS
# *****************************
# *****************************

# Get code set populator orchestration names (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_set_populator_orchestration_names', methods = g_allowed_request_methods)
def get_code_set_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='code_set_populator')

# Get code set populator orchestration JSON (e.g., to use to populate form in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_set_populator_orchestration_json', methods = g_allowed_request_methods)
def get_code_set_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='code_set_populator', orchestrator_name=g.req_args['id'])


# Use a query to populate code set in database
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_code_set_from_query', methods = g_allowed_request_methods)
def populate_code_set():
    return epf.launch_trackable_populator('code_set_populator', 'populate_code_set')


# *****************************
# *****************************
#  RELS POPULATION ENDPOINTS
# *****************************
# *****************************

# Get relationship populator orchestration names (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_populator_orchestration_names', methods = g_allowed_request_methods)
def get_rels_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='rels_populator')


# Get the JSON of a relationship populator
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_populator_orchestration_json', methods = g_allowed_request_methods)
def get_rel_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='rels_populator', orchestrator_name=g.req_args['id'])


# Launch a database populator in a way that we can track and manage as a task.
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/populate_rels', methods = g_allowed_request_methods)
def populate_rels():
    return epf.launch_trackable_populator('rels_populator', 'populate_rels')


# Return adjudicator types (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_adjudicator_types', methods = g_allowed_request_methods)
def get_adjudicator_types():
    return epf.get_adjudicator_types()


# Return code selector types (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_code_selector_types', methods = g_allowed_request_methods)
def get_code_selector_types():
    return epf.get_code_selector_types()


# Return beceptivity source types (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_beceptivity_src_types', methods = g_allowed_request_methods)
def get_beceptivity_src_types():
    return epf.get_beceptivity_src_types()


# *****************************
# *****************************
# CUSTOM TABLE POPULATOR ENDPOINTS
# *****************************
# *****************************

# Get custom table populator orchestration names (e.g., to show in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_custom_table_populator_orchestration_names', methods = g_allowed_request_methods)
def get_custom_table_populator_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='custom_table_populator')


# Get custom table populator orchestration JSON (e.g. to populate GUI content)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_custom_table_populator_orchestration_json', methods = g_allowed_request_methods)
def get_custom_table_populator_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='custom_table_populator', orchestrator_name=g.req_args['id'])

# Populate the custom table
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_custom_table', methods = g_allowed_request_methods)
def populate_custom_table():
    return epf.launch_trackable_populator('custom_table_populator', 'populate_custom_table')


# *****************************
# *****************************
# CODE MATCHER ITEMS
# *****************************
# *****************************

# Get code matcher populator orchestration names (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_matcher_orchestration_names', methods = g_allowed_request_methods)
def get_code_matcher_orchestration_names():
    return epf.get_orchestration_names(orchestrator_type='code_set_match_populator')


# Get custom table populator orchestration JSON (e.g. to populate GUI content)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_code_matcher_orchestration_json', methods = g_allowed_request_methods)
def get_code_matcher_orchestration_json():
    return epf.get_orchestration_json(orchestrator_type='code_set_match_populator', orchestrator_name=g.req_args['id'])

# Populate code matches in database
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/populate_code_set_matches', methods = g_allowed_request_methods)
def populate_code_set_matches():
    return epf.launch_trackable_populator('code_set_match_populator', 'populate_rel_code_matches')


# *****************************
# *****************************
# OTHER FRONT END AND QUERY HELPER ITEMS
# *****************************
# *****************************

# Get embedder info like name and ID to help query writers
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_embedder_info', methods = g_allowed_request_methods)
def get_embedder_info():
    return epf.get_embedder_info()


# Get replationship populator info like name and ID to help query writers
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_rp_info', methods = g_allowed_request_methods)
def get_rp_info():
    return epf.get_rp_info()


# Get replationship code matcher populator info like name and ID to help query writers
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_rcmp_info', methods = g_allowed_request_methods)
def get_rcmp_info():
    return epf.get_rcmp_info()


# Get expansion styles (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_expansion_styles', methods = g_allowed_request_methods)
def get_expansion_styles():
    return epf.get_expansion_styles()


# Get code set names (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_code_set_names', methods = g_allowed_request_methods)
def get_code_set_names():
    return epf.get_code_set_names()


# Get terminology names (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_terminology_names', methods = g_allowed_request_methods)
def get_terminology_names():
    return epf.get_terminology_names()


# Get LLM names (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_llm_config_names', methods = g_allowed_request_methods)
def get_llm_config_names():
    return epf.get_llm_config_names()


# Get relationship populator IDs and names (e.g. to use in GUI)
@endpoint_meta(access=accc.allow('admin'))
@endpoints.route('/get_relationship_populator_ids_and_names', methods = g_allowed_request_methods)
def get_relationship_populator_ids_and_names():
    return epf.get_relationship_populator_ids_and_names()


# Get relationships given a relationship populator (e.g. to show in GUI)
@endpoint_meta(access=accc.allow('admin', 'standard_user'))
@endpoints.route('/get_rels_of_rel_populator/')
@endpoints.route('/get_rels_of_rel_populator/<rel_populator>', methods = g_allowed_request_methods)
def get_rels_of_rel_populator(rel_populator=None):
    return epf.get_rels_of_rel_populator(rel_populator)


# *****************************
# *****************************
# SQL WHISPERER -- ALWAYS RUN
# to see if anything needs to be done
# or could be enhanced.
# *****************************
# *****************************
epf.run_sql_whisperer()
