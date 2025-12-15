/*
  ~ Copyright (c) 2025 Keylog Solutions LLC
  ~
  ~ ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.
  ~
  ~ Licensed under the Apache License, Version 2.0 (the "License");
  ~ you may not use this file except in compliance with the License.
  ~ You may obtain a copy of the License at
  ~
  ~     http://www.apache.org/licenses/LICENSE-2.0
  ~
  ~ Unless required by applicable law or agreed to in writing, software
  ~ distributed under the License is distributed on an "AS IS" BASIS,
  ~ WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ~ See the License for the specific language governing permissions and
  ~ limitations under the License.
*/

let taskId = null;

function lockPage() {
  document.getElementById('pageLock').classList.add('locked');
}

function unlockPage() {
  document.getElementById('pageLock').classList.remove('locked');
}

function setWaiting(isWaiting) {
  const status_area = document.getElementById('status_area');
  if (isWaiting) {
    document.body.classList.add('waiting');
    status_area.style.display = 'block';
  } else {
    document.body.classList.remove('waiting');
    status_area.style.display = 'none';
  }
}

/*
function startTask() {
  postWithContext('/start_task').then(data => {
    taskId = data.task_id;

    lockPage();
    setWaiting(true);
    updateStatus("Working...");
    pollStatus();
  }).catch(err => {
    updateStatus("Failed to start: " + err.message, true);
  });
}
*/

function pollStatus() {
  alert(taskId)
  if (!taskId) return;

  getWithContext('/get_task_status', { task_id: taskId }).then(
    data => {
        alert(data);
        updateStatus(data.status);

    if (!data.done) {
      setTimeout(pollStatus, 15000);
    } else {
      setWaiting(false);
      unlockPage();
      updateStatus("Done!");
    }
  }).catch(err => {
    setWaiting(false);
    unlockPage();
    updateStatus("Error occurred: " + err.message, true);
  });
}

function cancelTask() {
  if (!taskId) return;

  postWithContext('/cancel_task', { task_id: taskId }).then(data => {
    if (data.cancelled) {
      unlockPage();
      setWaiting(false);
      updateStatus("Cancelled!");
    }
  }).catch(err => {
    unlockPage();
    setWaiting(false);
    updateStatus("Cancel failed: " + err.message, true);
  });
}

function updateStatus(message, isError = false) {
  const status = document.getElementById('taskStatus');
  status.innerHTML = isError
    ? `<span class='error-text'>${message}</span>`
    : message;
}