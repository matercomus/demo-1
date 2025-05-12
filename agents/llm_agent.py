import asyncio
from dataclasses import dataclass
from models import Order, Product, RecipientInfo
from tools import ProductTool, PaymentTool, OrdersTool, OrderDB, ProductDB
from utils.ui import TerminalUI
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
)
from pydantic_ai.tools import RunContext
import os
from dotenv import load_dotenv
import sys

@dataclass
class OrderService:
    product_tool: ProductTool
    payment_tool: PaymentTool
    orders_tool: OrdersTool
    ui: TerminalUI

    async def save_order(self, order: Order, payment_method: str):
        self.orders_tool.decrement_stock(order.product.id, order.quantity)
        self.orders_tool.save_order(order, payment_method)

class LLMAgent:
    def __init__(self, ui: TerminalUI, db_path: str = 'products.db'):
        load_dotenv()
        self.ui = ui
        self.product_tool = ProductTool(db_path=db_path)
        self.payment_tool = PaymentTool()
        self.orders_tool = OrdersTool(self.product_tool.engine)
        self.order_service = OrderService(
            product_tool=self.product_tool,
            payment_tool=self.payment_tool,
            orders_tool=self.orders_tool,
            ui=self.ui,
        )
        self.last_order_id = None  # Track last placed order in session
        self.agent = Agent[OrderService, str](
            os.getenv('OPENAI_MODEL', 'openai:gpt-4o'),
            deps_type=OrderService,
            output_type=str,
            system_prompt=(
                'You are an order assistant. To process an order, you must call the `place_order` tool with the following fields: '
                'product_name, quantity, name, phone, email, address, delivery_time, payment_method.\n'
                'To cancel any order, call the `cancel_order` tool with the order_id.\n'
                'To show all orders, call the `show_orders` tool.\n'
                'To end the conversation, call the `stop_chat` tool.\n'
                'Do not claim to perform actions unless you call the corresponding tool.\n'
                'If the user asks to cancel an order, ask for the order ID if not provided, and use the `cancel_order` tool.\n'
                'If the user wants to stop, call the `stop_chat` tool.\n'
                'After collecting the info, summarize the order and confirm with the user.\n'
                'To actually place the order in the database, you must call the `place_order` tool.\n'
                'Example tool calls:\n'
                'place_order(product_name="Widget", quantity=2, name="John Doe", phone="123-456-7890", email="john@example.com", address="123 Main St", delivery_time="tomorrow 10am", payment_method="card")\n'
                'cancel_order(order_id=3)\n'
                'show_orders()\n'
                'stop_chat()\n'
            ),
        )
        self._register_tools()

    def _register_tools(self):
        @self.agent.tool
        async def place_order(
            ctx: RunContext[OrderService],
            product_name: str,
            quantity: int,
            name: str,
            phone: str,
            email: str,
            address: str,
            delivery_time: str,
            payment_method: str,
        ) -> str:
            try:
                products = ctx.deps.product_tool.list_products()
                product = next((p for p in products if p.name.lower() == product_name.lower()), None)
                if not product:
                    return f"Error: Product '{product_name}' not found."
                if quantity < 1:
                    return "Error: Quantity must be at least 1."
                if not ctx.deps.product_tool.check_stock(product, quantity):
                    return f"Error: Not enough stock for '{product.name}'. Only {product.stock} left."
                try:
                    recipient = RecipientInfo(name=name, phone=phone, email=email)
                except Exception as e:
                    return f"Validation error in recipient info: {e}"
                unit_price = ctx.deps.product_tool.get_price(product)
                total_price = unit_price * quantity
                order = Order(
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    recipient_info=recipient,
                    address=address,
                    delivery_time=delivery_time,
                )
                ctx.deps.orders_tool.decrement_stock(product.id, quantity)
                order_id = ctx.deps.orders_tool.save_order(order, payment_method)
                self.last_order_id = order_id  # Track last order ID
                return (
                    f"Order placed successfully!\n"
                    f"  Product: {product.name}\n"
                    f"  Quantity: {quantity}\n"
                    f"  Name: {name}\n"
                    f"  Phone: {phone}\n"
                    f"  Email: {email}\n"
                    f"  Address: {address}\n"
                    f"  Delivery Time: {delivery_time}\n"
                    f"  Payment Method: {payment_method}\n"
                    f"  Total Price: ${total_price:.2f}\n"
                    "Thank you for your order!"
                )
            except Exception as e:
                return f"Order placement error: {e}"
        self.place_order = place_order

        @self.agent.tool
        async def cancel_order(ctx: RunContext[OrderService], order_id: int) -> str:
            # Remove specified order and restore stock
            session = ctx.deps.orders_tool.Session()
            order_db = session.query(OrderDB).filter_by(id=order_id).first()
            if not order_db:
                session.close()
                return f"Order with ID {order_id} not found."
            # Restore stock
            product_db = session.query(ProductDB).filter_by(id=order_db.product_id).first()
            if product_db:
                product_db.stock += order_db.quantity
            session.delete(order_db)
            session.commit()
            session.close()
            # If the cancelled order was the last_order_id, clear it
            if self.last_order_id == order_id:
                self.last_order_id = None
            return f"Order {order_id} cancelled and removed from the database."
        self.cancel_order = cancel_order

        @self.agent.tool
        async def list_products(ctx: RunContext[OrderService]):
            products = ctx.deps.product_tool.list_products()
            if not products:
                return "No products are currently available."
            columns = ["#", "Name", "Price", "Stock"]
            rows = []
            for idx, p in enumerate(products, 1):
                stock_str = str(p.stock) if p.stock > 0 else "OUT OF STOCK"
                rows.append([str(idx), p.name, f"${p.price:.2f}", stock_str])
            rows.append(["0", "Cancel", "", ""])
            return {
                "type": "__TABLE_RESULT__",
                "title": "Available Products",
                "columns": columns,
                "rows": rows,
                "message": "Please select a product by number."
            }

        @self.agent.tool
        async def show_orders(ctx: RunContext[OrderService]):
            orders = ctx.deps.orders_tool.show_orders()
            if not orders:
                return "No orders found."
            columns = ["ID", "Product", "Qty", "Total", "Recipient", "Address", "Delivery Time", "Payment"]
            rows = []
            for o in orders:
                rows.append([
                    str(o.get('id', '')),
                    o.get('product_name', ''),
                    str(o.get('quantity', '')),
                    f"${o.get('total_price', 0):.2f}",
                    f"{o.get('recipient_name', '')} ({o.get('recipient_email', '')}, {o.get('recipient_phone', '')})",
                    o.get('address', ''),
                    o.get('delivery_time', ''),
                    o.get('payment_method', '')
                ])
            return {
                "type": "__TABLE_RESULT__",
                "title": "Orders",
                "columns": columns,
                "rows": rows,
                "message": "Here are your orders."
            }
        self.show_orders_tool = show_orders

        @self.agent.tool
        async def stop_chat(ctx: RunContext[OrderService]) -> str:
            return "Conversation ended. Thank you for visiting!"
        self.stop_chat = stop_chat

        @self.agent.tool
        async def stock_info(ctx: RunContext[OrderService]):
            products = ctx.deps.product_tool.list_products()
            if not products:
                return "No products are currently available."
            columns = ["#", "Name", "Stock"]
            rows = []
            for idx, p in enumerate(products, 1):
                stock_str = str(p.stock) if p.stock > 0 else "OUT OF STOCK"
                rows.append([str(idx), p.name, stock_str])
            return {
                "type": "__TABLE_RESULT__",
                "title": "Product Stock Information",
                "columns": columns,
                "rows": rows,
                "message": "Here is the stock information for available products."
            }

    def start_order(self):
        asyncio.run(self._start_order_async())

    async def _start_order_async(self):
        self.ui.print_section('Start New Order (LLM-powered, tool-based)')
        initial_prompt = (
            "Welcome to the order system! You can order any available product. "
            "Please tell me what you'd like to order, and I'll guide you through the process."
        )
        message_history = None
        user_input = initial_prompt
        while True:
            result = await self.agent.run(
                user_input,
                deps=self.order_service,
                message_history=message_history
            )
            # Check if the LLM called stop_chat tool in this turn
            stop = False
            for msg in result.new_messages():
                if isinstance(msg, FunctionToolCallEvent):
                    if getattr(msg.part, 'tool_name', None) == 'stop_chat':
                        stop = True
                        break
            if stop:
                # Print the exact shutdown message for test compatibility and show in the assistant bubble
                msg = "Conversation ended by LLM via stop_chat tool."
                print(msg)
                self.ui.print_agent_response(msg)
                sys.exit(0)
            if result.output:
                output = result.output
                if isinstance(output, dict) and output.get("type") == "__TABLE_RESULT__":
                    table = self.ui.build_table_message(output["columns"], output["rows"], title=output.get("title"))
                    msg = output.get("message", "")
                    self.ui.print_agent_response([table, msg] if msg else [table])
                else:
                    self.ui.print_agent_response(str(output))
            message_history = result.all_messages()
            user_input = self.ui.prompt("Your response:")
            self.ui.print_user_response(user_input)

    def _select_product(self) -> Optional[Product]:
        products = self.product_tool.list_products()
        self.ui.print_products(products)
        idx = self.ui.prompt_int('Select product by number (0 to cancel):', min_value=0, max_value=len(products))
        if idx == 0:
            return None
        return products[idx-1]

    async def show_orders(self, ctx):
        # For test compatibility: call the show_orders tool and return a string summary
        result = await self.show_orders_tool(ctx)
        # If result is a table dict, return a simple string for test assertion
        if isinstance(result, dict) and result.get("type") == "__TABLE_RESULT__":
            # Join rows as lines for test assertion
            lines = []
            for row in result["rows"]:
                lines.append(" | ".join(str(cell) for cell in row))
            return "\n".join(lines)
        return str(result)

    # Alias for tool access
    def show_orders_tool(self):
        return self.show_orders 