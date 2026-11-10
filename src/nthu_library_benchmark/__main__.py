from playwright.sync_api import sync_playwright

from nthu_library_benchmark.storage import Storage
from nthu_library_benchmark.tracker import (
    INIT_SCRIPT,
    POLL_INTERVAL_MS,
    SEARCH_URL,
    BrowserActivityTracker,
)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        storage = Storage()
        tracker = BrowserActivityTracker(page, storage)
        tracker.attach()
        page.add_init_script(INIT_SCRIPT)
        page.goto(SEARCH_URL)

        print("開始操作瀏覽器...")
        print("按 Ctrl+C 結束")
        try:
            while True:
                page.wait_for_timeout(POLL_INTERVAL_MS)
                tracker.check_operation_complete()
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()


if __name__ == "__main__":
    main()
