from models import Product, Order
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class ProductDB(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)

class ProductTool:
    """
    Tool for managing and querying products using a file-based SQLite database.
    """
    def __init__(self, db_path='products.db'):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._seed_products()

    def _seed_products(self):
        session = self.Session()
        if session.query(ProductDB).count() == 0:
            products = [
                ProductDB(name='Widget', price=9.99, stock=10),
                ProductDB(name='Gadget', price=19.99, stock=5),
                ProductDB(name='Thingamajig', price=14.99, stock=0),
            ]
            session.add_all(products)
            session.commit()
        session.close()

    def list_products(self) -> List[Product]:
        session = self.Session()
        db_products = session.query(ProductDB).all()
        products = [Product(id=p.id, name=p.name, price=p.price, stock=p.stock) for p in db_products]
        session.close()
        return products

    def check_stock(self, product: Product, quantity: int) -> bool:
        session = self.Session()
        db_product = session.query(ProductDB).filter_by(id=product.id).first()
        result = db_product and db_product.stock >= quantity
        session.close()
        return result

    def get_price(self, product: Product) -> float:
        session = self.Session()
        db_product = session.query(ProductDB).filter_by(id=product.id).first()
        price = db_product.price if db_product else 0.0
        session.close()
        return price

class PaymentTool:
    """
    Tool for processing payments (mock implementation).
    """
    def process_payment(self, order: Order, payment_method: str) -> bool:
        # Always succeed for now
        return True 