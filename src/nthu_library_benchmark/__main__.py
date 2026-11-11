from __future__ import annotations

import argparse
from collections.abc import Sequence

from playwright.sync_api import sync_playwright

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
    return parser.parse_args(arguments)


def run(arguments: Sequence[str] | None = None) -> None:
    options = parse_args(arguments)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=options.headless)
        try:
            page = browser.new_page()
            tracker = BrowserActivityTracker(page, Storage(options.output))
            tracker.attach()
            page.add_init_script(INIT_SCRIPT)
            page.goto(options.url, wait_until="domcontentloaded")

            print("開始操作瀏覽器；搜尋結果首次可用時會寫入記錄。")
            print("按 Ctrl+C 結束。")
            while True:
                page.wait_for_timeout(POLL_INTERVAL_MS)
                tracker.check_operation_complete()
        except KeyboardInterrupt:
            print("\n已停止記錄。")
        finally:
            browser.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
