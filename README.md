# Demo 1

## Description from Boss

### completing the order action through dialogue:

1. It is necessary to collect order information in a dialogue (voice or text). The way to collect information in a dialogue conforms to the way of human communication, which may be one sentence or multiple rounds. The purpose of the dialogue is to help the user choose the goods, the number of goods, the receiving address, the recipient's information, and the receiving time.

2. After the user selects a product, call tools or function call to check if the product is in stock and its price, and let the user confirm the total price of the order (the unit price of the product + the quantity of the product; if the product is out of stock or the user cancels, terminate and wait for the next conversation)

3. After the second confirmation is completed, continue to let the user confirm the recipient information of the goods, the receiving address, the receiving time, and the user confirms that the user is prompted to choose the payment method
After the user completes the payment, call tools or function call to complete the order action

## Plan

### 1. Define the Dialogue Flow
- Use **pydantic-ai** for agentic dialogue management and input validation.
- The agent will:
  1. Greet the user and start the order process.
  2. Collect product selection and quantity using structured prompts.
  3. Check product stock and price.
  4. Confirm order summary (product, quantity, total price) with the user.
  5. Collect recipient info, address, and delivery time.
  6. Confirm all details with the user.
  7. Present payment method options.
  8. Simulate payment and complete the order.
- **Tools/Modules:**
  - [pydantic-ai](https://github.com/pydantic-ai/pydantic-ai) for dialogue management and validation
  - Python functions and control flow for orchestration

### 2. Design Data Structures
- Product catalog (list/dict with name, stock, price).
- Order object (product, quantity, recipient info, address, time, payment method).
- **Tools/Modules:**
  - Python built-in types: `dict`, `list`, `dataclasses.dataclass`
  - [pydantic](https://pydantic-docs.helpmanual.io/) for data validation
  - SQLAlchemy models for persistent storage

### 3. Implement Dialogue Management
- Use **pydantic-ai** to manage conversation state and multi-turn dialogue.
- Route all user input through pydantic-ai for intent extraction and slot filling.
- **Tools/Modules:**
  - [pydantic-ai](https://github.com/pydantic-ai/pydantic-ai)

### 4. Implement Product and Order Persistence
- Implement product lookup, stock check, and price check using SQLAlchemy.
- Save orders and update product stock in the database.
- **Tools/Modules:**
  - SQLAlchemy for database operations
  - Python functions for business logic

### 5. Order Confirmation and Payment
- After collecting all info, show a summary and ask for confirmation (via pydantic-ai response).
- Simulate payment as a function.
- **Tools/Modules:**
  - Python functions for payment simulation
  - For real payment: Integrate with payment APIs if needed

### 6. Error Handling and Cancellation
- Handle cases where product is out of stock or user cancels using agent logic.
- Allow user to restart or exit at any point.
- **Tools/Modules:**
  - Python: `try/except`, custom exceptions
  - Logging: `logging` module

### 7. User Interface
- For demo, use text-based CLI (input/output in terminal), routing all input/output through the agent and pydantic-ai.
- Optionally, structure code to allow easy extension to voice or web UI.
- **Tools/Modules:**
  - CLI: `input()`, `print()`
  - For voice: [SpeechRecognition](https://pypi.org/project/SpeechRecognition/), [pyttsx3](https://pypi.org/project/pyttsx3/) for TTS
  - For web: [Flask](https://flask.palletsprojects.com/), [FastAPI](https://fastapi.tiangolo.com/)

### 8. Testing
- Prepare a few test scenarios (happy path, out-of-stock, user cancels, DB operations, etc.).
- **Tools/Modules:**
  - [pytest](https://docs.pytest.org/en/stable/)
  - For CLI automation: [pexpect](https://pexpect.readthedocs.io/en/stable/)
  - SQLAlchemy for DB assertions

---

#### Example File Structure

- `main.py` — Starts the CLI, initializes the agent with pydantic-ai.
- `tools.py` — Implements product and order persistence, payment simulation.
- `models.py` — Pydantic models for validation and SQLAlchemy models for persistence.
- `utils/ui.py` — Terminal UI logic.
- `tests/` — Pytest-based tests for all flows and DB operations.

