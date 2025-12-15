

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
ppc = pci.bootstrap_import(f"prompt_configs.py", make_dummy_if_not_exists=True)

from pydantic import BaseModel
from app_source.public_repo.core.code.interactors.support.enums import case_change

expansion_str_prompts = getattr(ppc, 'expansion_str_prompts', {'simple': '''Please provide three alternative versions of the term at the end of this prompt. The two versions should be the most basic versions. Provide no other verbiage other than the versions of the term. Do not number the terms, just make each key the term, not a number. The term is: <<<concept>>>'''})

prompt_starts = getattr(ppc, 'prompt_starts', {'standard': '''For the upcoming request, put your response in a list with no other words or explanation. Make the response specific, not a general category, class, or group. If an item in the response would represent a class of items, list out all the items instead of providing the class of items. Do not use 'or' or 'and' in your response items. Do not add any other information. Do NOT use line breaks. If the request doesn't make sense, (e.g., what is the color of sound?) then don't return anything. My request: '''})

#---- PYDANTIC CLASSES FOR PROMPT USE ----#
class pydantic_str_class(BaseModel):
    responses: str


default_instructions = getattr(ppc, 'default_prompt_instructions', f'''Provide no other verbiage, words, explanation, or examples other than exactly what is requested. If a part of the request doesn't make sense, (e.g., what is the color of sound?) then don't return anything for that part. For any response that is not a request for you to explain your thinking or provide your reasoning, then:

a) Make the response specific, not a general category, class, or group. 
b) If the response (or an item in the response, if the response is a list) would represent a class or category of items, list out all the items instead of providing the class or category of items. 
c) Do not use 'or' or 'and' in your response items. 
d) Do not add any other information. 
e) Do NOT use line breaks. 
f) Provide the response in lowercase.

''')

response_case_change = getattr(ppc, 'response_case_change', case_change.lower)

default_beceptivity_max_val = getattr(ppc, 'default_beceptivity_max_val', 10)
default_beceptivity_category_cutoff = getattr(ppc, 'default_beceptivity_category_cutoff', 7)
# Next lines must come after the prior lines for default_beceptivity_max_val and default_beceptivity_category_cutoff
default_beceptivity_val_if_none = getattr(ppc, 'default_beceptivity_val_if_none', 10)
default_beceptivity_name = getattr(ppc, 'default_beceptivity_name', f'Default beceptivity range 1-{default_beceptivity_max_val} cutoff {default_beceptivity_category_cutoff} v001')
"""default_beceptivity_instructions = getattr(ppc, 'default_beceptivity_instructions', f'''If asked for specificity of your responses, then:

a) Provide as an integer value, on a scale of 1 to {default_beceptivity_max_val}, the specificity of the relevent response, where 1 is a category containing an extremely diverse set of concepts and {default_beceptivity_max_val} is a super-specific, detailed concept.
b) If the relevant response is vague, plural because it represents different things, or if you would have put one or more parenthetical examples, then the value should be less than {default_beceptivity_category_cutoff}.
c) Even if a float is allowed, please only provide an integer for this number. 
d) Some concepts normally specify a location, and those types of concepts are typically considered more of a category if the location is missing. For example, "bruising" might be considered more of a category since it usually would be expected to include a location for clear communication. On the other hand, "forearm bruising" or "diffuse brusing" would be considered more specific concepts because they provide location information. This consideration would not apply to concepts for which location is not expected, like "vomiting." 
e) This specificity value is INDEPENDENT of priority and of the specificity of any other responses. This specificity value is simply determined by the specificity of the response term.

''')
"""

default_beceptivity_instructions = getattr(ppc, 'default_beceptivity_instructions', f'''If asked for specificity of your responses, then:

a) Provide an integer value of 1 if your associated response is vague, broad, poorly specfied, is a more general term having multiple specific subtypes (e.g., nutritional deficiency), more of a category than a very specific concept, or or is a response for which you could have put one or more parenthetical examples. Otherwise, provide {default_beceptivity_max_val}.
b) Even if a float is allowed, please only provide an integer for this number. 
c) Some concepts normally specify a location, and those types of concepts are typically considered a category if the location is missing. For example, "bruising" might be considered a category since it usually would be expected to include a location for clear communication. On the other hand, "forearm bruising" or "diffuse brusing" would be considered specific concepts because they provide location information. This consideration would not apply to concepts for which location is not expected, like "vomiting." 
d) This number is UNRELATED to any prioritization or ordering of the responses.
''')