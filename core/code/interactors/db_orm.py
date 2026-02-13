

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

############ IMPORTS ##############

# Regular Python imports
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, date
import weakref
import numpy as np
from typing import List, Any, Union
import numbers
import copy
import textwrap
# from contextlib import contextmanager

# Torch imports
import torch
from torch import Tensor

# Flask imports
# from flask import g

# PostgreSQL-related imports
from pgvector.sqlalchemy import Vector
from pglast import parse_sql
from pglast.ast import (
    DeleteStmt,
    DropStmt,
    TruncateStmt,
    UpdateStmt,
    AlterTableStmt,
    )

# SQL Alchemy imports
from sqlalchemy import (
    UniqueConstraint, Result, create_engine, URL, ForeignKey, Boolean, CursorResult,
    Column, Integer, Float, Text, TIMESTAMP, ARRAY, text, and_, or_, DOUBLE_PRECISION, event, String,
    Date, DateTime
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, selectinload

# This program imports
import app_source.public_repo.core.configs.orm_db_configs as odc
import app_source.public_repo.core.code.utilities.debug as debug
import app_source.public_repo.core.configs.other_configs as oc
from app_source.public_repo.core.code.interactors.sent_tran import sent_tran_class as stc, embedding_class as ec
from app_source.public_repo.core.code.utilities.list_processing_reporter import list_processing_reporter_class as lprc
import app_source.public_repo.core.code.interactors.llm as llmm
from app_source.public_repo.core.code.interactors.llm import llmer as llmc
from app_source.public_repo.core.code.interactors.support.rels_prompt import rel_prompt_class as rpc, rels_prompt_class as rspc, placeholders_class as plc
from app_source.public_repo.core.code.interactors.support.enums import *
import app_source.public_repo.core.code.interactors.support.enums as enums
import app_source.public_repo.core.code.utilities.arg_and_serializer_utils as su
import app_source.public_repo.core.code.utilities.task_manager as tskm

############# GLOBALS ###############
# This has to be global so other classes can inherit from it
dec_base = declarative_base()

# Die on LLM failure?
die_on_llm_failure = 1

# Debugging?
gl_d = debug.default_d

# Status reporting
g_status_report_functions = [tskm.emit_status]
if gl_d:
    g_status_report_functions.append(print)


############# FUNCTIONS USED BY TABLE CLASSES ################
def make_id(
        the_id
        )->str:

    if not the_id:
        return str(uuid.uuid4())
    else:
        return the_id

def make_datetime(
        the_datetime=None
        )->datetime:

    if not the_datetime:
        # return datetime.now(datetime.UTC)
        # return datetime.utcnow()
        return datetime.now(timezone.utc)
    else:
        return the_datetime


# Now for explicit delete or garbage collection delete, need to make sure we reduce the count
# of uses of the embedder, and if 0, remove it from the embedders store.
def embedder_cleanup(
        obj
        ):

    # Reduce reference count on deletion
    enhanced_db_class._embedders_use_count[obj.embedder_meta_obj.src] -= 1
    # Are we down to 0 objects using the model?
    if enhanced_db_class._embedders_use_count[obj.embedder_meta_obj.src] == 0:
        # Remove the embedder from the embedder store
        del enhanced_db_class._embedders[obj.embedder_meta_obj.src]
        # Remove the listing from the count of embedders using the embedder
        del enhanced_db_class._embedders_use_count[obj.embedder_meta_obj.src]


def get_col_names_for_table_obj(
        obj
        ):

    # table_class = obj.__class__
    col_names = [col.name for col in obj.__table__.columns]
    return col_names

def get_unique_field_sets(
        obj
        ):

    or_list = []
    for constraint in obj.__table__.constraints:
        if isinstance(constraint, UniqueConstraint):
            or_list.append(constraint.columns.keys())
    return or_list


def get_existing_obj_via_unique_constraints(
        session
        , obj
        ):
    """
    Query the database to find an existing object based on unique constraints.
    obj must be a table class
    """
    unique_constraints_sets = get_unique_field_sets(obj.__class__)
    table_class = obj.__class__

    or_filters = []
    for uc_set in unique_constraints_sets:
        and_filters = []
        for uc in uc_set:
            col_attr = getattr(table_class, uc)
            val = getattr(obj, uc)

            # and_filters.append(getattr(table_class, uc) == getattr(obj, uc))
            # If we get None as the value of obj.uc, it will convert to NULL
            # and an equals on NULL is always false, so handle that.
            if val is None:
                and_filters.append(col_attr.is_(None))
                continue

            # Normalize types based on column type -- this is required for psycopg3, which
            # is very strict about type matching compared to psycopg2, apparently.
            col_type = col_attr.type

            if isinstance(col_type, Integer):
                val = int(val)
            elif isinstance(col_type, Float):
                val = float(val)
            elif isinstance(col_type, String):
                val = str(val)
            elif isinstance(col_type, Boolean):
                val = bool(val)
            elif isinstance(col_type, Date):
                if isinstance(val, str):
                    val = date.fromisoformat(val)
                elif isinstance(val, datetime):
                    val = val.date()
                elif not isinstance(val, date):
                    raise TypeError(f"Cannot convert {val!r} to date")
            elif isinstance(col_type, DateTime):
                if isinstance(val, str):
                    val = datetime.fromisoformat(val)
                elif isinstance(val, date):
                    # Convert date to datetime at midnight
                    val = datetime(val.year, val.month, val.day)
                elif not isinstance(val, datetime):
                    raise TypeError(f"Cannot convert {val!r} to datetime")
            else:
                # Catch-all for UUID and other common types
                if isinstance(val, str) and getattr(col_type, "__class__", None).__name__ == "UUID":
                    val = uuid.UUID(val)

            # Add equality filter
            and_filters.append(col_attr == val)



        # self_group forces the parentheses around the AND-ed group.
        or_filters.append(and_(*and_filters).self_group())

    # Apply the filters to the query
    query = session.query(table_class).filter(or_(*or_filters))
    # print(query.statement.compile())
    # if obj.__class__.__name__ == 'rels_populator_class':
        # exit()

    # TO DO: CHECK HOW MANY ITEMS COME BACK. IF MORE THAN 1, SHOULD BE AN ERROR.
    if query.count() > 1:
        msg = "ERROR: More than one item came back in get_existing_obj_via_unique_constraints!"
        debug.log(__file__, msg)
        raise Exception(msg)

    # Next line gets existing object if there is one, otherwise returns None
    return query.first()

def update_non_null_properties(
        existing_obj
        , obj
        ):

    is_difference = False
    for k in get_col_names_for_table_obj(existing_obj):
        # We want to set the attribute ONLY if we don't already have a value for the
        # attribute because it was passed during object instantiation.
        obj_val = getattr(obj, k, None)
        existing_obj_val = getattr(existing_obj, k, None)
        # print(f"Comparing new val: {obj_val} to existing val: {existing_obj_val}")
        if obj_val is not None and not np.array_equal(obj_val, existing_obj_val):
            #print("There is a difference")
            is_difference = True
        # The way this works, you cannot overwrite an existing value with None.
        # If you want to do that, you have to explicitly set it and commit it
        # AFTER instantiating the object.
        # So, only overwrite the current value of the obj property with the existing
        # value from the database if the current value of the obj property is None.
        if obj_val is None:
            setattr(obj, k, existing_obj_val)
    return is_difference


def upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj:enhanced_db_class, obj:Any):
    with enhanced_db_obj.session_class() as session:
        # Get existing obj, if any
        existing_obj = get_existing_obj_via_unique_constraints(session, obj)

        # Copy existing_obj's attributes to obj, if it exists
        is_difference = True
        if existing_obj:
            is_difference = update_non_null_properties(existing_obj, obj)
        else:
            # print("Is not existing object")
            pass

        # Only update object if there is a difference to update
        if not is_difference:
            # print("There is no difference to update")
            return

        # Put object into database using merge, which seems to have the behavior of "upsert"
        # (insert if not present, update if present)
        session.merge(obj)
        session.commit()
        # Now need to reload with content from DB, because may have had some default values set.
        existing_obj = get_existing_obj_via_unique_constraints(session, obj)
        # Copy existing_obj's attributes to obj, if it exists
        if existing_obj:
            update_non_null_properties(existing_obj, obj)
        else:
            msg = "ERROR: Could not get existing object that should have just gotten created!"
            debug.log(__file__, msg)
            raise Exception(msg)
        return


def get_existing_obj_via_id(session, passed_class, the_id):
    """
    Query the database to find an existing object based on id.
    passed_class must be a table class
    """
    return session.query(passed_class).filter(passed_class.id == the_id).first()



######### MIXIN CLASSES ##########
class vector_auto_validator_mixin:
    """
    A mixin for SQLAlchemy models that automatically ensures all Vector columns
    are validated and padded (if necessary) to match their expected dimensions.

    Behavior:
    - On INSERT or UPDATE, vector fields are:
        - Validated for length
        - Padded with zeros if too short
        - Raise ValueError if too long
    - During runtime, assigning to a vector field:
        - Applies the same checks immediately
        - Padding occurs in-place, too-long vectors raise errors
    """
    __abstract__ = True  # Required to prevent SQLAlchemy from treating this as a table

    @classmethod
    def __declare_last__(cls):
        """
        SQLAlchemy calls this after mappings are completed.
        We use it to register event listeners that validate and pad vector columns.
        """
        table = cls.__table__

        # Identify which columns on the table are pgvector Vector columns
        vector_columns = [
            col.name for col in table.columns
            if isinstance(col.type, Vector)
        ]

        # If there are no vector columns, do nothing
        if not vector_columns:
            return

        # Register a listener for SQLAlchemy's "before_insert" and "before_update" events
        # These fire during flush/commit for normal SQLAlchemy sessions (not raw SQL)
        @event.listens_for(cls, 'before_insert', propagate=True)
        @event.listens_for(cls, 'before_update', propagate=True)
        def validate_vectors(mapper, connection, target):
            for col_name in vector_columns:
                vec = getattr(target, col_name)
                if vec is None:
                    continue  # Allow null vectors
                expected_len = table.columns[col_name].type.dim
                if len(vec) > expected_len:
                    raise ValueError(
                        f"{col_name} too long: got {len(vec)}, expected {expected_len}"
                    )
                elif len(vec) < expected_len:
                    # Pad with zeros to correct length
                    setattr(target, col_name, vec + [0.0] * (expected_len - len(vec)))

        # Register attribute-level listeners to catch bad vector values immediately
        for col_name in vector_columns:
            expected_len = table.columns[col_name].type.dim

            def make_attr_listener(col_name, expected_len):
                """
                Returns a closure that performs vector length validation and zero-padding
                on assignment to a vector field.
                """
                def listener(target, value, oldvalue, initiator):
                    if value is None:
                        return value  # Allow null vectors
                    if len(value) > expected_len:
                        raise ValueError(
                            f"{col_name} too long: got {len(value)}, expected {expected_len}"
                        )
                    elif len(value) < expected_len:
                        return value + [0.0] * (expected_len - len(value))
                    return value
                return listener

            # Hook into SQLAlchemy attribute 'set' events for the vector column
            # `retval=True` means the returned value (e.g. padded) will be used
            event.listen(
                getattr(cls, col_name),
                'set',
                make_attr_listener(col_name, expected_len),
                retval=True
            )


######### SYSTEM TABLE CLASSES ##########

class audit_log_class(dec_base):
    __tablename__ = "audit_log"
    __table_args__ = (
        UniqueConstraint('requester', 'requester_on_behalf_of', 'epoch_secs', 'request_msg', 'response_msg'),
        {"schema": odc.system_schema}
        )
    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    requester = Column(Text, nullable=False)
    requester_on_behalf_of = Column(Text, nullable=False)
    epoch_secs = Column(DOUBLE_PRECISION, nullable=False)
    request_msg = Column(Text, nullable=False)
    response_msg = Column(Text, nullable=False)

    def __init__(self
        , enhanced_db_obj:enhanced_db_class
        , requester:str
        , requester_on_behalf_of:str
        , epoch_secs:float
        , request_msg:str
        , response_msg:str
        ):
        self.requester:str = requester
        self.requester_on_behalf_of:str = requester_on_behalf_of
        self.epoch_secs:float = epoch_secs
        self.request_msg:str = request_msg
        self.response_msg:str = response_msg
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


######### TABLE CLASSES #############

class base_table_class(vector_auto_validator_mixin, dec_base):
    __abstract__ = True

