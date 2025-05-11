from models import Product, Order
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class ProductDB(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)

class OrderDB(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    recipient_name = Column(String, nullable=False)
    recipient_phone = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    address = Column(String, nullable=False)
    delivery_time = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)

class ProductTool:
    """
    Tool for managing and querying products using a file-based SQLite database.
    """
    def __init__(self, db_path='products.db', seed: bool = True):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        if seed:
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

    def add_product(self, name: str, price: float, stock: int):
        session = self.Session()
        product = ProductDB(name=name, price=price, stock=stock)
        session.add(product)
        session.commit()
        session.close()

class OrdersTool:
    """
    Tool for saving orders and updating product stock.
    """
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=self.engine)

    def save_order(self, order: Order, payment_method: str):
        session = self.Session()
        db_order = OrderDB(
            product_id=order.product.id,
            product_name=order.product.name,
            quantity=order.quantity,
            unit_price=order.unit_price,
            total_price=order.total_price,
            recipient_name=order.recipient_info.name,
            recipient_phone=order.recipient_info.phone,
            recipient_email=str(order.recipient_info.email),
            address=order.address,
            delivery_time=order.delivery_time,
            payment_method=payment_method
        )
        session.add(db_order)
        session.commit()
        order_id = db_order.id
        session.close()
        return order_id

    def show_orders(self):
        session = self.Session()
        orders = session.query(OrderDB).all()
        result = []
        for o in orders:
            result.append({
                'id': o.id,
                'product_name': o.product_name,
                'quantity': o.quantity,
                'unit_price': o.unit_price,
                'total_price': o.total_price,
                'recipient_name': o.recipient_name,
                'recipient_phone': o.recipient_phone,
                'recipient_email': o.recipient_email,
                'address': o.address,
                'delivery_time': o.delivery_time,
                'payment_method': o.payment_method
            })
        session.close()
        return result

    def decrement_stock(self, product_id: int, quantity: int):
        session = self.Session()
        db_product = session.query(ProductDB).filter_by(id=product_id).first()
        if db_product and db_product.stock >= quantity:
            db_product.stock -= quantity
            session.commit()
        session.close()

class PaymentTool:
    """
    Tool for processing payments (mock implementation).
    """
    def process_payment(self, order: Order, payment_method: str) -> bool:
        # Always succeed for now
        return True 