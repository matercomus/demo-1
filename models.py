from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

class Product(BaseModel):
    """A product in the catalog."""
    id: int
    name: str
    price: float
    stock: int

class RecipientInfo(BaseModel):
    """Recipient information for the order."""
    name: str
    phone: str
    email: EmailStr

class Order(BaseModel):
    """Order details."""
    product: Optional[Product] = None
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    recipient_info: Optional[RecipientInfo] = None
    address: Optional[str] = None
    delivery_time: Optional[str] = None

class OrderInput(BaseModel):
    name: str
    phone: str
    email: EmailStr
    address: str
    delivery_time: str
    payment_method: str

    @field_validator('name', 'address', 'delivery_time', 'payment_method')
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()

    @field_validator('phone')
    @classmethod
    def valid_phone(cls, v):
        digits = re.sub(r'[^0-9]', '', v)
        if len(digits) < 7:
            raise ValueError('Phone number must have at least 7 digits')
        if not re.match(r'^[0-9\-\+\s]+$', v):
            raise ValueError('Phone number can only contain numbers, spaces, dashes, or plus sign')
        return v.strip() 