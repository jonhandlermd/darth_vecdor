

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

from sqlalchemy import distinct, select
import json
from app_source.public_repo.core.code.interactors.db_orm import (
    enhanced_db_class
    , code_sets_class
    , codes_class
    , rels_populator_class
    , rels_class
    )
import app_source.public_repo.core.configs.orm_db_configs as odc
import app_source.public_repo.core.configs.prompt_configs as pc
import app_source.public_repo.core.configs.llm_configs as llm_configs

def get_rels_of_rel_populator(enhanced_db_obj:enhanced_db_class, rel_populator:str):
    with enhanced_db_obj.session_class() as session:
        stmt = select(distinct(rels_class.rel)).where(rels_class.rels_populator_id == rel_populator)
        results = session.execute(stmt).scalars().all()
        return results


def get_relationship_populator_ids_and_names(enhanced_db_obj:enhanced_db_class):
    with enhanced_db_obj.session_class() as session:
        stmt = select(rels_populator_class.id, rels_populator_class.name).distinct()
        results = session.execute(stmt).all()
        list_of_dicts = [{'value': row[0], 'label': row[1]} for row in results]
        return list_of_dicts

def get_code_set_names(enhanced_db_obj:enhanced_db_class):
    with enhanced_db_obj.session_class() as session:
        results = session.execute(
            select(distinct(code_sets_class.set_name))
            ).scalars().all()
        return results


def get_terminology_names(enhanced_db_obj:enhanced_db_class):
    with enhanced_db_obj.session_class() as session:
        return session.execute(
            select(distinct(codes_class.terminology))
        ).scalars().all()

def get_orchestrations(enhanced_db_obj:enhanced_db_class, orchestrator_type:str):
    # Make the query
    query_str = f'''
        SELECT po_name FROM
            (
            SELECT po_name, ROW_NUMBER() OVER (PARTITION BY po_name ORDER BY datetime DESC, id DESC) as rn
            FROM {odc.schema}.populator_orchestrations
            WHERE po_type = :po_type
            ) subquery
        WHERE rn = 1
        '''
    success, results = enhanced_db_obj.do_query(
            query=query_str
            , query_params={'po_type': orchestrator_type}
            )
    # I should get a list
    results = [row[0] for row in results]
    return results


def get_orchestration(enhanced_db_obj:enhanced_db_class, orchestrator_type:str, orchestrator_name:str):
    # Make the query
    query_str = f'''SELECT po_content 
        FROM {odc.schema}.populator_orchestrations
        WHERE 
            po_type = :po_type
            AND po_name = :po_name
        ORDER BY datetime DESC, id DESC
        -- ORDER BY id DESC
        LIMIT 1
        '''
    success, results = enhanced_db_obj.do_query(
            query=query_str
            , query_params={'po_name': orchestrator_name, 'po_type': orchestrator_type}
            )
    # By doing .scalars().first() I get a scalar
    return results[0][0]


def get_expansion_styles():
    results = list(pc.expansion_str_prompts.keys())
    results.insert(0, '')
    return results

def get_llm_configs():
    results = list(llm_configs.llm_config_maps.keys())
    return results

def get_embedder_info(enhanced_db_obj:enhanced_db_class):
    # Make the query
    query_str = f'''
SELECT DISTINCT
    em.id AS embedder_meta_id
	, em.src AS embedder_src
	, em.src_location AS embedder_src_location
FROM {odc.schema}.embedder_metas em
ORDER BY em.src
LIMIT 100
        '''
    success, results = enhanced_db_obj.do_query(
            query=query_str
            , query_params={}
            )
    # Convert results to list of dicts which is needed here.
    results = [dict(row._mapping) for row in results]
    return json.dumps(results or [])


def get_rp_info(enhanced_db_obj:enhanced_db_class):
    # Make the query
    query_str = f'''
-- This query may be helpful when configuring the custom table generators.
SELECT DISTINCT ON
    (
    rp.name
    , rp.id
    , rels.rel
    )
	rp.name AS rels_populator_name
	, rp.id AS relationship_populator_id
    , rels.rel
FROM {odc.schema}.rels_populator rp
INNER JOIN {odc.schema}.rels rels
	ON rp.id = rels.rels_populator_id
ORDER BY
	rp.name
	, rels.rel
LIMIT 100
        '''
    success, results = enhanced_db_obj.do_query(
            query=query_str
            , query_params={}
            )
    # Convert results to list of dicts which is needed here.
    results = [dict(row._mapping) for row in results]
    return json.dumps(results or [])


def get_rcmp_info(enhanced_db_obj:enhanced_db_class):
    # Make the query
    query_str = f'''
-- This query may be helpful when configuring the custom table generators.
SELECT DISTINCT
	rp.name AS rels_populator_name
	, rcmp.match_from_rel AS rel
	, rp.id AS relationship_populator_id
	, rcmp.embedder_meta_id AS rel_code_matches_populator_embedder_meta_id
	, em.src AS rel_code_matches_populator_embedder_src
	-- , em.src_location AS rel_code_matches_populator_src_location
FROM {odc.schema}.rels_populator rp
INNER JOIN {odc.schema}.rel_code_matches_populator rcmp
	ON rp.id = rcmp.match_from_rel_populator_id
LEFT OUTER JOIN {odc.schema}.embedder_metas em
	ON rcmp.embedder_meta_id = em.id
ORDER BY
	rp.name
	, rcmp.match_from_rel
	, em.src
LIMIT 100
        '''
    success, results = enhanced_db_obj.do_query(
            query=query_str
            , query_params={}
            )
    # Convert results to list of dicts which is needed here.
    results = [dict(row._mapping) for row in results]
    return json.dumps(results or [])





