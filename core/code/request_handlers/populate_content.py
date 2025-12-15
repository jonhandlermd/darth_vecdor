

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

import app_source.public_repo.core.code.interactors.db_orm as dbom
from app_source.public_repo.core.code.interactors.llm import llmer as llmc
import app_source.public_repo.core.configs.prompt_configs as ppc
from torch import Tensor
import json
import inspect
from typing import Optional

from app_source.public_repo.core.code.interactors.db_orm import (
    enhanced_db_class,
    code_populators_class,
    rels_populator_class,
    str_expansion_set_populator_class,
    code_sets_populator_class,
    manual_content_class,
    rel_code_matches_populator_class,
    custom_table_generators_class
    )
import app_source.public_repo.core.code.interactors.db_orm as db_orm_mod
# import app_source.public_repo.core.code.makers.obj_makers as om
import app_source.public_repo.core.code.interactors.llm as llmm
from app_source.public_repo.core.code.interactors.sent_tran import embedding_class as ec
from app_source.public_repo.core.code.interactors.support.rels_prompt import rels_prompt_class as rspc, placeholders_class as plc
import app_source.public_repo.core.code.utilities.task_manager as tskm
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.configs.llm_configs as llm_configs

# Create the "unset" object -- a "sentinel" value that we will use (per apparently a common Python approach)
# to denote "unset" via using an empty undifferentiated object to differentiate it from None,
# which could be a legitimate value. Unset is not a legitimate value, but use it as a placeholder
# when creating objects to allow leaving the value "unset". I want the ability of the field to exist for purposes
# of auto-complete/hinting, so it has to be present, but also to be unset so an error is generated if you
# use it. This plus EnsureNotUnsetBeforeuse will get us there. I can't use None, because sometimes None is okay.
_unset = object()

# Print status too?
print_also = True # debug.default_d

# Debugging on or off?
g_d =  debug.default_d

class EnsureNotUnsetBeforeUse:
    def __init__(self, name):
        self.name = name  # Store attribute name

    def __get__(self, instance, owner):
        if instance is None:
            raise AttributeError(f"No instance of this class {owner} provided")
            # Do not want to allow access via class
            # return self  # Accessed via class, return descriptor itself
        # Make sure the attribute exists
        if self.name not in instance.__dict__:
            raise AttributeError(f"'{self.name}' must be set before use")
        # Make sure that the attribute value is not "_unset
        if instance.__dict__[self.name] is _unset:
            raise AttributeError(f"'{self.name}' value must be set before use")

        # If we get here, we must be okauy
        return instance.__dict__[self.name]  # Retrieve from instance storage

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value  # Store in instance storage


def do_populator(enhanced_db_obj:enhanced_db_class, args_superset_dict):
    debug.debug(f"Got to do_populator", d=g_d)
    args_superset_dict['enhanced_db_obj'] = enhanced_db_obj
    the_func = args_superset_dict.get('__the_func__', None)
    if not the_func:
        msg = 'No function passed!'
        raise Exception(msg)
    debug.debug(f"do_populator function is {the_func.__name__}", d=g_d)
    the_func_args = get_function_args(the_func, args_superset_dict)
    debug.debug(f"Got function args {the_func_args} for function to do of: {the_func.__name__}", d=g_d)

    # Now run the function with its required args
    debug.debug(f"About to run the function {the_func.__name__}", d=g_d)
    return the_func(**the_func_args)


def populate_custom_table(
        enhanced_db_obj:enhanced_db_class,
        name:str,
        ctg_version:str,
        ctg_code_selector_type:str,
        ctg_code_selector:str,
        ctg_dest_table:str,
        ctg_query:str,
        ctg_code_placeholder:str = 'code',
        ctg_dest_code_field:str = 'code'
        ):
    tskm.emit_status("Making custom table_generator object", print_also=print_also)
    custom_table_generator_obj = custom_table_generators_class(
        enhanced_db_obj,
        name,
        ctg_version,
        ctg_code_selector_type,
        ctg_code_selector,
        ctg_dest_table,
        ctg_query,
        ctg_code_placeholder,
        ctg_dest_code_field
        )

    tskm.emit_status("Making and populating custom table", print_also=print_also)
    dbom.populate_custom_table(
        enhanced_db_obj=enhanced_db_obj
        , ctg_obj=custom_table_generator_obj
        )
    tskm.emit_status("Done making and populating custom table", print_also=print_also)


