

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

# For secrets, like passwords, keys, or anything else, use whatever secure approach is best. Do not assume
# the code shown here is necessarily the best approach or code.
# Example connection string, but remember, every DB seems to have a different connection string!
# connection_string = f'Driver={driver};DBCNAME={host};PORT={port};DATABASE={database};UID={user};PWD={password};{other}'
connection_string = ''

#### What is the name of the audit log table in the database?
table = ''

# Do audit logging at all?  True or False
do_audit_logging = False
# Do not return a response if unable to do logging? True or False
kill_response_if_unable_to_log = False

#### Request must contain keys listed in the following array/list for use in logging
#required_request_elements = {'requester': 'requester_field', 'requester_user': 'requester_user_field', 'requester_role': 'requester_role_field'}
required_request_elements = {'requester': 'requester_field', 'requester_user': 'requester_user_field', 'requester_role': 'requester_role_field'}