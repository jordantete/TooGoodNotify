class Error(Exception):
    """Base class for all custom errors."""
    def __init__(self, message: str = "An error occurred", *args):
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

class TgtgLoginError(Error):
    """Raised when login to TGTG API fails."""
    def __init__(self, message: str = "Failed to log in to TGTG API", *args):
        super().__init__(message, *args)

class TgtgAPIConnectionError(Error):
    """Raised for issues connecting to the TGTG API."""
    def __init__(self, message: str = "Failed to connect to TGTG API", status_code: int = None, *args):
        super().__init__(message, *args)
        self.status_code = status_code

    def __str__(self):
        base_message = super().__str__()
        if self.status_code:
            return f"{base_message} (Status Code: {self.status_code})"
        return base_message

class TgtgAPIParsingError(Error):
    """Raised for errors while parsing data from the TGTG API."""
    def __init__(self, message: str = "Error parsing data from TGTG API", data: str = None, *args):
        super().__init__(message, *args)
        self.data = data  # Optional raw data that caused the parsing error

    def __str__(self):
        base_message = super().__str__()
        if self.data:
            return f"{base_message} | Data: {self.data}"
        return base_message

class ForbiddenError(TgtgAPIConnectionError):
    """Raised when the API returns a 403 Forbidden error."""
    def __init__(self, message: str = "Access forbidden (403). Anti-bot detection triggered.", *args):
        super().__init__(message, status_code=403, *args)