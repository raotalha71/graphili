"""
API endpoints for managing user shopping carts.
"""
from fastapi import APIRouter
from services.inventory import check_stock_available

router = APIRouter()

# In-memory dictionary representing active carts for testing
mock_carts = {}

@router.post("/cart/{user_id}/add")
def add_item_to_cart(user_id: int, product_id: int, quantity: int):
    """Add a product item to a shopping cart, verifying availability first."""
    is_available = check_stock_available(product_id, quantity)
    if not is_available:
        return {"success": False, "message": "Insufficient stock"}
        
    cart = mock_carts.get(user_id, [])
    cart.append({"product_id": product_id, "quantity": quantity})
    mock_carts[user_id] = cart
    return {"success": True, "cart": cart}

@router.get("/cart/{user_id}")
def view_cart(user_id: int):
    """Retrieve shopping cart contents."""
    return {"user_id": user_id, "items": mock_carts.get(user_id, [])}
