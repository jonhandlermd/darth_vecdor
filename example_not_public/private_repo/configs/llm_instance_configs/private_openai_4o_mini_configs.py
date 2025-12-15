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

##############################
## CHATGPT CONFIG SECRETS
##############################
import openai
import os
import keyring as kr

# This module contains things to be passed to the LLM execution class which will pass it on to an
# LLM Plugin Module.

# INITIALIZE EMPTY DICTIONARIES
# Always need basic LLM Settings variable
llm_settings = {}
# Always need other_settings variable
other_settings = {}
# Always need request-specific settings variable
request_settings = {}
# Always need DV-related configs variable
dv_llm_configs = {}

# ****** BEGIN ACTUAL CONFIG SETTINGS *********
# Always need a password variable
# password = os.getenv("openai_key")
password = kr.get_password('dv_openai_key', 'dv')
# Always need a max spend variable (this is in dollars).
max_spend = 0 # Replace with your real number,

# These are the Open AI Basic LLM settings
llm_settings['model'] = 'gpt-4o-mini' # Always need a model (formerly called "engine")
llm_settings['model_type'] = 'ChatCompletion' # 'Completion' or 'ChatCompletion'

# Defaults required by azure
other_settings['api_type'] = 'openai'
other_settings['api_version'] = openai.api_version
try:
    other_settings['api_base'] = openai.api_base
except:
    other_settings['api_base'] = None


# OpenAI recommends adjusting either temperature or top_p but not both
request_settings['temperature'] = 0 # OpenAI's default I believe is 0.7
request_settings['max_tokens'] = 4096
request_settings['stop'] = ''
#request_settings['top_p'] = 0.01 # Default is 0.01
#request_settings['frequency_penalty'] = 0
#request_settings['presence_penalty'] = 0
#request_settings['best_of'] = 1 # Default is 1


# These are the DV-specific settings for this LLM and LLM instance
dv_llm_configs['prompt_cost_per_1000_tokens'] = 10000000 # Replace with real number, e.g., per https://openai.com/api/pricing/
dv_llm_configs['completion_cost_per_1000_tokens'] = 10000000 # Replace with real number, e.g., per  https://openai.com/api/pricing/
