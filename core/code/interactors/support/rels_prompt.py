

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

import pprint
import copy
from pydantic import BaseModel, Field
import pydantic
from typing import Any, Dict, Type, Optional
import textwrap

from app_source.public_repo.core.code.interactors.support.enums import adjudicator_type_class, beceptivity_src_type_class, case_change
import app_source.public_repo.core.code.utilities.arg_and_serializer_utils as su
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.code.utilities.error_avoider as ea
import app_source.public_repo.core.configs.prompt_configs as pc
import app_source.public_repo.core.configs.llm_configs as llm_configs

class placeholders_class:

    def __init__(self
            , concept:str="<<<concept>>>"
            , beceptivity:str="<<<beceptivity>>>"
            , subj_str:str="<<<subj_str>>>"
            , obj_str:str="<<<obj_str>>>"
            , orig_prompt:str="<<<orig_prompt>>>"
            ):
        self.concept = concept
        self.beceptivity = beceptivity
        self.subj_str = subj_str
        self.obj_str = obj_str
        self.orig_prompt = orig_prompt


class rel_prompt_class:

    def __init__(self
            , rel:str
            , rel_prompt:str
            , is_multi_resp:bool=True
            , min_acceptable_beceptivity:float=0.0
            , is_no_write=False
            , resp_dict=None
            , are_you_sure_prompt=None
            , are_you_sure_adjudicator=ea.return_str_whether_enum_or_str(adjudicator_type_class.vote.value, adjudicator_type_class)
            , are_you_sure_count=0
            , are_you_sure_val_if_error=1.0
            , expansion_str_style=None
            , expansion_str_style_version='001'
            , get_more_beceptive_content_prompt=None
            , is_assume_adequate_on_max_loop=True
            , max_beceptivity_loops=1
            ):
        self.rel = rel
        self.rel_prompt = rel_prompt
        self._is_multi_resp = is_multi_resp
        self.min_acceptable_beceptivity = min_acceptable_beceptivity
        self.is_no_write = is_no_write
        self.are_you_sure_prompt = are_you_sure_prompt
        self.are_you_sure_adjudicator = ea.return_str_whether_enum_or_str(are_you_sure_adjudicator, adjudicator_type_class)
        self.are_you_sure_count = are_you_sure_count
        self.are_you_sure_val_if_error = are_you_sure_val_if_error
        # Make sure we got a legit combo of are_you_sure items
        if self.are_you_sure_count is not None and self.are_you_sure_count > 0 and (not self.are_you_sure_adjudicator or not self.are_you_sure_prompt):
            msg = f"Problem with are_you_sure_count because we were asked to do are_you_sure via are_you_sure_count not being None or 0, but either adjudicator or prompt not set."
            debug.log(__file__, msg)
            raise Exception(msg)
        self.expansion_str_style = expansion_str_style
        self.expansion_str_style_version = expansion_str_style_version
        self.get_more_beceptive_content_prompt = get_more_beceptive_content_prompt
        self.is_assume_adequate_on_max_loop = is_assume_adequate_on_max_loop
        self.max_beceptivity_loops = max_beceptivity_loops

        # This is a dictionary that converts the response, like in the form of a number, to the
        # corresponding text. Why would we do this? Well, let's say I wanted to have the
        # thing return a number, but I want that mapped to a string to be returned. This
        # can happen because I have found that, sometimes, when you ask it to pick among
        # a list of items, it may not always reliably return the exact string, or it performs
        # less well than when you assign the desired a number (or other key).
        # Not used if set to None.
        if resp_dict is not None:
            if isinstance(resp_dict, dict):
                self.resp_dict = copy.deepcopy(resp_dict)
            elif isinstance(resp_dict, str):
                cleaned_resp_dict = resp_dict.strip()
                if cleaned_resp_dict:
                    # If we got a string, assume it is a JSON string and try to load it
                    try:
                        self.resp_dict = su.jsonpickle_loads(cleaned_resp_dict)
                    except Exception as e:
                        msg = f"Error loading resp_dict from string: {e}"
                        debug.log(__file__, msg)
                        raise ValueError(msg)
                else:
                    # If we got an empty string, set resp_dict to None
                    self.resp_dict = None
                msg = f"resp_dict must be a dictionary or a JSON string, but got {type(resp_dict)}"
                debug.log(__file__, msg)
                raise ValueError(msg)
        # If we got a None, then we will set it to None.
        else:
            self.resp_dict = None


        # Make beceptivity retry prompt, but it will be populated later, automatically
        self._beceptivity_retry_prompt = None


    @property
    def is_multi_resp(self):
        return self._is_multi_resp

    @is_multi_resp.setter
    def is_multi_resp(self, value):
        if value and self.resp_dict is not None:
            raise ValueError("resp_dict must be None if is_multi_resp is True")
        self._is_multi_resp = value

    @property
    def resp_dict(self):
        return self._resp_dict

    @resp_dict.setter
    def resp_dict(self, value:dict):
        if value is not None and not isinstance(value, dict):
            raise ValueError("resp_dict Value must be None or a dictionary")
        if self.is_multi_resp and value is not None:
            msg = f"{self.rel} is_multi_resp is True, so resp_dict must be None but it is {value}."
            raise ValueError(msg)
        self._resp_dict = copy.deepcopy(value)


