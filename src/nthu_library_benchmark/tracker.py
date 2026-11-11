from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import ConsoleMessage, Frame, Page

from nthu_library_benchmark.storage import Storage

SEARCH_URL = (
    "https://nthu.primo.exlibrisgroup.com/discovery/search?"
    "query=any,contains,*&tab=Everything&"
    "search_scope=MyInst_and_CI_NoResearch&"
    "vid=886UST_NTHU:886UST_NTHU&lang=zh-tw&offset=0"
)
POLL_INTERVAL_MS = 100
RESULT_SELECTOR = "prm-brief-result-container"
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
        config: TrackerConfig | None = None,
    ) -> None:
        self.page = page
        self.storage = storage
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

    def check_operation_complete(self) -> None:
        """Record completion once the first result is visible and populated."""
        if self.operation_started_at is None or self.completion_recorded:
            return
        if self.page.url != self.operation_url:
            return

        first_result = self.page.locator(self.config.result_selector).first
        if not first_result.is_visible():
            return
        if not (first_result.text_content() or "").strip():
            return

        elapsed = time.perf_counter() - self.operation_started_at
        self._record("READY_FOR_INTERACTIVE", self.operation_url, dom_elapsed=elapsed)
        self.completion_recorded = True

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
        self._record("URLCHANGE", url)
        self.operation_started_at = time.perf_counter()
        self.operation_url = url
        self.completion_recorded = False

    def _record(
        self,
        action: str,
        url: str,
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
