"""
Core automation class for ScaleWoB environments
"""

import json
import time
from typing import Any, Dict, List, Literal, Optional, overload

from PIL.Image import Image

from .exceptions import BrowserError, CommandError, EvaluationError, TimeoutError


class ScaleWoBAutomation:
    """
    Main automation interface for ScaleWoB environments.

    This class provides methods to interact with ScaleWoB environments
    through browser automation using Selenium with Chrome.

    Args:
        env_id: Environment ID to launch
        headless: Run browser in headless mode (default: False)
        base_url: Base URL for ScaleWoB environments (default: https://niumascript.com/scalewob-env)
        timeout: Default timeout for operations in milliseconds (default: 5000)
        screenshot_quality: Screenshot quality - 'low' for 1x scale, 'high' for 3x scale on mobile (default: 'high')
        platform: Platform type - 'mobile' for iPhone emulation, 'desktop' for standard browser (default: 'mobile')

    Note:
        Currently only Chrome browser is supported. The browser runs with stealth mode
        options to avoid automation detection.

        Mobile mode uses iPhone viewport (390x844) with 3x pixel ratio and touch interactions.
        Desktop mode uses standard browser window (1280x800) with mouse interactions.

    Example:
        >>> # Using context manager (recommended)
        >>> with ScaleWoBAutomation('booking-hotel-simple') as auto:
        ...     auto.start_evaluation()
        ...     auto.click(x=300, y=150)  # Click at coordinates
        ...     auto.type('New York')  # Type into focused element
        ...     result = auto.finish_evaluation({'destination': 'New York'})
        >>>
        >>> # Manual start/stop
        >>> auto = ScaleWoBAutomation(env_id='booking-hotel-simple')
        >>> auto.start()
        >>> auto.start_evaluation()
        >>> auto.click(x=300, y=150)
        >>> auto.type('New York')
        >>> result = auto.finish_evaluation({'destination': 'New York'})
        >>> auto.close()
        >>>
        >>> # Desktop mode
        >>> with ScaleWoBAutomation('booking-hotel-simple', platform='desktop') as auto:
        ...     auto.start_evaluation()
        ...     auto.click(x=640, y=400)  # Click at coordinates
    """

    def __init__(
        self,
        env_id: str,
        headless: bool = False,
        base_url: str = "https://niumascript.com/scalewob-env",
        timeout: int = 5000,
        screenshot_quality: Literal["low", "high"] = "high",
        platform: Literal["mobile", "desktop"] = "mobile",
    ):
        self.env_id = env_id
        self.headless = headless
        self.base_url = base_url
        self.default_timeout = timeout
        self.command_id = 0
        self.driver = None
        self._sdk_evaluation_active = False
        self._last_evaluation_result = None
        self._trajectory: List[Dict[str, Any]] = []
        self.platform = platform
        self._screenshot_scale = 1.0 if screenshot_quality == "low" else 3.0
        self._cached_tasks: Optional[List[Dict[str, Any]]] = None
        self._cached_original_schemas: Dict[Any, Dict[str, Any]] = {}

    def __enter__(self):
        """
        Context manager entry.

        Initializes the browser and navigates to the environment.
        Equivalent to calling start() manually.

        Returns:
            self: The ScaleWoBAutomation instance for use in the with statement
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - cleanup resources.

        Automatically closes the browser and cleans up resources when
        exiting the with statement, regardless of whether an exception occurred.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.close()

    def _init_driver(self):
        """
        Initialize Selenium WebDriver with Chrome.

        Configures Chrome with platform-specific settings:
        - Mobile: iPhone viewport (390x844, 3x pixel ratio) with touch emulation
        - Desktop: Standard browser window (1280x800)
        Both modes include stealth options to avoid automation detection.

        Raises:
            BrowserError: If Selenium is not installed
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
        except ImportError:
            raise BrowserError(
                "Selenium not installed. Install with: pip install selenium"
            )

        options = ChromeOptions()

        if self.headless:
            options.add_argument("--headless")

        # Common stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")

        mobile_profile = {
            "deviceMetrics": {
                "width": 390,
                "height": 844,
                "pixelRatio": self._screenshot_scale,
            },
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        }
        desktop_profile = {
            "width": 1280,
            "height": 800,
            "pixelRatio": self._screenshot_scale,
        }

        # Platform-specific configuration
        if self.platform == "mobile":
            options.add_experimental_option("mobileEmulation", mobile_profile)
        else:
            # Desktop mode - set window size
            options.add_argument(
                f"--window-size={desktop_profile['width']},{desktop_profile['height']}"
            )

        self.driver = webdriver.Chrome(options=options)

        # For desktop, ensure window is properly sized after creation
        if self.platform == "desktop":
            self.driver.set_window_size(
                desktop_profile["width"], desktop_profile["height"]
            )

    def _wait_for_dom_ready(self, timeout: int = 10000):
        """
        Wait for DOM to be fully loaded and interactive.

        Args:
            timeout: Maximum wait time in milliseconds

        Raises:
            TimeoutError: If DOM doesn't become ready within timeout
        """
        from selenium.webdriver.support.ui import WebDriverWait

        assert self.driver is not None  # Type narrowing for type checker

        try:
            # Wait for document.readyState to be 'complete'
            WebDriverWait(self.driver, timeout / 1000).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Ensure body exists with content
            WebDriverWait(self.driver, timeout / 1000).until(
                lambda d: d.execute_script(
                    "return document.body !== null && document.body.children.length > 0"
                )
            )

            # Small additional wait for any dynamic content
            time.sleep(0.5)

        except Exception as e:
            raise TimeoutError(f"DOM not ready within {timeout}ms: {str(e)}")

    def _get_viewport_dimensions(self) -> tuple[int, int]:
        """Get the current viewport dimensions from the browser."""
        assert self.driver is not None
        width = self.driver.execute_script("return window.innerWidth;")
        height = self.driver.execute_script("return window.innerHeight;")
        return int(width), int(height)

    def _clamp_coordinate(self, value: int, max_value: int) -> int:
        """Clamp a coordinate to be within valid bounds."""
        return max(0, min(value, max_value - 1))

    def _execute_mobile_touch(
        self,
        start_point: tuple[int, int],
        end_point: tuple[int, int] | None = None,
        press_duration: float = 0.1,
        move_duration: float = 0.3,
    ):
        """
        Unified function for all mobile gestures.

        Args:
            start_point: (x, y) starting coordinates
            end_point: (x, y) ending coordinates. If None, uses start_point (tap/long_press)
            press_duration: How long to hold down before moving (seconds)
            move_duration: Duration of movement (seconds)

        Gesture types by parameters:
            - Tap: end_point=None, press_duration=0.1
            - Long press: end_point=None, press_duration=1.0+
            - Swipe/Scroll: end_point!=start_point, move_duration=0.3
            - Drag: end_point!=start_point, move_duration=0.5+
        """
        assert self.driver is not None

        start_x, start_y = start_point
        viewport_width, viewport_height = self._get_viewport_dimensions()

        start_x, start_y = (
            self._clamp_coordinate(start_x, viewport_width),
            self._clamp_coordinate(start_y, viewport_height),
        )

        if end_point is None:
            end_x, end_y = start_x, start_y
        else:
            end_x, end_y = end_point
            end_x, end_y = (
                self._clamp_coordinate(end_x, viewport_width),
                self._clamp_coordinate(end_y, viewport_height),
            )

        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput

        pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=pointer)

        actions.pointer_action.move_to_location(start_x, start_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(press_duration)
        actions.pointer_action.move_to_location(end_x, end_y)
        actions.pointer_action.pause(move_duration)
        actions.pointer_action.pointer_up()

        actions.perform()

    def _execute_desktop_click(self, x: int, y: int):
        """
        Execute a standard mouse click at coordinates for desktop mode.

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
        """
        assert self.driver is not None

        viewport_width, viewport_height = self._get_viewport_dimensions()
        x = self._clamp_coordinate(x, viewport_width)
        y = self._clamp_coordinate(y, viewport_height)

        from selenium.webdriver.common.action_chains import ActionChains

        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(x, y).click().perform()
            actions.move_by_offset(-x, -y).perform()
        except Exception as e:
            raise CommandError(e)

    def _execute_desktop_scroll(self, x: int, y: int, direction: str, distance: int):
        """
        Execute scroll using JavaScript for desktop mode.

        Args:
            x: Horizontal coordinate (for element targeting)
            y: Vertical coordinate (for element targeting)
            direction: Scroll direction ('up', 'down', 'left', 'right')
            distance: Distance to scroll in pixels
        """
        assert self.driver is not None

        scroll_map = {
            "up": (0, -distance),
            "down": (0, distance),
            "left": (-distance, 0),
            "right": (distance, 0),
        }
        scroll_x, scroll_y = scroll_map[direction]

        # Scroll the window
        self.driver.execute_script(f"window.scrollBy({scroll_x}, {scroll_y});")

    def _execute_desktop_drag(self, x: int, y: int, end_x: int, end_y: int):
        """
        Execute drag using ActionChains for desktop mode.

        Args:
            x: Starting horizontal coordinate
            y: Starting vertical coordinate
            end_x: Ending horizontal coordinate
            end_y: Ending vertical coordinate
        """
        assert self.driver is not None

        viewport_width, viewport_height = self._get_viewport_dimensions()
        x = self._clamp_coordinate(x, viewport_width)
        y = self._clamp_coordinate(y, viewport_height)
        end_x = self._clamp_coordinate(end_x, viewport_width)
        end_y = self._clamp_coordinate(end_y, viewport_height)

        from selenium.webdriver.common.action_chains import ActionChains

        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(x, y).click_and_hold()
            actions.move_by_offset(end_x - x, end_y - y).release().perform()
            actions.move_by_offset(-end_x, -end_y).perform()
        except Exception as e:
            raise CommandError(e)

    def _execute_evaluate(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """
        Execute evaluation command via async JavaScript.

        Calls the environment's evaluateTask function with the provided parameters
        and waits for the result. Handles both successful evaluations and errors.

        Args:
            params: Evaluation parameters to pass to the environment
            timeout: Maximum wait time in milliseconds

        Returns:
            Evaluation result dictionary from the environment

        Raises:
            TimeoutError: If evaluation exceeds the timeout period
        """
        assert self.driver is not None  # Type narrowing for type checker

        script_async = f"""
        const callback = arguments[arguments.length - 1];
        const timeout = {timeout};

        (async function() {{
            try {{
                const params = {json.dumps(params)};
                let result;
                result = await window.evaluateTask(params);

                callback(result);
            }} catch (error) {{
                callback({{
                    success: false,
                    error: error.message
                }});
            }}
        }})();

        setTimeout(() => {{
            callback({{success: false, error: 'Evaluation timeout'}});
        }}, timeout);
        """

        result = self.driver.execute_async_script(script_async)

        # Only raise exception for actual errors (timeout, JS exceptions)
        # A result with success=false is a valid evaluation result (task failed)
        if isinstance(result, dict) and result.get("error") == "Evaluation timeout":
            raise TimeoutError("Evaluation timed out")

        return result

    def start(self):
        """
        Initialize browser and navigate to environment.

        This method must be called before any other automation methods.
        Waits for DOM to be fully loaded and interactive.

        Note:
            When using the context manager (with statement), this method is
            automatically called by __enter__, so you don't need to call it manually.
        """
        # Initialize Selenium driver
        self._init_driver()

        if not self.driver:
            raise ValueError("self.driver not initialized")

        # Navigate to standalone environment page
        env_url = f"{self.base_url}/{self.env_id}/index.html"
        self.driver.get(env_url)

        # Wait for DOM to be ready
        self._wait_for_dom_ready(timeout=self.default_timeout)

        # Clear cached tasks and fetch fresh ones
        self._cached_tasks = None
        self._cached_original_schemas.clear()
        self._fetch_tasks_internal()  # Auto-fetch tasks on start

    def _record_trajectory(self, action_type: str, data: Dict[str, Any]):
        """Record an action in the trajectory history."""
        trajectory_entry = {
            "timestamp": int(time.time() * 1000),  # Milliseconds
            "type": action_type,
            "data": data,
        }
        self._trajectory.append(trajectory_entry)

    def click(self, x: int, y: int):
        """
        Click at coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)

        if self.platform == "mobile":
            self._execute_mobile_touch((x, y), move_duration=0)
        else:
            self._execute_desktop_click(x, y)

        self._record_trajectory(
            "click",
            {"x": x, "y": y},
        )

    def type(self, text: str, append: bool = False):
        assert self.driver is not None

        active_element = self.driver.switch_to.active_element
        tag_name = active_element.tag_name.lower()

        if (
            tag_name not in ["input", "textarea"]
            and active_element.get_attribute("contenteditable") != "true"
        ):
            raise CommandError(f"Active element is '{tag_name}', not an input field")

        # Check if element is enabled and interactable
        if not active_element.is_enabled():
            raise CommandError("Input element is disabled")

        try:
            if not append:
                active_element.clear()

            active_element.send_keys(text)
        except Exception as e:
            raise CommandError(e)

        self._record_trajectory(
            "input",
            {"text": text},
        )

    def scroll(self, x: int, y: int, direction: str = "down", distance: int = 100):
        """
        Scroll in direction from coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            direction: Scroll direction ('up', 'down', 'left', 'right')
            distance: Distance to scroll in pixels
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)

        if self.platform == "mobile":
            delta_map = {
                "left": (x - distance, y),
                "right": (x + distance, y),
                "up": (x, y - distance),
                "down": (x, y + distance),
            }
            self._execute_mobile_touch((x, y), delta_map[direction], move_duration=0.5)
        else:
            self._execute_desktop_scroll(x, y, direction, distance)

        self._record_trajectory(
            "scroll",
            {
                "x": x,
                "y": y,
                "direction": direction,
                "distance": distance,
            },
        )

    def long_press(self, x: int, y: int, duration: int = 1000):
        """
        Long press at coordinates (x, y).

        Note: This is a mobile-specific gesture and will raise an error on desktop platform.

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            duration: Duration of press in milliseconds

        Raises:
            CommandError: If called on desktop platform
        """
        if self.platform == "desktop":
            raise CommandError(
                "long_press is not supported on desktop platform. Use click() instead."
            )

        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        self._execute_mobile_touch((x, y), press_duration=duration / 1000)
        self._record_trajectory(
            "touch",
            {
                "x": x,
                "y": y,
                "duration": duration,
                "touchType": "long_press",
            },
        )

    def drag(self, x: int, y: int, end_x: int, end_y: int):
        """
        Drag from start coordinates to end coordinates.

        Performs a touch drag gesture by pressing at the start point,
        moving to the end point, and releasing. Coordinates are automatically
        scaled based on screenshot quality settings.

        Args:
            x: Starting horizontal coordinate
            y: Starting vertical coordinate
            end_x: Ending horizontal coordinate
            end_y: Ending vertical coordinate
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        end_x = int(float(end_x) / self._screenshot_scale)
        end_y = int(float(end_y) / self._screenshot_scale)

        if self.platform == "mobile":
            self._execute_mobile_touch((x, y), (end_x, end_y))
        else:
            self._execute_desktop_drag(x, y, end_x, end_y)

        self._record_trajectory(
            "touch",
            {
                "x": x,
                "y": y,
                "end_x": end_x,
                "end_y": end_y,
                "touchType": "drag",
            },
        )

    def back(self):
        """
        Go back in navigation history.
        """
        assert self.driver is not None
        self.driver.back()
        self._record_trajectory("back", {})

    @overload
    def take_screenshot(self, format: Literal["base64"]) -> str: ...

    @overload
    def take_screenshot(self, format: Literal["pil"]) -> Image: ...

    def take_screenshot(self, format: str = "base64") -> str | Image:
        """
        Capture screenshot of environment.

        Args:
            format: Return format - "base64" for raw base64 string, "pil" for PIL Image object

        Returns:
            If format="base64": Raw base64 string
            If format="pil": PIL Image object

        Raises:
            ValueError: If format is invalid
            ImportError: If PIL not installed when format="pil"
        """
        if not self.driver:
            raise ValueError("self.driver not initialized")

        from selenium.webdriver.support.ui import WebDriverWait

        # Ensure page is ready
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Take screenshot directly from main window
        base64_data = self.driver.get_screenshot_as_base64()

        if format == "base64":
            return base64_data
        elif format == "pil":
            import base64
            import io

            from PIL import Image

            image_bytes = base64.b64decode(base64_data)
            return Image.open(io.BytesIO(image_bytes))
        else:
            raise ValueError(f"Invalid format: {format}. Use 'base64' or 'pil'")

    def start_evaluation(self):
        """
        Start evaluation mode.

        Ensures the environment is fully initialized and clears the trajectory
        for a fresh evaluation. The environment loads ready to interact without
        requiring any UI button clicks.

        This method calls window.reset() to restore the environment to its initial
        state, allowing multiple evaluations to be run in the same browser session.

        Raises:
            EvaluationError: If evaluation is already active or environment not ready
            BrowserError: If browser not initialized (call start() first)
        """
        if self._sdk_evaluation_active:
            raise EvaluationError("Evaluation already started")

        if not self.driver:
            raise BrowserError("Browser not initialized. Call start() first.")

        # Clear trajectory for fresh start
        self._trajectory = []

        # Reset environment to initial state
        self.driver.execute_script("window.reset();")

        # Wait for environment to stabilize after reset
        time.sleep(1)  # Buffer for reset and initialization

        try:
            state = self.driver.execute_script(
                """
        return {
            url: window.location.href,
            title: document.title,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight,
                scrollX: window.scrollX,
                scrollY: window.scrollY
            },
            readyState: document.readyState
        };
        """
            )
            if state.get("readyState") != "complete":
                raise EvaluationError("Environment not fully loaded")
        except Exception as e:
            raise EvaluationError(f"Failed to verify environment state: {str(e)}")

        # Mark evaluation as active
        self._sdk_evaluation_active = True

    @property
    def tasks(self) -> List[Dict[str, Any]]:
        """
        Tasks available in the current environment.

        Tasks are automatically fetched when `start()` is called and cached
        for the lifetime of the browser session. Access this property to get
        the list of available tasks.

        Returns:
            List of task dictionaries, each containing:
            - task_id: Task identifier (from window.getTasks(), may be string or number)
            - description: Task description
            - params: Optional JSON schema defining expected parameters (if present,
              you must provide actual values matching this schema when calling
              finish_evaluation())

        Raises:
            BrowserError: If environment is not loaded (start() not called)
            CommandError: If task fetching failed

        Example:
            >>> auto = ScaleWoBAutomation('booking-hotel-simple')
            >>> auto.start()
            >>> for idx, task in enumerate(auto.tasks):
            ...     print(f"Task {idx}: {task['description']}")
        """
        if self._cached_tasks is None:
            raise BrowserError(
                "Tasks not available. Call start() first to load the environment."
            )
        return self._cached_tasks

    def _fetch_tasks_internal(self) -> List[Dict[str, Any]]:
        """
        Internal method to fetch tasks from the currently loaded environment.

        Called automatically by `start()`. Fetches tasks via window.getTasks()
        and caches them for automatic validation in finish_evaluation().

        Returns:
            List of task dictionaries (cached in self._cached_tasks)

        Raises:
            CommandError: If JavaScript execution fails
        """
        assert self.driver is not None  # Guaranteed by caller (start method)

        try:
            # Call window.getTasks() and return result
            tasks = self.driver.execute_script("return window.getTasks();")

            if tasks is None:
                self._cached_tasks = []
                return []

            # Normalize response format
            normalized_tasks = []
            for task in tasks:
                task_id = task.get("taskId")  # May be string or number
                original_schema = task.get("params")  # Optional JSON schema

                # Store original schema for const extraction in finish_evaluation()
                if original_schema is not None:
                    self._cached_original_schemas[task_id] = original_schema

                # Remove const fields from schema for user display
                cleaned_schema = None
                if original_schema is not None:
                    cleaned_schema = self._remove_const_fields(original_schema)

                    # If no properties left, remove params entirely
                    if (
                        not cleaned_schema.get("properties")
                        or len(cleaned_schema.get("properties", {})) == 0
                    ):
                        cleaned_schema = None

                normalized_tasks.append({
                    "task_id": task_id,
                    "description": task.get("task description", ""),
                    "params": cleaned_schema,  # Schema with const fields removed, or None
                })

            # Cache for user access (const fields removed)
            self._cached_tasks = normalized_tasks
            return normalized_tasks

        except Exception as e:
            raise CommandError(f"Failed to fetch tasks: {str(e)}")

    def _extract_const_values(
        self, schema: Dict[str, Any], path: str = ""
    ) -> Dict[str, Any]:
        """
        Extract all const values from a JSON Schema.

        Recursively traverses the schema to find all properties with const keyword,
        handling nested objects, oneOf, anyOf, allOf, and arrays.

        Args:
            schema: JSON Schema dictionary to extract const values from
            path: Current JSON path (for error reporting and nested const tracking)

        Returns:
            Dictionary mapping JSON paths to their const values

        Raises:
            CommandError: If conflicting const values found at same path

        Example:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "userId": {"const": 123},
            ...         "config": {
            ...             "type": "object",
            ...             "properties": {
            ...                 "mode": {"const": "advanced"}
            ...             }
            ...         }
            ...     }
            ... }
            >>> auto._extract_const_values(schema)
            {'userId': 123, 'config.mode': 'advanced'}
        """
        result = {}

        # Direct const field at current path
        if "const" in schema:
            const_value = schema["const"]
            if path in result:
                # Conflicting const values at same path
                if result[path] != const_value:
                    raise CommandError(
                        f"Conflicting const values at '{path}': "
                        f"{result[path]!r} vs {const_value!r}"
                    )
            else:
                result[path] = const_value

        # Nested objects in properties
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                new_path = f"{path}.{prop_name}" if path else prop_name
                result.update(self._extract_const_values(prop_schema, new_path))

        # oneOf/anyOf/allOf - extract from all subschemas
        for keyword in ["oneOf", "anyOf", "allOf"]:
            if keyword in schema:
                for subschema in schema[keyword]:
                    result.update(self._extract_const_values(subschema, path))

        # Arrays - extract from items schema
        if "items" in schema and isinstance(schema["items"], dict):
            result.update(self._extract_const_values(schema["items"], path))

        return result

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Navigate a nested dictionary using dot-notation path.

        Args:
            data: Dictionary to navigate
            path: Dot-notation path (e.g., "config.mode")

        Returns:
            Value at path, or None if path doesn't exist

        Example:
            >>> data = {"config": {"mode": "advanced"}}
            >>> auto._get_nested_value(data, "config.mode")
            'advanced'
            >>> auto._get_nested_value(data, "config.missing")
            None
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _merge_const_values(
        self, params: Dict[str, Any], const_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge const values into params, only if not already present.

        Converts dot-notation paths in const_values to nested structure
        and merges them into params.

        Args:
            params: User-provided parameters
            const_values: Const values with dot-notation paths

        Returns:
            New dictionary with merged params and const values

        Example:
            >>> params = {"destination": "New York"}
            >>> const_values = {"userId": 123, "config.mode": "advanced"}
            >>> auto._merge_const_values(params, const_values)
            {'destination': 'New York', 'userId': 123, 'config': {'mode': 'advanced'}}
        """
        import copy

        result = copy.deepcopy(params)

        for const_path, const_value in const_values.items():
            # Check if user already provided this value
            if self._get_nested_value(params, const_path) is not None:
                # User provided it, skip auto-injection
                continue

            # Build nested structure from dot-notation path
            keys = const_path.split(".")
            current = result

            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    # User provided a non-dict value at intermediate path
                    break
                current = current[key]

            # Set the final value
            current[keys[-1]] = const_value

        return result

    def _remove_const_fields(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove const fields from a JSON Schema.

        Recursively traverses the schema and removes any properties or subschemas
        that have const values, creating a simplified schema for user display.

        Args:
            schema: JSON Schema dictionary to remove const fields from

        Returns:
            Modified schema with const fields removed

        Example:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "destination": {"type": "string"},
            ...         "userId": {"const": 123}
            ...     }
            ... }
            >>> auto._remove_const_fields(schema)
            {'type': 'object', 'properties': {'destination': {'type': 'string'}}}
        """
        import copy

        result = copy.deepcopy(schema)

        # Track which properties were removed (had const)
        removed_props = []

        # Process nested objects in properties
        if "properties" in result:
            for prop_name, prop_schema in list(result["properties"].items()):
                # If property has const, remove the entire property
                if "const" in prop_schema:
                    del result["properties"][prop_name]
                    removed_props.append(prop_name)
                else:
                    # Recursively clean nested properties
                    result["properties"][prop_name] = self._remove_const_fields(
                        prop_schema
                    )

            # Clean up required list - remove const fields
            if "required" in result and removed_props:
                result["required"] = [
                    field for field in result["required"] if field not in removed_props
                ]
                # If no required fields left, remove the key
                if not result["required"]:
                    del result["required"]

        # Process oneOf/anyOf/allOf
        for keyword in ["oneOf", "anyOf", "allOf"]:
            if keyword in result:
                result[keyword] = [
                    self._remove_const_fields(subschema)
                    for subschema in result[keyword]
                ]

        # Process arrays
        if "items" in schema and isinstance(schema["items"], dict):
            result["items"] = self._remove_const_fields(schema["items"])

        return result

    def finish_evaluation(
        self,
        task_id: int = 0,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Finish evaluation and get results.

        Sends the evaluate command to the environment with the collected trajectory.
        The trajectory of all actions since start_evaluation() is automatically included.

        Args:
            task_id: Task index within the environment (default: 0). Used to identify
                which task in the environment's tasks array is being evaluated.
            params: Evaluation parameters (environment-specific, optional). Const fields
                from the task's JSON schema are automatically injected and don't need to
                be included. If the task requires parameters, they will be automatically
                validated against the task's JSON schema.

        Returns:
            Evaluation result dictionary. Contains 'success' field indicating whether
            the task was completed correctly. A result with success=False is a valid
            return value (task failed), not an error.

        Raises:
            EvaluationError: If evaluation not started or environment communication fails
            TimeoutError: If evaluation times out
            CommandError: If params don't match the task's required schema, or if
                attempting to override a const field with a different value

        Example:
            >>> result = auto.finish_evaluation(
            ...     task_id=0,
            ...     params={'destination': 'New York'}
            ... )
            >>> if result['success']:
            ...     print("Task completed successfully!")
            ... else:
            ...     print(f"Task failed: {result.get('message', 'Unknown reason')}")
        """
        if not self._sdk_evaluation_active:
            raise EvaluationError(
                "Evaluation not started. Call start_evaluation() first."
            )

        # Auto-validate params against task schema if available
        if self._cached_tasks is not None:
            # Find task by task_id
            task = None
            for t in self._cached_tasks:
                if t["task_id"] == task_id:
                    task = t
                    break

            # Get original schema (with const fields) for const extraction
            original_schema = self._cached_original_schemas.get(task_id)

            if task is not None and task.get("params") is not None:
                # Task has a params schema
                try:
                    from jsonschema import ValidationError, validate
                except ImportError:
                    raise CommandError(
                        "jsonschema package is required for param validation. "
                        "Install it with: pip install jsonschema"
                    )

                # Extract const values from original schema
                const_values = {}
                if original_schema is not None:
                    const_values = self._extract_const_values(original_schema)

                # Validate user doesn't override const with different value
                for const_path, const_value in const_values.items():
                    user_value = self._get_nested_value(params or {}, const_path)
                    if user_value is not None and user_value != const_value:
                        raise CommandError(
                            f"Cannot override const field '{const_path}': "
                            f"schema requires {const_value!r}, got {user_value!r}"
                        )

                # Merge const values into user params
                merged_params = self._merge_const_values(params or {}, const_values)

                # Validate merged params against cleaned schema (without const fields)
                try:
                    validate(instance=merged_params, schema=task["params"])
                except ValidationError as e:
                    raise CommandError(
                        f"Params validation failed for task '{task_id}': {e.message} "
                        f"(at path: {' -> '.join(str(p) for p in e.absolute_path)})"
                    )

                # Use merged params for evaluation
                params = merged_params

        try:
            # Merge trajectory into params
            eval_params = params or {}
            eval_params["trajectory"] = self._trajectory
            eval_params["taskId"] = task_id

            result = self._execute_evaluate(eval_params, timeout=self.default_timeout)
            self._last_evaluation_result = result
            self._sdk_evaluation_active = False
            return result
        except Exception as e:
            self._sdk_evaluation_active = False
            raise EvaluationError(f"Evaluation failed: {str(e)}")

    def get_evaluation_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the last evaluation result.

        Returns:
            Last evaluation result or None
        """
        return self._last_evaluation_result

    def get_trajectory(self) -> List[Dict[str, Any]]:
        """
        Get current action trajectory.

        Returns a copy of the trajectory history containing all actions
        performed since start_evaluation() was called.

        Returns:
            List of trajectory entries with timestamp, type, and data

        Example:
            >>> trajectory = auto.get_trajectory()
            >>> print(f"Collected {len(trajectory)} actions")
            >>> for action in trajectory:
            ...     print(f"{action['type']} at {action['timestamp']}")
        """
        return self._trajectory.copy()

    def clear_trajectory(self):
        """
        Clear the current trajectory history.

        This is useful if you want to reset the trajectory without
        restarting the evaluation. Note that start_evaluation()
        automatically clears the trajectory.

        Example:
            >>> auto.clear_trajectory()
            >>> print(len(auto.get_trajectory()))  # 0
        """
        self._trajectory = []

    def close(self):
        """Close browser and cleanup resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        self._sdk_evaluation_active = False
