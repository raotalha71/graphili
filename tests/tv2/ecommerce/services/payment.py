"""
Payment processing services.
"""
from models.order import Order, save_order
from services.inventory import reserve_stock
from services.notification import notify_order_success

def charge_credit_card(card_number: str, amount: float) -> bool:
    """Mock-charges a credit card."""
    print(f"Charging card ending in {card_number[-4:]} for ${amount:.2f}")
    return True

def process_checkout(order: Order, card_number: str, email: str) -> bool:
    """
    Coordinates checkout: reserves stock, charges payment, 
    saves the order, and triggers success notifications.
    """
    # First, reserve stock for each item in the order
    for item in order.items:
        success = reserve_stock(item.product_id, item.quantity)
        if not success:
            print(f"Failed to reserve stock for product {item.product_id}")
            return False

    # Perform charge
    payment_ok = charge_credit_card(card_number, order.total_amount)
    if not payment_ok:
        order.status = "failed"
        save_order(order)
        return False

    # Update order state & save
    order.status = "paid"
    save_order(order)

    # Notify customer
    notify_order_success(email, order.id)
    return True
