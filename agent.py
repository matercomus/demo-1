from models import Order, Product, RecipientInfo
from tools import ProductTool, PaymentTool, OrdersTool
from utils.ui import TerminalUI
from typing import Optional
from pydantic import ValidationError
from models import OrderInput

class MockAgent:
    """
    Mock agent for development and testing. Controlled by developer input.
    Can be replaced by an LLM agent with the same interface.
    """
    def __init__(self, ui: TerminalUI, db_path: str = 'products.db'):
        self.ui = ui
        self.product_tool = ProductTool(db_path=db_path)
        self.payment_tool = PaymentTool()
        self.orders_tool = OrdersTool(self.product_tool.engine)

    def start_order(self):
        self.ui.print_section('Start New Order')
        order = Order()
        # 1. Product selection
        order.product = self._select_product()
        if not order.product:
            self.ui.print_error('Order cancelled.')
            return
        # 2. Quantity
        order.quantity = self.ui.prompt_int('Enter quantity:', min_value=1)
        # 3. Check stock and price
        if not self.product_tool.check_stock(order.product, order.quantity):
            self.ui.print_error('Not enough stock. Order cancelled.')
            return
        order.unit_price = self.product_tool.get_price(order.product)
        order.total_price = order.unit_price * order.quantity
        # 4. Confirm order summary
        if not self.ui.prompt_yes_no(f'Confirm order: {order.product.name} x{order.quantity} for ${order.total_price:.2f}?'):
            self.ui.print_error('Order cancelled.')
            return
        # 5-8. Collect all user input and validate with Pydantic
        fields = ['name', 'phone', 'email', 'address', 'delivery_time', 'payment_method']
        data = {f: '' for f in fields}
        while True:
            for f in fields:
                if not data[f]:
                    data[f] = self.ui.prompt(f.replace('_', ' ').capitalize() + ':')
            try:
                validated = OrderInput(**data)
                break
            except ValidationError as e:
                for err in e.errors():
                    field = err['loc'][0]
                    self.ui.print_error(f"{field.replace('_', ' ').capitalize()}: {err['msg']}")
                    data[field] = ''  # re-prompt this field
        # Fill order
        order.recipient_info = RecipientInfo(name=validated.name, phone=validated.phone, email=validated.email)
        order.address = validated.address
        order.delivery_time = validated.delivery_time
        payment_method = validated.payment_method
        if not self.payment_tool.process_payment(order, payment_method):
            self.ui.print_error('Payment failed. Order cancelled.')
            return
        # Update DB: decrement stock and save order
        self.orders_tool.decrement_stock(order.product.id, order.quantity)
        self.orders_tool.save_order(order, payment_method)
        self.ui.print_success('Order completed successfully!')
        self.ui.print_order_summary(order)

    def _select_product(self) -> Optional[Product]:
        products = self.product_tool.list_products()
        self.ui.print_products(products)
        idx = self.ui.prompt_int('Select product by number (0 to cancel):', min_value=0, max_value=len(products))
        if idx == 0:
            return None
        return products[idx-1]

    def _collect_recipient_info(self) -> RecipientInfo:
        # No longer used, but kept for interface compatibility if needed
        pass 