

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

import hashlib
import time
import inspect
import importlib
import app_source.public_repo.core.configs.file_locations as fl
import app_source.public_repo.core.configs.other_configs as oc
from app_source.public_repo.core.code.interactors.support.rels_prompt import rels_prompt_class as rspc
import app_source.public_repo.core.code.utilities.arg_and_serializer_utils as su
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.configs.llm_configs as llc

g_d = False


def update_dict_key(tdict, existing_key, replacer_key):
    if existing_key in tdict:
        tdict[replacer_key] = tdict.pop(existing_key)
    return tdict


class response_class:

    def __init__(self, the_response, spend:float):
        self.response = the_response
        self.spend = spend



class llmer:


    # If default alues are put here, then they won't be stored in the populator object and database.
    # So, recommend not doing so.
    def __init__(self,
                 llm_module:str,
                 max_spend: float,
                 password,
                 llm_settings,
                 llm_request_settings,
                 llm_other_settings,
                 dv_llm_configs,
                 **kwargs):

        # Set the temp_params dict
        frame = inspect.currentframe()
        temp_params = inspect.getargvalues(frame).locals
        # But now replace password.
        temp_params['password'] = oc.password_replacer
        # And now put in the class name
        temp_params['self'] = self.__class__.__name__
        # And now get rid of the frame entry
        del temp_params['frame']

        # Get the LLM class
        imported_llm_module = importlib.import_module(f'{fl.plugins_path}llm_plugins.{llm_module}')
        llm_class = getattr(imported_llm_module, 'llm_execution_class')

        # Set items that shouldn't be modified. I didn't bother trying to make them read-only because
        # it doesn't work for the properties of an object that itself is the value of a property.
        # Instead, we check for changes on each call for an LLM response.
        self._params = su.jsonpickle_dumps(temp_params)
        self.llm_obj = llm_class(password, llm_settings, llm_request_settings, llm_other_settings, dv_llm_configs)
        self.max_spend = max_spend
        self._baseline = self._make_baseline()

        # Create field for, and initialize to None, the variable to hold the last prompt that was processed and post-processed
        self.last_post_processed_prompt = None

        # Set password
        self.password = password

        # Are we testing?
        self.is_testing = kwargs.get('is_testing', False)

        # Keep track of this object's total spend
        self.total_spend = 0.00000000

        # Create and clear the last response stuff
        self.clear_lasts()


    @property
    def params(self):
        # Make sure that params still reflect the object, otherwise an exception will be raised.
        self.check_changed()
        return self._params


    def _make_baseline(self):
        static_components = [self.llm_obj, self.max_spend]
        """Generate a hash of the JSON-serialized object."""
        jp = su.jsonpickle_dumps(static_components)
        return hashlib.md5(jp.encode('utf-8')).hexdigest()

    def check_changed(self):
        """Check if the hash of the object state has changed."""
        if self._baseline != self._make_baseline():
            msg = "ERROR: he baseline properties of this llmer object have been modified."
            debug.log(__file__, msg)
            raise Exception(msg)


    def clear_lasts(self):
        self.last_resp = None
        self.last_post_processed = None
        self.last_resp_items = []

    def get_and_process_response(self, rels_prompt_obj:rspc, llm_replacer_content:dict):
        d = g_d
        debug.debug("Got to get_and_process_response", d=d)

        # Refuse to process any responses if they have changed the baseline, because otherwise the responses
        # will be based on a version of this object that is out of sync with the baseline -- the params
        # will not represent the actual params.
        # TODO: REVISIT THIS! Do we need it? If so, how to implement it differently now that I have moved rels_prompt_obj out of init.
        # self.check_changed()

        try:
            debug.debug("Getting post_processed_prompt", d=d)
            post_processed_prompt = rels_prompt_obj.prompt
            debug.debug("Got post_processed_prompt, getting placeholders", d=d)
            replacers = rels_prompt_obj.placeholders.__dict__
            debug.debug("Got placeholders", d=d)
        except Exception as prompt_processing_exception:
            msg = f"ERROR: Problem getting prompt or placeholders from rels_prompt_obj -- error was {prompt_processing_exception}"
            debug.log(__file__, msg)
            raise Exception(msg)

        # Clear prior response stuff
        debug.debug("About to clear lasts", d=d)
        self.clear_lasts()
        debug.debug("Done clearing lasts", d=d)

        # Replace in the elements we want inside the prompt
        for k in llm_replacer_content:
            # Make sure that k is ia key in replacer. If not, something is messed up.
            if k not in replacers:
                msg = f"ERROR: Problem: {k} not a prompt replacer placeholder"
                debug.log(__file__, msg)
                raise Exception(msg)
            # Replacers tells us the string to find and replace, as they map from the
            # element to replace to the string representing that element inside the prompt.
            str_to_replace = replacers[k]
            debug.debug(f"Replacing {str_to_replace} with key {k} in llm_replacer content having value {llm_replacer_content[k]}", d=d)
            # If we didn't get a replacer, change it to empty string.
            replacement_str = llm_replacer_content[k]
            if llm_replacer_content[k] is None:
                debug.debug(f"Got None for the k value of {k} for llm_replacer_content, so using empty string.", d=d)
                replacement_str = ''
            post_processed_prompt = post_processed_prompt.replace(str_to_replace, replacement_str)
            debug.debug(f"After replacement, post_processed_prompt is: {post_processed_prompt}", d=d)

        # Prompt now complete!
        self.last_post_processed_prompt = post_processed_prompt

        # print(f"PROMPT: {post_processed_prompt}")
        # exit()

        # Ask the LLM for a response to the prompt.
        # We should expect back a pydantic response in the expected format,
        # as a dictionary representation of the pydantic object,
        # because it seems pydantic cannot always just be loaded.
        debug.debug(f"Getting response from LLM with prompt: {post_processed_prompt}", d=d)

        try_counter = 0
        max_tries = 3
        last_error = None
        while try_counter < max_tries:
            try_counter += 1
            if try_counter >= max_tries:
                msg = f"ERROR: LLM call failed {max_tries} times, last error was {last_error}"
                debug.log(__file__, msg)
                raise Exception(msg)
            try:
                resp_obj = self.llm_obj.get_response(post_processed_prompt, rels_prompt_obj)
                break
            except Exception as llm_call_try_counter_loop_issue:
                # Track last error
                last_error = llm_call_try_counter_loop_issue
                debug.log(__file__,f"ERROR: LLM call failed on try {try_counter} with error {llm_call_try_counter_loop_issue}", show_log_msg=True)
                # Sleep for 1 second before any next try
                time.sleep(1)
        # resp_obj = self.llm_obj.get_response(post_processed_prompt, rels_prompt_obj)

        debug.debug(f"Got response from LLM: {resp_obj.response}", d=d)

        # Now loop through each rel item in the rels_prompt object to see
        # if it needs any of its content converted to the desired text because
        # it had a "response dictionary" aka resp_dict.
        try:
            for rel_prompt_obj in rels_prompt_obj.rels:
                if rel_prompt_obj.resp_dict is not None:
                    try:
                        # rel_prompt_obj cannot be is_multi_resp if resp_dict is not None
                        if rel_prompt_obj.is_multi_resp:
                            msg = "ERROR: Cannot have rel's resp_dict not None and have rel be multi_resp"
                            debug.log(__file__, msg)
                            raise Exception(msg)
                        rel = rel_prompt_obj.rel
                        # If this fails, then something went wrong, let the whole thing fail
                        resp_for_rel = resp_obj.response[rel]
                        # This response should be a dictionary with only one key.
                        # Change the key to the value of the resp_dict having the current value as its key.
                        # This gets the key of the response in dictionary form
                        k = next(iter(resp_for_rel))
                        # This is the replacement we want
                        try:
                            replacer_k = rel_prompt_obj.resp_dict[k]
                        except Exception as resp_dict_key_exception:
                            msg = f"""ERROR: 
Problem: A rel has a response dictionary but the response is not a response dictionary key.
Rel: {rel_prompt_obj.rel} 
Response: {k}
                               """
                            debug.log(__file__, msg)
                            raise Exception(msg)
                        try:
                            # Now update the key in the response dictionary
                            debug.debug(f"Updating response dictionary key {k} to {replacer_k} for rel {rel_prompt_obj.rel}", d=d)
                            update_dict_key(resp_for_rel, k, replacer_k)
                        except Exception as resp_dict_key_update_exception:
                            msg = f"ERROR: Problem updating rel {rel_prompt_obj.rel} response dictionary key {k} to {replacer_k} -- error was {resp_dict_key_update_exception}"
                            debug.log(__file__, msg)
                            raise Exception(msg)
                    except Exception as rels_resp_processing_exception:
                        msg = f"ERROR: Problem processing rel \"{rel_prompt_obj.rel}\" response -- error was {rels_resp_processing_exception}\n\n Response was {resp_obj.response}"
                        debug.log(__file__, msg)
                        raise Exception(msg)
        except Exception as resp_processing_exception:
            msg = f"ERROR: Problem processing response into rels -- error was {resp_processing_exception}"
            debug.log(__file__, msg)
            raise Exception(msg)

        # Add spend on this response to the total spend
        debug.debug("Total spend before this response: " + str(self.total_spend), d=d)
        self.total_spend += resp_obj.spend
        debug.debug("Response spend: " + str(resp_obj.spend), d=d)
        debug.debug("Total spend after this response: " + str(self.total_spend), d=d)

        #### Get the content itself
        contents = resp_obj.response
        self.last_resp = resp_obj.response

        #### If testing, show response
        if self.is_testing:
            ("RESPONSE:", self.last_resp)

        # Exit program if we've spent more than allocated!
        debug.debug(f"Total spend: {self.total_spend}", d=d)
        debug.debug(f"Max Spend: {self.max_spend}", d=d)
        if self.total_spend > self.max_spend:
            debug.log(__file__, f"Exceeded max spend of {self.max_spend}! Exiting immediately!")
            exit()

        #### All done -- return
        return

    @staticmethod
    def get_object_name(obj):
        if isinstance(obj, (str, list, dict, set, tuple, int, float, bool, bytes)):
            return type(obj).__name__
        elif hasattr(obj, '__class__'):
            return obj.__class__.__name__
        else:
            return type(obj).__name__

