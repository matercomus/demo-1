import pytest
import os

TEST_DB = "test_products.db"

@pytest.fixture(autouse=True, scope="function")
def clean_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

from agent import MockAgent
from models import Order, Product, OrderInput
from tools import ProductTool, ProductDB, OrderDB
from utils.ui import TerminalUI
from pydantic import ValidationError

class MockUI(TerminalUI):
    def __init__(self, inputs):
        self.inputs = iter(inputs)
        self.outputs = []
    def prompt(self, message: str) -> str:
        return next(self.inputs)
    def prompt_int(self, message: str, min_value: int = 1, max_value: int = 1000) -> int:
        return int(next(self.inputs))
    def prompt_yes_no(self, message: str) -> bool:
        return next(self.inputs).lower() in ("y", "yes")
    def print_success(self, message: str):
        self.outputs.append(message)
    def print_error(self, message: str):
        self.outputs.append(message)
    def print_order_summary(self, order: Order):
        self.outputs.append(f"Order: {order.product.name} x{order.quantity}")
    def print_products(self, products):
        pass
    def print_section(self, title: str):
        pass
    def print_welcome(self):
        pass
    def print_goodbye(self):
        pass

class _TestMockUI(MockUI):
    def prompt(self, message: str) -> str:
        try:
            return next(self.inputs)
        except StopIteration:
            # Always return a valid value for any prompt if inputs are exhausted
            if "email" in message.lower():
                return "test@example.com"
            if "phone" in message.lower():
                return "1234567890"
            if "name" in message.lower():
                return "Test User"
            if "address" in message.lower():
                return "123 Main St"
            if "delivery time" in message.lower():
                return "Tomorrow"
            if "payment" in message.lower():
                return "card"
            return "test"

# Pydantic validation tests
def test_orderinput_valid():
    data = dict(
        name="Alice",
        phone="+1 234-567-8901",
        email="alice@example.com",
        address="123 Main St",
        delivery_time="Tomorrow",
        payment_method="card"
    )
    model = OrderInput(**data)
    assert model.name == "Alice"
    assert model.phone == "+1 234-567-8901"
    assert model.email == "alice@example.com"

@pytest.mark.parametrize("field,value,error", [
    ("name", "", "cannot be empty"),
    ("address", "", "cannot be empty"),
    ("delivery_time", "", "cannot be empty"),
    ("payment_method", "", "cannot be empty"),
    ("phone", "123", "at least 7 digits"),
    ("phone", "abc1234567", "can only contain numbers, spaces, dashes, or plus sign"),
    ("email", "notanemail", "value is not a valid email address"),
])
def test_orderinput_invalid(field, value, error):
    data = dict(
        name="Alice",
        phone="+1 234-567-8901",
        email="alice@example.com",
        address="123 Main St",
        delivery_time="Tomorrow",
        payment_method="card"
    )
    data[field] = value
    with pytest.raises(ValidationError) as exc:
        OrderInput(**data)
    assert error in str(exc.value)

def test_orderinput_multiple_invalid():
    data = dict(
        name="",
        phone="12",
        email="bademail",
        address="",
        delivery_time="",
        payment_method=""
    )
    with pytest.raises(ValidationError) as exc:
        OrderInput(**data)
    msg = str(exc.value)
    assert "name" in msg and "cannot be empty" in msg
    assert "phone" in msg and "at least 7 digits" in msg
    assert "email" in msg and "valid email address" in msg
    assert "address" in msg and "cannot be empty" in msg
    assert "delivery_time" in msg and "cannot be empty" in msg
    assert "payment_method" in msg and "cannot be empty" in msg

# Agent flow tests
def test_happy_path():
    # Select product 1, quantity 2, confirm, then all valid fields
    inputs = [
        "1", "2", "y", "Alice", "+1 234-567-8901", "alice@example.com", "123 Main St", "Tomorrow", "card"
    ]
    ui = MockUI(inputs)
    agent = MockAgent(ui=ui, db_path=TEST_DB)
    agent.start_order()
    assert any("Order completed successfully" in o for o in ui.outputs)
    assert any("Order: Widget x2" in o for o in ui.outputs)

def test_out_of_stock():
    # Select product 3 (out of stock), quantity 1
    inputs = ["3", "1"]
    ui = MockUI(inputs)
    agent = MockAgent(ui=ui, db_path=TEST_DB)
    agent.start_order()
    assert any("Not enough stock" in o for o in ui.outputs)

def test_agent_invalid_email_then_valid():
    # Select product 1, quantity 1, confirm, then multiple invalid emails, then valid
    inputs = [
        "1", "1", "y", "Bob", "1234567", "notanemail", "also@not", "bob@example.com", "Somewhere", "Soon", "cash"
    ]
    ui = _TestMockUI(inputs)
    agent = MockAgent(ui=ui, db_path=TEST_DB)
    agent.start_order()
    # Should see Pydantic error for invalid email, then success
    assert any("value is not a valid email address" in o for o in ui.outputs)
    assert any("Order completed successfully" in o for o in ui.outputs)

def test_order_persistence_and_stock():
    # Place an order and check DB for order and stock update
    inputs = ["1", "2", "y", "Alice", "+1 234-567-8901", "alice@example.com", "123 Main St", "Tomorrow", "card"]
    ui = MockUI(inputs)
    agent = MockAgent(ui=ui, db_path=TEST_DB)
    agent.start_order()
    # Check DB
    engine = agent.product_tool.engine
    Session = agent.product_tool.Session
    session = Session()
    # Check order exists
    orders = session.query(OrderDB).all()
    assert len(orders) == 1
    order = orders[0]
    assert order.product_name == "Widget"
    assert order.quantity == 2
    # Check stock decremented
    product = session.query(ProductDB).filter_by(name="Widget").first()
    assert product.stock == 8
    session.close() 