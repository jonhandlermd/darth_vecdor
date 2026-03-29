/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Form Field Utilities Module
 * Handles rendering of different form field types
 */

import { get_with_context } from '../core/utils.js';
import { TIMING, UI_CONFIG } from '../config.js';
import { set_tooltip_timer, clear_tooltip_timer, get_tooltip_timer } from '../ui/ui_helpers.js';

// ============================================================================
// FIELD TYPE RESOLUTION
// ============================================================================

/**
 * Determines the effective type of a field based on its configuration
 * Handles dynamic types, conditional types, and fallbacks
 * @param {Object} field - The field configuration object
 * @param {Object} mainForm - The main form state
 * @returns {string} The effective field type
 */
export function get_effective_type(field, main_form) {
  // Check for conditional types
  if (field.typeWhen) {
    const v = main_form[field.typeWhen.field];
    return field.typeWhen.cases?.[v] || field.type;
  }

  // Check for dynamic options that might change type
  if (field.dynamicOptions) {
    const controller = main_form[field.dynamicOptions.dependsOn];
    const variant = field.dynamicOptions.sources?.[controller];
    return variant?.type || field.type;
  }

  return field.type;
}

// ============================================================================
// OPTIONS RESOLUTION
// ============================================================================

/**
 * Gets the effective options for a field, considering dynamic sources
 * @param {Object} field - The field configuration
 * @param {Object} mainForm - The main form state
 * @param {Object} dynamicDropdowns - Cache of dynamically loaded options
 * @returns {Array} Array of options for the field
 */
export function get_effective_options(field, main_form, dynamic_dropdowns) {
  if (!field) return [];

  const controlling_value = field.dynamicOptions?.dependsOn
    ? main_form?.[field.dynamicOptions.dependsOn]
    : undefined;

  const sources = field.dynamicOptions?.sources || {};
  const variant = sources[controlling_value] || {};

  // Check dynamic_dropdowns for populated options
  const dynamic_set = dynamic_dropdowns?.[field.name];
  if (
    dynamic_set &&
    typeof dynamic_set === 'object' &&
    !Array.isArray(dynamic_set) &&
    Array.isArray(dynamic_set[controlling_value])
  ) {
    return dynamic_set[controlling_value];
  }

  // Fallback to static options
  if (variant?.options) return variant.options;

  // Last fallback
  return dynamic_dropdowns?.[field.name] || field.options || [];
}

// ============================================================================
// FIELD VISIBILITY
// ============================================================================

/**
 * Determines if a field should be shown based on conditional logic
 * @param {Object} field - The field configuration
 * @param {Object} mainForm - The main form state
 * @returns {boolean} Whether the field should be visible
 */
export function should_show_field(field, main_form) {
  if (!field.showWhen) return true;

  const { field: dependency, value, values } = field.showWhen;
  const actual = main_form[dependency];

  if (value !== undefined) {
    return actual === value;
  } else if (Array.isArray(values)) {
    return values.includes(actual);
  }

  return true;
}

// ============================================================================
// TOOLTIP RENDERING
// ============================================================================

/**
 * Renders a help tooltip button with the given help text
 * @param {string} help_text - The help text to display
 * @param {Function} h - Preact createElement function
 * @returns {Object} Preact virtual DOM element
 */
export function render_help_tooltip(help_text, h) {
  return h('span', {
    style: `
      background: var(--accent-color);
      color: white;
      border-radius: 50%;
      padding: 0.2em 0.5em;
      font-size: 0.8em;
      cursor: pointer;
      user-select: none;
    `,
    onClick: e => {
      e.stopPropagation();
      e.target.classList.add('pulse');
      setTimeout(() => e.target.classList.remove('pulse'), 300);
      
      const tooltip = e.target.parentNode.querySelector(`.${UI_CONFIG.CLASSES.TOOLTIP_TEXT}`);
      if (tooltip) {
        const alreadyVisible = tooltip.classList.contains(UI_CONFIG.CLASSES.SHOW);
        
        // Close all tooltips first
        document.querySelectorAll(`.${UI_CONFIG.CLASSES.TOOLTIP_TEXT}.${UI_CONFIG.CLASSES.SHOW}`).forEach(tip => {
          tip.classList.remove(UI_CONFIG.CLASSES.SHOW);
          tip.classList.remove(UI_CONFIG.CLASSES.TOOLTIP_TOP);
        });
        
        if (!alreadyVisible) {
          tooltip.classList.add(UI_CONFIG.CLASSES.SHOW);
          
          // Auto-close after configured timeout
          clear_tooltip_timer();
          set_tooltip_timer(setTimeout(() => {
            tooltip.classList.remove(UI_CONFIG.CLASSES.SHOW);
            tooltip.classList.remove(UI_CONFIG.CLASSES.TOOLTIP_TOP);
          }, TIMING.TOOLTIP_AUTO_CLOSE));

          // Position tooltip if it would go off screen
          const rect = tooltip.getBoundingClientRect();
          if (rect.bottom > window.innerHeight - UI_CONFIG.VIEWPORT_OFFSETS.BOTTOM_MARGIN) {
            tooltip.classList.add(UI_CONFIG.CLASSES.TOOLTIP_TOP);
          }

          // Scroll parent into view if needed
          const tooltipParent = e.target.closest('div');
          if (tooltipParent) {
            const parentRect = tooltipParent.getBoundingClientRect();
            if (parentRect.bottom > window.innerHeight - UI_CONFIG.VIEWPORT_OFFSETS.SCROLL_MARGIN || parentRect.top < 0) {
              tooltipParent.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          }
        }
      }
    }
  }, '?');
}

/**
 * Renders the tooltip text element
 * @param {string} help_text - The help text to display
 * @param {Function} h - Preact createElement function
 * @returns {Object} Preact virtual DOM element
 */
export function render_tooltip_text(help_text, h) {
  return h('div', {
    class: UI_CONFIG.CLASSES.TOOLTIP_TEXT,
    onMouseEnter: () => {
      const timer = get_tooltip_timer();
      if (timer) {
        clear_tooltip_timer();
      }
    },
    onMouseLeave: e => {
      if (!get_tooltip_timer()) {
        set_tooltip_timer(setTimeout(() => {
          e.target.classList.remove(UI_CONFIG.CLASSES.SHOW);
          e.target.classList.remove(UI_CONFIG.CLASSES.TOOLTIP_TOP);
        }, TIMING.TOOLTIP_HOVER_CLOSE));
      }
    }
  }, help_text);
}

// ============================================================================
// FIELD LABEL RENDERING
// ============================================================================

/**
 * Renders the field label with optional help tooltip
 * @param {Object} field - The field configuration
 * @param {Function} h - Preact createElement function
 * @returns {Object} Preact virtual DOM element
 */
export function render_field_label(field, h) {
  return h('div', { style: 'display: flex; align-items: center; gap: 0.5rem;' },
    h('span', {}, field.label),
    field.help && render_help_tooltip(field.help, h),
    field.help && render_tooltip_text(field.help, h)
  );
}
