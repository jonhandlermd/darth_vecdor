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

import app_source.public_repo.core.code.utilities.private_configs_importer as pci
pllc = pci.bootstrap_import(f"llm_configs.py", make_dummy_if_not_exists=True)


from app_source.public_repo.core.code.interactors.support.llm_config_mapper import llm_config_mapper_class as lcmc

# Of course, for this default to work,
# these have to be present (llm_openai.py in your llm_plugins location,
# and the associated config file in the noted location
default_config_name = getattr(pllc, 'default_config_name', 'default_llm_config')
default_llm_plugin = getattr(pllc, 'default_llm_plugin', 'default_llm_plugin')
llm_config_maps = getattr(pllc, 'llm_config_maps',
        {
        default_config_name: lcmc(
            config_name=default_config_name,
            llm_plugin_name=default_llm_plugin,
            llm_model_config_module_dotted_package_path='app_source.public_repo.core.configs.llm_instance_configs.example_llm_instance_configs'
            )
        }
    )

# Next could be 'pipe', other options also available if I remember correctly
default_llm_str_output_separator_name = getattr(pllc, 'default_llm_str_output_separator_name', 'tab')
llm_str_output_response_surrounder = getattr(pllc, 'llm_str_output_response_surrounder', '__resp__')