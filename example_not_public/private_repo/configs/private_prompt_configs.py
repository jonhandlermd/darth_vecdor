

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

expansion_str_prompts = {}
expansion_str_prompts['simple'] = '''Please provide three alternative versions of the term at the end of this prompt. The two versions should be the most basic versions. Provide no other verbiage other than the versions of the term. Do not number the terms, just make each key the term, not a number. The term is: <<<concept>>>'''

prompt_starts = {}
prompt_starts['standard'] = '''For the upcoming request, put your response in a list with no other words or explanation. Unless requested otherwise, make each response very specific, not general categories, classes, or groups. If an item in the response would represent a class of items, list out all the items instead of providing the class of items. Do not use 'or' or 'and' in your response items. Do not add any other information. Do NOT use line breaks. If the request doesn't make sense, (e.g., what is the color of sound?) then don't return anything. My request: '''

response_formats_dict = {}
default_response_format = 'pydantic_list_of_strs_class'