def populate_terminology(enhanced_db_obj:enhanced_db_class, query:str, terminology:str):

    tskm.emit_status("Making code populators object", print_also=print_also)
    code_populators_obj = code_populators_class(enhanced_db_obj, enhanced_db_obj.params, query, terminology)

    tskm.emit_status("Populating code and strings", print_also=print_also)
    dbom.populate_code_and_strs(code_populators_obj)
    tskm.emit_status("Done populating code and strings", print_also=print_also)

    tskm.emit_status("Populating code summary vectors", print_also=print_also)
    with enhanced_db_obj.session_class() as session:
        code_populators_obj = session.query(code_populators_class).filter(
            code_populators_class.terminology == terminology).first()
        dbom.populate_code_summary_vectors(code_populators_obj)
        tskm.emit_status("Done populating code summary vectors", print_also=print_also)


def populate_code_set(
        enhanced_db_obj:enhanced_db_class
        , code_set_name:str
        , query:str
        , expansion_str_style:str
        , expansion_str_style_version:float
        , llm_config_name:str=llm_configs.default_config_name
        , notes:str=''):
    debug.debug(f"Got to populate code set for set named {code_set_name}", d=g_d)

    # Concoct string expansion variables from above or that are hard-coded to this function.
    # Done here instead of below near other expansion code since I think included in the populator, which
    # we make before executing string expansion.
    if expansion_str_style:
        debug.debug(f"About to concoct expansion string set name for code set {code_set_name}", d=g_d)
        expansion_str_set_name = f'{code_set_name}_code_set_{expansion_str_style}_{expansion_str_style_version}_expansion_set'
        debug.debug(f"Concocted expansion string set name for code set {code_set_name}", d=g_d)

        debug.debug(f"About to make expansion string prompt for code set {code_set_name}", d=g_d)
        # Can use caching if put static part of the question at the beginning.
        expansion_str_prompt = f'''{ppc.prompt_starts['standard']} {ppc.expansion_str_prompts[expansion_str_style]}'''
        debug.debug(f"Made expansion string prompt for code set {code_set_name}", d=g_d)
        # query = pqc.src_data_queries[code_set_name]
        # If populating expansion string set for this code_set's strings,
        # which strings will we need to expand?
        str_selector = code_set_name
        str_selector_type = 'code_set'
    else:
        expansion_str_set_name = ''
        expansion_str_prompt = ''

    # Make code set
    debug.debug(f"About to make code set populator for set named {code_set_name}", d=g_d)
    tskm.emit_status("About to make code set", print_also=print_also)
    q_params = {}
    csp_obj = code_sets_populator_class(enhanced_db_obj, code_set_name, enhanced_db_obj.params, query)
    debug.debug(f"Made code set populator for set named {code_set_name}", d=g_d)
    debug.debug(f"About to actually populate code set for set named {code_set_name}", d=g_d)
    db_orm_mod.populate_code_set(csp_obj)
    debug.debug(f"Done actually populating code set for set named {code_set_name}", d=g_d)
    tskm.emit_status("Done making code set", print_also=print_also)

    if tskm.is_cancelled():
        tskm.emit_status("Cancelled population of code_set.")
        return

    # Don't do any of the upcoming expansion string stuff if not given an expansion string style
    if not expansion_str_style:
        debug.debug(f"Returing because not requested to make expansion set for set named {code_set_name}", d=g_d)
        return

    # If we have an expansion string style but no version, then raise error
    if expansion_str_style_version is None:
        msg = "Expansion string style version cannot be None"
        raise Exception(f"msg")

    #### Now do expansion of code strings
    # Make LLM object
    debug.debug(f"Making LLM object for expanding code set strings for set named {code_set_name}", d=g_d)
    llm_obj = llmm.make_llm_obj(llm_config_name)
    debug.debug(f"Done making LLM object for expanding code set strings for set named {code_set_name}", d=g_d)

    # Now do the expansion
    tskm.emit_status("\n\nPopulating expansion strings\n----------\n", print_also=print_also)

    # Make expansion string populator object
    debug.debug(f"Making expansion string populator for expanding code set strings for set named {code_set_name}", d=g_d)
    exp_str_populators_obj = str_expansion_set_populator_class(
        enhanced_db_obj=enhanced_db_obj,
        name=expansion_str_set_name,
        db_params=enhanced_db_obj.params,
        str_selector=str_selector,
        str_selector_type=str_selector_type,
        llm_params=llm_obj.params,
        prompt=expansion_str_prompt,
        style=expansion_str_style,
        style_version=expansion_str_style_version,
        placeholders=plc()

    )
    debug.debug(f"Done making expansion string populator for expanding code set strings for set named {code_set_name}", d=g_d)
    # Do populate expansion strings using populator object
    debug.debug(f"Actually expanding strings for code set named {code_set_name}", d=g_d)
    dbom.populate_expansion_strs(espo=exp_str_populators_obj, llm_password=llm_obj.password)
    debug.debug(f"Done actually expanding strings for code set named {code_set_name}", d=g_d)

    # Finally populate object's summary vectors
    # Get expansion set populator object
    # sespo = session.query(str_expansion_set_populator_class).filter(
    # str_expansion_set_populator_class.name == expansion_set_populator_name).first()
    # Don't need to get set populator object, because we already have it
    tskm.emit_status("\n\nPopulating code set expansion string summary vectors\n----------\n", print_also=print_also)
    debug.debug(f"About to populate string summary vectors for expansion strings for code set named {code_set_name}", d=g_d)
    dbom.populate_str_summary_vectors(exp_populators_obj=exp_str_populators_obj)
    debug.debug(f"Done populating string summary vectors for expansion strings for code set named {code_set_name}", d=g_d)


