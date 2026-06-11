# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke-test a deployed GitHub Pages site over HTTP(S)."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

PLACEHOLDER_MARKERS = (
    "79e/79e/",
    "PLACEHOLDER_PUBLIC_KEY",
    "PLACEHOLDER_KEY_INJECTED_BY_CI",
)
REQUIRED_PAGES = (
    "index.html",
    "analytics.html",
    "proxies.html",
    "lab.html",
    "wiki.html",
)
REQUIRED_PUBLIC_FILES = (
    "health.json",
    "metadata.json",
    "artifact_manifest.json",
    "base64.txt",
    "chosen/base64.txt",
    "proxies.json",
    "api/proxies",
    "api/stats",
)
EMPTY_VALID_PUBLIC_FILES = {
    "base64.txt",
    "chosen/base64.txt",
}


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    body: bytes
    content_type: str

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def _join(base_url: str, rel_path: str) -> str:
    base = base_url if base_url.endswith("/") else base_url + "/"
    return urllib.parse.urljoin(base, rel_path)


def _fetch(url: str, *, timeout: float) -> Response:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise urllib.error.URLError(f"unsupported URL scheme/host: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "accept": "*/*",
            "user-agent": "ConfigStream deploy smoke",
        },
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:  # nosec B310
            try:
                body = response.read()
            except http.client.IncompleteRead as exc:
                return Response(
                    url=url,
                    status=0,
                    body=exc.partial,
                    content_type=response.headers.get("content-type", ""),
                )
            return Response(
                url=url,
                status=int(response.status),
                body=body,
                content_type=response.headers.get("content-type", ""),
            )
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except http.client.IncompleteRead as read_exc:
            body = read_exc.partial
        return Response(
            url=url,
            status=int(exc.code),
            body=body,
            content_type=exc.headers.get("content-type", ""),
        )


def _json(response: Response) -> object:
    return json.loads(response.text)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _assert_ok(
    response: Response,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> None:
    if response.status < 200 or response.status >= 300:
        errors.append(f"{response.url} returned HTTP {response.status}")
    if not response.body and not allow_empty:
        errors.append(f"{response.url} returned an empty body")


def _assert_no_placeholders(label: str, text: str, errors: list[str]) -> None:
    for marker in PLACEHOLDER_MARKERS:
        if marker in text:
            errors.append(f"{label} contains placeholder marker: {marker}")


def _manifest_hashes(manifest: object, errors: list[str]) -> dict[str, str]:
    if not isinstance(manifest, dict):
        errors.append("artifact_manifest.json must be a JSON object")
        return {}
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("artifact_manifest.json missing files list")
        return {}
    hashes: dict[str, str] = {}
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            errors.append(f"artifact_manifest.json files[{index}] must be an object")
            continue
        path = entry.get("path")
        digest = entry.get("sha256")
        if isinstance(path, str) and isinstance(digest, str):
            hashes[path] = digest
    return hashes


def _assert_manifest_hash(
    rel_path: str,
    response: Response,
    manifest_hashes: dict[str, str],
    errors: list[str],
) -> None:
    expected = manifest_hashes.get(rel_path)
    if not expected:
        errors.append(f"artifact_manifest.json missing file entry: {rel_path}")
        return
    actual = _sha256(response.body)
    if actual != expected:
        errors.append(f"artifact_manifest.json sha256 mismatch: {rel_path}")


def verify_pages_deployment(base_url: str, *, timeout: float = 20.0) -> list[str]:
    errors: list[str] = []
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return [f"invalid deployment URL: {base_url}"]

    for page in REQUIRED_PAGES:
        response = _fetch(_join(base_url, page), timeout=timeout)
        _assert_ok(response, errors)
        text = response.text
        if "<html" not in text.lower():
            errors.append(f"{page} did not look like HTML")
        if "ConfigStream" not in text:
            errors.append(f"{page} missing ConfigStream page identity")
        _assert_no_placeholders(page, text, errors)

    runtime_config = _fetch(
        _join(base_url, "assets/js/runtime-config.js"), timeout=timeout
    )
    _assert_ok(runtime_config, errors)
    runtime_text = runtime_config.text
    _assert_no_placeholders("assets/js/runtime-config.js", runtime_text, errors)
    if 'PUBLIC_KEY: ""' in runtime_text:
        errors.append("assets/js/runtime-config.js is missing PUBLIC_KEY")
    if 'STEGO_KEY: ""' in runtime_text:
        errors.append("assets/js/runtime-config.js is missing STEGO_KEY")

    constants = _fetch(_join(base_url, "assets/js/constants.js"), timeout=timeout)
    _assert_ok(constants, errors)
    _assert_no_placeholders("assets/js/constants.js", constants.text, errors)

    stego = _fetch(_join(base_url, "assets/js/stego.js"), timeout=timeout)
    _assert_ok(stego, errors)
    _assert_no_placeholders("assets/js/stego.js", stego.text, errors)

    responses = {
        rel_path: _fetch(_join(base_url, rel_path), timeout=timeout)
        for rel_path in REQUIRED_PUBLIC_FILES
    }
    for rel_path, response in responses.items():
        _assert_ok(
            response,
            errors,
            allow_empty=rel_path in EMPTY_VALID_PUBLIC_FILES,
        )

    try:
        metadata_response = responses["metadata.json"]
        api_stats_response = responses["api/stats"]
        metadata = _json(metadata_response)
        api_stats = _json(api_stats_response)
        if metadata != api_stats:
            errors.append("api/stats does not match metadata.json")
        if not isinstance(metadata, dict):
            errors.append("metadata.json must be a JSON object")
        elif not metadata.get("proxies_snapshot_hash"):
            errors.append("metadata.json missing proxies_snapshot_hash")
    except json.JSONDecodeError as exc:
        errors.append(f"metadata/api stats JSON decode failed: {exc}")

    try:
        proxies_response = responses["proxies.json"]
        api_proxies_response = responses["api/proxies"]
        proxies = _json(proxies_response)
        api_proxies = _json(api_proxies_response)
        if proxies != api_proxies:
            errors.append("api/proxies does not match proxies.json")
        if not isinstance(proxies, list):
            errors.append("proxies.json must be a JSON array")
    except json.JSONDecodeError as exc:
        errors.append(f"proxy JSON decode failed: {exc}")

    try:
        health_json = _json(responses["health.json"])
        if not isinstance(health_json, dict) or health_json.get("status") not in {
            "ok",
            "degraded",
        }:
            errors.append("health.json status must be ok or degraded")
        elif not health_json.get("run_id") or not health_json.get("source_commit"):
            errors.append("health.json missing run_id or source_commit")
    except json.JSONDecodeError as exc:
        errors.append(f"health.json decode failed: {exc}")

    try:
        manifest = _json(responses["artifact_manifest.json"])
        manifest_hashes = _manifest_hashes(manifest, errors)
        for rel_path in (
            "health.json",
            "metadata.json",
            "proxies.json",
            "base64.txt",
            "chosen/base64.txt",
            "api/proxies",
            "api/stats",
        ):
            _assert_manifest_hash(
                rel_path, responses[rel_path], manifest_hashes, errors
            )
    except json.JSONDecodeError as exc:
        errors.append(f"artifact_manifest.json decode failed: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="GitHub Pages deployment URL")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--report-file", help="Path to save JSON report")
    args = parser.parse_args(argv)

    errors = verify_pages_deployment(args.url, timeout=args.timeout)

    if args.report_file:
        report = {
            "url": args.url,
            "status": "passed" if not errors else "failed",
            "errors": errors,
        }
        with open(args.report_file, "w") as f:
            json.dump(report, f, indent=2)

    if errors:
        print("ERROR: deployed Pages smoke failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"OK: deployed Pages smoke passed for {args.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
