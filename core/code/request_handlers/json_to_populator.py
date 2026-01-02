

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

import json
import copy
import traceback

import app_source.public_repo.core.code.request_handlers.populate_content as pc
from app_source.public_repo.core.code.interactors.db_orm import adjudicator_type_class
from app_source.public_repo.core.code.interactors.support.rels_prompt import rels_prompt_class as rspc, rel_prompt_class as rpc, beceptivity_src_type_class as bstc, placeholders_class as ppc
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.configs.llm_configs as llm_configs_mod
import app_source.public_repo.core.configs.prompt_configs as prompt_configs_mod

# Debugging on/off
g_d = debug.default_d


def convert_to_bool_prn(tdict, tkey):
    if (str(tdict[tkey]).lower()) in ['no', 'false', '0']:
        tdict[tkey] = False
    else:
        tdict[tkey] = True

def convert_to_default_prn(tdict, tkey, default_val, convert_to_numeric=False, is_float=False):
    if tkey not in tdict or not tdict[tkey]:
        tdict[tkey] = default_val
    if convert_to_numeric:
        tdict[tkey] = convert_to_num_or_zero_prn(tdict, tkey, is_float=is_float)
    return tdict[tkey]

def convert_to_num_or_zero_prn(tdict, tkey, is_float=False):
    if not tdict[tkey]:
        if not is_float:
            tdict[tkey] = 0
        else:
            tdict[tkey] = 0.0
    else:
        if not is_float:
            tdict[tkey] = int(tdict[tkey])
        else:
            tdict[tkey] = float(tdict[tkey])
    return tdict[tkey]


def convert_to_none_prn(tdict, tkey):
    # This handles not having the tkey, empty string or list or dict or None all lead to None
    if tkey not in tdict or not tdict[tkey]:
        tdict[tkey] = None
    else:
        tdict[tkey] = tdict[tkey]
    return tdict[tkey]


def json_loaded_obj_to_terminology_populator(obj_loaded_from_json):
    # Make base object
    # bobj = json.loads(json_txt)
    bobj = copy.deepcopy(obj_loaded_from_json)
    rhs_name = f"populate_terminology_{bobj['base_name']}"
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_terminology_params()
    nobj.name = rhs_name
    nobj.query = bobj['query']
    nobj.terminology = bobj['terminology']
    return copy.deepcopy(nobj)

def all_unprocessed_expansion_str_summary_vectors_populator():
    # Make base object
    rhs_name = f"populate_all_unprocessed_expansion_str_summary_vectors"
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_all_unprocessed_expansion_str_summary_vectors_params()
    nobj.name = rhs_name
    nobj.exp_populators_obj = None
    return copy.deepcopy(nobj)


def json_loaded_obj_to_code_set_populator(obj_loaded_from_json):
    # Make base object
    # bobj = json.loads(json_txt)
    bobj = copy.deepcopy(obj_loaded_from_json)

    rhs_name = f"populate_code_set_{bobj['base_name']}"
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_code_set_params(llm_config_name=bobj.get('llm_config_name', llm_configs_mod.default_config_name))
    nobj.code_set_name = bobj['base_name']
    nobj.query = bobj['query']
    nobj.name = bobj['base_name']
    nobj.expansion_str_style = bobj['expansion_str_style']
    nobj.expansion_str_style_version = bobj['expansion_str_style_version']
    return copy.deepcopy(nobj)


def json_loaded_obj_to_custom_table_generator(obj_loaded_from_json):
    # Make base object
    # bobj = json.loads(json_txt)
    bobj = copy.deepcopy(obj_loaded_from_json)

    # If needed (i.e. because no value provided), convert to default values
    ctg_dest_code_field = convert_to_default_prn(bobj, 'ctg_dest_code_field','')
    ctg_code_placeholder = convert_to_default_prn(bobj, 'ctg_code_placeholder','')

    # Now populate object
    base_name = f"{bobj['name']}_v{bobj['ctg_version']}"
    rhs_name = f'populate_rels_{base_name}'
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_custom_table_params()
    nobj.name = base_name
    nobj.ctg_version = bobj['ctg_version']
    nobj.ctg_dest_table = bobj['ctg_dest_table']
    nobj.ctg_query = bobj['ctg_query']
    nobj.ctg_code_selector_type = bobj['ctg_code_selector_type']
    nobj.ctg_code_selector = bobj['ctg_code_selector']
    nobj.ctg_code_placeholder = ctg_code_placeholder
    nobj.ctg_dest_code_field = ctg_dest_code_field
    return copy.deepcopy(nobj)


