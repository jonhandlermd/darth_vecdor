

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

from app_source.public_repo.core.code.interactors.llm import response_class as rc
from pydantic import BaseModel
from app_source.public_repo.core.code.utilities.timer import timer as timer_class
from transformers import AutoTokenizer, AutoModelForCausalLM
import app_source.public_repo.core.configs.file_locations as fl
from app_source.public_repo.core.code.interactors.llm_execution_base import llm_execution_base_class

class open_ai_responses_class(BaseModel):
    responses: list[str]


class llm_execution_class(llm_execution_base_class):

    # If default alues are put here, then they won't be stored in the populator object and database.
    # So, recommend not doing so.
    def __init__(self,
                 password,
                 llm_settings,
                 request_settings,
                 other_settings,
                 **kwargs):

        # This can emit JSON
        super().__init__(can_output_json=False)

        ## Llama3 request settings
        self.request_settings = request_settings

        # Load the tokenizer and model
        print("Tokenizer about to load")
        self.tokenizer = AutoTokenizer.from_pretrained(f'{fl.model_path}Meta-Llama-3.1-8B-Instruct')
        print("Tokenizer loaded, now loading model")
        self.model = AutoModelForCausalLM.from_pretrained(f'{fl.model_path}Meta-Llama-3.1-8B-Instruct')
        print("Model loaded")


    def get_response(self, prompt:str)->rc:

        # Create response object
        resp_obj = rc(None, None)

        #### Don't do anything if not given a prompt
        if not prompt:
            resp_obj.response = ''
            resp_obj.spend = 0.00000

        timer = timer_class(do_start=True)


        # Tokenize input
        print("About to tokenize iputs")
        inputs = self.tokenizer(prompt, return_tensors='pt')
        print("inputs tokenized")

        # Generate text
        print("About to generate outputs")
        outputs = self.model.generate(**inputs, max_new_tokens=self.request_settings.get('max_new_tokens', 5))
        print("Outputs generated")

        # Decode and print the output
        print("About to decode outputs")
        response_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("Outputs decoded: ", response_text)
        timer.stop(True)

        #### Prep response
        resp_obj.response = response_text
        prompt_tokens = float(0.0)
        completion_tokens = float(0.0)

        # Calculate spend on this request
        resp_obj.spend = float(0.0)

        # Return response object
        return resp_obj

