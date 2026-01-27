# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScaleWoB is a Python SDK for evaluating Computer-Use Agents through browser automation. It provides coordinate-based interaction with web environments using Selenium WebDriver, supporting both mobile (iPhone emulation) and desktop platforms.

**Core Architecture:**
- `ScaleWoBAutomation`: Main automation class that wraps Selenium WebDriver
- Coordinate-based interactions (click, type, scroll, drag) rather than element selectors
- Trajectory recording system that captures all actions for evaluation
- Platform-agnostic design with mobile/desktop mode switching
- Evaluation lifecycle: start() → start_evaluation() → actions → finish_evaluation()

## Development Commands

### Setup
```bash
uv sync                      # Install dependencies
uv run pre-commit install    # Install pre-commit hooks
```

### Code Quality
```bash
uv run poe format            # Format code (ruff sort imports + format)
uv run poe check             # Run all checks (format, lint, typecheck)
uv run poe fix               # Auto-fix linting issues
uv run poe fix_unsafe        # Auto-fix with unsafe fixes
```

### Individual Tools
```bash
ruff format . --preview                  # Format only
ruff check . --preview                   # Lint only
pyright                                  # Type check only
```

### Release Management
```bash
uv run poe release_preview   # Preview next version (dry-run)
uv run poe release           # Create release (requires GH_TOKEN)
```

## Code Architecture

### Module Structure
- `src/scalewob/__init__.py` - Public API exports
- `src/scalewob/automation.py` - Core `ScaleWoBAutomation` class (~745 lines)
- `src/scalewob/exceptions.py` - Custom exception hierarchy
- `src/scalewob/api.py` - Environment metadata fetching with caching

### Key Design Patterns

**Platform Abstraction:**
The SDK supports two platforms with different interaction models:
- **Mobile mode** (default): iPhone viewport (390x844), touch interactions via `PointerInput(POINTER_TOUCH)`
- **Desktop mode**: Standard browser (1280x800), mouse interactions via `ActionChains`

Platform-specific methods:
- `_execute_mobile_touch()` - Unified touch gesture handler (tap, long press, swipe, drag)
- `_execute_desktop_click()`, `_execute_desktop_scroll()`, `_execute_desktop_drag()` - Desktop equivalents

**Coordinate Scaling:**
Screenshots use configurable quality ('low'=1x, 'high'=3x scale). All public methods automatically scale coordinates:
```python
x = int(float(x) / self._screenshot_scale)
```

**Trajectory Recording:**
Every action is recorded with timestamp and data via `_record_trajectory()`. The trajectory is:
- Cleared on `start_evaluation()`
- Accumulated during interaction
- Sent to environment in `finish_evaluation()`

**Evaluation Lifecycle:**
```python
auto.start()              # Initialize browser, navigate to env
auto.start_evaluation()   # Clear trajectory, verify ready state
# ... perform actions ...
result = auto.finish_evaluation(params)  # Send trajectory, get results
```

### Exception Hierarchy
All exceptions inherit from `ScaleWoBError`:
- `TimeoutError` - Operation timeouts
- `CommandError` - Action execution failures
- `EvaluationError` - Evaluation lifecycle errors
- `BrowserError` - Browser initialization failures
- `NetworkError` - API/network failures

### Important Implementation Details

**Selenium Stealth Mode:**
Chrome is configured with anti-detection options:
- `--disable-blink-features=AutomationControlled`
- `excludeSwitches: ["enable-automation"]`
- Custom user agents for mobile emulation

**Async JavaScript Evaluation:**
`_execute_evaluate()` uses `execute_async_script()` to call `window.evaluateTask()` with timeout handling.

**DOM Ready Waiting:**
`_wait_for_dom_ready()` ensures:
1. `document.readyState === 'complete'`
2. `document.body` exists with children
3. 500ms buffer for dynamic content

**Mouse Position Reset:**
Desktop mode resets mouse position after each action to prevent offset accumulation:
```python
actions.move_by_offset(-x, -y).perform()
```

## Code Style Requirements

- **Python Version**: 3.12+ required
- **Type Hints**: Required on all functions/methods
- **Docstrings**: Google-style with Args/Returns/Raises sections
- **Naming**: PascalCase for classes, snake_case for functions/variables
- **Imports**: Sorted by ruff (standard library first)
- **Timeouts**: Always in milliseconds (default: 5000ms)
- **Error Handling**: Use custom exceptions from `scalewob.exceptions`
- **Context Managers**: Implement `__enter__`/`__exit__` for resource cleanup

## Testing Considerations

When testing or debugging:
- Use `headless=False` to see browser interactions
- Mobile mode requires touch-specific Selenium APIs (`PointerInput`)
- Desktop mode uses standard `ActionChains`
- `long_press()` raises `CommandError` on desktop platform
- Coordinates in screenshots are scaled by `_screenshot_scale`

## Semantic Release

This project uses conventional commits and semantic-release:
- `feat:` - Minor version bump
- `fix:`, `perf:`, `refactor:` - Patch version bump
- `BREAKING CHANGE:` in footer - Major version bump (or minor if version < 1.0)
- Other types: `build`, `chore`, `ci`, `docs`, `style`, `test`

Version is stored in `pyproject.toml:project.version` and auto-updated on release.