def json_loaded_obj_to_rel_populator(obj_loaded_from_json):

    d = g_d

    # Make base object
    # bobj = json.loads(json_txt)
    bobj = copy.deepcopy(obj_loaded_from_json)
    version = bobj['version']
    base_name = f"{bobj['base_name']}_v{bobj['version']}"
    rhs_name = f'populate_rels_{base_name}'
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_rels_params(llm_config_name=bobj.get('llm_config_name', llm_configs_mod.default_config_name))

    nobj.code_selector_type = bobj['code_selector_type']
    nobj.code_selector = bobj['code_selector']
    nobj.rels_populator_name = base_name
    nobj.name = nobj.rels_populator_name
    nobj.expansion_str_style = convert_to_default_prn(bobj, 'expansion_str_style', None)
    nobj.expansion_str_style_version = bobj.get('expansion_str_style_version', '001')
    nobj.notes = bobj['notes']
    nobj.mode = bobj['mode']
    nobj.test_term = bobj.get('test_term', None)

    # Set up relationship set object
    rp = None
    ppo = ppc()
    rp = rspc(
        name = rhs_name,
        rels = [],
        rels_case_change = bobj['rels_case_change'],
        # TODO: Check if this will work (next line)!
        can_llm_output_json = nobj.llm_obj.llm_obj.can_output_json,
        llm_str_output_separator_name = convert_to_default_prn(bobj, 'llm_str_output_separator_name', llm_configs_mod.default_llm_str_output_separator_name),
        llm_str_output_response_surrounder = bobj.get('llm_str_output_response_surrounder', llm_configs_mod.llm_str_output_response_surrounder),
        instructions = convert_to_default_prn(bobj, 'instructions', prompt_configs_mod.default_instructions),
        beceptivity_src_type = convert_to_default_prn(bobj, 'beceptivity_src_type', None),
        beceptivity_instructions = convert_to_default_prn(bobj, 'beceptivity_instructions', prompt_configs_mod.default_beceptivity_instructions),
        # Even though I believe next two are handled as a string because it's just part of the prompt, I will convert to numeric just in case needed as one.

        beceptivity_max_val = convert_to_default_prn(bobj, 'beceptivity_max_val', prompt_configs_mod.default_beceptivity_max_val, convert_to_numeric=True, is_float=True),
        beceptivity_cutoff = convert_to_default_prn(bobj, 'beceptivity_cutoff', prompt_configs_mod.default_beceptivity_category_cutoff, convert_to_numeric=True, is_float=True),
        beceptivity_val_if_none = convert_to_default_prn(bobj,'beceptivity_val_if_none', prompt_configs_mod.default_beceptivity_val_if_none, convert_to_numeric=True, is_float=True),
        beceptivity_name = convert_to_default_prn(bobj, 'beceptivity_name', prompt_configs_mod.default_beceptivity_name),
        placeholders = ppc()
        )

    for rel_part in bobj['rels']:
        # If we don't have a prompt value, then it's not a legit rel.
        if 'rel_prompt' not in rel_part or not rel_part['rel_prompt']:
            msg = f"Skipping rel part {rel_part} because it has no rel_prompt."
            debug.debug(msg, d=d)
            continue

        if 'get_more_beceptive_content_prompt' not in rel_part:
            rel_part['get_more_beceptive_content_prompt'] = ''

        if 'is_assume_adequate_on_max_loop' not in rel_part:
            rel_part['is_assume_adequate_on_max_loop'] = 'True'

        if 'max_beceptivity_loops' not in rel_part:
            rel_part['max_beceptivity_loops'] = '1'

        rel = f"{rel_part['rel']}_v{version}"

        new_rel = None
        try:

            # Convert what was submitted to proper format, or default.
            convert_to_num_or_zero_prn(rel_part, 'are_you_sure_count', is_float=False)
            convert_to_num_or_zero_prn(rel_part, 'are_you_sure_val_if_error', is_float=True)
            convert_to_num_or_zero_prn(rel_part, 'min_acceptable_beceptivity', is_float=True)
            convert_to_num_or_zero_prn(rel_part, 'max_beceptivity_loops', is_float=False)
            convert_to_default_prn(rel_part, 'are_you_sure_adjudicator', 'vote')
            convert_to_bool_prn(rel_part, 'is_no_write')
            convert_to_bool_prn(rel_part, 'is_multi_resp')
            convert_to_bool_prn(rel_part, 'is_assume_adequate_on_max_loop')
            convert_to_none_prn(rel_part, 'resp_dict')

            # Resp dict needs to be converted to a dict if it is JSON for a string
            # It definitely exists because of the convert_to_none_prn above
            if isinstance(rel_part['resp_dict'], str):
                cleaned_resp_dict = rel_part['resp_dict'].strip()
                if cleaned_resp_dict:
                    try:
                        rel_part['resp_dict'] = json.loads(cleaned_resp_dict)
                    except Exception as e:
                        msg = f"Got exception trying to json.loads the resp_dict {rel_part['resp_dict']} for rel {rel}. Exception was: {e}"
                        debug.log(__file__, msg)
                        raise Exception
                else:
                    rel_part['resp_dict'] = None

            new_rel = rpc(
                rel=rel
                , rel_prompt=rel_part['rel_prompt']
                , is_multi_resp=rel_part['is_multi_resp']
                , min_acceptable_beceptivity=rel_part['min_acceptable_beceptivity']
                , is_no_write=rel_part['is_no_write']
                , resp_dict=rel_part['resp_dict']
                , are_you_sure_prompt=rel_part['are_you_sure_prompt']
                , are_you_sure_adjudicator=adjudicator_type_class(rel_part['are_you_sure_adjudicator'])
                , are_you_sure_count=rel_part['are_you_sure_count']
                , are_you_sure_val_if_error=rel_part['are_you_sure_val_if_error']
                , get_more_beceptive_content_prompt=rel_part['get_more_beceptive_content_prompt']
                , is_assume_adequate_on_max_loop = rel_part['is_assume_adequate_on_max_loop']
                , max_beceptivity_loops = rel_part['max_beceptivity_loops']
                )
        except Exception as e:
            msg = f"Got exception doing new rel {rel}. Exception was: {e}"
            debug.log(__file__, msg)
            raise Exception

        # Add it -- the add function will add a deepcopy of new_rel
        rp.add(new_rel)

        # Null out new_rel just to be sure nothing carried forward.
        new_rel = None
    debug.debug("Done looping relparts", d=d)
    nobj.rels_prompt_obj = copy.deepcopy(rp)
    rp = None
    return copy.deepcopy(nobj)


