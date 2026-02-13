import importlib
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
from openai import OpenAI
import openai

# import app_source.public_repo.core.configs.llm_instance_configs.openai_configs as gptc
from app_source.public_repo.core.code.interactors.llm import response_class as rc
from app_source.public_repo.core.code.utilities.timer import timer as timer_class
import app_source.public_repo.core.code.interactors.support.rels_prompt as rp
from app_source.public_repo.core.code.interactors.support.rels_prompt import rels_prompt_class as rspc
from app_source.public_repo.core.code.interactors.llm_execution_base import llm_execution_base_class
import app_source.public_repo.core.code.utilities.debug as debug

class llm_execution_class(llm_execution_base_class):

    # If default alues are put here, then they won't be stored in the populator object and database.
    # So, recommend not doing so.
    def __init__(self,
                 password,
                 llm_settings,
                 request_settings,
                 other_settings,
                 dv_llm_configs,
                 **kwargs):

        # This can emit JSON
        super().__init__(can_output_json=True)

        self.prompt_cost_per_1000_tokens = dv_llm_configs['prompt_cost_per_1000_tokens']
        self.completion_cost_per_1000_tokens = dv_llm_configs['completion_cost_per_1000_tokens']

        self.api_key = password
        self.model_type = llm_settings['model_type'] # completions or chat
        self.engine = llm_settings['model']

        ## OpenAI recommends adjusting either temperature or top_p but not both
        self.request_settings = request_settings
        ## Azure-required settings
        self.api_type = other_settings['api_type']
        self.api_version = other_settings['api_version']
        self.api_base = other_settings['api_base']


    def get_response(self, prompt:str, rels_prompt_obj:rspc)->rc:
        # Put response format class into its own variable
        response_format_class = rels_prompt_obj.model
        # Create response object
        resp_obj = rc(None, None)
        # Azure-required settings
        openai.api_type = self.api_type
        openai.api_version = self.api_version
        openai.api_base = self.api_base
        openai.api_key = self.api_key
        # Keep track of time
        timer = timer_class(do_start=True)
        # Set up the client
        client = OpenAI(api_key=self.api_key)

        # Initialize response
        resp_obj.response = None
        prompt_tokens = 0.0000
        completion_tokens = 0.000

        # If we got a Pydantic object, just use it, but if we got a string then assume JSON
        # and convert to pydantic, and if we got a dict then assume it was schema and convert to pydantic
        if isinstance(response_format_class, str):
            response_format_class = json.loads(response_format_class)
        if isinstance(response_format_class, dict):
            response_format_class = rp.schema_to_pydantic_model(response_format_class)

        # Don't do anything if not given a prompt
        if not prompt:
            pass
        # Otherwise, ask the question
        else:
            # Need to make sure we get a legitimate response
            keep_asking = 1
            ask_count = 0
            max_ask_count = 2
            while keep_asking and ask_count <= max_ask_count:
                ask_count += 1
                # Ask question

                #d = debug.default_d
                d = debug.default_d
                debug.debug(f"----------\n{prompt}\n----\n", d=d)
                # print(prompt)
                # print(self.engine)
                d = debug.default_d

                try:
                    completion = client.beta.chat.completions.parse(
                    #completion = client.chat.completions.create(
                    #completion = client.chat.completions.create(
                        model=self.engine,
                        timeout=30,
                        messages=[
                            {"role": "user", "content": prompt},
                            ],
                        response_format={"type": "json_object"},
                        # response_format=response_format_class, # Failing on parse, not sure why
                        **self.request_settings
                        )
                    raw_response = completion.choices[0].message.content
                    # print(raw_response)
                    # exit()
                    d =  debug.default_d
                    debug.debug(f"----\n{raw_response}---------\n", d=d)
                    d = debug.default_d
                    # exit()

                    # Get response
                    #resp_obj.response = completion.choices[0].messsage.parsed.responses
                    # print(completion.choices[0].messsage.parsed.responses)
                    # Increment the cost, in tokens, of this response
                    prompt_tokens += float(completion.usage.prompt_tokens)
                    completion_tokens += float(completion.usage.completion_tokens)

                except Exception as e:
                    msg = f"ERROR: Failed to get response from LLM.\nError was: {e}"
                    debug.log(__file__, msg)
                    print(msg)
                    raise Exception("ERROR: Failed to get response from LLM.")

                # Check if response is legitimate
                try:
                    obj = json.loads(raw_response)
                    response = response_format_class(**obj)

                    # response = response_format_class.model_validate(completion.choices[0].message.parsed)
                    # resp_obj.response = completion.choices[0].message
                    # MUST return a dictionary representation of the pydantic object
                    # Response object MUST contain a property of "responses"
                    # resp_obj.response = response.responses.__dict__
                    resp_obj.response = response.__dict__
                    keep_asking = 0
                except Exception as e:
                    msg = f"ERROR: Raw response for \n{prompt}\n was:\n{raw_response}\n\nValidation failed with error {e}\nand response of: {resp_obj.response}"
                    debug.log(__file__, msg)
                    print(msg)

        # Calculate spend on this request
        thousand_as_float = float(1000.0000000)
        prompt_cost = (prompt_tokens / thousand_as_float) * self.prompt_cost_per_1000_tokens
        completion_cost = (completion_tokens / thousand_as_float) * self.completion_cost_per_1000_tokens
        total_cost = prompt_cost + completion_cost
        resp_obj.spend = total_cost

        # Stop timer
        timer.stop(False)

        # Return response object
        return resp_obj

