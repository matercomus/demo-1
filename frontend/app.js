const app = document.getElementById('app');

let mode = null; // 'chore' or 'meal'
let stage = null;
let currentData = {};
let stepLoading = false;
let stepError = '';

// --- Chat UI State ---
let chatMessages = [];
let chatLoading = false;
let chatError = '';

function renderTable(data, type) {
  if (!Array.isArray(data) || data.length === 0) {
    return `<div class="text-gray-500 text-center py-4">No ${type}s found.</div>`;
  }
  const headers = Object.keys(data[0]);
  return `
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-blue-100">
          <tr>
            ${headers.map(h => `<th class="px-4 py-2 text-left text-xs font-medium text-blue-700 uppercase tracking-wider">${h.replace(/_/g, ' ')}</th>`).join('')}
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-100">
          ${data.map(row => `
            <tr>
              ${headers.map(h => `<td class="px-4 py-2 text-sm text-gray-700">${Array.isArray(row[h]) ? row[h].join(', ') : (row[h] ?? '')}</td>`).join('')}
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// --- Render the top menu bar ---
function renderMenuBar() {
  const menuBar = document.getElementById('menuBar');
  if (!menuBar) return;
  menuBar.innerHTML = `
    <h1 class="text-xl font-bold text-blue-700">Smart Household Assistant</h1>
    <div class="flex flex-wrap gap-3 items-center">
      <button class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition" id="choreBtn">Create Chore</button>
      <button class="px-4 py-2 bg-green-600 text-white rounded shadow hover:bg-green-700 transition" id="mealBtn">Plan Meal</button>
      <button class="px-4 py-2 bg-indigo-600 text-white rounded shadow hover:bg-indigo-700 transition" id="viewChoresBtn">View All Chores</button>
      <button class="px-4 py-2 bg-purple-600 text-white rounded shadow hover:bg-purple-700 transition" id="viewMealsBtn">View All Meals</button>
      <button class="px-4 py-2 bg-pink-600 text-white rounded shadow hover:bg-pink-700 transition" id="editMembersBtn">Edit Family Members</button>
    </div>
  `;
  document.getElementById('choreBtn').onclick = () => startFlow('chore');
  document.getElementById('mealBtn').onclick = () => startFlow('meal');
  document.getElementById('viewChoresBtn').onclick = () => fetchAndShowList('chore');
  document.getElementById('viewMealsBtn').onclick = () => fetchAndShowList('meal');
  document.getElementById('editMembersBtn').onclick = renderEditMembers;
}

function renderMenu() {
  stepLoading = false;
  stepError = '';
  // Render the menu bar at the top
  renderMenuBar();
  // Render the chat UI stretched to fill the main area
  app.innerHTML = `
    <div class="flex flex-col flex-1 h-full w-full items-center justify-center">
      ${renderChatUI()}
    </div>
  `;
  // Chat form handler
  const chatForm = document.getElementById('chatForm');
  if (chatForm) chatForm.onsubmit = handleChatSubmit;
  scrollChatToBottom();
}

function startFlow(selectedMode) {
  mode = selectedMode;
  stage = null;
  currentData = {};
  step();
}

// Helper to render a field input based on field name and mode
function renderField(field, mode, value = "") {
  if (field === "chore_name" || field === "meal_name") {
    return `<label class="block mb-2 font-medium">${mode === 'chore' ? 'Chore Name' : 'Meal Name'}
      <input id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" placeholder="Enter name..." />
    </label>`;
  }
  if (field === "assigned_members") {
    return `<label class="block mb-2 font-medium">Assigned Members
      <input id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" placeholder="Comma-separated names (e.g. Alex, Jamie)" />
    </label>`;
  }
  if (field === "start_date" || field === "meal_date") {
    return `<label class="block mb-2 font-medium">${field === 'start_date' ? 'Start Date' : 'Meal Date'}
      <input id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="date" value="${value}" />
    </label>`;
  }
  if (field === "repetition") {
    return `<label class="block mb-2 font-medium">Repetition
      <select id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
        <option value="daily">Daily</option>
        <option value="weekly">Weekly</option>
        <option value="one-time">One-time</option>
      </select>
    </label>`;
  }
  if (field === "meal_kind") {
    return `<label class="block mb-2 font-medium">Meal Kind
      <select id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
        <option value="breakfast">Breakfast</option>
        <option value="lunch">Lunch</option>
        <option value="dinner">Dinner</option>
        <option value="snack">Snack</option>
      </select>
    </label>`;
  }
  // fallback
  return `<label class="block mb-2 font-medium">${field}
    <input id="fieldInput" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" />
  </label>`;
}

// Utility to add disabled styles
function getDisabledAttrs(loading) {
  return loading ? "disabled style='opacity:0.5;cursor:not-allowed;pointer-events:none;'" : '';
}

async function step(userInput = null, confirm = false) {
  const endpoint = mode === 'chore' ? '/chore/step' : '/meal/step';
  const payload = { current_data: currentData };
  if (userInput) payload.user_input = userInput;
  if (confirm) payload.confirm = true;

  stepLoading = true;
  stepError = '';
  renderStepStage();
  try {
    const res = await fetch(`http://localhost:8000${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to communicate with server.');
    const data = await res.json();
    stage = data.stage;
    if (stage === 'collecting_info') {
      currentData = data.current_data;
      stepLoading = false;
      renderCollecting(data.missing_fields, data.prompt);
    } else if (stage === 'confirming_info') {
      currentData = { ...currentData, ...data.summary };
      stepLoading = false;
      renderConfirming(data.summary, data.prompt);
    } else if (stage === 'created') {
      stepLoading = false;
      renderCreated(data.message, data.id);
    } else {
      stepLoading = false;
      app.innerHTML = `<p class="text-red-600">Error: ${data.message || 'Unknown error'}</p>`;
    }
  } catch (e) {
    stepError = e.message || 'An error occurred.';
    stepLoading = false;
    renderStepStage();
  }
}

function renderStepStage() {
  // Show loading or error for step-based flows
  if (stepLoading) {
    app.innerHTML = `<div class='flex items-center justify-center py-8'><svg class='animate-spin h-8 w-8 text-blue-600' xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24'><circle class='opacity-25' cx='12' cy='12' r='10' stroke='currentColor' stroke-width='4'></circle><path class='opacity-75' fill='currentColor' d='M4 12a8 8 0 018-8v8z'></path></svg><span class='ml-3 text-blue-700 font-medium'>Loading...</span></div>`;
    return;
  }
  if (stepError) {
    app.innerHTML = `<div class='bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4'>${stepError}</div><button class='mt-4 px-4 py-2 bg-gray-400 text-white rounded' id='backToMenuBtn'>Back to Menu</button>`;
    document.getElementById('backToMenuBtn').onclick = renderMenu;
    return;
  }
}

function renderSummaryCard(summary, mode) {
  // Render a nice summary card for confirmation
  const fields = Object.entries(summary).filter(([k, v]) => v !== null && v !== undefined && k !== 'id');
  return `
    <div class="bg-gray-50 rounded-lg shadow p-4 mb-4">
      <h3 class="text-lg font-semibold text-blue-700 mb-2">${mode === 'chore' ? 'Chore Summary' : 'Meal Summary'}</h3>
      <dl class="divide-y divide-gray-200">
        ${fields.map(([k, v]) => `
          <div class="py-2 flex justify-between">
            <dt class="font-medium text-gray-600">${k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</dt>
            <dd class="text-gray-900">${Array.isArray(v) ? v.join(', ') : v}</dd>
          </div>
        `).join('')}
      </dl>
    </div>
  `;
}

function renderStageCard(content, stage) {
  // Use different accent colors for each stage
  let accent = '';
  if (stage === 'collecting_info') accent = 'border-blue-300 bg-blue-50';
  else if (stage === 'confirming_info') accent = 'border-yellow-300 bg-yellow-50';
  else if (stage === 'created') accent = 'border-green-400 bg-green-50';
  else accent = 'border-gray-200 bg-white';
  return `<div class="max-w-md mx-auto rounded-lg shadow p-6 border ${accent}">${content}</div>`;
}

function renderCollecting(missingFields, prompt) {
  let field = missingFields[0];
  if (mode === 'meal' && field === 'exist') {
    step({ exist: true });
    return;
  }
  let value = currentData[field] || "";
  const content = `
    <h2 class="text-xl font-semibold text-blue-700 mb-4">${mode === 'chore' ? 'Create Chore' : 'Plan Meal'}</h2>
    <form id="stepForm" class="space-y-4">
      ${renderField(field, mode, value)}
      <div class="flex gap-3 mt-4">
        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition" ${getDisabledAttrs(stepLoading)}>Next</button>
        <button type="button" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="cancelBtn" ${getDisabledAttrs(stepLoading)}>Cancel</button>
      </div>
    </form>
  `;
  app.innerHTML = renderStageCard(content, 'collecting_info');
  document.getElementById('stepForm').onsubmit = (e) => {
    e.preventDefault();
    let val = document.getElementById('fieldInput').value;
    let userInput = {};
    if (field === 'assigned_members') {
      userInput[field] = val.split(',').map(s => s.trim()).filter(Boolean);
    } else {
      userInput[field] = val;
    }
    step(userInput);
  };
  document.getElementById('cancelBtn').onclick = () => {
    stepLoading = false;
    stepError = '';
    renderMenu();
  };
}

function renderConfirming(summary, prompt) {
  const content = `
    ${renderSummaryCard(summary, mode)}
    <p class="mb-4 text-gray-700">${prompt}</p>
    <div class="flex gap-3">
      <button id="doneBtn" class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition" ${getDisabledAttrs(stepLoading)}>Confirm</button>
      <button id="editBtn" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" ${getDisabledAttrs(stepLoading)}>Edit</button>
      <button id="cancelBtn" class="px-4 py-2 bg-gray-200 text-gray-700 rounded shadow hover:bg-gray-400 transition" ${getDisabledAttrs(stepLoading)}>Cancel</button>
    </div>
  `;
  app.innerHTML = renderStageCard(content, 'confirming_info');
  document.getElementById('doneBtn').onclick = () => step(null, true);
  document.getElementById('editBtn').onclick = () => editLastStep(summary);
  document.getElementById('cancelBtn').onclick = () => {
    stepLoading = false;
    stepError = '';
    renderMenu();
  };
}

function editLastStep(summary) {
  // List of editable fields for each mode
  const choreFields = [
    "chore_name", "assigned_members", "repetition", "start_date", "end_date", "due_time", "reminder", "type"
  ];
  const mealFields = [
    "meal_name", "meal_kind", "meal_date", "dishes"
  ];
  const fields = mode === 'chore' ? choreFields : mealFields;

  // Helper for reminder select
  function renderReminderField(value) {
    const options = [
      { label: "None", value: "" },
      { label: "10 min before", value: "10min before" },
      { label: "1 hour before", value: "1h before" },
      { label: "1 day before", value: "1d before" },
      { label: "Custom...", value: "custom" }
    ];
    let isCustom = value && !options.some(opt => opt.value === value);
    return `
      <label class="block mb-2 font-medium">Reminder
        <select id="edit_reminder" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
          ${options.map(opt => `<option value="${opt.value}"${isCustom && opt.value === 'custom' ? ' selected' : value === opt.value ? ' selected' : ''}>${opt.label}</option>`).join('')}
        </select>
        <input id="edit_reminder_custom" class="mt-2 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" placeholder="Custom reminder..." value="${isCustom ? value : ''}" style="display:${isCustom ? 'block' : 'none'}" />
      </label>
    `;
  }

  // Helper for time fields
  function renderTimeField(id, label, value) {
    return `<label class="block mb-2 font-medium">${label}
      <input id="${id}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="time" value="${value || ''}" />
    </label>`;
  }

  // Render a form with all fields pre-filled
  let repetition = currentData['repetition'] || 'daily';
  const content = `
    <h2 class="text-xl font-semibold text-yellow-700 mb-4">Edit ${mode === 'chore' ? 'Chore' : 'Meal'}</h2>
    <form id="editForm" class="space-y-4">
      ${fields.map(field => {
        let value = currentData[field] || "";
        if ((field === 'assigned_members' || field === 'dishes') && Array.isArray(value)) {
          value = value.join(', ');
        }
        if (field === "chore_name" || field === "meal_name") {
          return `<label class="block mb-2 font-medium">${mode === 'chore' ? 'Chore Name' : 'Meal Name'}
            <input id="edit_${field}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" placeholder="Enter name..." />
          </label>`;
        }
        if (field === "assigned_members") {
          return `<label class="block mb-2 font-medium">Assigned Members
            <input id="edit_${field}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" placeholder="Comma-separated names (e.g. Alex, Jamie)" />
          </label>`;
        }
        if (field === "repetition") {
          return `<label class="block mb-2 font-medium">Repetition
            <select id="edit_repetition" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
              <option value="daily"${value === 'daily' ? ' selected' : ''}>Daily</option>
              <option value="weekly"${value === 'weekly' ? ' selected' : ''}>Weekly</option>
              <option value="one-time"${value === 'one-time' ? ' selected' : ''}>One-time</option>
            </select>
          </label>`;
        }
        // Dynamic date/time fields for chores
        if (mode === 'chore') {
          if (field === "start_date" && repetition !== 'one-time') {
            return `<label class="block mb-2 font-medium">Start Date
              <input id="edit_start_date" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="date" value="${value}" />
            </label>`;
          }
          if (field === "end_date" && (repetition === 'daily' || repetition === 'weekly')) {
            return `<label class="block mb-2 font-medium">End Date (optional)
              <input id="edit_end_date" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="date" value="${value}" />
            </label>`;
          }
          if (field === "start_date" && repetition === 'one-time') {
            return `<label class="block mb-2 font-medium">Date
              <input id="edit_start_date" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="date" value="${value}" />
            </label>`;
          }
          if (field === "due_time" && repetition === 'one-time') {
            return renderTimeField('edit_due_time', 'Time', value);
          }
          if (field === "due_time" && (repetition === 'daily' || repetition === 'weekly')) {
            return renderTimeField('edit_due_time', 'Due Time', value);
          }
        }
        if (field === "meal_kind") {
          return `<label class="block mb-2 font-medium">Meal Kind
            <select id="edit_${field}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
              <option value="breakfast"${value === 'breakfast' ? ' selected' : ''}>Breakfast</option>
              <option value="lunch"${value === 'lunch' ? ' selected' : ''}>Lunch</option>
              <option value="dinner"${value === 'dinner' ? ' selected' : ''}>Dinner</option>
              <option value="snack"${value === 'snack' ? ' selected' : ''}>Snack</option>
            </select>
          </label>`;
        }
        if (field === "dishes") {
          return `<label class="block mb-2 font-medium">Dishes
            <input id="edit_${field}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" type="text" value="${value}" placeholder="Comma-separated dishes (e.g. Salad, Soup)" />
          </label>`;
        }
        if (field === "reminder") {
          return renderReminderField(value);
        }
        if (field === "type") {
          return `<label class="block mb-2 font-medium">Task Type
            <select id="edit_${field}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">
              <option value="individual"${value === 'individual' ? ' selected' : ''}>Individual</option>
              <option value="rotate"${value === 'rotate' ? ' selected' : ''}>Rotate</option>
              <option value="compete"${value === 'compete' ? ' selected' : ''}>Compete</option>
            </select>
          </label>`;
        }
        // fallback
        return '';
      }).join('')}
      <div class="flex gap-3 mt-4">
        <button type="submit" class="px-4 py-2 bg-yellow-600 text-white rounded shadow hover:bg-yellow-700 transition">Save Changes</button>
        <button type="button" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="cancelEditBtn">Cancel</button>
      </div>
    </form>
  `;
  app.innerHTML = renderStageCard(content, 'confirming_info');

  // Reminder custom field logic
  const reminderSelect = document.getElementById('edit_reminder');
  if (reminderSelect) {
    reminderSelect.addEventListener('change', (e) => {
      const customInput = document.getElementById('edit_reminder_custom');
      if (e.target.value === 'custom') {
        customInput.style.display = 'block';
        customInput.focus();
      } else {
        customInput.style.display = 'none';
      }
    });
  }

  // Repetition logic for dynamic fields
  const repetitionSelect = document.getElementById('edit_repetition');
  if (repetitionSelect) {
    repetitionSelect.addEventListener('change', (e) => {
      currentData['repetition'] = e.target.value;
      editLastStep(summary); // re-render with new repetition
    });
  }

  document.getElementById('editForm').onsubmit = (e) => {
    e.preventDefault();
    // Gather all field values
    const newData = { ...currentData };
    fields.forEach(field => {
      if (field === 'reminder') {
        const sel = document.getElementById('edit_reminder');
        const custom = document.getElementById('edit_reminder_custom');
        if (sel.value === 'custom') {
          newData.reminder = custom.value;
        } else {
          newData.reminder = sel.value;
        }
        return;
      }
      if (field === 'repetition') {
        newData.repetition = document.getElementById('edit_repetition').value;
        return;
      }
      let val = document.getElementById(`edit_${field}`)?.value;
      if (val !== undefined) {
        if (field === 'assigned_members' || field === 'dishes') {
          newData[field] = val.split(',').map(s => s.trim()).filter(Boolean);
        } else {
          newData[field] = val;
        }
      }
    });
    currentData = newData;
    // Re-render confirmation with updated data
    renderConfirming(currentData, 'Please confirm your changes.');
  };
  document.getElementById('cancelEditBtn').onclick = () => renderConfirming(currentData, 'No changes made. Please confirm or edit.');
}

function renderCreated(message, id) {
  const content = `
    <div class="flex flex-col items-center">
      <div class="mb-4">
        <svg class="w-16 h-16 text-green-500 mx-auto" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2l4-4m5 2a9 9 0 11-18 0a9 9 0 0118 0z"/></svg>
      </div>
      <h2 class="text-2xl font-bold text-green-700 mb-2">Success!</h2>
      <p class="text-green-800 font-medium mb-2">${message}</p>
      <p class="text-gray-700 mb-4">ID: <span class="font-mono text-base text-gray-900">${id}</span></p>
      <div class="flex gap-3">
        <button id="viewListBtn" class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition">View All ${mode === 'chore' ? 'Chores' : 'Meals'}</button>
        <button id="backBtn" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition">Back to Menu</button>
      </div>
    </div>
  `;
  app.innerHTML = renderStageCard(content, 'created');
  document.getElementById('viewListBtn').onclick = () => fetchAndShowList(mode);
  document.getElementById('backBtn').onclick = renderMenu;
}

async function fetchAndShowList(listMode) {
  stepLoading = false;
  stepError = '';
  const endpoint = listMode === 'chore' ? '/chores' : '/meals';
  const res = await fetch(`http://localhost:8000${endpoint}`);
  const data = await res.json();
  app.innerHTML = `
    <h2 class="text-xl font-semibold text-blue-700 mb-4">All ${listMode === 'chore' ? 'Chores' : 'Meals'}</h2>
    ${renderTable(data, listMode === 'chore' ? 'chore' : 'meal')}
    <div class="mt-6 flex justify-center">
      <button class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="backBtn">Back to Menu</button>
    </div>
  `;
  document.getElementById('backBtn').onclick = renderMenu;
}

// Utility for rendering a button
function renderButton(text, onClick, extra = "") {
  return `<button class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition ${extra}" onclick="${onClick}">${text}</button>`;
}

// Utility for rendering an input
function renderInput(id, placeholder, value = "", type = "text") {
  return `<input id="${id}" type="${type}" placeholder="${placeholder}" value="${value}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2" />`;
}

// Utility for rendering a select
function renderSelect(id, options, value = "") {
  return `<select id="${id}" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-blue-500 focus:ring focus:ring-blue-200 focus:ring-opacity-50 px-3 py-2">${options.map(opt => `<option value="${opt}"${opt === value ? ' selected' : ''}>${opt}</option>`).join('')}</select>`;
}

// Utility for rendering a card
function renderCard(content) {
  return `<div class="bg-gray-100 rounded-lg p-4 shadow">${content}</div>`;
}

async function renderEditMembers() {
  stepLoading = false;
  stepError = '';
  // Fetch members from backend
  async function fetchMembers() {
    try {
      const res = await fetch('http://localhost:8000/members');
      if (!res.ok) throw new Error('Failed to fetch members');
      return await res.json();
    } catch (e) {
      throw new Error('Could not load family members.');
    }
  }

  let members = [];
  let stage = 'collecting_info';
  let editingId = null;
  let formData = { name: '', gender: '', avatar: '' };
  let confirmData = null;
  let message = '';
  let error = '';
  let loading = false;

  async function refreshMembers() {
    try {
      loading = true;
      renderPage();
      members = await fetchMembers();
      error = '';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
      renderPage();
    }
  }

  function renderErrorCard(msg) {
    return `<div class='bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4'>${msg}</div>`;
  }

  function renderLoading() {
    return `<div class='flex items-center justify-center py-8'><svg class='animate-spin h-8 w-8 text-pink-600' xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24'><circle class='opacity-25' cx='12' cy='12' r='10' stroke='currentColor' stroke-width='4'></circle><path class='opacity-75' fill='currentColor' d='M4 12a8 8 0 018-8v8z'></path></svg><span class='ml-3 text-pink-700 font-medium'>Loading...</span></div>`;
  }

  function renderMemberSummaryCard(member) {
    return `
      <div class="bg-gray-50 rounded-lg shadow p-4 mb-4">
        <h3 class="text-lg font-semibold text-pink-700 mb-2">Family Member</h3>
        <dl class="divide-y divide-gray-200">
          <div class="py-2 flex justify-between">
            <dt class="font-medium text-gray-600">Name</dt>
            <dd class="text-gray-900">${member.name}</dd>
          </div>
          <div class="py-2 flex justify-between">
            <dt class="font-medium text-gray-600">Gender</dt>
            <dd class="text-gray-900">${member.gender || ''}</dd>
          </div>
          <div class="py-2 flex justify-between">
            <dt class="font-medium text-gray-600">Avatar</dt>
            <dd class="text-gray-900"><img src="${member.avatar || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(member.name)}" class="w-10 h-10 rounded-full border inline" alt="avatar" /></dd>
          </div>
        </dl>
      </div>
    `;
  }

  function renderForm(editing = false) {
    return `
      <form id="memberForm" class="space-y-4 mb-6">
        <div class="flex gap-4">
          <input id="memberName" class="flex-1 px-3 py-2 rounded border border-gray-300 focus:border-blue-500" type="text" placeholder="Name" value="${formData.name}" required />
          <select id="memberGender" class="flex-1 px-3 py-2 rounded border border-gray-300 focus:border-blue-500">
            <option value="">Gender</option>
            <option value="male"${formData.gender === 'male' ? ' selected' : ''}>Male</option>
            <option value="female"${formData.gender === 'female' ? ' selected' : ''}>Female</option>
            <option value="other"${formData.gender === 'other' ? ' selected' : ''}>Other</option>
          </select>
        </div>
        <input id="memberAvatar" class="w-full px-3 py-2 rounded border border-gray-300 focus:border-blue-500" type="text" placeholder="Avatar URL (optional)" value="${formData.avatar}" />
        <div class="flex gap-3">
          <button type="submit" class="px-4 py-2 bg-pink-600 text-white rounded shadow hover:bg-pink-700 transition">${editing ? 'Next' : 'Add'}</button>
          <button type="button" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="cancelMemberBtn">Cancel</button>
        </div>
      </form>
    `;
  }

  function renderMembersList() {
    return `
      <div class="mb-6">
        <h2 class="text-lg font-semibold text-pink-700 mb-2">Family Members</h2>
        <div class="space-y-2">
          ${members.map(m => `
            <div class="flex items-center gap-3 bg-gray-50 rounded p-3 shadow">
              <img src="${m.avatar || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(m.name)}" class="w-10 h-10 rounded-full border" alt="avatar" />
              <div class="flex-1">
                <div class="font-medium">${m.name}</div>
                <div class="text-xs text-gray-500">${m.gender || ''}</div>
              </div>
              <button class="px-2 py-1 bg-yellow-400 text-white rounded hover:bg-yellow-500 transition" data-edit="${m.id}">Edit</button>
              <button class="px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600 transition" data-delete="${m.id}">Delete</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderStageCard(content, stage) {
    let accent = '';
    if (stage === 'collecting_info') accent = 'border-pink-300 bg-pink-50';
    else if (stage === 'confirming_info') accent = 'border-yellow-300 bg-yellow-50';
    else if (stage === 'created') accent = 'border-green-400 bg-green-50';
    else accent = 'border-gray-200 bg-white';
    return `<div class="max-w-lg mx-auto rounded-lg shadow p-6 border ${accent}">${content}</div>`;
  }

  function renderPage() {
    let content = '';
    let currentStage = stage;
    if (stage === 'collecting_info' && editingId) currentStage = 'confirming_info';
    if (loading) {
      content = renderLoading();
    } else if (error) {
      content = renderErrorCard(error) + `<button class='mt-4 px-4 py-2 bg-gray-400 text-white rounded' id='backToMenuBtn'>Back to Menu</button>`;
    } else if (stage === 'collecting_info') {
      content = `
        <button class="mb-4 px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition" id="backToMenuBtn">Back to Menu</button>
        <h2 class="text-lg font-semibold text-pink-700 mb-4">${editingId ? `Editing: ${formData.name}` : 'Add Family Member'}</h2>
        ${editingId ? renderMemberSummaryCard(formData) : ''}
        ${renderForm(!!editingId)}
        ${renderMembersList()}
      `;
    } else if (stage === 'confirming_info') {
      content = `
        <button class="mb-4 px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition" id="backToMenuBtn">Back to Menu</button>
        <h2 class="text-lg font-semibold text-yellow-700 mb-4">Confirm Changes</h2>
        ${renderMemberSummaryCard(confirmData)}
        <div class="flex gap-3 mt-4">
          <button id="confirmMemberBtn" class="px-4 py-2 bg-pink-600 text-white rounded shadow hover:bg-pink-700 transition">Confirm</button>
          <button id="editAgainBtn" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition">Edit</button>
          <button id="cancelMemberBtn" class="px-4 py-2 bg-gray-200 text-gray-700 rounded shadow hover:bg-gray-400 transition">Cancel</button>
        </div>
      `;
    } else if (stage === 'created') {
      content = `
        <div class="flex flex-col items-center">
          <div class="mb-4">
            <svg class="w-16 h-16 text-green-500 mx-auto" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2l4-4m5 2a9 9 0 11-18 0a9 9 0 0118 0z"/></svg>
          </div>
          <h2 class="text-2xl font-bold text-green-700 mb-2">Success!</h2>
          <p class="text-green-800 font-medium mb-2">${message}</p>
          <div class="flex gap-3 mt-4">
            <button id="backToMembersBtn" class="px-4 py-2 bg-pink-600 text-white rounded shadow hover:bg-pink-700 transition">Back to Family Members</button>
            <button id="backToMenuBtn" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition">Back to Menu</button>
          </div>
        </div>
      `;
    }
    app.innerHTML = renderStageCard(content, currentStage);

    // Button handlers
    if (document.getElementById('backToMenuBtn')) document.getElementById('backToMenuBtn').onclick = renderMenu;
    if (document.getElementById('backToMembersBtn')) document.getElementById('backToMembersBtn').onclick = () => { stage = 'collecting_info'; renderPage(); };
    if (document.getElementById('cancelMemberBtn')) document.getElementById('cancelMemberBtn').onclick = () => {
      editingId = null;
      formData = { name: '', gender: '', avatar: '' };
      stage = 'collecting_info';
      renderPage();
    };
    if (document.getElementById('editAgainBtn')) document.getElementById('editAgainBtn').onclick = () => { stage = 'collecting_info'; renderPage(); };
    if (document.getElementById('memberForm')) {
      document.getElementById('memberForm').onsubmit = (e) => {
        e.preventDefault();
        formData.name = document.getElementById('memberName').value;
        formData.gender = document.getElementById('memberGender').value;
        formData.avatar = document.getElementById('memberAvatar').value;
        confirmData = { ...formData };
        stage = 'confirming_info';
        renderPage();
      };
    }
    if (document.getElementById('confirmMemberBtn')) {
      document.getElementById('confirmMemberBtn').onclick = async () => {
        try {
          loading = true;
          renderPage();
          if (editingId) {
            await fetch(`http://localhost:8000/members/${editingId}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(confirmData)
            });
            message = 'Family member updated!';
          } else {
            await fetch('http://localhost:8000/members', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(confirmData)
            });
            message = 'Family member added!';
          }
          await refreshMembers();
          editingId = null;
          formData = { name: '', gender: '', avatar: '' };
          stage = 'created';
        } catch (e) {
          error = 'Failed to save family member.';
          stage = 'collecting_info';
        } finally {
          loading = false;
          renderPage();
        }
      };
    }
    // Edit and delete buttons
    document.querySelectorAll('[data-edit]').forEach(btn => {
      btn.onclick = () => {
        editingId = btn.getAttribute('data-edit');
        const member = members.find(m => m.id == editingId);
        formData = { name: member.name, gender: member.gender || '', avatar: member.avatar || '' };
        stage = 'collecting_info';
        renderPage();
      };
    });
    document.querySelectorAll('[data-delete]').forEach(btn => {
      btn.onclick = async () => {
        const id = btn.getAttribute('data-delete');
        if (confirm('Delete this member?')) {
          try {
            loading = true;
            renderPage();
            await fetch(`http://localhost:8000/members/${id}`, { method: 'DELETE' });
            await refreshMembers();
          } catch (e) {
            error = 'Failed to delete family member.';
          } finally {
            loading = false;
            renderPage();
          }
        }
      };
    });
  }

  // Initial load
  loading = true;
  renderPage();
  members = await fetchMembers();
  loading = false;
  renderPage();
}

// --- Chat UI Functions ---
function renderChatUI() {
  // Chat container, now stretches more
  const chatBox = `
    <div class="flex flex-col flex-1 w-full max-w-3xl mx-auto h-[70vh] min-h-[400px]">
      <h2 class="text-lg font-semibold text-gray-700 mb-2">🤖 Assistant Chat</h2>
      <div id="chatHistory" class="flex-1 bg-gray-100 rounded-lg p-4 overflow-y-auto mb-2 border border-gray-200">
        ${chatMessages.length === 0 ? '<div class="text-gray-400 text-center">No messages yet. Say hello!</div>' :
          chatMessages.map(m => `
            <div class="mb-2 flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}">
              <div class="max-w-xl px-3 py-2 rounded-lg shadow ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border text-gray-800'}">
                ${m.content}
              </div>
            </div>
          `).join('')
        }
        ${chatLoading ? '<div class="flex items-center gap-2 text-gray-500"><svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path></svg> Assistant is typing...</div>' : ''}
      </div>
      <form id="chatForm" class="flex gap-2">
        <input id="chatInput" class="flex-1 px-3 py-2 rounded border border-gray-300 focus:border-blue-500" type="text" placeholder="Type your message..." autocomplete="off" ${chatLoading ? 'disabled' : ''} />
        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition" ${chatLoading ? 'disabled' : ''}>Send</button>
      </form>
      ${chatError ? `<div class='text-red-600 mt-2'>${chatError}</div>` : ''}
    </div>
  `;
  return chatBox;
}

function scrollChatToBottom() {
  setTimeout(() => {
    const el = document.getElementById('chatHistory');
    if (el) el.scrollTop = el.scrollHeight;
  }, 50);
}

function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg || chatLoading) return;
  input.value = '';
  chatMessages.push({ role: 'user', content: msg });
  chatLoading = true;
  chatError = '';
  renderMenu();
  scrollChatToBottom();
  // Send to backend
  fetch('http://localhost:8000/chat/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  })
    .then(res => res.json())
    .then(data => {
      if (data && data.reply) {
        chatMessages.push({ role: 'bot', content: data.reply });
      } else {
        chatMessages.push({ role: 'bot', content: 'Sorry, I did not understand that.' });
      }
      chatLoading = false;
      renderMenu();
      scrollChatToBottom();
    })
    .catch(err => {
      chatError = 'Error contacting assistant.';
      chatLoading = false;
      renderMenu();
    });
}

// Initial render
renderMenu();
