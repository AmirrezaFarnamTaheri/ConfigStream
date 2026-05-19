#!/usr/bin/env bash
# ConfigStream Lab Runner - Run and test chain configs
# Works on Linux and macOS. Zero dependencies beyond curl.
#
# Usage:
#   bash lab-runner.sh run config.json          # Run a chain config
#   bash lab-runner.sh test config.json         # Test connectivity through the chain
#   bash lab-runner.sh scan-ips                 # Quick clean IP scan
#   bash lab-runner.sh scan-ips --through socks5://127.0.0.1:1080
#   bash lab-runner.sh install                  # Download sing-box binary

set -euo pipefail

VERSION="1.0.0"
SINGBOX_VERSION="1.11.0"
LISTEN_PORT="${LISTEN_PORT:-2080}"

# --- Colors ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC}  $1"; }
fail() { echo -e "  ${RED}[--]${NC}  $1"; }
info() { echo -e "  ${YELLOW}[**]${NC}  $1"; }

banner() {
    echo -e "${BOLD}============================================${NC}"
    echo -e "${CYAN}  ConfigStream Lab Runner v${VERSION}${NC}"
    echo -e "${BOLD}============================================${NC}"
    echo
}

# --- sing-box Management ---
SINGBOX_BIN=""

find_singbox() {
    if command -v sing-box &>/dev/null; then
        SINGBOX_BIN="sing-box"
        return 0
    fi
    local local_bin="./sing-box"
    if [[ -x "$local_bin" ]]; then
        SINGBOX_BIN="$local_bin"
        return 0
    fi
    local home_bin="$HOME/.local/bin/sing-box"
    if [[ -x "$home_bin" ]]; then
        SINGBOX_BIN="$home_bin"
        return 0
    fi
    return 1
}

install_singbox() {
    info "Downloading sing-box v${SINGBOX_VERSION}..."
    local ARCH
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        armv7*) ARCH="armv7" ;;
        *) fail "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    local OS
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    local NAME="sing-box-${SINGBOX_VERSION}-${OS}-${ARCH}"
    local URL="https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/${NAME}.tar.gz"

    local TMP
    TMP=$(mktemp -d)
    trap "rm -rf $TMP" EXIT

    if command -v curl &>/dev/null; then
        curl -sL "$URL" -o "$TMP/sb.tar.gz"
    elif command -v wget &>/dev/null; then
        wget -q "$URL" -O "$TMP/sb.tar.gz"
    else
        fail "Neither curl nor wget found. Install one first."
        exit 1
    fi

    tar xzf "$TMP/sb.tar.gz" -C "$TMP"
    local BIN="$TMP/${NAME}/sing-box"
    if [[ ! -f "$BIN" ]]; then
        fail "Binary not found in archive."
        exit 1
    fi
    chmod +x "$BIN"

    # Install to ~/.local/bin or current dir
    local DEST="$HOME/.local/bin"
    mkdir -p "$DEST" 2>/dev/null || DEST="."
    cp "$BIN" "$DEST/sing-box"
    chmod +x "$DEST/sing-box"
    SINGBOX_BIN="$DEST/sing-box"
    ok "Installed sing-box to $SINGBOX_BIN"
}

ensure_singbox() {
    if ! find_singbox; then
        install_singbox
    fi
}

# --- Run Config ---
cmd_run() {
    local config_file="${1:?Usage: lab-runner.sh run <config.json>}"
    if [[ ! -f "$config_file" ]]; then
        fail "Config file not found: $config_file"
        exit 1
    fi
    ensure_singbox
    info "Starting chain proxy on 127.0.0.1:${LISTEN_PORT}..."
    info "Set your browser/system proxy to socks5://127.0.0.1:${LISTEN_PORT}"
    echo
    "$SINGBOX_BIN" run -c "$config_file"
}

# --- Test Config ---
cmd_test() {
    local config_file="${1:?Usage: lab-runner.sh test <config.json>}"
    if [[ ! -f "$config_file" ]]; then
        fail "Config file not found: $config_file"
        exit 1
    fi
    ensure_singbox

    info "Starting sing-box in background..."
    "$SINGBOX_BIN" run -c "$config_file" &
    local PID=$!
    sleep 3

    if ! kill -0 "$PID" 2>/dev/null; then
        fail "sing-box exited immediately. Check config."
        exit 1
    fi

    info "Testing connectivity through the chain..."
    local PROXY="socks5h://127.0.0.1:${LISTEN_PORT}"
    local TEST_URLS=(
        "http://cp.cloudflare.com/generate_204"
        "http://connectivitycheck.gstatic.com/generate_204"
        "https://www.google.com"
    )
    local passed=0
    for url in "${TEST_URLS[@]}"; do
        local start end lat code
        start=$(date +%s%N 2>/dev/null || echo 0)
        code=$(curl -x "$PROXY" -s -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 15 "$url" 2>/dev/null || echo 0)
        end=$(date +%s%N 2>/dev/null || echo 0)
        if [[ "$start" != "0" && "$end" != "0" ]]; then
            lat=$(( (end - start) / 1000000 ))
        else
            lat="?"
        fi
        if [[ "$code" -ge 200 && "$code" -lt 400 ]]; then
            ok "$url -> HTTP $code (${lat}ms)"
            passed=$((passed + 1))
        else
            fail "$url -> HTTP $code"
        fi
    done

    # Get exit IP
    local exit_ip
    exit_ip=$(curl -x "$PROXY" -s --connect-timeout 10 --max-time 15 "https://api.ipify.org" 2>/dev/null || echo "unknown")
    if [[ "$exit_ip" != "unknown" && -n "$exit_ip" ]]; then
        ok "Exit IP: $exit_ip"
    fi

    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true

    echo
    if [[ "$passed" -gt 0 ]]; then
        ok "Chain is WORKING! ($passed/${#TEST_URLS[@]} tests passed)"
    else
        fail "Chain test FAILED. Check your config and try different clean IPs."
    fi
}

