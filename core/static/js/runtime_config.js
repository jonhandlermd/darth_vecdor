/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Runtime Configuration Module
 * Handles configuration that can be modified at runtime
 */

import { DEBUG } from '../config.js';

/**
 * Configuration that can be overridden at runtime
 * Useful for environment-specific settings
 */
export class RuntimeConfig {
  constructor() {
    this._apiBaseUrl = '';
    this._debugMode = false;
  }
  
  /**
   * Set the API base URL (e.g., for different environments)
   * @param {string} url - Base URL for API endpoints
   */
  setApiBaseUrl(url) {
    this._apiBaseUrl = url.replace(/\/$/, ''); // Remove trailing slash
  }
  
  /**
   * Get the full API endpoint URL
   * @param {string} endpoint - Endpoint from API_ENDPOINTS
   * @returns {string} Full URL
   */
  getApiUrl(endpoint) {
    return this._apiBaseUrl + endpoint;
  }
  
  /**
   * Enable/disable debug mode
   * @param {boolean} enabled
   */
  setDebugMode(enabled) {
    this._debugMode = enabled;
    DEBUG.LOG_API_CALLS = enabled;
    DEBUG.LOG_NAVIGATION = enabled;
    DEBUG.LOG_TASK_STATUS = enabled;
  }
  
  /**
   * Check if debug mode is enabled
   * @returns {boolean}
   */
  isDebugMode() {
    return this._debugMode;
  }
}

// Singleton instance for runtime config
export const runtime = new RuntimeConfig();
