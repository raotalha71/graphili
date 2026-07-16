"""
Inventory services to manage product availability.
"""
from models.product import find_product_by_id, update_product_stock

def check_stock_available(product_id: int, quantity: int) -> bool:
    """Verifies if the requested quantity of product is in stock."""
    product = find_product_by_id(product_id)
    if not product:
        return False
    return product.stock_quantity >= quantity

def reserve_stock(product_id: int, quantity: int) -> bool:
    """Reduces stock of product if available."""
    product = find_product_by_id(product_id)
    if not product or product.stock_quantity < quantity:
        return False
    
    new_stock = product.stock_quantity - quantity
    return update_product_stock(product_id, new_stock)
