import sys
from typing import List
from models import Product, Order
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.console import Group

TABLE_RESULT_MARKER = "__TABLE_RESULT__"

class TerminalUI:
    """
    Terminal-based user interface for the order system.
    Provides methods for printing and prompting user input.
    Uses Rich for enhanced formatting.
    """
    def __init__(self):
        self.console = Console()

    def print_welcome(self):
        self.console.print(Panel.fit(
            "[bold magenta]Welcome to the Order System[/bold magenta]\n\n"
            "[bold]What you can do:[/bold]\n"
            "[green]•[/green] Place a new order for any available product\n"
            "[green]•[/green] View the list of products and their stock\n"
            "[green]•[/green] Check your order history\n"
            "[green]•[/green] Cancel an order (if needed)\n"
            "[green]•[/green] Type 'stop chat' at any time to exit\n\n"
            "[dim]Tip: Just type what you want, e.g. 'order a Widget', 'show stock', or 'cancel my last order'.[/dim]",
            title="[cyan]==============================[/cyan]",
            subtitle="[cyan]==============================[/cyan]",
            style="bold green"
        ))

    def print_goodbye(self):
        self.console.print(Panel.fit("Thank you for using the Order System. Goodbye!", style="bold magenta"))

    def print_section(self, title: str):
        self.console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]", style="blue"))

    def print_error(self, message: str):
        self.console.print(Panel.fit(f"[bold red][ERROR][/bold red] {message}", style="red"), file=sys.stderr)

    def print_success(self, message: str):
        self.console.print(Panel.fit(f"[bold green][SUCCESS][/bold green] {message}", style="green"))

    def print_info(self, message: str):
        self.console.print(Panel.fit(f"[bold yellow][INFO][/bold yellow] {message}", style="yellow"))

    def print_agent_response(self, message):
        # Accepts str, Rich renderable, or list/tuple of them
        if isinstance(message, (list, tuple)):
            group = Group(*message)
        else:
            group = message
        panel = Panel.fit(group, title="Assistant", border_style="blue")
        self.console.print(Align.left(panel))

    def print_user_response(self, message: str):
        panel = Panel.fit(message, title="You", border_style="green")
        self.console.print(Align.right(panel))

    def print_products(self, products: List[Product]):
        table = Table(title="Available Products", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Name", style="bold")
        table.add_column("Price", justify="right")
        table.add_column("Stock", justify="center")
        for idx, p in enumerate(products, 1):
            stock_str = f"[green]{p.stock}[/green]" if p.stock > 0 else "[red]OUT OF STOCK[/red]"
            table.add_row(str(idx), p.name, f"${p.price:.2f}", stock_str)
        table.add_row("0", "[dim]Cancel[/dim]", "", "")
        self.console.print(table)

    def print_order_summary(self, order: Order):
        table = Table(title="Order Summary", show_header=False, box=None)
        table.add_row("Product", order.product.name if order.product else "-")
        table.add_row("Quantity", str(order.quantity))
        table.add_row("Unit Price", f"${order.unit_price:.2f}")
        table.add_row("Total Price", f"${order.total_price:.2f}")
        if order.recipient_info:
            table.add_row("Recipient", f"{order.recipient_info.name} ({order.recipient_info.email}, {order.recipient_info.phone})")
        table.add_row("Address", order.address)
        table.add_row("Delivery Time", order.delivery_time)
        self.console.print(Panel(table, title="[bold cyan]Order Summary[/bold cyan]", style="cyan"))

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

    def print_orders_table(self, orders):
        table = Table(title="Orders", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Product")
        table.add_column("Qty", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Recipient")
        table.add_column("Address")
        table.add_column("Delivery Time")
        table.add_column("Payment")
        for o in orders:
            table.add_row(
                str(o.get('id', '')),
                o.get('product_name', ''),
                str(o.get('quantity', '')),
                f"${o.get('total_price', 0):.2f}",
                f"{o.get('recipient_name', '')} ({o.get('recipient_email', '')}, {o.get('recipient_phone', '')})",
                o.get('address', ''),
                o.get('delivery_time', ''),
                o.get('payment_method', '')
            )
        self.console.print(table)

    def build_table_message(self, columns, rows, title=None):
        table = Table(title=title or "Table", show_header=True, header_style="bold magenta")
        for col in columns:
            if isinstance(col, dict):
                table.add_column(
                    col.get("header", ""),
                    style=col.get("style", None),
                    justify=col.get("justify", None),
                    width=col.get("width", None),
                )
            else:
                table.add_column(str(col), style="bold")
        for row in rows:
            formatted_row = list(row)
            # Product stock table formatting
            if title and ("Stock" in columns):
                stock_idx = columns.index("Stock")
                if formatted_row[stock_idx] == "OUT OF STOCK":
                    formatted_row[stock_idx] = f"[red]{formatted_row[stock_idx]}[/red]"
                elif formatted_row[stock_idx].isdigit() and int(formatted_row[stock_idx]) > 0:
                    formatted_row[stock_idx] = f"[green]{formatted_row[stock_idx]}[/green]"
                # Dim the Cancel row for product tables
                if formatted_row[0] == "0" and formatted_row[1].lower() == "cancel":
                    formatted_row = [f"[dim]{cell}[/dim]" if cell else "" for cell in formatted_row]
            # Orders table formatting
            if title and "Orders" in title:
                # Optionally dim cancelled orders or highlight certain fields
                pass  # Add more formatting as needed
            table.add_row(*[str(cell) for cell in formatted_row])
        return table 