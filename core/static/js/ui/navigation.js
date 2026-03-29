/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Navigation & Menu Module
 * Handles menu generation, navigation, and routing
 */

import { get_accessible_endpoints, set_menu_visibility } from '../core/access.js';
import { UI_CONFIG } from '../config.js';

// ============================================================================
// MENU GENERATION
// ============================================================================

/**
 * Generates the application menu based on configuration
 * Respects accessibility permissions from server
 * @param {Object} app_config - The application configuration object
 */
export async function generate_menu(app_config) {
  // Get from server what endpoints are accessible
  const accessible_endpoints = await get_accessible_endpoints();

  // Modify the app_config to add metadata about accessible menu items
  set_menu_visibility(app_config, accessible_endpoints);

  const menu = document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_MENU);
  menu.innerHTML = ''; // Clear old items

  // Group children by parent key
  const children_by_parent = {};
  Object.entries(app_config).forEach(([key, cfg]) => {
    if (cfg.parent) {
      if (!children_by_parent[cfg.parent]) children_by_parent[cfg.parent] = [];
      children_by_parent[cfg.parent].push(key);
    }
  });

  // Render top-level items and parents
  Object.entries(app_config).forEach(([key, cfg]) => {
    if (cfg.visible === false) return;
    if (cfg.parent) return; // Skip children; they'll be rendered below

    const label = cfg.label || key;
    const has_children = children_by_parent[key]?.some(
      child_key => app_config[child_key]?.visible !== false
    );
    
    // Skip menu parents with no visible children
    if (!has_children && cfg.type === 'menu_parent') return;

    const parent_item = document.createElement('div');
    parent_item.className = UI_CONFIG.CLASSES.MENU_ITEM + (has_children ? ` ${UI_CONFIG.CLASSES.HAS_CHILDREN}` : '');
    parent_item.style.cursor = 'pointer';

    const label_div = document.createElement('div');
    label_div.className = UI_CONFIG.CLASSES.MENU_LABEL;
    label_div.textContent = label;

    parent_item.appendChild(label_div);
    menu.appendChild(parent_item);

    if (has_children) {
      // Toggle submenu on parent label click
      label_div.onclick = (e) => {
        e.stopPropagation();
        const is_expanded = parent_item.classList.toggle(UI_CONFIG.CLASSES.EXPANDED);
        const children = document.querySelectorAll(`.submenu-of-${key}`);
        children.forEach(child => {
          child.classList.toggle(UI_CONFIG.CLASSES.HIDDEN, !is_expanded);
        });
      };

      // Render children as siblings, hidden by default
      children_by_parent[key]
        .filter(child_key => app_config[child_key]?.visible !== false)
        .forEach(child_key => {
          const child_cfg = app_config[child_key];
          if (!child_cfg) return;

          const child_item = document.createElement('div');
          child_item.className = `${UI_CONFIG.CLASSES.MENU_ITEM} ${UI_CONFIG.CLASSES.SUBMENU_ITEM} submenu-of-${key} ${UI_CONFIG.CLASSES.HIDDEN}`;
          child_item.style.cursor = 'pointer';

          const child_label = document.createElement('div');
          child_label.className = UI_CONFIG.CLASSES.MENU_LABEL;
          child_label.textContent = child_key;

          const child_desc = document.createElement('div');
          child_desc.className = UI_CONFIG.CLASSES.MENU_DESC;
          child_desc.textContent = '';

          child_item.appendChild(child_label);
          child_item.appendChild(child_desc);
          child_item.onclick = () => navigate_to(child_key);

          menu.appendChild(child_item);
        });

    } else {
      // If no children, clicking parent navigates immediately
      // (unless it's a menu parent, which we already filtered out)
      if (key in app_config && app_config[key].type !== 'menu_parent') {
        parent_item.onclick = () => navigate_to(key);
      }
    }
  });
}

// ============================================================================
// MENU CONTROL
// ============================================================================

/**
 * Collapses all expanded menu items
 */
export function collapse_menu() {
  const menu = document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_MENU);
  menu.querySelectorAll(`.${UI_CONFIG.CLASSES.MENU_ITEM}.${UI_CONFIG.CLASSES.EXPANDED}`).forEach(item => {
    item.classList.remove(UI_CONFIG.CLASSES.EXPANDED);
  });
  menu.querySelectorAll(`.${UI_CONFIG.CLASSES.SUBMENU_ITEM}`).forEach(item => {
    item.classList.add(UI_CONFIG.CLASSES.HIDDEN);
  });
  menu.classList.remove(UI_CONFIG.CLASSES.SHOW);
}

/**
 * Toggles the dropdown menu visibility
 */
export function toggle_dropdown() {
  document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_MENU).classList.toggle(UI_CONFIG.CLASSES.SHOW);
}

// ============================================================================
// NAVIGATION
// ============================================================================

/**
 * Navigates to a specific page by setting the hash
 * @param {string} page_name - The name of the page to navigate to
 */
export function navigate_to(page_name) {
  collapse_menu();
  window.location.hash = encodeURIComponent(page_name);
}

/**
 * Navigates to a section using hash
 * Legacy function for compatibility
 * @param {string} hash - The hash to navigate to
 */
export function navigate_section(hash) {
  document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_MENU).classList.remove(UI_CONFIG.CLASSES.SHOW);
  location.hash = hash;
}

// ============================================================================
// MENU EVENT LISTENERS
// ============================================================================

/**
 * Initializes menu event listeners
 * Closes menu when clicking outside
 */
export function initialize_menu_listeners() {
  document.addEventListener('click', function(event) {
    const menu = document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_MENU);
    const toggle_btn = document.getElementById(UI_CONFIG.ELEMENTS.DROPDOWN_BTN);

    // If click is NOT inside menu or toggle button, close the menu
    if (!menu.contains(event.target) && !toggle_btn.contains(event.target)) {
      menu.classList.remove(UI_CONFIG.CLASSES.SHOW);

      // Also collapse all expanded submenus
      menu.querySelectorAll(`.${UI_CONFIG.CLASSES.MENU_ITEM}.${UI_CONFIG.CLASSES.EXPANDED}`).forEach(item => {
        item.classList.remove(UI_CONFIG.CLASSES.EXPANDED);
      });
    }
  });
}