def populate_rels(
        enhanced_db_obj:enhanced_db_class
        , rels_populator_name:str
        , rels_prompt_obj:rspc
        , code_selector:str
        , code_selector_type:str
        , expansion_str_style:str
        , expansion_str_style_version:float
        , notes:str
        , llm_obj:llmc
        , mode:str='full_run'
        , test_term:str=''
        ):

    tskm.emit_status("Making rels populator object", print_also=print_also)

    # Make rels populator object
    rels_populator_obj = rels_populator_class(
        enhanced_db_obj=enhanced_db_obj
        , name=rels_populator_name
        , db_params=enhanced_db_obj.params
        , code_selector=code_selector
        , code_selector_type=code_selector_type
        , llm_params=llm_obj.params
        , rels_prompt_obj=rels_prompt_obj
        , notes=notes
        )

    tskm.emit_status("DONE making rels populator object", print_also=print_also)

    # Now populate the relationships
    if mode == 'full_run':
        tskm.emit_status("Doing full run of relationship population", print_also=print_also)
    else:
        tskm.emit_status(f"Testing relationship populator with test term {test_term}", print_also=print_also)
    dbom.populate_rels(
        rpo=rels_populator_obj
        , llm_password=llm_obj.password
        , mode=mode
        , test_term=test_term
        )

    if tskm.is_cancelled() or mode != 'full_run':
        if mode != 'full_run':
            tskm.emit_status("Finished test run. Check terminal/standard output or log for results.")
        return

    # If we need to do expansion strings, then do them
    if expansion_str_style:
        # Can use caching if put static part of the question at the beginning.
        expansion_str_prompt = f'''{ppc.prompt_starts['standard']} {ppc.expansion_str_prompts[expansion_str_style]}'''

        # This will populate expansion strings AND string summary vectors
        populate_expansion_strs(
            enhanced_db_obj=enhanced_db_obj
            , rels_populator_name=rels_populator_name
            , llm_obj=llm_obj
            , expansion_str_prompt=expansion_str_prompt
            , expansion_str_style=expansion_str_style
            , expansion_str_style_version=expansion_str_style_version
            , placeholders=plc()
            )


