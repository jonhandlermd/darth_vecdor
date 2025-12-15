


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

#### Imports
# from app_source.public_repo.core.code.utilities.db import db as db


def log_request(request_to_log, response_to_log):
    return True, ''
    """
    if not alc.do_audit_logging:
        return False, 'Not set up to do logging.'
    else:
        tdb = db(connection_string=alc.connection_string)
        now_epoch_secs = time.time()
        required_req_eles = alc.required_request_elements
        got_reqs = True
        query_fields = ['epoch_secs', 'request_msg', 'response_msg']
        query_fields_vals = [now_epoch_secs, json.dumps(request_to_log), json.dumps(response_to_log)]
        query_fields_vals_qmarks = ['?', '?', '?']
        for required_req_ele in required_req_eles.keys():
            req_ele = request_to_log.get(required_req_ele, None)
            if not req_ele:
                got_reqs = False
                break
            query_fields.append(required_req_eles[required_req_ele])
            query_fields_vals.append(req_ele)
            query_fields_vals_qmarks.append('?')

        if not got_reqs:
            return False, 'ERROR: Did not receive required request elements.'

        query_fields_str = ', '.join(query_fields)
        query_fields_vals_qmarks_str = ', '.join(query_fields_vals_qmarks)

        query = f'''
            INSERT INTO {alc.audit_log_table} ({query_fields_str})
            VALUES ({query_fields_vals_qmarks_str})
            '''
        result, err = tdb.do_non_select_query(query, (query_fields_vals))
        return result, err
        """


