"""
Database connection layer.
"""


class DatabaseConnection:
    """Simple database connection wrapper."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connected = False

    def connect(self):
        self._connected = True

    def execute(self, query: str) -> list:
        """Execute a query and return results."""
        return [{"row": 1}, {"row": 2}]

    def close(self):
        self._connected = False


def get_connection(db_url: str = "sqlite:///default.db") -> DatabaseConnection:
    """Factory function to create a database connection."""
    conn = DatabaseConnection(db_url)
    conn.connect()
    return conn
