"""
Core business logic — compute analytics and validate inputs.
"""


def validate_input(dataset_id: str, filters: str = None) -> dict:
    """Validate and normalize input parameters."""
    cleaned = dataset_id.strip().lower()
    return {
        "dataset_id": cleaned,
        "filters": filters.split(",") if filters else [],
    }


def compute_analytics(validated_input: dict, connection) -> dict:
    """Run analytics computation on a validated dataset."""
    dataset_id = validated_input["dataset_id"]
    # Simulate fetching and computing
    raw_data = connection.execute(f"SELECT * FROM {dataset_id}")
    return {
        "dataset": dataset_id,
        "row_count": len(raw_data),
        "summary": "computed",
    }
