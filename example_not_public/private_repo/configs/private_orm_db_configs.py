
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

import keyring as kr
import app_source.not_public.private_repo.configs.private_file_locations as fl
_host = 'localhost'
_port = '5432'
_database = 'darth_vecdor' # reportedly, default in Postgresql is postgres
_user = kr.get_password('dv_db_username', 'dv')
password = kr.get_password('dv_db_password', 'dv')
_double_check_access_credential = kr.get_password('dv_db_double_checkaccess_credential', 'dv')
connection_string = f"postgresql+psycopg2://{_user}:{password}@{_host}:{_port}/{_database}"
vector_size = 768
schema = 'dv_objs'
system_schema = 't_sys'
default_embedder_meta_src = f'neuml-pubmedbert-base-embeddings'
default_embedder_meta_src_location = f'{fl.model_path}neuml-pubmedbert-base-embeddings'

# For custom table generator queries where we need create the table first,
# we will attempt to generate a create table statement from the query itself.
# That's not always possible, for example, when the query references its own table,
# because what if the table is not yet created? Or, what if someone wants to
# put in indexes in the table creation, or primary key, or specify field types
# that may differ from the auto-generated field types? If so, they can do a create
# table at the beginning of the query, but we need to know that's a create table
# statement and must be able to separate it from the SELECT query that will be used
# to get data that will do inserts into the table. So, we put the table snippet separator
# and if present, it will be separated from the query that follows the separator,
# and it will be run first to ensure the table is created.
dv_query_separator = '<dv_query_separator>'