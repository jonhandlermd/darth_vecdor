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

# External module imports
from flask import g
import json as json
import copy

# This programs modules
import app_source.public_repo.core.configs.other_configs as oc
import app_source.public_repo.core.code.utilities.web_request_utils as wru
import app_source.public_repo.core.code.utilities.task_manager as tskm
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.code.request_handlers.front_end_list_getter as felg
import app_source.public_repo.core.code.request_handlers.json_to_populator as jtp
from app_source.public_repo.core.code.interactors.db_orm import (
    enhanced_db_class,
    populator_orchestrations_class as poc
)
import app_source.public_repo.core.code.request_handlers.populate_content as rhpc
import app_source.public_repo.core.configs.orm_db_configs as odc

# Turn on/off debugging
g_d = debug.default_d


def get_orchestration_names(orchestrator_type:str):

    # Set up variables to connect to DB
    enhanced_db_obj = set_up_db()
    results = felg.get_orchestrations(enhanced_db_obj=enhanced_db_obj, orchestrator_type=orchestrator_type)
    return wru.concoct_response('', results)


def get_orchestration_json(orchestrator_type:str, orchestrator_name:str):
    # Set up variables to connect to DB
    enhanced_db_obj = set_up_db()
    results = felg.get_orchestration(enhanced_db_obj=enhanced_db_obj, orchestrator_type=orchestrator_type, orchestrator_name=orchestrator_name)
    return wru.concoct_response('', results)


def launch_trackable_populator(populator_type:str, populator:str):
    debug.debug(f"Got to launch trackable populator with populator type of: {populator_type}; and populator of: {populator}", d=g_d)
    #### Check for requirements
    err = wru.check_reqs(['tjson'])
    if err:
        debug.debug("Did not get tjson submitted", d=g_d)
        return wru.concoct_response(err, '')

    #### Handle differently depending upon if we got inputs as an qrgument or not.
    try:
        enhanced_db_obj = set_up_db()
    except Exception as e:
        msg = f'ERROR: Could not set up the database connection.'
        debug.log(__file__, msg)
        return wru.concoct_response(msg, '')
    debug.debug("DB is set up", d=g_d)
    orig_json = 'Unassigned JSON'
    try:
        orig_json = g.req_args['tjson']
        orig_obj = json.loads(orig_json)
        debug.debug("tjson is loaded as object", d=g_d)
    except Exception as e:
        msg = f"Could not parse the JSON you submitted {orig_json}. Got exception {e}"
        debug.log(__file__, msg)
        return wru.concoct_response(f'ERROR: {msg}', '')

    try:
        #### Convert JSON to input dictionary
        if populator == 'populate_rels':
            nobj = jtp.json_loaded_obj_to_rel_populator(orig_obj)
        elif populator == 'populate_custom_table':
            nobj = jtp.json_loaded_obj_to_custom_table_generator(orig_obj)
        elif populator == 'populate_code_set':
            debug.debug("about to load tjson as code set populator", d=g_d)
            nobj = jtp.json_loaded_obj_to_code_set_populator(orig_obj)
            debug.debug("loaded tjson as code set populator", d=g_d)
        elif populator == 'populate_terminology':
            nobj = jtp.json_loaded_obj_to_terminology_populator(orig_obj)
        elif populator == 'populate_rel_code_matches':
            nobj = jtp.json_loaded_obj_to_rel_code_matches_populator(orig_obj)
        elif populator == 'populate_all_unprocessed_expansion_str_summary_vecs':
            nobj = jtp.all_unprocessed_expansion_str_summary_vectors_populator()

        else:
            raise Exception("Unknown 'populator' param")
    except Exception as e:
        msg = f'ERROR: Could not convert the JSON to {populator} populator: {orig_json}\n\n GOT ERROR: {e}'
        debug.log(__file__, msg)
        return wru.concoct_response(msg, '')

    # If we are only looking at the object, then just return it in printable format.
    mode = orig_obj.get('mode', "full_run")
    if mode == "see_obj_only" or mode == "see_obj_and_resp":
        debug.debug("The prompt object is:\n{ret}", d=g_d)
        ret = json.dumps(nobj.rels_prompt_obj.prompt, indent=2)

        # We are done if only seeing the object
        if mode == "see_obj_only":
            print(ret)
            return wru.concoct_response('', {'obj': ret})

    save_json = 'Unassigned save JSON'
    try:
        # Save these configs
        debug.debug(f"About to save these configs populator type {populator_type} and name {nobj.name}", d=g_d)
        # First though, remove test configs if they exist
        save_obj = copy.deepcopy(orig_obj)
        if 'test_term' in orig_obj.keys():
            del save_obj['test_term']
        save_json = json.dumps(save_obj)
        poc(enhanced_db_obj=enhanced_db_obj, po_type=populator_type, po_name=nobj.name, po_content=save_json)
    except Exception as e:
        msg = f'ERROR: Could not save these configs {save_json}\n\n Error was {e}.'
        debug.log(__file__, msg)
        return wru.concoct_response(msg, '')

    try:
        # add .schema to args_superset_dict because assume we are dealing with a Pydantic BaseModel object
        debug.debug(f"Launching task to do populator", d=g_d)
        task_id = tskm.launch_task(
            task_function=rhpc.do_populator
            , enhanced_db_obj=enhanced_db_obj
            , args_superset_dict=vars(nobj)
        )
        debug.debug("Task launched!", d=g_d)
    except Exception as e:
        msg = f'ERROR: Could not launch task, got exception {e}.'
        debug.log(__file__, msg)
        return wru.concoct_response(msg, '')

    # Close the session and exit
    debug.debug("All done!", d=g_d)

    #### Return response
    return wru.concoct_response('', {'task_id': task_id})

def set_up_db()->enhanced_db_class:
    return enhanced_db_class(
        embedder_meta_src=odc.default_embedder_meta_src,
        embedder_meta_src_location=odc.default_embedder_meta_src_location
    )

