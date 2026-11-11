from __future__ import annotations

import argparse
import signal
from collections.abc import Sequence
from pathlib import Path
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

DEFAULT_KEYWORDS_FILE = Path("keywords.txt")
SEARCH_TIMEOUT_MS = 10_000


def load_keywords(path: str | Path) -> tuple[str, ...]:
    """Load non-empty, non-comment keyword lines from a text file."""
    keyword_path = Path(path)
    keywords = tuple(
        line.strip()
        for line in keyword_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not keywords:
        raise ValueError(f"Keyword file is empty: {keyword_path}")
    return keywords


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
    keyword_group = parser.add_mutually_exclusive_group()
    keyword_group.add_argument(
        "--keywords",
        nargs="+",
        metavar="KEYWORD",
        help="Keywords to submit in order instead of the keyword file.",
    )
    keyword_group.add_argument(
        "--keywords-file",
        default=str(DEFAULT_KEYWORDS_FILE),
        metavar="PATH",
        help="One keyword per line (default: keywords.txt).",
    )
    return parser.parse_args(arguments)


def run(arguments: Sequence[str] | None = None) -> None:
    options = parse_args(arguments)
    keywords = tuple(options.keywords or load_keywords(options.keywords_file))
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
                tracker.reset_operation()

                print(f"開始自動搜尋，共 {len(keywords)} 個關鍵字。")
                print("按 Ctrl+C 結束。")
                for keyword in keywords:
                    if shutdown_requested.is_set():
                        break
                    try:
                        previous_url = page.url
                        print(f"\n搜尋：{keyword}")
                        tracker.submit_keyword(keyword, timeout_ms=SEARCH_TIMEOUT_MS)
                        page.wait_for_url(
                            lambda url: url != previous_url,
                            timeout=SEARCH_TIMEOUT_MS,
                        )
                        while not shutdown_requested.is_set():
                            page.wait_for_timeout(POLL_INTERVAL_MS)
                            if tracker.check_operation_complete():
                                break
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
