/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Centralized Configuration Module
 * 
 * All hardcoded values, URLs, timeouts, and magic numbers should be defined here.
 * Import this module wherever you need configuration values.
 * 
 * Usage:
 *   import { API_ENDPOINTS, TIMING, UI_CONFIG } from './config.js';
 */

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * Server API endpoints
 * Change these if your backend URLs change
 */
export const API_ENDPOINTS = {
  // Security/Access endpoints
  GET_ACCESSIBLE_ENDPOINTS: '/get_accessible_endpoints',
  
  // Task management endpoints
  GET_TASK_STATUS: '/get_task_status',
  CANCEL_TASK: '/cancel_task',
  
  // Add your other endpoints here as you discover them:
  // GET_CONFIGS: '/api/get_configs',
  // LOAD_CONFIG: '/api/load_config',
  // SUBMIT_FORM: '/api/submit',
  // etc.
};

// ============================================================================
// TIMING CONFIGURATION
// ============================================================================

/**
 * Timing values in milliseconds
 */
export const TIMING = {
  // Task polling interval (15 seconds)
  TASK_POLL_INTERVAL: 15000,
  
  // Tooltip auto-close delay (8 seconds)
  TOOLTIP_AUTO_CLOSE: 8000,
  
  // Tooltip hover auto-close (5 seconds)
  TOOLTIP_HOVER_CLOSE: 5000,
  
  // Tooltip animation delay (200ms)
  TOOLTIP_ANIMATION_DELAY: 200,
  
  // Spinner restart animation delay (300ms)
  SPINNER_PULSE_ANIMATION: 300,
  
  // Status area fade-in animation (500ms)
  STATUS_FADE_IN: 500,
};

// ============================================================================
// UI CONFIGURATION
// ============================================================================

/**
 * UI-related configuration
 */
export const UI_CONFIG = {
  // Element IDs (in case you want to change them)
  ELEMENTS: {
    PAGE_LOCK: 'pageLock',
    STATUS_AREA: 'status_area',
    STATUS_TEXTAREA: 'status_textarea',
    SPINNER: 'spinner',
    CANCEL_BUTTON: 'cancelButton',
    CLOSE_BUTTON: 'statusCloseButton',
    DROPDOWN_MENU: 'dropdown-menu',
    DROPDOWN_BTN: 'dropdown-btn',
    APP_CONTAINER: 'app',
  },
  
  // CSS classes
  CLASSES: {
    LOCKED: 'locked',
    SHOW: 'show',
    TOOLTIP_TOP: 'tooltip-top',
    TOOLTIP_TEXT: 'tooltip-text',
    PULSE: 'pulse',
    EXPANDED: 'expanded',
    HIDDEN: 'hidden',
    MENU_ITEM: 'menu-item',
    HAS_CHILDREN: 'has-children',
    SUBMENU_ITEM: 'submenu-item',
    MENU_LABEL: 'menu-label',
    MENU_DESC: 'menu-desc',
    DYNAMIC_TABLE: 'dynamic-table',
  },
  
  // Animations
  ANIMATIONS: {
    FADE_IN: 'fadeIn 0.5s forwards',
  },
  
  // Display settings
  DISPLAY: {
    BLOCK: 'block',
    INLINE_BLOCK: 'inline-block',
    NONE: 'none',
  },
  
  // Viewport offsets for tooltip positioning
  VIEWPORT_OFFSETS: {
    BOTTOM_MARGIN: 20,
    SCROLL_MARGIN: 50,
  },
};

// ============================================================================
// URL PROCESSING CONFIGURATION
// ============================================================================

/**
 * Configuration keys that represent URLs in your app config
 * Used for URL extraction and normalization
 */
export const URL_KEYS = new Set([
  'fetchUrl',
  'optionsUrl',
  'configListUrl',
  'configLoadUrl',
  'submitUrl',
  // Add any other config keys that contain URLs
]);

/**
 * URL normalization patterns
 */
export const URL_PATTERNS = {
  // Replace {param} or {value} with placeholder
  PARAM_PLACEHOLDER: /<\*>/g,
  PARAM_MATCH: /\{[^}]+\}/g,
  
  // Trim trailing slashes
  TRAILING_SLASH: /\/+$/,
};

// ============================================================================
// THEME CONFIGURATION
// ============================================================================

