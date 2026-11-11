from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import ConsoleMessage, Frame, Page

from nthu_library_benchmark.statistics import Statistics
from nthu_library_benchmark.storage import Storage

SEARCH_URL = (
    "https://nthu.primo.exlibrisgroup.com/discovery/search?"
    "query=any,contains,*&tab=Everything&"
    "search_scope=MyInst_and_CI_NoResearch&"
    "vid=886UST_NTHU:886UST_NTHU&lang=zh-tw&offset=0"
)
POLL_INTERVAL_MS = 100
RESULT_SELECTOR = "prm-brief-result-container"
SEARCH_INPUT_SELECTOR = (
    'input[type="search"]:visible, '
    'input[aria-label*="搜尋"]:visible, input[aria-label*="Search"]:visible, '
    'input[placeholder*="搜尋"]:visible, input[placeholder*="Search"]:visible'
)
SEARCH_BUTTON_SELECTOR = (
    'button[type="submit"]:visible, '
    'button[aria-label*="搜尋"]:visible, button[aria-label*="Search"]:visible, '
    'button[aria-label="提交檢索"]:visible, '
    'button[aria-label="Submit search"]:visible'
)
URL_EVENT_PREFIX = "__NTHU_BENCHMARK_URL__"

INIT_SCRIPT = f"""
    (() => {{
        const notifyUrlChange = () => console.log(
            '{URL_EVENT_PREFIX}' + location.href
        );
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;

        history.pushState = function(...args) {{
            const result = originalPushState.apply(this, args);
            notifyUrlChange();
            return result;
        }};
        history.replaceState = function(...args) {{
            const result = originalReplaceState.apply(this, args);
            notifyUrlChange();
            return result;
        }};

        addEventListener('popstate', notifyUrlChange);
        addEventListener('hashchange', notifyUrlChange);
    }})();
"""


@dataclass(frozen=True)
class TrackerConfig:
    """Settings for detecting when search results first become usable."""

    result_selector: str = RESULT_SELECTOR


class BrowserActivityTracker:
    """Measure time from each URL change until the first visible result."""

    def __init__(
        self,
        page: Page,
        storage: Storage,
        statistics: Statistics | None = None,
        config: TrackerConfig | None = None,
    ) -> None:
        self.page = page
        self.storage = storage
        self.statistics = statistics or Statistics()
        self.config = config or TrackerConfig()
        self.last_url = page.url
        self.last_event_at = time.perf_counter()
        self.operation_started_at: float | None = None
        self.operation_url = page.url
        self.completion_recorded = False

    def attach(self) -> None:
        """Register the page events used by the tracker."""
        self.page.on("console", self._handle_console)
        self.page.on("framenavigated", self._handle_frame_navigated)

    def check_operation_complete(self) -> bool:
        """Record completion once the first result is visible and populated."""
        if self.operation_started_at is None or self.completion_recorded:
            return self.completion_recorded
        if self.page.url != self.operation_url:
            return False

        first_result = self.page.locator(self.config.result_selector).first
        if not first_result.is_visible():
            return False
        if not (first_result.text_content() or "").strip():
            return False

        elapsed = time.perf_counter() - self.operation_started_at
        self.statistics.add(elapsed)
        self._record("READY_FOR_INTERACTIVE", dom_elapsed=elapsed)
        self.completion_recorded = True
        return True

    def reset_operation(self) -> None:
        """Reset timing state after the initial page load."""
        self.last_url = self.page.url
        self.operation_started_at = None
        self.operation_url = self.page.url
        self.completion_recorded = False

    def submit_keyword(self, keyword: str, *, timeout_ms: int = 10_000) -> None:
        """Fill the search field and submit one keyword through the page button."""
        input_locator = self.page.locator(SEARCH_INPUT_SELECTOR).first
        input_locator.wait_for(state="visible", timeout=timeout_ms)
        input_locator.fill(keyword)

        button_locator = self.page.locator(SEARCH_BUTTON_SELECTOR).first
        button_locator.wait_for(state="visible", timeout=timeout_ms)
        button_locator.dispatch_event("click", timeout=timeout_ms)

    def _handle_console(self, message: ConsoleMessage) -> None:
        if message.text.startswith(URL_EVENT_PREFIX):
            self._record_url(message.text.removeprefix(URL_EVENT_PREFIX))

    def _handle_frame_navigated(self, frame: Frame) -> None:
        if frame == self.page.main_frame:
            self._record_url(frame.url)

    def _record_url(self, url: str) -> None:
        if url == self.last_url:
            return

        self.last_url = url
        self._record("URLCHANGE")
        self.operation_started_at = time.perf_counter()
        self.operation_url = url
        self.completion_recorded = False

    def _record(
        self,
        action: str,
        *,
        dom_elapsed: float | None = None,
    ) -> None:
        now = time.perf_counter()
        message = f"{action}\tdelta={now - self.last_event_at:.3f}s"
        if dom_elapsed is not None:
            message += f"\tdom_elapsed={dom_elapsed:.3f}s"
        self.storage.write(message)
        print(message)
        self.last_event_at = now
