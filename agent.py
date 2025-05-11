from models import Order, Product, RecipientInfo
from tools import ProductTool, PaymentTool, OrdersTool
from utils.ui import TerminalUI
from typing import Optional, Protocol
from pydantic import ValidationError
from models import OrderInput
import json
import re
from pydantic_ai import capture_run_messages

class BaseAgent(Protocol):
    def start_order(self):
        ...

class MockAgent(BaseAgent):
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

# --- PydanticAIAgent ---
class PydanticAIAgent(BaseAgent):
    def __init__(self, ui: TerminalUI, db_path: str = 'products.db'):
        self.ui = ui
        self.product_tool = ProductTool(db_path=db_path)
        self.payment_tool = PaymentTool()
        self.orders_tool = OrdersTool(self.product_tool.engine)

    def start_order(self):
        self.ui.print_section('Start New Order (pydantic-ai)')
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
        # 5-8. Use pydantic-ai Dialogue for input collection and validation
        class OrderDialogue:
            name: str
            phone: str
            email: str
            address: str
            delivery_time: str
            payment_method: str

        dialogue = OrderDialogue()
        for field in dialogue.__annotations__:
            value = self.ui.prompt(f"{field.replace('_', ' ').capitalize()}: ")
            setattr(dialogue, field, value)
        validated = dialogue.__dict__
        # Fill order
        order.recipient_info = RecipientInfo(name=validated['name'], phone=validated['phone'], email=validated['email'])
        order.address = validated['address']
        order.delivery_time = validated['delivery_time']
        payment_method = validated['payment_method']
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

# --- LLMAgent ---
import os
from dotenv import load_dotenv
from pydantic_ai import Agent as PydanticAIAgentBase

class LLMAgent(BaseAgent):
    def __init__(self, ui: TerminalUI, db_path: str = 'products.db'):
        load_dotenv()
        self.ui = ui
        self.product_tool = ProductTool(db_path=db_path)
        self.payment_tool = PaymentTool()
        self.orders_tool = OrdersTool(self.product_tool.engine)
        # Custom output validator for robust logging and JSON extraction
        def output_validator(data):
            try:
                # If already a dict or OrderInput, just return
                if isinstance(data, dict):
                    return data
                if hasattr(data, 'model_dump'):
                    return data
                # Try to parse as JSON directly
                return json.loads(data)
            except Exception as e:
                # Try to extract JSON substring
                self.ui.print_error(f"[LLM][Validator] Failed to parse output as JSON: {e}")
                self.ui.print_error(f"[LLM][Validator] Raw output: {data}")
                match = re.search(r'\{.*\}', str(data), re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except Exception as e2:
                        self.ui.print_error(f"[LLM][Validator] Failed to parse extracted JSON: {e2}")
                        self.ui.print_error(f"[LLM][Validator] Extracted: {match.group(0)}")
                raise
        self.llm_agent = PydanticAIAgentBase(
            model=os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            output_type=OrderInput,
            instructions=(
                "You are an order assistant. Collect the following fields from the user as a JSON object: "
                "name, phone, email, address, delivery_time, payment_method. "
                "Ask for each field in a natural, conversational way. "
                "When all fields are collected, output ONLY a valid JSON object with these keys. "
                "Example: {\"name\": \"John Doe\", \"phone\": \"123-456-7890\", \"email\": \"john@example.com\", \"address\": \"123 Main St\", \"delivery_time\": \"tomorrow 10am\", \"payment_method\": \"card\"} "
                "Respond ONLY with a JSON object, no extra text. If you include anything else, the order will fail."
            ),
            output_retries=5
        )
        self.llm_agent.output_validator(output_validator)

    def start_order(self):
        self.ui.print_section('Start New Order (LLM-powered)')
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
        # 5-8. Use LLM agent for recipient info, address, delivery time, payment method
        user_prompt = (
            f"Product: {order.product.name}\n"
            f"Quantity: {order.quantity}\n"
            f"Total price: ${order.total_price:.2f}\n"
            "Please provide the recipient information, address, delivery time, and payment method."
        )
        self.ui.print_info("[LLM] Sending prompt to LLM agent...")
        self.ui.print_info(f"[LLM] Prompt: {user_prompt}")
        result = None
        try:
            result = self.llm_agent.run_sync(user_prompt)
            self.ui.print_info(f"[LLM] Raw result object: {result}")
            validated = result.output
            self.ui.print_success("[LLM] Received valid response from LLM agent.")
            self.ui.print_info(f"[LLM] Raw output: {validated}")
        except Exception as e:
            self.ui.print_error(f'[LLM] LLM agent error: {e}')
            if result is not None:
                self.ui.print_error(f"[LLM] Raw result object: {result}")
                if hasattr(result, 'output'):
                    self.ui.print_error(f"[LLM] Raw LLM output: {getattr(result, 'output', None)}")
            # Print all agent run messages for debugging
            self.ui.print_info("[LLM] Capturing all agent run messages for debugging:")
            with capture_run_messages() as run_msgs:
                msgs = getattr(run_msgs, "messages", run_msgs)
                for msg in msgs:
                    self.ui.print_info(str(msg))
            return
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