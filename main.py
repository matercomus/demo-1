import logging
import sys

# Set root logger to WARNING
logging.basicConfig(level=logging.WARNING)

# Configure SQLAlchemy logger
sa_logger = logging.getLogger("sqlalchemy.engine")
sa_logger.setLevel(logging.WARNING)
sa_logger.propagate = False
for h in list(sa_logger.handlers):
    sa_logger.removeHandler(h)
if not sa_logger.handlers:
    sa_logger.addHandler(logging.StreamHandler(sys.stderr))

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
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose SQLAlchemy logs"
    )
    args = parser.parse_args()

    # Set SQLAlchemy logging level based on -v
    if args.verbose:
        sa_logger.setLevel(logging.INFO)
        for h in sa_logger.handlers:
            h.setLevel(logging.INFO)
    else:
        sa_logger.setLevel(logging.WARNING)
        for h in sa_logger.handlers:
            h.setLevel(logging.WARNING)

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
