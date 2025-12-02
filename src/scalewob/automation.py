"""
Core automation class for ScaleWoB environments
"""

import json
import time
from typing import Any, Dict, List, Literal, Optional

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
        screenshot_quality: Screenshot quality - 'low' for 1x scale, 'high' for 3x scale (default: 'high')

    Note:
        Currently only Chrome browser is supported. The browser runs with stealth mode
        options to avoid automation detection.

    Example:
        >>> auto = ScaleWoBAutomation(env_id='booking-hotel-simple')
        >>> auto.start()
        >>> auto.start_evaluation()
        >>> auto.click(x=300, y=150)  # Click at coordinates
        >>> auto.type('New York')  # Type into focused element
        >>> result = auto.finish_evaluation({'destination': 'New York'})
    """

    def __init__(
        self,
        env_id: str,
        headless: bool = False,
        base_url: str = "https://niumascript.com/scalewob-env",
        timeout: int = 5000,
        screenshot_quality: Literal["low", "high"] = "high",
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
        self._screenshot_scale = 1.0 if screenshot_quality == "low" else 3.0

    def __enter__(self):
        """
        Context manager entry.

        Returns:
            self: The ScaleWoBAutomation instance for use in the with statement
        """
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

        Configures Chrome with mobile emulation (iPhone viewport), stealth mode
        options to avoid automation detection, and headless mode if specified.
        Sets up a 390x844 viewport with 3x pixel ratio for mobile testing.

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
        mobile_emulation = {
            "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        }
        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        self.driver = webdriver.Chrome(options=options)

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

        # If no end_point specified, use start_point (tap/long_press)
        if end_point is None:
            end_x, end_y = start_x, start_y
        else:
            end_x, end_y = end_point

        from selenium.common.exceptions import MoveTargetOutOfBoundsException
        from selenium.webdriver.common.actions import interaction
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        from selenium.webdriver.common.actions.pointer_input import PointerInput

        try:
            pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
            actions = ActionBuilder(self.driver, mouse=pointer)

            actions.pointer_action.move_to_location(start_x, start_y)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(press_duration)
            actions.pointer_action.move_to_location(end_x, end_y)
            actions.pointer_action.pause(move_duration)
            actions.pointer_action.pointer_up()

            actions.perform()

        except MoveTargetOutOfBoundsException as e:
            raise CommandError(
                f"Coordinates ({start_x}, {start_y}) or ({end_x}, {end_y}) is out of view port: {e}"
            )

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
        self._execute_mobile_touch((x, y), move_duration=0)
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

        delta_map = {
            "left": (x - distance, y),
            "right": (x + distance, y),
            "up": (x, y - distance),
            "down": (x, y + distance),
        }

        self._execute_mobile_touch((x, y), delta_map[direction], move_duration=0.5)
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

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            duration: Duration of press in milliseconds
        """
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

        self._execute_mobile_touch((x, y), (end_x, end_y))
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

    def take_screenshot(self, format: str = "base64") -> Any:
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

        # Verify environment is ready (start() already waited for DOM)
        time.sleep(1)  # Buffer for any initialization

        try:
            state = self.driver.execute(
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

    def finish_evaluation(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Finish evaluation and get results.

        Sends the evaluate command to the environment with the collected trajectory.
        The trajectory of all actions since start_evaluation() is automatically included.

        Args:
            params: Evaluation parameters (environment-specific, optional)

        Returns:
            Evaluation result dictionary. Contains 'success' field indicating whether
            the task was completed correctly. A result with success=False is a valid
            return value (task failed), not an error.

        Raises:
            EvaluationError: If evaluation not started or environment communication fails
            TimeoutError: If evaluation times out

        Example:
            >>> result = auto.finish_evaluation({'destination': 'New York'})
            >>> if result['success']:
            ...     print("Task completed successfully!")
            ... else:
            ...     print(f"Task failed: {result.get('message', 'Unknown reason')}")
        """
        if not self._sdk_evaluation_active:
            raise EvaluationError(
                "Evaluation not started. Call start_evaluation() first."
            )

        try:
            # Merge trajectory into params
            eval_params = params or {}
            eval_params["trajectory"] = self._trajectory

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