def populate_expansion_strs(
        enhanced_db_obj:enhanced_db_class
        , rels_populator_name
        , llm_obj
        , expansion_str_prompt
        , expansion_str_style
        , expansion_str_style_version
        , placeholders:plc=plc()
    ):
    # Only populate expansion strings if requested.
    if not expansion_str_style:
        return

    if not expansion_str_prompt:
        expansion_str_prompt = f'''{ppc.prompt_starts['standard']} {ppc.expansion_str_prompts[expansion_str_style]}'''

    # Which strings do we need to expand?
    # TODO: Fix to allow for rel + rels_populator_name
    str_selector = rels_populator_name
    str_selector_type = 'rel'
    expansion_str_set_name = f'{rels_populator_name}_{expansion_str_style}_{expansion_str_style_version}_expansion_set'


    ## Populate expansion string set for these relationships
    tskm.emit_status("\n\nPopulating expansion strings\n----------\n", print_also=print_also)

    # Make expansion string populator object
    exp_str_populators_obj = str_expansion_set_populator_class(
        enhanced_db_obj=enhanced_db_obj,
        name=expansion_str_set_name,
        db_params=enhanced_db_obj.params,
        str_selector=str_selector,
        str_selector_type=str_selector_type,
        llm_params=llm_obj.params,
        prompt=expansion_str_prompt,
        style=expansion_str_style,
        style_version=expansion_str_style_version,
        placeholders=placeholders
    )

    # Do populate expansion strings using populator object
    dbom.populate_expansion_strs(espo=exp_str_populators_obj, llm_password=llm_obj.password)

    # Finally populate relationship object's summary vectors
    tskm.emit_status("\n\nPopulating rel object summary vectors\n----------\n", print_also=print_also)
    populate_str_summary_vectors(expansion_str_set_name, enhanced_db_obj)


def populate_str_summary_vectors(str_expansion_set_populator_name:str, enhanced_db_obj:enhanced_db_class):
    tskm.emit_status("Making expansion strs vectors", print_also=print_also)
    with enhanced_db_obj.session_class() as session:
        # Get expansion set populator object
        sespo = session.query(str_expansion_set_populator_class).filter(str_expansion_set_populator_class.name == str_expansion_set_populator_name).first()

    #### Do populate the vectors -- the enhanced DB will be created from the db_params of the sespo object.
    dbom.populate_str_summary_vectors(exp_populators_obj=sespo)


def populate_manual_content_via_str(
    enhanced_db_obj:enhanced_db_class
    , purpose:str
    , generator_str:str
    , vec_type:str
    ):

    # Make vector
    eco = ec(generator_str, enhanced_db_obj.embedder_execution_obj)
    if vec_type == 'max':
        vec = eco.max_pooling
    elif vec_type == 'mean':
        vec = eco.mean_pooling
    else:
        vec = eco.cls_embedding

    # Make the manual content object, which will also put the content (upsert it) into database
    manual_content_obj = manual_content_class(
        enhanced_db_obj=enhanced_db_obj
        , purpose=purpose
        , generator_str=generator_str
        , generator_type='str'
        , db_params=enhanced_db_obj.params
        , vec=vec
        , vec_type=vec_type
        )


