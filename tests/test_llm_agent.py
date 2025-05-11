import pytest
from agents.llm_agent import LLMAgent, OrderService
from models import OrderInput
from tools import ProductTool, PaymentTool, OrdersTool
from utils.ui import TerminalUI
import os
import tempfile
import asyncio
from unittest.mock import patch

class FakeRunContext:
    def __init__(self, deps):
        self.deps = deps

@pytest.fixture
def agent_and_service(tmp_path):
    db_path = str(tmp_path / "test_products.db")
    ui = TerminalUI()
    agent = LLMAgent(ui=ui, db_path=db_path)
    return agent, agent.order_service

def test_place_order_and_show_orders(agent_and_service):
    agent, service = agent_and_service
    # Place an order
    result = asyncio.run(agent.place_order(
        FakeRunContext(service),
        product_name="Widget",
        quantity=1,
        name="Test User",
        phone="123456789",
        email="test@example.com",
        address="123 Test St",
        delivery_time="tomorrow 10am",
        payment_method="card"
    ))
    assert "Order placed successfully" in result
    # Show orders
    orders = asyncio.run(agent.show_orders(FakeRunContext(service)))
    assert "Widget" in orders

def test_cancel_order(agent_and_service):
    agent, service = agent_and_service
    # Place an order
    asyncio.run(agent.place_order(
        FakeRunContext(service),
        product_name="Widget",
        quantity=1,
        name="Test User",
        phone="123456789",
        email="test@example.com",
        address="123 Test St",
        delivery_time="tomorrow 10am",
        payment_method="card"
    ))
    # Set last_order_id to the last order's ID
    last_order = service.orders_tool.show_orders()[-1]
    agent.last_order_id = last_order['id']
    # Cancel the order
    result = asyncio.run(agent.cancel_order(FakeRunContext(service)))
    assert "Order cancelled" in result

def test_stop_chat(agent_and_service):
    agent, service = agent_and_service
    result = asyncio.run(agent.stop_chat(FakeRunContext(service)))
    assert "Conversation ended" in result

def test_llm_agent_instantiates(tmp_path):
    ui = TerminalUI()
    agent = LLMAgent(ui=ui, db_path=str(tmp_path / "products.db"))
    assert agent is not None

def test_stop_chat_tool_called(agent_and_service):
    agent, service = agent_and_service
    with patch.object(agent, 'stop_chat', wraps=agent.stop_chat) as mock_stop_chat:
        result = asyncio.run(agent.stop_chat(FakeRunContext(service)))
        mock_stop_chat.assert_called_once()
        assert "Conversation ended" in result 