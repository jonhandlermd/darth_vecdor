To make Darth Vecdor
=====================
NOTE: This information may have errors, potentially serious ones, and is surely woefully incomplete. USE THIS AT YOUR OWN RISK. Scroll toward the bottom for license and other very important information, warnings, and caveats.

Clone a copy of the source code to your desired location.

Install the required libraries, in addition to Python, if not already installed. The requirements.txt file should help identify needed libraries, but may not be correct or complete. 

Create a parent directory to the public_repo directory. Name this parent directory app_source

Move or copy the file move_to_app_source_and_rename_as_just_app.py to the app_source directory you just created, and rename that file app.py

Move or copy the example_not_public directory to the app_source directory, and rename it to not_public

Go through every file in the not_public directory and adjust the contents as needed. For example, adding in the connection info to database and LLMs, and other configurations. Please handle all sensitive information safely and securely. This is entirely up to you.

Install the PostgreSQL database.
Make a PostgreSQL database called darth_vecdor
Make a schema in the darth_vecdor database called t_sys
Make a schema in the darth_vecdor database called dv_objs
Make a schema in the darth_vecdor database called custom_generated_tables

For the database user/login that Darth Vecdor will use, grant the ability to create, read, and write in those schemas (and probably the database). For this, consider (thank you ChatGPT):

<HR>
Grant rights on all existing tables/views at once
For bulk granting, you can run SQL like this:

-- Grant SELECT/INSERT/UPDATE/DELETE on all tables
GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA your_schema
TO your_user;

-- Grant SELECT on all views
GRANT SELECT
ON ALL TABLES IN SCHEMA your_schema
TO your_user;  -- views are included as tables in PostgreSQL


Default privileges (for future objects)
* There’s a secondary concept: Default Privileges (not always directly exposed in the GUI).
* Default privileges define what privileges new objects will have when created in this schema.
* For example, you could configure it so that any new table created in the schema automatically gives SELECT to a certain role.
* In SQL, this is done with:

ALTER DEFAULT PRIVILEGES IN SCHEMA my_schema
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO my_user;
* In PGAdmin, you may see something like “Default privileges” or an “Add Default” button when editing schema privileges. This is just a GUI way to manage that.
<HR>


Make sure all required or desired extensions are installed in the database. The ones I found I had were: CREATE EXTENSION IF NOT EXISTS btree_gin
CREATE EXTENSION IF NOT EXISTS pg_trgm
CREATE EXTENSION IF NOT EXISTS pgstattuple
CREATE EXTENSION IF NOT EXISTS vector

Create an external_js folder at this location: app_source/public_repo/core/static/ (inside that static directory)
Put the following JavaScript libraries in that external JS folder (should be downloadable from public sites):
- preach-10.26
- hooks.umd.js
- hooks.umd.js.map
- preact.umd.js
- preact.umd.js.map

Add or apply any security or privacy or other things as needed to ensure safety, security, and every other desirable attribute.

Run the program (app.py) as a Python program.

Open the appropriate URL to access the program (e.g., http://localhost:5001)

<HR>
Copyright (c) 2025 Keylog Solutions LLC

ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.



