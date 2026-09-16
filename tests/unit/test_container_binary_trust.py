# SPDX-License-Identifier: AGPL-3.0-or-later

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_image_pins_baked_go_tester_digest() -> None:
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")

    copy_line = "COPY --from=builder /app/tester /usr/local/bin/configstream-tester"
    digest_line = (
        "sha256sum /usr/local/bin/configstream-tester | awk '{print $1}' "
        "> /usr/local/bin/configstream-tester.sha256"
    )
    chmod_line = "chmod 0444 /usr/local/bin/configstream-tester.sha256"

    assert copy_line in dockerfile
    assert digest_line in dockerfile
    assert chmod_line in dockerfile

    copy_index = dockerfile.index(copy_line)
    digest_index = dockerfile.index(digest_line)
    chmod_index = dockerfile.index(chmod_line)
    first_runner_user_index = dockerfile.index("USER runner")

    assert copy_index < digest_index < chmod_index < first_runner_user_index


def test_container_pins_vwarp_digest_sidecar_too() -> None:
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert (
        "sha256sum /usr/local/bin/vwarp | awk '{print $1}' > /usr/local/bin/vwarp.sha256"
        in dockerfile
    )
    assert "chmod 0444 /usr/local/bin/vwarp.sha256" in dockerfile
