from agents import MockAgent, PydanticAIAgent, LLMAgent
from models import Order
from tools import ProductTool, PaymentTool
from utils.ui import TerminalUI

def main():
    ui = TerminalUI()
    ui.print_welcome()
    agent_options = [
        ("1", "Manual (MockAgent)", MockAgent),
        ("2", "Pydantic CLI (PydanticAIAgent)", PydanticAIAgent),
        ("3", "LLM-powered (LLMAgent)", LLMAgent),
    ]
    ui.print_section("Select agent type:")
    for key, label, _ in agent_options:
        print(f"  {key}. {label}")
    while True:
        choice = input("Enter agent number: ").strip()
        for key, _, agent_cls in agent_options:
            if choice == key:
                agent = agent_cls(ui=ui)
                break
        else:
            print("Invalid choice. Try again.")
            continue
        break
    while True:
        agent.start_order()
        if not ui.prompt_yes_no('Would you like to place another order?'):
            break
    ui.print_goodbye()

if __name__ == "__main__":
    import sys
    try:
        main()
    except EOFError:
        print("Input stream closed. Exiting.")
        sys.exit(0)