class code_populators_class(base_table_class):
    __tablename__ = 'code_populators'
    __table_args__ = (
            UniqueConstraint('terminology'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    # datetime = Column(DateTime, default=lambda: make_datetime())
    datetime = Column(TIMESTAMP(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    # DB connection params
    db_obj_params = Column(Text)
    # Query to get the data
    query = Column(Text)
    # Terminology
    terminology = Column(Text, nullable=False)
    # Additional info
    desc = Column(Text)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , db_obj_params:str
            , query:str
            , terminology:str
            , desc:str=None
            ):

        self.db_obj_params = db_obj_params
        self.query = query
        self.terminology = terminology
        self.desc = desc
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


# These contain the "metadata" info for each embedder
class embedder_metas_class(base_table_class):
    __tablename__ = 'embedder_metas'
    __table_args__ = (
            UniqueConstraint('src'),
            UniqueConstraint('src_location'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    src = Column(Text, nullable=False)
    src_location = Column(Text, nullable=False)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , src:str
            , src_location:str
            ):

        self.src = src
        self.src_location = src_location
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class codes_class(base_table_class):
    __tablename__ = 'codes'
    __table_args__ = (
            UniqueConstraint('code', 'terminology'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    code_populator_id = Column(Text, ForeignKey(f'{odc.schema}.code_populators.id'))
    code = Column(Text, nullable=False)
    terminology = Column(Text, nullable=False)
    main_str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'))
    strs_model = relationship("strs_class")

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , code_populator_id:str
            , code:str
            , terminology:str
            , main_str_id:str
            ):

        self.code_populator_id = code_populator_id
        self.code = code
        self.terminology = terminology
        self.main_str_id = main_str_id
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class beceptivities_class(base_table_class):
    __tablename__ = 'beceptivities'
    __table_args__ = (
            UniqueConstraint('name'),
            UniqueConstraint('name', 'prompt', 'min_val', 'max_val'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    name = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    min_val = Column(Float, nullable=False)
    max_val = Column(Float, nullable=False)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , name:str
            , prompt:str
            , min_val:str=0.0
            , max_val:float=10.0
            ):

        self.name = name
        self.prompt = prompt
        self.min_val = min_val
        self.max_val = max_val
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class str_beceptivities_class(base_table_class):
    __tablename__ = 'str_beceptivities'
    __table_args__ = (
            UniqueConstraint('beceptivity_id', 'str'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    beceptivity_id = Column(Text, ForeignKey(f'{odc.schema}.beceptivities.id'), nullable=False)
    # I did not use str_id and denormalize into the strs table because this may be a concept that we never use
    # for anything else, and may not want to keep or generate its vector. So, let's just store the string here.
    # I hope I don't regret this later. <sigh>
    str = Column(Text, nullable=False)
    val = Column(Float)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , beceptivity_id:str
            , str:str
            , val:float
            ):

        self.beceptivity_id = beceptivity_id
        self.str = str
        self.val = val
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class manual_content_class(base_table_class):
    __tablename__ = 'manual_content'
    __table_args__ = (
            UniqueConstraint('generator_str', 'generator_type', 'embedder_meta_id', 'vec_type'),
            UniqueConstraint('purpose'),
            {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    purpose = Column(Text, nullable=False)
    generator_str = Column(Text, nullable=False)
    generator_type = Column(Text, nullable=False)
    embedder_meta_id = Column(Text, ForeignKey(f'{odc.schema}.embedder_metas.id'), nullable=False)
    db_params = Column(Text)
    vec = Column(Vector(odc.vector_size), nullable=False)
    vec_type = Column(Text, nullable=False) # like max, min, cls

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , purpose:str
            , generator_str:str
            , generator_type:str
            , db_params:str
            , vec_type:str
            , vec:Vector
            ):

        self.purpose = purpose
        self.generator_str = generator_str
        self.generator_type = generator_type
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.db_params = db_params
        self.vec = Tensor.cpu(vec).flatten()
        self.vec_type = vec_type
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class strs_class(base_table_class):
    __tablename__ = 'strs'
    __table_args__ = (
            UniqueConstraint('str'),
            {'schema': f'{odc.schema}'}
        )


    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    str = Column(Text, nullable=False)
    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , the_str:str
            , change_case_to:case_change=case_change.none
            ):

        if change_case_to == case_change.lower:
            self.str = str(the_str).lower()
        elif change_case_to == case_change.upper:
            self.str = str(the_str).upper()
        else:
            self.str = the_str
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class code_strs_class(base_table_class):
    __tablename__ = 'code_strs'
    __table_args__ = (
        # Need priority as a constraint?
        UniqueConstraint('code_id', 'str_id'),
        {'schema': f'{odc.schema}'}
        )
    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    code_id = Column(Text, ForeignKey(f'{odc.schema}.codes.id'), nullable=False)
    str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)
    priority = Column(Integer)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , code_id:str
            , str_id:str
            , priority:int
            ):

        self.code_id = code_id
        self.str_id = str_id
        self.priority = priority
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


# I have discovered this seems to denote beceptivity (specificity) of the term -- actually not sure.
def tensor_abs_max(the_tensor:Tensor):
    return torch.max(torch.abs(the_tensor)).item()

class str_vectors_class(base_table_class):
    __tablename__ = 'str_vectors'
    __table_args__ = (
        UniqueConstraint('str_id', 'embedder_meta_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)
    embedder_meta_id = Column(Text, ForeignKey(f'{odc.schema}.embedder_metas.id'), nullable=False)
    # Vectors
    cls = Column(Vector(odc.vector_size))
    mean = Column(Vector(odc.vector_size))
    max = Column(Vector(odc.vector_size))
    cls_max = Column(Float)
    mean_max = Column(Float)
    max_max = Column(Float)
    # Vector info
    dim = Column(Integer)
    orig_shape = Column(ARRAY(Integer))

    def __init__(self,
            enhanced_db_obj:enhanced_db_class,
            str_id:str,
            cls:Vector=None,
            the_mean:Vector=None,
            the_max:Vector=None,
            cls_max:float=None,
            mean_max:float=None,
            max_max:float=None,
            the_dim:int=None,
            orig_shape:list[int]=None
            ):
        self.str_id = str_id
        # If you want a different embedder, pass a different enhanced db obj
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.cls = cls
        self.mean = the_mean
        self.max = the_max
        self.cls_max = cls_max
        self.mean_max = mean_max
        self.max_max = max_max
        self.dim = the_dim
        self.orig_shape = orig_shape
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)

        # If the embedding has been populated, just return -- nothing to do
        if self.cls is not None and len(self.cls) > 0:
            return

        # Otherwise, do the embedding
        # Do the embedding
        # First need to get the associated string
        with enhanced_db_obj.session_class() as session:
            str_obj = session.query(strs_class).filter(strs_class.id == self.str_id).first()
            # Get the embedding
            embedding_obj = ec(str_obj.str, enhanced_db_obj.embedder_execution_obj)
            # Update the str_vector_object
            self.cls = Tensor.cpu(embedding_obj.cls_embedding).flatten()
            self.mean = Tensor.cpu(embedding_obj.mean_pooling).flatten()
            self.max = Tensor.cpu(embedding_obj.max_pooling).flatten()

            # Get the max ebsolute value of the elements in the vector, which
            # I have discovered seems to denote specificity of the term.
            self.cls_max = tensor_abs_max(self.cls)
            self.mean_max = tensor_abs_max(self.mean)
            self.max_max = tensor_abs_max(self.max)

            self.dim = Tensor.cpu(embedding_obj.cls_embedding).dim()
            self.orig_shape = Tensor.cpu(embedding_obj.cls_embedding).shape
            # Commit to the DB.
            session.merge(self)
            session.commit()
        # All done
        return


class str_expansion_set_summary_vectors_class(base_table_class):
    __tablename__ = 'str_expansion_set_summary_vectors'
    __table_args__ = (
        UniqueConstraint('str_expansion_set_id', 'embedder_meta_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    str_expansion_set_id = Column(Text, ForeignKey(f'{odc.schema}.str_expansion_set.id'), nullable=False)
    # The summary vectors may not be generated by an embedder, but the underlying
    # vectors that are being summarized will have been generated by an embedder,
    # so either way we want to know which embedder it was.
    embedder_meta_id = Column(Text, ForeignKey(f'{odc.schema}.embedder_metas.id'), nullable=False)
    orig_and_exp_mean = Column(Vector(odc.vector_size))
    orig_and_exp_max = Column(Vector(odc.vector_size))
    # Summary vectors of just the expansion strings PLUS including the original string
    all_mean = Column(Vector(odc.vector_size))
    all_max = Column(Vector(odc.vector_size))
    orig_and_exp_mean_max = Column(Float)
    orig_and_exp_max_max = Column(Float)
    all_mean_max = Column(Float)
    all_max_max = Column(Float)
    # Summary vetor Info
    dim = Column(Integer)
    orig_shape = Column(ARRAY(Integer))

    def __init__(self,
            enhanced_db_obj:enhanced_db_class,
            str_expansion_set_id:str,
            orig_and_exp_mean:Vector = None,
            orig_and_exp_max:Vector = None,
            all_mean:Vector=None,
            all_max:Vector=None,
            orig_and_exp_mean_max:float=None,
            orig_and_exp_max_max: float=None,
            all_mean_max:float=None,
            all_max_max:float=None,
            the_dim:int=None,
            orig_shape:list[int]=None
            ):
        self.str_expansion_set_id = str_expansion_set_id
        # If you want a different embedder_meta_id, use a different enhanced_db_obj
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.orig_and_exp_max = orig_and_exp_max
        self.orig_and_exp_mean = orig_and_exp_mean
        self.orig_and_exp_mean_max = orig_and_exp_mean_max
        self.orig_and_exp_max_max = orig_and_exp_max_max
        self.all_mean = all_mean
        self.all_max = all_max
        self.all_mean_max = all_mean_max
        self.all_max_max = all_max_max
        self.dim = the_dim
        self.orig_shape = orig_shape
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)

        # Note: We do not populate the vectors with this routine if the vectors are not yet
        # populated, because we don't know when called if all the strings have been populated
        # as part of the expansion set. We could assume so, but I'd rather not do that right now.


class code_str_expansion_set_summary_vectors_class(base_table_class):
    __tablename__ = 'code_str_expansion_set_summary_vectors'
    __table_args__ = (
        UniqueConstraint('code_summary_vectors_id', 'str_expansion_set_id', 'embedder_meta_id'),
        {'schema': f'{odc.schema}'}
    )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    code_summary_vectors_id = Column(Text, ForeignKey(f'{odc.schema}.code_summary_vectors.id'), nullable=False)
    str_expansion_set_id = Column(Text, ForeignKey(f'{odc.schema}.str_expansion_set.id'), nullable=False)
    # NOTE: The embedder MUST come from the associated code_summary_vectors object
    embedder_meta_id = Column(Text, ForeignKey(f'{odc.schema}.embedder_metas.id'), nullable=False)
    # Summary vectors of just the expansion strings NOT including the original string
    exp_only_mean = Column(Vector(odc.vector_size))
    exp_only_max = Column(Vector(odc.vector_size))
    # Summary vectors of just the expansion strings PLUS including the original string
    # PLUS the code strings
    all_mean = Column(Vector(odc.vector_size))
    all_max = Column(Vector(odc.vector_size))
    # Max element in each summary vector type (serves as specificity metric)
    exp_only_mean_max = Column(Float)
    exp_only_max_max = Column(Float)
    all_mean_max = Column(Float)
    all_max_max = Column(Float)
    # NOTE: Summary vector info (dim, orig_shape) MUST come from the associated code_summary_vectors object


    def __init__(self,
            enhanced_db_obj:enhanced_db_class,
            code_summary_vectors_id,
            str_expansion_set_id: str,
            exp_only_mean: Vector,
            exp_only_max: Vector,
            all_mean: Vector,
            all_max: Vector,
            exp_only_mean_max: float,
            exp_only_max_max: float,
            all_mean_max: float,
            all_max_max: float
            ):

        self.code_summary_vectors_id = code_summary_vectors_id
        self.str_expansion_set_id = str_expansion_set_id
        # If you want a different embedder_meta_id, use a different enhanced_db_obj
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.exp_only_mean = exp_only_mean
        self.exp_only_max = exp_only_max
        self.all_mean = all_mean
        self.all_max = all_max
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)

        # Note: We do not populate the vectors with this routine if the vectors are not yet
        # populated, because we don't know when called if all the strings have been populated
        # as part of the expansion set. We could assume so, but I'd rather not do that right now.


class code_summary_vectors_class(base_table_class):
    __tablename__ = 'code_summary_vectors'
    __table_args__ = (
        UniqueConstraint('code_id', 'embedder_meta_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    code_id = Column(Text, ForeignKey(f'{odc.schema}.codes.id'), nullable=False)
    # str_expansion_set_id = Column(Text, ForeignKey(f'{odc.schema}.str_expansion_set.id'))
    # The summary vectors may not be generated by an embedder, but the underlying
    # vectors that are being summarized will have been generated by an embedder,
    # so either way we want to know which embedder it was.
    embedder_meta_id = Column(Text, ForeignKey(f'{odc.schema}.embedder_metas.id'), nullable=False)
    # Summary vectors of just the expansion strings NOT including the original string
    mean = Column(Vector(odc.vector_size))
    max = Column(Vector(odc.vector_size))
    mean_max = Column(Float)
    max_max = Column(Float)
    '''
    # Summary vectors of just the expansion strings NOT including the original string
    exp_only_mean = Column(Vector(odc.vector_size))
    exp_only_max = Column(Vector(odc.vector_size))
    # Summary vectors of just the expansion strings PLUS including the original string
    all_mean = Column(Vector(odc.vector_size))
    all_max = Column(Vector(odc.vector_size))
    '''
    # Summary vector info
    dim = Column(Integer)
    orig_shape = Column(ARRAY(Integer))

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 code_id:str,
                 the_mean:Vector=None,
                 the_max:Vector=None,
                 # exp_only_mean:Vector=None,
                 # exp_only_max:Vector=None,
                 # all_mean:Vector=None,
                 # all_max:Vector=None,
                 mean_max:float=None,
                 max_max:float=None,
                 the_dim:int=None,
                 orig_shape:list[int]=None
                 ):
        self.code_id = code_id
        # self.str_expansion_set_id = str_expansion_set_id
        # If you want a different embedder_meta_obj, use a different enhanced_db_obj
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.mean = the_mean
        self.max = the_max
        #self.exp_only_mean = exp_only_mean
        #self.exp_only_max = exp_only_max
        #self.all_mean = all_mean
        #self.all_max = all_max
        self.mean_max = mean_max
        self.max_max = max_max
        self.dim = the_dim
        self.orig_shape = orig_shape
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)

        # Note: We do not populate the vectors with this routine if the vectors are not yet
        # populated, because we don't know when called if all the strings have been populated
        # as part of the expansion set. We could assume so, but I'd rather not do that right now.


class str_expansion_set_populator_class(base_table_class):
    __tablename__ = 'str_expansion_set_populator'
    __table_args__ = (
        UniqueConstraint('db_params', 'llm_params', 'style', 'style_version', 'str_selector', 'str_selector_type'),
        UniqueConstraint('name'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    # datetime = Column(DateTime, default=lambda: make_datetime())
    datetime = Column(TIMESTAMP(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    # Name to easily and *uniquely* reference this expansion
    name = Column(Text, nullable=False)
    # What are the params of the database object creator?
    db_params = Column(Text, nullable=False)
    # What is the terminology, code_set, or relationship used to get the strings needing expansion?
    # Did not want to make this a foreign key relationship because I was concerned this could lead
    # to a situation where the populator was forced to be deleted if the strings were
    # deleted, but we might want to hang onto the content.
    str_selector = Column(Text, nullable=False)
    # What is the code selector type -- terminology, codes_set, or rel?.
    str_selector_type = Column(Text, nullable=False)
    # What are the params of the LLM connection to the LLM that will give us the expansions
    llm_params = Column(Text, nullable=False)
    # What is the prompt to get these expansions
    prompt = Column(Text)
    # What is the style
    style = Column(Text, nullable=False)
    # What are the prompt placeholders to be replaced with content?
    placeholders_json = Column(Text)
    # What is the style version
    style_version = Column(Float, nullable=False)
    notes = Column(Text)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , name:str
            , db_params:str
            , str_selector:str
            , str_selector_type:str
            , llm_params:str
            , prompt:str
            , style:str
            , style_version:float
            , placeholders:plc=None
            , notes:str=None
            ):
        self.name = name
        self.db_params = db_params
        self.str_selector = str_selector
        self.str_selector_type = str_selector_type
        self.llm_params = llm_params
        self.prompt = prompt
        self.style = style
        self.style_version = style_version
        if placeholders is None:
            self.placeholders_json = su.jsonpickle_dumps(plc())
        else:
            self.placeholders_json = su.jsonpickle_dumps(placeholders)

        self.notes = notes
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


# This defines the expansion string set and provides an ID that
# is used to get all the strings that comprise the string set
# which are stored in str_expansion_set_strs_class
class str_expansion_set_class(base_table_class):

    __tablename__ = 'str_expansion_set'
    __table_args__ = (
        UniqueConstraint('orig_str_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    str_expansion_set_populator_id = Column(Text, ForeignKey(f'{odc.schema}.str_expansion_set_populator.id'))
    orig_str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , str_expansion_set_populator_id:str
            , orig_str_id:str
            ):

        # self.id = make_id(id)
        self.str_expansion_set_populator_id = str_expansion_set_populator_id
        self.orig_str_id = orig_str_id
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


# This identifies the child strings that are included in the expansion string set
class str_expansion_set_strs_class(base_table_class):
    __tablename__ = 'str_expansion_set_strs'
    __table_args__ = (
        UniqueConstraint('str_expansion_set_id', 'expansion_str_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    str_expansion_set_id = Column(Text, ForeignKey(f'{odc.schema}.str_expansion_set.id'), nullable=False)
    expansion_str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)
    
    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , str_expansion_set_id:str
            , expansion_str_id:str
            ):

        self.str_expansion_set_id = str_expansion_set_id
        self.expansion_str_id = expansion_str_id
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class code_sets_populator_class(base_table_class):
    __tablename__ = 'code_sets_populator'
    __table_args__ = (
        UniqueConstraint('set_name'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    set_name = Column(Text, nullable=False)
    # What are the params of the database object creator?
    db_params = Column(Text)
    query = Column(Text, nullable=False)

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 set_name:str,
                 db_params:str,
                 query:str
                 ):
        self.set_name = set_name
        self.db_params = db_params
        self.query = query
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class code_sets_class(base_table_class):
    __tablename__ = 'code_sets'
    __table_args__ = (
        UniqueConstraint('set_name', 'code_id'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    set_name = Column(Text, nullable=False)
    code_id = Column(Text, ForeignKey(f'{odc.schema}.codes.id'), nullable=False)

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 set_name:str,
                 code_id:str
                 ):
        self.set_name = set_name
        self.code_id = code_id
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class rel_code_matches_populator_class(base_table_class):
    __tablename__ = 'rel_code_matches_populator'
    __table_args__ = (
        UniqueConstraint(
            'embedder_meta_id'
            , 'match_from_rel_populator_id'
            , 'match_from_rel'
            , 'match_obj_main_str'
            , 'match_obj_expansion_summary_vec'
            , 'match_code_main_str'
            , 'match_code_other_strs'
            , 'match_code_summary_vec'
            , 'match_code_expansion_summary_vec'
            , 'expanion_str_styles_json'
            , 'match_to_code_set_name'
            ),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    db_obj_params = Column(Text, nullable=False)
    embedder_meta_id = Column(Text, nullable=False)
    match_from_rel_populator_id = Column(Text, ForeignKey(f'{odc.schema}.rels_populator.id'), nullable=False)
    match_from_rel = Column(Text, nullable=False)
    match_obj_main_str = Column(Boolean, nullable=False)
    match_obj_expansion_summary_vec = Column(Boolean, nullable=False)
    match_code_main_str = Column(Boolean, nullable=False)
    match_code_other_strs = Column(Boolean, nullable=False)
    match_code_summary_vec = Column(Boolean, nullable=False)
    match_code_expansion_summary_vec = Column(Boolean, nullable=False)
    vec_to_use = Column(Text, nullable=False)
    # I could hvae done this as an array, but I'm worried I might need more flexibility in the future.
    expanion_str_styles_json = Column(Text, nullable=False)
    match_to_code_set_name = Column(Text, nullable=False)

    def __init__(self,
                enhanced_db_obj:enhanced_db_class,
                db_obj_params:str,
                match_from_rel_populator_id:str,
                match_from_rel:str,
                match_obj_main_str:str,
                match_obj_expansion_summary_vec:bool,
                match_code_main_str:bool,
                match_code_other_strs:bool,
                match_code_summary_vec:bool,
                match_code_expansion_summary_vec:bool,
                vec_to_use:str,
                expanion_str_styles_json:str,
                match_to_code_set_name:str
                ):
        self.db_obj_params = db_obj_params
        # If you want a different embedder meta_id, use a different enhanced_db_obj
        self.embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id
        self.match_from_rel_populator_id = match_from_rel_populator_id
        self.match_from_rel = match_from_rel
        self.match_obj_main_str = match_obj_main_str
        self.match_obj_expansion_summary_vec = match_obj_expansion_summary_vec
        self.match_code_main_str = match_code_main_str
        self.match_code_other_strs = match_code_other_strs
        self.match_code_summary_vec = match_code_summary_vec
        self.match_code_expansion_summary_vec = match_code_expansion_summary_vec
        self.vec_to_use = vec_to_use
        self.expanion_str_styles_json = expanion_str_styles_json
        self.match_to_code_set_name = match_to_code_set_name
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class rel_code_matches_class(base_table_class):
    __tablename__ = 'rel_code_matches'
    __table_args__ = (
        # Each rel_obj_str_id may be in multiple times (because multiple matched codes by rank)
        # but each rel_obj_str_id should only have a single match to a code_id per matches populator,
        # and each rel_obj_str associated ranking should only occur once.
        # But, don't want code and ranking in the same contraint, or could end up with code in there twice for same str
        # just with different rankings.
        UniqueConstraint('rel_code_matches_populator_id', 'match_from_rel_obj_str_id', 'matched_code_id'),
        UniqueConstraint('rel_code_matches_populator_id', 'match_from_rel_obj_str_id', 'ranking'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    rel_code_matches_populator_id = Column(Text, ForeignKey(f'{odc.schema}.rel_code_matches_populator.id'), nullable=False)
    match_from_rel_obj_str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)
    matched_code_id = Column(Text, ForeignKey(f'{odc.schema}.codes.id'), nullable=False)
    ranking = Column(Integer, nullable=False)
    distance = Column(Float, nullable=False)

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 rel_code_matches_populator_id,
                 match_from_rel_obj_str_id:str,
                 matched_code_id:str,
                 ranking:int,
                 distance:float
                 ):
        self.rel_code_matches_populator_id = rel_code_matches_populator_id
        self.match_from_rel_obj_str_id = match_from_rel_obj_str_id
        self.matched_code_id = matched_code_id
        self.ranking = ranking
        self.distance = distance
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class rels_populator_class(base_table_class):
    # TODO: Make a field that is hash of the important fields and prevent update if hash differs unless explicitly requested to update, likely through a flag in the __init__ params.
    __tablename__ = 'rels_populator'
    __table_args__ = (
        UniqueConstraint('name'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    # datetime = Column(DateTime, default=lambda: make_datetime())
    datetime = Column(TIMESTAMP(timezone=True), server_default=text('CURRENT_TIMESTAMP'))
    # Name to easily and *uniquely* reference this relationship
    name = Column(Text, nullable=False)
    # What are the params of the database object creator?
    db_params = Column(Text)
    # What is the terminology or code_set used to get the codes needing a relationship?
    # Did not want to make this a foreign key relationship because I was concerned this could lead
    # to a situation where the populator was forced to be deleted if the codes from that terminology were
    # deleted, but we might want to hang onto the content.
    code_selector = Column(Text)
    # What is the code selector type -- terminology or codes_set?.
    code_selector_type = Column(Text)
    # What are the params of the LLM object creator?
    llm_params = Column(Text)
    # What is the object holding configs about each relationship?
    rels_prompt_obj_json = Column(Text)
    # What is the prompt if the minimum required beceptivity is not met?
    notes = Column(Text)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , name
            , db_params:str
            , code_selector:str
            , code_selector_type
            , llm_params:str
            , rels_prompt_obj:rspc
            , notes:str=None
            ):
        # print("Got to rels populator init")
        self.name = name
        self.db_params = db_params
        self.code_selector = code_selector
        self.code_selector_type = code_selector_type
        self.llm_params = llm_params
        self.rels_prompt_obj_json = rels_prompt_obj.params # jsonpickle.dumps(rels_prompt_obj)
        self.notes = notes

        # print("About to upsert rels_populator")
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)
        # print("rels populator upserted")


class rels_class(base_table_class):
    __tablename__ = 'rels'
    __table_args__ = (
        UniqueConstraint('subj_code_id', 'rels_populator_id', 'rel', 'obj_str_id'),
        {'schema': f'{odc.schema}'}
        )
    subj_code_model = relationship("codes_class")
    obj_code_model = relationship("strs_class")

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    subj_code_id = Column(Text, ForeignKey(f'{odc.schema}.codes.id'), nullable=False)
    rels_populator_id = Column(Text, ForeignKey(f'{odc.schema}.rels_populator.id'), nullable=False)
    rel = Column(Text, nullable=False)
    rels_populator_name = Column(Text, ForeignKey(f'{odc.schema}.rels_populator.name'))
    obj_str_id = Column(Text, ForeignKey(f'{odc.schema}.strs.id'), nullable=False)
    priority = Column(Float)

    def __init__(
            self
            , enhanced_db_obj:enhanced_db_class
            , subj_code_id:str
            , rels_populator_id:str
            , rel:str
            , rels_populator_name:str
            , obj_str_id:str
            , priority:int
            ):

        self.subj_code_id = subj_code_id
        self.rels_populator_id = rels_populator_id
        self.rel = rel
        self.rels_populator_name = rels_populator_name
        self.obj_str_id = obj_str_id
        self.priority = priority
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class custom_table_generators_class(base_table_class):
    __tablename__ = 'custom_table_generators'
    __table_args__ = (
        UniqueConstraint('name', 'ctg_version', 'ctg_code_selector_type', 'ctg_code_selector', 'ctg_code_placeholder', 'ctg_dest_table', 'ctg_query', 'ctg_dest_code_field'),
        {'schema': f'{odc.schema}'}
        )
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    name = Column(Text, nullable=False)
    ctg_version = Column(Text, nullable=False)
    ctg_code_selector_type = Column(Text, nullable=False)
    ctg_code_selector = Column(Text, nullable=False)
    ctg_code_placeholder = Column(Text, nullable=False)
    ctg_dest_table = Column(Text, nullable=False)
    ctg_query = Column(Text, nullable=False)
    ctg_dest_code_field = Column(Text, nullable=False)
    datetime = Column(TIMESTAMP(timezone=True), server_default=text('CURRENT_TIMESTAMP'))

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 name:str,
                 ctg_version:str,
                 ctg_code_selector_type:str,
                 ctg_code_selector:str,
                 ctg_dest_table:str,
                 ctg_query:str,
                 ctg_code_placeholder:str = '',
                 ctg_dest_code_field:str='',
                 datetime=None
                 ):
        self.name = name
        self.ctg_version = ctg_version
        self.ctg_code_selector_type = ctg_code_selector_type
        self.ctg_code_selector = ctg_code_selector
        self.ctg_code_placeholder = ctg_code_placeholder
        self.ctg_dest_table = ctg_dest_table
        self.ctg_query = ctg_query
        self.ctg_dest_code_field = ctg_dest_code_field
        self.datetime = datetime
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class populator_orchestrations_class(base_table_class):
    __tablename__ = 'populator_orchestrations'
    __table_args__ = (
        # UniqueConstraint('po_type', 'po_name', 'po_content', 'datetime'),
        UniqueConstraint('po_type', 'po_name', 'po_content'),
        {'schema': f'{odc.schema}'}
        )

    # id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)
    id = Column(Text, primary_key=True, server_default = text("gen_random_uuid()"), nullable=False)
    po_type = Column(Text, nullable=False)
    po_name = Column(Text, nullable=False)
    po_content = Column(Text, nullable=False)
    datetime = Column(TIMESTAMP(timezone=True), server_default=text('CURRENT_TIMESTAMP'))

    def __init__(self,
                 enhanced_db_obj:enhanced_db_class,
                 po_type:str,
                 po_name:str,
                 po_content:str,
                 datetime=None
                 ):
        self.po_type = po_type
        self.po_name = po_name
        self.po_content = po_content
        self.datetime = datetime
        upsert_not_none_fields_only_via_unique_constraints(enhanced_db_obj, self)


class base_db_class:

    def __init__(
            self
            , connection_string:str=None
            , engine_options_dict:dict=None
            ):
        """
        Initialize the database connection to be used by SQLAlchemy
        :param connection_string: Should be SQLAlchemy-compatible, like this if using psycopg -- "postgresql+psycopg://user:password@host:port/dbname", -- default is the config connection string.
        :param engine_options_dict: dictionary of key-value pairs that represent connection options, like echo or pool. Default or None will be treated is an echo False.
        """

        # Make the engine, which is really the db connection.
        # If they gave us a connection string, use it.
        if connection_string:
            final_connection_string = connection_string
        else:
            final_connection_string = odc.connection_string

        final_engine_options_dict = engine_options_dict
        if final_engine_options_dict is None:
            final_engine_options_dict = {"echo": False}
        self.engine = create_engine(final_connection_string, **final_engine_options_dict)

        # Make a class that is bound to the engine. Interesting this is how it works.
        # If I set expire_on_commit to False, then if I commit and then close a session, the objects
        # won't have empty properties. The properties will be dirty, but they will be retained. Then,
        # to reattach them to the DB, I have to add them back into a session. I actually think this is the desired
        # behavior. If not desired, a session can be created that overrides this default value.
        self.session_class = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Make sure all tables are created
        dec_base.metadata.create_all(self.engine)


    def do_query(
            self
            , query: str
            , query_params: dict
            , as_role=None
            ) -> (bool, Result):

        try:
            with self.session_class() as session:
                # Execute the query with parameters
                results = session.execute(text(query), query_params).fetchall()
        except Exception as e:
            debug.log(__file__, f"Could not execute query.\nError was: {e}\n{query}\nwith params\n{query_params}\n")
            return False, None

        return True, results


    def do_no_result_query(
            self
            , query: str
            , query_params: dict
            , as_role=None
            ) -> bool:

        try:
            with self.session_class() as session:
                # Execute the query with parameters
                session.execute(text(query), query_params)
                session.commit()

        except Exception as e:
            debug.log(__file__, f"Could not execute query.\nError was: {e}\n{query}\nwith params\n{query_params}\n")
            return False

        return True

    def do_no_result_query_with_change_count(
            self
            , query: str
            , query_params: dict
            ) -> bool:

        try:
            with self.session_class() as session:
                # Execute the query with parameters
                result:CursorResult = session.execute(text(query), query_params)
                change_count = result.rowcount
                session.commit()

        except Exception as e:
            debug.log(__file__, f"Could not execute query.\nError was: {e}\n{query}\nwith params\n{query_params}\n")
            return False, 0

        return True, change_count


    # Does the query contain anything that could remove data?
    def contains_destructive(query: str) -> bool:
        DESTRUCTIVE = (
            DeleteStmt
            , DropStmt
            , TruncateStmt
            , UpdateStmt
            , AlterTableStmt
            )
        tree = parse_sql(query)

        for stmt in tree:
            for node in stmt.traverse():
                if isinstance(node, DESTRUCTIVE):
                    return True
        return False

"""
    @contextmanager
    def _query_context(self, as_role: str | None):
        with self.session_class() as session:
            with session.begin():
                # --- SET LOCAL ROLE ---
                if as_role:
                    session.execute(
                        text("SET LOCAL ROLE :role"),
                        {"role": as_role}
                    )

                # --- application_name ---
                app_name = oc.app_name
                if hasattr(g, "ks_endpoint"):
                    app_name += f"::{g.ks_endpoint}"

                    session.execute(
                        text("SET LOCAL application_name = :app_name"),
                        {"app_name": app_name}
                    )

                    # --- user context ---
                    if hasattr(g, "user") and g.user:
                        session.execute(
                            text("SET LOCAL app.user_id = :user_id"),
                            {"user_id": str(g.user)}
                        )
                    yield session
"""

class enhanced_db_class(base_db_class):

    _embedders: dict[str, stc] = {}  # Store loaded embedders
    _embedders_use_count = {}  # Stores active use count for each embedder

    def __init__(
            self
            , connection_string:str=None
            , engine_options_dict=None
            , embedder_meta_src:str=None
            , embedder_meta_src_location:str=None
            ):
        """
        Initialize the database connection to be used by SQLAlchemy
        :param connection_string: Should be SQLAlchemy-compatible, like this if using psycopg -- "postgresql+psycopg://user:password@host:port/dbname", -- default is the config connection string.
        :param engine_options_dict: dictionary of key-value pairs that represent connection options, like echo or pool. Default is an echo False.
        :param embedder_meta_src: string with name of embedder
        :param embedder_meta_src_location: string pointing to where to find the embedder
        """
        super().__init__(connection_string=connection_string, engine_options_dict=engine_options_dict)

        # We will need to do some database work, and for that we need a session
        session = self.session_class()

        # We MUST have gotten an embedder_meta_src
        if not embedder_meta_src:
            msg = "ERROR: Did not receive embedder_meta_src"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)
        else:
            self.embedder_meta_src = embedder_meta_src

        # If they did not pass us an embedder_meta_src_location, then
        # let's query the database to see if one is already stored in the
        # database
        if not embedder_meta_src_location:
            embedder_meta_src_location = query_for_embedder_src_location(self, self.embedder_meta_src)

        # If we still don't have an embedder_meta_src_location, error,
        # otherwise, set the self.embedder_meta_src_location
        if not embedder_meta_src_location:
            msg = "ERROR: Did not receive embedder_meta_src_location"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)
        else:
            self.embedder_meta_src_location = embedder_meta_src_location

        # We need to make sure that embedder_meta_src is in the DB,
        # and if not, to add it.
        # Then use that info to instantiate an embedder_meta_class object.
        # (next line does all this).
        self.embedder_meta_obj = embedder_metas_class(self, self.embedder_meta_src, self.embedder_meta_src_location)

        # Close the session, since I believe we don't need it anymore.
        session.close()

        # THIS IS PROBABLY NOT WANTED IN SOME FUTURE STATE -- BUT...
        # Just to reduce risk of mismatch of embedders, ensure that the configged embedder
        # is the embedder we have. I specifically wanted to allow for multiple embedders,
        # but ensuring every query and use uses the right embedder right now I'm not sure is
        # ensured throughout. So, try to enforce the use of one embedder at a time, for now,
        # and that it's the configged embedder. This doesn't make sense with the tracking
        # of multiple embedders above -- the idea was to allow for multiple embedders, but
        # for safety, try to limit to one configged embedder. This won't be perfect, and need
        # to fix later so this is not needed.
        if self.embedder_meta_obj.src != odc.default_embedder_meta_src:
            msg = "ERROR: For now, need to use only the default embedder."
            raise Exception(msg)

        # Make the params dict, but be sure to get rid of the password in the connection string.
        sanitized_connection_dict = {
            'drivername': self.engine.url.drivername,
            'username': self.engine.url.username,
            'password': oc.password_replacer,
            'host': self.engine.url.host,
            'port': self.engine.url.port,
            'database': self.engine.url.database,
            'query': self.engine.url.query
        }

        self.params = {'self': self.__class__.__name__, 'connection_string': sanitized_connection_dict,
                       'engine_options_dict': engine_options_dict, 'embedder_meta_src': self.embedder_meta_obj.src}
        self.params = su.jsonpickle_dumps(self.params)

        # Set this object up to get rid of unused embedders
        weak_ref = weakref.ref(self, embedder_cleanup)

        # Load embedder to the class, not the object, only if not already loaded
        if self.embedder_meta_obj.src not in enhanced_db_class._embedders:
            enhanced_db_class._embedders[self.embedder_meta_obj.src] = stc(self.embedder_meta_obj.src_location)

        # Now assign the embedder to this object
        self.embedder_execution_obj = enhanced_db_class._embedders[self.embedder_meta_obj.src]

        # If the item is not in the embedders count, then create the item in the count and set it to 0.
        if self.embedder_meta_obj.src not in enhanced_db_class._embedders_use_count:
            enhanced_db_class._embedders_use_count[self.embedder_meta_obj.src] = 0
        # Finally, increment the count of how many enhanced_db_class objects are using this embedder
        enhanced_db_class._embedders_use_count[self.embedder_meta_obj.src] += 1



############### FUNCTIONS ###################

# Convert string version of vector returned by Postgres to tensor
def vec_str_to_torch(vec_str):

    # Remove unwanted characters
    vec_str = str(vec_str).replace('[', '')
    vec_str = str(vec_str).replace(']', '')
    vec_str = str(vec_str).replace('{', '')
    vec_str = str(vec_str).replace('}', '')
    vec_str = str(vec_str).replace('_', '')
    vec_str = str(vec_str).replace(' ', '')


    # Split string to get values
    vec_vals = vec_str.split(',')
    new_vec_vals = []
    for vec_val in vec_vals:
        new_vec_vals.append(float(vec_val))

    # Convert list to tensor
    return torch.tensor(new_vec_vals)


# Given db_params (that include a sanitized param string without a DB password)
# substitute in the password and then get the database object.
def get_db_from_db_params(db_params:str) -> enhanced_db_class:
    # db_dict = jsonpickle.loads(db_params)
    db_dict = su.jsonpickle_loads(db_params)
    db_dict['connection_string']['password'] = odc.password
    connection_string = URL.create(**db_dict['connection_string'])
    engine_options_dict = db_dict['engine_options_dict']
    embedder_meta_src = db_dict['embedder_meta_src']
    return enhanced_db_class(connection_string, engine_options_dict, embedder_meta_src=embedder_meta_src)


def populate_code_and_strs(code_populators_obj:code_populators_class, str_expansion_set_id=None):

    # Make sure this object is legit populated.
    if not code_populators_obj:
        msg = 'ERROR: Exception raised! No code populators object.'
        debug.log(__file__, msg)
        raise Exception(msg)

    # Don't think I need this
    # dt = get_utc_now()

    # Do query, then loop through items and add them where appropriate
    enhanced_db_obj = get_db_from_db_params(code_populators_obj.db_obj_params)

    query_params = {'terminology': code_populators_obj.terminology}
    success, results = enhanced_db_obj.do_query(code_populators_obj.query, query_params)
    if not success:
        tskm.emit_status(f"NOT POPULATE TERMINOLOGY SUCCESS! {success}", print_also=gl_d)
        return
    elif not results:
        tskm.emit_status(f"NOTHING TO PROCESS! {results}",  print_also=gl_d)
        return

    # Set up object to track progress through the results
    if results:
        lpro = lprc('populate_code_and_strs', len(results), 100, True, status_report_functions=g_status_report_functions)

    # Iterate through results.
    for idx, row in enumerate(results):
        # Report progress -- will only print if at report increment
        lpro.report_progress(idx)

        if tskm.is_cancelled():
            tskm.emit_status("Cancelled population of terminology.")
            return

        # Populate code but don't yet know the main string id (unless we've already done this one)
        code_obj = codes_class(enhanced_db_obj=enhanced_db_obj, code_populator_id=code_populators_obj.id, code=row.code, terminology=code_populators_obj.terminology, main_str_id=None)

        # Populate str
        str_obj = strs_class(enhanced_db_obj, the_str=row.str)
        # Populate main_string_id property of the this_code object if appropriate.
        if row.priority == 1:
            with enhanced_db_obj.session_class() as session:
                code_obj.main_str_id = str_obj.id
                session.merge(code_obj)
                session.commit()
        # Populate code_str combo associated code and string
        code_str_obj = code_strs_class(enhanced_db_obj, code_obj.id, str_obj.id, row.priority)
        str_vector_obj = str_vectors_class(enhanced_db_obj, str_id=str_obj.id)


    if tskm.is_cancelled():
        tskm.emit_status("Cancelled population of terminology.")
        return
    
    # Codes and strings populated, so now reloop through codes and get summary vectors and populate them,
    # provided we got an embedder_meta_obj. We don't need the embedder, but if we didn't get an embedder, then
    # we wouldn't assume the vectors were populated for the related strings.
    if enhanced_db_obj.embedder_meta_obj:
        populate_code_summary_vectors(code_populators_obj)

    return


def populate_expansion_strs(espo:str_expansion_set_populator_class, llm_password):

    d = gl_d

    # Make sure this object is legit populated.
    if not espo:
        msg = 'ERROR: No expansion string object.'
        debug.log(__file__, msg)
        raise Exception(msg)

    # Do query, then loop through items and add them where appropriate
    # First need a database object
    enhanced_db_obj = get_db_from_db_params(espo.db_params)

    with enhanced_db_obj.session_class() as session:
        # Get the desired strs
        #TODO: Consider changing these to be .scalars().all() so that they return lists instead of tuples in order to fix type hinting. Just need to check downstream no issues if I do that.
        if espo.str_selector_type == 'terminology':
            expansion_str_descriptor = 'terminology code\'s string to be expanded'
            results:List[str] = session.query(codes_class).distinct().filter(codes_class.terminology == espo.str_selector).with_entities(codes_class.main_str_id).all()
        elif espo.str_selector_type == 'code_set':
            expansion_str_descriptor = 'code set code\'s string to be expanded'
            results:List[str] = session.query(codes_class).join(code_sets_class).distinct().filter(code_sets_class.set_name == espo.str_selector).with_entities(codes_class.main_str_id).all()
        elif espo.str_selector_type == 'rel':
            expansion_str_descriptor = 'relationship object string to be expanded'
            results:List[str] = session.query(rels_class).distinct().filter(rels_class.rels_populator_name == espo.str_selector).with_entities(rels_class.obj_str_id).all()
        else:
            expansion_str_descriptor = 'Something went wrong'
            msg = "ERROR: Got exception. Was query wrong? Something else?"
            debug.log(__file__, msg)
            raise Exception(msg)

    # Loop through every string ID and get the expansion string
    result_len = len(results)
    lpro = lprc('populate_expansion_strs', len(results), 100, True, status_report_functions=g_status_report_functions)
    tskm.emit_status(f"\n\nAbout to process {lpro.name} using LLM, got {lpro.list_length} to process.", print_also=gl_d)
    for top_idx, result in enumerate(results):
        lpro.report_progress(top_idx)

        if tskm.is_cancelled():
            tskm.emit_status("Cancelled population of expansion strings.")
            return

        str_id = result[0]
        debug.debug(f"\n\n#{top_idx} of {result_len}: Expanding id of {expansion_str_descriptor}: {str_id}", d=d)

        # Create string expansion set object prn and get the object
        seso = str_expansion_set_class(enhanced_db_obj, espo.id, str_id)

        # Have we expanded this string already? I think we should, for now, not allow multiple string expansions. I may late regret this but for now, it seems the right way. It doesn't seem symmetric to me with things like relationships, where it seems there may be a real chance that a better AI would give a better relationship set. In this case, I think expanding a string may be somewhat trivial. If we allow more than one expander for a string, I see lots of potential issues, like even just checking if the string has already been expanded. In some cases I might want to skip it if already present and only expand if some expansion doesn't exist. But, I'm not sure how to handle or keep track of all that. Therefore, I think best to assume only one expander for any string.
        with enhanced_db_obj.session_class() as session:
            existing = session.query(str_expansion_set_strs_class).filter(str_expansion_set_strs_class.str_expansion_set_id == seso.id).first()

            # If this one has been done, don't redo it, go to the next one.
            if existing:
                lpro.skip_count += 1
                debug.debug("Already exists", d=d)
                continue

            # Now we need the actual string. We'll only deal with the main string
            str_objs_to_expand = (session.query(strs_class).join(str_expansion_set_class).filter(str_expansion_set_class.orig_str_id == str_id).with_entities(strs_class.str).first())
            str_to_expand = str_objs_to_expand[0] if str_objs_to_expand else None
            debug.debug(f"String to be expanded is: {str_to_expand}", d=d)
            #str_to_expand = str(str_obj_to_expand.str)
            # continue

        # Ask the LLM for the expansions
        # Get LLM object
        llm_obj = llmm.get_llm_from_llm_params(espo.llm_params, llm_password)

        # Make the requisite rel prompt and rels prompt objects
        rel_prompt_obj = rpc(
            rel=f'has_expansion_strs_{espo.style}_v{espo.style_version}'
            , rel_prompt=espo.prompt # TODO: IS THIS CORRECT?
            , is_multi_resp=True
            )
        rels_prompt_obj = rspc(
            name='expansion_str_rel_prompt_obj'
            , rels=[rel_prompt_obj]
            , can_llm_output_json=llm_obj.llm_obj.can_output_json
            #, placeholders=jsonpickle.loads(espo.placeholders_json)
            , placeholders=su.jsonpickle_loads(espo.placeholders_json)
            , beceptivity_src_type=None # not relevant
            , beceptivity_instructions=None # not relevant
            )

        try:
            debug.debug("Asking LLM for expansion strings", d=d)
            llm_obj.get_and_process_response(rels_prompt_obj, {'concept': str_to_expand})
            debug.debug("Asked LLM for expansion strings", d=d)
            last_resp_items = copy.deepcopy(llm_obj.last_resp[rel_prompt_obj.rel])
            resp_item_count = len(last_resp_items)
            for inner_idx, resp_item in enumerate(last_resp_items):
                debug.debug(f"Got expansion string {inner_idx} of {resp_item_count}: {resp_item}", d=d)
                # Priority is the index + 1
                priority = inner_idx + 1
                # Add string if it doesn't exist
                expansion_str_obj = strs_class(enhanced_db_obj, resp_item)
                # Make string vector if we don't already have one
                vec_obj = str_vectors_class(enhanced_db_obj, expansion_str_obj.id)
                # Now make/store the expansion set string item
                esso = str_expansion_set_strs_class(enhanced_db_obj, str_expansion_set_id=seso.id, expansion_str_id=expansion_str_obj.id)
        except Exception as e:
            msg = f"ERROR: Got exception processing response with llm: {e}"
            debug.log(__file__, msg)
            # print(msg)
            if die_on_llm_failure:
                raise Exception(f"Exiting because set to die on llm failure")
    tskm.emit_status(f"DONE processing {lpro.name} using LLM with {lpro.list_length} to process.", print_also=d)

    return


def populate_str_summary_vectors(exp_populators_obj:str_expansion_set_populator_class):

    # Generate the enhanced_db_obj here from params to ensure the correct embedder.
    enhanced_db_obj = get_db_from_db_params(exp_populators_obj.db_params)

    # Handle different scenarios -- do they want us only to populate summary vectors
    # for a specific group of expansion sets (those populated by a specific populator)
    # or vectors for all unprocessed expansion sets?
    # Might make sense to always do summary vectors for all unprocessed expansion sets
    # but may be times when, for processing times, prefer not to.

    # If given a specific expansion set populator to process summary vectors for:
    if exp_populators_obj is not None:
        exp_pop_filter = 'AND sesp.name = :expansion_set_name'
        query_params = {'expansion_set_name': exp_populators_obj.name,
                        'embedder_meta_id': enhanced_db_obj.embedder_meta_obj.id}
    # If just updating all unprocessed expansion set summary vectors:
    else:
        exp_pop_filter = ''
        query_params = {'embedder_meta_id': enhanced_db_obj.embedder_meta_obj.id}

    # Loop through codes and get summary vectors and populate them.
    # TODO: Added :embedder_meta_id stuff to the joins -- check still okay. I don't know why wouldn't need this if more than one embedder.
    query = f'''
SELECT 
	ses.id AS str_expansion_set_id
	-- , string_agg(CAST(v.cls AS TEXT), '__sep__') AS concatted_vecs
	, CASE 
	    WHEN string_agg(CAST(v.cls AS TEXT), '__sep__') IS NOT NULL
		    AND string_agg(CAST(v.cls AS TEXT), '__sep__') <> '' 
		-- Double the value of the original string, but use both the CLS and the mean
		THEN MAX(CAST(sv.cls AS TEXT)) || '_sep_' || MAX(CAST(sv.mean AS TEXT)) || '_sep_' || string_agg(CAST(v.cls AS TEXT), '__sep__')
		ELSE MAX(CAST(sv.cls AS TEXT)) END
		AS concatted_vecs
 
FROM {odc.schema}.str_expansion_set ses
INNER JOIN {odc.schema}.strs orig_strs 
	ON orig_strs.id = ses.orig_str_id
INNER JOIN {odc.schema}.str_vectors sv
	ON sv.str_id = orig_strs.id AND sv.embedder_meta_id = :embedder_meta_id
INNER JOIN {odc.schema}.str_expansion_set_populator sesp
	ON ses.str_expansion_set_populator_id = sesp.id
INNER JOIN {odc.schema}.str_expansion_set_strs sess
	ON ses.id = sess.str_expansion_set_id
INNER JOIN {odc.schema}.str_vectors v
	ON sess.expansion_str_id = v.str_id
LEFT OUTER JOIN {odc.schema}.str_expansion_set_summary_vectors sessv
	ON sessv.str_expansion_set_id = ses.id AND sessv.embedder_meta_id = :embedder_meta_id
WHERE 
    1 = 1
	{exp_pop_filter}
	-- Not already processed the vectors
	AND sessv.orig_and_exp_mean IS NULL
	-- Must have the right embedder. Shouldn't really need this, but just to be sure
	AND v.embedder_meta_id = :embedder_meta_id
GROUP BY ses.id
-- Make sure no string is missing a calculated vector
HAVING SUM(CASE WHEN v.cls IS NULL THEN 1 ELSE 0 END) = 0
	-- Make sure at least one string has a vector calculated
	-- In other words, that the reason no string was missing a calculated vector is NOT that
	-- there was no string
	AND SUM(CASE WHEN v.cls IS NOT NULL THEN 1 ELSE 0 END) > 0
            '''

    count_query = f'''
            SELECT COUNT(*) as the_count FROM
                (
                {query}
                )count_sq1
            '''

    # Get count of items to process
    with enhanced_db_obj.session_class() as session:
        # Do query
        tskm.emit_status(f"Doing count query.", print_also=gl_d)
        results = session.execute(text(count_query), query_params).first()
        total_count = results.the_count
        tskm.emit_status(f"Count query done, count is: {total_count}.", print_also=gl_d)

    # Do query, then loop through items and add them where appropriate
    # IMPORTANT CAVEAT!!!
    # After I do the next query, it may look like I have what I need. However, since I am streaming results,
    # I will NOT have access to the desired results variable content once I'm outside this next "with" block.
    # So... ANYTHING that expects to use this results variable MUST be within this block. ALSO,
    # there can be NO writes in the same session from which I am reading. To do writes, open another session!!!
    with enhanced_db_obj.session_class() as session:
        # Do query
        tskm.emit_status(f"Doing main query.", print_also=gl_d)
        stmt = text(query).execution_options(stream_results=True)
        results = session.execute(stmt, query_params)
        if not results:
            msg = "NOT SUCCESS populating summary vectors!"
            debug.log(__file__, msg)
            return
        tskm.emit_status(f"Did main query.", print_also=gl_d)

        # Set up object to track progress through the results
        lpro = lprc('populate_str_summary_vectors', total_count, 100, True, status_report_functions=g_status_report_functions)

        # Iterate over rows one at a time
        for idx, row in enumerate(results):
            # Report progress -- will only print if at report increment
            lpro.report_progress(idx)

            # Any writes ensuing from this next line will happen in a new session, since that's how this next class works.
            sessvo = str_expansion_set_summary_vectors_class(
                enhanced_db_obj=enhanced_db_obj
                , str_expansion_set_id=row.str_expansion_set_id
            )
            # Don't populate if we've already done this one.
            if sessvo.orig_and_exp_mean is not None:
                lpro.skip_count += 1
                continue
            cls_vecs_str_list = row.concatted_vecs.split(oc.sep)
            cls_vecs_list = []
            for cls_str_vec in cls_vecs_str_list:
                cls_vecs_list.append(vec_str_to_torch(cls_str_vec))
            # Now get a single vector summarizing the CLS vectors
            # Now get average of the CLS tokens
            # Stack the list into a single tensor with shape of: (number of sentences, embedding dimension)
            stacked_cls_tokens = torch.stack(cls_vecs_list)
            # Calculate the mean along axis 0 (across the sentences)

            mean_cls_token = torch.mean(stacked_cls_tokens, dim=0)
            sessvo.orig_shape = mean_cls_token.shape
            mean_cls_token = mean_cls_token.flatten()
            max_cls_vals, max_cls_indices = torch.max(stacked_cls_tokens, dim=0)
            max_cls_token = max_cls_vals.flatten()
            sessvo.orig_and_exp_mean = mean_cls_token
            sessvo.orig_and_exp_max = max_cls_token
            sessvo.orig_and_exp_mean_max = tensor_abs_max(mean_cls_token)
            sessvo.orig_and_exp_max_max = tensor_abs_max(max_cls_token)
            sessvo.dim = mean_cls_token.dim()
            # OK, I've populated this object, but that was outside a session. So now, I need to create a session,
            # merge the object into the session, and then commit so it's in the database.
            with enhanced_db_obj.session_class() as obj_merger_session:
                obj_merger_session.merge(sessvo)
                obj_merger_session.commit()

    return


def populate_code_summary_vectors(code_populators_obj:code_populators_class):

    # I assume best to get enhanced_db_obj by loading
    # enhanced_db_obj from the ...populators_obj so that I have, theoretically for sure, th3
    # right embedder.
    # Do query, then loop through items and add them where appropriate
    enhanced_db_obj = get_db_from_db_params(code_populators_obj.db_obj_params)
    embedder_meta_id = enhanced_db_obj.embedder_meta_obj.id


    # Loop through codes and get summary vectors and populate them.
    # TODO: CHECK STILL WORKS SINCE ADDED EMBEDDER ID AS JOIN REQUIREMENTS AND ALSO parameterized sep
    query = f'''
        SELECT 
            cd.id AS code_id
            , string_agg(CAST(v.cls AS TEXT), :sep ORDER BY cs.priority) AS concatted_vecs 
        FROM {odc.schema}.codes cd
        INNER JOIN {odc.schema}.code_strs cs
            ON cd.id = cs.code_id
        INNER JOIN {odc.schema}.str_vectors v
            ON cs.str_id = v.str_id AND v.embedder_meta_id = :embedder_meta_id
		LEFT OUTER JOIN {odc.schema}.code_summary_vectors csvec
			ON cd.id = csvec.code_id AND csvec.embedder_meta_id = :embedder_meta_id
        WHERE 
            cd.terminology = :terminology
            -- Not already processed the vectors
            AND csvec.mean IS NULL
            -- But the strings have their vectors populated
        GROUP BY cd.id
        -- Make sure no string is missing a calculated vector
        HAVING SUM(CASE WHEN v.cls IS NULL THEN 1 ELSE 0 END) = 0
            -- Make sure at least one string has a vector calculated
            -- In other words, that the reason no string was missing a calculated vector is NOT that
            -- there was no string
            AND SUM(CASE WHEN v.cls IS NOT NULL THEN 1 ELSE 0 END) > 0
        '''
    query_params = {'terminology': code_populators_obj.terminology, 'sep': oc.sep, 'embedder_meta_id': embedder_meta_id}

    count_query = f'''
        SELECT COUNT(*) as the_count FROM
            (
            {query}
            )count_sq1
        '''

    # TODO: CHECK STILL WORKS SINCE ADDED EMBEDDER ID AS JOIN REQUIREMENTS
    count_query = f'''
        SELECT 
            count(cd.id) AS the_count
        FROM {odc.schema}.codes cd
        INNER JOIN {odc.schema}.code_strs cs
            ON cd.id = cs.code_id
        INNER JOIN {odc.schema}.str_vectors v
            ON cs.str_id = v.str_id AND v.embedder_meta_id = :embedder_meta_id 
		LEFT OUTER JOIN {odc.schema}.code_summary_vectors csvec
			ON cd.id = csvec.code_id AND csvec.embedder_meta_id = :embedder_meta_id
        WHERE 
            cd.terminology = :terminology
            -- Not already processed the vectors
            AND csvec.mean IS NULL
            -- But the strings have their vectors populated
        HAVING SUM(CASE WHEN v.cls IS NULL THEN 1 ELSE 0 END) = 0
            -- Make sure at least one string has a vector calculated
            -- In other words, that the reason no string was missing a calculated vector is NOT that
            -- there was no string
            AND SUM(CASE WHEN v.cls IS NOT NULL THEN 1 ELSE 0 END) > 0
        '''

    # Get count of items to process
    with enhanced_db_obj.session_class() as session:
        # Do query
        tskm.emit_status(f"Doing count query.", print_also=gl_d)
        results = session.execute(text(count_query), query_params).first()
        if results is None:
            tskm.emit_status(f"Apparently all desired codes already have code summary vectors, so not doing anything.", print_also=gl_d)
            return
        total_count = results.the_count
        tskm.emit_status(f"Count query done, count is: {total_count}", print_also=gl_d)

    # Do query, then loop through items and add them where appropriate
    # IMPORTANT CAVEAT!!!
    # After I do the next query, it may look like I have what I need. However, since I am streaming results,
    # I will NOT have access to the desired results variable content once I'm outside this next "with" block.
    # So... ANYTHING that expects to use this results variable MUST be within this block. ALSO,
    # there can be NO writes in the same session from which I am reading. To do writes, open another session!!!
    with enhanced_db_obj.session_class() as session:
        # Do query
        tskm.emit_status(f"Doing main query.", print_also=gl_d)
        stmt = text(query).execution_options(stream_results=True)
        results = session.execute(stmt, query_params)
        if not results:
            tskm.emit_status(f"NOT SUCCESS populating summary vectors!", print_also=gl_d)
            return
        tskm.emit_status(f"Did main query", print_also=gl_d)

        # Set up object to track progress through the results
        lpro = lprc('populate_code_summary_vectors', total_count, 100, True, status_report_functions=g_status_report_functions)

        # Iterate over rows one at a time
        for idx, row in enumerate(results):
            # Report progress -- will only print if at report increment
            lpro.report_progress(idx)

            if tskm.is_cancelled():
                tskm.emit_status("Cancelled population of code summary vectors.")
                return

            code_summary_vectors_obj = code_summary_vectors_class(
                enhanced_db_obj=enhanced_db_obj,
                code_id=row.code_id
                )
            # Don't populate if we've already done this one.
            if code_summary_vectors_obj.mean is not None:
                lpro.skip_count += 1
                continue
            cls_vecs_str_list = row.concatted_vecs.split(oc.sep)
            cls_vecs_list = []
            for cls_str_vec in cls_vecs_str_list:
                cls_vecs_list.append(vec_str_to_torch(cls_str_vec))
            # Now get a single vector summarizing the CLS vectors
            # Now get average of the CLS tokens
            # Stack the list into a single tensor with shape of: (number of sentences, embedding dimension)
            stacked_cls_tokens = torch.stack(cls_vecs_list)
            # Calculate the mean along axis 0 (across the sentences)

            mean_cls_token = torch.mean(stacked_cls_tokens, dim=0)
            code_summary_vectors_obj.orig_shape = mean_cls_token.shape
            mean_cls_token = mean_cls_token.flatten()
            max_cls_vals, max_cls_indices = torch.max(stacked_cls_tokens, dim=0)
            max_cls_token = max_cls_vals.flatten()
            code_summary_vectors_obj.mean = mean_cls_token
            code_summary_vectors_obj.max = max_cls_token
            code_summary_vectors_obj.mean_max = tensor_abs_max(mean_cls_token)
            code_summary_vectors_obj.max_max = tensor_abs_max(max_cls_token)
            code_summary_vectors_obj.dim = mean_cls_token.dim()
            # OK, I've populated this object, but that was outside a session. So now, I need to create a session,
            # merge the object into the session, and then commit so it's in the database.
            with enhanced_db_obj.session_class() as obj_merger_session:
                obj_merger_session.merge(code_summary_vectors_obj)
                obj_merger_session.commit()

    return


def populate_code_set(csp:code_sets_populator_class):
    # Get the database object from the params
    enhanced_db_obj = get_db_from_db_params(csp.db_params)

    success, results = enhanced_db_obj.do_query(csp.query, ())
    if not success:
        msg = f"ERROR: Not success populating code_set, problem with query: {csp.query}"
        debug.log(__file__, msg)
        raise Exception

    # results MUST return a set of code_ids.
    lpro = lprc('populate_code_set', len(results), 100, True, status_report_functions=g_status_report_functions)
    for idx, row in enumerate(results):
        lpro.report_progress(idx)

        if tskm.is_cancelled():
            tskm.emit_status("Cancelled population.")
            return

        # Make the code set.
        cso = code_sets_class(enhanced_db_obj, csp.set_name, row.code_id)

    # All done!
    return


def populate_custom_table(enhanced_db_obj:enhanced_db_class, ctg_obj:custom_table_generators_class):

    d = gl_d

    # Create the table if needed.
    # We only want to make a create table if not exists query
    # if that's not already part of the submitted query.
    # Before separator must be the create table if not exists query.
    # After the separator must be the query that we will use to insert.
    dv_query_separator = odc.dv_query_separator
    orig_queries = ctg_obj.ctg_query.split(dv_query_separator)
    # Now get rid of anything that is just white space
    queries = []
    for orig_query in orig_queries:
        new_query = orig_query.strip()
        if new_query:
            queries.append(new_query)

    # If we have nothing in queries, got a problem.
    if not queries:
        msg = f"FAILED: could not find any queries submitted."
        debug.log(__file__, msg)
        tskm.emit_status(msg, print_also=gl_d)
        return

    # Setup queries are all except the last. If only one, this will be empty (as desired)
    setup_queries = queries[:-1]
    # Last one is the select query.
    # If only one (because there is no separator) this will be that one, as desired.
    select_query = queries[-1]

    # If we did not get either both or neither of ctg_dest_code_field and , then error.
    if (ctg_obj.ctg_dest_code_field or ctg_obj.ctg_code_placeholder) and not (ctg_obj.ctg_dest_code_field and ctg_obj.ctg_code_placeholder):
        msg = f"ERROR: FAILED populate_custom_table get codes to process because must either get both or neither of  code placeholder and destination code field -- cannot get only one of those two."
        debug.log(__file__, msg)
        tskm.emit_status(msg, print_also=gl_d)
        raise Exception(msg)

    # If we got a ctg_obj.ctg_code_placeholder but do not find it in the query, then error.
    if ctg_obj.ctg_code_placeholder and not ':' + ctg_obj.ctg_code_placeholder in select_query:
        msg = f"ERROR: FAILED populate_custom_table get codes to process because got neither code placeholder nor destination code field -- must get either both or at least code placeholder (if doing batch query)."
        debug.log(__file__, msg)
        tskm.emit_status(msg, print_also=gl_d)
        raise Exception(msg)

    # Long and weird subquery names so it's almost certainly unique (not likely found elsewhere in the query)
    probably_unique_subquery_name = """sq_9832942348901273406665663894_dv"""
    probably_unique_subquery_explanation = """-- long and weird subquery name so it's almost certainly unique (not likely found elsewhere in the query by coincidence)"""
    probably_unique_subquery_snippet = f"{probably_unique_subquery_name} {probably_unique_subquery_explanation}"

    probably_unique_exist_subquery_name = 'dv_665368727728894991'

    # Make a create table query to ensure table exists before we try to populate it.
    create_table_query = f"""
CREATE TABLE IF NOT EXISTS {ctg_obj.ctg_dest_table} AS
SELECT * FROM
(
{ctg_obj.ctg_query}
) {probably_unique_subquery_snippet}
WHERE 1 = 0
        """
    # Make he create table query the first one in setup queries
    setup_queries.insert(0, create_table_query)

    # Run setup queries sequentially
    if ctg_obj.ctg_code_placeholder:
        query_params = {ctg_obj.ctg_code_placeholder: None}
    else:
        query_params = {}
    for setup_query in setup_queries:
        success = enhanced_db_obj.do_no_result_query(setup_query, query_params)
        if not success:
            msg = f"ERROR: FAILED populate_custom_table get codes to process! {success}"
            debug.log(__file__, msg)
            tskm.emit_status(msg, print_also=gl_d)
            raise Exception(msg)

    # If we got neither a ctg_dest_code_field nor a ctg_obj.ctg_code_placeholder,
    # then we are doing a batch.
    if not ctg_obj.ctg_dest_code_field and not ctg_obj.ctg_code_placeholder:
        insert_query = f"""
INSERT INTO {ctg_obj.ctg_dest_table}
    SELECT * FROM
    (
    {select_query}
    ) {probably_unique_subquery_snippet}

                """
        # Set up query params
        query_params = {}
        debug.debug(f"Begin batch populating custom table: {ctg_obj.ctg_dest_table}.", d=d)
        check_success, change_count = enhanced_db_obj.do_no_result_query_with_change_count(insert_query, query_params)
        '''
        print(insert_query)
        print(check_success)
        print(query_params)
        exit()
        '''
        if not check_success:
            msg = f"FAILED populate_custom_table: {ctg_obj.ctg_dest_table}! {check_success}"
            debug.log(__file__, msg)
            tskm.emit_status(msg, print_also=d)
            return
        if change_count < 1:
            debug.debug(f"No rows inserted by query to populate custom table {ctg_obj.ctg_dest_table}", d=d)

        # All done!
        return


    # If we get here, then we are processing code-by-code (one code at a time, not batch).
    # Now get codes to process.
    results = get_codes_via_selector(enhanced_db_obj, ctg_obj.ctg_code_selector, ctg_obj.ctg_code_selector_type)

    lpro = lprc(name=f'populate_custom_table {ctg_obj.ctg_dest_table}', list_length=len(results), report_increment=1, show_progress=True, status_report_functions=g_status_report_functions)
    tskm.emit_status(f"About to process {lpro.name}, got {lpro.list_length} to process.", print_also=d)

    check_query = f"""
SELECT {ctg_obj.ctg_dest_code_field} FROM {ctg_obj.ctg_dest_table}
WHERE {ctg_obj.ctg_dest_code_field} = :{ctg_obj.ctg_code_placeholder}
LIMIT 1
        """

    insert_query = f"""
INSERT INTO {ctg_obj.ctg_dest_table}
    SELECT * FROM
    (
    {select_query}
    ) {probably_unique_subquery_snippet}
    WHERE NOT EXISTS 
        (
        SELECT 1
        FROM {ctg_obj.ctg_dest_table} {probably_unique_exist_subquery_name}
        WHERE {probably_unique_exist_subquery_name}.{ctg_obj.ctg_dest_code_field} = :{ctg_obj.ctg_code_placeholder} -- {probably_unique_subquery_name}.{ctg_obj.ctg_dest_code_field}
        )
        """

    # Loop through each concept
    for idx, result in enumerate(results):

        in_proc_str = result.strs_model.str
        in_proc_code = result.code
        debug.debug(f"\n-------\nBegin processing code {in_proc_code} ({in_proc_str})\n-------\n", d=d)

        if tskm.is_cancelled():
            debug.debug(f"\n-------\nProcessing was cancelled.)\n-------\n", d=d)
            tskm.emit_status("Cancelled population.")
            return

        # Report progress
        lpro.report_progress(idx)

        # Set up query params
        query_params = {ctg_obj.ctg_code_placeholder: in_proc_code}
        debug.debug(f"Processing this one. {in_proc_code} ({in_proc_str})", d=d)
        check_success, change_count = enhanced_db_obj.do_no_result_query_with_change_count(insert_query, query_params)
        '''
        print(insert_query)
        print(check_success)
        print(query_params)
        exit()
        '''
        if not check_success:
            msg = f"FAILED populate_custom_table on {in_proc_code} ({in_proc_str})! {check_success}"
            debug.log(__file__, msg)
            tskm.emit_status(msg, print_also=d)
            return
        if change_count < 1:
            lpro.skip_count += 1
            debug.debug(f"Already did {in_proc_code} for {in_proc_str}", d=d)

    # All done!
    return


def get_codes_via_selector(enhanced_db_obj:enhanced_db_class, code_selector:str, code_selector_type:str):

    with enhanced_db_obj.session_class() as session:
        # Get the desired codes
        if code_selector_type == 'terminology':
            results:List[codes_class] = (
                session.query(codes_class)
                .options(selectinload(codes_class.strs_model)) # added this because not lazy loading.
                .filter(codes_class.terminology == code_selector)
                .order_by(codes_class.id.asc())  # or .desc()
                .all()
            )
        elif code_selector_type == 'code_set':
            results: List[codes_class] = (
                session.query(codes_class)
                .options(selectinload(codes_class.strs_model)) # added this because not lazy loading.
                .join(code_sets_class)
                .filter(code_sets_class.set_name == code_selector)
                .order_by(codes_class.id.asc())  # or .desc()
                .all()
            )
        elif code_selector_type == 'query':
            # This maps the results of the code_selector SQL query to the codes class.
            # Note that this expects the query to return rows from the codes table.
            # results:List[codes_class] = session.query(codes_class).from_statement(text(code_selector)).all()
            results: List[codes_class] = (
                session.query(codes_class)
                .options(selectinload(codes_class.strs_model))  # added this because not lazy loading.
                .from_statement(text(code_selector))
                .all()
            )
        else:
            msg = 'ERROR: Cannot get codes via selector because not given legit code selector type.'
            debug.log(__file__, msg)
            raise Exception(msg)
        return results

'''
# THIS IS NOT YET RIGHT. NEED TO FIX JOIN WHERE ???, and also I'm not sure this should be getting
# list of codes_class objects.
def get_strs_via_populator(enhanced_db_obj, selector, selector_type:str):
    with enhanced_db_obj.session_class() as session:
        # Get the desired codes
        if selector_type == 'terminology':
            results:List[codes_class] = session.query(codes_class).filter(codes_class.terminology == selector).all()
        elif selector_type == 'code_sets':
            results:List[codes_class] = session.query(codes_class).join(code_sets_class).filter(code_sets_class.set_name == selector).all()
        elif selector_type == 'rels':
            results:List[codes_class] = session.query(rels_class).join(code_sets_class, rels_class.??? = code_sets_class.???).filter(code_sets_class.set_name == selector).all()
        else:
            raise Exception
    return results
'''

def make_rel_item(enhanced_db_obj:enhanced_db_class, subj_code_id:str, rel:str, final_obj_str:str, rpo:rels_populator_class, priority:float):

        if not rel or not final_obj_str:
            msg = f"ERROR: Did not get either a rel (got: {rel}) or a final_obj_str (got: {final_obj_str}"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)

        # Add string if it doesn't exist
        str_obj = strs_class(
            enhanced_db_obj=enhanced_db_obj
            , the_str=final_obj_str
            )
        if not str_obj or not str_obj.id:
            msg = f"ERROR: Did not get either a str_obj (got: {str_obj}) or a str_obj.id (got: {str_obj.id}"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)
        # Make string vector if we don't already have one
        vec_obj = str_vectors_class(enhanced_db_obj=enhanced_db_obj, str_id=str_obj.id)
        if not vec_obj or not vec_obj.id:
            msg = f"ERROR: Did not get either a vec_obj (got: {vec_obj}) or a vec_obj.id (got: {vec_obj.id})"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)
        # Now make/store the relationship
        rel_obj = rels_class(
            enhanced_db_obj=enhanced_db_obj
            , subj_code_id=subj_code_id
            , rels_populator_id=rpo.id
            , rel=rel
            , rels_populator_name=rpo.name
            , obj_str_id=str_obj.id
            , priority=priority
            )
        if not rel_obj or not rel_obj.rel or not rel_obj.id:
            msg = f"ERROR: Did not get either a rel_obj (got: {rel_obj}) or a rel_obj.rel (got: {rel_obj.rel} or a rel_obj.id (got: {rel_obj.id})"
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)


def are_you_sureify(llm_obj:llmc, rels_prompt_obj:rspc, rel_prompt_obj:rpc, subj_str_to_check, obj_str_to_check:str):

    # Turn on/off debugging
    d = gl_d

    # If we are not doing a check, just return the item that was sent.
    if not rel_prompt_obj.are_you_sure_count:
        debug.debug("Not doing are_you_sureify because are you sure count was None or 0", d=d)
        return obj_str_to_check

    resps = []
    # Need to make sure the needed replacer keys are in the rel prompt object
    if rels_prompt_obj.placeholders.subj_str is None or rels_prompt_obj.placeholders.obj_str is None:
        msg = f'ERROR: {rels_prompt_obj.placeholders.subj_str} and {rels_prompt_obj.placeholders.obj_str} must not be None in the rel_prompt_obj but one or both were None.'
        debug.log(__file__, msg)
        raise Exception(msg)

    # Make the llm_replacer_content dictionary the content for the elements to be replaced.
    llm_replacer_content = {'subj_str': subj_str_to_check, 'obj_str': obj_str_to_check}

    # Determine value to use if error
    if rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.categorical.value:
        if_error_val = obj_str_to_check
    else:
        if_error_val = rel_prompt_obj.are_you_sure_val_if_error

    # Need to create new rel_prompt_obj and rels_prompt_obj to check are you sure (ays)
    ays_rel_prompt_obj = rpc(
        rel='ays'
        , rel_prompt=rel_prompt_obj.are_you_sure_prompt
        , is_multi_resp=False
        )
    ays_rels_prompt_obj = rspc(
        name='ays_rels_prompt_obj'
        , rels=[ays_rel_prompt_obj]
        # Inherit next items from original rels_prompt_obj
        , placeholders=rels_prompt_obj.placeholders
        , can_llm_output_json=rels_prompt_obj.can_llm_output_json
        , llm_str_output_response_surrounder=rels_prompt_obj.llm_str_output_response_surrounder
        , llm_str_output_separator_name=rels_prompt_obj.llm_str_output_separator_name
        )

    for rep in range(rel_prompt_obj.are_you_sure_count):
        try:
            llm_obj.get_and_process_response(rels_prompt_obj=ays_rels_prompt_obj, llm_replacer_content=llm_replacer_content)
            debug.debug(llm_obj.last_post_processed_prompt, d=d)
            debug.debug(llm_obj.last_resp, d=d)
        except Exception as e:
            msg = f"ERROR: Got exception processing are_you sure response with llm: {e}"
            debug.log(__file__, msg)
            # print(msg)
            if die_on_llm_failure:
                raise Exception(f"{msg}, exiting because set to die on llm failure")
        last_resp = copy.deepcopy(llm_obj.last_resp)
        # Should only get one item, so get it (this is a dictionary, want first key, which is the response)
        are_you_sure_resp = next(iter(last_resp['ays']))
        # Debugging
        debug.debug(f"'Are you sure' #{rep} for {subj_str_to_check} {rel_prompt_obj.rel} {obj_str_to_check} is {are_you_sure_resp}", d=d)
        # If we did not get a response, then replace it with the error value.
        if are_you_sure_resp is None:
            debug.debug(f"Replacing with default value {if_error_val}", d=d)
            are_you_sure_resp = if_error_val

        # If supposed to match a categorical value, then make sure we were returned a number.
        if not rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.categorical.value and not isinstance(are_you_sure_resp, numbers.Number):
            try:
                if rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.vote.value:
                    are_you_sure_resp = int(are_you_sure_resp)
                else:
                    are_you_sure_resp = float(are_you_sure_resp)
            except Exception:
                debug.log(__file__, f"Got exception processing returned result from LLM of {are_you_sure_resp} with adjudicator, using default value of {if_error_val}")
                are_you_sure_resp = if_error_val

        # If voting, make sure we are dealing with either a 1 or 0
        if rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.vote.value:
            if not are_you_sure_resp == 0 and not are_you_sure_resp == 1:
                are_you_sure_resp = if_error_val

        # Now we can append the result to the list of "are you sure" responses
        resps.append(are_you_sure_resp)
        debug.debug(f"Completed #{rep} 'are you sure' processing for {subj_str_to_check} {rel_prompt_obj.rel} {obj_str_to_check} with result of {are_you_sure_resp}", d=d)

        # Handle adjudication if voting, because don't need to do the full are_you_sure_count if the vote
        # is already yes or no. If they gave us even number for are_you_sure_count, then we count the
        # initial response as a yes (True or 1) vote. Responses of 1 = True/yes, 0 = False/No
        if rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.vote.value:
            debug.debug("Voting", d=d)
            if sum(resps) >= rel_prompt_obj.are_you_sure_count/2.0:
                debug.debug(f"Returning final response: {obj_str_to_check}", d=d)
                return obj_str_to_check
            # If we are checking for a no vote, if even number for are_you_sure_count, then
            # we want to use > rather than >+ because the initial response counts as a yes vote.
            elif resps.count(0) > rel_prompt_obj.are_you_sure_count/2.0:
                debug.debug(f"Returning final response of None value", d=d)
                return None
    # If we get here, then we are dealing with a sum or an average or categorical, so handle those.
    if rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.avg.value:
        result = sum(resps)/len(resps)
        debug.debug(f"Adjudicator avg result is {result}", d=d)
        return result
    elif rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.sum.value:
        result = sum(resps)
        debug.debug(f"Adjudicator sum result is {result}", d=d)
        return result
    # TODO: Since we require a numercial resonse, I think, make sure that our AYS functionality
    # can handle resp dictionary.
    elif rel_prompt_obj.are_you_sure_adjudicator == adjudicator_type_class.categorical.value:
        resp_count = {obj_str_to_check: 1}
        highest = obj_str_to_check
        highest_count = 1
        for resp in resps:
            debug.debug(f"Vote for {obj_str_to_check}: {resp}", d=d)
            if not resp in resp_count:
                resp_count[resp] = 1
            else:
                resp_count[resp] += 1
            # Tie will go to the LATER response
            if resp_count[resp] >= highest_count:
                highest = resp
        debug.debug(f"Adjudicator result is {highest}", d=1)
        return highest
    else:
        # Shouldn't get here. If we do, return an error.
        msg = f"ERROR: Got an invalid adjudicator of {rel_prompt_obj.are_you_sure_adjudicator}"
        debug.log(__file__, msg)
        raise Exception(msg)


# Ask the LLM to provide beceptivity for a term
def get_beceptivity_from_llm(
        enhanced_db_obj:enhanced_db_class
        , llm_obj:llmc
        , str_to_check:str
        , orig_rels_prompt_obj:rspc
        )->float:

    # Debugging on or off?
    d = gl_d

    # str_to_check = 'joint pain'

    # Make life easier
    orpo = orig_rels_prompt_obj

    # Make the requisite rel prompt and rels prompt objects
    rp_01 = rpc(
        rel=f'no_write_logic'
        , rel_prompt=f'''What would a typical person consider the specificity of the term at the end of the prompt? For your response, the key should be your reasoinging, including the logic of your thinking, and the value should be null.'''
        , is_multi_resp=False
        , is_no_write=True
        , min_acceptable_beceptivity=0
        , are_you_sure_count=0
        , resp_dict=None
        )
    rp_02 = rpc(
        rel=f'beceptivity_result'
        , rel_prompt=f'''Based on your previous response, provide the specificity (a number between 1 and {orpo.beceptivity_max_val} as the key, and null for the value. Provide no other verbiage.'''
        , is_multi_resp=False
        , is_no_write=False
        , min_acceptable_beceptivity=0
        , are_you_sure_count=0
        , resp_dict=None
        )

    rspo = rspc(
        name=orpo.beceptivity_name,
        rels_case_change=orpo.rels_case_change,
        can_llm_output_json=orpo.can_llm_output_json,
        llm_str_output_separator_name=orpo.llm_str_output_separator_name,
        llm_str_output_response_surrounder=orpo.llm_str_output_response_surrounder,
        instructions=orpo.instructions,
        beceptivity_src_type=beceptivity_src_type_class.is_pure_beceptivity.value,
        beceptivity_instructions=orpo.beceptivity_instructions,
        beceptivity_max_val=orpo.beceptivity_max_val,
        beceptivity_cutoff=orpo.beceptivity_cutoff,
        beceptivity_val_if_none=orpo.beceptivity_val_if_none,
        beceptivity_name=orpo.beceptivity_name,
        placeholders=orpo.placeholders
        )

    rspo.add(rp_01)
    rspo.add(rp_02)

    # This creates the beceptivities class if needd
    bc = beceptivities_class(
        enhanced_db_obj=enhanced_db_obj
        , name=orpo.beceptivity_name
        , prompt=rspo.prompt
        , min_val=1
        , max_val=rspo.beceptivity_max_val
        )

    with enhanced_db_obj.session_class() as session:
        query_results = (
            session.query(str_beceptivities_class.val)
            .join(beceptivities_class)
            .filter(and_(
                str_beceptivities_class.str == str_to_check
                , str_beceptivities_class.beceptivity_id == bc.id
                ))
            .all()  # Get all matching results
            )

    # Should only have one result
    if len(query_results) > 1:
        msg = "ERROR: Got more than one hit for beceptivity of string in beceptivities table."
        debug.log(__file__, msg, show_log_msg=True)
        raise Exception(msg)

    # If we got a result and the length is non-zero, then there must be only one result
    if query_results:
        beceptivity_value = query_results[0].val
        debug.debug(f"Beceptivity valye: {beceptivity_value}", d=d)
        return beceptivity_value

    # If we get here, we need to get the beceptivity value
    try:
        llm_obj.get_and_process_response(rspo, {'concept': str_to_check})
        last_resp_items = copy.deepcopy(llm_obj.last_resp['beceptivity_result'])
        d=gl_d
        debug.debug(last_resp_items, d=d)
        d=gl_d
        resp_item_count = len(last_resp_items)
        # If None or less than 1 resp item, return rspo.beceptivity_val_if_none
        if resp_item_count is None or resp_item_count < 1:
            return rspo.beceptivity_val_if_none
        # Should not have gotten more than 1 resp item
        elif resp_item_count > 1:
            msg = f'ERROR: Got more than one response for beceptivity, which should not have happened.'
            debug.log(__file__, msg, show_log_msg=True)
            raise Exception(msg)
        # Get here if got exactlu 1
        else:
            resp_item = list(last_resp_items.keys())[0]
            d = gl_d
            debug.debug(f"For string {str_to_check} got beceptivity value of: {resp_item}", d=d)
            d = gl_d

            sbo = str_beceptivities_class(
                enhanced_db_obj=enhanced_db_obj
                , beceptivity_id=bc.id
                , str=str_to_check
                , val=float(resp_item)
                )

            return float(resp_item)
    except Exception as e:
        msg = f'ERROR: Problem processing llm for beceptivity. Error was: {e}'
        debug.log(__file__, msg, show_log_msg=True)
        if die_on_llm_failure:
            raise Exception(f"{msg}, exiting because set to die on llm failure")


# This gets more beceptive (specific) terms for the passed term
def get_more_beceptive_content(
        llm_obj:llmc
        , rels_prompt_obj:rspc
        , rel_prompt_obj_idx:int
        , obj_str_to_replace:str
        , concept:str
        ):

    # Turn on/off debugging
    d = gl_d

    rel_prompt_obj = copy.deepcopy(rels_prompt_obj.rels[rel_prompt_obj_idx])

    # If we are not doing a check, just return the item that was sent.
    if not rel_prompt_obj.min_acceptable_beceptivity:
        return obj_str_to_replace

    resps = []

    # Make life easier
    orpo = rels_prompt_obj

    # Make the llm_replacer_content dictionary the content for the elements to be replaced.
    llm_replacer_content = {'concept': concept, 'obj_str': obj_str_to_replace, 'orig_prompt': rel_prompt_obj.rel_prompt}

    bec_rels_prompt_obj = rspc(
        name = 'bec_rels_prompt_obj',
        rels=[],
        rels_case_change = orpo.rels_case_change,
        can_llm_output_json = orpo.can_llm_output_json,
        llm_str_output_separator_name = orpo.llm_str_output_separator_name,
        llm_str_output_response_surrounder = orpo.llm_str_output_response_surrounder,
        instructions = orpo.instructions,
        beceptivity_src_type = orpo.beceptivity_src_type,
        beceptivity_instructions = orpo.beceptivity_instructions,
        beceptivity_max_val = orpo.beceptivity_max_val,
        beceptivity_cutoff = orpo.beceptivity_cutoff,
        beceptivity_val_if_none = orpo.beceptivity_val_if_none,
        beceptivity_name = orpo.beceptivity_name,
        placeholders = orpo.placeholders
        )

    # If we got a prompt to use to get more beceptive content, then use it.
    if rel_prompt_obj.get_more_beceptive_content_prompt:
        # But, to get more beceptive content, they must have AT LEAST given us the object string requiring
        # more beceptive content.
        if orpo.placeholders.obj_str in rel_prompt_obj.get_more_beceptive_content_prompt:
            get_more_beceptive_content_prompt_to_use = rel_prompt_obj.get_more_beceptive_content_prompt
        # If we did not get the object string placeholder, then raise an error.
        else:
            msg = f'''ERROR: Did not find an object string placeholder in the prompt. 
Prompt for more beceptive ccontent than the originally returned object string must have that placeholder in it. 
The placeholder is: 
{orpo.placeholders.obj_str}'''
            debug.log(__file__, msg)
            raise Exception(msg)
    # If they did not give us a retry prompt, then make one.
    else:
        get_more_beceptive_content_prompt_to_use = textwrap.dedent(f'''For this prompt:
                                {rel_prompt_obj.rel_prompt}
                an answer was 
                {obj_str_to_replace}
                which you previously said was overly general. If it is not overly general, then return it as the key to your response. If it is overly general, please provide as your {'keys ALL more specific instances' if rel_prompt_obj.is_multi_resp else 'key the single best more specific instance'} of {obj_str_to_replace} that ALSO answer the prompt.
                ''')

    bec_rel_prompt_obj = rpc(
        rel=f"response"
        # rel = f"[{rel_prompt_obj.rel} and is a more specific type of {obj_str_to_replace}]"
        # , rel_prompt = rel_prompt_obj._beceptivity_retry_prompt
        , rel_prompt = get_more_beceptive_content_prompt_to_use
        , is_multi_resp = rel_prompt_obj.is_multi_resp
        , is_no_write = False
        , min_acceptable_beceptivity = rel_prompt_obj.min_acceptable_beceptivity
        , are_you_sure_count = 0
        , resp_dict = None
        )
    bec_rels_prompt_obj.add(bec_rel_prompt_obj)

    d = gl_d
    debug.debug(f"BECEPTIVITY RETRY PROMPT {bec_rels_prompt_obj.prompt}", d=False)
    d = gl_d

    try:
        llm_obj.get_and_process_response(rels_prompt_obj=bec_rels_prompt_obj, llm_replacer_content=llm_replacer_content)
        d = gl_d
        debug.debug(f"Last post-processed prompt:\n{llm_obj.last_post_processed_prompt}", d=d)
        d = gl_d
        debug.debug(f"""
*******
GET MORE BECEPTIVE CONTENT
Concept: {concept}
Obj str to replace: {obj_str_to_replace}
LLM OBJ LAST RESP: {llm_obj.last_resp}
*******
            """, d=d)
        d = gl_d
    except Exception as e:
        msg = f"ERROR: Got exception processing beceptivity retry response with llm: {e}"
        debug.log(__file__, msg)
        # print(msg)
        if die_on_llm_failure:
            tskm.emit_status("ERROR: Exiting because set to die on LLM failure.")
            raise Exception(f"{msg}, exiting because set to die on llm failure")

    last_resp = copy.deepcopy(llm_obj.last_resp)
    response_obj_dict = dict(last_resp[bec_rel_prompt_obj.rel])
    # To make sure we don't lose anything, put back in the inadequately beceptive term if it isn't there.
    # if {bec_rels_prompt_obj.placeholders.obj_str} not in response_obj_dict.keys():
        # response_obj_dict[obj_str_to_replace] = ??? # not sure what to put here.
    d= gl_d
    debug.debug(f"More beceptive response_obj_dict = {response_obj_dict}", d=d)
    d = gl_d
    # exit()
    return response_obj_dict


def populate_rels(
        rpo:rels_populator_class
        , llm_password:str
        , mode:str='full_run'
        , test_term:str=''
        ):

    # Get the database object from the params
    enhanced_db_obj = get_db_from_db_params(rpo.db_params)

    # Get the desired codes
    results: Union[List[str], codes_class] # to help linting
    if mode != 'full_run':
        # If not full run, then we are just doing a test term, so get the code for that.
        if not test_term:
            msg = "ERROR: If not doing a full run, then must provide a test term to process."
            debug.log(msg)
            raise Exception(msg)
        results = test_term.split("\n")
        # Remove empty or whitespace-only strings.
        results = [s for s in results if isinstance(s, str) and s.strip()]
        # results = [test_term]
    else:
        results = get_codes_via_selector(enhanced_db_obj, rpo.code_selector, rpo.code_selector_type)

    # Get LLM object
    llm_obj = llmm.get_llm_from_llm_params(rpo.llm_params, llm_password)
    # Get rels object
    # rels_prompt_obj:rspc = jsonpickle.loads(rpo.rels_prompt_obj_json)
    rels_prompt_obj:rspc = su.jsonpickle_loads(rpo.rels_prompt_obj_json)
    # rels_prompt_obj.model = pydantic.create_model('responses_property_model', **rels_prompt_obj.model)
    # Keep track of progress
    lpro = lprc(name='populate_rels', list_length=len(results), report_increment=1, show_progress=True, status_report_functions=g_status_report_functions)
    tskm.emit_status(f"About to process {lpro.name} using LLM, got {lpro.list_length} to process.", print_also=gl_d)

    # DEBUGGING ON/OFF
    local_d = gl_d

    # For performance, let's hang onto any beceptivity we've already assessed
    is_adequate_beceptivity_dict = {}

    # Variable to hold testing info
    ret = ''

    # Loop through each concept
    for idx, result in enumerate(results):

        if mode == 'full_run':
            in_proc_str = result.strs_model.str
            in_proc_code = result.code
        else:
            in_proc_str = result
            in_proc_code = 'this is testing mode so no code'
        debug.debug(f"\n-------\nBegin processing string:{in_proc_str}\n-------\n", d=local_d)

        if tskm.is_cancelled():
            msg = "Cancelled rels population."
            debug.log(__file__, msg)
            tskm.emit_status(msg)
            return

        # Report progress
        debug.debug("BEGIN reporting progress with progress reporter.", d=local_d)
        lpro.report_progress(idx)
        debug.debug("DONE reporting progress with progress reporter.", d=local_d)

        # First check and see if this code has already been processed by this rels_populator
        if mode == 'full_run':
            with enhanced_db_obj.session_class() as session:
                if session.query(rels_class).filter(rels_class.subj_code_id == result.id, rels_class.rels_populator_id == rpo.id).first() is not None:
                    lpro.skip_count += 1
                    debug.debug(f"Already did {result.code} for {in_proc_str}", d=local_d)
                    continue
                else:
                    debug.debug(f"Processing this one. {result.code}", d=local_d)
                    # exit()

        # Get LLM response
        debug.debug(f"About to try to get LLM response for {in_proc_str}.", d=local_d)
        try:
            # content_dict = {'concept': result.strs_model.str}
            content_dict = {'concept': in_proc_str}
            debug.debug(f"About to get and process LLM response for {in_proc_str}.", d=local_d)
            llm_obj.get_and_process_response(rels_prompt_obj=rels_prompt_obj, llm_replacer_content=content_dict)
            debug.debug(f"DONE get and process LLM response for {in_proc_str}.", d=local_d)
            last_prompt = llm_obj.last_post_processed_prompt
            debug.debug(f"Got last_prompt for {in_proc_str}.", d=local_d)
            # If testing, capture prompt and response
            ret += f"\n\n-----\nFor concept: {in_proc_str}\nPrompt sent to LLM:\n{last_prompt}\n"
            # last_resp_items = llm_obj.last_resp_items.copy()
            last_resp_items = copy.deepcopy(llm_obj.last_resp)
            ret += f"\nLLM Response:\n{llm_obj.last_resp}\n-----\n"
            debug.debug(f"Got resp_items for {in_proc_str}.", d=local_d)
        except Exception as initial_response_for_in_proc_str_for_llm:
            msg = f"""ERROR:
Got exception processing with llm initial response for term. 
Term: {in_proc_str} 
Error message: {initial_response_for_in_proc_str_for_llm}
                """
            debug.log(__file__, msg)
            # print(msg)
            if die_on_llm_failure:
                tskm.emit_status("Cancelled rels population.")
                raise Exception(f"{msg}, exiting because set to die on llm failure")

        # Initialize list of relationships to write
        json_rels_to_write = dict()

        try:
            debug.debug(f"Prompt was {rels_prompt_obj.prompt}\n\nResponse was:\n{last_resp_items}", d=local_d)
        except Exception as debug_exception:
            debug.log(__file__,f"ERROR: Cannot show debug message!!! Error was: {debug_exception}")

        # Loop through each relationship
        for idx2, rel_str in enumerate(last_resp_items):
            debug.debug(f"\n\nDealing with #{idx2} for {in_proc_str}, rel is {rel_str}", d=local_d)

            # Copy the original last response item
            last_resp_item = copy.deepcopy(last_resp_items[rel_str])
            ret += f"\n\nFor {in_proc_str} {rel_str}, initial LLM response item includes: {last_resp_item}\n"
            debug.debug(f"Last response item for {in_proc_str} {rel_str} is: {last_resp_item}", d=local_d)
            debug.debug(f"last_resp_item is of type {type(last_resp_item)} and length {len(last_resp_item)}", d=local_d)

            # Get the relevant rel_prompt object
            rel_prompt_obj = rels_prompt_obj.rels[idx2]

            # Was this a rel prompt object to ignore? If so, skip to the next one.
            if rel_prompt_obj.is_no_write:
                debug.debug(f"Last resp item is a no_write", d=local_d)
                continue

            # Loop through and get all object strings for this relationship
            # last_resp_item should ALWAYS be a dictionary with keys as the object string.
            # If we don't care about beceptivity, then it should be None, or at worst, 0.
            # If we do care about beceptivity, then it should be > 0.
            for idx3, orig_obj_str in enumerate(last_resp_item):
                debug.debug(f"\n\nDealing with {in_proc_str} {rel_str}:{orig_obj_str}", d=local_d)
                # If we did not specify we wanted multiple responses, then
                # error out? Or just take first item? We will just take first item.
                # For now, we will just take the first item
                if not rel_prompt_obj.is_multi_resp and idx3 > 0:
                    msg = "\n!!! GOT MORE THAN 1 REL HIT WHEN ONLY 1 EXPECTED! !!!\n"
                    debug.debug(msg, d=local_d)
                    debug.log(__file__, msg)
                    continue

                # Do we fix beceptivity first if needed, or do are you sure first?
                # Doesn't seem right to fix beceptivity if this thing isn't even right.
                obj_str = are_you_sureify(
                    llm_obj=llm_obj
                    , rels_prompt_obj=rels_prompt_obj
                    , rel_prompt_obj=rel_prompt_obj
                    # , subj_str_to_check=result.strs_model.str
                    , subj_str_to_check=in_proc_str
                    , obj_str_to_check=orig_obj_str)

                ret += f"""
After are_you_sureify, original obj_str of:
{orig_obj_str}
is now:
{obj_str}
                """

                # If we didn't get an obj_str because it wasn't legit then don't do any further
                # work with this one.
                if obj_str is None:
                    debug.debug(f"This obj_str ({orig_obj_str}) didn't validate as legitimate.", d=local_d)
                    continue

                def extract_beceptivity_from_str_src(the_str, the_str_src):
                    # We may have gotten a string or a dictionary for resp_item_obj.
                    # If a dictionary, then key is the object string and value is the beceptivity.
                    # Otherwise, the object is the object string and it's got no beceptivity.
                    # Either way, get current_obj_beceptivity.
                    if isinstance(the_str_src, dict):
                        current_obj_beceptivity = the_str_src[the_str]
                    else:
                        current_obj_beceptivity = None
                    return current_obj_beceptivity

                def is_obj_adequately_beceptive(the_str, the_str_src, ret, loop_num):

                    # If no minimum acceptable beceptivity set, then just return None
                    if not rel_prompt_obj.min_acceptable_beceptivity:
                        return True, ret

                    # If we did not get a valid beceptivity source type but we did get
                    # a minimum acceptable beceptivity (because we got here), raise an error.
                    if rels_prompt_obj.beceptivity_src_type not in [beceptivity_src_type_class.llm_response.value, beceptivity_src_type_class.llm_2nd_response.value, beceptivity_src_type_class.query.value
                            ]:
                        # Problem! Raise exception
                        msg = "ERROR: Did not get a valid beceptivity_src_type."
                        debug.log(__file__, msg)
                        raise Exception(msg)

                    # If we did not get > 0 beceptivity loops but we did get
                    # a minimum acceptable beceptivity (because we got here), raise an error.
                    if not rel_prompt_obj.max_beceptivity_loops:
                        # Problem! Raise exception
                        msg = "ERROR: If a minimum acceptable beceptivity is set over zero, then there must be more than zero loops set for getting more beceptive content."
                        debug.log(__file__, msg)
                        raise Exception(msg)

                    # We may have gotten a string or a dictionary for resp_item_obj.
                    # If a dictionary, then key is the object string and value is the beceptivity.
                    # Otherwise, the object is the object string and it's got no beceptivity.
                    # Either way, get current obj_str and current_obj_beceptivity.
                    current_obj_beceptivity = extract_beceptivity_from_str_src(the_str, the_str_src)
                    ret += f"\nWhile checking if {the_str} from {the_str_src} is adequately beceptive, got current_obj_beceptivity of {current_obj_beceptivity}\n"

                    # Handle if we already have checked this beceptivity before.
                    # This does mean that, if we are checking every time (LLM first response),
                    # we will really only pay attention to the very first one we ever got. Is this bad?
                    # Maybe, but we functionally do the same thing for LLM second response. Not sure of
                    # a better approach.
                    if the_str in is_adequate_beceptivity_dict and is_adequate_beceptivity_dict[the_str]:
                        ret += f"\nContent for {the_str} adequately beceptive because in is_adequate_beceptivity_dict as True.\n"
                        return True, ret
                    if the_str in is_adequate_beceptivity_dict and not is_adequate_beceptivity_dict[
                        the_str]:
                        ret += f"\nContent for {the_str} NOT adequately beceptive because in is_adequate_beceptivity_dict as False.\n"
                        return False, ret

                    # If this is the last loop and we are going to assume the response is adequate?
                    # If so, then don't bother to continue.
                    if loop_num == rel_prompt_obj.max_beceptivity_loops and rel_prompt_obj.is_assume_adequate_on_max_loop:
                        ret += f"\nContent for {the_str} adequately beceptive because we are on max loop and assume adequate on max loop.\n"
                        return True, ret

                    # Now we have to get the beceptivity and see if it's okay.
                    # Do we already have it?
                    if rels_prompt_obj.beceptivity_src_type == beceptivity_src_type_class.llm_response.value:
                        # In this case, we already have the beceptivity, and it is current_obj_beceptivity, so
                        # nothing to do here.
                        pass
                    # Do we need to query DB for it?
                    elif rels_prompt_obj.beceptivity_src_type == beceptivity_src_type_class.query.value:
                        return Exception("Query for beceptivity not yet implemented.")
                        # This seems problematic -- where to put obj string?
                        # Need to put in terms parameter for this call!
                        # Uncomment below when fixed and things work.
                        """
                        current_obj_beceptivity = query_for_beceptivity(
                            enhanced_db_obj=enhanced_db_obj
                            , rels_prompt_obj=rels_prompt_obj
                            , rel_prompt_obj=rel_prompt_obj
                            )
                        """
                    # Do we need to prompt LLM for it?
                    elif rels_prompt_obj.beceptivity_src_type == beceptivity_src_type_class.llm_2nd_response.value:
                        current_obj_beceptivity = get_beceptivity_from_llm(
                            enhanced_db_obj=enhanced_db_obj
                            , llm_obj=llm_obj
                            , str_to_check=the_str
                            # , val_if_none=rels_prompt_obj.beceptivity_val_if_none
                            , orig_rels_prompt_obj=rels_prompt_obj
                            )
                        debug.debug(f"Obj beceptivity from LLM 2nd reponse is: {current_obj_beceptivity}", d=local_d)

                    # We should now have a beceptivity. If not, raise an error.
                    if current_obj_beceptivity is None:
                        msg = f"\nERROR: Current obj beceptivity is: {current_obj_beceptivity} but we should have gotten a numberic object beceptivity.\n"
                        debug.log(__file__, msg)
                        raise Exception(msg)

                    # Now we have a beceptivity. Is it adequate? Decide and return result
                    is_adequate_tf = current_obj_beceptivity >= rel_prompt_obj.min_acceptable_beceptivity
                    is_adequate_beceptivity_dict[the_str] = is_adequate_tf
                    msg = f"Is adequate beceptivity is {is_adequate_tf} for {in_proc_str} {rel_str} {the_str} based on comparing current obj beceptivity of {current_obj_beceptivity} to min acceptable value of  {rel_prompt_obj.min_acceptable_beceptivity} "
                    debug.debug(msg, d=local_d)
                    ret += f"\n{msg}\n"
                    return is_adequate_tf, ret

                def in_loop_get_more_beceptive_content(base_obj_str, current_obj_str, ret):

                    # Get additionally beceptive content
                    returned_obj_dict = get_more_beceptive_content(
                        llm_obj=llm_obj
                        , rels_prompt_obj=rels_prompt_obj
                        , rel_prompt_obj_idx=idx2
                        , obj_str_to_replace=current_obj_str
                        , concept=in_proc_str
                        )

                    # Append original base string to the more beceptive content
                    new_obj_dict = {}
                    for new_str in returned_obj_dict:
                        new_obj_dict[f"{base_obj_str} - {new_str}"] = returned_obj_dict[new_str]

                    debug.debug(f"New obj strings and beceptivities after get_more_beceptive_content: {new_obj_dict}\n", d=local_d)

                    ret += f"\nGet_more_beceptive_content for {current_obj_str}, returned new_obj_dict of: {new_obj_dict}\n"

                    # Testing beceptivity only -- exit
                    # exit()
                    return new_obj_dict, ret

                # The obj_str in the last_resp_item may not be the obj_str we are using, because
                # the AYS functionality above may have selected a different one.
                # Now get the beceptivity for the object. If we already have it from the LLM,
                # then it will just be the same as the llm_dict_beceptivity. Otherwise, it will handle
                # getting the beceptivity as needed.
                current_obj_beceptivity = extract_beceptivity_from_str_src(orig_obj_str, last_resp_item)
                current_obj = {obj_str: current_obj_beceptivity}
                base_obj_str = obj_str

                # We will only get beceptivity related to this item
                # up to rel_prompt_obj.max_beceptivity_loops times.
                # Unless otherwise specified, range will go from 0 to the range value - 1.
                for loop_num in range(rel_prompt_obj.max_beceptivity_loops + 1):
                    # Keep track of the objects that will need rechecking still, if not past max_beceptivity_loops.
                    recheck_obj = {}
                    # Loop through each item in the current_obj
                    ret += f"Loop {loop_num} has current_obj = {current_obj}\n"
                    for working_obj_str in current_obj:

                        ret += f"\nDoing {loop_num} beceptivity loop of {rel_prompt_obj.max_beceptivity_loops} max loops with working_obj_str ."

                        # If more beceptive content is needed, then get it.
                        content_is_adequately_beceptive, ret = is_obj_adequately_beceptive(working_obj_str, current_obj, ret, loop_num)
                        if not content_is_adequately_beceptive:
                            ret += f"\nMore beceptive content is needed for {working_obj_str}."
                            # Only actually get more beceptive content if we are not at/past the max loops.
                            # This is because loop_num is 0-based, so at max_loops loop_num, we are actually
                            # past the max # of loops.
                            if loop_num < rel_prompt_obj.max_beceptivity_loops:
                                more_beceptive_obj, ret = in_loop_get_more_beceptive_content(base_obj_str, working_obj_str, ret)
                                #for k in more_beceptive_obj.keys():
                                    #recheck_obj[k] = more_beceptive_obj[k]
                                recheck_obj = recheck_obj | more_beceptive_obj

                        # If more beceptive content is not needed, add it to the dictionary
                        # of things to write to the database.
                        else:
                            ret += f"\nMore beceptive content is NOT needed for {working_obj_str}."
                            the_dict = {rel_prompt_obj.rel: working_obj_str}
                            json_rels_to_write[json.dumps(the_dict)] = None

                    current_obj = copy.deepcopy(recheck_obj)

        debug.debug(f"json_rels_to_write for {in_proc_str} = {list(json_rels_to_write.keys())}", d=local_d)

        # Continue before writing if testing only
        # exit()
        # continue

        # Write data if full_run, otherwise just print and log what would be written
        ret += """
        *******************************
        *******************************
                            """
        # Manage priorities
        priorities_dict = {}
        for idx4, rel_obj_str in enumerate(json_rels_to_write.keys()):
            # debug.debug(f"Storing {result.strs_model.str} relationship (sent as JSON) to {rel_obj_str}", d=local_d)
            if mode == 'full_run':
                debug.debug(f"Storing {in_proc_str} relationship (sent as JSON) to {rel_obj_str}", d=local_d)

                try:
                    obj_dict = json.loads(rel_obj_str)
                except Exception as e:
                    msg = f"ERROR: Problem decoding JSON response of {rel_obj_str} -- error was {e}"
                    debug.log(__file__, msg, show_log_msg=True)
                    raise Exception(msg)
                # This should have only a single key/value pair
                rel = list(obj_dict.keys())[0]
                final_obj_str = str(obj_dict[rel])
                if rel not in priorities_dict:
                    priorities_dict[rel] = 0
                priorities_dict[rel] += 1

                make_rel_item(
                    enhanced_db_obj=enhanced_db_obj
                    , subj_code_id=result.id
                    , rel=rel
                    , final_obj_str=final_obj_str
                    #, obj_str=rel_obj_str
                    , rpo=rpo
                    , priority=priorities_dict[rel]
                    )
            else: # testing mode
                msg = f"(TESTING MODE) {in_proc_str} LLM-identified relationship (sent as JSON): {rel_obj_str}"
                ret += f"\n{msg}\n"
                ret += """
**************************************************************
**************************************************************
                            """

                debug.debug(f"******  Loop finished concept: {in_proc_str} for result index {idx} among result count {len(results)}", d=local_d)

    if mode != 'full_run':
        debug.log(__file__, ret)

    tskm.emit_status(f"DONE processing {lpro.name} using LLM with {lpro.list_length} to process.", print_also=local_d)

    # All done -- return!
    return


# TODO: TEST this next subroutine
def query_for_beceptivity(
        enhanced_db_obj:enhanced_db_class
        , rels_prompt_obj:rspc
        , rel_prompt_obj:rpc
        , terms:list
        )->float:

    query = rels_prompt_obj.beceptivity_instructions # TODO: Fix this to use something appropriate!
    val_if_none = rels_prompt_obj.beceptivity_val_if_none
    terms = terms
    change_terms_case = rels_prompt_obj.rels_case_change

    # Make sure we even can query for beceptivity
    if not query or not terms:
        msg = f"""ERROR: Either did not get a beceptivity retry prompt or did not get terms to retry"""
        debug.debug(msg, d=gl_d)
        debug.log(__file__, msg)
        raise Exception(msg)

    # Get a lowered list of the items too
    # the_strs_list = terms.copy()
    # Get a lowered list of the items
    the_strs_list = []
    for term in terms:
        if change_terms_case == enums.case_change.lower.value:
            the_strs_list.append(term.lower())
        elif change_terms_case == enums.case_change.upper.value:
            the_strs_list.append(term.upper())
        else:
            the_strs_list.append(term)
    qparams = {'strs_list': tuple(the_strs_list)}

    # Run query and return result
    with enhanced_db_obj.session_class() as session:
        # Do query
        result = session.execute(text(query), qparams).first()
        if result.beceptivity is None:
            return val_if_none
        else:
            return result.beceptivity

def query_for_embedder_src_location(enhanced_db_obj:enhanced_db_class, embedder_meta_src:str):

    # I think this may error if no source location found for the embedder_src_str
    with enhanced_db_obj.session_class() as session:
        return session.query(embedder_metas_class).filter_by(src=embedder_meta_src).first().src_location


def check_if_attr_exists_and_is_true(obj, attr):
    # print(f"For attr {attr} is it present in obj? {hasattr(obj, attr)}")
    # if hasattr(obj, attr):
        # print(f"For attr {attr} value is: {getattr(obj, attr)}")
    return hasattr(obj, attr) and getattr(obj, attr)


# Class for attribute, query, parameter relationship
class attr_query_item:
    def __init__(self, name, query=None, params=None):
        self.name = name
        self.query = query
        self.params = {}

    def add_param(self, k, v):
        self.params[k] = v


class matches_populator_class:

    def __init__(self
        , config_obj
        # Next variable contains params that can only be populated from the row.
        , row_params:dict # key is query param in the final_query to get match_results, val is the relevant field name returned in the unmatched_row_results query
        , left_queries_list:list
        , right_queries_list:list
        , left_vec_name:str='obj_vec'
        , right_vec_name:str='code_vec'
        , top_hit_count:int=4
        , unmatched_getter_func=None
        ):

        self.config_obj = config_obj
        self.row_params = row_params
        self.left_queries_list = left_queries_list
        self.right_queries_list = right_queries_list
        self.left_vec_name = left_vec_name
        self.right_vec_name = right_vec_name
        self.top_hit_count = top_hit_count
        self.unmatched_getter_func = unmatched_getter_func
        self.left_queries = []
        self.right_queries = []

        # Make sure this object is legit populated.
        if not config_obj:
            msg = "ERROR: Did not get a code matches populator object"
            debug.log(__file__, msg)
            raise Exception(msg)

        # Do query, then loop through items and add them where appropriate
        self.enhanced_db_obj = get_db_from_db_params(config_obj.db_obj_params)

        # Get the embedder meta id
        self.embedder_meta_id = self.enhanced_db_obj.embedder_meta_obj.id


    def process_attr_query_items(self, starting_dict:dict, attr_query_dict: dict):
        # Initialize items
        self.left_queries = []
        self.right_queries = []
        final_dict = copy.deepcopy(starting_dict) # Initialize final dict with starting dict

        for k in attr_query_dict.keys():

            # Populate lists of left and right qeuries
            if k in self.left_queries_list:
                self.left_queries.append(attr_query_dict[k].query)
            if k in self.right_queries_list:
                self.right_queries.append(attr_query_dict[k].query)

            # Populate params dictionary
            for pk in attr_query_dict[k].params.keys():
                # Make sure we don't have a conflict of values
                new_val = attr_query_dict[k].params[pk]
                if pk in final_dict.keys() and final_dict[pk] != new_val:
                    msg = f'''ERROR: {pk} key has multiple different values for the same final query -- this is not allowed. 
                    The starting dictionary was:
                    {starting_dict}
                    The problematic dictionary (converted here to JSON) was: {json.dumps(attr_query_dict)}
                        '''
                    debug.log(__file__, msg)
                    raise Exception("ERROR: Duplicated key for final dictionary")
                final_dict[pk] = attr_query_dict[k].params[pk]
        return final_dict


    def get_rel_codes_to_match_query_item(self):
        rel_code_matches_populator_obj = self.config_obj
        ret = attr_query_item('rel_code_to_match')
        # Query for all relationship object strings to be matched, excluding those that have already been done.
        ret.query = f'''
SELECT DISTINCT ON 
    (rels.obj_str_id)
    rels.obj_str_id
FROM {odc.schema}.rels rels
INNER JOIN {odc.schema}.code_sets cs ON rels.subj_code_id = cs.code_id
WHERE 
    rels_populator_id = :rel_populator_id
    AND rel = :rel
    AND NOT EXISTS
        (
        SELECT 
            rcm.match_from_rel_obj_str_id
        FROM {odc.schema}.rel_code_matches rcm 
        INNER JOIN {odc.schema}.rel_code_matches_populator rcmp
            ON rcmp.id = rcm.rel_code_matches_populator_id AND rcmp.id = :rel_code_matches_populator_id
        WHERE 
            rcm.match_from_rel_obj_str_id = rels.obj_str_id
            -- In another run, someone could have done the same match from rel and match to code set 
            -- but with a different set of strings used. The rel_code_matches_populator_id filter
            -- addresses that by making sure it was THIS set of strings.
            -- Probably not necessary given the join, but just to be sure.
            AND rcm.rel_code_matches_populator_id = :rel_code_matches_populator_id
        )
                    '''
        ret.add_param('rel_populator_id', str(rel_code_matches_populator_obj.match_from_rel_populator_id))
        ret.add_param('rel', str(rel_code_matches_populator_obj.match_from_rel))
        ret.add_param('rel_code_matches_populator_id', str(rel_code_matches_populator_obj.id))
        # I think next one is not used in this query, but should not be harmful.
        ret.add_param('match_to_code_set_name', str(rel_code_matches_populator_obj.match_to_code_set_name))
        return ret


    def create_final_code_match_query(self):
        # Cannot embed this in query because contains \n
        left_queries_str = '\n\nUNION\n\n'.join(self.left_queries)
        right_queries_str = '\n\nUNION\n\n'.join(self.right_queries)
        # Get top top_hit_count hits
        final_query = f'''
            SELECT * FROM
                (
                SELECT 
                    code_id
                    , ROW_NUMBER() OVER (ORDER BY dist) AS ranking
                    , dist
                    FROM (
                    SELECT
                        -- Get best matching value for each code
                        MIN({self.left_vec_name} <=> {self.right_vec_name}) AS dist
                        , code_id
                    FROM
                        ----******* START LEFT QUERIES *************
                        (
                        {left_queries_str}
                        ) sq_left_vecs
                        ----******* END LEFT QUERIES *************
                    CROSS JOIN
                        ----******* START RIGHT QUERIES *************
                        (
                        {right_queries_str}
                        ) sq_right_vecs
                        ----******* END RIGHT QUERIES *************
                    WHERE {self.left_vec_name} <=> {self.right_vec_name} < 0.4
                    GROUP BY code_id
                    ) sq_rn
                ) sq_outermost
                WHERE ranking < {self.top_hit_count}
                -- ADDING THIS
                ORDER BY code_id
                '''
        return final_query


    def do_matches_populate(self):
        # Get the object to get all unpopulated matches
        config_obj_class_name = self.config_obj.__class__.__name__

        # Debugging
        debug.debug(f"Config object class name: {config_obj_class_name}", d=gl_d)
        debug.debug(f"Unmatched getter function: {self.unmatched_getter_func.__name__}", d=gl_d)

        # Get all unmatched items
        attr_query_obj = self.unmatched_getter_func(self)
        unmatched_query_success, unmatched_query_results = self.enhanced_db_obj.do_query(attr_query_obj.query, attr_query_obj.params)

        # Handle success situations
        if not unmatched_query_success:
            msg = f"NOT SUCCESS for doing unmatched query: {unmatched_query_success}"
            debug.log(__file__, msg)
            tskm.emit_status(msg, print_also=gl_d)
            return
        elif not unmatched_query_results:
            msg = f"NOT SUCCESS because got no query results, claimed query success was: {unmatched_query_success}"
            debug.log(__file__, msg)
            tskm.emit_status(msg,  print_also=gl_d)
            return

        # Set up object to track progress through the results.
        # Loop through this instead of one big query, because
        # then can cancel it if long-running, control it, etc...
        if not unmatched_query_results:
            # All done -- emit status and return!
            tskm.emit_status(f"Nothing found to process, so DONE processing code_matches.", print_also=gl_d)
            return

        msg = f"About to go through {len(unmatched_query_results)} as yet unmatched rel query results"
        debug.debug(msg, d=debug.default_d)

        # Get all possible subqueries as dictionary
        all_subqueries, expansion_strs_query_params = self.make_all_subqueries()

        # Get the list of all params we will need, de-duped
        # all_params = self.combine_all_attr_query_params(all_subqueries)
        all_params = self.process_attr_query_items(expansion_strs_query_params, all_subqueries)

        # Validate that match_from_field_name is a value in row_params
        '''
        if 'match_from_field_name' not in self.row_params.values():
            msg = f'Row params must contain match_from_field_name as a key/value pair, but it does not. Contents of row params (provided here as JSON) are: {json.dumps(self.row_params)}'
            debug.log(__file__, msg)
            raise Exception('Row param error -- check log.')
        '''

        # Make final query
        #final_query = self.create_final_code_match_query(self.left_queries_list, self.right_queries_list, self.left_vec_name, self.right_vec_name, self.top_hit_count)
        final_query = self.create_final_code_match_query()

        # Keep track of the results we are about to iterate through -- this is
        # trccking/reporting object.
        lpro = lprc('populate_code_matches', len(unmatched_query_results), 1, True, status_report_functions=g_status_report_functions)

        # Iterate through results.
        for unmatched_query_idx, unmatched_query_row in enumerate(unmatched_query_results):
            # print("Doing row:", unmatched_query_idx)
            # Report progress -- will only print if at report increment
            lpro.report_progress(unmatched_query_idx)

            # Make the final params for the query by adding in the needed row params
            final_params = copy.deepcopy(all_params)
            for row_param in self.row_params:
                final_params[row_param] = getattr(unmatched_query_row, row_param)

            match_success, match_results = self.enhanced_db_obj.do_query(final_query, final_params)

            d = False # gl_d
            debug.debug(f'''
=========================
      *************
=========================
{final_query}
========================
       *************
=========================
{final_params}
=========================
       *************
=========================
            ''', d=d)

            # print(final_query)
            # print(final_params)
            # exit()

            # Handle success situations
            if not match_success:
                msg = f"ERROR: NOT MATCH SUCCESS! {match_success}"
                debug.log(__file__, msg)
                tskm.emit_status(msg, print_also=gl_d)
                raise Exception(msg)

            elif not match_results:
                tskm.emit_status(f"NOTHING TO PROCESS! {match_results}", print_also=gl_d)
                lpro.skip_count += 1
                continue

            # Loop through rows
            for match_idx, match_row in enumerate(match_results):
                # I tried to come up with a generic matches class, but I was struggling to succeed.
                # Some issues -- with each row's populator ID joining to a different table, can't
                # just put a foreign key constraint on it. Aslo, the matching from and to stuff seemed
                # like it was getting challenging to keep adequately generic. I think I could find a way,
                # and I'm struggling to decide if I will regret this later, or if it's worth it. Still,
                # I'm moving on without a generic matches class for now. I understand this will be hard
                # to change later, but the foreign key thing worries me -- using an application-level
                # enforcement seems concerning.

                # If matching rel string to code in code_set
                if config_obj_class_name == 'rel_code_matches_populator_class': # rel_code_matches_populator_class.__class__.__name__:
                    rel_code_matches_class(
                        enhanced_db_obj=self.enhanced_db_obj
                        , rel_code_matches_populator_id=self.config_obj.id
                        , match_from_rel_obj_str_id=unmatched_query_row.obj_str_id
                        , matched_code_id=match_row.code_id
                        , ranking=match_row.ranking
                        , distance=match_row.dist
                        )
                else:
                    msg = f'ERROR: incompatible config object with class name of {self.config_obj.__class__name}'
                    debug.log(__file__, msg)
                    raise Exception(msg)

        # All done -- emit status and return!
        tskm.emit_status(f"DONE processing {lpro.name} with {lpro.list_length} to process.", print_also=gl_d)
        return


    def make_all_subqueries(self):

        # Initialize params
        params = {}

        # Load up the "match which strings" object.
        if hasattr(self.config_obj, "expanion_str_styles_json"):
            match_which_strs_obj = json.loads(self.config_obj.expanion_str_styles_json)
            # Get the expansion string summary vectors for the desired expansion string types.
            # Probably would have been better if I had made vectors for each expansion string and got the closest.
            # But I was worried about storage consumption, probably inappropriately. Comparing each expansion string's
            # vector almost surely would have been better for code matching, but how much better? Not sure. This will
            # also surely be faster.
            style_parts = []
            expansion_strs_query_params = {}
            for idx, style in enumerate(match_which_strs_obj):
                style_parts.append(f'sesp.style = :style_{idx}')
                expansion_strs_query_params[f'style_{idx}'] = style
            style_parts_str = ''
            if style_parts:
                style_parts_str = ' OR '.join(style_parts)
                style_parts_str = f" AND ({style_parts_str}) "

        # Figure out which vector to use, for cases in which that's an option.
        vec_to_use = None
        if hasattr(self.config_obj, "vec_to_use"):
            vec_to_use = self.config_obj.vec_to_use
        else:
            msg = 'ERROR: no vec to use!'
            debug.log(__file__, msg)
            raise Exception(msg)

        # Make sure this is a legit value to use
        if vec_to_use not in enums.get_enum_vals('vec_type_class'):
            msg = 'ERROR: Unknown vec type!'
            tskm.emit_status(msg, print_also=gl_d)
            debug.log(__file__, msg)
            raise Exception(msg)
        else:
            vec_to_use = vec_type_class(vec_to_use).value

        all_queries = {}

        # Query to get all main string vectors for codes in the code set
        attr = 'match_code_main_str'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get code's main string's vector *** --
                SELECT DISTINCT ON
					(
					cs.code_id
                    , sv.{vec_to_use}
					)
                    cs.code_id
                    , sv.{vec_to_use} AS code_vec
                FROM {odc.schema}.codes codes
                INNER JOIN {odc.schema}.code_sets cs
                    ON cs.set_name = :match_to_code_set_name AND codes.id = cs.code_id
                INNER JOIN {odc.schema}.str_vectors sv
                    ON sv.str_id = codes.main_str_id AND sv.embedder_meta_id = :embedder_meta_id           
            '''
            all_queries[attr].add_param('match_to_code_set_name', self.config_obj.match_to_code_set_name)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)

        # Query to get all non-expansion string vectors for codes in the code set
        attr = 'match_code_other_strs'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get code's other string vectors *** --
                SELECT DISTINCT ON
					(
					cs.code_id
                    , sv.{vec_to_use}
					)
                    cstrs.code_id
                    , sv.{vec_to_use} AS code_vec
                FROM {odc.schema}.code_strs cstrs
                INNER JOIN {odc.schema}.code_sets cs
                    ON cs.set_name = :match_to_code_set_name AND cstrs.code_id = cs.code_id
                INNER JOIN {odc.schema}.str_vectors sv
                    ON sv.str_id = cstrs.str_id AND sv.embedder_meta_id = :embedder_meta_id           
                '''
            # Get params for queries needed above (and also below)
            all_queries[attr].add_param('match_to_code_set_name', self.config_obj.match_to_code_set_name)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)


        # Query to get code's summary vectors for all official code strings for a code
        attr = 'match_code_summary_vec'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get code's summary vector of all of its official strings *** --
                SELECT DISTINCT ON
					(
					csvs.code_id
                    , csvs.mean
					)
                    csvs.code_id
                    , csvs.mean AS code_vec
                FROM {odc.schema}.code_summary_vectors csvs
                INNER JOIN {odc.schema}.code_sets cs
                    ON cs.set_name = :match_to_code_set_name AND csvs.code_id = cs.code_id
                WHERE
                    csvs.embedder_meta_id = :embedder_meta_id        
                '''
            # Get params for queries needed above (and also below)
            all_queries[attr].add_param('match_to_code_set_name', self.config_obj.match_to_code_set_name)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)

        # Query to get all expansion string vectors for codes in the code set
        attr = 'match_code_expansion_summary_vec'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get code original+expansion summary vector *** --
                SELECT DISTINCT ON
                    (
                    cs.code_id
                    , sessv.orig_and_exp_mean
                    )
                    cs.code_id
                    , sessv.orig_and_exp_mean AS code_vec
                FROM {odc.schema}.code_sets cs
                INNER JOIN {odc.schema}.code_strs cstrs
                    ON cs.code_id = cstrs.code_id
                INNER JOIN {odc.schema}.str_expansion_set ses
                    ON cstrs.str_id = ses.orig_str_id
                INNER JOIN {odc.schema}.str_expansion_set_summary_vectors sessv
                    ON ses.id = sessv.str_expansion_set_id AND sessv.embedder_meta_id = :embedder_meta_id
                INNER JOIN {odc.schema}.str_expansion_set_populator sesp
                    ON ses.str_expansion_set_populator_id = sesp.id
                WHERE 
                    cs.set_name = :match_to_code_set_name
                    {style_parts_str}       
                '''
            # Get params for queries needed above (and also below)
            all_queries[attr].add_param('match_to_code_set_name', self.config_obj.match_to_code_set_name)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)

        # Query for match object's main string
        attr = 'match_obj_main_str'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get object main string (vector) *** --
                SELECT DISTINCT 
                    *
                FROM
                    (
                    SELECT
                        sv.{vec_to_use} AS obj_vec
                    FROM {odc.schema}.str_vectors sv
                    WHERE 
                        sv.str_id = :obj_str_id
                        AND sv.embedder_meta_id = :embedder_meta_id
                    LIMIT 1 -- there should only be one
                    )sq_obj_main_str     
                '''
            # Get params for queries needed above (and also below)
            # Next one has to be set later
            all_queries[attr].add_param('obj_str_id', None)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)

        attr = 'match_obj_expansion_summary_vec'
        if check_if_attr_exists_and_is_true(self.config_obj, attr):
            all_queries[attr] = attr_query_item(attr)
            all_queries[attr].query = f'''
                -- *** Get object expansion summary vector *** --
                SELECT
                    sessv.orig_and_exp_mean AS obj_vec
                FROM {odc.schema}.str_expansion_set ses
                INNER JOIN {odc.schema}.str_expansion_set_summary_vectors sessv
                    ON ses.id = sessv.str_expansion_set_id AND sessv.embedder_meta_id = :embedder_meta_id
                INNER JOIN {odc.schema}.str_expansion_set_populator sesp
                    ON ses.str_expansion_set_populator_id = sesp.id
                WHERE 
                    ses.orig_str_id = :obj_str_id
                    {style_parts_str}    
                '''
            # Get params for queries needed above (and also below)
            # Next one has to be set later
            all_queries[attr].add_param('obj_str_id', None)
            all_queries[attr].add_param('embedder_meta_id', self.embedder_meta_id)

        return all_queries, expansion_strs_query_params


def populate_rel_code_matches(
    rel_code_matches_populator_obj:rel_code_matches_populator_class
    , top_hit_count:int=4
    ):

    match_populator_obj = matches_populator_class(
        config_obj=rel_code_matches_populator_obj
        , row_params = {'obj_str_id': 'obj_str_id'}
        , left_queries_list=[
            'match_obj_main_str'
            , 'match_obj_expansion_summary_vec'
            ]
        , right_queries_list=[
            'match_code_main_str'
            , 'match_code_other_strs'
            , 'match_code_summary_vec'
            , 'match_code_expansion_summary_vec'
            ]
        , left_vec_name='obj_vec'
        , right_vec_name='code_vec'
        , top_hit_count=top_hit_count
        , unmatched_getter_func=matches_populator_class.get_rel_codes_to_match_query_item
    )
    match_populator_obj.do_matches_populate()







