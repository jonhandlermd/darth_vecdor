
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

# I doubt this is actually used anymore.
src_data_queries = {}

src_data_queries['all_codes_and_strs'] = '''
SELECT
	code
	, str
	, ROW_NUMBER() OVER (PARTITION BY code ORDER BY MIN(priority)) AS priority
FROM my_code_src
GROUP BY code, str
ORDER BY code, priority
    '''