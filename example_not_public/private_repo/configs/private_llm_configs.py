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

from app_source.public_repo.core.code.interactors.support.llm_config_mapper import llm_config_mapper_class as lcmc

llm_config_maps = {}
llm_config_maps['open_ai_4o_mini'] = lcmc(
    config_name='open_ai_4o_mini'
    , llm_plugin_name='llm_openai'
    , llm_model_config_module_dotted_package_path='app_source.not_public.private_repo.configs.llm_instance_configs.private_openai_4o_mini_configs'
    )
llm_config_maps['open_ai_5_mini'] = lcmc(
    config_name='open_ai_5_mini'
    , llm_plugin_name='llm_openai'
    , llm_model_config_module_dotted_package_path='app_source.not_public.private_repo.configs.llm_instance_configs.private_openai_5_mini_configs'
    )

# Default config name to be used when none provided. Leave as none if you want program to raise
# an exception if LLM config name not specified
default_config_name = 'open_ai_4o_mini'

default_llm_str_output_separator_name = 'tab'
llm_str_output_response_surrounder = '__resp__'