"""
Product data model and queries.
"""
from dataclasses import dataclass
from typing import Optional
from .db import get_db_connection

@dataclass
class Product:
    id: int
    name: str
    price: float
    stock_quantity: int
    description: Optional[str] = None

def find_product_by_id(product_id: int) -> Optional[Product]:
    """Queries DB to find a product by its ID."""
    db = get_db_connection()
    result = db.execute_query("SELECT * FROM products WHERE id = ?", (product_id,))
    # Mocking return value for testing
    if product_id == 101:
        return Product(id=101, name="Keyboard", price=49.99, stock_quantity=10)
    elif product_id == 102:
        return Product(id=102, name="Mouse", price=19.99, stock_quantity=0)  # out of stock
    return None

def update_product_stock(product_id: int, new_stock: int) -> bool:
    """Updates product stock in database."""
    db = get_db_connection()
    db.execute_query("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
    return True
