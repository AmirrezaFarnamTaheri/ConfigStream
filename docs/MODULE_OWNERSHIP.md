# Module Ownership Map

`docs/module_ownership.json` is the canonical ownership map for first-party module boundaries. It records the owner domain, public APIs, internal-only helpers, duplicate implementations that must not be reintroduced, removed-module replacements, tests, and docs for each major `src/configstream` area.

The map is validated by `scripts/validate_module_ownership.py`. The validator checks that mapped paths, tests, and docs exist, removed module paths stay removed, and Python imports do not reference removed module names such as `configstream.output`, `configstream.pipeline_core`, `configstream.fetcher_core`, `configstream.tools.vwarp_tool`, or `configstream.intelligence.washer`.

Contributor rule: add new shared behavior to the mapped canonical module, or update the map and proof surfaces in the same change. Do not preserve compatibility shims for removed modules.
