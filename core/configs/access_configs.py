#  Copyright (c) 2026 Keylog Solutions LLC
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
ac = pci.bootstrap_import(f"access_configs.py", make_dummy_if_not_exists=True)

#*********** READ THIS! IMPORTANT! *******************#
# NOTE: Protection is only supplemental to the main protection YOU must provide from the web gateway.
# Don't trust this protection!
# This protection TOTALLY TRUSTS the gateway to pass user and roles correctly.
# Use this functionality AT YOUR OWN RISK!
#*****************************************************#

# Map headers to concepts related to access as named in this program
header_mapper = getattr(ac, 'header_mapper', {
        "X-Remote-User": "user",
        "X-Remote-Groups": "roles",
        }
    )

# Roles
# Dictionary where app role names are the keys and value is set of roles that may be passed in header that
# should map to that app role.
# Example:
# roles = {
#       'admin': {'sys_admin', 'admin'},
#       'standard': {'sys_admin', 'admin', 'basic_user', 'consultant'}
#       }
# A passed role from the headers can be in zero, one, or more than one of this app's roles.
roles = getattr(ac, 'roles', {})

# Even if the following variable is true, this will only be offered
# if running in dev mode or debug mode and if run from if __name__ is '__main__ in app.py
# The person running the app will be asked on command line to confirm desire to run in admin mode and if
# not confirmed, it will nto run in admin mode.
# The admin mode should only still be effective if request is coming from localhost.
# admin mode removes all endpoint access controls enforced by this app.
offer_run_as_admin = getattr(ac, 'offer_run_as_admin', False)




