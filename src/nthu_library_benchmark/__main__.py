from __future__ import annotations

import argparse
import signal
from collections.abc import Sequence
from threading import Event
from types import FrameType

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from nthu_library_benchmark.statistics import Statistics
from nthu_library_benchmark.storage import DEFAULT_RECORD_PATH, Storage
from nthu_library_benchmark.tracker import (
    INIT_SCRIPT,
    POLL_INTERVAL_MS,
    SEARCH_URL,
    BrowserActivityTracker,
)


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure when NTHU Primo search results first become usable."
    )
    parser.add_argument(
        "--url",
        default=SEARCH_URL,
        help="Initial page URL (default: the NTHU Primo search page).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_RECORD_PATH),
        help="Record path prefix (default: storage/records.txt).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a visible browser window.",
    )
    parser.add_argument(
        "--stats-output",
        help="Save the final statistics report and histogram to this path.",
    )
    return parser.parse_args(arguments)


def run(arguments: Sequence[str] | None = None) -> None:
    options = parse_args(arguments)
    statistics = Statistics()
    shutdown_requested = Event()

    def request_shutdown(_signal_number: int, _frame: FrameType | None) -> None:
        del _signal_number, _frame
        shutdown_requested.set()

    previous_sigint_handler = signal.signal(signal.SIGINT, request_shutdown)
    previous_sigterm_handler = signal.signal(signal.SIGTERM, request_shutdown)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=options.headless)
            try:
                page = browser.new_page()
                tracker = BrowserActivityTracker(
                    page,
                    Storage(options.output),
                    statistics=statistics,
                )
                tracker.attach()
                page.add_init_script(INIT_SCRIPT)
                page.goto(options.url, wait_until="domcontentloaded")

                print("開始操作瀏覽器；搜尋結果首次可用時會寫入記錄。")
                print("按 Ctrl+C 結束。")
                while not shutdown_requested.is_set():
                    try:
                        page.wait_for_timeout(POLL_INTERVAL_MS)
                        tracker.check_operation_complete()
                    except PlaywrightError:
                        if not shutdown_requested.is_set():
                            raise
                        break
            finally:
                browser.close()
    finally:
        signal.signal(signal.SIGINT, previous_sigint_handler)
        signal.signal(signal.SIGTERM, previous_sigterm_handler)

    print("\n已停止記錄。")
    report = statistics.format_report()
    print(f"\n{report}")
    if options.stats_output:
        report_path = statistics.write_report(options.stats_output)
        print(f"\n統計報告已儲存至：{report_path}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
