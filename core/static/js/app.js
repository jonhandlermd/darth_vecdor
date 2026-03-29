/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Application Core Module
 * Handles initialization, routing, and page rendering
 */

import { logout } from './core/utils.js';
import { generate_menu, navigate_to, initialize_menu_listeners } from './ui/navigation.js';
import { load_saved_theme, initialize_tooltips, render_table } from './ui/ui_helpers.js';
import { unlock_page } from './core/task_manager.js';
import { get_with_context } from './core/utils.js';
import { STATUS_MESSAGES, RESPONSE_PATTERNS, DEFAULTS, UI_CONFIG } from './config.js';

// Import manage_json_resp for inline use if needed
function manage_json_resp(json) {
  if (!json || typeof json !== 'object') {
    throw new Error(STATUS_MESSAGES.INVALID_JSON);
  }
  if (json.status?.toLowerCase().startsWith(RESPONSE_PATTERNS.ERROR_STATUS_PREFIX)) {
    throw new Error(json.status);
  }
  const data = typeof json.data === 'string' ? JSON.parse(json.data) : json.data;
  return data;
}

// ============================================================================
// PREACT REFERENCES
// ============================================================================

let h, render;

/**
 * Sets Preact references (h and render functions)
 * Must be called before using any Preact functionality
 * @param {Function} create_element - Preact's h function
 * @param {Function} render_func - Preact's render function
 */
export function set_preact_refs(create_element, render_func) {
  h = create_element;
  render = render_func;
}

// ============================================================================
// DYNAMIC PAGE RENDERING
// ============================================================================

/**
 * Renders a dynamic page by fetching data and applying a render function
 * @param {Object} config - Page configuration with fetchUrl and renderFunction
 */
async function render_dynamic_page(config) {
  const container = document.getElementById(UI_CONFIG.ELEMENTS.APP_CONTAINER);
  
  // Show loading message
  container.innerHTML = STATUS_MESSAGES.LOADING;

  try {
    const resp = await fetch(config.fetchUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    
    const json_resp = manage_json_resp(data);

    // Clear container and render content
    container.innerHTML = '';
    const content = h('div', {},
      h('h2', {}, config.label || 'Results'),
      config.renderFunction(json_resp, h)
    );
    render(content, container);

  } catch (err) {
    container.innerHTML = 'Error loading page';
    console.error(err);
  }
}

// ============================================================================
// SECTION/PAGE ROUTING
// ============================================================================

/**
 * Shows the appropriate section based on current hash
 * Main routing function for the application
 * @param {Object} app_config - Application configuration
 * @param {Function} darth_vecdor_form - Form component constructor
 */
export function show_section(app_config, darth_vecdor_form) {
  const container = document.getElementById(UI_CONFIG.ELEMENTS.APP_CONTAINER);
  const hash = decodeURIComponent(window.location.hash.substring(1)) || DEFAULTS.HOME_PAGE;

  const config = app_config[hash];
  if (!config) {
    container.innerHTML = `<h1>Page Not Found</h1>`;
    return;
  }

  // Clear previous content or unmount old components
  container.innerHTML = '';
  render(null, container);

  // Render based on type
  if (config.type === "page") {
    container.innerHTML = config.content;
  }
  else if (config.type === "form") {
    render(h(darth_vecdor_form, { config }), container);
  }
  else if (config.type === "dynamic_page") {
    render_dynamic_page(config);
  }
  else if (config.type === 'action') {
    logout();
  }
}

// ============================================================================
// APPLICATION INITIALIZATION
// ============================================================================

/**
 * Initializes the application
 * Sets up event listeners, loads theme, generates menu, and shows initial section
 * @param {Object} app_config - Application configuration
 * @param {Function} darth_vecdor_form - Form component constructor
 */
export function initialize_app(app_config, darth_vecdor_form) {
  // Load saved theme
  load_saved_theme();
  
  // Initialize UI components
  initialize_tooltips();
  initialize_menu_listeners();
  
  // Generate menu
  generate_menu(app_config);
  
  // Set up routing
  window.addEventListener("hashchange", () => show_section(app_config, darth_vecdor_form));
  
  // Navigate to home if no hash present
  if (!window.location.hash) {
    window.location.hash = encodeURIComponent(DEFAULTS.HOME_PAGE);
  }
  
  // Show initial section
  show_section(app_config, darth_vecdor_form);
  
  // Set up status close button handler
  const close_button = document.getElementById(UI_CONFIG.ELEMENTS.CLOSE_BUTTON);
  if (close_button) {
    close_button.addEventListener("click", () => {
      document.getElementById(UI_CONFIG.ELEMENTS.STATUS_AREA).style.display = UI_CONFIG.DISPLAY.NONE;
      unlock_page();
    });
  }
}

/**
 * Convenience function to initialize everything with Preact
 * @param {Object} preact - Preact library object
 * @param {Object} preact_hooks - Preact hooks library object
 * @param {Object} app_config - Application configuration
 * @param {Function} darth_vecdor_form - Form component constructor
 */
export function bootstrap(preact, preact_hooks, app_config, darth_vecdor_form) {
  set_preact_refs(preact.h, preact.render);
  
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initialize_app(app_config, darth_vecdor_form);
    });
  } else {
    initialize_app(app_config, darth_vecdor_form);
  }
}

/**
 * Export render_table with h parameter for use in dynamic pages
 */
export function get_render_table() {
  return (data) => render_table(data, h);
}
