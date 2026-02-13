
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
import json as json
from flask import current_app, g, abort, Blueprint, request
import app_source.public_repo.core.configs.file_locations as fl
import app_source.public_repo.core.code.request_handlers.access_functions as af

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
def get_html(filename, replacers=None, **kwargs):
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
# Get html
#######################
def get_html_with_replacers_param(filename, replacers=None, **kwargs):
    with open(fl.html_loc + filename, encoding='utf8') as tf:
        lines = (tf.readlines())
        return_string = "\n".join(lines)
        for replacer in replacers:
            return_string = return_string.replace(replacer, replacers[replacer])
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
def get_request_data():
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


#*************************
# Do work prior to fulfilling request.
# 1) Get the request data into a Flask g variable.
# 2) Get the user and roles from the header and into a Flask g variable.
# 3) If endpoint doesn't exist, send back a 404 code.
# IMPORTANT NOTE: Protection is only supplemental to the main protection you must provide from the web gateway.
# Don't trust this protection!
# This protection TOTALLY TRUSTS the gateway to pass user and roles correctly.
# Use this functionality AT YOUR OWN RISK!
def do_pre_fulfill_request_work(bp:"Blueprint"):

    # Get the request data. This will put the result into g.req_args so that anything with access to Flask's
    # g variable can get it.
    get_request_data()

    # At app runtime, the validate_blueprint_endpoints ensures that all my endpoint blueprint
    # endpoints have the required decorator to check if access is allowed, so don't need to recheck
    # that here.

    # Put endpoint in the g variable so that logging or auditing has access to it as long
    # as it has access to Flask's g variable.
    g.ks_endpoint = request.endpoint
    # Now, get the endpoint view.
    g.ks_endpoint_view = current_app.view_functions.get(g.ks_endpoint)

    # This next line should abort the request if it's not allowed.
    allowed, msg = af.enforce_endpoint_access()
    if not allowed:
        abort(403, msg)

    # If you get here then process not aborted earlier and you are done!
    return


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


