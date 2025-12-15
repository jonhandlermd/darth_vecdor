

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

import threading
from threading import Thread, Event
from contextvars import ContextVar
import uuid
import traceback

_task_context = {}  # task_id → {status, cancel, done}
_current_task_id = ContextVar("current_task_id", default=None)

def launch_task(task_function, *args, **kwargs):
    task_id = task_function.__name__ + '_' +  str(uuid.uuid4())
    cancel = Event()
    _task_context[task_id] = {
        'status': 'Pending...',
        'done': False,
        'cancel': cancel
    }

    def wrapper():
        _current_task_id.set(task_id)
        try:
            task_function(*args, **kwargs)
        except Exception as wrapper_exception:
            tb = traceback.TracebackException.from_exception(wrapper_exception)
            for frame in tb.stack:
                print(f"{frame.filename}, line {frame.lineno}, in {frame.name}")
            print(f"{type(wrapper_exception).__name__}: {wrapper_exception}")
            emit_status(f"Error from wrapper doing {args}: {wrapper_exception}")
        else:
            emit_status("Completed.")
        finally:
            _task_context[task_id]['done'] = True
            _current_task_id.set(None)

    Thread(target=wrapper, name=task_id, daemon=True).start()
    return task_id

def emit_status(message, print_also=False):
    task_id = _current_task_id.get()
    if task_id and task_id in _task_context:
        _task_context[task_id]['status'] = message
        if print_also:
            print(f"From task manager emit status: {message}")

def print_all_running_threads():
    print("--------------")
    print("Running threads:")
    counter = 0
    for t in threading.enumerate():
        counter += 1
        print(f"Thread {t.name} is still running")
    if counter == 0:
        print("NO RUNNING THREADS!")
    print("--------------")

def get_cancel_event(task_id=None):
    task_id = task_id or _current_task_id.get()
    return _task_context.get(task_id, {}).get('cancel')

def is_cancelled(task_id=None):
    event = get_cancel_event(task_id)
    return event.is_set() if event else False

def get_task_status(task_id):
    task = _task_context.get(task_id)
    if not task:
        return None
    return {
        'status': task['status'],
        'done': task['done']
    }

def cancel_task(task_id):
    task = _task_context.get(task_id)
    if task:
        task['cancel'].set()
        task['status'] = "Cancelled."
        return True
    return False
