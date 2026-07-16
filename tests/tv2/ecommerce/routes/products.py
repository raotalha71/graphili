"""
API endpoints for searching and browsing products.
"""
from fastapi import APIRouter, HTTPException
from models.product import find_product_by_id

router = APIRouter()

@router.get("/products/{product_id}")
def get_product_details(product_id: int):
    """Retrieve details of a specific product."""
    product = find_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "in_stock": product.stock_quantity > 0
    }

@router.get("/products/search")
def search_catalog(query: str):
    """Search for products by query text."""
    # Mocking static catalog search
    return [
        {"id": 101, "name": "Keyboard", "price": 49.99}
    ]
