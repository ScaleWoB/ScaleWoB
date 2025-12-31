"""
API functions for fetching ScaleWoB environment metadata
"""

from typing import Any, Dict, List, Optional

from .exceptions import NetworkError

_cache: Dict[str, List[Dict[str, Any]]] = {}


def fetch_environments(
    difficulty: Optional[str] = None,
    platform: Optional[str] = None,
    tags: Optional[List[str]] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch environment metadata from ScaleWoB registry.

    Args:
        difficulty: Filter by difficulty level (e.g., "Basic", "Advanced", "Expert")
        platform: Filter by platform (e.g., "Mobile Interfaces")
        tags: Filter by tags (returns environments matching any tag)
        force_refresh: Bypass cache and fetch fresh data

    Returns:
        List of environment dictionaries, each containing:
        - id: Environment ID
        - name: Environment display name
        - difficulty: Difficulty level
        - platform: Platform type
        - tags: List of tags

    Raises:
        NetworkError: If fetching or parsing fails

    Example:
        >>> envs = fetch_environments(difficulty="Basic")
        >>> for env in envs:
        ...     print(f"[{env['id']}] {env['name']}")
    """
    url = "https://niumascript.com/scalewob-env/environments.json"

    if not force_refresh and url in _cache:
        environments = _cache[url]
    else:
        try:
            import requests

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            environments = response.json()
            _cache[url] = environments
        except Exception as e:
            raise NetworkError(f"Failed to fetch environments: {str(e)}")

    # Apply environment-level filters
    if difficulty:
        environments = [e for e in environments if e.get("difficulty") == difficulty]

    if platform:
        environments = [e for e in environments if e.get("platform") == platform]

    if tags:
        environments = [
            e for e in environments if any(t in e.get("tags", []) for t in tags)
        ]

    return environments