/**
 * Theme settings
 */
export const THEME_CONFIG = {
  STORAGE_KEY: 'theme',
  ATTRIBUTE: 'data-theme',
  VALUES: {
    LIGHT: 'light',
    DARK: 'dark',
  },
};

// ============================================================================
// META TAG NAMES
// ============================================================================

/**
 * Meta tag names used in the application
 */
export const META_TAGS = {
  GATEWAY_LOGOUT_URL: 'gateway_logout_url',
  // Add other meta tags as needed
};

// ============================================================================
// STATUS MESSAGES
// ============================================================================

/**
 * Standard status messages
 * Helps keep messaging consistent across the app
 */
export const STATUS_MESSAGES = {
  WORKING: 'Working...',
  DONE: 'Done!',
  CANCELLED: 'Cancelled!',
  CANCEL_REQUESTED: 'Cancellation requested...',
  LOADING: 'Loading...',
  ERROR_PREFIX: 'ERROR: ',
  
  // Error messages
  NO_TASK_ID: 'JS ERROR: Task cancel requested but no task ID.',
  UNKNOWN_ERROR: 'Unknown error',
  CANCEL_FAILED: 'Cancel failed',
  INVALID_JSON: 'Invalid JSON',
  GET_FAILED: 'GET failed',
  POST_FAILED: 'POST failed',
  
  // Logout warnings
  INVALID_LOGOUT_URL: 'Invalid gateway logout URL',
  LOGOUT_FAILED: 'Logout failed',
};

// ============================================================================
// RESPONSE STATUS PATTERNS
// ============================================================================

/**
 * Patterns for identifying error responses
 */
export const RESPONSE_PATTERNS = {
  ERROR_STATUS_PREFIX: 'error',
};

// ============================================================================
// DEFAULT VALUES
// ============================================================================

/**
 * Default values for various operations
 */
export const DEFAULTS = {
  // Default home page
  HOME_PAGE: 'Home',
  
  // Default scroll behavior
  SCROLL_BEHAVIOR: 'smooth',
  SCROLL_BLOCK: 'center',
  
  // Status message defaults
  IS_ERROR: false,
};

// ============================================================================
// TASK CONFIGURATION
// ============================================================================

/**
 * Task processing configuration
 */
export const TASK_CONFIG = {
  // If true: poll server for status updates (async mode)
  // If false: wait for POST response to complete (sync mode)
  // Both modes keep page locked and spinner showing
  ENABLE_ASYNC_POLLING: true,
};

// ============================================================================
// DEBUGGING / DEVELOPMENT
// ============================================================================

/**
 * Development and debugging flags
 * Set to true during development, false in production
 */
export const DEBUG = {
  // Log API requests/responses
  LOG_API_CALLS: false,
  
  // Log navigation events
  LOG_NAVIGATION: false,
  
  // Log task status updates
  LOG_TASK_STATUS: false,
  
  // Expose modules to window for console debugging
  EXPOSE_TO_WINDOW: false,
};

// ============================================================================
// BROWSER COMPATIBILITY
// ============================================================================

/**
 * Browser-specific settings
 */
export const BROWSER_CONFIG = {
  // Minimum supported browser versions
  MIN_VERSIONS: {
    CHROME: 61,
    FIREFOX: 60,
    SAFARI: 11,
    EDGE: 79,
  },
};

// ============================================================================
// VALIDATION RULES
// ============================================================================

/**
 * Validation rules and limits
 */
export const VALIDATION = {
  // Max file sizes, string lengths, etc.
  MAX_JSON_SIZE: 5 * 1024 * 1024, // 5MB
  
  // Add validation rules as needed
};

// ============================================================================
// EXPORT CONVENIENCE OBJECT
// ============================================================================

/**
 * All configuration in one object (if you prefer)
 * Usage: import CONFIG from './config.js';
 */
export default {
  API_ENDPOINTS,
  TIMING,
  UI_CONFIG,
  URL_KEYS,
  URL_PATTERNS,
  THEME_CONFIG,
  META_TAGS,
  STATUS_MESSAGES,
  RESPONSE_PATTERNS,
  DEFAULTS,
  TASK_CONFIG,
  DEBUG,
  BROWSER_CONFIG,
  VALIDATION,
};
