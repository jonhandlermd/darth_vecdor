/*
  ~ Copyright (c) 2025 Keylog Solutions LLC
  ~
  ~ ATTRIBUTION NOTICE: This work was conceived and created by Jonathan A. Handler. Large language model(s) and/or many other resources were used to help create this work.
  ~
  ~ Licensed under the Apache License, Version 2.0 (the "License");
  ~ you may not use this file except in compliance with the License.
  ~ You may obtain a copy of the License at
  ~
  ~     http://www.apache.org/licenses/LICENSE-2.0
  ~
  ~ Unless required by applicable law or agreed to in writing, software
  ~ distributed under the License is distributed on an "AS IS" BASIS,
  ~ WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ~ See the License for the specific language governing permissions and
  ~ limitations under the License.
*/

// Javascript for Darth Vecdor

///////// START PROGRESS FUNCTIONS ///////
let taskId = null;

///////// KEEP TRACK OF CURRENT PAGE INFO //////////
let current_page_name = null;

function lockPage() {
  document.getElementById('pageLock').classList.add('locked');
}

function unlockPage() {
  document.getElementById('pageLock').classList.remove('locked');
}


function showCloseButton() {
  const btn = document.getElementById("statusCloseButton");
  btn.style.display = "inline-block";
  btn.style.opacity = "1";
}

function hideCloseButton() {
  const btn = document.getElementById("statusCloseButton");
  btn.style.display = "none";
  btn.style.opacity = "0";
}

function showCancelButton() {
  const btn = document.getElementById("cancelButton");
  btn.style.display = "inline-block";
  btn.style.opacity = "1";
}

function hideCancelButton() {
  const btn = document.getElementById("cancelButton");
  btn.style.display = "none";
  btn.style.opacity = "0";
}


function setWaiting(isWaiting) {
  const status_area = document.getElementById('status_area');
  const spinner = document.getElementById('spinner');
  const cancelBtn = document.getElementById('cancelButton');
  const closeBtn = document.getElementById('statusCloseButton');

  if (isWaiting) {
    lockPage();
    status_area.style.animation = "fadeIn 0.5s forwards";
    status_area.style.display = 'block';

    // 🔄 always restart spinner
    spinner.style.display = 'inline-block';
    const new_spinner = spinner.cloneNode(true);
    spinner.parentNode.replaceChild(new_spinner, spinner);

    cancelBtn.style.display = "inline-block";
    cancelBtn.style.opacity = "1";
    closeBtn.style.display = "none";
    closeBtn.style.opacity = "0";

  } else {
    // finished state
    const current_spinner = document.getElementById('spinner');
    if (current_spinner) {
      current_spinner.style.display = 'none';
    }

    cancelBtn.style.display = "none";
    cancelBtn.style.opacity = "0";
    closeBtn.style.display = "inline-block";
    closeBtn.style.opacity = "1";
  }
}


function pollStatus() {
  if (!taskId) return;

  getWithContext('/get_task_status', { task_id: taskId }).then(
    data => {
        updateStatus(data.status);

    if (!data.done) {
      setTimeout(pollStatus, 15000);
    } else {
      setWaiting(false);
      // unlockPage();
      updateStatus("Done with status : " + data.status);
      taskId = null;
    }
  }).catch(err => {
    setWaiting(false);
    // unlockPage();
    updateStatus("Error occurred: " + err.message, true);
  });
}


function cancelTask() {
  if (!taskId) return;

  postWithContext('/cancel_task', { task_id: taskId }).then(data => {
    if (data.cancelled) {
      // unlockPage();
      setWaiting(false);
      updateStatus("Cancelled!");
    }
  }).catch(err => {
    // unlockPage();
    setWaiting(false);
    updateStatus("Cancel failed: " + err.message, true);
  });
}

function updateStatus(message, isError = false) {
  const status = document.getElementById('status_textarea');
  /*
  status.innerText = isError
    ? `<span class='error-text'>${message}</span>`
    : message;
  */
    status.value = isError
    ? `ERROR: ${message}`
    : message;
}

//////// START Helper utilities /////////

async function getWithContext(baseUrl, orig_payload = {}) {
  // We JSON stringify the main payload.
  // It will be DOUBLE stringified if it's a form submission where we are submitting the form itself as a JSON string.
  // It will be further stringified as URL search params.
  const main_payload = { data: JSON.stringify(orig_payload) };
  const query = new URLSearchParams(main_payload).toString();
  const fullUrl = `${baseUrl}?${query}`;

  try {
    const res = await fetch(fullUrl);
    const json = await res.json();

    if (!json || typeof json !== 'object') {
      throw new Error("Invalid JSON");
    }

    if (json.status?.toLowerCase().startsWith("error")) {
      throw new Error(json.status);
    }

    const data = typeof json.data === 'string' ? JSON.parse(json.data) : json.data;
    return data;
  } catch (err) {
    throw new Error("GET failed: " + err.message);
  }
}

async function postWithContext(url, orig_payload = {}) {
  // We JSON stringify the main payload. This means it will be double stringified after stringification to send to server.
  // It will be TRIPLE stringified if it's a form submission where we are submitting the form itself as a JSON string.
  const main_payload = { data: JSON.stringify(orig_payload) };

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(main_payload)
    });

    const json = await res.json();

    if (!json || typeof json !== 'object') {
      throw new Error("Invalid JSON response");
    }

    if (json.status?.toLowerCase().startsWith("error")) {
      throw new Error(json.status);
    }

    const data = typeof json.data === 'string' ? JSON.parse(json.data) : json.data;
    return data;
  } catch (err) {
    throw new Error("POST failed: " + err.message);
  }
}

//////// END Helper utilities /////////



/////////////////// BEGIN SCRIPT FOR PAGE CONTENT AND BEHAVIORS EXCLUDING WEB SOCKET INTERACTIONS //////////////////////
    let tooltipAutoCloseTimer = null;

    const { h, render } = preact;
    const { useState } = preactHooks;


