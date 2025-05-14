[![Pytest](https://github.com/matercomus/demo-1/actions/workflows/pytest.yml/badge.svg?branch=master)](https://github.com/matercomus/demo-1/actions/workflows/pytest.yml)

# Demo 2 — Smart Household Assistant (Chore & Meal Management)

## Overview

Demo 2 is a modular, API-driven household assistant that helps users manage chores and meal planning for their family. The system uses natural language (text or voice) to collect, confirm, and create tasks, with a clear separation between backend (FastAPI) and frontend (simple web UI). The assistant infers as much as possible from user input, asks for missing info, and guides the user through confirmation and creation stages.

---

## Project Implementation Checklist

### Backend
- [x] Chore, Meal, and FamilyMember models, schemas, and CRUD
- [x] Stage-based conversational endpoints (`/chore/step`, `/meal/step`)
- [x] Robust test suite
- [ ] Fuzzy recipe matching for meals
- [ ] Reminders for chores (optional)
- [ ] Logging improvements (reminders/fuzzy matching)
- [ ] API for recipes (for fuzzy matching)

### Frontend
- [x] Minimal HTML/JS frontend
- [ ] UI for fuzzy meal matching and recipe suggestions
- [ ] UI for reminders (if implemented)
- [ ] UI polish and error handling

### Extensibility & Polish
- [ ] Robust error handling and user feedback
- [ ] Document API endpoints and flows in README
- [ ] (Optional) Add voice input support

---

## Features

- **Chore Management**
  - Add, review, and assign chores to family members
  - Support for individual, rotate, and compete task types
  - Repetition (daily, weekly, one-time)
  - Reminders (optional)
  - Multi-turn dialogue to fill missing info
  - Chore summary and confirmation before saving
- **Meal Planning**
  - Add meals for specific dates and times
  - Fuzzy matching against a recipe database
  - Create custom meals if not found
  - Plan multiple dishes for a meal (e.g., Thanksgiving dinner)
  - Meal summary and confirmation before saving
- **Family Member Management**
  - Add/view family members (name, gender, avatar)
- **Stage-based API**
  - Every API response includes a `stage` field: `collecting_info`, `confirming_info`, or `created`
  - Frontend adapts UI based on the current stage
- **Separation of Concerns**
  - FastAPI backend for business logic and persistence
  - Simple frontend (React, Vue, or plain JS) for user interaction

---

## System Architecture

```
[User] <-> [Frontend UI] <-> [FastAPI Backend] <-> [SQLite DB]
```

- **Backend:** FastAPI, Pydantic models, SQLite (or other DB)
- **Frontend:** Simple web app (React, Vue, or HTML/JS)
- **API:** JSON-based, stateless or session-based

---

## Project Structure (V2)

```
project-root/
  backend/           # FastAPI app, models, routers, services, etc.
    main.py
    models.py
    database.py
    routers/
    services/
    schemas/
    utils/
    tests/
  frontend/          # Simple web UI (React, Vue, or HTML/JS)
    src/
    public/
    ...
  .github/
  .vscode/
  .env
  .gitignore
  LICENSE
  pyproject.toml
  requirements.txt
  README.md
```

- **backend/**: All backend logic, API, and business rules for chores, meals, and members.
- **frontend/**: All frontend code for the user interface, communicating with the backend via API.

---

## Data Models

### Chore
- `chore_name` (str, required)
- `icon` (str, auto-selected)
- `assigned_members` (list[str], required)
- `start_date` (date, default: today)
- `end_date` (date, optional)
- `due_time` (str, default: 23:59)
- `repetition` (str: daily, weekly, one-time, inferred)
- `reminder` (str or bool, default: off)
- `type` (str: individual, rotate, compete; required if multiple members)

### Meal
- `meal_name` (str, required)
- `exist` (bool, inferred via fuzzy match)
- `meal_kind` (str: breakfast, lunch, dinner, snack, required)
- `meal_date` (date, required)
- `dishes` (list[str], for multi-dish meals)

### Family Member
- `name` (str, required)
- `gender` (str: male, female, other)
- `avatar` (str, image URL)

### Recipe (for fuzzy matching)
- `name` (str)
- `kind` (str)
- `description` (str)

---

## API Design

### Chore Flow
- `POST /chore` — Start a new chore creation session
- `POST /chore/step` — Submit user input, get next stage and prompt
- `GET /chore/{id}` — Retrieve a saved chore

### Meal Flow
- `POST /meal` — Start a new meal planning session
- `POST /meal/step` — Submit user input, get next stage and prompt
- `GET /meal/{id}` — Retrieve a saved meal

### Family/Recipe
- `GET /members` — List family members
- `GET /recipes` — List/search recipes (for fuzzy matching)

#### API Response Schema (for all flows)
```json
{
  "stage": "collecting_info" | "confirming_info" | "created",
  "prompt": "string", // What to display to the user
  "missing_fields": ["field1", "field2"], // If collecting info
  "current_data": { ... }, // Collected so far
  "summary": { ... }, // If confirming
  "message": "string", // If created
  "id": 123 // If created
}
```

---

## Dialogue & Stage Flow

### 1. Information Collection (`collecting_info`)
- System infers as much as possible from user input
- Asks follow-up questions for missing required fields
- For meals, performs fuzzy matching and asks for clarification if needed
- Example prompt: "Who should do this task?"

### 2. Information Confirmation (`confirming_info`)
- System presents a summary of all collected info
- User can confirm or request edits
- Example summary:
  - 🧺 Laundry
  - 👤 Alex, Jamie (rotating)
  - 📅 Starts April 22, repeats daily
  - 🕒 Due by 11:59 PM
  - 🔄 Task type: Rotate
  - 🔕 No reminder
- Example prompt: "If everything looks good, please type Done to confirm."

### 3. Information Creation (`created`)
- On confirmation, system saves the chore/meal
- Returns a success message and ID
- Example: "Awesome! Your new chore has been saved."

---

## Frontend Requirements

- **Stage-aware UI:**
  - Show input forms for `collecting_info`
  - Show summary/confirmation card for `confirming_info`
  - Show success message for `created`
- **API Communication:**
  - Use `fetch`/`axios` to call FastAPI endpoints
  - Pass user input and session info as needed
- **Minimal Design:**
  - Responsive, clear indication of current stage
  - Support for both text and (optionally) voice input

---

## Example Flows (from ai功能需求模型.md)

### Chore Example
```
User: I want to set up a laundry task starting tomorrow.
AI: Got it! Creating a "Laundry" task. I'll choose an icon automatically.
AI: Who should do this task? (Please select one or more members)
(User selects members)
AI: Should this be an individual task, a competition, or should the members take turns?
(User selects "rotate")
AI: Great! Here's the chore summary:
🧺 Laundry
👤 Alex, Jamie (rotating)
📅 Starts April 22, repeats daily
🕒 Due by 11:59 PM
🔄 Task type: Rotate
🔕 No reminder
👉 If everything looks good, please type Done to confirm.
(User: Done)
AI: Awesome! Your new chore has been saved.
```

### Meal Example
```
User: Hi Cozy. I am hungry.
AI: Hi there! I'm happy to help. What would you like to eat?
User: Guacamole.
AI: Got it. When would you like to have it?
User: Next Monday at noon.
AI: Understood! I've scheduled it for lunch next Monday. Would you like to confirm this meal?
User: Confirm.
AI: Awesome! Enjoy your meal!
```

---

## Implementation Notes

- **State Management:** Use session IDs or pass all state in each request
- **Fuzzy Matching:** For meals, use a recipe database and suggest close matches
- **Extensibility:** Easy to add new task types, properties, or flows
- **Testing:** Write tests for all flows and edge cases
- **Documentation:** Keep this file updated as the source of truth

---

## Development Checklist

- [ ] Design and implement data models (Pydantic, DB)
- [ ] Implement FastAPI endpoints for all flows
- [ ] Implement fuzzy matching for meals
- [ ] Build a simple, stage-aware frontend
- [ ] Write tests for all major flows
- [ ] Update documentation as needed

---

## Development & Running

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and running scripts. **Always use `uv run` to ensure the correct environment is used.**

### Install dependencies

```
uv pip install -r requirements.txt
```

### Running tests

```
uv run pytest
```

### Running the FastAPI app

If your entrypoint is `backend/main.py`:

```
uv run python -m backend.main
```

Or, to run with Uvicorn (recommended for FastAPI):

```
uv run uvicorn backend.main:app --reload
```

- Do **not** activate `.venv` or use `python` directly; always use `uv run ...` for scripts and tests.
- The `uv.lock` file ensures reproducible environments.

---

**Enjoy building your smart household assistant!**  
For questions or contributions, please open an issue or pull request.

