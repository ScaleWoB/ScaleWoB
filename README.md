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
    browser='chrome',           # 'chrome', 'firefox', or 'safari'
    headless=False,             # Run in headless mode
    base_url='https://scalewob.github.io',
    timeout=5000                # Default timeout in milliseconds
)
```

## API Reference

### Initialization

#### `ScaleWoBAutomation(env_id, browser='chrome', headless=False, base_url='https://scalewob.github.io', timeout=5000)`

Initialize automation interface for ScaleWoB environments.

**Parameters:**
- `env_id` (str): Environment ID to launch
- `browser` (str): Browser type ('chrome', 'firefox', 'safari')
- `headless` (bool): Run browser in headless mode
- `base_url` (str): Base URL for ScaleWoB launcher
- `timeout` (int): Default timeout for operations in milliseconds

### Core Methods

#### `start()`

Initialize browser and navigate to environment launcher. Must be called before any other automation methods.

#### `start_evaluation()`

Start evaluation mode in the launcher UI. Clicks the Play Mode toggle and Start button to initialize evaluation mode.

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

Capture screenshot of iframe environment only.

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

## Exception Handling

```python
from scalewob import (
    ScaleWoBError,      # Base exception
    TimeoutError,       # Operation timeout
    CommandError,       # Command execution failure
    EvaluationError,    # Evaluation failure
    BrowserError        # Browser automation failure
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