class rels_prompt_class:

    def __init__(
            self
            , name:str
            , rels:list[rel_prompt_class]=None
            , rels_case_change:str=ea.return_str_whether_enum_or_str(pc.response_case_change, case_change)
            , can_llm_output_json:bool=False
            , llm_str_output_separator_name:str=llm_configs.default_llm_str_output_separator_name # or "pipe"
            , llm_str_output_response_surrounder:str=llm_configs.llm_str_output_response_surrounder
            , instructions=pc.default_instructions
            , beceptivity_src_type:str=ea.return_str_whether_enum_or_str(beceptivity_src_type_class.llm_response.value, beceptivity_src_type_class)
            , beceptivity_instructions:str=pc.default_beceptivity_instructions
            , beceptivity_max_val:float=pc.default_beceptivity_max_val
            , beceptivity_cutoff:float=pc.default_beceptivity_category_cutoff
            , beceptivity_val_if_none:float = 0.0
            , beceptivity_name:str=pc.default_beceptivity_name
            , placeholders:placeholders_class=None
            ):
        self.name = name
        self.can_llm_output_json = can_llm_output_json
        if rels is None:
            rels = []
        self.rels: list[rel_prompt_class] = rels
        self.rels = rels
        self.rels_case_change = rels_case_change
        self.can_llm_output_json = can_llm_output_json
        self.llm_str_output_separator_name = llm_str_output_separator_name
        self.llm_str_output_response_surrounder = llm_str_output_response_surrounder
        self.instructions = instructions

        # Beceptivity items will to all beceptivity retry prompts
        self.beceptivity_src_type = beceptivity_src_type
        self.beceptivity_instructions = beceptivity_instructions
        self.beceptivity_max_val = beceptivity_max_val
        self.beceptivity_cutoff = beceptivity_cutoff
        self.beceptivity_val_if_none = beceptivity_val_if_none
        self.beceptivity_name = beceptivity_name

        # Rest of properties to set
        if placeholders is None:
            placeholders = placeholders_class()
        self.placeholders:placeholders_class = placeholders
        self._params = su.jsonpickle_dumps(self)

    def add(self, rel:rel_prompt_class):
        if self.rels is None:
            self.rels = []
        self.rels.append(copy.deepcopy(rel))
        # self.create_pydantic_model_and_prompt()
        # self._params = su.jsonpickle_dumps(self)
        self.params # I hope this owrks like it should

    @property
    def params(self):
        self.prompt # I hope this works like it should to regenerate prompt
        self._params = su.jsonpickle_dumps(self)
        return self._params

    @property
    def prompt(self):
        prompt, model = self.create_pydantic_model_and_prompt()
        self._prompt = prompt
        return self._prompt

    @property
    def model(self):
        prompt, model = self.create_pydantic_model_and_prompt()
        # I think I did not make self._model because I think it didn't work with jsonpickle.
        return model

    def create_pydantic_model_and_prompt(self):

        # Make fields we need for making model, and make prompt
        fields, prompt = self.create_layered_model_and_prompt()

        # Make the model
        model = pydantic.create_model('responses_property_model', **fields)

        # All done
        return prompt, model


    def create_layered_model_and_prompt(self):

        # Each pydantic "field" is a relationship
        fields = {}

        # Will we need beceptivity instructions? Assume False for now, will update later.
        need_beceptivity_instructions = False

        # Begin concocting prompt, but keep prompt start because we will use it for beceptivity subprompts
        prompt = textwrap.dedent(f'''{self.instructions}
                {self.placeholders.beceptivity}
                ''')

        # Describe response format depending on LLM capability
        if self.can_llm_output_json:
            prompt += f'''Please provide results as a json dictionary having the following keys and values:\n'''
        else:
            prompt += f'''\nFor each requested response, put the response on a single line, and surround the response at the beginning of the line and the end of the line with the characters on the next line:\n{self.llm_str_output_response_surrounder}\n'''

        # Finish the start of the prompt
        prompt += 'My request is:\n'

        # Now populate the fields
        for idx, rel_obj in enumerate(self.rels):

            # Each key in the dictionary is a value (object) for the relationship.
            # Each value in the dictionary is a beceptivity value
            # Since we are dealing with a dictionary, it natively handles multiple relationship objects.
            fields[rel_obj.rel] = (Dict[str, float|None], Field(..., description=rel_obj.rel))

            # If they want beceptivity attached to each item in the response, even
            # if we get only one response, then best to have a dictionary for this. Plus,
            # a dictionary can also handle multiple keys, therefore a list of responses, except instead
            # of a list we have a dictionary where the keys are the list of items and the value of each
            # key is its beceptivity.
            if self.beceptivity_src_type is not None:
                if (
                        (rel_obj.min_acceptable_beceptivity and self.beceptivity_src_type == beceptivity_src_type_class.llm_response.value)
                        or (self.beceptivity_src_type == beceptivity_src_type_class.is_pure_beceptivity.value)
                    ):
                    # Set has specificity to true, because now at least one rel has beceptivity
                    need_beceptivity_instructions = True

            # If we got ANY beceptivity type and didn't get beceptivity instructions, we have
            # a problem -- so error.
            # TODO: Make sure this works with query for beceptivity -- not sure if name will be a problem.
            if (rel_obj.min_acceptable_beceptivity
                    and self.beceptivity_src_type
                    and (not self.beceptivity_instructions
                         or not self.beceptivity_max_val
                         or not self.beceptivity_cutoff
                         or not self.beceptivity_name
                    )
                ):
                msg = f"You asked for beceptivity by setting min_acceptable_beceptivity to non-zero (it was {rel_obj.min_acceptable_beceptivity}) but did not have all of: beceptivity_instructions, beceptivity_max_val, beceptivity_name, or beceptivity_cutoff. You need all those when you are asking the LLM for beceptivity (which you are via beceptivity_src__type of {self.beceptivity_src_type}.)"
                debug.log(__file__, msg)
                raise Exception('Problem with beceptivity configuration -- see log.')

            # Now we have to finish making the actual prompt.
            # Handle if the response is expected to contain multiple concepts
            if rel_obj.is_multi_resp:
                if rel_obj.min_acceptable_beceptivity and self.beceptivity_src_type == beceptivity_src_type_class.llm_response.value:
                    if self.can_llm_output_json:
                        prompt += f"\nKey: {rel_obj.rel}\nValue: The value for this key is itself a dictionary where each key is a string and each value is a float denoting the specificity of the key. Each key is in prioritized order and is the response to: {rel_obj.rel_prompt}"
                    else:
                        prompt += f"\nRequest response #{idx}: Provide a {self.llm_str_output_separator_name}-delimited list in prioritized order that is the response to: {rel_obj.rel_prompt}"
                        prompt += f"\nRequest response #{idx}b: Provide a {self.llm_str_output_separator_name}-delimited list containing the specificity of each corresponding item in response #{idx}."
                else:
                    if self.can_llm_output_json:
                        prompt += f"\nKey: {rel_obj.rel}\nValue: The value for this key is itself a dictionary where each key is a string and each value is null. Each key, in prioritized order, is the response to: {rel_obj.rel_prompt}"
                    else:
                        prompt += f"\nRequest response #{idx}: Provide a {self.llm_str_output_separator_name}-delimited list in prioritized order that is the response to: {rel_obj.rel_prompt}"
            # Handle if the response is expected to contain one concept
            else:
                # Handle if the response is expected to also contain beceptivity in the same response.
                if rel_obj.min_acceptable_beceptivity and self.beceptivity_src_type == beceptivity_src_type_class.llm_response.value:
                    # Handle if the response can handle JSON
                    if self.can_llm_output_json:
                        prompt += f"\nKey: {rel_obj.rel}\nValue: The value for this key is itself a dictionary with a single string key with a value that is a float denoting the specificity of the key. The key is the response to: {rel_obj.rel_prompt}"
                    # Handle if the response can NOT handle JSON
                    else:
                        prompt += f"\nRequest response #{idx}: Provide a string that is the response to: {rel_obj.rel_prompt}"
                        prompt += f"\nRequest response #{idx}b: Provide a string that is the specificity of the item in response #{idx}"
                # Handle if the response is NOT expected to contain beceptivity in the same response.
                else:
                    # Handle if the response can handle JSON
                    if self.can_llm_output_json:
                        prompt += f"""\nKey: {rel_obj.rel}\nValue: The value for this key is itself a dictionary with a single key that is a string and a value of that key is null. Make the key of the dictionary NOT the term at the end of the prompt but instead your answer to the following: {rel_obj.rel_prompt}"""
                    # Handle if the response can NOT handle JSON
                    else:
                        prompt += f"\nRequest response #{idx}: Provide a string that is the response to: {rel_obj.rel_prompt}"


        # Finish the prompt. The prompt will not prepend a note that the term is at the end of the prompt, nor
        # will it append a note with the term at the end of the prompt if the prompt already contains a concept holder
        # ANYWHERE within it.

        # Placeholders part
        if self.placeholders.concept not in prompt:
            prompt = textwrap.dedent(f'''
                This prompt relates to the term or phrase at the end of this prompt. If the prompt asks for a string, remember that the string may or may not be the string representation of a number, depending on what the prompt asks for.
                {prompt}
                The term or phrase is: {self.placeholders.concept}
                ''')

        # Put in the beceptivity prompt instructions if we are going to need them.
        if need_beceptivity_instructions:
            # Let this error if beceptivity replacer not present
            prompt = prompt.replace(self.placeholders.beceptivity, self.beceptivity_instructions)
        # Otherwise, get rid of the placeholder
        else:
            prompt = prompt.replace(self.placeholders.beceptivity, '')

        return fields, prompt


