/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Security & Permissions Module
 * Handles endpoint accessibility, URL extraction, and menu visibility
 */

import { normalize_url, get_with_context } from './utils.js';
import { URL_KEYS, API_ENDPOINTS } from '../config.js';

// ============================================================================
// ACCESSIBLE ENDPOINTS
// ============================================================================

/**
 * Fetches the list of accessible endpoints from the server
 * @returns {Promise<Set<string>>} Set of normalized accessible endpoint URLs
 */
export async function get_accessible_endpoints() {
  const res = await fetch(API_ENDPOINTS.GET_ACCESSIBLE_ENDPOINTS);
  const json = await res.json();
  
  // Import manage_json_resp if needed, or handle inline
  if (!json || typeof json !== 'object') {
    throw new Error("Invalid JSON");
  }
  if (json.status?.toLowerCase().startsWith("error")) {
    throw new Error(json.status);
  }
  
  const data = typeof json.data === 'string' ? JSON.parse(json.data) : json.data;
  const received_accessible_endpoints = data;
  
  return new Set(received_accessible_endpoints.map(normalize_url));
}

// ============================================================================
// URL EXTRACTION FROM CONFIGURATION
// ============================================================================

/**
 * Extracts all URL values from a single configuration object
 * @param {Object} obj - Configuration object to extract URLs from
 * @returns {Array<string>} Array of normalized URLs
 */
export function extract_urls_from_object(obj) {
  const urls = [];

  for (const [key, value] of Object.entries(obj)) {
    if (URL_KEYS.has(key) && typeof value === "string") {
      const normalized_value = normalize_url(value);
      urls.push(normalized_value);
    }
  }

  return urls;
}

/**
 * Recursively extracts all URLs from a configuration node and its children
 * @param {Object} node - Configuration node (may contain nested objects)
 * @returns {Array<string>} Array of all normalized URLs found
 */
export function extract_urls_recursive(node) {
  let urls = [];

  if (node && typeof node === "object") {
    // Extract URLs from this level
    urls.push(...extract_urls_from_object(node));

    // Recursively process nested structures
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) {
        for (const item of value) {
          urls.push(...extract_urls_recursive(item));
        }
      } else if (typeof value === "object") {
        urls.push(...extract_urls_recursive(value));
      }
    }
  }

  return urls;
}

// ============================================================================
// MENU VISIBILITY MANAGEMENT
// ============================================================================

/**
 * Sets the visibility property for each menu item based on accessible endpoints
 * Modifies the config object in place, adding a 'visible' property to each node
 * 
 * Logic:
 * - If node has URLs: visible if user can access ALL of them
 * - If node has no URLs: visible if any child is visible
 * - Parent nodes with no children and no URLs are visible by default
 * 
 * @param {Object} config - The application configuration object
 * @param {Set<string>} accessible_endpoints - Set of normalized accessible URLs
 */
export function set_menu_visibility(config, accessible_endpoints) {
  for (const key in config) {
    const node = config[key];

    // First, process children recursively (if any)
    if (node.children && typeof node.children === "object") {
      set_menu_visibility(node.children, accessible_endpoints);
    }

    // Collect all URLs for this node (already normalized)
    const urls = extract_urls_recursive(node);

    // Determine if this node is visible
    if (urls.length === 0) {
      // Node has no direct URLs: visible if any child is visible
      const anyChildVisible = node.children
        ? Object.values(node.children).some(child => child.visible)
        : false;
      
      // Parents with no URLs and no children are still visible
      node.visible = anyChildVisible || urls.length === 0;
    } else {
      // Node has URLs: visible if user can access ALL of them
      node.visible = urls.every(url => accessible_endpoints.has(normalize_url(url)));
    }
  }
}
