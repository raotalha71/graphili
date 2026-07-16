"""
Mock database utility module for the e-commerce test project.
"""

class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.is_connected = False

    def connect(self) -> bool:
        """Connects to the database."""
        self.is_connected = True
        return True

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Executes a SQL query and returns raw mock rows."""
        if not self.is_connected:
            raise ConnectionError("Database not connected.")
        print(f"Executing: {query} with params {params}")
        return []

def get_db_connection() -> DatabaseConnection:
    """Helper to initialize and return a database connection."""
    conn = DatabaseConnection("sqlite:///:memory:")
    conn.connect()
    return conn
