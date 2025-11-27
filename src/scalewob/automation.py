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

    def _execute_click(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute click command directly."""
        assert self.driver is not None  # Type narrowing for type checker

        x = params.get("x", 0)
        y = params.get("y", 0)
        delay = params.get("options", {}).get("delay", 100)

        script = f"""
        return (function() {{
            try {{
                // Wait for delay
                const startTime = Date.now();
                while (Date.now() - startTime < {delay}) {{}}

                // Get element at coordinates
                const element = document.elementFromPoint({x}, {y});
                if (!element) {{
                    return {{success: false, error: 'No element at coordinates ({x}, {y})'}};
                }}

                // Focus the element if it's focusable
                if (element.focus && typeof element.focus === 'function') {{
                    try {{
                        element.focus();
                    }} catch (e) {{
                        // Some elements may throw when focusing, ignore
                    }}
                }}

                // Create and dispatch click event
                const clickEvent = new MouseEvent('click', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: {x},
                    clientY: {y}
                }});
                element.dispatchEvent(clickEvent);

                // Also trigger native click for form elements
                if (element.click) {{
                    element.click();
                }}

                // Get element info
                const rect = element.getBoundingClientRect();
                return {{
                    success: true,
                    element: {{
                        tagName: element.tagName,
                        id: element.id || '',
                        className: element.className || '',
                        text: element.textContent?.substring(0, 100) || '',
                        x: rect.left + rect.width / 2,
                        y: rect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height
                    }}
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)
        if not result.get("success"):
            raise CommandError(f"Click failed: {result.get('error', 'Unknown error')}")

        return result.get("element", {})

    def _execute_type(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute type command directly."""
        assert self.driver is not None  # Type narrowing for type checker

        text = params.get("text", "")
        typing_delay = params.get("options", {}).get("typingDelay", 50)

        script = f"""
        return (function() {{
            try {{
                const text = {json.dumps(text)};
                const typingDelay = {typing_delay};

                // Get focused element
                const element = document.activeElement;
                if (!element || (element.tagName !== 'INPUT' &&
                               element.tagName !== 'TEXTAREA' && !element.isContentEditable)) {{
                    return {{success: false, error: 'No input element focused'}};
                }}

                // Type each character with delay
                for (let i = 0; i < text.length; i++) {{
                    const char = text[i];

                    // Dispatch keydown event
                    const keydownEvent = new KeyboardEvent('keydown', {{
                        key: char,
                        bubbles: true,
                        cancelable: true
                    }});
                    element.dispatchEvent(keydownEvent);

                    // Update value
                    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {{
                        element.value += char;
                        // Trigger input event
                        const inputEvent = new Event('input', {{bubbles: true}});
                        element.dispatchEvent(inputEvent);
                    }} else if (element.isContentEditable) {{
                        element.textContent += char;
                    }}

                    // Dispatch keyup event
                    const keyupEvent = new KeyboardEvent('keyup', {{
                        key: char,
                        bubbles: true,
                        cancelable: true
                    }});
                    element.dispatchEvent(keyupEvent);

                    // Delay between characters (busy wait)
                    const startTime = Date.now();
                    while (Date.now() - startTime < typingDelay) {{}}
                }}

                // Trigger change event
                const changeEvent = new Event('change', {{bubbles: true}});
                element.dispatchEvent(changeEvent);

                // Get element info
                const rect = element.getBoundingClientRect();
                return {{
                    success: true,
                    element: {{
                        tagName: element.tagName,
                        id: element.id || '',
                        className: element.className || '',
                        type: element.type || '',
                        value: element.value || element.textContent || '',
                        x: rect.left + rect.width / 2,
                        y: rect.top + rect.height / 2
                    }}
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)

        if not result.get("success"):
            raise CommandError(f"Type failed: {result.get('error', 'Unknown error')}")

        return result.get("element", {})

    def _execute_scroll(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute scroll command directly."""
        assert self.driver is not None  # Type narrowing for type checker

        x = params.get("x", 0)
        y = params.get("y", 0)
        direction = params.get("direction", "down")
        distance = params.get("options", {}).get("distance", 100)

        # Calculate deltaX and deltaY based on direction
        delta_map = {
            "down": (0, distance),
            "up": (0, -distance),
            "right": (distance, 0),
            "left": (-distance, 0),
        }
        deltaX, deltaY = delta_map.get(direction, (0, distance))

        script = f"""
        return (function() {{
            try {{
                const element = document.elementFromPoint({x}, {y});
                if (!element) {{
                    return {{success: false, error: 'No element at coordinates'}};
                }}

                // Create and dispatch wheel event
                const wheelEvent = new WheelEvent('wheel', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: {x},
                    clientY: {y},
                    deltaX: {deltaX},
                    deltaY: {deltaY},
                    deltaMode: WheelEvent.DOM_DELTA_PIXEL
                }});
                element.dispatchEvent(wheelEvent);

                // Also perform actual scroll
                let scrollElement = element;
                while (scrollElement && scrollElement !== document.body) {{
                    if (scrollElement.scrollHeight > scrollElement.clientHeight ||
                        scrollElement.scrollWidth > scrollElement.clientWidth) {{
                        break;
                    }}
                    scrollElement = scrollElement.parentElement;
                }}

                if (!scrollElement) {{
                    scrollElement = window;
                }}

                if (scrollElement === window) {{
                    window.scrollBy({deltaX}, {deltaY});
                }} else {{
                    scrollElement.scrollLeft += {deltaX};
                    scrollElement.scrollTop += {deltaY};
                }}

                return {{
                    success: true,
                    deltaX: {deltaX},
                    deltaY: {deltaY}
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)

        if not result.get("success"):
            raise CommandError(f"Scroll failed: {result.get('error', 'Unknown error')}")

        return {"deltaX": result.get("deltaX", 0), "deltaY": result.get("deltaY", 0)}

    def _execute_long_press(
        self, params: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Execute long press command directly."""
        assert self.driver is not None  # Type narrowing for type checker

        x = params.get("x", 0)
        y = params.get("y", 0)
        duration = params.get("options", {}).get("duration", 1000)

        script = f"""
        return (function() {{
            try {{
                const element = document.elementFromPoint({x}, {y});
                if (!element) {{
                    return {{success: false, error: 'No element at coordinates'}};
                }}

                // Dispatch touchstart
                const touchstartEvent = new TouchEvent('touchstart', {{
                    bubbles: true,
                    cancelable: true,
                    touches: [new Touch({{
                        identifier: 0,
                        target: element,
                        clientX: {x},
                        clientY: {y}
                    }})]
                }});
                element.dispatchEvent(touchstartEvent);

                // Wait for duration
                const startTime = Date.now();
                while (Date.now() - startTime < {duration}) {{}}

                // Dispatch touchend
                const touchendEvent = new TouchEvent('touchend', {{
                    bubbles: true,
                    cancelable: true,
                    changedTouches: [new Touch({{
                        identifier: 0,
                        target: element,
                        clientX: {x},
                        clientY: {y}
                    }})]
                }});
                element.dispatchEvent(touchendEvent);

                // Get element info
                const rect = element.getBoundingClientRect();
                return {{
                    success: true,
                    element: {{
                        tagName: element.tagName,
                        id: element.id || '',
                        className: element.className || '',
                        text: element.textContent?.substring(0, 100) || ''
                    }}
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)

        if not result.get("success"):
            raise CommandError(
                f"Long press failed: {result.get('error', 'Unknown error')}"
            )

        return result.get("element", {})

    def _execute_drag(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute drag command directly."""
        assert self.driver is not None  # Type narrowing for type checker

        x = params.get("x", 0)
        y = params.get("y", 0)
        direction = params.get("direction", "down")
        distance = params.get("options", {}).get("distance", 100)

        # Calculate end coordinates
        end_coords = {
            "down": (x, y + distance),
            "up": (x, y - distance),
            "right": (x + distance, y),
            "left": (x - distance, y),
        }
        end_x, end_y = end_coords.get(direction, (x, y + distance))

        script = f"""
        return (function() {{
            try {{
                const element = document.elementFromPoint({x}, {y});
                if (!element) {{
                    return {{success: false, error: 'No element at coordinates'}};
                }}

                // Dispatch touchstart
                const touchstartEvent = new TouchEvent('touchstart', {{
                    bubbles: true,
                    cancelable: true,
                    touches: [new Touch({{
                        identifier: 0,
                        target: element,
                        clientX: {x},
                        clientY: {y}
                    }})]
                }});
                element.dispatchEvent(touchstartEvent);

                // Dispatch touchmove
                const touchmoveEvent = new TouchEvent('touchmove', {{
                    bubbles: true,
                    cancelable: true,
                    touches: [new Touch({{
                        identifier: 0,
                        target: element,
                        clientX: {end_x},
                        clientY: {end_y}
                    }})]
                }});
                element.dispatchEvent(touchmoveEvent);

                // Dispatch touchend
                const touchendEvent = new TouchEvent('touchend', {{
                    bubbles: true,
                    cancelable: true,
                    changedTouches: [new Touch({{
                        identifier: 0,
                        target: element,
                        clientX: {end_x},
                        clientY: {end_y}
                    }})]
                }});
                element.dispatchEvent(touchendEvent);

                // Get element info
                const rect = element.getBoundingClientRect();
                return {{
                    success: true,
                    element: {{
                        tagName: element.tagName,
                        id: element.id || '',
                        className: element.className || '',
                        text: element.textContent?.substring(0, 100) || ''
                    }}
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)

        if not result.get("success"):
            raise CommandError(f"Drag failed: {result.get('error', 'Unknown error')}")

        return result.get("element", {})

    def _execute_back(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute back navigation command."""
        assert self.driver is not None  # Type narrowing for type checker

        self.driver.back()
        time.sleep(0.5)  # Wait for navigation
        return {"success": True}

    def _execute_get_state(
        self, params: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Get current page state."""
        assert self.driver is not None  # Type narrowing for type checker

        script = """
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
        return self.driver.execute_script(script)

    def _execute_get_element_info(
        self, params: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Get element information at coordinates."""
        assert self.driver is not None  # Type narrowing for type checker

        x = params.get("x", 0)
        y = params.get("y", 0)

        script = f"""
        return (function() {{
            try {{
                const element = document.elementFromPoint({x}, {y});
                if (!element) {{
                    return {{success: false, error: 'No element at coordinates'}};
                }}

                const rect = element.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(element);

                return {{
                    success: true,
                    tagName: element.tagName,
                    id: element.id || '',
                    className: element.className || '',
                    text: element.textContent?.substring(0, 100) || '',
                    value: element.value || '',
                    type: element.type || '',
                    href: element.href || '',
                    src: element.src || '',
                    position: {{
                        x: rect.left + rect.width / 2,
                        y: rect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        left: rect.left,
                        bottom: rect.bottom,
                        right: rect.right
                    }},
                    style: {{
                        display: computedStyle.display,
                        visibility: computedStyle.visibility,
                        opacity: computedStyle.opacity
                    }},
                    attributes: Array.from(element.attributes).reduce((acc, attr) => {{
                        acc[attr.name] = attr.value;
                        return acc;
                    }}, {{}})
                }};
            }} catch (error) {{
                return {{success: false, error: error.message}};
            }}
        }})();
        """

        result = self.driver.execute_script(script)

        if not result.get("success"):
            raise CommandError(
                f"Get element info failed: {result.get('error', 'Unknown error')}"
            )

        # Remove success flag from result
        result.pop("success", None)
        return result

    def _execute_custom_script(
        self, params: Dict[str, Any], timeout: int
    ) -> Dict[str, Any]:
        """Execute custom JavaScript."""
        assert self.driver is not None  # Type narrowing for type checker

        script = params.get("script", "")
        if not script:
            raise CommandError("No script provided")

        try:
            result = self.driver.execute_script(script)
            return result if result is not None else {}
        except Exception as e:
            raise CommandError(f"Script execution failed: {str(e)}")

    def _execute_evaluate(self, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Execute evaluation command."""
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
        self._wait_for_dom_ready(timeout=10000)

    def _send_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute command directly in the standalone webpage.

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

        # Map commands to JavaScript implementations
        command_handlers = {
            "click": self._execute_click,
            "type": self._execute_type,
            "scroll": self._execute_scroll,
            "long_press": self._execute_long_press,
            "drag": self._execute_drag,
            "back": self._execute_back,
            "get-state": self._execute_get_state,
            "execute-script": self._execute_custom_script,
            "get-element-info": self._execute_get_element_info,
            "evaluate": self._execute_evaluate,
        }

        handler = command_handlers.get(command)
        if not handler:
            raise CommandError(f"Unknown command: {command}")

        try:
            result = handler(params, timeout)
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
        # Execute JavaScript to find element and get its info
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
            state = self.get_state()
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
