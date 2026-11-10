import time

from playwright.sync_api import ConsoleMessage, Page, Request

from nthu_library_benchmark.storage import Storage

SEARCH_URL = (
    "https://nthu.primo.exlibrisgroup.com/discovery/search?"
    "query=any,contains,*&tab=Everything&"
    "search_scope=MyInst_and_CI_NoResearch&"
    "vid=886UST_NTHU:886UST_NTHU&lang=zh-tw&offset=0"
)
QUIET_PERIOD_SECONDS = 0.8
POLL_INTERVAL_MS = 100

INIT_SCRIPT = """
    const notifyUrlChange = () => console.log('__URL__' + location.href);
    const pushState = history.pushState;
    const replaceState = history.replaceState;

    history.pushState = function(...args) {
        const result = pushState.apply(this, args);
        notifyUrlChange();
        return result;
    };
    history.replaceState = function(...args) {
        const result = replaceState.apply(this, args);
        notifyUrlChange();
        return result;
    };

    addEventListener('popstate', notifyUrlChange);
    addEventListener('hashchange', notifyUrlChange);
"""


class BrowserActivityTracker:
    """Collect browser activity and report when each operation settles."""

    def __init__(self, page: Page, storage: Storage):
        self.page = page
        self.start_time = time.perf_counter()
        self.last_time = self.start_time
        self.last_url = page.url
        self.in_flight_requests: set[Request] = set()
        self.operation_started_at: float | None = None
        self.operation_url = page.url
        self.completion_recorded = False
        self.storage: Storage = storage

    def record(self, action: str, url: str) -> None:
        now = time.perf_counter()
        log_message = f"{action:<15} delta={now - self.last_time:.3f}s url={url}"
        self.storage.record_new_line_to_file(log_message)
        print(log_message)
        self.last_time = now

    def mark_operation(self, url: str) -> None:
        self.operation_started_at = time.perf_counter()
        self.operation_url = url
        self.completion_recorded = False

    def record_url(self, url: str) -> None:
        if url == self.last_url:
            return
        self.last_url = url
        self.record("URL", url)
        print(f"URL changed to {url}")
        self.mark_operation(url)

    def handle_console(self, message: ConsoleMessage) -> None:
        if message.text.startswith("__URL__"):
            self.record_url(message.text.removeprefix("__URL__"))

    def check_operation_complete(self) -> None:
        if self.operation_started_at is None or self.completion_recorded:
            return
        quiet_long_enough = (
            time.perf_counter() - self.operation_started_at >= QUIET_PERIOD_SECONDS
        )
        if not self.in_flight_requests and quiet_long_enough:
            self.record("DONE", self.operation_url)
            self.completion_recorded = True

    def attach(self) -> None:
        self.page.on(
            "framenavigated",
            lambda frame: (
                self.record_url(frame.url) if frame == self.page.main_frame else None
            ),
        )
        self.page.on("console", self.handle_console)
        self.page.on("request", lambda request: self.in_flight_requests.add(request))
        self.page.on(
            "requestfinished",
            lambda request: self.in_flight_requests.discard(request),
        )
        self.page.on(
            "requestfailed",
            lambda request: self.in_flight_requests.discard(request),
        )
