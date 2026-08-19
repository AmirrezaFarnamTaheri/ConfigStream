#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Install checksum-authenticated native validators used by release workflows.
set -euo pipefail

: "${SING_BOX_VERSION:?SING_BOX_VERSION is required}"
: "${XRAY_VERSION:?XRAY_VERSION is required}"
: "${MIHOMO_VERSION:?MIHOMO_VERSION is required}"

install_dir="${INSTALL_DIR:-${HOME}/.local/bin}"
work_dir="$(mktemp -d)"
staging_dir="$work_dir/staged"
trap 'rm -rf "$work_dir"' EXIT
mkdir -p "$install_dir" "$staging_dir"
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

release_asset_digest() {
  local repository="$1"
  local tag="$2"
  local asset="$3"
  local digest

  digest="$(gh api "repos/${repository}/releases/tags/${tag}" \
    --jq "first(.assets[] | select(.name == \"${asset}\") | .digest) // empty")"
  if [[ ! "$digest" =~ ^sha256:[0-9a-fA-F]{64}$ ]]; then
    echo "Missing or invalid SHA-256 digest metadata for ${repository}@${tag}:${asset}" >&2
    return 1
  fi
  printf '%s\n' "${digest#sha256:}" | tr '[:upper:]' '[:lower:]'
}

download_verified_asset() {
  local repository="$1"
  local tag="$2"
  local asset="$3"
  local expected actual

  expected="$(release_asset_digest "$repository" "$tag" "$asset")"
  retry gh release download "$tag" \
    --repo "$repository" \
    --pattern "$asset" \
    --clobber
  test -f "$asset"
  actual="$(sha256sum "$asset" | awk '{print tolower($1)}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "SHA-256 mismatch for ${repository}@${tag}:${asset}" >&2
    echo "expected=${expected}" >&2
    echo "actual=${actual}" >&2
    return 1
  fi
}

atomic_install() {
  local source="$1"
  local destination="$2"
  local mode="${3:-0755}"
  local temporary

  test -f "$source"
  temporary="$(mktemp "${install_dir}/.${destination}.XXXXXX")"
  if ! install -m "$mode" "$source" "$temporary"; then
    rm -f "$temporary"
    return 1
  fi
  if ! mv -f "$temporary" "$install_dir/$destination"; then
    rm -f "$temporary"
    return 1
  fi
}

sing_box_archive="sing-box-${SING_BOX_VERSION}-linux-amd64.tar.gz"
download_verified_asset "SagerNet/sing-box" "v${SING_BOX_VERSION}" "$sing_box_archive"
tar -xzf "$sing_box_archive"
install -m 0755 \
  "sing-box-${SING_BOX_VERSION}-linux-amd64/sing-box" \
  "$staging_dir/sing-box"

xray_archive="Xray-linux-64.zip"
download_verified_asset "XTLS/Xray-core" "$XRAY_VERSION" "$xray_archive"
mkdir -p xray
unzip -oq "$xray_archive" -d xray
install -m 0755 xray/xray "$staging_dir/xray"
for geodata in geoip.dat geosite.dat; do
  if [[ ! -f "xray/$geodata" ]]; then
    echo "Xray release asset is missing required ${geodata}" >&2
    exit 1
  fi
  install -m 0644 "xray/$geodata" "$staging_dir/$geodata"
done

mihomo_asset="$(gh api "repos/MetaCubeX/mihomo/releases/tags/${MIHOMO_VERSION}" \
  --jq 'first(.assets[].name | select(test("^mihomo-linux-amd64-v[0-9]+-v[0-9.]+\\.gz$"))) // empty')"
if [[ -z "$mihomo_asset" ]]; then
  echo "No exact linux-amd64 Mihomo asset found for ${MIHOMO_VERSION}" >&2
  exit 1
fi
download_verified_asset "MetaCubeX/mihomo" "$MIHOMO_VERSION" "$mihomo_asset"
mihomo_temp="$(mktemp "${staging_dir}/.mihomo.XXXXXX")"
gzip -dc "$mihomo_asset" > "$mihomo_temp"
chmod 0755 "$mihomo_temp"
mv -f "$mihomo_temp" "$staging_dir/mihomo"

for executable in sing-box xray mihomo; do
  test -x "$staging_dir/$executable"
done
for geodata in geoip.dat geosite.dat; do
  test -r "$staging_dir/$geodata"
done

for executable in sing-box xray mihomo; do
  atomic_install "$staging_dir/$executable" "$executable" 0755
done
for geodata in geoip.dat geosite.dat; do
  atomic_install "$staging_dir/$geodata" "$geodata" 0644
done

for executable in sing-box xray mihomo; do
  test -x "$install_dir/$executable"
done
for geodata in geoip.dat geosite.dat; do
  test -r "$install_dir/$geodata"
done
