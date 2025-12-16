# ScaleWoB Python SDK

[![PyPI version](https://badge.fury.io/py/scalewob.svg)](https://badge.fury.io/py/scalewob)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![REUSE status](https://api.reuse.software/badge/github.com/ScaleWoB/ScaleWoB)](https://api.reuse.software/info/github.com/ScaleWoB/ScaleWoB)

Python SDK for evaluating in ScaleWoB: Scalable world-of-bit that revolutionizes the evaluation of Computer-Use Agents. 

🔥 Use this SDK to plug your computer-use agent to our upcoming benchmark!

## Installation

```bash
pip install scalewob
```

## Quick Start

```python
from scalewob import ScaleWoBAutomation

# Initialize automation for a specific environment
auto = ScaleWoBAutomation(env_id='booking-hotel-simple')

# Start browser and load environment
auto.start()

# Start evaluation mode
auto.start_evaluation()

# Perform actions using coordinates
auto.click(x=300, y=150)  # Click at coordinates
auto.type('New York')      # Type into focused element

# Finish evaluation and get results
result = auto.finish_evaluation({'destination': 'New York'})
print(result)

# Clean up
auto.close()
```

## Discovering Tasks

Fetch available tasks from the ScaleWoB registry as a flat list:

```python
from scalewob import fetch_tasks

# Get all available tasks
tasks = fetch_tasks()
print(f"Found {len(tasks)} tasks")

# Filter by difficulty
expert_tasks = fetch_tasks(difficulty="Expert")

# Filter by platform and tags
time_selection_tasks = fetch_tasks(
    platform="Mobile Interfaces",
    tags=["Time Selection"]
)

# Each task includes environment context
for task in tasks[:3]:
    print(f"[{task['env_id']}:{task['task_id']}] {task['description']}")
```

See [Task Discovery](#task-discovery) in the API Reference for more details.

## Usage

### Context Manager

```python
with ScaleWoBAutomation(env_id='booking-hotel-simple') as auto:
    auto.start()
    auto.start_evaluation()
    auto.click(x=300, y=150)
    auto.type('New York')
    result = auto.finish_evaluation({'destination': 'New York'})
```

### Configuration

```python
auto = ScaleWoBAutomation(
    env_id='booking-hotel-simple',
    headless=False,             # Run in headless mode
    base_url='https://niumascript.com/scalewob-env',
    timeout=5000,               # Default timeout in milliseconds
    screenshot_quality='high',  # 'low' (1x) or 'high' (3x) scale on mobile
    platform='mobile'           # 'mobile' for iPhone emulation, 'desktop' for standard browser
)
```

## API Reference

### Initialization

#### `ScaleWoBAutomation(env_id, headless=False, base_url='https://niumascript.com/scalewob-env', timeout=5000, screenshot_quality='high', platform='mobile')`

Initialize automation interface for ScaleWoB environments.

**Parameters:**
- `env_id` (str): Environment ID to launch
- `headless` (bool): Run browser in headless mode (default: False). Uses Chrome browser.
- `base_url` (str): Base URL for ScaleWoB environments (default: 'https://niumascript.com/scalewob-env')
- `timeout` (int): Default timeout for operations in milliseconds (default: 5000)
- `screenshot_quality` (str): Screenshot quality - 'low' for 1x scale, 'high' for 3x scale on mobile (default: 'high')
- `platform` (str): Platform type - 'mobile' for iPhone emulation, 'desktop' for standard browser (default: 'mobile')

**Note:** Currently only Chrome browser is supported. The browser runs with stealth mode options to avoid detection. Mobile mode uses iPhone viewport (390x844) with 3x pixel ratio and touch interactions. Desktop mode uses standard browser window (1280x800) with mouse interactions.

### Core Methods

#### `start()`

Initialize Chrome browser and navigate to the environment page. Must be called before any other automation methods. Waits for DOM to be fully loaded before returning.

#### `start_evaluation()`

Start evaluation mode. Ensures the environment is fully initialized and clears the trajectory for a fresh evaluation. The environment loads ready to interact without requiring UI button clicks.

#### `finish_evaluation(task_id=0, params=None)`

Finish evaluation and get results.

**Parameters:**
- `task_id` (int, optional): Task index within the environment (default: 0). Used to identify which task in the environment's tasks array is being evaluated.
- `params` (dict, optional): Evaluation parameters (environment-specific)

**Returns:** Evaluation result dictionary

### Interaction Methods

#### `click(x, y)`

Click at coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate

#### `type(text, append=False)`

Type text into the currently focused element. An element must be focused first (e.g., via click).

**Parameters:**
- `text` (str): Text to type
- `append` (bool): If True, append to existing text; if False, clear field first (default: False)

#### `scroll(x, y, direction='down', distance=100)`

Scroll in direction from coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `direction` (str): Scroll direction ('up', 'down', 'left', 'right')
- `distance` (int): Distance to scroll in pixels

#### `long_press(x, y, duration=1000)`

Long press at coordinates (x, y).

**Note:** This is a mobile-specific gesture and will raise `CommandError` on desktop platform.

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `duration` (int): Duration of press in milliseconds

#### `drag(x, y, end_x, end_y)`

Drag from start coordinates to end coordinates.

**Parameters:**
- `x` (int): Starting horizontal coordinate
- `y` (int): Starting vertical coordinate
- `end_x` (int): Ending horizontal coordinate
- `end_y` (int): Ending vertical coordinate

#### `back()`

Go back in navigation history.

### State and Information Methods

#### `take_screenshot(format='base64')`

Capture screenshot of the environment.

**Parameters:**
- `format` (str): Return format - "base64" for raw base64 string, "pil" for PIL Image object

**Returns:** Base64 string or PIL Image object

#### `get_evaluation_result()`

Get the last evaluation result.

**Returns:** Last evaluation result or None

#### `get_trajectory()`

Get current action trajectory.

Returns a copy of the trajectory history containing all actions performed since `start_evaluation()` was called.

**Returns:** List of trajectory entries with timestamp, type, and data

**Example:**
```python
trajectory = auto.get_trajectory()
print(f"Collected {len(trajectory)} actions")
for action in trajectory:
    print(f"{action['type']} at {action['timestamp']}")
```

#### `clear_trajectory()`

Clear the current trajectory history.

This is useful if you want to reset the trajectory without restarting the evaluation. Note that `start_evaluation()` automatically clears the trajectory.

**Example:**
```python
auto.clear_trajectory()
print(len(auto.get_trajectory()))  # 0
```

#### `close()`

Close browser and cleanup resources.

### Task Discovery

#### `fetch_tasks(difficulty=None, platform=None, tags=None, force_refresh=False)`

Fetch all tasks from ScaleWoB registry as a flat list with optional filtering.

Each task includes its environment context, making it easy to iterate through all available tasks without nested loops.

**Parameters:**
- `difficulty` (str, optional): Filter by difficulty level (e.g., "Basic", "Advanced", "Expert")
- `platform` (str, optional): Filter by platform (e.g., "Mobile Interfaces")
- `tags` (list, optional): Filter by tags (returns tasks from environments matching any tag)
- `force_refresh` (bool): Bypass cache and fetch fresh data (default: False)

**Returns:** List of task dictionaries, each containing:
- `env_id`: Environment ID
- `env_name`: Environment display name
- `task_id`: Task index within the environment (for use with `finish_evaluation()`)
- `task_name`: Task name (if available)
- `description`: Task description/instruction
- `difficulty`: Environment difficulty level
- `platform`: Environment platform
- `tags`: Environment tags
- `params`: Task parameters (if any)

**Raises:** `NetworkError` if fetching or parsing fails

**Example:**
```python
from scalewob import fetch_tasks, ScaleWoBAutomation

# Get all tasks
all_tasks = fetch_tasks()

# Filter by multiple criteria
filtered = fetch_tasks(
    difficulty="Expert",
    platform="Mobile Interfaces"
)

# Force refresh cache
fresh = fetch_tasks(force_refresh=True)

# Iterate through tasks and run evaluations
for task in fetch_tasks(difficulty="Basic"):
    auto = ScaleWoBAutomation(task['env_id'])
    auto.start()
    auto.start_evaluation()
    # ... perform actions based on task['description'] ...
    result = auto.finish_evaluation(task_id=task['task_id'])
    auto.close()
```

## Exception Handling

```python
from scalewob import (
    ScaleWoBError,      # Base exception
    TimeoutError,       # Operation timeout
    CommandError,       # Command execution failure
    EvaluationError,    # Evaluation failure
    BrowserError,       # Browser automation failure
    NetworkError        # Network operation failure
)

try:
    auto = ScaleWoBAutomation(env_id='booking-hotel-simple')
    auto.start()
    auto.start_evaluation()
    result = auto.finish_evaluation()
except TimeoutError as e:
    print(f"Operation timed out: {e}")
except EvaluationError as e:
    print(f"Evaluation failed: {e}")
except ScaleWoBError as e:
    print(f"ScaleWoB error: {e}")
finally:
    auto.close()
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
