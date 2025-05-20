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

// Set the backend API base URL
const API_BASE = 'http://localhost:8000';

// --- Global pendingConfirmation getter/setter ---
function getPendingConfirmation() {
  if (typeof window !== 'undefined') return window.pendingConfirmation;
  if (typeof globalThis !== 'undefined') return globalThis.pendingConfirmation;
  return null;
}
function setPendingConfirmation(val) {
  if (typeof window !== 'undefined') window.pendingConfirmation = val;
  else if (typeof globalThis !== 'undefined') globalThis.pendingConfirmation = val;
}

// Initialize global pendingConfirmation if not set
if (typeof window !== 'undefined' && typeof window.pendingConfirmation === 'undefined') {
  window.pendingConfirmation = null;
} else if (typeof globalThis !== 'undefined' && typeof globalThis.pendingConfirmation === 'undefined') {
  globalThis.pendingConfirmation = null;
}

if (typeof window !== 'undefined' && !window.marked) {
  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
  script.onload = () => { window.marked = window.marked || marked; };
  document.head.appendChild(script);
}

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
      <button class="px-4 py-2 bg-yellow-600 text-white rounded shadow hover:bg-yellow-700 transition" id="viewRecipesBtn">View Recipes</button>
      <button class="px-4 py-2 bg-pink-600 text-white rounded shadow hover:bg-pink-700 transition" id="editMembersBtn">Edit Family Members</button>
      <button class="px-4 py-2 bg-orange-600 text-white rounded shadow hover:bg-orange-700 transition" id="createRecipeBtn">Create Recipe</button>
    </div>
  `;
  document.getElementById('choreBtn').onclick = () => startFlow('chore');
  document.getElementById('mealBtn').onclick = () => startFlow('meal');
  document.getElementById('viewChoresBtn').onclick = () => fetchAndShowList('chore');
  document.getElementById('viewMealsBtn').onclick = () => fetchAndShowList('meal');
  document.getElementById('viewRecipesBtn').onclick = () => fetchAndShowList('recipe');
  document.getElementById('editMembersBtn').onclick = renderEditMembers;
  document.getElementById('createRecipeBtn').onclick = renderCreateRecipe;
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

// Patch step to store lastStepData for suggestions
let step = async function(userInput = null, confirm = false) {
  const endpoint = mode === 'chore' ? '/chore/step' : '/meal/step';
  const payload = { current_data: currentData };
  if (userInput) payload.user_input = userInput;
  if (confirm) payload.confirm = true;
  stepLoading = true;
  stepError = '';
  renderStepStage();
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to communicate with server.');
    const data = await res.json();
    window.lastStepData = data;
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
};

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

function renderStageCard(content, stage, stepInfo = null) {
  // Use different accent colors and icons for each stage
  let accent = '', icon = '', border = '', progress = '';
  if (stage === 'collecting_info') {
    accent = 'border-blue-300 bg-blue-50';
    icon = '📝';
    border = 'border-blue-400';
    if (stepInfo) {
      progress = `<div class="mb-2 text-xs text-blue-700 font-semibold">Step ${stepInfo.current} of ${stepInfo.total}</div>`;
    }
  } else if (stage === 'confirming_info') {
    accent = 'border-yellow-300 bg-yellow-50';
    icon = '✅';
    border = 'border-yellow-400';
    if (stepInfo) {
      progress = `<div class="mb-2 text-xs text-yellow-700 font-semibold">Confirmation</div>`;
    }
  } else if (stage === 'confirming_removal') {
    accent = 'border-red-200 bg-red-50';
    icon = '🗑️';
    border = 'border-red-400';
    progress = `<div class="mb-2 text-xs text-red-700 font-semibold">Confirm Removal</div>`;
  } else if (stage === 'created') {
    accent = 'border-green-400 bg-green-50';
    icon = '🎉';
    border = 'border-green-500';
    progress = `<div class="mb-2 text-xs text-green-700 font-semibold">Success</div>`;
  } else if (stage === 'greeting') {
    accent = 'border-blue-200 bg-blue-50';
    icon = '👋';
    border = 'border-blue-300';
  } else if (stage === 'error') {
    accent = 'border-red-200 bg-red-50';
    icon = '❌';
    border = 'border-red-400';
  } else if (stage === 'other') {
    accent = 'border-gray-200 bg-white';
    icon = '💬';
    border = 'border-gray-300';
  } else {
    accent = 'border-gray-200 bg-white';
    icon = '';
    border = 'border-gray-300';
  }
  // Fade-in animation
  return `<div class="max-w-md mx-auto rounded-lg shadow p-6 border ${accent} ${border} animate-fadein" style="animation: fadein 0.5s;">
    ${icon ? `<div class="text-3xl mb-2">${icon}</div>` : ''}
    ${progress}
    ${content}
  </div>`;
}

// Add fade-in animation CSS
const style = document.createElement('style');
style.innerHTML = `@keyframes fadein { from { opacity: 0; transform: translateY(20px);} to { opacity: 1; transform: none; } }
.animate-fadein { animation: fadein 0.5s; }`;
document.head.appendChild(style);

function renderCollecting(missingFields, prompt) {
  let field = missingFields[0];
  if (mode === 'meal' && field === 'exist' && window.lastStepData && window.lastStepData.suggested_recipes) {
    // Show recipe suggestions
    const suggestions = window.lastStepData.suggested_recipes;
    let suggestionHtml = '';
    if (suggestions.length > 0) {
      suggestionHtml = `
        <div class="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded">
          <div class="font-semibold text-yellow-800 mb-2">Did you mean one of these recipes?</div>
          <ul class="space-y-2">
            ${suggestions.map((r, i) => `
              <li>
                <button class="px-3 py-2 bg-yellow-200 hover:bg-yellow-300 rounded w-full text-left" data-suggest="${i}">
                  <span class="font-bold">${r.name}</span> <span class="text-xs text-gray-600">(${r.kind})</span><br/>
                  <span class="text-gray-700">${r.description || ''}</span>
                </button>
              </li>
            `).join('')}
          </ul>
          <button class="mt-3 px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded w-full" id="noRecipeMatchBtn">None of these</button>
        </div>
      `;
    }
    app.innerHTML = renderStageCard(`
      <h2 class="text-xl font-semibold text-green-700 mb-4">Plan Meal</h2>
      <div class="mb-2">${prompt}</div>
      ${suggestionHtml}
      <form id="stepForm" class="space-y-4">
        ${renderField(field, mode, currentData[field] || "")}
        <div class="flex gap-3 mt-4">
          <button type="submit" class="px-4 py-2 bg-green-600 text-white rounded shadow hover:bg-green-700 transition" ${getDisabledAttrs(stepLoading)}>Next</button>
          <button type="button" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="cancelBtn" ${getDisabledAttrs(stepLoading)}>Cancel</button>
        </div>
      </form>
    `, 'collecting_info');
    // Suggestion click handlers
    suggestions.forEach((r, i) => {
      const btn = document.querySelector(`[data-suggest="${i}"]`);
      if (btn) btn.onclick = () => {
        currentData.meal_name = r.name;
        currentData.exist = true;
        step({ exist: true });
      };
    });
    const noBtn = document.getElementById('noRecipeMatchBtn');
    if (noBtn) noBtn.onclick = () => {
      currentData.exist = false;
      step({ exist: false });
    };
    document.getElementById('stepForm').onsubmit = (e) => {
      e.preventDefault();
      let val = document.getElementById('fieldInput').value;
      let userInput = {};
      userInput[field] = val;
      step(userInput);
    };
    document.getElementById('cancelBtn').onclick = () => {
      stepLoading = false;
      stepError = '';
      renderMenu();
    };
    return;
  }
  // fallback to default
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
  let endpoint, label;
  if (listMode === 'chore') {
    endpoint = '/chores';
    label = 'Chores';
  } else if (listMode === 'meal') {
    endpoint = '/meals';
    label = 'Meals';
  } else if (listMode === 'recipe') {
    endpoint = '/recipes';
    label = 'Recipes';
  }
  const res = await fetch(`${API_BASE}${endpoint}`);
  const data = await res.json();
  app.innerHTML = `
    <h2 class="text-xl font-semibold text-blue-700 mb-4">All ${label}</h2>
    ${renderTable(data, label.toLowerCase())}
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
      const res = await fetch(`${API_BASE}/members`);
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
            await fetch(`${API_BASE}/members/${editingId}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(confirmData)
            });
            message = 'Family member updated!';
          } else {
            await fetch(`${API_BASE}/members`, {
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
            await fetch(`${API_BASE}/members/${id}`, { method: 'DELETE' });
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
          chatMessages.map(m => {
            if (m.role === 'bot') {
              // Use the stage field for card styling
              if (m.stage && m.stage !== 'unknown') {
                // Special style for destructive confirmation
                if (m.stage === 'confirming_removal') {
                  return `<div class="mb-4 w-full flex justify-start"><div class="w-full">${renderStageCard(`<span class='font-bold text-red-700'>${window.marked ? window.marked.parse(m.content) : m.content}</span><div class='mt-2 text-sm text-red-600'>Please type <b>yes</b> to confirm or <b>no</b> to cancel.</div>`, 'confirming_removal', null)}</div></div>`;
                }
                return `<div class="mb-4 w-full flex justify-start">${renderChatBotMessage(m.content, m.stage, true)}</div>`;
              }
              // Otherwise, render as a normal bubble
              return `<div class="mb-2 flex justify-start">${renderChatBotMessage(m.content, m.stage, false)}</div>`;
            } else {
              // User message
              return `<div class="mb-2 flex justify-end"><div class="max-w-xl px-3 py-2 rounded-lg shadow bg-blue-600 text-white">${m.content}</div></div>`;
            }
          }).join('')
        }
        ${chatLoading ? '<div class="flex items-center gap-2 text-gray-500"><svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path></svg> Assistant is typing...</div>' : ''}
      </div>
      <form id="chatForm" class="flex gap-2">
        <input id="chatInput" class="flex-1 px-3 py-2 rounded border border-gray-300 focus:border-blue-500" type="text" placeholder="Type your message..." autocomplete="off" ${chatLoading ? 'disabled' : ''} ${(getPendingConfirmation() ? '' : '')} />
        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700 transition" ${chatLoading ? 'disabled' : ''}>Send</button>
      </form>
      ${getPendingConfirmation() ? `<div class='text-red-600 mt-2'>Please type <b>yes</b> to confirm or <b>no</b> to cancel.</div>` : ''}
      ${chatError ? `<div class='text-red-600 mt-2'>${chatError}</div>` : ''}
    </div>
  `;
  return chatBox;
}

