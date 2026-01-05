# ScaleWoB Python SDK

[![PyPI version](https://badge.fury.io/py/scalewob.svg)](https://badge.fury.io/py/scalewob)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![REUSE status](https://api.reuse.software/badge/github.com/ScaleWoB/ScaleWoB)](https://api.reuse.software/info/github.com/ScaleWoB/ScaleWoB)
[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/ScaleWoB/ScaleWoB)

Python SDK for evaluating in ScaleWoB: Scalable world-of-bit that revolutionizes the evaluation of Computer-Use Agents. 

🔥 Use this SDK to plug your computer-use agent to our upcoming benchmark!

## Installation

```bash
pip install scalewob
```

## Discovering Tasks

ScaleWoB uses a two-step process to discover tasks:

1. Fetch available environments
2. Load each environment to get its tasks

```python
from scalewob import ScaleWoBAutomation, fetch_environments

# Step 1: Fetch available environments
envs = fetch_environments()
print(f"Found {len(envs)} environments")

# Filter by difficulty
basic_envs = fetch_environments(difficulty="Basic")

# Filter by platform and tags
mobile_envs = fetch_environments(
    platform="Mobile Interfaces",
    tags=["Time Selection"]
)

# Step 2: For each environment, load it and work with its tasks
for env in basic_envs:
    with ScaleWoBAutomation(env_id=env['id']) as auto:  # the browser will show up
        # Access tasks via the tasks property
        print(f"Environment {env['name']} has {len(auto.tasks)} tasks")

        # Work with each task
        for idx, task in enumerate(auto.tasks):
            auto.start_evaluation()
            # ... perform actions based on task['description'] ...

            # The task's params field (if present) is a JSON schema
            # You need to provide actual parameter values that match this schema
            if task.get('params'):
                # Example: provide actual values matching the schema
                # Validation is automatic when you call finish_evaluation
                actual_params = {
                    "destination": "New York",
                    "check_in": "2024-01-15"
                }
                result = auto.finish_evaluation(
                    task_id=task['task_id'],
                    params=actual_params  # Auto-validated against task['params']
                )
            else:
                result = auto.finish_evaluation(task_id=task['task_id'])
```

## Development

### Setup

```bash
# Clone the repo and enter the directory first
uv sync

# Install pre-commit hooks
uv pre-commit install
```

### Code Quality

```bash
# Format code
uv run poe format

# Run checks (format, lint, type checking)
uv run poe check

# Fix linting issues
uv run poe fix
```

## License

MIT License - see LICENSE file for details.

## Links

- **Homepage:** https://github.com/ScaleWoB/ScaleWoB.github.io
- **Documentation:** https://github.com/ScaleWoB/ScaleWoB#readme
- **Bug Tracker:** https://github.com/ScaleWoB/ScaleWoB/issues
