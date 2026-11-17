"""Browser QA for a local report; no hosted service, mocks or external assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(path: Path, screenshot: Path) -> dict:
    errors = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(path.resolve().as_uri())
        page.wait_for_selector(".candidate")
        assert page.title().startswith("workevo")
        assert page.locator(".candidate").count() == 5
        assert page.locator("#cases tr").count() == 24
        assert page.locator("#quality").inner_text() == "100.0%"
        page.select_option("#filter", "rejected")
        assert page.locator(".candidate").count() == 1
        page.locator(".candidate").click()
        assert "regression" in page.locator("#decision").inner_text()
        assert page.locator("#graph .node").count() == 1
        page.select_option("#filter", "all")
        page.fill("#search", "no-match-zz")
        assert page.locator(".empty").count() == 1
        page.fill("#search", "")
        page.locator(".candidate").nth(3).click()
        page.locator("summary").first.click()
        assert page.locator("#trace").is_visible()
        page.locator("summary").first.click()
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        assert page.locator(".candidate").count() == 5
        page.screenshot(
            path=str(screenshot.with_name(screenshot.stem + "-mobile.png")), full_page=True
        )
        assert not errors, errors
        assert not page.evaluate("Boolean(window.INJECTED)")
        browser.close()
    return {
        "desktop": [1440, 1080],
        "mobile": [390, 844],
        "candidate_count": 5,
        "errors": errors,
        "checks": [
            "filter",
            "search",
            "selection",
            "trace disclosure",
            "metric display",
            "responsive overflow",
        ],
        "screenshot": str(screenshot),
        "source": str(path),
        "data_kind": "real local recorded authored-fixture run",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--screenshot", type=Path, default=Path("reports/inspector.png"))
    args = parser.parse_args()
    receipt = check(args.report, args.screenshot)
    args.screenshot.with_suffix(".json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
