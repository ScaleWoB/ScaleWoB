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

## Discovering Environments

Fetch available environment metadata from the ScaleWoB registry:

```python
from scalewob import fetch_environments

# Get all available environments
envs = fetch_environments()
print(f"Found {len(envs)} environments")

# Filter by difficulty
expert_envs = fetch_environments(difficulty="Expert")

# Filter by platform and tags
time_selection_envs = fetch_environments(
    platform="Mobile Interfaces",
    tags=["Time Selection"]
)
```

See [Environment Discovery](#environment-discovery) in the API Reference for more details.

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
    screenshot_quality='high'   # 'low' (1x) or 'high' (3x) scale
)
```

## API Reference

### Initialization

#### `ScaleWoBAutomation(env_id, headless=False, base_url='https://niumascript.com/scalewob-env', timeout=5000, screenshot_quality='high')`

Initialize automation interface for ScaleWoB environments.

**Parameters:**
- `env_id` (str): Environment ID to launch
- `headless` (bool): Run browser in headless mode (default: False). Uses Chrome browser.
- `base_url` (str): Base URL for ScaleWoB environments (default: 'https://niumascript.com/scalewob-env')
- `timeout` (int): Default timeout for operations in milliseconds (default: 5000)
- `screenshot_quality` (str): Screenshot quality - 'low' for 1x scale, 'high' for 3x scale (default: 'high')

**Note:** Currently only Chrome browser is supported. The browser runs with stealth mode options to avoid detection.

### Core Methods

#### `start()`

Initialize Chrome browser and navigate to the environment page. Must be called before any other automation methods. Waits for DOM to be fully loaded before returning.

#### `start_evaluation()`

Start evaluation mode. Ensures the environment is fully initialized and clears the trajectory for a fresh evaluation. The environment loads ready to interact without requiring UI button clicks.

#### `finish_evaluation(params=None)`

Finish evaluation and get results.

**Parameters:**
- `params` (dict, optional): Evaluation parameters (environment-specific)

**Returns:** Evaluation result dictionary

### Interaction Methods

#### `click(x, y, delay=100)`

Click at coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `delay` (int): Delay before clicking in milliseconds

#### `type(text, typing_delay=50)`

Type text into the currently focused element. An element must be focused first (e.g., via click).

**Parameters:**
- `text` (str): Text to type
- `typing_delay` (int): Delay between keystrokes in milliseconds

#### `scroll(x, y, direction='down', distance=100)`

Scroll in direction from coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `direction` (str): Scroll direction ('up', 'down', 'left', 'right')
- `distance` (int): Distance to scroll in pixels

#### `long_press(x, y, duration=1000)`

Long press at coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `duration` (int): Duration of press in milliseconds

#### `drag(x, y, direction='down', distance=100)`

Drag from coordinates (x, y) in specified direction.

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate
- `direction` (str): Drag direction ('up', 'down', 'left', 'right')
- `distance` (int): Distance to drag in pixels

#### `back()`

Go back in navigation history.

### State and Information Methods

#### `get_state()`

Get current environment state including URL, title, viewport, etc.

**Returns:** Environment state dictionary

#### `get_element_info(x, y)`

Get information about element at coordinates (x, y).

**Parameters:**
- `x` (int): Horizontal coordinate
- `y` (int): Vertical coordinate

**Returns:** Element information (position, size, attributes, etc.)

#### `get_element_info_by_selector(selector)`

Get information about first element matching CSS selector.

**Parameters:**
- `selector` (str): CSS selector for element

**Returns:** Element information dictionary

#### `take_screenshot(format='base64')`

Capture screenshot of the environment.

**Parameters:**
- `format` (str): Return format - "base64" for raw base64 string, "pil" for PIL Image object

**Returns:** Base64 string or PIL Image object

#### `execute_script(script)`

Execute arbitrary JavaScript in the environment.

**Parameters:**
- `script` (str): JavaScript code to execute

**Returns:** Script execution result

#### `get_evaluation_result()`

Get the last evaluation result.

**Returns:** Last evaluation result or None

#### `close()`

Close browser and cleanup resources.

### Environment Discovery

#### `fetch_environments(difficulty=None, platform=None, tags=None, force_refresh=False)`

Fetch environment metadata from ScaleWoB registry with optional filtering.

**Parameters:**
- `difficulty` (str, optional): Filter by difficulty level (e.g., "Basic", "Advanced", "Expert")
- `platform` (str, optional): Filter by platform (e.g., "Mobile Interfaces")
- `tags` (list, optional): Filter by tags (returns environments matching any tag)
- `force_refresh` (bool): Bypass cache and fetch fresh data (default: False)

**Returns:** List of environment metadata dictionaries

**Raises:** `NetworkError` if fetching or parsing fails

**Example:**
```python
from scalewob import fetch_environments

# Get all environments
all_envs = fetch_environments()

# Filter by multiple criteria
filtered = fetch_environments(
    difficulty="Expert",
    platform="Mobile Interfaces"
)

# Force refresh cache
fresh = fetch_environments(force_refresh=True)
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
