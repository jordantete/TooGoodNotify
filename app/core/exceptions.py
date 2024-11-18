class CoreError(Exception):
    """Base class for core-related errors."""
    def __init__(self, message: str = "A core error occurred", *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

class DatabaseError(CoreError):
    """Base class for database-related errors."""
    def __init__(self, message: str = "A database error occurred", *args):
        super().__init__(message, *args)

class DatabaseConnectionError(DatabaseError):
    """Raised when a connection to the database fails."""
    def __init__(self, message: str = "Failed to connect to the database", *args):
        super().__init__(message, *args)

class DatabaseQueryError(DatabaseError):
    """Raised when a query to the database fails."""
    def __init__(self, message: str = "Database query failed", query: str = None, *args):
        super().__init__(message, *args)
        self.query = query

    def __str__(self):
        base_message = super().__str__()
        if self.query:
            return f"{base_message} | Query: {self.query}"
        return base_message
