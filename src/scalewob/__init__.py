"""
ScaleWoB Python SDK - Automated Evaluation for GUI Agent Benchmarks

This SDK provides a Python interface for automating interactions with ScaleWoB
environments using Selenium WebDriver.

Example:
    from scalewob import ScaleWoBAutomation

    # Initialize automation
    auto = ScaleWoBAutomation(env_id='booking-hotel-simple')
    auto.start()
    auto.start_evaluation()

    # Perform coordinate-based actions
    auto.click(x=300, y=150)  # Click search button at coordinates
    auto.type('New York')  # Type into focused element

    # Evaluate
    result = auto.finish_evaluation({'destination': 'New York'})
    print(result)
"""

from importlib.metadata import version as get_version

from .api import fetch_environments
from .automation import ScaleWoBAutomation
from .exceptions import (
    BrowserError,
    CommandError,
    EvaluationError,
    NetworkError,
    ScaleWoBError,
    TimeoutError,
)

__version__ = get_version(__package__)  # type: ignore
__all__ = [
    "ScaleWoBAutomation",
    "fetch_environments",
    "ScaleWoBError",
    "TimeoutError",
    "CommandError",
    "EvaluationError",
    "BrowserError",
    "NetworkError",
]
