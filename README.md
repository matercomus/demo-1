[![Pytest](https://github.com/matercomus/demo-1/actions/workflows/pytest.yml/badge.svg?branch=master)](https://github.com/matercomus/demo-1/actions/workflows/pytest.yml)

# Demo 1 — Conversational Order System

## Overview

Demo 1 is a conversational order system that lets users place, review, and cancel product orders through a natural, multi-turn dialogue in the terminal. The system uses an LLM-powered agent (via [pydantic-ai](https://github.com/pydantic-ai/pydantic-ai)) to guide users through product selection, recipient info, delivery details, and payment, all in a human-like conversation.

- Place orders for products in stock
- Confirm order details and recipient info
- Choose payment method and complete the order
- View and cancel any order by ID
- All data is persisted in a local SQLite database

## Getting Started

### 1. Clone the repository

```bash
git clone git@github.com:matercomus/demo-1.git
cd demo-1
```

### 2. Python Version

This project requires **Python >=3.8**.

### 3. Install dependencies & Run (with uv)

#### Option A: Using [uv](https://github.com/astral-sh/uv) (recommended)

If you have [uv](https://github.com/astral-sh/uv) installed, you can run the project directly—no need to manually create or activate a virtual environment:

```bash
uv run python main.py
```

Or, to specify an agent:

```bash
uv run python main.py --agent mock
uv run python main.py --agent pydantic
uv run python main.py --agent llm
```

uv will automatically create a virtual environment and install dependencies as needed.

#### Option B: Using pip

If you prefer classic pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> You may need to install additional dependencies if you use LLMs or other features.

### 4. Set up your `.env` file

Create a `.env` file in the project root (this file is ignored by git):

```
# LLM model to use (default: openai:gpt-4o)
OPENAI_MODEL=openai:gpt-4o
# If using OpenAI or other providers, you may also need:
# OPENAI_API_KEY=sk-...
```

### 5. Using the System

- Follow the prompts to select products, enter recipient and delivery info, and confirm your order.
- You can view all orders, and cancel any order by its ID.
- To exit, follow the prompts or press `Ctrl+C` or `Ctrl+D` (EOF).

## Project Structure

- `main.py` — Starts the CLI and agent.
- `agents/` — Agent implementations (LLM, mock, pydantic).
- `tools.py` — Product/order persistence and payment simulation.
- `models.py` — Data models and validation.
- `utils/ui.py` — Terminal UI logic.
- `tests/` — Automated tests (run with `pytest`).

## Testing

To run all tests:

```bash
pytest
```

---

**Enjoy your conversational ordering experience!**  
For questions or contributions, please open an issue or pull request.