def schema_to_pydantic_model(
        schema: Dict[str, Any]
        ) -> Type[BaseModel]:
    model_name = schema.get('title', 'DynamicModel')
    properties = schema.get('properties', {})

    model_fields = {}
    for field_name, field_schema in properties.items():

        # print(f"{field_name} is a {field_schema['type']}")
        field_type = str  # Default to string type

        if field_schema['type'] == 'integer':
            field_type = int
        elif field_schema['type'] == 'boolean':
            field_type = bool
        elif field_schema['type'] == 'list' or field_schema['type'] == 'array':
            field_type = list[str]
        elif field_schema['type'] == 'dict':
            field_type = dict[str, str]
        elif field_schema['type'] == 'object':  # Handle nested objects
            nested_model = schema_to_pydantic_model(field_schema)
            field_type = nested_model

        model_fields[field_name] = (field_type, Field(..., title=field_schema.get('title')))

    return pydantic.create_model('responses_property_model', **model_fields)


# I don't think used
"""
def load_rels_prompt_obj_from_params(
        params: str
        ) -> rels_prompt_class:
    obj_dict = su.jsonpickle_loads(params)
    del obj_dict['self']
    return rels_prompt_class(**obj_dict)

def subset_rels_prompt_obj(rels_prompt_obj:rels_prompt_class, keep_rels:list[str])->rels_prompt_class:
    '''
    Makes a new rels_prompt_class object that contains only a subset of its rels -- the rels with the string value of the rel property in the list passed in keep_rels.
    :param rels_prompt_obj: The rels_prompt_class object to subset.
    :param keep_rels: The rel list to keep -- these are the values of rel for each rel_prompt_class object that you wish to keep from the rels_prompt_class object.
    :return: a new rels_prompt_class object containing only your subset of rels. The model and prompt should also automatically update to be your new ones that relate only to the subset.
    '''
    new_rpo = copy.deepcopy(rels_prompt_obj)
    new_rpo.rels = None
    for orig_rel in rels_prompt_obj.rels:
        if orig_rel in keep_rels:
            new_rel = copy.deepcopy(orig_rel)
            new_rpo.add(new_rel)
"""