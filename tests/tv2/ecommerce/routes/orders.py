"""
API endpoints for managing orders and checkout.
"""
from fastapi import APIRouter, HTTPException
from models.order import Order, OrderItem, get_order_by_id
from services.payment import process_checkout

router = APIRouter()

@router.post("/orders/checkout")
def checkout_cart(user_id: int, items_data: list[dict], card_number: str, email: str):
    """API endpoint to check out a list of items and place an order."""
    if not items_data:
        raise HTTPException(status_code=400, detail="Cart is empty")

    items = []
    total_amount = 0.0
    for idx, item in enumerate(items_data):
        pid = item.get("product_id")
        qty = item.get("quantity", 1)
        price = item.get("price", 10.0) # mock fallback price
        items.append(OrderItem(product_id=pid, quantity=qty, price=price))
        total_amount += price * qty

    # Create dummy new order with incrementing ID representation
    new_order = Order(
        id=999, # mock ID
        user_id=user_id,
        items=items,
        status="pending",
        total_amount=total_amount
    )

    success = process_checkout(new_order, card_number, email)
    if not success:
        raise HTTPException(status_code=400, detail="Checkout failed (payment error or stock issue)")

    return {
        "success": True,
        "order_id": new_order.id,
        "total": new_order.total_amount,
        "status": new_order.status
    }

@router.get("/orders/{order_id}")
def get_order_details(order_id: int):
    """Retrieve details for a past order."""
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.id,
        "status": order.status,
        "total": order.total_amount
    }