def populate_manual_content_via_query(
    enhanced_db_obj:enhanced_db_class
    , generator_str:str
    ):

    tskm.emit_status("About to do query", print_also=print_also)
    is_success, results = enhanced_db_obj.do_query(
        query=generator_str
        , query_params=None
    )
    tskm.emit_status("Query complete!", print_also=print_also)

    if results:
        # Only need the firstt row
        first_row = results[0]
        # Get fields and field values into a dictionary
        row_dict = first_row._mapping
        for idx, k in enumerate(row_dict.keys()):
            vec = json.loads(row_dict[k])
            # vec = [float(x) for x in vec]
            # print(results[0][idx])
            vec = Tensor(vec)  # results[0][idx]
            vec = Tensor.cpu(vec).flatten()
            generator_type = 'query'
            purpose = k
            vec_type = 'concocted'

            tskm.emit_status("Storing the vector", print_also=print_also)
            manual_content_obj = manual_content_class(enhanced_db_obj=enhanced_db_obj
              , purpose=purpose
              , generator_str=generator_str
              , generator_type=generator_type
              , db_params=enhanced_db_obj.params
              , vec=vec
              , vec_type=vec_type
              )
            tskm.emit_status("Vector stored!", print_also=print_also)


def populate_rel_code_matches(
        enhanced_db_obj:enhanced_db_class
        , match_from_rel_populator_id:str
        , match_from_rel:str
        , match_obj_main_str:bool
        , match_obj_expansion_summary_vec:bool
        , match_code_main_str:bool
        , match_code_other_strs:bool
        , match_code_summary_vec:bool
        , match_code_expansion_summary_vec:bool
        , vec_to_use:str
        , expanion_str_styles_json:str
        , match_to_code_set_name:str
        ):
    debug.debug("Got to populate_rel_code_matches!", d=g_d)

    tskm.emit_status("Making rel_code_matches_populators object", print_also=print_also)
    populators_obj = rel_code_matches_populator_class(
        enhanced_db_obj=enhanced_db_obj
        , db_obj_params=enhanced_db_obj.params
        , match_from_rel_populator_id=match_from_rel_populator_id
        , match_from_rel=match_from_rel
        , match_obj_main_str=match_obj_main_str
        , match_obj_expansion_summary_vec=match_obj_expansion_summary_vec
        , match_code_main_str=match_code_main_str
        , match_code_other_strs=match_code_other_strs
        , match_code_summary_vec=match_code_summary_vec
        , match_code_expansion_summary_vec=match_code_expansion_summary_vec
        , vec_to_use=vec_to_use
        , expanion_str_styles_json=expanion_str_styles_json
        , match_to_code_set_name=match_to_code_set_name
        )

    tskm.emit_status("Populating rel code matches", print_also=print_also)
    dbom.populate_rel_code_matches(populators_obj)
    tskm.emit_status("Done populating rel code matches", print_also=print_also)


def get_function_args(the_function, args_superset):
    # Get the parameter names of the function
    func_keys = inspect.signature(the_function).parameters.keys()
    return {k: v for k, v in args_superset.items() if k in func_keys}


#####################################
# CLASSES
#####################################
class populate_terminology_params:
    query:str = EnsureNotUnsetBeforeUse('query')
    terminology:str = EnsureNotUnsetBeforeUse('terminology')

    def __init__(self, query:Optional[str]=_unset, terminology:Optional[str]=_unset, name:Optional[str]=_unset):
        """
        :param query: Query to get data as a string
        :param terminology: Give a terminology name for these codes
        """
        self.__the_func__ = populate_terminology
        self.query = query
        self.terminology = terminology
        self.name = name


class populate_all_unprocessed_expansion_str_summary_vectors_params:

    def __init__(
            self
            , exp_populators_obj:str_expansion_set_populator_class=None
            , name:Optional[str]=_unset
            ):
        """
        :param exp_populators_obj: String expansion populator object
        """
        self.__the_func__ = dbom.populate_str_summary_vectors
        # __the_func__ = populate_all_unprocessed_expansion_str_summary_vectors
        self.exp_populators_obj = exp_populators_obj
        self.name = name


class populate_code_set_params:
    code_set_name:Optional[str] = EnsureNotUnsetBeforeUse('code_set_name')

    def __init__(
            self
            , code_set_name:Optional[str]=_unset
            , query:Optional[str]=_unset
            , expansion_str_style:str=None
            , expansion_str_style_version:float=None
            , llm_config_name:str=llm_configs.default_config_name
            ):
        """

        :param code_set_name: Provide a name for this code subset
        :param expansion_str_style: Provide the desired key of ppc.expansion_str_prompts
        :param expansion_str_style_version: Version, as a float number, of this expansion string style
        """
        self.__the_func__ = populate_code_set
        self.code_set_name:str = code_set_name
        self.query = query
        self.expansion_str_style:str = expansion_str_style
        self.expansion_str_style_version = expansion_str_style_version
        self.llm_config_name = llm_config_name