function renderChatBotMessage(content, stage = null, fullWidth = false) {
  // Only use the stage for card styling, no badge
  if (stage && stage !== 'unknown') {
    return `<div class="${fullWidth ? 'w-full' : 'max-w-xl'}">${renderStageCard(window.marked ? window.marked.parse(content) : content, stage, null)}</div>`;
  }
  // Fallback: normal chat bubble
  return `<div class="max-w-xl px-3 py-2 rounded-lg shadow bg-white border text-gray-800">${window.marked ? window.marked.parse(content) : content}</div>`;
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

  // Step: Handle destructive confirmation with confirmation_id
  if (getPendingConfirmation()) {
    if (/^yes$/i.test(msg)) {
      chatMessages.push({ role: 'user', content: msg });
      chatLoading = true;
      chatError = '';
      renderMenu();
      scrollChatToBottom();
      fetch(`${API_BASE}/confirm_action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmation_id: getPendingConfirmation().confirmation_id,
          confirm: true
        })
      })
        .then(res => res.json())
        .then(data => {
          if (typeof data === 'string') {
            try { data = JSON.parse(data); } catch (e) {}
          }
          if (data && data.message) {
            chatMessages.push({ role: 'bot', content: data.message, stage: data.stage });
          } else {
            chatMessages.push({ role: 'bot', content: 'Sorry, I did not understand that.', stage: 'error' });
          }
          chatLoading = false;
          setPendingConfirmation(null);
          renderMenu();
          scrollChatToBottom();
        })
        .catch(err => {
          chatError = 'Error contacting assistant.';
          chatLoading = false;
          setPendingConfirmation(null);
          renderMenu();
        });
      return;
    } else if (/^no$/i.test(msg)) {
      chatMessages.push({ role: 'user', content: msg });
      chatMessages.push({ role: 'bot', content: 'Deletion cancelled.', stage: 'other' });
      setPendingConfirmation(null);
      renderMenu();
      scrollChatToBottom();
      return;
    } else {
      chatMessages.push({ role: 'user', content: msg });
      chatMessages.push({ role: 'bot', content: 'Please type "yes" to confirm or "no" to cancel.', stage: 'confirming_removal', destructive: true });
      renderMenu();
      scrollChatToBottom();
      return;
    }
  }

  chatMessages.push({ role: 'user', content: msg });
  chatLoading = true;
  chatError = '';
  renderMenu();
  scrollChatToBottom();
  fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: msg,
      message_history: chatMessages.map(m => ({
        role: m.role === 'bot' ? 'assistant' : m.role,
        content: m.content
      }))
    })
  })
    .then(res => res.json())
    .then(data => {
      if (typeof data === 'string') {
        try {
          data = JSON.parse(data);
        } catch (e) {
          console.error('Failed to parse data:', data);
        }
      }
      // If backend returns confirmation-required, store confirmation_id and show prompt
      if (data && data.reply && typeof data.reply === 'object' && data.reply.stage === 'confirming_removal' && data.reply.confirmation_id) {
        setPendingConfirmation(data.reply);
        chatMessages.push({ role: 'bot', content: data.reply.message, stage: 'confirming_removal', destructive: true });
        chatLoading = false;
        renderMenu();
        scrollChatToBottom();
        return;
      }
      if (data && data.reply) {
        chatMessages.push({ role: 'bot', content: typeof data.reply === 'string' ? data.reply : data.reply.message, stage: data.stage });
      } else {
        chatMessages.push({ role: 'bot', content: 'Sorry, I did not understand that.', stage: 'error' });
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

function renderCreateRecipe() {
  app.innerHTML = `
    <div class="max-w-md mx-auto rounded-lg shadow p-6 border border-yellow-300 bg-yellow-50">
      <h2 class="text-xl font-semibold text-yellow-700 mb-4">Create Recipe</h2>
      <form id="createRecipeForm" class="space-y-4">
        <label class="block mb-2 font-medium">Name
          <input id="recipeName" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-200 focus:ring-opacity-50 px-3 py-2" type="text" placeholder="Recipe name..." required />
        </label>
        <label class="block mb-2 font-medium">Kind
          <select id="recipeKind" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-200 focus:ring-opacity-50 px-3 py-2">
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="dinner">Dinner</option>
            <option value="snack">Snack</option>
          </select>
        </label>
        <label class="block mb-2 font-medium">Description
          <textarea id="recipeDescription" class="mt-1 block w-full rounded border-gray-300 shadow-sm focus:border-yellow-500 focus:ring focus:ring-yellow-200 focus:ring-opacity-50 px-3 py-2" placeholder="Description..."></textarea>
        </label>
        <div class="flex gap-3 mt-4">
          <button type="submit" class="px-4 py-2 bg-yellow-600 text-white rounded shadow hover:bg-yellow-700 transition">Create</button>
          <button type="button" class="px-4 py-2 bg-gray-400 text-white rounded shadow hover:bg-gray-600 transition" id="cancelBtn">Cancel</button>
        </div>
      </form>
    </div>
  `;
  document.getElementById('createRecipeForm').onsubmit = async (e) => {
    e.preventDefault();
    const name = document.getElementById('recipeName').value;
    const kind = document.getElementById('recipeKind').value;
    const description = document.getElementById('recipeDescription').value;
    const res = await fetch(`${API_BASE}/recipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, kind, description })
    });
    if (res.ok) {
      fetchAndShowList('recipe');
    } else {
      alert('Failed to create recipe.');
    }
  };
  document.getElementById('cancelBtn').onclick = renderMenu;
}

// Initial render
renderMenu();

// Only export for Node.js (e.g., for Jest tests)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    handleChatSubmit,
    chatMessages,
    renderMenu,
    get pendingRemoval() {
      return (typeof window !== 'undefined') ? window.pendingRemoval : globalThis.pendingRemoval;
    },
    set pendingRemoval(val) {
      if (typeof window !== 'undefined') window.pendingRemoval = val;
      else if (typeof globalThis !== 'undefined') globalThis.pendingRemoval = val;
    },
    get pendingConfirmation() {
      return getPendingConfirmation();
    },
    set pendingConfirmation(val) {
      setPendingConfirmation(val);
    },
  };
}
