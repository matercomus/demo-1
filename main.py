from agent import MockAgent
from models import Order
from tools import ProductTool, PaymentTool
from utils.ui import TerminalUI

def main():
    ui = TerminalUI()
    agent = MockAgent(ui=ui)
    ui.print_welcome()
    while True:
        agent.start_order()
        if not ui.prompt_yes_no('Would you like to place another order?'):
            break
    ui.print_goodbye()

if __name__ == "__main__":
    main()