class populate_rels_params:
    code_selector_type:Optional[str] = EnsureNotUnsetBeforeUse('code_selector_type')
    code_selector:Optional[str] = EnsureNotUnsetBeforeUse('code_selector')
    # rel_prompt:Optional[str] = EnsureNotUnsetBeforeUse('rel_prompt')
    # rel_for_db:Optional[str] = EnsureNotUnsetBeforeUse('rel_for_db')
    rels_populator_name:Optional[str] = EnsureNotUnsetBeforeUse('rels_populator_name')
    rels_prompt_obj: Optional[rspc] = EnsureNotUnsetBeforeUse('rels_prompt_obj')

    def __init__(self
        , code_selector_type:Optional[str]=_unset
        , code_selector:Optional[str]=_unset
        , rels_populator_name:Optional[str]=_unset
        , rels_prompt_obj:Optional[rspc]=_unset
        # Next line should be the desired key of ppc.expansion_str_prompts
        , expansion_str_style:str=None
        , expansion_str_style_version:float=1.0000
        # , retry_prompt:str=None # Not used
        , notes:str=''
        , llm_config_name:str=llm_configs.default_config_name
        ):
        """

        :param code_selector_type: allowed values: code_set or query
        :param code_selector: code set name or the SQL of the query
        :param rels_populator_name: Rels populator object name, and this name will be used as part of the expansion string set name.
        :param rels_prompt_obj: Rels object holding rel objects.
        :param expansion_str_style: desired key of ppc.expansion_str_prompts
        :param expansion_str_style_version: Version, as a float number, of this expansion string style
        :param notes: Any notes you want to provide regarding this relationship.
        :param llm_config_name: Name of the LLM config.
        """
        self.__the_func__ = populate_rels
        self.code_selector_type:str = code_selector_type
        self.code_selector:str = code_selector
        self.rels_populator_name:str = rels_populator_name
        self.rels_prompt_obj:rspc = rels_prompt_obj
        # Next line should be the desired key of ppc.expansion_str_prompts
        self.expansion_str_style:str = expansion_str_style
        self.expansion_str_style_version:float = expansion_str_style_version
        self.notes:str = notes
        self.llm_obj:llmc = llmm.make_llm_obj(llm_config_name)


class populate_custom_table_params:
    name: Optional[str] = EnsureNotUnsetBeforeUse('name')
    ctg_version: Optional[str] = EnsureNotUnsetBeforeUse('ctg_version')
    code_selector_type: Optional[str] = EnsureNotUnsetBeforeUse('code_selector_type')
    code_selector:Optional[str] = EnsureNotUnsetBeforeUse('code_selector')
    ctg_dest_table: Optional[str] = EnsureNotUnsetBeforeUse('ctg_dest_table')
    ctg_query: Optional[str] = EnsureNotUnsetBeforeUse('ctg_query')
    ctg_code_placeholder: Optional[str] = EnsureNotUnsetBeforeUse('ctg_code_placeholder')
    ctg_dest_code_field:Optional[str] = EnsureNotUnsetBeforeUse('ctg_dest_code_field')

    def __init__(
        self
        , name: Optional[str] = _unset
        , ctg_version: Optional[str] = _unset
        , code_selector_type: Optional[str] = _unset
        , code_selector:Optional[str]=_unset
        , ctg_dest_table: Optional[str] = _unset
        , ctg_query: Optional[str] = _unset
        , ctg_code_placeholder: Optional[str] = _unset
        , ctg_dest_code_field: Optional[str] = _unset
        ):
        self.__the_func__ = populate_custom_table
        self.name = name
        self.ctg_version = ctg_version
        self.code_selector_type = code_selector_type
        self.code_selector = code_selector
        self.ctg_dest_table = ctg_dest_table
        self.ctg_query = ctg_query
        self.ctg_code_placeholder = ctg_code_placeholder
        self.ctg_dest_code_field = ctg_dest_code_field


