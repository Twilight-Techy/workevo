# Dependency and asset inventory

Reviewed installed runtime metadata on 2026-11-17. No upstream optimizer code is copied or vendored. Dependencies are separately installed distributions, not bundled copies of those libraries.

| Runtime distribution | Locked version | Declared license |
| --- | --- | --- |
| pydantic | 2.14.3 | MIT |
| pydantic-core | 2.50.4 | MIT |
| annotated-types | 0.8.0 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.5 | MIT |

Each installed distribution declares its own LICENSE file. Exact resolved distributions/hashes are in uv.lock. Build/check dependencies are optional development tools; Playwright/its browser are an optional browser-check group and are not runtime requirements or redistributed browser binaries.

The inspector HTML/CSS/JavaScript, fictional fixture records, documentation and screenshots were authored in this project. The UI uses system fonts and inline SVG generated from recorded numeric metrics. No downloaded imagery, external fonts, third-party UI assets, or copied optimizer implementations are bundled. Local source conversations and integrity receipts are excluded from distributions and are not licensed for redistribution by this project's MIT file.


README presentation assets (2026-11-18): the workevo banner is original code-authored SVG. The benchmark SVG is rendered from recorded JSON by the optional Matplotlib 3.11.2 command; it is a documentation tool, not a runtime dependency. Charts record input-report hashes and plotted values. Badges reference GitHub Actions and Shields.io; no remote images or fonts are downloaded into the repository.
