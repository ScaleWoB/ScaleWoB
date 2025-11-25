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
    through browser automation using Selenium.

    Args:
        env_id: Environment ID to launch
        browser: Browser type ('chrome', 'firefox', 'safari')
        headless: Run browser in headless mode
        base_url: Base URL for ScaleWoB launcher (default: https://scalewob.github.io)
        timeout: Default timeout for operations in milliseconds
        screenshot_quality: Screenshot quality ('low' for 1x scale, 'high' for 3x scale)

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
        browser: Literal["chrome", "firefox", "safari"] = "chrome",
        headless: bool = False,
        base_url: str = "https://scalewob.github.io",
        timeout: int = 5000,
        screenshot_quality: Literal["low", "high"] = "high",
    ):
        self.env_id = env_id
        self.browser = browser
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
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.close()

    def _init_driver(self):
        """Initialize Selenium WebDriver"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.safari.options import Options as SafariOptions
        except ImportError:
            raise BrowserError(
                "Selenium not installed. Install with: pip install selenium"
            )

        if self.browser == "chrome":
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)
        elif self.browser == "firefox":
            options = FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            self.driver = webdriver.Firefox(options=options)
        elif self.browser == "safari":
            options = SafariOptions()
            self.driver = webdriver.Safari(options=options)
        else:
            raise BrowserError(f"Unsupported browser: {self.browser}")
        self.driver.maximize_window()

    def start(self):
        """
        Initialize browser and navigate to environment launcher.

        This method must be called before any other automation methods.
        """
        # Initialize Selenium driver
        self._init_driver()

        if not self.driver:
            raise ValueError("self.driver not initialized")

        # Navigate to launcher page
        launcher_url = f"{self.base_url}/#/launcher/{self.env_id}"
        self.driver.get(launcher_url)

        # Wait for page to load
        time.sleep(2)

    def _send_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send command to iframe via JavaScript injection.

        Args:
            command: Command name
            params: Command parameters
            timeout: Command timeout in milliseconds

        Returns:
            Command result payload

        Raises:
            CommandError: If command execution fails
            TimeoutError: If command times out
        """
        if params is None:
            params = {}

        if timeout is None:
            timeout = self.default_timeout

        if not self.driver:
            raise ValueError("self.driver not initialized")

        command_id = f"cmd_{self.command_id}"
        self.command_id += 1

        # JavaScript to send command and wait for response
        # CRITICAL: Must use Selenium's callback (arguments[arguments.length - 1])
        # NOT Promise resolve/reject - Selenium doesn't bridge Promises automatically
        script = f"""
        var callback = arguments[arguments.length - 1];

        const iframe = document.querySelector('iframe');
        if (!iframe) {{
            callback({{'error': 'Iframe not found'}});
            return;
        }}

        const commandId = '{command_id}';
        const timeout = {timeout};
        let timeoutId;

        const handler = (e) => {{
            if (e.data.type === 'scalewob-response' && e.data.id === commandId) {{
                window.removeEventListener('message', handler);
                clearTimeout(timeoutId);

                if (e.data.payload.success) {{
                    callback(e.data.payload.result);
                }} else {{
                    callback({{'error': e.data.payload.error || 'Command failed'}});
                }}
            }}
        }};

        window.addEventListener('message', handler);

        timeoutId = setTimeout(() => {{
            window.removeEventListener('message', handler);
            callback({{'error': 'Command timeout'}});
        }}, timeout);

        iframe.contentWindow.postMessage({{
            type: 'scalewob-command',
            id: commandId,
            payload: {{
                command: '{command}',
                params: {json.dumps(params)}
            }}
        }}, '*');
        """

        try:
            result = self.driver.execute_async_script(script)

            # Check if result contains an error from our callback
            if isinstance(result, dict) and "error" in result:
                error_msg = result["error"]
                if "timeout" in error_msg.lower():
                    raise TimeoutError(
                        f"Command '{command}' timed out after {timeout}ms"
                    )
                else:
                    raise CommandError(f"Command '{command}' failed: {error_msg}")

            return result
        except (TimeoutError, CommandError):
            raise
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                raise TimeoutError(f"Command '{command}' timed out after {timeout}ms")
            else:
                raise CommandError(f"Command '{command}' failed: {error_msg}")

    def _record_trajectory(self, action_type: str, data: Dict[str, Any]):
        """Record an action in the trajectory history."""
        trajectory_entry = {
            "timestamp": int(time.time() * 1000),  # Milliseconds
            "type": action_type,
            "data": data,
        }
        self._trajectory.append(trajectory_entry)

    def click(self, x: int, y: int, delay: int = 100) -> Dict[str, Any]:
        """
        Click at coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            delay: Delay before clicking in milliseconds

        Returns:
            Element information after click
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        result = self._send_command(
            "click", {"x": x, "y": y, "options": {"delay": delay}}
        )
        self._record_trajectory(
            "click",
            {
                "x": x,
                "y": y,
                "element": result.get("element"),
                "tagName": result.get("element", {}).get("tagName", ""),
                "id": result.get("element", {}).get("id", ""),
                "className": result.get("element", {}).get("className", ""),
                "text": result.get("element", {}).get("text", ""),
            },
        )
        return result

    def type(self, text: str, typing_delay: int = 50) -> Dict[str, Any]:
        """
        Type text into the currently focused element.

        Note: An element must be focused first (e.g., via click) before typing.

        Args:
            text: Text to type
            typing_delay: Delay between keystrokes in milliseconds

        Returns:
            Element information after typing
        """
        result = self._send_command(
            "type",
            {"text": text, "options": {"typingDelay": typing_delay}},
        )
        self._record_trajectory(
            "keypress",
            {
                "text": text,
                "element": result.get("element"),
                "target": {
                    "tagName": result.get("element", {}).get("tagName", ""),
                    "id": result.get("element", {}).get("id", ""),
                    "className": result.get("element", {}).get("className", ""),
                    "inputType": result.get("element", {}).get("type", ""),
                    "isInput": result.get("element", {}).get("tagName", "")
                    in ["INPUT", "TEXTAREA", "SELECT"],
                },
            },
        )
        return result

    def scroll(
        self, x: int, y: int, direction: str = "down", distance: int = 100
    ) -> Dict[str, Any]:
        """
        Scroll in direction from coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            direction: Scroll direction ('up', 'down', 'left', 'right')
            distance: Distance to scroll in pixels

        Returns:
            Scroll result
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        result = self._send_command(
            "scroll",
            {"x": x, "y": y, "direction": direction, "options": {"distance": distance}},
        )
        self._record_trajectory(
            "scroll",
            {
                "x": x,
                "y": y,
                "direction": direction,
                "distance": distance,
                "deltaX": result.get("deltaX", 0),
                "deltaY": result.get("deltaY", 0),
                "eventType": "wheel",
            },
        )
        return result

    def long_press(self, x: int, y: int, duration: int = 1000) -> Dict[str, Any]:
        """
        Long press at coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            duration: Duration of press in milliseconds

        Returns:
            Long press result
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        result = self._send_command(
            "long_press", {"x": x, "y": y, "options": {"duration": duration}}
        )
        self._record_trajectory(
            "touch",
            {
                "x": x,
                "y": y,
                "duration": duration,
                "touchType": "long_press",
                "element": result.get("element"),
            },
        )
        return result

    def drag(
        self, x: int, y: int, direction: str = "down", distance: int = 100
    ) -> Dict[str, Any]:
        """
        Drag from coordinates (x, y) in specified direction.

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate
            direction: Drag direction ('up', 'down', 'left', 'right')
            distance: Distance to drag in pixels

        Returns:
            Drag result
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        result = self._send_command(
            "drag",
            {"x": x, "y": y, "direction": direction, "options": {"distance": distance}},
        )
        self._record_trajectory(
            "touch",
            {
                "x": x,
                "y": y,
                "direction": direction,
                "distance": distance,
                "touchType": "drag",
                "element": result.get("element"),
            },
        )
        return result

    def back(self) -> Dict[str, Any]:
        """
        Go back in navigation history.

        Returns:
            Navigation result
        """
        result = self._send_command("back")
        self._record_trajectory(
            "navigation",
            {
                "action": "back",
            },
        )
        return result

    def get_state(self) -> Dict[str, Any]:
        """
        Get current environment state.

        Returns:
            Environment state including URL, title, viewport, etc.
        """
        return self._send_command("get-state")

    def take_screenshot(self, format: str = "base64") -> Any:
        """
        Capture screenshot of iframe environment only.

        Args:
            format: Return format - "base64" for raw base64 string, "pil" for PIL Image object

        Returns:
            If format="base64": Raw base64 string of iframe content
            If format="pil": PIL Image object of iframe content
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        if not self.driver:
            raise ValueError("self.driver not initialized")

        iframe = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        original_size = iframe.size
        original_width = original_size["width"]
        original_height = original_size["height"]
        iframe_src = iframe.get_attribute("src")

        if not iframe_src:
            raise ValueError("Iframe lacks `src` attribute")

        self.driver.execute_script(f"window.open('{iframe_src}', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[1])

        self.driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": original_width,
                "height": original_height,
                "deviceScaleFactor": self._screenshot_scale,
                "mobile": True,
                "screenOrientation": {"angle": 0, "type": "portraitPrimary"},
            },
        )
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        try:
            # Take screenshot of iframe element
            base64_data = self.driver.get_screenshot_as_base64()

            if format == "base64":
                return base64_data
            elif format == "pil":
                try:
                    import base64
                    import io

                    from PIL import Image

                    image_bytes = base64.b64decode(base64_data)
                    return Image.open(io.BytesIO(image_bytes))
                except ImportError:
                    raise ImportError(
                        "PIL/Pillow is required for format='pil'. Install with: pip install Pillow"
                    )
            else:
                raise ValueError(f"Invalid format: {format}. Use 'base64' or 'pil'")
        finally:
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

    def get_element_info(self, x: int, y: int) -> Dict[str, Any]:
        """
        Get information about element at coordinates (x, y).

        Args:
            x: Horizontal coordinate
            y: Vertical coordinate

        Returns:
            Element information (position, size, attributes, etc.)
        """
        x = int(float(x) / self._screenshot_scale)
        y = int(float(y) / self._screenshot_scale)
        return self._send_command("get-element-info", {"x": x, "y": y})

    def get_element_info_by_selector(self, selector: str) -> Dict[str, Any]:
        """
        Get information about first element matching selector.

        Note: This is a helper method that finds an element by CSS selector
        and returns its coordinates. The primary API uses coordinate-based
        interactions (get_element_info with x, y coordinates).

        Args:
            selector: CSS selector for element

        Returns:
            Element information (position, size, attributes, etc.)
        """
        # Execute JavaScript in iframe to find element and get its info
        script = f"""
            const element = document.querySelector('{selector}');
            if (!element) {{
                throw new Error('Element not found: {selector}');
            }}
            const rect = element.getBoundingClientRect();
            return {{
                tagName: element.tagName,
                id: element.id || '',
                className: element.className || '',
                text: element.textContent?.substring(0, 100) || '',
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2,
                width: rect.width,
                height: rect.height,
                visible: rect.width > 0 && rect.height > 0
            }};
        """
        return self.execute_script(script)

    def execute_script(self, script: str) -> Dict[str, Any]:
        """
        Execute arbitrary JavaScript in the environment.

        Args:
            script: JavaScript code to execute

        Returns:
            Script execution result
        """
        return self._send_command("execute-script", {"script": script})

    def start_evaluation(self):
        """
        Start evaluation mode in the launcher UI.

        This clicks the Play Mode toggle (if needed) and Start button to properly
        initialize evaluation mode through the frontend React UI.
        Waits for iframe to be ready before returning.
        """
        if self._sdk_evaluation_active:
            raise EvaluationError("Evaluation already started")

        if not self.driver:
            raise BrowserError("Browser not initialized. Call start() first.")

        # Clear trajectory for fresh start
        self._trajectory = []

        try:
            from selenium.webdriver.common.by import By

            # Check if Play Mode toggle is ON (green) - if so, click to turn it OFF
            play_mode_toggle = self.driver.find_element(
                By.XPATH,
                "//button[contains(@class, 'bg-green-600') or contains(@class, 'bg-gray-300')]",
            )

            # If toggle has green background, it's ON - click to switch to Evaluate Mode
            class_attr = play_mode_toggle.get_attribute("class")
            if class_attr and "bg-green-600" in class_attr:
                play_mode_toggle.click()
                time.sleep(0.5)

            # Click the Start button to begin evaluation
            start_button = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Start') and not(@disabled)]"
            )
            start_button.click()

            # Wait for iframe to be ready by checking the status indicator
            script = """
            const timeout = arguments[0];
            const callback = arguments[arguments.length - 1];
            const startTime = Date.now();

            const checkReady = () => {
                // Check if environment status is 'online' by looking for the Live indicator
                const liveIndicator = document.querySelector('[class*="bg-green-500"]');
                const parentText = liveIndicator?.parentElement?.textContent;

                if (parentText && parentText.includes('Live')) {
                    callback({ready: true});
                    return;
                }

                if (Date.now() - startTime > timeout) {
                    callback({ready: false, error: 'Timeout waiting for iframe'});
                    return;
                }

                setTimeout(checkReady, 200);
            };

            checkReady();
            """

            result = self.driver.execute_async_script(script, 10000)

            if not result.get("ready"):
                raise EvaluationError(
                    result.get("error", "Failed to wait for iframe ready")
                )

            # Mark evaluation as active
            self._sdk_evaluation_active = True

        except Exception as e:
            raise EvaluationError(f"Failed to start evaluation: {str(e)}")

    def finish_evaluation(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Finish evaluation and get results.

        This sends the evaluate command to the environment and waits for results.
        The trajectory of actions is automatically included in the evaluation.

        Args:
            params: Evaluation parameters (environment-specific)

        Returns:
            Evaluation result

        Raises:
            EvaluationError: If evaluation fails
        """
        if not self._sdk_evaluation_active:
            raise EvaluationError(
                "Evaluation not started. Call start_evaluation() first."
            )

        try:
            # Merge trajectory into params
            eval_params = params or {}
            eval_params["trajectory"] = self._trajectory

            result = self._send_command("evaluate", eval_params, timeout=10000)
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