class populate_manual_content_params:
    generator_str:Optional[str] = EnsureNotUnsetBeforeUse('generator_str')
    generator_type:Optional[str] = EnsureNotUnsetBeforeUse('generator_type')
    purpose:Optional[str] = EnsureNotUnsetBeforeUse('purpose')
    vec_type:Optional[str] = EnsureNotUnsetBeforeUse('vec_type')
    def __init__(
            self
            , generator_str:Optional[str]=_unset
            , generator_type:Optional[str]=_unset
            , purpose:Optional[str]=_unset
            , vec_type:Optional[str]=_unset
            ):
        """

        :param generator_str: String that will be used to generate a vector that represents that string
        :param generator_type: Type of generator string, can be str for string or query for or a SQL query.
        :param purpose: What is the purpose of this content? Think of this like the name to give this content.
        :param vec_type: What kind of vector is it? Options are max, mean, or cls
        """
        self.generator_str = generator_str
        self.generator_type = generator_type
        self.purpose = purpose
        self.vec_type = vec_type


class populate_manual_content_via_query_params(populate_manual_content_params):
    __the_func__ = populate_manual_content_via_query

class populate_manual_content_via_str_params(populate_manual_content_params):
    __the_func__ = populate_manual_content_via_str


class populate_rel_code_matches_params:
    match_from_rel_populator_id:Optional[str] = EnsureNotUnsetBeforeUse('match_from_rel_populator_id')
    name: Optional[str] = EnsureNotUnsetBeforeUse('name')
    match_from_rel:Optional[str] = EnsureNotUnsetBeforeUse('match_from_rel')
    match_obj_main_str:Optional[bool] = EnsureNotUnsetBeforeUse('match_obj_main_str')
    match_obj_expansion_strs:Optional[bool] = EnsureNotUnsetBeforeUse('match_obj_expansion_strs')
    match_code_main_str:Optional[bool] = EnsureNotUnsetBeforeUse('match_code_main_str')
    match_code_other_strs:Optional[bool] = EnsureNotUnsetBeforeUse('match_code_other_strs')
    match_code_expansion_strs:Optional[bool] = EnsureNotUnsetBeforeUse('match_code_expansion_strs')
    vec_to_use:Optional[str] = EnsureNotUnsetBeforeUse('vec_to_use')
    expanion_str_styles_json:Optional[str] = EnsureNotUnsetBeforeUse('expanion_str_styles_json')
    match_to_code_set_name:Optional[str] = EnsureNotUnsetBeforeUse('match_to_code_set_name')

    def __init__(self
        , name:Optional[str]=_unset
        , match_from_rel_populator_id:Optional[str]=_unset
        , match_from_rel:Optional[str]=_unset
        , match_obj_main_str:Optional[bool]=_unset
        , match_obj_expansion_strs:Optional[bool]=_unset
        , match_code_main_str:Optional[bool]=_unset
        , match_code_other_strs:Optional[bool]=_unset
        , match_code_expansion_strs:Optional[bool]=_unset
        , vec_to_use:Optional[str]=_unset
        , expanion_str_styles_json: Optional[str] = _unset
        , match_to_code_set_name: Optional[str] = _unset
        ):

        self.__the_func__ = populate_rel_code_matches
        self.name = name
        self.match_from_rel_populator_id = match_from_rel_populator_id
        self.match_from_rel = match_from_rel
        self.match_obj_main_str = match_obj_main_str
        self.match_obj_expansion_strs = match_obj_expansion_strs
        self.match_code_main_str = match_code_main_str
        self.match_code_other_strs = match_code_other_strs
        self.match_code_expansion_strs = match_code_expansion_strs
        self.vec_to_use = vec_to_use
        self.expanion_str_styles_json = expanion_str_styles_json
        self.match_to_code_set_name = match_to_code_set_name