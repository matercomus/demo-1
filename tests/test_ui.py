import pytest
from utils.ui import TerminalUI
from models import Product, Order, RecipientInfo

def make_order():
    product = Product(id=1, name="Widget", price=9.99, stock=5)
    recipient = RecipientInfo(name="Alice", phone="1234567890", email="alice@example.com")
    return Order(
        product=product,
        quantity=2,
        unit_price=9.99,
        total_price=19.98,
        recipient_info=recipient,
        address="123 Main St",
        delivery_time="Tomorrow 10am"
    )

def test_print_pending_order_summary(capsys):
    ui = TerminalUI()
    order = make_order()
    ui.print_pending_order_summary(order)
    out = capsys.readouterr().out
    assert "Pending Order" in out
    assert "Not yet confirmed" in out
    assert "Widget" in out
    assert "Alice" in out

def test_print_confirmed_order(capsys):
    ui = TerminalUI()
    order = make_order()
    ui.print_confirmed_order(order)
    out = capsys.readouterr().out
    assert "Order Placed Successfully" in out
    assert "Thank you for your order" in out
    assert "Widget" in out
    assert "Alice" in out

def test_print_cancel_confirmation(capsys):
    ui = TerminalUI()
    ui.print_cancel_confirmation(42)
    out = capsys.readouterr().out
    assert "Are you sure you want to cancel order" in out
    assert "42" in out

def test_print_cancelled_order(capsys):
    ui = TerminalUI()
    ui.print_cancelled_order(99)
    out = capsys.readouterr().out
    assert "has been cancelled" in out
    assert "99" in out 