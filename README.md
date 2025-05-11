# Demo 1

## Description from Boss

### completing the order action through dialogue:

1. It is necessary to collect order information in a dialogue (voice or text). The way to collect information in a dialogue conforms to the way of human communication, which may be one sentence or multiple rounds. The purpose of the dialogue is to help the user choose the goods, the number of goods, the receiving address, the recipient's information, and the receiving time.

2. After the user selects a product, call tools or function call to check if the product is in stock and its price, and let the user confirm the total price of the order (the unit price of the product + the quantity of the product; if the product is out of stock or the user cancels, terminate and wait for the next conversation)

3. After the second confirmation is completed, continue to let the user confirm the recipient information of the goods, the receiving address, the receiving time, and the user confirms that the user is prompted to choose the payment method
After the user completes the payment, call tools or function call to complete the order action

## Plan

### 1. Define the Dialogue Flow
- Use **pyagent** to orchestrate the conversation and manage dialogue state.
- The agent will:
  1. Greet the user and start the order process.
  2. Collect product selection and quantity using LLM-powered natural language understanding (DeepSeek).
  3. Call tools/functions to check product stock and price.
  4. Confirm order summary (product, quantity, total price) with the user.
  5. Collect recipient info, address, and delivery time.
  6. Confirm all details with the user.
  7. Present payment method options.
  8. Simulate payment and complete the order.
- **Tools/Modules:**
  - [pyagent](https://github.com/pyagent-ai/pyagent) for agentic dialogue management
  - [DeepSeek LLM](https://deepseek.com/) (or other LLM) for language understanding and response generation

### 2. Design Data Structures
- Product catalog (list/dict with name, stock, price).
- Order object (product, quantity, recipient info, address, time, payment method).
- **Tools/Modules:**
  - Python built-in types: `dict`, `list`, `dataclasses.dataclass`
  - For more complex data: [pydantic](https://pydantic-docs.helpmanual.io/) for data validation

### 3. Implement Dialogue Management
- Use **pyagent** to manage conversation state and multi-turn dialogue.
- Route all user input through pyagent and DeepSeek LLM for intent extraction and slot filling.
- **Tools/Modules:**
  - [pyagent](https://github.com/pyagent-ai/pyagent)
  - [DeepSeek LLM](https://deepseek.com/) API

### 4. Implement Product Check Functions
- Implement product lookup, stock check, and price check as pyagent tools/functions.
- The agent will call these tools as needed based on LLM output.
- **Tools/Modules:**
  - Python functions
  - pyagent tool interface
  - For real inventory: Connect to a database (e.g., `sqlite3`, [SQLAlchemy](https://www.sqlalchemy.org/))

### 5. Order Confirmation and Payment
- After collecting all info, show a summary and ask for confirmation (via LLM response).
- Simulate payment as a pyagent tool/function.
- **Tools/Modules:**
  - pyagent tool for payment simulation
  - For real payment: Integrate with payment APIs (e.g., [Stripe](https://stripe.com/docs/api), [PayPal](https://developer.paypal.com/docs/api/overview/))

### 6. Error Handling and Cancellation
- Handle cases where product is out of stock or user cancels using agent logic.
- Allow user to restart or exit at any point.
- **Tools/Modules:**
  - pyagent error handling and state management
  - Python: `try/except`, custom exceptions
  - Logging: `logging` module

### 7. User Interface
- For demo, use text-based CLI (input/output in terminal), routing all input/output through pyagent and the LLM.
- Optionally, structure code to allow easy extension to voice or web UI.
- **Tools/Modules:**
  - CLI: `input()`, `print()`
  - For voice: [SpeechRecognition](https://pypi.org/project/SpeechRecognition/), [pyttsx3](https://pypi.org/project/pyttsx3/) for TTS
  - For web: [Flask](https://flask.palletsprojects.com/), [FastAPI](https://fastapi.tiangolo.com/)

### 8. Testing
- Prepare a few test scenarios (happy path, out-of-stock, user cancels, etc.).
- **Tools/Modules:**
  - [unittest](https://docs.python.org/3/library/unittest.html), [pytest](https://docs.pytest.org/en/stable/)
  - For CLI automation: [pexpect](https://pexpect.readthedocs.io/en/stable/)

---

#### Example File Structure

- `main.py` — Starts the CLI, initializes pyagent with DeepSeek LLM.
- `tools.py` — Implements product lookup, order, and payment as pyagent tools.
- `config.py` — Stores API keys and configuration for DeepSeek and pyagent.

