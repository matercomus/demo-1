const app = document.getElementById('app');

let mode = null; // 'chore' or 'meal'
let stage = null;
let currentData = {};

function renderMenu() {
  app.innerHTML = `
    <h1>Smart Household Assistant</h1>
    <button id="choreBtn">Create Chore</button>
    <button id="mealBtn">Plan Meal</button>
    <button id="viewChoresBtn">View All Chores</button>
    <button id="viewMealsBtn">View All Meals</button>
  `;
  document.getElementById('choreBtn').onclick = () => startFlow('chore');
  document.getElementById('mealBtn').onclick = () => startFlow('meal');
  document.getElementById('viewChoresBtn').onclick = () => fetchAndShowList('chore');
  document.getElementById('viewMealsBtn').onclick = () => fetchAndShowList('meal');
}

function startFlow(selectedMode) {
  mode = selectedMode;
  stage = null;
  currentData = {};
  step();
}

async function step(userInput = null, confirm = false) {
  const endpoint = mode === 'chore' ? '/chore/step' : '/meal/step';
  const payload = { current_data: currentData };
  if (userInput) payload.user_input = userInput;
  if (confirm) payload.confirm = true;

  const res = await fetch(`http://localhost:8000${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  stage = data.stage;

  if (stage === 'collecting_info') {
    currentData = data.current_data;
    renderCollecting(data.prompt);
  } else if (stage === 'confirming_info') {
    currentData = { ...currentData, ...data.summary };
    renderConfirming(data.summary, data.prompt);
  } else if (stage === 'created') {
    renderCreated(data.message, data.id);
  } else {
    app.innerHTML = `<p>Error: ${data.message || 'Unknown error'}</p>`;
  }
}

function renderCollecting(prompt) {
  app.innerHTML = `
    <h2>${mode === 'chore' ? 'Create Chore' : 'Plan Meal'}</h2>
    <p>${prompt}${prompt.toLowerCase().includes('exist') ? ' (yes/no or true/false)' : ''}</p>
    <input id="userInput" type="text" autofocus />
    <button id="nextBtn">Next</button>
    <button id="backBtn">Back to Menu</button>
  `;
  document.getElementById('nextBtn').onclick = () => {
    const val = document.getElementById('userInput').value;
    if (!val) return;
    // Try to guess the field being asked for
    let field = prompt.toLowerCase().includes('name') ? (mode === 'chore' ? 'chore_name' : 'meal_name') :
                prompt.toLowerCase().includes('member') ? 'assigned_members' :
                prompt.toLowerCase().includes('start') ? 'start_date' :
                prompt.toLowerCase().includes('repeat') ? 'repetition' :
                prompt.toLowerCase().includes('kind') ? 'meal_kind' :
                prompt.toLowerCase().includes('date') ? (mode === 'chore' ? 'start_date' : 'meal_date') :
                prompt.toLowerCase().includes('exist') ? 'exist' :
                null;
    let userInput = {};
    if (field === 'assigned_members') {
      userInput[field] = val.split(',').map(s => s.trim());
    } else if (field === 'exist') {
      const v = val.trim().toLowerCase();
      userInput[field] = (v === 'true' || v === 'yes' || v === 'y');
    } else {
      userInput[field] = val;
    }
    step(userInput);
  };
  document.getElementById('backBtn').onclick = renderMenu;
}

function renderConfirming(summary, prompt) {
  app.innerHTML = `
    <h2>Confirm ${mode === 'chore' ? 'Chore' : 'Meal'}</h2>
    <pre>${JSON.stringify(summary, null, 2)}</pre>
    <p>${prompt}</p>
    <button id="doneBtn">Done</button>
    <button id="backBtn">Back to Menu</button>
  `;
  document.getElementById('doneBtn').onclick = () => step(null, true);
  document.getElementById('backBtn').onclick = renderMenu;
}

function renderCreated(message, id) {
  app.innerHTML = `
    <h2>Success!</h2>
    <p>${message}</p>
    <p>ID: ${id}</p>
    <button id="viewListBtn">View All ${mode === 'chore' ? 'Chores' : 'Meals'}</button>
    <button id="backBtn">Back to Menu</button>
  `;
  document.getElementById('viewListBtn').onclick = () => fetchAndShowList(mode);
  document.getElementById('backBtn').onclick = renderMenu;
}

async function fetchAndShowList(listMode) {
  const endpoint = listMode === 'chore' ? '/chores' : '/meals';
  const res = await fetch(`http://localhost:8000${endpoint}`);
  const data = await res.json();
  app.innerHTML = `
    <h2>All ${listMode === 'chore' ? 'Chores' : 'Meals'}</h2>
    <pre>${JSON.stringify(data, null, 2)}</pre>
    <button id="backBtn">Back to Menu</button>
  `;
  document.getElementById('backBtn').onclick = renderMenu;
}

// Initial render
renderMenu();