# --- Scan Clean IPs ---
cmd_scan_ips() {
    local PROXY_ARG=""
    if [[ "${1:-}" == "--through" && -n "${2:-}" ]]; then
        PROXY_ARG="-x $2"
        info "Scanning through proxy: $2"
    fi

    local IPS=(
        162.159.192.1 162.159.192.4 162.159.192.5 162.159.192.8
        162.159.192.10 162.159.192.83 162.159.192.166 162.159.195.2
        188.114.96.1 188.114.96.101 188.114.97.1
        188.114.98.224 188.114.99.73 188.114.99.153
    )
    local PORTS=(500 854 890 2408 2506 3854 5956 7103 8319)

    info "Scanning ${#IPS[@]} IPs x ${#PORTS[@]} ports..."
    echo
    printf "  %-20s %-8s %-12s\n" "IP" "Port" "Latency"
    printf "  %-20s %-8s %-12s\n" "----" "----" "-------"

    local found=0
    for ip in "${IPS[@]}"; do
        for port in "${PORTS[@]}"; do
            local start end lat
            start=$(date +%s%N 2>/dev/null || echo 0)
            # Try TCP connect using /dev/tcp or curl
            if timeout 3 bash -c "echo >/dev/tcp/$ip/$port" 2>/dev/null; then
                end=$(date +%s%N 2>/dev/null || echo 0)
                if [[ "$start" != "0" && "$end" != "0" ]]; then
                    lat=$(( (end - start) / 1000000 ))
                else
                    lat="?"
                fi
                printf "  ${GREEN}%-20s %-8s %sms${NC}\n" "$ip" "$port" "$lat"
                found=$((found + 1))
            fi
        done
    done

    echo
    if [[ "$found" -gt 0 ]]; then
        ok "Found $found reachable Cloudflare endpoints."
    else
        fail "No reachable endpoints found."
        info "Try scanning through a local proxy:"
        info "  bash lab-runner.sh scan-ips --through socks5://127.0.0.1:1080"
    fi
}

# --- Layer Test ---
cmd_test_layer() {
    local layer_type="${1:?Usage: lab-runner.sh test-layer <type> <host:port>}"
    local hostport="${2:?Usage: lab-runner.sh test-layer <type> <host:port>}"
    local host="${hostport%%:*}"
    local port="${hostport##*:}"

    info "Testing $layer_type layer at $host:$port..."

    case "$layer_type" in
        tcp)
            if timeout 3 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
                ok "TCP connection succeeded."
            else
                fail "TCP connection failed."
            fi
            ;;
        socks5)
            # Send SOCKS5 greeting
            local resp
            resp=$(printf '\x05\x01\x00' | timeout 3 nc -w 3 "$host" "$port" 2>/dev/null | xxd -p 2>/dev/null || echo "")
            if [[ "$resp" == "0500"* ]]; then
                ok "SOCKS5 handshake succeeded."
            else
                fail "SOCKS5 handshake failed."
            fi
            ;;
        http)
            local code
            code=$(curl -x "http://$host:$port" -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "http://cp.cloudflare.com/generate_204" 2>/dev/null || echo 0)
            if [[ "$code" -ge 200 && "$code" -lt 400 ]]; then
                ok "HTTP proxy works (HTTP $code)."
            else
                fail "HTTP proxy test failed (HTTP $code)."
            fi
            ;;
        tls)
            if timeout 5 openssl s_client -connect "$host:$port" -servername "$host" </dev/null 2>/dev/null | grep -q "Verify"; then
                ok "TLS handshake succeeded."
            else
                fail "TLS handshake failed."
            fi
            ;;
        *)
            fail "Unknown layer type: $layer_type (use: tcp, socks5, http, tls)"
            ;;
    esac
}

# --- Main ---
banner

case "${1:-}" in
    run)        shift; cmd_run "$@" ;;
    test)       shift; cmd_test "$@" ;;
    scan-ips)   shift; cmd_scan_ips "$@" ;;
    test-layer) shift; cmd_test_layer "$@" ;;
    install)    install_singbox ;;
    install-vwarp)
        info "Downloading Vwarp..."
        curl -fsSL https://raw.githubusercontent.com/voidr3aper-anon/Vwarp/master/termux.sh | bash
        ;;
    *)
        echo "Usage: lab-runner.sh <command> [args]"
        echo
        echo "Commands:"
        echo "  run <config.json>              Run a chain config with sing-box"
        echo "  test <config.json>             Start chain and test connectivity"
        echo "  scan-ips [--through proxy]     Scan for clean Cloudflare IPs"
        echo "  test-layer <type> <host:port>  Test a single layer (tcp/socks5/http/tls)"
        echo "  install                        Download sing-box binary"
        echo "  install-vwarp                  Download Vwarp binary"
        echo
        echo "Examples:"
        echo "  bash lab-runner.sh run chain.json"
        echo "  bash lab-runner.sh test chain.json"
        echo "  bash lab-runner.sh scan-ips"
        echo "  bash lab-runner.sh scan-ips --through socks5://127.0.0.1:1080"
        echo "  bash lab-runner.sh test-layer socks5 127.0.0.1:1080"
        echo "  bash lab-runner.sh test-layer tcp 162.159.192.1:2408"
        ;;
esac
