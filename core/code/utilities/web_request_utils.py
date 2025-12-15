
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

##############################
# IMPORTS
##############################
import app_source.public_repo.core.configs.file_locations as fl
import json as json
from flask import g

##############################
##############################
##############################
##############################
# Common front end functions
##############################
##############################
##############################
##############################


#######################
# BEGIN FUNCTION
# Get html
#######################
def get_html(filename, **kwargs):
    with open(fl.html_loc + filename, encoding='utf8') as tf:
        lines = (tf.readlines())
        return_string = "\n".join(lines)
        for kwarg in kwargs:
            return_string.replace("<!--replaceme_" + kwarg + "-->", kwargs[kwarg])
        return return_string
#######################
# END FUNCTION
#######################


#######################
# BEGIN FUNCTION
# Check to make sure required arguments were provided
#######################
def check_reqs(req_list, req_args=None):

    if not req_args:
        req_args = g.req_args

    err_list = []
    for req_arg in req_list:
        if req_arg not in req_args.keys():
            err_list.append(req_arg)

    if err_list:
        return f"ERROR: The following required inputs were not provided:  {', '.join(err_list)}."
    else:
        return ''
#######################
# END FUNCTION
#######################


##########################
# BEGIN FUNCTION
# Style for Yes in dataframe as HTML
##########################
def style_all_yeses(val):
    """
    Takes a scalar and returns a string with
    the css property `'color: red'` for negative
    strings, black otherwise.
    """
    font_weight = 'bold' if val == 'Yes' else 'normal'
    return f'font-weight: {font_weight}'
############################
# END FUNCTION
############################


##########################
# BEGIN FUNCTION
# Style for No in dataframe as HTML
##########################
def style_all_nos(val):
    """
    Takes a scalar and returns a string with
    the css property `'color: red'` for negative
    strings, black otherwise.
    """
    font_style = 'italic' if val == 'No' else 'normal'
    return f'font-style: {font_style}'
############################
# END FUNCTION
############################


##########################
# BEGIN FUNCTION
# Get request data
##########################
def get_request_data(request):
    req_args = {}

    # Include query parameters (?key=value)
    req_args.update(request.args.to_dict())

    # Include form fields from POST (form-urlencoded or multipart)
    req_args.update(request.form.to_dict())

    # Include JSON body (if applicable)
    if request.is_json:
        json_data = request.get_json(silent=True)
        if isinstance(json_data, dict):
            req_args.update(json_data)

    data = req_args.get('data')
    if data:
        g.req_args = json.loads(data)
    else:
        g.req_args = data

############################
# End function
############################


##########################
# Concoct response back to client
##########################
def concoct_response(status, data, raw_data_only=False):
    # print(status)
    # print(data)

    if raw_data_only:
        g.resp = data
    else:
        r_dict = {}
        r_dict["status"] = status
        r_dict["data"] = data
        g.resp = json.dumps(r_dict, default=str)

    g.resp_concocted = True
    return g.resp

############################
# End function
############################


