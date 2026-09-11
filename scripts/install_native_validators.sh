#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Install checksum-authenticated native validators used by release workflows.
set -euo pipefail

: "${SING_BOX_VERSION:?SING_BOX_VERSION is required}"
: "${XRAY_VERSION:?XRAY_VERSION is required}"
: "${MIHOMO_VERSION:?MIHOMO_VERSION is required}"

# Repository-owned trust anchors for the exact Linux/amd64 release artifacts.
# Version bumps must update these digests in the same reviewed change.
readonly SING_BOX_ARCHIVE_SHA256="d34d987ed6ae39ca3760269264fb502b867e5477db45518c829b07776245c495"
readonly XRAY_ARCHIVE_SHA256="8195d909f1109b8f3d99eefe401a3c451d7bf4af71f24d3815420f77e5dd2a40"
readonly MIHOMO_ARCHIVE_SHA256="343b2046967b236bc868b82537040cd0cecdedd20f3c6796ac96170f96b2debe"

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

download_verified_asset() {
  local repository="$1"
  local tag="$2"
  local asset="$3"
  local expected="$4"
  local actual

  if [[ ! "$expected" =~ ^[0-9a-fA-F]{64}$ ]]; then
    echo "Invalid pinned SHA-256 for ${repository}@${tag}:${asset}" >&2
    return 1
  fi
  expected="$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')"
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
download_verified_asset \
  "SagerNet/sing-box" \
  "v${SING_BOX_VERSION}" \
  "$sing_box_archive" \
  "$SING_BOX_ARCHIVE_SHA256"
tar -xzf "$sing_box_archive"
install -m 0755 \
  "sing-box-${SING_BOX_VERSION}-linux-amd64/sing-box" \
  "$staging_dir/sing-box"

xray_archive="Xray-linux-64.zip"
download_verified_asset \
  "XTLS/Xray-core" \
  "$XRAY_VERSION" \
  "$xray_archive" \
  "$XRAY_ARCHIVE_SHA256"
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

mihomo_asset="mihomo-linux-amd64-v3-${MIHOMO_VERSION}.gz"
download_verified_asset \
  "MetaCubeX/mihomo" \
  "$MIHOMO_VERSION" \
  "$mihomo_asset" \
  "$MIHOMO_ARCHIVE_SHA256"
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
