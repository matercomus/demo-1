import pytest
from agents.llm_agent import LLMAgent, OrderService
from models import OrderInput
from tools import ProductTool, PaymentTool, OrdersTool
from utils.ui import TerminalUI
import os
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

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
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
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

def test_place_order_requires_confirmation(agent_and_service):
    agent, service = agent_and_service
    with patch.object(service.ui, 'prompt_yes_no', return_value=False):
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
        assert "not confirmed" in result
        # No order should be placed
        orders = service.orders_tool.show_orders()
        assert len(orders) == 0
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
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
        orders = service.orders_tool.show_orders()
        assert len(orders) == 1

def test_cancel_order(agent_and_service):
    agent, service = agent_and_service
    # Place an order
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
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
        # Cancel the order (now requires order_id)
        result = asyncio.run(agent.cancel_order(FakeRunContext(service), order_id=last_order['id']))
        assert "cancelled" in result

def test_cancel_order_requires_confirmation(agent_and_service):
    agent, service = agent_and_service
    # Place an order first
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
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
    last_order = service.orders_tool.show_orders()[-1]
    order_id = last_order['id']
    # Decline cancellation
    with patch.object(service.ui, 'prompt_yes_no', return_value=False):
        result = asyncio.run(agent.cancel_order(FakeRunContext(service), order_id=order_id))
        assert "aborted" in result
        # Order should still exist
        orders = service.orders_tool.show_orders()
        assert any(o['id'] == order_id for o in orders)
    # Accept cancellation
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
        result = asyncio.run(agent.cancel_order(FakeRunContext(service), order_id=order_id))
        assert "cancelled" in result
        orders = service.orders_tool.show_orders()
        assert not any(o['id'] == order_id for o in orders)

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

def test_cancel_specific_order(agent_and_service):
    agent, service = agent_and_service
    # Place two orders
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
        asyncio.run(agent.place_order(
            FakeRunContext(service),
            product_name="Widget",
            quantity=1,
            name="User1",
            phone="111",
            email="user1@example.com",
            address="Addr1",
            delivery_time="soon",
            payment_method="card"
        ))
        asyncio.run(agent.place_order(
            FakeRunContext(service),
            product_name="Widget",
            quantity=1,
            name="User2",
            phone="222",
            email="user2@example.com",
            address="Addr2",
            delivery_time="later",
            payment_method="card"
        ))
        orders = service.orders_tool.show_orders()
        assert len(orders) == 2
        # Cancel the first order by ID
        first_order_id = orders[0]['id']
        result = asyncio.run(agent.cancel_order(FakeRunContext(service), order_id=first_order_id))
        assert f"Order {first_order_id} cancelled" in result
        # Only one order should remain, and it should not be the cancelled one
        remaining_orders = service.orders_tool.show_orders()
        assert len(remaining_orders) == 1
        assert remaining_orders[0]['id'] != first_order_id

def test_cancel_nonexistent_order(agent_and_service):
    agent, service = agent_and_service
    # Try to cancel an order with a high, non-existent ID
    with patch.object(service.ui, 'prompt_yes_no', return_value=True):
        result = asyncio.run(agent.cancel_order(FakeRunContext(service), order_id=9999))
        assert "not found" in result 