import sys
import argparse
from agents import MockAgent, PydanticAIAgent, LLMAgent
from models import Order
from tools import ProductTool, PaymentTool
from utils.ui import TerminalUI

def main():
    parser = argparse.ArgumentParser(description="Order System CLI")
    parser.add_argument(
        "--agent",
        choices=["mock", "pydantic", "llm"],
        default="llm",
        help="Agent type: mock, pydantic, or llm (default: llm)"
    )
    args = parser.parse_args()

    ui = TerminalUI()
    ui.print_welcome()
    agent_map = {
        "mock": MockAgent,
        "pydantic": PydanticAIAgent,
        "llm": LLMAgent,
    }
    agent_cls = agent_map[args.agent]
    agent = agent_cls(ui=ui)
    while True:
        agent.start_order()
        if not ui.prompt_yes_no('Would you like to place another order?'):
            break
    ui.print_goodbye()

if __name__ == "__main__":
    try:
        main()
    except EOFError:
        print("Input stream closed. Exiting.")
        sys.exit(0)
