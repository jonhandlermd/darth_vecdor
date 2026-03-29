/*
 * Copyright (c) 2025 Keylog Solutions LLC
 * Licensed under the Apache License, Version 2.0
 */

/**
 * Main Form Component
 * Handles dynamic form rendering with main fields and repeating subforms
 */

import { get_with_context, post_with_context } from '../core/utils.js';
import { 
  lock_page, 
  unlock_page, 
  set_waiting, 
  update_status,
  set_task_id,
  poll_status
} from '../core/task_manager.js';
import { 
  get_effective_type, 
  get_effective_options, 
  should_show_field,
  render_field_label 
} from './field_utils.js';
import { 
  TASK_CONFIG, 
  STATUS_MESSAGES,
  UI_CONFIG 
} from '../config.js';
import { get_button_style } from '../ui/ui_helpers.js';

/**
 * Main application form component
 * Renders forms based on configuration with main fields and optional subforms
 */
export function AppForm({ config }) {
  const { h } = preact;
  const { useState, useEffect } = preactHooks;

  const main_form_config = config.mainFields;
  const subform_config = config.subformFields || [];

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  const [main_form, set_main_form] = useState(
    Object.fromEntries(main_form_config.map(f => [f.name, f.default || '']))
  );
  
  const [subforms, set_subforms] = useState([]);
  const [collapsed_index, set_collapsed_index] = useState([]);
  const [main_collapsed, set_main_collapsed] = useState(false);
  const [form_key, set_form_key] = useState(0);
  const [dynamic_dropdowns, set_dynamic_dropdowns] = useState({});

  // For form input from file
  let file_input_el = null;

  // Configuration selector state
  const [config_options, set_config_options] = useState([]);
  const [selected_config, set_selected_config] = useState('');

  // ============================================================================
  // FORM LOADING/EXPORTING
  // ============================================================================

  /**
   * Loads form data from JSON object
   */
  const load_form_from_json = (payload) => {
    if (!payload) return;

    const { rels = [], ...rest } = payload;

    // Update main form
    set_main_form(prev => {
      const new_state = {};
      main_form_config.forEach(f => {
        new_state[f.name] = rest[f.name] ?? '';
      });
      return new_state;
    });

    // Update subforms
    if (!Array.isArray(subform_config)) {
      console.warn("subform_config is not available or not an array:", subform_config);
      return;
    }

    const new_subforms = rels.map(rel => {
      const form = {};
      subform_config.forEach(f => {
        form[f.name] = rel[f.name] ?? '';
      });
      return form;
    });

    set_subforms(new_subforms);
    set_collapsed_index([]);
    set_main_collapsed(false);
  };

  /**
   * Exports current form state to JSON file
   */
  const export_form_to_json = () => {
    // Build filename
    const form_title = (config.formTitle && String(config.formTitle).trim()) || 'form';
    const base_name = (main_form?.base_name && String(main_form.base_name).trim()) ||
                      (main_form?.name && String(main_form.name).trim()) ||
                      'unnamed';
    const version = (main_form?.ctg_version && String(main_form.ctg_version).trim()) ||
                    (main_form?.version && String(main_form.version).trim()) ||
                    null;

    // Compact timestamp YYYYMMDD_HHMMSS
    const d = new Date();
    const timestamp = d.getFullYear().toString() +
      String(d.getMonth() + 1).padStart(2, '0') +
      String(d.getDate()).padStart(2, '0') +
      '_' +
      String(d.getHours()).padStart(2, '0') +
      String(d.getMinutes()).padStart(2, '0') +
      String(d.getSeconds()).padStart(2, '0');

    let filename = `${form_title}__${base_name}`;
    if (version) filename += `__v${version}`;
    filename += `__${timestamp}`;

    // Sanitize
    const safe_name = filename
      .replace(/[^\w\d\-_.]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '')
      .toLowerCase();

    // Prompt user
    const user_filename = window.prompt('Edit export filename if desired:', safe_name);
    if (!user_filename) return;

    // Polish user input
    const final_name = user_filename
      .trim()
      .replace(/[^\w\d\-_.]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '')
      .toLowerCase();

    // Build payload
    const payload = {
      ...main_form,
      rels: subforms,
      formKey: config.formKey,
      exportedAt: new Date().toISOString()
    };

    // Create blob and download
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${final_name}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /**
   * Imports form data from JSON file
   */
  const import_form_from_json = (file, file_input_el) => {
    if (!file) return;

    const reader = new FileReader();
    reader.onload = e => {
      let parsed;
      try {
        parsed = JSON.parse(e.target.result);
      } catch (err) {
        alert('Invalid JSON file');
        console.error(err);
        if (file_input_el) file_input_el.value = '';
        return;
      }

      // Check formKey
      if (parsed.formKey !== config.formKey) {
        alert(
          `CANNOT IMPORT YOUR FILE.\n` +
          `=====================\n` +
          `CAUSE OF THE PROBLEM:\n` +
          `The currently showing form is: "${config.formTitle}"\n` +
          `However, the import file is intended for a different form (formKey: "${parsed.formKey}").\n` +
          `=====================\n` +
          `SOLUTION:\n` +
          `1) Go to the menu.\n` +
          `2) Select the correct form and retry the import.\n` +
          `=====================`
        );
        if (file_input_el) file_input_el.value = '';
        return;
      }

      // Load the form data
      load_form_from_json(parsed);

      // Reset file input
      if (file_input_el) file_input_el.value = '';
    };

    reader.readAsText(file);
  };

  // ============================================================================
  // CONFIGURATION SELECTOR
  // ============================================================================

  useEffect(() => {
    if (!config || !config.configListUrl) return;

    get_with_context(config.configListUrl)
      .then(list => {
        if (!Array.isArray(list)) {
          alert("Expected array from configListUrl");
          return;
        }
        set_config_options(list.map(item =>
          typeof item === 'string'
            ? { id: item, label: item }
            : { id: item.id, label: item.label ?? item.id }
        ));
      })
      .catch(err => alert("Config list error: " + err.message));
  }, [config]);

  // ============================================================================
  // DYNAMIC DROPDOWN LOADING
  // ============================================================================

  useEffect(() => {
    const fields = [...main_form_config, ...subform_config];
    fields.forEach(field => {
      if (field.dynamicOptions) {
        const controlling_value = main_form[field.dynamicOptions.dependsOn];
        const sources = field.dynamicOptions.sources || {};
        const variant = sources[controlling_value] || {};

        const options_url =
          variant.optionsUrl ||
          (field.dynamicOptions.optionsUrlTemplate
            ? field.dynamicOptions.optionsUrlTemplate.replace('{value}', encodeURIComponent(controlling_value))
            : null);

        if (options_url) {
          const already_loaded = dynamic_dropdowns[field.name]?.[controlling_value];
          if (!already_loaded) {
            get_with_context(options_url)
              .then(options => {
                const cleaned = Array.isArray(options) ? options : Object.values(options);
                set_dynamic_dropdowns(prev => ({
                  ...prev,
                  [field.name]: {
                    ...(prev[field.name] || {}),
                    [controlling_value]: cleaned
                  }
                }));
              })
              .catch(err =>
                console.warn(`Lazy load for '${field.name}' → ${controlling_value} failed:`, err.message)
              );
          }
        }
      }
      // Static dropdown
      else if (field.optionsUrl) {
        if (!dynamic_dropdowns[field.name]) {
          get_with_context(field.optionsUrl)
            .then(options => {
              const cleaned = Array.isArray(options) ? options : Object.values(options);
              set_dynamic_dropdowns(prev => ({ ...prev, [field.name]: cleaned }));
            })
            .catch(err => console.warn(`Dropdown '${field.name}' failed:`, err.message));
        }
      }
    });
  }, [main_form]);

  // ============================================================================
  // FORM STATE UPDATES
  // ============================================================================

  const update_main = (name, value) => {
    set_main_form(prev => {
      const updated = { ...prev, [name]: value };

      // Auto-clear dependent fields
      for (const field of main_form_config) {
        if (
          field.dynamicOptions &&
          field.dynamicOptions.dependsOn === name &&
          prev[field.name] !== undefined
        ) {
          updated[field.name] = '';
        }
      }

      return updated;
    });
  };

  const update_subform = (i, name, value) => {
    const updated = [...subforms];
    updated[i][name] = value;
    set_subforms(updated);
  };

  const add_subform = () => {
    const new_form = Object.fromEntries(subform_config.map(f => [f.name, f.default || '']));
    set_subforms(prev => [...prev, new_form]);
    set_collapsed_index([...Array(subforms.length).keys()]);
    set_main_collapsed(true);
  };

  const delete_subform = (i) => {
    set_subforms(prev => prev.filter((_, idx) => idx !== i));
    set_collapsed_index(prev =>
      prev
        .filter(idx => idx !== i)
        .map(idx => (idx > i ? idx - 1 : idx))
    );
  };

  const move_subform = (i, direction) => {
    const updated = [...subforms];
    const [moved] = updated.splice(i, 1);
    updated.splice(i + direction, 0, moved);
    set_subforms(updated);
  };

  const toggle_collapse = (i) => {
    set_collapsed_index(prev => prev.includes(i)
      ? prev.filter(idx => idx !== i)
      : [...prev, i]);
  };

  const toggle_main_collapse = () => set_main_collapsed(!main_collapsed);
  const collapse_all = () => set_collapsed_index(subforms.map((_, i) => i));
  const expand_all = () => set_collapsed_index([]);

  // ============================================================================
  // FORM SUBMISSION
  // ============================================================================

  const handle_jsonned_form_submit = async (e) => {
    e.preventDefault();
    const raw_payload = { ...main_form, rels: subforms };
    const payload = { tjson: JSON.stringify(raw_payload) };

    try {
      lock_page();
      set_waiting(true);
      update_status(STATUS_MESSAGES.WORKING);

      const result = await post_with_context(config.submitUrl, payload);

      if (result?.task_id && TASK_CONFIG.ENABLE_ASYNC_POLLING) {
        // Async mode: start polling
        set_task_id(result.task_id);
        poll_status();
      } else {
        // Sync mode: already done
        set_waiting(false);
        unlock_page();
        update_status(STATUS_MESSAGES.DONE);
      }

    } catch (err) {
      set_waiting(false);
      unlock_page();
      update_status(`Submit failed: ${err.message}`, true);
      alert("Had an error! " + err.message);
    }
  };

  // ============================================================================
  // FIELD RENDERING
  // ============================================================================

  const render_field = (f, value, on_change) => {
    try {
      const effective_type = get_effective_type(f, main_form);
      const raw_options = get_effective_options(f, main_form, dynamic_dropdowns);
      const dropdown_options = Array.isArray(raw_options)
        ? raw_options.filter(opt => {
            return (
              opt != null &&
              (typeof opt === 'string' ||
               typeof opt === 'number' ||
               (typeof opt === 'object' && 'label' in opt && 'value' in opt))
            );
          })
        : [];

      return h('div', {
        style: 'display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; position: relative;'
      },
        // Field label and help tooltip
        render_field_label(f, h),

        // Render field based on type
        effective_type === 'textarea' ?
          h('textarea', {
            name: f.name,
            value: value || '',
            onInput: e => on_change(f.name, e.target.value)
          }) :

        effective_type === 'plaintext' ?
          h('div', { class: 'static-text' }, f.text || '') :

        effective_type === 'dropdown' ?
          h('select', {
            name: f.name,
            value: value != null ? String(value) : '',
            onInput: e => on_change(f.name, e.target.value)
          },
            dropdown_options.map((opt, i) => {
              if (opt && typeof opt === 'object' && 'label' in opt && 'value' in opt) {
                return h('option', { key: i, value: String(opt.value) }, String(opt.label));
              }
              return h('option', { key: i, value: String(opt) }, String(opt));
            })
          ) :

        effective_type === 'checkbox' ?
          h('input', {
            type: 'checkbox',
            name: f.name,
            checked: value === true,
            onInput: e => on_change(f.name, e.target.checked)
          }) :

        effective_type === 'radio' ?
          h('div', { style: 'display: flex; gap: 1rem;' },
            (f.options || []).map(opt =>
              h('label', { style: 'display: flex; align-items: center; gap: 0.3rem;' },
                h('input', {
                  type: 'radio',
                  name: f.name,
                  value: opt,
                  checked: value === opt,
                  onInput: e => on_change(f.name, e.target.value)
                }),
                opt
              )
            )
          ) :

        effective_type === 'multicheckbox' ?
          h('div', { class: 'multicheckbox-group' },
            (f.options || []).map(opt =>
              h('label', { class: 'multicheckbox-item' },
                h('input', {
                  type: 'checkbox',
                  value: opt,
                  checked: Array.isArray(value) && value.includes(opt),
                  onInput: e => {
                    const is_checked = e.target.checked;
                    const new_value = Array.isArray(value) ? [...value] : [];
                    if (is_checked && !new_value.includes(opt)) {
                      new_value.push(opt);
                    } else if (!is_checked && new_value.includes(opt)) {
                      new_value.splice(new_value.indexOf(opt), 1);
                    }
                    on_change(f.name, new_value);
                  }
                }),
                opt
              )
            )
          ) :

        effective_type === 'accumulator' ?
          render_accumulator(f, value, on_change) :

        // Default: text input
        h('input', {
          type: 'text',
          name: f.name,
          value: value,
          onInput: e => on_change(f.name, e.target.value)
        })
      );

    } catch (err) {
      console.error(`Error rendering field '${f.name}':`, err);
      return h('div', {}, `⚠️ Error rendering ${f.label || f.name}`);
    }
  };

  /**
   * Renders accumulator (dual-list) field
   */
  const render_accumulator = (f, value, on_change) => {
    const raw_options = get_effective_options(f, main_form, dynamic_dropdowns);

    if (!Array.isArray(raw_options) || raw_options.length === 0) {
      return h('div', { class: 'accumulator-wrapper empty' }, 'Loading options...');
    }

    const selected = value || [];
    const available = raw_options.filter(opt => !selected.includes(opt));

    const [selected_available, set_selected_available] = useState(null);
    const [selected_chosen, set_selected_chosen] = useState(null);

    const move_to_selected = () => {
      if (selected_available != null) {
        on_change(f.name, [...selected, selected_available]);
        set_selected_available(null);
      }
    };

    const move_all_to_selected = () => {
      on_change(f.name, [...selected, ...available]);
      set_selected_available(null);
    };

    const remove_from_selected = () => {
      if (selected_chosen != null) {
        on_change(f.name, selected.filter(i => i !== selected_chosen));
        set_selected_chosen(null);
      }
    };

    const remove_all_from_selected = () => {
      on_change(f.name, []);
      set_selected_chosen(null);
    };

    const render_option = (opt, is_selected, on_click) =>
      h('div', {
        class: `accumulator-option${is_selected ? ' selected' : ''}`,
        onClick: () => on_click(opt),
        title: String(opt) || '(empty)'
      }, String(opt) || '(empty)');

    return h('div', { class: 'accumulator-wrapper horizontal' }, [
      h('div', { class: 'accumulator-column' }, [
        h('div', { class: 'accumulator-title' }, 'Available'),
        h('div', { class: 'accumulator-listbox' }, available.map(opt =>
          render_option(opt, selected_available === opt, set_selected_available)
        ))
      ]),
      h('div', { class: 'accumulator-actions' }, [
        h('button', {
          type: 'button',
          class: 'accumulator-button',
          onClick: move_to_selected,
          disabled: selected_available == null
        }, 'Add →'),
        h('button', {
          type: 'button',
          class: 'accumulator-button',
          onClick: move_all_to_selected,
          disabled: available.length === 0
        }, 'Add All →'),
        h('button', {
          type: 'button',
          class: 'accumulator-button',
          onClick: remove_from_selected,
          disabled: selected_chosen == null
        }, '← Remove'),
        h('button', {
          type: 'button',
          class: 'accumulator-button',
          onClick: remove_all_from_selected,
          disabled: selected.length === 0
        }, '← Remove All')
      ]),
      h('div', { class: 'accumulator-column' }, [
        h('div', { class: 'accumulator-title' }, 'Selected'),
        h('div', { class: 'accumulator-listbox' }, selected.map(opt =>
          render_option(opt, selected_chosen === opt, set_selected_chosen)
        ))
      ])
    ]);
  };

  // ============================================================================
  // CONFIG SELECTOR RENDERING
  // ============================================================================

  const render_config_selector_dropdown = () => {
    return h('div', { class: 'config-selector-wrapper' }, [
      h('div', { class: 'config-selector-box' },
        h('label', {}, 'Database-Stored Configurations: Select to Load'),
        h('select', {
          value: selected_config,
          onInput: async e => {
            const selected = e.target.value;
            set_selected_config(selected);
            if (selected && config?.configLoadUrl) {
              try {
                const payload = await get_with_context(
                  config.configLoadUrl,
                  { id: selected }
                );
                load_form_from_json(payload);
              } catch (err) {
                console.error('Failed to load config payload:', err);
              }
            }
          }
        },
          h('option', { value: '' }, '-- Choose --'),
          config_options.map(opt =>
            h('option', { value: opt.id }, opt.label)
          )
        )
      ),

      h('div', { class: 'config-selector-box' },
        h('label', {}, 'File-Stored Configurations: Import and Export'),
        h('i', { style: 'font-weight: normal;' },
          'NOTE: Exports save on-screen form content to a file, ',
          'Imports will import data only to the form on the screen, ',
          'not to the database (unless you import and then click the Submit button to run the function).'
        ),
        h('div', { style: 'display: flex; gap: 0.5rem; margin-bottom: 0.25rem;' },
          h('button', {
            type: 'button',
            class: 'control-btn',
            style: 'flex: 1;',
            onClick: () => {
              if (!file_input_el) {
                console.error('File input not mounted');
                return;
              }
              file_input_el.click();
            }
          }, 'Import Configs from File'),

          h('button', {
            type: 'button',
            class: 'control-btn',
            style: 'flex: 1;',
            onClick: export_form_to_json
          }, 'Export Configs to File')
        )
      )
    ]);
  };

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  const include_config_selector = !!config.configListUrl;

  const config_selector_field = {
    name: '__config_selector__',
    label: 'Select Configuration',
    type: 'custom'
  };

  const all_main_fields = include_config_selector
    ? [config_selector_field, ...main_form_config]
    : main_form_config;

  return h('form', { onSubmit: handle_jsonned_form_submit, key: form_key },

    // File input for importing
    h('input', {
      type: 'file',
      accept: 'application/json',
      style: 'display: none;',
      ref: el => { file_input_el = el },
      onChange: e => {
        import_form_from_json(e.target.files[0], file_input_el);
        e.target.value = '';
      }
    }),

    // Main form section
    h('div', { class: 'subform', style: 'border: 2px solid var(--accent-color);' },
      h('div', { class: 'subform-header' },
        h('div', { class: 'subform-title' }, config.formTitle || 'Form'),
        h('div', { class: 'subform-controls' },
          h('button', {
            type: 'button',
            class: 'control-btn small',
            onClick: toggle_main_collapse
          }, main_collapsed ? 'Expand' : 'Collapse')
        )
      ),
      h('div', { class: main_collapsed ? 'collapsed-fields' : '' },
        all_main_fields
          .filter(f => should_show_field(f, main_form))
          .map(f =>
            f.name === '__config_selector__'
              ? render_config_selector_dropdown()
              : render_field(f, main_form[f.name], update_main)
          )
      )
    ),

    // Subforms section
    subform_config.length > 0 && [
      h('h2', null, 'Relationships'),
      h('div', { style: 'display: flex; gap: 1rem; margin-bottom: 1rem;' },
        h('button', { type: 'button', class: 'add-btn', onClick: add_subform }, 'Add Relationship'),
        h('button', {
          type: 'button',
          class: 'control-btn',
          onClick: collapse_all,
          style: get_button_style(subforms.length === 0),
          disabled: subforms.length === 0
        }, 'Collapse All'),
        h('button', {
          type: 'button',
          class: 'control-btn',
          onClick: expand_all,
          style: get_button_style(subforms.length === 0),
          disabled: subforms.length === 0
        }, 'Expand All')
      ),
      subforms.map((sf, i) =>
        h('div', { class: 'subform', key: i },
          h('div', { class: 'subform-header' },
            h('div', { class: 'subform-title' },
              typeof config.subformTitle === 'function'
                ? config.subformTitle(i, sf)
                : `Subform #${i + 1}`
            ),
            h('div', { class: 'subform-controls' },
              h('button', {
                type: 'button',
                class: 'control-btn small',
                style: get_button_style(i === 0 || subforms.length < 2),
                onClick: () => move_subform(i, -1),
                disabled: i === 0 || subforms.length < 2
              }, '↑'),
              h('button', {
                type: 'button',
                class: 'control-btn small',
                style: get_button_style(i === subforms.length - 1 || subforms.length < 2),
                onClick: () => move_subform(i, 1),
                disabled: i === subforms.length - 1 || subforms.length < 2
              }, '↓'),
              h('button', {
                type: 'button',
                class: 'control-btn small',
                style: get_button_style(subforms.length === 0),
                onClick: () => toggle_collapse(i),
                disabled: subforms.length === 0
              }, collapsed_index.includes(i) ? 'Expand' : 'Collapse'),
              h('button', {
                type: 'button',
                class: 'control-btn small danger',
                style: get_button_style(false),
                onClick: () => delete_subform(i)
              }, 'Delete')
            )
          ),
          h('div', { class: collapsed_index.includes(i) ? 'collapsed-fields' : '' },
            subform_config
              .filter(f => should_show_field(f, main_form))
              .map(f => render_field(f, sf[f.name], (name, val) => update_subform(i, name, val)))
          )
        )
      )
    ],

    // Submit button
    h('div', { style: 'display: flex; gap: 1rem; justify-content: flex-end' },
      h('button', { type: 'submit', class: 'submit-btn' }, 'Submit')
    )
  );
}
