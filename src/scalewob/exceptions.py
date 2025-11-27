"""
Custom exceptions for ScaleWoB SDK
"""


class ScaleWoBError(Exception):
    """Base exception for all ScaleWoB SDK errors"""

    pass


class TimeoutError(ScaleWoBError):
    """Raised when an operation times out"""

    pass


class CommandError(ScaleWoBError):
    """Raised when a command execution fails"""

    pass


class EvaluationError(ScaleWoBError):
    """Raised when evaluation fails"""

    pass


class BrowserError(ScaleWoBError):
    """Raised when browser automation fails"""

    pass


class NetworkError(ScaleWoBError):
    """Raised when network operations fail"""

    pass
