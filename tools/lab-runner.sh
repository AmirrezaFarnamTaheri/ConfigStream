#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# ConfigStream Lab Runner - run and test chain configs.
# Linux and macOS are supported when the required command-line tools are present.

set -Eeuo pipefail

VERSION="1.1.0"
LISTEN_PORT="${LISTEN_PORT:-2080}"
SINGBOX_BIN=""
TIMEOUT_BIN=""
CHILD_PID=""

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

require_command() {
    local name="$1"
    if ! command -v "$name" >/dev/null 2>&1; then
        fail "Required command not found: $name"
        return 1
    fi
}

validate_port() {
    local port="$1"
    [[ "$port" =~ ^[0-9]+$ ]] || return 1
    (( 10#$port >= 1 && 10#$port <= 65535 ))
}

validate_host() {
    local host="$1"
    [[ -n "$host" ]] || return 1
    if [[ "$host" == *:* ]]; then
        [[ "$host" =~ ^[0-9A-Fa-f:.]+$ ]]
    else
        [[ "$host" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]]
    fi
}

parse_hostport() {
    local value="$1"
    PARSED_HOST=""
    PARSED_PORT=""

    if [[ "$value" =~ ^\[([0-9A-Fa-f:.]+)\]:([0-9]+)$ ]]; then
        PARSED_HOST="${BASH_REMATCH[1]}"
        PARSED_PORT="${BASH_REMATCH[2]}"
    elif [[ "$value" =~ ^([^:]+):([0-9]+)$ ]]; then
        PARSED_HOST="${BASH_REMATCH[1]}"
        PARSED_PORT="${BASH_REMATCH[2]}"
    else
        return 1
    fi

    validate_host "$PARSED_HOST" && validate_port "$PARSED_PORT"
}

find_timeout() {
    if command -v timeout >/dev/null 2>&1; then
        TIMEOUT_BIN="$(command -v timeout)"
    elif command -v gtimeout >/dev/null 2>&1; then
        TIMEOUT_BIN="$(command -v gtimeout)"
    else
        fail "A timeout utility is required (timeout on Linux, or gtimeout from coreutils on macOS)."
        return 1
    fi
}

now_ms() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import time; print(time.monotonic_ns() // 1_000_000)'
        return
    fi
    echo $(( $(date +%s) * 1000 ))
}

cleanup_child() {
    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill "$CHILD_PID" 2>/dev/null || true
        wait "$CHILD_PID" 2>/dev/null || true
    fi
    CHILD_PID=""
}
trap cleanup_child EXIT
trap 'cleanup_child; exit 130' INT
trap 'cleanup_child; exit 143' TERM

find_singbox() {
    local candidate
    if candidate="$(command -v sing-box 2>/dev/null)" && [[ -n "$candidate" ]]; then
        SINGBOX_BIN="$candidate"
        return 0
    fi
    if [[ -x "./sing-box" ]]; then
        SINGBOX_BIN="$(pwd)/sing-box"
        return 0
    fi
    if [[ -x "$HOME/.local/bin/sing-box" ]]; then
        SINGBOX_BIN="$HOME/.local/bin/sing-box"
        return 0
    fi
    return 1
}

install_singbox() {
    fail "Automatic sing-box download is disabled for security."
    info "Install sing-box from the official release channel and verify its integrity."
    info "Expected binary location: PATH, ./sing-box, or ~/.local/bin/sing-box"
    return 1
}

ensure_singbox() {
    if ! find_singbox; then
        fail "sing-box not found."
        install_singbox
        return 1
    fi
}

tcp_probe() {
    local host="$1"
    local port="$2"
    find_timeout
    # Host and port are positional parameters, never interpolated into shell code.
    "$TIMEOUT_BIN" 3 bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$host" "$port" 2>/dev/null
}

cmd_run() {
    local config_file="${1:?Usage: lab-runner.sh run <config.json>}"
    [[ -f "$config_file" ]] || { fail "Config file not found: $config_file"; return 1; }
    ensure_singbox
    info "Starting chain proxy. Expected local listener: 127.0.0.1:${LISTEN_PORT}"
    info "The config itself must define that listener if you want the test command to use it."
    "$SINGBOX_BIN" run -c "$config_file"
}

cmd_test() {
    local config_file="${1:?Usage: lab-runner.sh test <config.json>}"
    [[ -f "$config_file" ]] || { fail "Config file not found: $config_file"; return 1; }
    validate_port "$LISTEN_PORT" || { fail "LISTEN_PORT must be between 1 and 65535."; return 1; }
    ensure_singbox
    require_command curl

    info "Starting sing-box in background..."
    "$SINGBOX_BIN" run -c "$config_file" &
    CHILD_PID=$!
    sleep 3

    if ! kill -0 "$CHILD_PID" 2>/dev/null; then
        fail "sing-box exited immediately. Check config."
        wait "$CHILD_PID" 2>/dev/null || true
        CHILD_PID=""
        return 1
    fi

    local proxy="socks5h://127.0.0.1:${LISTEN_PORT}"
    local test_urls=(
        "http://cp.cloudflare.com/generate_204"
        "http://connectivitycheck.gstatic.com/generate_204"
        "https://www.google.com"
    )
    local passed=0
    local url start end latency code
    info "Testing connectivity through ${proxy}..."
    for url in "${test_urls[@]}"; do
        start="$(now_ms)"
        code="$(curl -x "$proxy" -sS -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 15 "$url" 2>/dev/null || echo 0)"
        end="$(now_ms)"
        latency=$(( end - start ))
        if [[ "$code" =~ ^[0-9]+$ ]] && (( code >= 200 && code < 400 )); then
            ok "$url -> HTTP $code (${latency}ms)"
            passed=$((passed + 1))
        else
            fail "$url -> HTTP $code"
        fi
    done

    local exit_ip
    exit_ip="$(curl -x "$proxy" -fsS --connect-timeout 10 --max-time 15 https://api.ipify.org 2>/dev/null || true)"
    [[ -n "$exit_ip" ]] && ok "Exit IP: $exit_ip"

    cleanup_child
    echo
    if (( passed > 0 )); then
        ok "Chain is WORKING ($passed/${#test_urls[@]} tests passed)."
        return 0
    fi
    fail "Chain test FAILED. Check the config and LISTEN_PORT."
    return 1
}

cmd_scan_ips() {
    if (( $# > 0 )); then
        if [[ "${1:-}" == "--through" ]]; then
            fail "--through is not supported for raw TCP reachability scans."
            info "The previous implementation accepted this option but never used the proxy."
        else
            fail "Unknown scan-ips argument: ${1:-}"
        fi
        return 2
    fi

    local ips=(
        162.159.192.1 162.159.192.4 162.159.192.5 162.159.192.8
        162.159.192.10 162.159.192.83 162.159.192.166 162.159.195.2
        188.114.96.1 188.114.96.101 188.114.97.1
        188.114.98.224 188.114.99.73 188.114.99.153
    )
    local ports=(500 854 890 2408 2506 3854 5956 7103 8319)
    local found=0 ip port start end latency

    find_timeout
    info "Scanning ${#ips[@]} IPs x ${#ports[@]} ports..."
    printf "  %-20s %-8s %-12s\n" "IP" "Port" "Latency"
    printf "  %-20s %-8s %-12s\n" "----" "----" "-------"
    for ip in "${ips[@]}"; do
        for port in "${ports[@]}"; do
            start="$(now_ms)"
            if tcp_probe "$ip" "$port"; then
                end="$(now_ms)"
                latency=$(( end - start ))
                printf "  ${GREEN}%-20s %-8s %sms${NC}\n" "$ip" "$port" "$latency"
                found=$((found + 1))
            fi
        done
    done

    echo
    if (( found > 0 )); then
        ok "Found $found reachable Cloudflare endpoints."
        return 0
    fi
    fail "No reachable endpoints found."
    return 1
}

cmd_test_layer() {
    local layer_type="${1:?Usage: lab-runner.sh test-layer <type> <host:port>}"
    local hostport="${2:?Usage: lab-runner.sh test-layer <type> <host:port>}"
    parse_hostport "$hostport" || {
        fail "Invalid host:port. Use host:port or [IPv6]:port with port 1..65535."
        return 2
    }
    local host="$PARSED_HOST"
    local port="$PARSED_PORT"

    info "Testing $layer_type layer at $host:$port..."
    case "$layer_type" in
        tcp)
            if tcp_probe "$host" "$port"; then ok "TCP connection succeeded."; else fail "TCP connection failed."; return 1; fi
            ;;
        socks5)
            require_command nc
            require_command xxd
            local resp
            resp="$(printf '\x05\x01\x00' | nc -w 3 "$host" "$port" 2>/dev/null | xxd -p 2>/dev/null || true)"
            if [[ "$resp" == "0500"* ]]; then ok "SOCKS5 handshake succeeded."; else fail "SOCKS5 handshake failed."; return 1; fi
            ;;
        http)
            require_command curl
            local code
            code="$(curl -x "http://[$host]:$port" -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://cp.cloudflare.com/generate_204 2>/dev/null || echo 0)"
            if [[ "$host" != *:* ]]; then
                code="$(curl -x "http://$host:$port" -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 http://cp.cloudflare.com/generate_204 2>/dev/null || echo 0)"
            fi
            if [[ "$code" =~ ^[0-9]+$ ]] && (( code >= 200 && code < 400 )); then ok "HTTP proxy works (HTTP $code)."; else fail "HTTP proxy test failed (HTTP $code)."; return 1; fi
            ;;
        tls)
            require_command openssl
            local connect_target="$host:$port"
            [[ "$host" == *:* ]] && connect_target="[$host]:$port"
            if openssl s_client -connect "$connect_target" -servername "$host" -brief </dev/null >/dev/null 2>&1; then ok "TLS handshake succeeded."; else fail "TLS handshake failed."; return 1; fi
            ;;
        *)
            fail "Unknown layer type: $layer_type (use tcp, socks5, http, tls)"
            return 2
            ;;
    esac
}

banner
validate_port "$LISTEN_PORT" || { fail "LISTEN_PORT must be between 1 and 65535."; exit 2; }

case "${1:-}" in
    run)        shift; cmd_run "$@" ;;
    test)       shift; cmd_test "$@" ;;
    scan-ips)   shift; cmd_scan_ips "$@" ;;
    test-layer) shift; cmd_test_layer "$@" ;;
    install)    install_singbox ;;
    install-vwarp)
        fail "Automatic Vwarp install is disabled for security."
        info "Install Vwarp manually from its official repository and verify integrity before use."
        exit 1
        ;;
    *)
        echo "Usage: lab-runner.sh <command> [args]"
        echo
        echo "Commands:"
        echo "  run <config.json>              Run a chain config with sing-box"
        echo "  test <config.json>             Start chain and test connectivity"
        echo "  scan-ips                       Scan direct TCP reachability of known Cloudflare IPs"
        echo "  test-layer <type> <host:port>  Test tcp/socks5/http/tls (IPv6 must use [addr]:port)"
        echo "  install                        Show sing-box install guidance"
        echo "  install-vwarp                  Show Vwarp install guidance"
        exit 2
        ;;
esac
