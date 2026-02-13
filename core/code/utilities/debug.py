

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

####################
####################
####################
# IMPORTS
####################
####################
####################
import app_source.public_repo.core.configs.other_configs as oc
import app_source.public_repo.core.configs.file_locations as bfl
import app_source.public_repo.core.code.utilities.file_utils as fu
import datetime
import sys

########################
# Global variables
########################
default_d = oc.d
default_log_debugging = oc.default_log_debugging
default_show_log_msgs = oc.default_show_log_msgs
default_show_progress = oc.default_show_progress
default_log_progress = oc.default_log_progress
log_tag_start = 'at'

#####################
# Make locations if they don't exist already
#####################
fu.create_folder(bfl.debugging_directory)

#####################
# BEGIN FUNCTION
# Print debugging info if requested to do so
#####################
def debug(msg, **kwargs):
    #### Deal with kwargs
    d = kwargs.get("d", default_d)
    sender = kwargs.get("sender", 'debug')
    do_log = kwargs.get("do_log", default_log_debugging)

    #### Do the work (show message, and log if requested to do so
    __do_show(msg, sender, d, do_log, bfl.debug_filepath, 'debug')

    #### All done!
    return

#############################
# END FUNCTION
#############################


#####################
# BEGIN FUNCTION
# Print debugging info if requested to do so
#####################
def show_progress(msg, **kwargs):
    #### Deal with kwargs
    d = kwargs.get("suppress", default_show_progress)
    sender = kwargs.get("sender", 'progress')
    do_log = kwargs.get("do_log", default_log_progress)

    #### Do the work (show message, and log if requested to do so
    __do_show(msg, sender, d, do_log, bfl.progress_filepath, 'progress')

    #### All done!
    return

#############################
# END FUNCTION
#############################


#############################
# BEGIN FUNCTION
# Show on screen debug or progress stuff
#############################
def __do_show(msg, sender, do_showing, do_log_if_doing_showing, log_path, log_type):

    #### If we are doing the showing of messages, then print the msg to stdout otherwise return
    if do_showing:
        #### Kill this pass if we actually want to show the messages.
        # pass
        #### FOR SAFETY, I HAVE COMMENTED THIS OUT. ALTHOUGH IT SHOULD ONLY EVER PRINT OUT TO STDOUT,
        #### I DON'T KNOW UNDER WHAT CONDITIONS IT COULD POTENTIALLY RETURN SENSITIVE OR UNINTENDED INFORMATION
        #### TO AN END USER OR SOMEONE WHO SHOULD NOT SEE IT
        print(f"Debug message type - {log_type}: {msg}")
        # print("Debug message would have printed.")
        # write_to_log(sender, msg, log_path, log_type)
    else:
        return

    if do_log_if_doing_showing:
        write_to_log(sender, msg, log_path, log_type)

    #### All done!
    return

#############################
# END FUNCTION
#############################


#############################
# BEGIN FUNCTION
# Append error to file and print error prn
#############################
def log(sender:str, msg:str, **kwargs):
    """

    :param sender: info about the source of the error, like the file, module, etc. that sent it
    :param msg: message to log in log file
    :param kwargs: 'filepath' of log, default is the config error filepath; 'log_type' description of entry, default is error; and 'show_log_msg' for whether or not to show the log message in stdout, default is whatever is set in other configs file.
    :return: None
    """

    #### Deal with kwargs
    file_path = kwargs.get('file_path', bfl.errors_filepath)
    log_type = kwargs.get('log_type', 'error')
    show_log_msg = kwargs.get('show_log_msg', default_show_log_msgs)

    write_to_log(sender, msg, file_path, log_type)

    if show_log_msg:
        #### FOR SAFETY, I HAVE COMMENTED THIS OUT. ALTHOUGH IT SHOULD ONLY EVER PRINT OUT TO STDOUT,
        #### I DON'T KNOW UNDER WHAT CONDITIONS IT COULD POTENTIALLY RETURN SENSITIVE OR UNINTENDED INFORMATION
        #### TO AN END USER OR SOMEONE WHO SHOULD NOT SEE IT
        #print(msg)
        print("Check log.")

    return
#############################
# END FUNCTION
#############################


#############################
# BEGIN FUNCTION
# Append error to file and print error prn
#############################
def write_to_log(sender, msg, file_path, log_type):

    if msg is not None:
        #### Concoct the time to show
        now = datetime.datetime.now()
        dt = now.strftime("%Y-%m-%d %H:%M:%S")

        log_msg = f'''

<{log_tag_start}_{log_type}>
    <{log_tag_start}_datetime>{dt}</{log_tag_start}_datetime>
    <{log_tag_start}_sender>{sender}</{log_tag_start}_sender>
    <{log_tag_start}_msg>
    {msg}
    </{log_tag_start}_msg>
</{log_tag_start}_{log_type}>

            '''

        #### Append errors to errors file
        # fu.append_to_file(log_msg, file_path, add_newlines=False)
        fu.capped_append(log_msg, file_path, max_bytes=oc.max_logfile_bytes, add_newlines=False)

    return
#############################
# END FUNCTION
#############################