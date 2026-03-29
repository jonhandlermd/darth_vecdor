/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Task Management Module
 * Handles asynchronous task tracking, status polling, and UI locking
 */

import { get_with_context, post_with_context } from './utils.js';
import { 
  API_ENDPOINTS, 
  TIMING, 
  UI_CONFIG, 
  STATUS_MESSAGES 
} from '../config.js';

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

/**
 * Current task ID being tracked
 * @type {string|null}
 */
let task_id = null;

/**
 * Current page name (for context tracking)
 * @type {string|null}
 */
let current_page_name = null;

/**
 * Accumulated retained content (messages with is_status_only=False)
 * @type {Array<string>}
 */
let retained_content = [];

// ============================================================================
// PAGE LOCKING (PREVENT USER INTERACTION)
// ============================================================================

/**
 * Locks the page to prevent user interaction during async operations
 */
export function lock_page() {
  document.getElementById(UI_CONFIG.ELEMENTS.PAGE_LOCK).classList.add(UI_CONFIG.CLASSES.LOCKED);
}

/**
 * Unlocks the page to allow user interaction
 */
export function unlock_page() {
  document.getElementById(UI_CONFIG.ELEMENTS.PAGE_LOCK).classList.remove(UI_CONFIG.CLASSES.LOCKED);
}

// ============================================================================
// STATUS UI CONTROLS
// ============================================================================

/**
 * Shows the close button in the status area
 */
export function show_close_button() {
  const btn = document.getElementById(UI_CONFIG.ELEMENTS.CLOSE_BUTTON);
  btn.style.display = UI_CONFIG.DISPLAY.INLINE_BLOCK;
  btn.style.opacity = "1";
}

/**
 * Hides the close button in the status area
 */
export function hide_close_button() {
  const btn = document.getElementById(UI_CONFIG.ELEMENTS.CLOSE_BUTTON);
  btn.style.display = UI_CONFIG.DISPLAY.NONE;
  btn.style.opacity = "0";
}

/**
 * Shows the cancel button in the status area
 */
export function show_cancel_button() {
  const btn = document.getElementById(UI_CONFIG.ELEMENTS.CANCEL_BUTTON);
  btn.style.display = UI_CONFIG.DISPLAY.INLINE_BLOCK;
  btn.style.opacity = "1";
}

/**
 * Hides the cancel button in the status area
 */
export function hide_cancel_button() {
  const btn = document.getElementById(UI_CONFIG.ELEMENTS.CANCEL_BUTTON);
  btn.style.display = UI_CONFIG.DISPLAY.NONE;
  btn.style.opacity = "0";
}

// ============================================================================
// WAITING STATE MANAGEMENT
// ============================================================================

/**
 * Sets the UI to waiting state (showing spinner, locking page)
 * @param {boolean} is_waiting - Whether to show waiting state
 */
export function set_waiting(is_waiting) {
  const status_area = document.getElementById(UI_CONFIG.ELEMENTS.STATUS_AREA);
  const spinner = document.getElementById(UI_CONFIG.ELEMENTS.SPINNER);
  const cancel_btn = document.getElementById(UI_CONFIG.ELEMENTS.CANCEL_BUTTON);
  const close_btn = document.getElementById(UI_CONFIG.ELEMENTS.CLOSE_BUTTON);

  if (is_waiting) {
    lock_page();
    status_area.style.animation = UI_CONFIG.ANIMATIONS.FADE_IN;
    status_area.style.display = UI_CONFIG.DISPLAY.BLOCK;

    // Always restart spinner animation
    spinner.style.display = UI_CONFIG.DISPLAY.INLINE_BLOCK;
    const new_spinner = spinner.cloneNode(true);
    spinner.parentNode.replaceChild(new_spinner, spinner);

    cancel_btn.style.display = UI_CONFIG.DISPLAY.INLINE_BLOCK;
    cancel_btn.style.opacity = "1";
    close_btn.style.display = UI_CONFIG.DISPLAY.NONE;
    close_btn.style.opacity = "0";

  } else {
    // Finished state
    const current_spinner = document.getElementById(UI_CONFIG.ELEMENTS.SPINNER);
    if (current_spinner) {
      current_spinner.style.display = UI_CONFIG.DISPLAY.NONE;
    }

    cancel_btn.style.display = UI_CONFIG.DISPLAY.NONE;
    cancel_btn.style.opacity = "0";
    close_btn.style.display = UI_CONFIG.DISPLAY.INLINE_BLOCK;
    close_btn.style.opacity = "1";
  }
}

// ============================================================================
// STATUS MESSAGE DISPLAY
// ============================================================================

/**
 * Updates the status message displayed to the user
 * @param {string} message - The status message to display
 * @param {boolean} is_error - Whether this is an error message
 */
export function update_status(message, is_error = false) {
  const status = document.getElementById(UI_CONFIG.ELEMENTS.STATUS_TEXTAREA);
  status.value = is_error ? `${STATUS_MESSAGES.ERROR_PREFIX}${message}` : message;
}