/////////////////// BEGIN APPLICATION CONFIGURATIONS/CONTENT //////////////////////
    const appConfig = {
    "Home": {
        type: "page",
        content: `
<h1>Welcome to Darth Vecdor</h1>
<p><B>Use is entirely at your own risk. Read this entire page, all the way to the bottom, for some of the important caveats, and other critical information.</B></p>
<p>Darth Vecdor is a platform that does a number of things, especially creating knowledge graphs, using a galaxy of modern semantic vector-based technologies. Darth Vecdor provides force-like control over these complex technologies with a simple graphical user interface, and behind the scenes, powerful APIs.</p>
<p>Darth Vecdor navigates the secret arts of concept relationships, including:<UL>
        <LI>Loading in terminologies.</LI>
        <LI>Creating code subsets (aka code sets).</LI>
        <LI>Creating one or more vector representations (embeddings) for the strings in the terminologies and/or code subsets.</LI>
        <LI>Creating summary vectors for terminology or code set codes.</LI>
        <LI>Creating expansion (synonymous) strings for various strings to potnetially facilitate mapping of strings (e.g., from LLM responses) back to structured codes.</LI>
        <LI>Storing previously identified relationships.</LI>
        <LI>Creating relationships (creating or enhancing knowledge graphs) using the knowledge encoded in LLMs by iteratively querying LLMs.</LI>
        <LI>Potentially enhancing responses from LLMs by requerying ("are you sure") to possibly reduce hallucinations or erroneous repsonses, and requerying when potentially overly general responses are provided to possibly get more specific ("beceptive") and useful responses.</LI>
        <LI>Mapping strings responses returned by LLMs (or other strings) to codes in a code-set or terminology.</LI>
        <LI>... and probably more!
    </UL></p>
    <I>Note, some functionality above may not yet be implemented.</I>
<p>It’s not just smart — it’s semantically savvy. Like Darth Vecdor did, step out of the dark and into the light (of knowledge graphs).</p>
        `
    },
    "Functions": {
        type: "menu_parent",
        label: "Functions"
        },
    "Terminology Populator": {
        type: "form",
        formKey: "terminology_populator",
        formTitle: "Terminology Populator",
        parent: "Functions",

        subformTitle: "No Subform",
        configListUrl: "/get_terminology_populator_orchestration_names",
        configLoadUrl: "/get_terminology_populator_orchestration_json",
        submitUrl: "/populate_terminology_from_query",
        mainFields: [
            { name: 'base_name', label: 'Name', type: 'text', default: '', help: 'The name you want to give to this populator configuration.' },
            { name: 'terminology', label: 'Terminology', type: 'text', default: '', help: 'The name of the terminology that holds all these codes.' },
            { name: 'query', label: 'SQL Query', type: 'textarea', default: 'SELECT the_code, one_of_the_strings_for_the_code, priority FROM the_table WHERE terminology = \'my_terminology\'', help: 'SQL Query to get all the codes and associated strings for the terminology. Your terminology may have more than one string per code, just return each such string in a different row.The last field ("priority") denotes the priority ordering of the strings. Most important is to denote one string as the top priority (priority number 1) string, which will be the main string associated with the code. There can be more than one string per code, just return each such string in a different row.' },
            ]
        },
    "Code Set Populator": {
        type: "form",
        formKey: "code_set_populator",
        formTitle: "Code Set Populator",
        parent: "Functions",

        subformTitle: "No Subform",
        configListUrl: "/get_code_set_populator_orchestration_names",
        configLoadUrl: "/get_code_set_populator_orchestration_json",
        submitUrl: "/populate_code_set_from_query",
        mainFields: [
            { name: 'base_name', label: 'Name', type: 'text', default: '', help: 'The name you want to give to this populator configuration.' },
            { name: 'code_set', label: 'Code Set Name', type: 'text', default: '', help: 'The name you want to give to this code set.' },
            { name: 'query', label: 'SQL Query', type: 'textarea', default: 'SELECT DISTINCT id AS code_id FROM dv_objs.codes WHERE terminology = \'my_terminology\' AND code IN (SELECT code FROM terminology_source_table WHERE code_type = \'desired_code_type\' )', help: 'Must return a field called code_id that is the set of ids from the codes table in the Darth Vecdor database (e.g., dv_objs.codes) desired for the code set.' },
            { name: 'expansion_str_style', label: 'Expansion Style', type: 'dropdown', optionsUrl: '/get_expansion_styles', default: '', help: 'Describe the "style" of the expansion strings. This should be one of the styles configured for Darth Vecdor.' },
            { name: 'expansion_str_style_version', label: 'Expansion Style Version', type: 'text', default: '001', help: 'The version of the expansion string style.' },
            ]
        },
    "Relationship Populator": {
        type: "form",
        formKey: "relationship_populator",
        formTitle: "Relationship Set",
        parent: "Functions",

        subformTitle: (i, sf) => `Relationship #${i + 1}: ${sf.rel || '(no name)'}`,
        configListUrl: "/get_rels_populator_orchestration_names",
        configLoadUrl: "/get_rels_populator_orchestration_json",
        submitUrl: "/populate_rels",

        mainFields: [
            {
                name: 'mode',
                label: 'Mode',
                type: 'dropdown',
                options: [
                    { label: "1) TESTING: See only prompt and configs", value: "see_obj_only" }
                    , { label: "2) TESTING: See prompt, configs, and sample response", value: "see_obj_and_resp" }
                    , { label: "3) FULL RUN", value: "full_run" }
                    ],
                default: 'full_processing',
                help: 'On submit, do what? Options: 1) Just get the resulting configurations and prompt that will get generated, do not actually save data. Results in debug log. 2) Show resulting configurations and prompt, and also show relationships to be generated using the sample term provided elsewhere on this form. Configurations and populators will be saved to the database, but you can make changes to them using this form. Relationship data will not be saved. Expansion strings do not get tested. Results in debug log. 3) Fully process and save all configurations and data as requested.'
            },
            { name: 'test_term', label: 'Test term', type: 'textarea', default: '', help: 'If you have chosen option 2 for "Mode" then what item(s) should be used as the subject of the prompt? For multiple, put one item per row.' },
            { name: 'version', label: 'Version', type: 'text', default: '001', help: 'Enter what you want to use as a version number for this relationship set.' },
            { name: 'base_name', label: 'Base Name', type: 'text', default: '', help: 'The root or base name of the relationship set.' },

            {
                name: 'code_selector_type',
                label: 'Code Selector Type',
                type: 'dropdown',
                options: [
                    { label: "Code Set", value: "code_set" },
                    { label: "Terminology", value: "terminology" },
                    { label: "Query", value: "query" }
                ],
                default: 'code_set',
                help: 'What should be used to choose the select the codes for which the relationship(s) will be identified.'
            },
            {
                name: 'code_selector',
                label: 'Code Selector',
                dynamicOptions: {
                    dependsOn: 'code_selector_type',
                    sources: {
                        'terminology': { type: 'dropdown', optionsUrl: '/get_terminology_names' },
                        'code_set': { type: 'dropdown', optionsUrl: '/get_code_set_names' },
                        'query': { type: 'textarea' }
                    }
                },
                default: '',
                help: 'The terminology name, code set name, or query to use to get the codes. If you selected "Code Set" as your Code Selector Type above but see no code sets in the dropdown here, then you will have to create and populate one first -- available from the menu at the top right. Simiarly, you will have to populate a terminology if you have not done so already but would like your code selector to use a terminology.'
            },

            // :
            { name: 'llm_config_name', label: 'LLM+LLM configs to use', type: 'dropdown', optionsUrl: '/get_llm_config_names', default: '', help: 'Which LLM and associated configurations should be used? This is the name of an LLM configuration defined on the Darth Vecdor server configs.' },
            { name: 'rels_case_change', label: 'LLM Response Case Change Mode', type: 'dropdown', options: ['none', 'lower', 'upper'], default: 'lower', help: 'How to change the case of responses from LLM (if at all) prior to storage.' },
            // Next items will just handle using LLM config defaults. This stuff is so dynamically generated, it seems a mistake to do otherwise right now.
            // { name: 'llm_str_output_separator_name', label: 'LLM Output Separator', type: 'text', default: '', help: 'What string separates multiple LLM responses.' },
            // { name: 'llm_str_output_response_surrounder', label: 'LLM Output Surrounder', type: 'text', default: '', help: 'Optional character(s) surrounding the LLM output.' },
            // { name: 'instructions', label: 'LLM Prompt Instructions', type: 'textarea', default: '', help: 'Required instructions used in prompts.' },

            // Beceptivity related fields
            { name: 'beceptivity_src_type', label: 'Beceptivity Source Type (ignored for any relationship with minimum beceptivity unset or set to 0)', type: 'dropdown', options: ['llm_response', 'llm_2nd_response'], default: 'llm_response', help: 'llm_response means the beceptivity of a response will be requested along with the response itself. llm_2nd_response means the beceptivity of each response will be requested in a second query to the LLM. llm_2nd_response is much slower and incurs many more hits to the LLM (one per initial response to go back and obtain a beceptivity value) but alos anecdotally seemed to get better results. YMMV.' },
            // Next items will just handle using LLM config defaults. This stuff is so dynamically generated, it seems a mistake to do otherwise right now.
            // { name: 'beceptivity_instructions', label: 'Beceptivity Instructions', type: 'textarea', default: '', help: 'Prompt instructions for beceptivity.' },
            // { name: 'beceptivity_max_val', label: 'Beceptivity Max Value', type: 'text', default: '', help: 'Highest valid beceptivity value.' },
            // { name: 'beceptivity_cutoff', label: 'Beceptivity Cutoff', type: 'text', default: '', help: 'In each relationship you can set a minimum acceptable beceptivity threshold for a response. Any response less than this will trigger a requery of the LLM to get a more beceptive response. This particular global setting for this set of relationships is what we will tell the LLM is the value that it should use to separate specific items from categories. This theoretically should not differ from the minimum acceptable beceptivity thresholds you might set for each relationship, but in practice, you might find that, despite this instruction, the values require you to set a different minimum threshold to adequately separate what you consider a category from what you consider a specific item, based on how you see the LLM actually responds.' },
            // { name: 'beceptivity_val_if_none', label: 'Beceptivity Value if None Returned', type: 'text', default: '', help: 'Fallback value if beceptivity lookup fails.' },
            // { name: 'beceptivity_name', label: 'Beceptivity Name', type: 'text', default: '', help: 'Alternate name for beceptivity, if needed.' },

            // Expansion string related fields
            { name: 'expansion_str_style', label: 'Expansion Style (Optional)', type: 'dropdown', optionsUrl: '/get_expansion_styles', default: '', help: 'Which "style" of expansion strings should be used? If you do not want expansion strings, just leave this blank. Expansion strings facilitate matching across concepts or to terminology systems by providing alternative words or phraases ("expansion strings") for each response from the LLM -- excluding "no write" responses. This is much more time-consuming, because each returned item will be requeried for its expansion terms, but it can be very helpful for many uses in which strings meaning the same thing but having different terminology or phraseology need to be compared or matched. Theoretically, vector comparisons already do this, but anecdotally it appears that such comparisons may be enhanced with augmented with expansion strings (and associated vectors). In many cases, string expansion may be unnecessary, such as when the returned response is expected to be a magnitude in the form of a number in numerical format.' },
            // { name: 'expansion_str_style_version', label: 'Expansion Style Version', type: 'text', default: '001', help: 'The version of the expansion string style.' },

            // Other fields
            { name: 'notes', label: 'Notes (Optional)', type: 'textarea', default: '', help: 'Any notes you might like to add about this set, for any reason.' }

        ],

        subformFields: [
            { name: 'rel', label: 'Relationship Term or Phrase to Be Stored In Database', type: 'text', default: '', help: 'How should I store this relationship in the database? For example, if I am getting the colors of objects, this value might be something like "has color or colors of" (without the quotes).' },
            { name: 'rel_prompt', label: 'Prompt to Use to Get the Desired Relationship Information for Each Term in the Code Set from the LLM', type: 'textarea', default: '', help: 'Prompt for generating the related data. For example, let us say one of my prompts to the LLM will be asking for expected color or colors of an object. In such a case, you might put (without the quotes) "What are the color or colors of the term at the end of the prompt?" The system will automatically add the term (a member of your code set) to the end of the prompt and provide instructions at the beginning that all of these prompts refer to that term that it will add to the end of the prompt. Therefore, you do not actually have to specify "at the end of the prompt" in each relationship prompt, and (in this example) could simply say something like, "For the term, what color or colors does it have?"' },

            // ✅ FIXED: use string booleans for consistent JSON and server parsing
            { name: 'is_multi_resp', label: 'Multi-Response? (note: must be false if you have a response dictionary defined below)', type: 'dropdown', options: ['True', 'False'], default: 'True', help: 'Allow the LLM to return multiple values? For example, if you ask for all colors of an object, that would imply an object could have more than one color, therefore teh LLM could return multiple values and you would set this to True. If you ask for the single main color of an object, then you would set this to False.' },
            { name: 'is_no_write', label: 'No Write?', type: 'dropdown', options: ['True', 'False'], default: 'False', help: 'Whether to skip writing responses to this prompt and for this "relationship" to the LLM. This is intended to serve as an opportunity for the LLM to provide its reasoning for an answer before actually providing an answer in later relationship prompts. Prompts are ordered, so typically you would order a no-write prompt asking the LLM to reason first, then create another prompt asking the LLM for its "final" answer. Why do this? Anecdotal experience and many articles suggest that having the LLM reason first can lead to better responses. As LLMs evolve and automatically do reasoning prior to providing an answer, the need or utility for this no-write functionality may diminish or disappear.' },

            { name: 'resp_dict', label: 'Response Dictionary (note: must be blank if Multi-Response above is set to True)', type: 'textarea', default: '', help: `Optional JSON dict of allowed responses.
    Example:
    {
        "1": "Head",
        "2": "Shoulders",
        "3": "Knees",
        "4": "Toes"
    }
    Your prompt needs to specify that the LLM should return one of these values (1, 2, 3, or 4). For example the prompt might say, "What is your favorite body part? Answer 1 if Head, 2 if Shoulders, 3 if Knees, and 4 if Toes." This system will check the response (e.g., "3") against this dictionary and convert the key of the Response Dictionary to the value (e.g., "Knees"). If the response is not in the dictionary, it will be considered an error and will not be written to the database. If you do not want to use a response dictionary, just leave this blank.` },

            { name: 'min_acceptable_beceptivity', label: 'Min Acceptable Beceptivity', type: 'text', default: '0', help: 'Minimum acceptable beceptivity score. Unless set otherwise in configs, Set Beceptivity to 0 if you do not want the system to require each response to have some minimum beceptivity. Unless set otherwise in configs, non-zero beceptivities are integers ranging from 1 - 10, with the LLM being instructed that anything that is a category should get a value less than 7.' },
            { name: 'get_more_beceptive_content_prompt', label: 'Prompt to Get More Beceptive Content', type: 'textarea', default: '', help: 'Prompt to use to get more beceptive content if any response for this relationship is inadequately beceptive. Ignored if minimum beceptivity is set to 0 for this relationship. If you set a minimum beceptivity above 0 but leave this blank, then a prompt to get more beceptive content will be created for you. If you do enter a prompt here, it MUST CONTAIN the object string placeholder (default, unless otherwise configured, is <<<obj_str>>)' },
            { name: 'max_beceptivity_loops', label: 'Count of beceptivity loops to do to try to get adequate beceptivity', type: 'text', default: '1', help: 'How many retries to allow to try to get adequately beceptive content? This MUST be over 0 if minimum acceptable beceptivity is greater than zero.' },
            { name: 'is_assume_adequate_on_max_loop', label: 'Assume adequate beceptivity for any results on final attempt to get more beceptivity?', type: 'dropdown', options: ['True', 'False'], default: 'True', help: 'If False, then will not retain as relationship objects any object strings returned on final beceptivity loop found inadequately beceptive (specific). If True, then all object strings returned on final beceptivity loop will be stored, without further considering beceptivity.'},
            { name: 'are_you_sure_count', label: 'Are-You-Sure Count', type: 'text', default: '0', help: 'How many retries to allow before adjudication? If 0, then this functionality will not trigger to re-ask the LLM if it is sure of a response.' },
            // I removed categorical here as an option (and from the info button content) because it requires
            // a response dicitonary, and I'm not sure I enabled that for the AYS prompt.
            // Also, if the "vote" on a category ends in a tie, then the LATTER of the responses will win.
            // That's kind of complex to explain, so overall, for now, just remove this option.
            { name: 'are_you_sure_adjudicator', label: 'Adjudicator Type (ignored if the Are-You-Sure Count is blank or 0)', type: 'dropdown', options: ['', 'vote', 'avg', 'sum'], default: '', help: 'How to adjudicate disagreement. If the type is "vote" then you will want the Are-You-Sure (AYS) prompt below to ask the LLM to return a 1 if it confirms your prompt, and a 0 if it thinks the proposition is incorrect. The adjudicator will then compare the count of 1 and count of 0 responses to determine a final answer. If you set an AYS count above to an odd number, then the original prompt response will not be used for the voting. If you set the AYS count to an even number, the original prompt response will be used for the voting (a presumed 1 vote). This ensures an odd number of votes, guaranteeing a "winner". avg and sum Adjudiator types mean that your original prompt and this Are-You-Sure prompt all expect a numerical response from the LLM. avg will make the final answer the average of all of its responses, sum will make the final answer the sum of all of its responses. IMPORTANT NOTE: ONLY VOTE HAS HAD ANY TESTING.' },
            { name: 'are_you_sure_prompt', label: 'Are-You-Sure Prompt (ignored if the Are-You-Sure Count is blank or 0)', type: 'textarea', default: '', help: 'Prompt to use to ask the LLM if it is sure of its response. <<<obj_str>>> in the prompt will be substituted with each item in the response from the LLM. <<<subj_str>>> in the prompt will be substituted with the term from the code set that was submitted with the original prompt. If your Adjudicator Type above is "vote" then you will want the prompt to ask the LLM to return either a 1 if it confirms your prompt, and a 0 if it thinks the proposition is incorrect.  An example might be: Imagine that your relationship prompt was "What color is the term at the end of this prompt?". Your AYS prompt might be something like, "Answer only with a 1 for yes or 0 for no. Provide no explanation or other verbiage. Is it correct that <<<obj_str>>> is the color of <<<subj_str>>>?"' },
            { name: 'are_you_sure_val_if_error', label: 'Value to Use If Adjudication Fails (ignored if the Are-You-Sure Count is blank or 0)', type: 'text', default: '', help: 'If adjudication fails, what should the adjudication response be? For example, if asked for a vote of 1 or 0, and the prompt(s) fail(s), what should the vote be? 1 or 0?' }
        ]
    },


    "Relationship String to Code Matcher": {
        type: "form",
        formKey: "relationship_string_to_code_matcher",
        formTitle: "Relationship String to Code Matcher",
        parent: "Functions",

        subformTitle: "No Subform",
        configListUrl: "/get_code_matcher_orchestration_names",
        configLoadUrl: "/get_code_matcher_orchestration_json",
        submitUrl: "/populate_code_set_matches",

        mainFields: [
            { name: 'base_name', label: 'Base Name', type: 'text', default: '', help: 'Base name to be used to generate a name for this configuration.' },
            { name: 'match_from_rel_populator_id', label: 'Original Relationship Populator', type: 'dropdown', optionsUrl: '/get_relationship_populator_ids_and_names', default: '', help: 'The populator object that had been used to generate the relevant relationship strings.' },
            {
            name: 'match_from_rel'
            , label: 'Relationship to Match From'
            , type: 'dropdown'
            , dynamicOptions: {
                dependsOn: 'match_from_rel_populator_id'
                ,optionsUrlTemplate: '/get_rels_of_rel_populator/{value}'
                }
            , default: ''
            , help: 'The name of the specific relationship to match from.'
            },
            //{ name: 'match_from_rel', label: 'Relationship to Match From', type: 'text', default: '', help: 'The name of the specific relationship to match from.' },
            { name: 'match_obj_main_str', label: 'Match Using Original Relationship Object String?', type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For the object, use the original relationship object string for matching to a code?' },
            { name: 'match_obj_expansion_summary_vec', label: 'Match Using Object String\'s Summary Vector of all It\'s Expansion Strings?',  type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For the object, use the relationship object string\'s expansion strings for matching to a code?' },
            { name: 'match_code_main_str', label: 'Match Using Code Main String?',  type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For the code, use the code\'s main string for matching to a relationship object string?' },
            { name: 'match_code_other_strs', label: 'Match Using Code\'s Other Strings?',  type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For the code, use the code\'s alternative (non-main) strings for matching to a relationship object string?' },
            { name: 'match_code_summary_vec', label: 'Match Using Code\'s Summary Vector of All It\'s Official Strings?',  type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For matching, use the code\'s mean summary vector that is the average of the vectors of its main and alternative (non-main) strings?' },
            { name: 'match_code_expansion_summary_vec', label: 'Match Using Code Expansion Summary Vector?',  type: 'dropdown', options: ['Yes', 'No'], default: 'Yes', help: 'For matching, use the code\'s mean expansion string summary vector that is the average of the vectors of its main string and its expansion strings?' },
            { name: 'vec_to_use', label: 'Vector to Use', type: 'dropdown', options: ['cls', 'mean'], default: 'cls', help: 'The vector type to use for matching.' },
            { name: 'expanion_str_styles', label: 'Expansion Styles', type: 'accumulator', optionsUrl: '/get_expansion_styles', default: '', help: 'If expansion strings will be used for matching, which expansion string styles should be used?' },
            //{ name: 'expanion_str_styles_json', label: 'Expansion Styles JSON', type: 'multi_checkbox', default: '', help: 'Full JSON structure of expansion string styles.' },
            { name: 'match_to_code_set_name', label: 'Match Relationship Object Into Code Set With Name Of...', type: 'dropdown', optionsUrl: '/get_code_set_names', default: '', help: 'The code set name to match the relationship object string into.' }
            ]
        },

    "Custom Table Populator": {
        type: "form",
        formKey: "custom_table_populator",
        formTitle: "Custom Table Populator",
        parent: "Functions",

        subformTitle: "No Subform",
        configListUrl: "/get_custom_table_populator_orchestration_names",
        configLoadUrl: "/get_custom_table_populator_orchestration_json",
        submitUrl: "/populate_custom_table",

        mainFields: [
            { name: 'name', label: 'Name', type: 'text', default: '', help: 'The name you want to give to this populator configuration.' },
            { name: 'ctg_version', label: 'Version', type: 'text', default: '001', help: 'The version you want to give to this populator configuration.' },

            {
                name: 'ctg_code_selector_type',
                label: 'Code Selector Type',
                type: 'dropdown',
                options: [
                    { label: "Code Set", value: "code_set" },
                    { label: "Terminology", value: "terminology" },
                    { label: "Query", value: "query" }
                ],
                default: 'code_set',
                help: 'What should be used to choose the select the codes for which the custom table will be generated. If you do not enter a code placeholder value and destionation code field below, then the value of this field will be ignored and the query will be run as a batch insert query, not one insert query per code.'
            },
            {
                name: 'ctg_code_selector',
                label: 'Code Selector',
                dynamicOptions: {
                    dependsOn: 'ctg_code_selector_type',
                    sources: {
                        'terminology': { type: 'dropdown', optionsUrl: '/get_terminology_names' },
                        'code_set': { type: 'dropdown', optionsUrl: '/get_code_set_names' },
                        'query': { type: 'textarea' }
                    }
                },
                default: '',
                help: 'The terminology name, code set name, or query to use to get the codes. If you selected "Code Set" as your Code Selector Type above but see no code sets in the dropdown here, then you will have to create and populate one first -- available from the menu at the top right. Simiarly, you will have to populate a terminology if you have not done so already but would like your code selector to use a terminology. If you do not enter a code placeholder value and destionation code field below, then the value of this field will be ignored and the query will be run as a batch insert query, not one insert query per code.'
            },

            { name: 'ctg_dest_table', label: 'Destinaton Schema and Table', type: 'text', default: 'custom_generated_tables.my_custom_table_name', help: 'The destination table (with associated schema) to be populated.' },
            { name: 'ctg_query', label: 'SQL Query', type: 'textarea', default: 'SELECT codes.code, LENGTH(codes.code) AS code_length, mci.code_importance FROM dv_objs.codes codes INNER JOIN source_schema.more_code_info mci ON codes.code = mci.code WHERE codes.code = :code', help: 'The SELECT query to be used to populate the table. It should contain a parameter placeholder where the terminology code or code set code will be substitued in. That placeholder should start with a colon (as in the example query). You can use any word/term (no spaces or characters other than letters, numbers, and underscore) for your placeholder. You will tell the system what is that placeholder in the Code Placeholder entry below (include the placeholder text without the colon). The system will wrap your select query in a CREATE TABLE IF NOT EXISTS in order to auto-generate the table if it is not already present. However, you may wish to have your own CREATE TABLE IF NOT EXISTS query. You may also wish to do other things, like CREATE INDEX IF NOT EXISTS statmements. If so, put all your setup queries first (create table, create index, etc.), then put your select query last. Separate each query with your configured query separator (default is <dv_query_separator>). Do not end any queries with a semicolon. Do not add another query separator at the end of your last query or before your first one. If you only have the one select query, you do not need a query separator. For populating the table, the system will automatically wrap your select query into an INSERT INTO table query, substituting in each code from your code selector, one at a time, running the query once per code.'},
            { name: 'ctg_code_placeholder', label: 'Code Placeholder', type: 'text', default: 'code', help: 'Placeholder in your query that will be substituted with each code returned by your code selector (one code per query). Do not include the colon (":") at the beginning. If you leave both Code Placeholder and Destination Code Field blank, the query will be run as a single batch insert, not one insert query per code.' },
            { name: 'ctg_dest_code_field', label: 'Destination Code Field Name', type: 'text', default: 'code', help: 'In the destionation table to be populated, what is the name of the field that will be populated with the code from the code selector. If you leave both Code Placeholder and Destination Code Field blank, the query will be run as a single batch insert, not one insert query per code.' },
            ]
        },

    "About": {
        type: "menu_parent",
        label: 'About - PLEASE READ'
        },

    "Contributors": {
        type: "page",
        parent: "About",
        content: "<B>CONTRIBUTORS</B><p>Darth Vecdor was conceived and created by Jonathan A. Handler. Large language models (mostly ChatGPT) and many other resources were used to help create this project. As the owner of this software, Keylog Solutions LLC is proud to offer Darth Vecdor as an open source project -- please see the associated license. This project depends on many brilliant and innovative  technologies (software, hardware, and more) created, implemented, deployed, and managed by many other people. This project is a tribute to all those who have contributed to the underlying math, engineering, technology, and science that made Darth Vecdor possible.</p>"
        },

    "USE IS AT YOUR OWN RISK - PLEASE READ": {
        type: "page",
        parent: "About",
        content: "<B>USE IS AT YOUR OWN RISK AND THERE ARE NO WARRANTIES OR CONDITIONS OF ANY KIND</B><p>In addition to all the caveats in and elements of the license for use of Darth Vecdor, on these pages, and throughout the codebase, please exercise great care in using Darth Vecdor or any of its outputs. Even if anything communicated in any way by Keylog Solutions LLC or any of the Darth Vecdor contributors, creators, or other associates might seem to imply that it might be used or be useful for medical or healthcare (or for any other purpose), it may in fact NOT be suitable for those purposes or for any other purpose, and may even be dangerous and harmful. Your use of the software is entirely at your own risk. There are VERY IMPORTANT terms of use in the license -- please read them.</p><p>In addition to all other terms in the license, please especially note that  there is a <B><K>Disclaimer of Warranty.</I></B> Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an \"AS IS\" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.</p><p>In addition, there is a <B><I>Limitation of Liability</B></I>. In no event and under no legal theory, whether in tort (including negligence), contract, or otherwise, unless required by applicable law (such as deliberate and grossly negligent acts) or agreed to in writing, shall any Contributor be liable to You for damages, including any direct, indirect, special, incidental, or consequential damages of any character arising as a result of this License or out of the use or inability to use the Work (including but not limited to damages for loss of goodwill, work stoppage, computer failure or malfunction, or any and all other commercial damages or losses), even if such Contributor has been advised of the possibility of such damages. There are also other very important terms in the license. Please read it carefully. In addition, please note that Darth Vecdor is a work in progress and is not yet complete. It is being released as an open source project, but it may not be suitable for production use or for any other purpose. Please use it with caution and at your own risk.</p>"
        },
    "ASSUME NO SECURITY OR PRIVACY PROTECTION IN THIS SOFTWARE": {
        type: "page",
        parent: "About",
        content: "<B>ASSUME NO SECURITY OR PRIVACY PROTECTION IN THIS SOFTWARE</B><p>This software generally does not contain security or privacy features or even basic security functionality, capabilities, or even necessarily best practices. It is up to you to configure this program for secure and private use (if that is even possible, which it may not be), to protect your URL endpoints, to decide which functions or endpoints to expose and/or enable (if any), and to ensure data, network and transmission, application, and any other security and privacy. None of thie should be assumed present by default (and much of it definitely is not), and if you see or experience anything that appears to involve security or privacy, you should not trust it. Security and privacy are entirely up to you.</p>"
        }
    };
/////////////////// BEGIN APPLICATION CONFIGURATIONS/CONTENT //////////////////////


/////////////////// BEGIN FUNCTIONS FOR THE PAGE NOT SPECIFICALLY RELATED TO THE FORM //////////////////////
function generateMenu() {
  const menu = document.getElementById('dropdown-menu');
  menu.innerHTML = ''; // Clear old items

  // Group children by parent key
  const childrenByParent = {};
  Object.entries(appConfig).forEach(([key, cfg]) => {
    if (cfg.parent) {
      if (!childrenByParent[cfg.parent]) childrenByParent[cfg.parent] = [];
      childrenByParent[cfg.parent].push(key);
    }
  });

  // Render top-level items and parents
  Object.entries(appConfig).forEach(([key, cfg]) => {
    if (cfg.parent) return; // Skip children here; they'll be rendered below manually

    const label = cfg.label || key;
    const hasChildren = childrenByParent[key] && childrenByParent[key].length > 0;

    const parentItem = document.createElement('div');
    parentItem.className = 'menu-item' + (hasChildren ? ' has-children' : '');
    parentItem.style.cursor = 'pointer';

    const labelDiv = document.createElement('div');
    labelDiv.className = 'menu-label';
    labelDiv.textContent = label;

    parentItem.appendChild(labelDiv);

    // Append parent first (important for submenu to appear below)
    menu.appendChild(parentItem);

    if (hasChildren) {
      // Toggle submenu on parent label click
      labelDiv.onclick = (e) => {
        e.stopPropagation();
        const isExpanded = parentItem.classList.toggle('expanded');
        const children = document.querySelectorAll(`.submenu-of-${key}`);
        children.forEach(child => {
          child.classList.toggle('hidden', !isExpanded);
        });
      };

      // Render children as siblings, hidden by default
      childrenByParent[key].forEach(childKey => {
        const childCfg = appConfig[childKey];
        if (!childCfg) return;

        const childItem = document.createElement('div');
        childItem.className = `menu-item submenu-item submenu-of-${key} hidden`;
        childItem.style.cursor = 'pointer';

        const childLabel = document.createElement('div');
        childLabel.className = 'menu-label';
        childLabel.textContent = childKey;

        const childDesc = document.createElement('div');
        childDesc.className = 'menu-desc';
        childDesc.textContent =
          // childCfg.type === 'form' ? 'Configure ' + childKey : 'View ' + childKey;
          '';
        childItem.appendChild(childLabel);
        childItem.appendChild(childDesc);

        childItem.onclick = () => navigateTo(childKey);

        menu.appendChild(childItem);
      });

    } else {
      // If no children, clicking parent navigates immediately UNLESS it's a menu parent
      if (key in appConfig && appConfig[key].type !== 'menu_parent')
        {
        parentItem.onclick = () => navigateTo(key);
        }
    }
  });
}


function collapseMenu() {
  const menu = document.getElementById('dropdown-menu');
  menu.querySelectorAll('.menu-item.expanded').forEach(item => {
    item.classList.remove('expanded');
  });
  menu.querySelectorAll('.submenu-item').forEach(item => {
    item.classList.add('hidden');
  });
  menu.classList.remove('show');
}

function navigateTo(pageName) {
  collapseMenu();
  window.location.hash = encodeURIComponent(pageName);
}

function toggleDropdown() {
  document.getElementById('dropdown-menu').classList.toggle('show');
}


    function navigateSection(hash) {
      document.getElementById("dropdown-menu").classList.remove("show");
      location.hash = hash;
    }

    // Close any open tooltips if clicking outside
    window.addEventListener('click', () => {
    document.querySelectorAll('.tooltip-text.show').forEach(tip => {
        tip.classList.remove('tooltip-top');
        setTimeout(() => {
        tip.classList.remove('show');
        }, 200); // ⏳ wait 200ms before fully hiding
    });
    });


    function toggleTheme() {
      const current = document.body.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.body.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
    }


    window.addEventListener("hashchange", showSection);
    window.addEventListener("DOMContentLoaded", () => {
      generateMenu();
      const saved = localStorage.getItem("theme");
      if (saved) document.body.setAttribute("data-theme", saved);
      if (!window.location.hash) window.location.hash = encodeURIComponent("Home");
      showSection();
    });

    function showSection() {
    const container = document.getElementById('app');
    const hash = decodeURIComponent(window.location.hash.substring(1)) || "Home";

    const config = appConfig[hash];
    if (!config) {
        container.innerHTML = `<h1>Page Not Found</h1>`;
        return;
    }

    // Clear previous content or unmount old components
    container.innerHTML = ''; // 🧹 Clear old content first!
    render(null, container);  // 👈 This unmounts any previous Preact component

    if (config.type === "page") {
        container.innerHTML = config.content;
        }
    else if (config.type === "form") {
        render(h(DarthVecdorForm, { config }), container);
        }
    }
/////////////////// END FUNCTIONS FOR THE PAGE NOT SPECIFICALLY RELATED TO THE FORM //////////////////////



/////////////////// BEGIN FUNCTIONS FOR THE PAGE SPECIFICALLY RELATED TO THE FORM //////////////////////
function DarthVecdorForm({ config }) {


    const mainFormConfig = config.mainFields;
    const subformConfig = config.subformFields || [];

  const { h } = preact;
  const { useState } = preactHooks;

  const [mainForm, setMainForm] = useState(
    Object.fromEntries(mainFormConfig.map(f => [f.name, f.default || '']))
  );
  const [subforms, setSubforms] = useState([]);
  const [collapsedIndex, setCollapsedIndex] = useState([]);
  const [mainCollapsed, setMainCollapsed] = useState(false);
  const [formKey, setFormKey] = useState(0);
  const [dynamicDropdowns, setDynamicDropdowns] = useState({});

  // For form input from file
  let fileInputEl = null;


  /* Automating getting config options for dropdown from server as needed */
  const [configOptions, setConfigOptions] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState('');


    // FUNCTION Load form from JSON
    const load_form_from_json = (payload) => {
    if (!payload) return;

    const { rels = [], ...rest } = payload;

    // Update main form
    setMainForm(prev => {
      const newState = {};
      mainFormConfig.forEach(f => {
        newState[f.name] = rest[f.name] ?? '';
      });
      return newState;
    });

    // Update subforms
    if (!Array.isArray(subformConfig)) {
        console.warn("subformConfig is not available or not an array:", subformConfig);
        return;
        }

    const newSubforms = rels.map(rel => {
      const form = {};
      subformConfig.forEach(f => {
        form[f.name] = rel[f.name] ?? '';
      });
      return form;
    });

    setSubforms(newSubforms);
    setCollapsedIndex([]);
    setMainCollapsed(false);
  };


// EXPORT current form state
const exportFormToJson = () => {
  const payload = {
    ...mainForm,
    rels: subforms,
    exportTime: new Date().toISOString(),
    formKey: config.formKey,
    formTitle: config.formTitle
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${config.formTitle || 'form'}.json`;
  a.click();
  URL.revokeObjectURL(url);
};


const importFormFromJson = (file, fileInputEl) => {
  if (!file) return;

  const reader = new FileReader();
  reader.onload = e => {
    let parsed;
    try {
      parsed = JSON.parse(e.target.result);
    } catch (err) {
      alert('Invalid JSON file');
      console.error(err);
      if (fileInputEl) fileInputEl.value = '';
      return;
    }

    // Check formKey
    if (parsed.formKey !== config.formKey) {
      const importedTitle = Object.values(appConfig)
        .find(cfg => cfg.formKey === parsed.formKey)?.formTitle || 'unknown';

           alert(
            `CANNOT IMPORT YOUR FILE.
=====================
CAUSE OF THE PROBLEM:
The currently showing form is: "${config.formTitle}"
However, the import file is intended for form: "${importedTitle}"
=====================
SOLUTION:
1) Go to the menu.
2) Select "${importedTitle}" and retry the import.
=====================`
          );
      if (fileInputEl) fileInputEl.value = '';
      return;
    }

    // Track failed keys
    const failedKeys = {};

    // Attempt to load each key individually into live form objects
    Object.keys(parsed).forEach(key => {
      if (key === 'exportedAt' || key === 'formKey') return;

      try {
        if (key === 'rels') {
          if (Array.isArray(subforms)) {
            subforms.length = 0;
            if (Array.isArray(parsed.rels)) subforms.push(...parsed.rels);
          } else {
            failedKeys[key] = '"rels" skipped: subforms missing or not an array';
          }
        } else {
          // Let the old loader handle most keys (mainForm)
          if (mainForm) mainForm[key] = parsed[key];
          else failedKeys[key] = 'mainForm missing';
        }
      } catch (err) {
        failedKeys[key] = err.message || String(err);
      }
    });

    // Use the original loader to ensure everything else works
    try {
      load_form_from_json(parsed); // 🔒 scoped to this form instance
    } catch (err) {
      failedKeys['_load_form_from_json'] = err.message || String(err);
    }

    // Alert failures if any
    if (Object.keys(failedKeys).length > 0) {
      alert(
        `Some keys failed to import for form "${config.formTitle}":\n` +
        JSON.stringify(failedKeys, null, 2)
      );
    }

    // Reset file input so retry works
    if (fileInputEl) fileInputEl.value = '';
  };

  reader.readAsText(file);
};


      // Top-level config selector
        preactHooks.useEffect(() => {
            if (!config || !config.configListUrl) return;

          getWithContext(config.configListUrl)
            .then(list => {
              if (!Array.isArray(list)) {
                alert("Expected array from configListUrl");
                return;
              }
              setConfigOptions(list.map(item =>
                typeof item === 'string'
                  ? { id: item, label: item }
                  : { id: item.id, label: item.label ?? item.id }
              ));
            })
            .catch(err => alert("Config list error: " + err.message));
        }, [config]);


preactHooks.useEffect(() => {
  const fields = [...mainFormConfig, ...subformConfig];
  fields.forEach(field => {
    if (field.dynamicOptions) {
      const controllingValue = mainForm[field.dynamicOptions.dependsOn];
      const sources = field.dynamicOptions.sources || {};
      const variant = sources[controllingValue] || {};

      const optionsUrl =
        variant.optionsUrl ||
        (field.dynamicOptions.optionsUrlTemplate
          ? field.dynamicOptions.optionsUrlTemplate.replace('{value}', encodeURIComponent(controllingValue))
          : null);

      if (optionsUrl) {
        const alreadyLoaded = dynamicDropdowns[field.name]?.[controllingValue];
        if (!alreadyLoaded) {
          getWithContext(optionsUrl)
            .then(options => {
              const cleaned = Array.isArray(options) ? options : Object.values(options);
              setDynamicDropdowns(prev => ({
                ...prev,
                [field.name]: {
                  ...(prev[field.name] || {}),
                  [controllingValue]: cleaned
                }
              }));
            })
            .catch(err =>
              console.warn(`Lazy load for '${field.name}' → ${controllingValue} failed:`, err.message)
            );
        }
      }
    }

    // Static or single-source dropdown (not dynamicOptions)
    else if (field.optionsUrl) {
      if (!dynamicDropdowns[field.name]) {
        getWithContext(field.optionsUrl)
          .then(options => {
            const cleaned = Array.isArray(options) ? options : Object.values(options);
            setDynamicDropdowns(prev => ({ ...prev, [field.name]: cleaned }));
          })
          .catch(err => console.warn(`Dropdown '${field.name}' failed:`, err.message));
      }
    }
  });
}, [mainForm]);


const updateMain = (name, value) => {
  setMainForm(prev => {
    const updated = { ...prev, [name]: value };

    // Auto-clear dependent fields
    for (const field of mainFormConfig) {
      if (
        field.dynamicOptions &&
        field.dynamicOptions.dependsOn === name &&
        prev[field.name] !== undefined
      ) {
        updated[field.name] = '';  // or default to field.default if you want that
        // updated[field.name] = field.default
      }
    }

    return updated;
  });
};


  const updateSubform = (i, name, value) => {
    const updated = [...subforms];
    updated[i][name] = value;
    setSubforms(updated);
  };

  const addSubform = () => {
    const newForm = Object.fromEntries(subformConfig.map(f => [f.name, f.default || '']));
    setSubforms(prev => [...prev, newForm]);
    setCollapsedIndex([...Array(subforms.length).keys()]);
    setMainCollapsed(true);
  };

  const deleteSubform = (i) => {
      // Remove the subform at index i
      setSubforms(prev => prev.filter((_, idx) => idx !== i));

      // Update collapsedIndex so it still points to the right subforms
      setCollapsedIndex(prev =>
        prev
          .filter(idx => idx !== i)           // remove the deleted index
          .map(idx => (idx > i ? idx - 1 : idx)) // shift higher ones down
      );
    };


  const moveSubform = (i, direction) => {
    const updated = [...subforms];
    const [moved] = updated.splice(i, 1);
    updated.splice(i + direction, 0, moved);
    setSubforms(updated);
  };

  const toggleCollapse = (i) => {
    setCollapsedIndex(prev => prev.includes(i)
      ? prev.filter(idx => idx !== i)
      : [...prev, i]);
  };

  const toggleMainCollapse = () => setMainCollapsed(!mainCollapsed);
  const collapseAll = () => setCollapsedIndex(subforms.map((_, i) => i));
  const expandAll = () => setCollapsedIndex([]);

const handleJsonnedFormSubmit = async (e) => {
  e.preventDefault();
  const rawPayload = { ...mainForm, rels: subforms };
  const payload = { tjson: JSON.stringify(rawPayload) };

  try {
    // lockPage();
    setWaiting(true);
    updateStatus("Working...");

    const result = await postWithContext(config.submitUrl, payload);

    if (result?.task_id) {
      // Async task: start polling
      taskId = result.task_id;
      pollStatus();
    } else {
      // Synchronous response: we're done right away
      // alert(JSON.stringify(result, null, 2).replace(/\\\\n/g, '\n'));
      //alert(JSON.stringify(result, null, 2));
      // alert(JSON.stringify(result));
      updateStatus("✅ Done!");
      setWaiting(false);
      // unlockPage();
    }

    /*
    if (!result?.task_id) {
      throw new Error("No task_id returned from server.");
    }

    taskId = result.task_id;
    pollStatus();  // same as used by startTask()
    */

  } catch (err) {
    setWaiting(false);
    // unlockPage();
    updateStatus("❌ Submit failed: " + err.message, true);
    alert("Had an error! " + err.message);
  }
};


  const btnStyle = (disabled) => ({
    opacity: disabled ? 0.5 : 1,
    pointerEvents: disabled ? 'none' : 'auto'
  });


// BEGIN FUNCTION
const getEffectiveType = (field) => {

  if (field.dynamicOptions) {

  if (field.typeWhen) {
    const v = mainForm[field.typeWhen.field];
    return field.typeWhen.cases?.[v] || field.type;
  }

  if (field.dynamicOptions) {
    const controller = mainForm[field.dynamicOptions.dependsOn];
    const variant = field.dynamicOptions.sources?.[controller];
    return variant?.type || field.type;
  }

}

  return field.type;
};
// END FUNCTION


// BEGIN FUNCTION
const getEffectiveOptions = (field, mainForm, dynamicDropdowns) => {
  if (!field) return [];

  const controllingValue = field.dynamicOptions?.dependsOn
    ? mainForm?.[field.dynamicOptions.dependsOn]
    : undefined;

  const sources = field.dynamicOptions?.sources || {};
  const variant = sources[controllingValue] || {};

  // Always check dynamicDropdowns for populated options
  const dynamicSet = dynamicDropdowns?.[field.name];
  if (
    dynamicSet &&
    typeof dynamicSet === 'object' &&
    !Array.isArray(dynamicSet) &&
    Array.isArray(dynamicSet[controllingValue])
  ) {
    return dynamicSet[controllingValue];
  }

  // Fallback to static options
  if (variant?.options) return variant.options;

  // Last fallback
  return dynamicDropdowns?.[field.name] || field.options || [];
};
// END FUNCTION


// BEGIN FUNCTION
const shouldShowField = (field) => {
  if (!field.showWhen) return true;

  const { field: dependency, value, values } = field.showWhen;
  const actual = mainForm[dependency];

  if (value !== undefined) {
    return actual === value;
  } else if (Array.isArray(values)) {
    return values.includes(actual);
  }

  return true;
};
// END FUNCTION


// BEGIN FUNCTION
// render fieldconst renderField = (f, value, onChange) => {
const renderField = (f, value, onChange) => {
  try {
    const effectiveType = getEffectiveType(f);
    const rawOptions = getEffectiveOptions(f, mainForm, dynamicDropdowns);
    const dropdownOptions = Array.isArray(rawOptions)
      ? rawOptions.filter(opt => {
          return (
            opt != null &&
            (typeof opt === 'string' ||
             typeof opt === 'number' ||
             (typeof opt === 'object' && 'label' in opt && 'value' in opt))
          );
        })
      : [];

    const available = dropdownOptions.filter(opt => !value?.includes(opt));
    const selected = value || [];
    // END NEW


    return h('div', {
      style: 'display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; position: relative;'
    },

    // === Field label and help tooltip button ===
    h('div', { style: 'display: flex; align-items: center; gap: 0.5rem;' },
      h('span', {}, f.label),
      f.help && h('span', {
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
          const tooltip = e.target.parentNode.querySelector('.tooltip-text');
          if (tooltip) {
            const alreadyVisible = tooltip.classList.contains('show');
            document.querySelectorAll('.tooltip-text.show').forEach(tip => {
              tip.classList.remove('show');
              tip.classList.remove('tooltip-top');
            });
            if (!alreadyVisible) {
              tooltip.classList.add('show');
              if (tooltipAutoCloseTimer) clearTimeout(tooltipAutoCloseTimer);
              tooltipAutoCloseTimer = setTimeout(() => {
                tooltip.classList.remove('show');
                tooltip.classList.remove('tooltip-top');
              }, 8000);

              const rect = tooltip.getBoundingClientRect();
              if (rect.bottom > window.innerHeight - 20) {
                tooltip.classList.add('tooltip-top');
              }

              const tooltipParent = e.target.closest('div');
              if (tooltipParent) {
                const parentRect = tooltipParent.getBoundingClientRect();
                if (parentRect.bottom > window.innerHeight - 50 || parentRect.top < 0) {
                  tooltipParent.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
              }
            }
          }
        }
      }, '?'),
      f.help && h('div', {
        class: 'tooltip-text',
        onMouseEnter: () => {
          if (tooltipAutoCloseTimer) {
            clearTimeout(tooltipAutoCloseTimer);
            tooltipAutoCloseTimer = null;
          }
        },
        onMouseLeave: e => {
          if (!tooltipAutoCloseTimer) {
            tooltipAutoCloseTimer = setTimeout(() => {
              e.target.classList.remove('show');
              e.target.classList.remove('tooltip-top');
            }, 5000);
          }
        }
      }, f.help)
    ),

    // === Textarea ===
    effectiveType === 'textarea' ?
      h('textarea', {
        name: f.name,
        value: value || '',
        onInput: e => onChange(f.name, e.target.value)
      }) :

    // === Text display ===
    effectiveType === 'plaintext' ?
      h('div', { class: 'static-text' }, f.text || '') :



    // === Dropdown (select) ===
    effectiveType === 'dropdown' ?
      h('select', {
        name: f.name,
        value: value != null ? String(value) : '',
        onInput: e => onChange(f.name, e.target.value)
      },
        (Array.isArray(dropdownOptions) ? dropdownOptions : []).map((opt, i) => {
          if (opt && typeof opt === 'object' && 'label' in opt && 'value' in opt) {
            return h('option', { key: i, value: String(opt.value) }, String(opt.label));
          }
          return h('option', { key: i, value: String(opt) }, String(opt));
        })
      ) :

    // === Checkbox ===
    effectiveType === 'checkbox' ?
      h('input', {
        type: 'checkbox',
        name: f.name,
        checked: value === true,
        onInput: e => onChange(f.name, e.target.checked)
      }) :

    // === Radio group ===
    effectiveType === 'radio' ?
      h('div', { style: 'display: flex; gap: 1rem;' },
        (f.options || []).map(opt =>
          h('label', { style: 'display: flex; align-items: center; gap: 0.3rem;' },
            h('input', {
              type: 'radio',
              name: f.name,
              value: opt,
              checked: value === opt,
              onInput: e => onChange(f.name, e.target.value)
            }),
            opt
          )
        )
      ) :

    // === Multi-checkbox group ===
    effectiveType === 'multicheckbox' ?
      h('div', { class: 'multicheckbox-group' },
        (f.options || []).map(opt =>
          h('label', { class: 'multicheckbox-item' },
            h('input', {
              type: 'checkbox',
              value: opt,
              checked: Array.isArray(value) && value.includes(opt),
              onInput: e => {
                const isChecked = e.target.checked;
                const newValue = Array.isArray(value) ? [...value] : [];
                if (isChecked && !newValue.includes(opt)) {
                  newValue.push(opt);
                } else if (!isChecked && newValue.includes(opt)) {
                  newValue.splice(newValue.indexOf(opt), 1);
                }
                onChange(f.name, newValue);
              }
            }),
            opt
          )
        )
      ) :


    // === Dual list accumulator ===
    effectiveType === 'accumulator' ?
      (() => {
        const rawOptions = getEffectiveOptions(f, mainForm, dynamicDropdowns);

        if (!Array.isArray(rawOptions) || rawOptions.length === 0) {
          return h('div', { class: 'accumulator-wrapper empty' }, 'Loading options...');
        }

        const selected = value || [];
        const available = rawOptions.filter(opt => !selected.includes(opt));

        const [selectedAvailable, setSelectedAvailable] = preactHooks.useState(null);
        const [selectedChosen, setSelectedChosen] = preactHooks.useState(null);

        const moveToSelected = () => {
          if (selectedAvailable != null) {
            onChange(f.name, [...selected, selectedAvailable]);
            setSelectedAvailable(null);
          }
        };

        const moveAllToSelected = () => {
          onChange(f.name, [...selected, ...available]);
          setSelectedAvailable(null);
        };

        const removeFromSelected = () => {
          if (selectedChosen != null) {
            onChange(f.name, selected.filter(i => i !== selectedChosen));
            setSelectedChosen(null);
          }
        };

        const removeAllFromSelected = () => {
          onChange(f.name, []);
          setSelectedChosen(null);
        };

        const renderOption = (opt, isSelected, onClick) =>
          h('div', {
            class: `accumulator-option${isSelected ? ' selected' : ''}`,
            onClick: () => onClick(opt),
            title: String(opt) || '(empty)'
          }, String(opt) || '(empty)');

        return h('div', { class: 'accumulator-wrapper horizontal' }, [
          h('div', { class: 'accumulator-column' }, [
            h('div', { class: 'accumulator-title' }, 'Available'),
            h('div', { class: 'accumulator-listbox' }, available.map(opt =>
              renderOption(opt, selectedAvailable === opt, setSelectedAvailable)
            ))
          ]),
          h('div', { class: 'accumulator-actions' }, [
            h('button', {
              type: 'button',
              class: 'accumulator-button',
              onClick: moveToSelected,
              disabled: selectedAvailable == null
            }, 'Add →'),
            h('button', {
              type: 'button',
              class: 'accumulator-button',
              onClick: moveAllToSelected,
              disabled: available.length === 0
            }, 'Add All →'),
            h('button', {
              type: 'button',
              class: 'accumulator-button',
              onClick: removeFromSelected,
              disabled: selectedChosen == null
            }, '← Remove'),
            h('button', {
              type: 'button',
              class: 'accumulator-button',
              onClick: removeAllFromSelected,
              disabled: selected.length === 0
            }, '← Remove All')
          ]),
          h('div', { class: 'accumulator-column' }, [
            h('div', { class: 'accumulator-title' }, 'Selected'),
            h('div', { class: 'accumulator-listbox' }, selected.map(opt =>
              renderOption(opt, selectedChosen === opt, setSelectedChosen)
            ))
          ])
        ]);
      })()
    :


    // === Default: plain text input ===
    h('input', {
      type: 'text',
      name: f.name,
      value: value,
      onInput: e => onChange(f.name, e.target.value)
    })
  );

} catch (err) {
  console.error(`Error rendering field '${f.name}':`, err);
  return h('div', {}, `⚠️ Error rendering ${f.label || f.name}`);
}
};

const renderConfigSelectorDropdown = () => {
  return h('div', { class: 'config-selector-wrapper' }, [

    h('div', { class: 'config-selector-box' },
      h('label', {}, 'Database-Stored Configurations: Select to Load'),
      h('select', {
        value: selectedConfig,
        onInput: async e => {
          const selected = e.target.value;
          setSelectedConfig(selected);
          if (selected && config?.configLoadUrl) {
            try {
              const payload = await getWithContext(
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
        configOptions.map(opt =>
          h('option', { value: opt.id }, opt.label)
        )
      )
    ),

    h('div', { class: 'config-selector-box' },
      h('label', {}, 'File-Stored Configurations: Import and Export'),
      h('div', {style: 'display: flex; gap: 0.5rem; margin-bottom: 0.25rem;'},
      h('button', {
        type: 'button',
        class: 'control-btn',
        style: 'flex: 1;',  // take up roughly half each
        onClick: () => {
          if (!fileInputEl) {
            console.error('File input not mounted');
            return;
          }
          fileInputEl.click();
        }
      }, 'Import Configs from File'),

      h('button', {
        type: 'button',
        class: 'control-btn',
        style: 'flex: 1;',  // take up roughly half each
        onClick: exportFormToJson
      }, 'Export Configs to File')
    )
    )

  ]);
};

const includeConfigSelector = !!config.configListUrl;

const configSelectorField = {
  name: '__config_selector__',
  label: 'Select Configuration',
  type: 'custom'
};

const allMainFields = includeConfigSelector
  ? [configSelectorField, ...mainFormConfig]
  : mainFormConfig;


    return h('form', { onSubmit: handleJsonnedFormSubmit, key: formKey },

    // Next input is for form importing
    h('input', {
      type: 'file',
      accept: 'application/json',
      style: 'display: none;',
      ref: el => { fileInputEl = el },
      onChange: e => {
        importFormFromJson(e.target.files[0]);
        // Reset the input so the same file can be re-imported
        e.target.value = '';
        }
    }),



        h('div', { class: 'subform', style: 'border: 2px solid var(--accent-color);' },
        h('div', { class: 'subform-header' },
            h('div', { class: 'subform-title' }, config.formTitle || 'Form'),
            h('div', { class: 'subform-controls' },
            h('button', {
                type: 'button',
                class: 'control-btn small',
                onClick: toggleMainCollapse
            }, mainCollapsed ? 'Expand' : 'Collapse')
            )
        ),
        h('div', { class: mainCollapsed ? 'collapsed-fields' : '' },
          allMainFields
            .filter(f => shouldShowField(f))
            .map(f =>
              f.name === '__config_selector__'
                ? renderConfigSelectorDropdown()
                : renderField(f, mainForm[f.name], updateMain)
            )
        )
        ),

        subformConfig.length > 0 && [
        h('h2', null, 'Relationships'),
        h('div', { style: 'display: flex; gap: 1rem; margin-bottom: 1rem;' },
        h('button', { type: 'button', class: 'add-btn', onClick: addSubform }, 'Add Relationship'),
        h('button', {
            type: 'button',
            class: 'control-btn',
            onClick: collapseAll,
            style: btnStyle(subforms.length === 0),
            disabled: subforms.length === 0
        }, 'Collapse All'),
        h('button', {
            type: 'button',
            class: 'control-btn',
            onClick: expandAll,
            style: btnStyle(subforms.length === 0),
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
                style: btnStyle(i === 0 || subforms.length < 2),
                onClick: () => moveSubform(i, -1),
                disabled: i === 0 || subforms.length < 2
                }, '↑'),
                h('button', {
                type: 'button',
                class: 'control-btn small',
                style: btnStyle(i === subforms.length - 1 || subforms.length < 2),
                onClick: () => moveSubform(i, 1),
                disabled: i === subforms.length - 1 || subforms.length < 2
                }, '↓'),
                h('button', {
                type: 'button',
                class: 'control-btn small',
                style: btnStyle(subforms.length === 0),
                onClick: () => toggleCollapse(i),
                disabled: subforms.length === 0
                }, collapsedIndex.includes(i) ? 'Expand' : 'Collapse'),
                h('button', {
                type: 'button',
                class: 'control-btn small danger', // you can add a .danger CSS class for red styling
                style: btnStyle(false),
                onClick: () => deleteSubform(i)
              }, 'Delete')
            )
            ),
            h('div', { class: collapsedIndex.includes(i) ? 'collapsed-fields' : '' },
            // subformConfig.map(f => renderField(f, sf[f.name], (name, val) => updateSubform(i, name, val)))
            subformConfig
                .filter(f => shouldShowField(f))
                .map(f => renderField(f, sf[f.name], (name, val) => updateSubform(i, name, val)))
            )
        )
        )
        ],
        h('div', { style: 'display: flex; gap: 1rem; justify-content: flex-end' },
            h('button', { type: 'submit', class: 'submit-btn' }, 'Submit')
        )
    );
    }
/////////////////// END FUNCTIONS FOR THE PAGE SPECIFICALLY RELATED TO THE FORM //////////////////////


    // Close any open tooltips if clicking outside
    window.addEventListener('click', () => {
    document.querySelectorAll('.tooltip-text.show').forEach(tip => tip.classList.remove('show'));
    if (tooltipAutoCloseTimer) {
        clearTimeout(tooltipAutoCloseTimer);
        tooltipAutoCloseTimer = null;
        }
    });

document.addEventListener('click', function(event) {
  const menu = document.getElementById('dropdown-menu');
  const toggleBtn = document.getElementById('dropdown-btn'); // Make sure your toggle button has this ID

  // If click is NOT inside menu or toggle button, close the menu
  if (!menu.contains(event.target) && !toggleBtn.contains(event.target)) {
    menu.classList.remove('show');

    // Also collapse all expanded submenus
    menu.querySelectorAll('.menu-item.expanded').forEach(item => {
      item.classList.remove('expanded');
    });
  }
});


// add a handler for Close button
document.getElementById("statusCloseButton").addEventListener("click", () => {
  document.getElementById("status_area").style.display = "none";
  unlockPage(); // <- unlock only here
});


