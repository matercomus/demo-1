import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools import ProductTool

def reset_db(db_path: str, seed: bool = True):
    if os.path.exists(db_path):
        os.remove(db_path)
    tool = ProductTool(db_path=db_path, seed=False)
    if seed:
        tool.add_product('Widget', 9.99, 10)
        tool.add_product('Gadget', 19.99, 10)
        tool.add_product('Thingamajig', 14.99, 10)
    print(f"Reset and seeded {db_path}")

def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'reset':
        print("Usage: python utils/db_utils.py reset [--test]")
        sys.exit(1)
    if '--test' in sys.argv:
        reset_db('test_products.db')
    else:
        reset_db('products.db')

if __name__ == "__main__":
    main() 