// ============================================================================
// TASK POLLING
// ============================================================================

/**
 * Polls the server for task status at regular intervals
 * Automatically calls itself until task is complete
 */
export function poll_status() {
  if (!task_id) return;

  get_with_context(API_ENDPOINTS.GET_TASK_STATUS, { task_id: task_id })
    .then(data => {
      // Handle retained content (messages with is_status_only=False)
      if (data.retained_content && Array.isArray(data.retained_content)) {
        retained_content = data.retained_content;
      }

      // Show current status (this gets replaced each poll)
      update_status(data.status);

      if (!data.done) {
        // Continue polling
        setTimeout(poll_status, TIMING.TASK_POLL_INTERVAL);
/*
      } else {
        // Task complete
        set_waiting(false);

        // Build final display: "Done" followed by retained content
        const status_textarea = document.getElementById(UI_CONFIG.ELEMENTS.STATUS_TEXTAREA);

        if (retained_content.length > 0) {
          // Show Done + separator + accumulated retained content
          status_textarea.value =
            STATUS_MESSAGES.DONE + '\n' +
            '─'.repeat(50) + '\n' +
            retained_content.join('\n');
        } else {
          // No retained content, just show Done
          status_textarea.value = STATUS_MESSAGES.DONE;
        }

        // Clear state
        task_id = null;
        retained_content = [];
*/
} else {
        // Task complete
        set_waiting(false);

        // Build final display: final status followed by retained content
        const status_textarea = document.getElementById(UI_CONFIG.ELEMENTS.STATUS_TEXTAREA);
        const final_status = data.status || STATUS_MESSAGES.DONE;

        if (retained_content.length > 0) {
          // Show final status + separator + accumulated retained content
          status_textarea.value =
            final_status + '\n' +
            '─'.repeat(50) + '\n' +
            retained_content.join('\n');
        } else {
          // No retained content, just show final status
          status_textarea.value = final_status;
        }

        // Clear state
        task_id = null;
        retained_content = [];
      }
    })
    .catch(err => {
      set_waiting(false);
      update_status(`Error occurred: ${err.message}`, true);
      retained_content = [];
    });
}

// ============================================================================
// TASK CANCELLATION
// ============================================================================

/**
 * Cancels the currently running task
 */
/*
export function cancel_task() {
  if (!task_id) {
    alert(STATUS_MESSAGES.NO_TASK_ID);
    return;
  }

  post_with_context(API_ENDPOINTS.CANCEL_TASK, { task_id: task_id })
    .then(data => {
      if (data.cancelled) {
        update_status(STATUS_MESSAGES.CANCELLED);
      } else {
        const msg = `Cancel request sent, but task not confirmed cancelled.\n${data}`;
        alert(msg);
        update_status(msg, true);
      }
    })
    .catch(err => {
      const msg = err?.message || err?.toString() || STATUS_MESSAGES.UNKNOWN_ERROR;
      alert(msg);
      update_status(`${STATUS_MESSAGES.CANCEL_FAILED}: ${msg}`, true);
    })
    .finally(() => {
      unlock_page();
      set_waiting(false);
    });
}
*/
export function cancel_task() {
  if (!task_id) {
    alert(STATUS_MESSAGES.NO_TASK_ID);
    return;
  }

  // Show immediate feedback
  update_status(STATUS_MESSAGES.CANCEL_REQUESTED);

  post_with_context(API_ENDPOINTS.CANCEL_TASK, { task_id: task_id })
    .then(data => {
      // Polling will continue and show the final status from server
      // Don't stop polling or unlock - let the normal poll cycle handle it
      if (!data.cancelled) {
        // Alert if cancellation failed, but keep polling to see what happens
        const msg = `Cancel request sent, but task not confirmed cancelled.\n${data}`;
        alert(msg);
      }
    })
    .catch(err => {
      // Even on error, keep polling - server might still be processing
      const msg = err?.message || err?.toString() || STATUS_MESSAGES.UNKNOWN_ERROR;
      alert(`Cancel request error: ${msg}\nWill continue monitoring task status.`);
    });
  // Note: Do NOT unlock page, clear task_id, or stop polling here
  // Let poll_status() handle everything when server returns done:true
}

// ============================================================================
// TASK ID MANAGEMENT
// ============================================================================

/**
 * Sets the current task ID being tracked
 * @param {string} id - The task ID
 */
export function set_task_id(id) {
  task_id = id;
}

/**
 * Gets the current task ID
 * @returns {string|null} The current task ID or null
 */
export function get_task_id() {
  return task_id;
}

/**
 * Sets the current page name for context tracking
 * @param {string} name - The page name
 */
export function set_current_page_name(name) {
  current_page_name = name;
}

/**
 * Gets the current page name
 * @returns {string|null} The current page name or null
 */
export function get_current_page_name() {
  return current_page_name;
}