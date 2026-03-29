/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Core Utilities Module
 * Provides foundational functions for API communication, URL handling, and common operations
 */

import { STATUS_MESSAGES, RESPONSE_PATTERNS, META_TAGS } from '../config.js';

// ============================================================================
// META & CONFIGURATION HELPERS
// ============================================================================

/**
 * Retrieves content from a meta tag by name
 * @param {string} name - The name attribute of the meta tag
 * @returns {string|null} The content attribute value or null
 */
export function get_meta(name) {
  const el = document.querySelector(`meta[name="${name}"]`);
  return el ? el.content : null;
}

// ============================================================================
// URL NORMALIZATION
// ============================================================================

/**
 * Normalizes URL by replacing parameters and removing trailing slashes
 * @param {string} url - The URL to normalize
 * @returns {string} Normalized URL
 */
export function normalize_url(url) {
  return url
    .replace(/\{[^}]+\}/g, '<*>')  // {value} → <*>
    .replace(/\/+$/, '');          // trim trailing slash
}

// ============================================================================
// JSON RESPONSE MANAGEMENT
// ============================================================================

/**
 * Processes and validates JSON responses from the server
 * @param {Object} json - The JSON response object
 * @returns {*} The parsed data from the response
 * @throws {Error} If the response is invalid or contains an error status
 */
export function manage_json_resp(json) {
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
// HTTP REQUEST HELPERS
// ============================================================================

/**
 * Performs a GET request with context payload
 * Automatically stringifies payload and handles JSON parsing
 * @param {string} baseUrl - The endpoint URL
 * @param {Object} orig_payload - The payload to send (will be stringified)
 * @returns {Promise<*>} Parsed response data
 * @throws {Error} If the request fails
 */
export async function get_with_context(base_url, orig_payload = {}) {
  // Stringify the payload for transmission
  const main_payload = { data: JSON.stringify(orig_payload) };
  const query = new URLSearchParams(main_payload).toString();
  const full_url = `${base_url}?${query}`;

  try {
    const res = await fetch(full_url);
    const json = await res.json();
    return manage_json_resp(json);
  } catch (err) {
    throw new Error(`${STATUS_MESSAGES.GET_FAILED}: ${err.message}`);
  }
}

/**
 * Performs a POST request with context payload
 * Automatically stringifies payload and handles JSON parsing
 * @param {string} url - The endpoint URL
 * @param {Object} orig_payload - The payload to send (will be stringified)
 * @returns {Promise<*>} Parsed response data
 * @throws {Error} If the request fails
 */
export async function post_with_context(url, orig_payload = {}) {
  // Stringify the payload for transmission
  const main_payload = { data: JSON.stringify(orig_payload) };

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(main_payload)
    });

    const json = await res.json();
    return manage_json_resp(json);
  } catch (err) {
    throw new Error(`${STATUS_MESSAGES.POST_FAILED}: ${err.message}`);
  }
}

// ============================================================================
// LOGOUT FUNCTIONALITY
// ============================================================================

/**
 * Handles user logout by clearing storage and redirecting
 * Checks for gateway logout URL in meta tags
 */
export function logout() {
  try {
    // Clear all local/session storage for this origin
    sessionStorage.clear();
    localStorage.clear();

    const gateway_logout_url = get_meta(META_TAGS.GATEWAY_LOGOUT_URL);

    // Optional: redirect to gateway logout URL if configured
    if (gateway_logout_url) {
      try {
        const url = new URL(gateway_logout_url);
        window.location.href = url.href;
      } catch (err) {
        console.warn(`${STATUS_MESSAGES.INVALID_LOGOUT_URL}:`, gateway_logout_url);
      }
    } else {
      // Otherwise, try to close window
      window.close();
    }
  } catch (err) {
    console.error(`${STATUS_MESSAGES.LOGOUT_FAILED}:`, err);
  }
}
