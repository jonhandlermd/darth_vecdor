/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * UI Utilities Module
 * Handles tooltips, theme management, and other UI-related functionality
 */

import { TIMING, THEME_CONFIG, UI_CONFIG } from '../config.js';

// ============================================================================
// TOOLTIP MANAGEMENT
// ============================================================================

/**
 * Timer for auto-closing tooltips
 * @type {number|null}
 */
let tooltip_auto_close_timer = null;

/**
 * Gets the tooltip auto-close timer
 * @returns {number|null}
 */
export function get_tooltip_timer() {
  return tooltip_auto_close_timer;
}

/**
 * Sets the tooltip auto-close timer
 * @param {number|null} timer
 */
export function set_tooltip_timer(timer) {
  tooltip_auto_close_timer = timer;
}

/**
 * Clears the tooltip auto-close timer
 */
export function clear_tooltip_timer() {
  if (tooltip_auto_close_timer) {
    clearTimeout(tooltip_auto_close_timer);
    tooltip_auto_close_timer = null;
  }
}

/**
 * Closes all visible tooltips
 */
export function close_all_tooltips() {
  document.querySelectorAll(`.${UI_CONFIG.CLASSES.TOOLTIP_TEXT}.${UI_CONFIG.CLASSES.SHOW}`).forEach(tip => {
    tip.classList.remove(UI_CONFIG.CLASSES.TOOLTIP_TOP);
    setTimeout(() => {
      tip.classList.remove(UI_CONFIG.CLASSES.SHOW);
    }, TIMING.TOOLTIP_ANIMATION_DELAY);
  });
}

/**
 * Initializes global tooltip event listeners
 * Should be called once during app initialization
 */
export function initialize_tooltips() {
  // Close any open tooltips if clicking outside
  window.addEventListener('click', () => {
    close_all_tooltips();
    clear_tooltip_timer();
  });
}

// ============================================================================
// THEME MANAGEMENT
// ============================================================================

/**
 * Toggles between light and dark themes
 * Saves preference to localStorage
 */
export function toggle_theme() {
  const current = document.body.getAttribute(THEME_CONFIG.ATTRIBUTE);
  const next = current === THEME_CONFIG.VALUES.DARK ? THEME_CONFIG.VALUES.LIGHT : THEME_CONFIG.VALUES.DARK;
  document.body.setAttribute(THEME_CONFIG.ATTRIBUTE, next);
  localStorage.setItem(THEME_CONFIG.STORAGE_KEY, next);
}

/**
 * Loads saved theme from localStorage
 * Should be called during app initialization
 */
export function load_saved_theme() {
  const saved = localStorage.getItem(THEME_CONFIG.STORAGE_KEY);
  if (saved) {
    document.body.setAttribute(THEME_CONFIG.ATTRIBUTE, saved);
  }
}

// ============================================================================
// TABLE RENDERING
// ============================================================================

/**
 * Renders a data array as an HTML table using Preact
 * Used for dynamic page content
 * @param {Array<Object>} data - Array of objects to render as table rows
 * @returns {Object} Preact virtual DOM element
 */
export function render_table(data, h) {
  if (!Array.isArray(data) || data.length === 0) {
    return h('div', {}, 'No data available.');
  }

  return h('table', { class: UI_CONFIG.CLASSES.DYNAMIC_TABLE },
    h('thead', {},
      h('tr', {},
        ...Object.keys(data[0]).map(k => h('th', {}, k))
      )
    ),
    h('tbody', {},
      data.map(row =>
        h('tr', {},
          ...Object.values(row).map(v => h('td', {}, v))
        )
      )
    )
  );
}

// ============================================================================
// STYLE HELPERS
// ============================================================================

/**
 * Returns CSS style object for disabled buttons
 * @param {boolean} disabled - Whether the button is disabled
 * @returns {Object} Style object
 */
export function get_button_style(disabled) {
  return {
    opacity: disabled ? 0.5 : 1,
    pointerEvents: disabled ? 'none' : 'auto'
  };
}
