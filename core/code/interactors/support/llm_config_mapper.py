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

import app_source.public_repo.core.code.utilities.debug as debug
import importlib

class llm_config_mapper_class:
    def __init__(self
                 , config_name: str
                 , llm_plugin_name: str
                 , llm_model_config_module_dotted_package_path: str
                 ):
        # Make sure we have what we need
        if not config_name:
            msg = f'No config_name for {self.__class__.__name__}'
            debug.log(__file__, msg)
            raise Exception(msg)
        if not llm_plugin_name:
            msg = f'No llm_plugin_name for {self.__class__.__name__}'
            debug.log(__file__, msg)
            raise Exception(msg)
        if not llm_model_config_module_dotted_package_path:
            msg = f'No llm_model_config_module_dotted_package_path for {self.__class__.__name__}'
            debug.log(__file__, msg)
            raise Exception(msg)

        # Import the desired config module
        try:
            self.imported_cfg_module = importlib.import_module(
                llm_model_config_module_dotted_package_path
                , llm_model_config_module_dotted_package_path
                )
        except Exception as e:
            msg = f'Got error importing module {llm_model_config_module_dotted_package_path} -- error was: {e}'
            debug.log(__file__, msg)
            raise Exception(f'Got error importing an LLM config module')

        self.config_name = config_name
        self.llm_plugin_name = llm_plugin_name