"""
API endpoints for the myapp project.
Uses a src/ layout — imports reference myapp.core.logic, NOT src.myapp.core.logic.
This is the test case that BREAKS without proper source root detection.
"""

from fastapi import APIRouter

from myapp.core.logic import compute_analytics, validate_input
from myapp.core.database import get_connection


router = APIRouter()


@router.get("/analytics/{dataset_id}")
def get_analytics(dataset_id: str, filters: str = None) -> dict:
    """Fetch analytics for a given dataset."""
    conn = get_connection()
    validated = validate_input(dataset_id, filters)
    result = compute_analytics(validated, conn)
    return {"status": "ok", "data": result}


@router.post("/analytics/batch")
def run_batch_analytics(dataset_ids: list[str]) -> dict:
    """Run analytics across multiple datasets."""
    conn = get_connection()
    results = []
    for ds_id in dataset_ids:
        validated = validate_input(ds_id)
        results.append(compute_analytics(validated, conn))
    return {"status": "ok", "results": results}