def json_loaded_obj_to_rel_code_matches_populator(obj_loaded_from_json):
    # Make base object
    # bobj = json.loads(json_txt)
    bobj = copy.deepcopy(obj_loaded_from_json)

    convert_to_bool_prn(bobj, 'match_obj_main_str')
    convert_to_bool_prn(bobj, 'match_obj_expansion_summary_vec')
    convert_to_bool_prn(bobj, 'match_code_main_str')
    convert_to_bool_prn(bobj, 'match_code_other_strs')
    convert_to_bool_prn(bobj, 'match_code_summary_vec')
    convert_to_bool_prn(bobj, 'match_code_expansion_summary_vec')

    # ORIGINAL
    '''
    {"base_name":"diff_dx_snm_core_str_to_icd10_3_5","match_from_rel_populator_id":"189902e5-24ef-4f4e-8c92-1a867fa2df49","match_from_rel":"has_diff_dx_of_v001","match_obj_main_str":"Yes","match_obj_expansion_strs":"Yes","match_code_main_str":"Yes","match_code_other_strs":"Yes","match_code_expansion_strs":"Yes","vec_to_use":"cls","expanion_str_styles":["simple"],"match_to_code_set_name":"umls_icd10_3_5","rels":[]}
    '''

    # NEW
    '''
{"base_name": "diff_dx_snm_core_str_to_icd10_3_5",
"match_from_rel_populator_id": "189902e5-24ef-4f4e-8c92-1a867fa2df49", "match_from_rel": "has_diff_dx_of_v001",
"match_obj_main_str": "Yes", "match_obj_expansion_summary_vec": "Yes", "match_code_main_str": "Yes",
"match_code_other_strs": "No", "match_code_summary_vec" = "Yes", "match_code_expansion_summary_vec": "Yes", "vec_to_use": "cls",
"expanion_str_styles": ["simple"], "match_to_code_set_name": "umls_icd10_3_5", "rels": []}
     '''
    '''
    {
    "base_name": "diff_dx_snm_core_str_to_icd10_3_5"
    , "match_from_rel_populator_id": "189902e5-24ef-4f4e-8c92-1a867fa2df49"
    , "match_from_rel": "has_diff_dx_of_v001"
    , "match_obj_main_str": "Yes"
    , "match_obj_expansion_summary_vec": "Yes"
    , "match_code_main_str": "Yes"
    , "match_code_other_strs": "No"
    , "match_code_summary_vec": "Yes"
    , "match_code_expansion_summary_vec": "Yes"
    , "vec_to_use": "cls"
    , "expanion_str_styles": ["simple"]
    , "match_to_code_set_name": "umls_icd10_3_5"
    , "rels": []
    }
        '''

    rhs_name = f"populate_rel_code_matches_{bobj['base_name']}"
    # Make new object
    nobj = None # to be sure
    nobj = pc.populate_rel_code_matches_params()
    nobj.name = rhs_name
    nobj.match_from_rel_populator_id = bobj['match_from_rel_populator_id']
    nobj.match_from_rel = bobj['match_from_rel']
    nobj.match_obj_main_str = bobj['match_obj_main_str']
    nobj.match_obj_expansion_summary_vec = bobj['match_obj_expansion_summary_vec']
    nobj.match_code_main_str = bobj['match_code_main_str']
    nobj.match_code_other_strs = bobj['match_code_other_strs']
    nobj.match_code_summary_vec = bobj['match_code_summary_vec']
    nobj.match_code_expansion_summary_vec = bobj['match_code_expansion_summary_vec']
    nobj.vec_to_use = bobj['vec_to_use']
    nobj.expanion_str_styles_json = json.dumps(bobj['expanion_str_styles'])
    nobj.match_to_code_set_name = bobj['match_to_code_set_name']
    debug.debug("Completed build of nobj for json_loaded_obj_to_rel_code_matches_populator", d=g_d)
    return copy.deepcopy(nobj)

# json_to_rel_populator(tjson)
# exit()