# Given params (that include a sanitized param string without a password)
# substitute in the password and then get the object.
def get_llm_from_llm_params(params:str, password) -> llmer:
    obj_dict = su.jsonpickle_loads(params)
    obj_dict['password'] = password
    del obj_dict['self']
    return llmer(**obj_dict)

def get_object_name(obj):
    if isinstance(obj, (str, list, dict, set, tuple, int, float, bool, bytes)):
        return type(obj).__name__
    elif hasattr(obj, '__class__'):
        return obj.__class__.__name__
    else:
        return type(obj).__name__



def make_llm_obj(llm_config_name:str)->llmer:
    try:
        cfg_map = llc.llm_config_maps.get(llm_config_name)
    except Exception as e:
        msg = f'"ERROR: Could not get config map with name {llm_config_name} -- error was {e}'
        debug.log(__file__, msg)
        raise Exception('Could not get requested config map for LLM. See log.')


    llm_obj = llmer(
        llm_module=cfg_map.llm_plugin_name,
        max_spend=cfg_map.imported_cfg_module.max_spend,
        password=cfg_map.imported_cfg_module.password,
        llm_settings=cfg_map.imported_cfg_module.llm_settings,
        llm_request_settings=cfg_map.imported_cfg_module.request_settings,
        llm_other_settings=cfg_map.imported_cfg_module.other_settings,
        dv_llm_configs=cfg_map.imported_cfg_module.dv_llm_configs
        )

    return llm_obj




