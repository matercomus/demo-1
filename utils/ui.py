import sys
from typing import List
from models import Product, Order

class TerminalUI:
    """
    Terminal-based user interface for the order system.
    Provides methods for printing and prompting user input.
    """
    def print_welcome(self):
        print("\n==============================")
        print(" Welcome to the Order System ")
        print("==============================\n")

    def print_goodbye(self):
        print("\nThank you for using the Order System. Goodbye!\n")

    def print_section(self, title: str):
        print(f"\n--- {title} ---\n")

    def print_error(self, message: str):
        print(f"[ERROR] {message}\n", file=sys.stderr)

    def print_success(self, message: str):
        print(f"[SUCCESS] {message}\n")

    def print_products(self, products: List[Product]):
        print("Available Products:")
        for idx, p in enumerate(products, 1):
            stock_str = f"(stock: {p.stock})" if p.stock > 0 else "[OUT OF STOCK]"
            print(f"  {idx}. {p.name} - ${p.price:.2f} {stock_str}")
        print("  0. Cancel\n")

    def print_order_summary(self, order: Order):
        print("\nOrder Summary:")
        print(f"  Product: {order.product.name if order.product else '-'}")
        print(f"  Quantity: {order.quantity}")
        print(f"  Unit Price: ${order.unit_price:.2f}")
        print(f"  Total Price: ${order.total_price:.2f}")
        if order.recipient_info:
            print(f"  Recipient: {order.recipient_info.name} ({order.recipient_info.email}, {order.recipient_info.phone})")
        print(f"  Address: {order.address}")
        print(f"  Delivery Time: {order.delivery_time}\n")

    def prompt(self, message: str) -> str:
        return input(f"{message} ").strip()

    def prompt_int(self, message: str, min_value: int = 1, max_value: int = 1000) -> int:
        while True:
            try:
                value = int(input(f"{message} ").strip())
                if value < min_value or value > max_value:
                    print(f"Please enter a number between {min_value} and {max_value}.")
                    continue
                return value
            except ValueError:
                print("Please enter a valid integer.")

    def prompt_yes_no(self, message: str) -> bool:
        while True:
            resp = input(f"{message} (y/n): ").strip().lower()
            if resp in ("y", "yes"): return True
            if resp in ("n", "no"): return False
            print("Please enter 'y' or 'n'.") 