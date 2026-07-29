#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Install the exact native validators used by release and replay workflows.
set -euo pipefail

: "${SING_BOX_VERSION:?SING_BOX_VERSION is required}"
: "${XRAY_VERSION:?XRAY_VERSION is required}"
: "${MIHOMO_VERSION:?MIHOMO_VERSION is required}"

install_dir="${INSTALL_DIR:-${HOME}/.local/bin}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$install_dir"
cd "$work_dir"

retry() {
  local attempt=1
  local max_attempts=3
  local delay=10
  until "$@"; do
    if (( attempt >= max_attempts )); then
      return 1
    fi
    sleep "$delay"
    attempt=$((attempt + 1))
    delay=$((delay * 2))
  done
}

sing_box_archive="sing-box-${SING_BOX_VERSION}-linux-amd64.tar.gz"
retry gh release download "v${SING_BOX_VERSION}" \
  --repo SagerNet/sing-box \
  --pattern "$sing_box_archive"
tar -xzf "$sing_box_archive"
install -m 0755 \
  "sing-box-${SING_BOX_VERSION}-linux-amd64/sing-box" \
  "$install_dir/sing-box"

retry gh release download "$XRAY_VERSION" \
  --repo XTLS/Xray-core \
  --pattern "Xray-linux-64.zip"
mkdir -p xray
unzip -oq Xray-linux-64.zip -d xray
install -m 0755 xray/xray "$install_dir/xray"

mihomo_asset="$({
  gh api "repos/MetaCubeX/mihomo/releases/tags/${MIHOMO_VERSION}" \
    --jq '.assets[].name | select(test("^mihomo-linux-amd64-v[0-9]+-v[0-9.]+\\.gz$"))'
} | head -n 1)"
if [[ -z "$mihomo_asset" ]]; then
  echo "No exact linux-amd64 mihomo asset found for ${MIHOMO_VERSION}" >&2
  exit 1
fi
retry gh release download "$MIHOMO_VERSION" \
  --repo MetaCubeX/mihomo \
  --pattern "$mihomo_asset"
gzip -dc "$mihomo_asset" > "$install_dir/mihomo"
chmod 0755 "$install_dir/mihomo"

for executable in sing-box xray mihomo; do
  test -x "$install_dir/$executable"
done
