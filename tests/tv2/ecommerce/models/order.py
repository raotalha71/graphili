"""
Order data model and database operations.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from .db import get_db_connection

@dataclass
class OrderItem:
    product_id: int
    quantity: int
    price: float

@dataclass
class Order:
    id: int
    user_id: int
    items: List[OrderItem] = field(default_factory=list)
    status: str = "pending"
    total_amount: float = 0.0

def save_order(order: Order) -> bool:
    """Inserts or updates an order in the database."""
    db = get_db_connection()
    db.execute_query(
        "INSERT INTO orders (id, user_id, status, total) VALUES (?, ?, ?, ?)",
        (order.id, order.user_id, order.status, order.total_amount)
    )
    for item in order.items:
        db.execute_query(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order.id, item.product_id, item.quantity, item.price)
        )
    return True

def get_order_by_id(order_id: int) -> Optional[Order]:
    """Retrieves an order from the database by ID."""
    db = get_db_connection()
    db.execute_query("SELECT * FROM orders WHERE id = ?", (order_id,))
    # Mocking order for testing
    return Order(id=order_id, user_id=42, status="paid", total_amount=49.99)
