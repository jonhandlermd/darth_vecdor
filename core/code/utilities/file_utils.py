

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
# IMPORTS
####################
####################
####################
import os
import gzip
import shutil
from zipfile import ZipFile as zf
import pathlib
from pathlib import Path
import app_source.public_repo.core.code.utilities.debug as debug


###############################
# GLobals
###############################
me = 'file_utils'


###############################
# BEGIN FUNCTION
# Check if file exists
###############################
def check_if_file_exists(file_path):
    if os.path.exists(file_path):
        return True
    else:
        return False
###############################
# BEGIN FUNCTION
# Get list of FOLDERS in directory
###############################
def get_folders(dir_path, **kwargs):

    #### Keep track of folders we find
    folders = []

    #### Loop through all folder contents
    for item in os.listdir(dir_path):
        #### Check if folder
        if os.path.isdir(os.path.join(os.path.abspath(dir_path), item)):
            folders.append(item)

    #### List from listdir is in arbitrary order.  Sort by name.
    folders.sort()

    return folders

#############################
# END FUNCTION
#############################


###############################
# BEGIN FUNCTION
# Get list of files in directory
###############################
def get_files(file_path, **kwargs):

    #### If they gave us a filepath, use it, otherwise use the one from the initialization of the object.
    file_type = kwargs.get("file_type", None)

    files = []
    for fn in os.listdir(file_path):
        if file_type is not None:
            if fn.endswith(file_type):
                files.append(fn)
        else:
            files.append(fn)

    #### List from listdir is in arbitrary order.  Sort by name.
    files.sort()

    return files

#############################
# END FUNCTION
#############################


########################
# Get list of data files
########################
def get_files_advanced(folder_path:str, extensions:list=None, keep_extension:bool=True, exclude_non_files=True):
    files = []
    if extensions is None:
        extensions = []
    for fn in os.listdir(folder_path):
        #### Get file extension
        ext = pathlib.Path(fn).suffix
        #### Get rid of the period
        ext = ext.replace('.', '')
        #### If they didn't ask for any extensions, we will include all files. Otherwise, we will include files
        #### as long as one of the extensions they requested.
        if not extensions or ext in extensions:
            #### Is this a "non-file" like __init__.py or any other file that starts with an underscroe or dot?
            if exclude_non_files and (fn.startswith('.') or fn.startswith('_')):
                continue

            #### Do they want us to keep the extension? If not, remove it.
            if not keep_extension:
                fn = pathlib.Path(fn).stem

            #### Now append the file
            files.append(fn)

    #### List is in arbitrary order. Sort by name.
    files.sort()

    #### All done -- return files
    return files

#############################
# END FUNCTION
#############################


###############################
# BEGIN FUNCTION
# Unzip a file
###############################
def unzip_file(zip_file, dest_loc, **kwargs):

    #### Deal with kwargs
    zip_type = kwargs.get("zip_type", "zip")

    #### Check if we got the needed info
    if zip_file is None or dest_loc is None:
        debug.log(me, f"Did not get either zip file or dest loc path.")
        exit()

    if zip_type == "gzip":
        #### Unzip the file
        with open(dest_loc, 'wb') as f_out, gzip.open(zip_file, 'rb') as f_in:
            shutil.copyfileobj(f_in, f_out)

    if zip_type == "zip":
        with zf(zip_file, 'r') as t_zip:
            #### **** DON'T DO PATH -- JUST UNZIP TO WORKING DIRECTORY
            t_zip.extractall(dest_loc)

    return

#############################
# END FUNCTION
#############################


###############################
# BEGIN FUNCTION
# Get list of files in directory
###############################
def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        debug.log(me, "Cannot delete file as it does not exist.")
    return

#############################
# END FUNCTION
#############################


#############################
# BEGIN FUNCTINO
# Append list to file
#############################
def append_to_file(string_or_list_of_strings, file_path, **kwargs):

    #### Deal with kwargs
    add_newlines = kwargs.get('add_newlines', True)

    if add_newlines:
        string_or_list_of_strings = map(lambda x: x + '\n', string_or_list_of_strings)
    try:
        with open(file_path, "a") as f:
            f.writelines(string_or_list_of_strings)
    except Exception as e:
        #### DO !!!NOT!!! CHANGE TO USE DEBUG TO WRITE THIS ERROR, BECAUSE DEBUG USES THIS ROUTINE TO WRITE THIS ERROR.
        #### We would end up in infinite loop.
        debug.log('file_utils.py append_to_file', f"ERROR: {e}")
        exit()

    return
#############################
# END FUNCTION
#############################


#############################
# START FUNCTION
#############################
def capped_append(
        content:str
        , base_path:str
        , max_bytes:int = 20 * 1024 * 1024 # 20 MB
        , **kwargs
        ):

    #### Deal with kwargs
    add_newlines = kwargs.get('add_newlines', True)

    # If we are supposed to add newlines to the end of each line of the content, then do so.
    write_content = content
    if add_newlines:
        write_content = map(lambda x: x + '\n', content)

    # Encode entry once to get size in bytes
    entry_bytes = write_content.encode("utf-8")
    entry_size = len(entry_bytes)

    # We are going to have two files. Make dictionary, key is file path, value is file size.
    # Initialize filesize to None.
    class file_class:
        def __init__(self, num):
            self.path = f"{base_path}.{num}.log"
            with open(self.path, "ab") as f:
                nothing_content = ''
                no_bytes = nothing_content.encode("utf-8")
                f.write(no_bytes)
            self.size = os.path.getsize(self.path)

        def write_to_file(self):
            try:
                with open(self.path, "ab") as f:
                    f.write(entry_bytes)
            except Exception as e:
                print('file_utils.py capped_append', f"ERROR: {e}")
                exit()

    file_obj_1 = file_class('1')
    file_obj_2 = file_class('2')

    # We always write to the 2nd file. If it's full, we erase the
    # 1st file and make the second file the first file.
    # Then we create the second file and write to it.
    # Do we have room in the 2nd file to write anything?
    if file_obj_2.size + entry_size > max_bytes:
        # Copy file 2 contents as file 1
        shutil.copy2(file_obj_2.path, file_obj_1.path)
        # Empty out file 2. This approach keeeps "inode" (metadata)
        with open(file_obj_2.path, "r+") as f:
            f.truncate(0)

    # Append new data to file_obj_2.
    file_obj_2.write_to_file()
#############################
# END FUNCTION
#############################


###############################
# BEGIN FUNCTION
# Create file or folder
###############################
def create_folder(the_path):
    os.makedirs(the_path, mode=0o777, exist_ok=True)


def write_if_changed(path: Path, new_text: str):
    new_text = new_text.strip()
    if path.exists():
        old_text = path.read_text().strip()
        if old_text == new_text:
            return  # No change needed
    path.write_text(new_text)
    print(f"📝 Updated {path.relative_to(Path.cwd())}")

