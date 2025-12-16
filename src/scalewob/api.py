"""
API functions for fetching ScaleWoB environment metadata
"""

from typing import Any, Dict, List, Optional

from .exceptions import NetworkError

_cache: Dict[str, List[Dict[str, Any]]] = {}


def fetch_tasks(
    difficulty: Optional[str] = None,
    platform: Optional[str] = None,
    tags: Optional[List[str]] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch all tasks from ScaleWoB registry as a flat list.

    Each task includes its environment context, making it easy to iterate
    through all available tasks without nested loops.

    Args:
        difficulty: Filter by difficulty level (e.g., "Basic", "Advanced", "Expert")
        platform: Filter by platform (e.g., "Mobile Interfaces")
        tags: Filter by tags (returns tasks from environments matching any tag)
        force_refresh: Bypass cache and fetch fresh data

    Returns:
        List of task dictionaries, each containing:
        - env_id: Environment ID
        - env_name: Environment display name
        - task_id: Task index within the environment (for use with finish_evaluation)
        - task_name: Task name (if available)
        - description: Task description/instruction
        - difficulty: Environment difficulty level
        - platform: Environment platform
        - tags: Environment tags
        - params: Task parameters (if any)

    Raises:
        NetworkError: If fetching or parsing fails

    Example:
        >>> tasks = fetch_tasks(difficulty="Basic")
        >>> for task in tasks:
        ...     print(f"[{task['env_id']}:{task['task_id']}] {task['description']}")
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

    # Flatten into task list
    tasks = []
    for env in environments:
        env_tasks = env.get("tasks", [])
        for task_idx, task in enumerate(env_tasks):
            tasks.append({
                "env_id": env.get("id"),
                "env_name": env.get("name"),
                "task_id": task_idx,
                "task_name": task.get("name"),
                "description": task.get("description"),
                "difficulty": env.get("difficulty"),
                "platform": env.get("platform"),
                "tags": env.get("tags", []),
                "params": task.get("params"),
            })

    return tasks
