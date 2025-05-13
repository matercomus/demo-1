import os
import pytest
from utils.db_utils import reset_db
from tools import ProductTool

def test_reset_main_db(tmp_path):
    db_path = tmp_path / "products.db"
    reset_db(str(db_path))
    tool = ProductTool(db_path=str(db_path))
    products = tool.list_products()
    names = [p.name for p in products]
    assert set(names) == {"Widget", "Gadget", "Thingamajig"}
    assert all(p.stock == 10 for p in products)

def test_reset_test_db(tmp_path):
    db_path = tmp_path / "test_products.db"
    reset_db(str(db_path))
    tool = ProductTool(db_path=str(db_path))
    products = tool.list_products()
    names = [p.name for p in products]
    assert set(names) == {"Widget", "Gadget", "Thingamajig"}
    assert all(p.stock == 10 for p in products)

def test_reset_overwrites_existing_db(tmp_path):
    db_path = tmp_path / "products.db"
    # Create a DB with different stock
    tool = ProductTool(db_path=str(db_path), seed=False)
    tool.add_product('Widget', 9.99, 1)
    tool.add_product('Gadget', 19.99, 2)
    tool.add_product('Thingamajig', 14.99, 3)
    # Close all connections before resetting
    tool.engine.dispose()
    # Now reset
    reset_db(str(db_path))
    tool = ProductTool(db_path=str(db_path))
    products = tool.list_products()
    assert all(p.stock == 10 for p in products)

def test_reset_no_seed(tmp_path):
    db_path = tmp_path / "products.db"
    reset_db(str(db_path), seed=False)
    tool = ProductTool(db_path=str(db_path), seed=False)
    products = tool.list_products()
    assert products == [] 