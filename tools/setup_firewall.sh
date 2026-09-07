#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# AsanFilter

set -Eeuo pipefail

GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

BORDER_TOP="┌──────────────────────────────────────────────────────────────────────┐"
BORDER_BOTTOM="└──────────────────────────────────────────────────────────────────────┘"
INNER_WIDTH=70

if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}This script must be run as root.${RESET}"
  exit 1
fi

echo "Installing required packages (ufw/iproute2 when missing)..."

if ! command -v ufw >/dev/null 2>&1 || ! command -v ss >/dev/null 2>&1; then
  apt-get update -y
fi
if ! command -v ufw >/dev/null 2>&1; then
  apt-get install -y ufw
fi
if ! command -v ss >/dev/null 2>&1; then
  apt-get install -y iproute2
fi

is_wildcard_listener() {
  local host="$1"
  case "$host" in
    "0.0.0.0"|"*"|"[::]"|"::") return 0 ;;
    *) return 1 ;;
  esac
}

declare -A SEEN
declare -A SSH_PORTS
total_rules=0
tcp_rules=0
udp_rules=0
skipped_bound_listeners=0

allow_rule() {
  local port="$1"
  local rule="$2"
  local label="$3"
  if ! ufw allow "$port/$rule" >/dev/null 2>&1; then
    echo -e "${RED}Failed to ensure UFW rule for ${label} (${port}/${rule}).${RESET}" >&2
    exit 1
  fi
  total_rules=$((total_rules + 1))
  if [[ "$rule" == "tcp" ]]; then
    tcp_rules=$((tcp_rules + 1))
  else
    udp_rules=$((udp_rules + 1))
  fi
}

echo "Collecting wildcard-bound TCP/UDP listening ports..."
while read -r proto addr; do
  [[ -z "$proto" || -z "$addr" ]] && continue
  port="${addr##*:}"
  host="${addr%:*}"
  [[ "$port" =~ ^[0-9]+$ ]] || continue

  case "$proto" in
    tcp|tcp6) key="tcp_$port"; rule="tcp" ;;
    udp|udp6) key="udp_$port"; rule="udp" ;;
    *) continue ;;
  esac

  if ! is_wildcard_listener "$host"; then
    skipped_bound_listeners=$((skipped_bound_listeners + 1))
    continue
  fi

  if [[ -z "${SEEN[$key]+x}" ]]; then
    SEEN["$key"]=1
    allow_rule "$port" "$rule" "wildcard listener"
  fi
done < <(ss -H -lntu | awk '{print $1" "$5}')

# Preserve the port used by the current SSH session even if sshd -T is
# unavailable or the daemon uses configuration includes.
if [[ -n "${SSH_CONNECTION:-}" ]]; then
  current_ssh_port="$(awk '{print $4}' <<<"$SSH_CONNECTION")"
  if [[ "$current_ssh_port" =~ ^[0-9]+$ ]]; then
    SSH_PORTS["$current_ssh_port"]=1
  fi
fi

# Prefer sshd's effective configuration over grepping one config file. This
# handles Include directives and avoids silently assuming port 22.
if command -v sshd >/dev/null 2>&1; then
  sshd_effective=""
  if ! sshd_effective="$(sshd -T 2>/dev/null)"; then
    if [[ "${#SSH_PORTS[@]}" -eq 0 ]]; then
      echo -e "${RED}Unable to determine the effective SSH port; refusing to prepare UFW rules that could lock out remote access.${RESET}" >&2
      exit 1
    fi
    echo -e "${YELLOW}Warning: sshd -T failed; preserving only the current SSH session port.${RESET}" >&2
  else
    while read -r ssh_port; do
      [[ "$ssh_port" =~ ^[0-9]+$ ]] || continue
      SSH_PORTS["$ssh_port"]=1
    done < <(awk '$1 == "port" && $2 ~ /^[0-9]+$/ {print $2}' <<<"$sshd_effective")
  fi
fi

for ssh_port in "${!SSH_PORTS[@]}"; do
  key="tcp_$ssh_port"
  if [[ -z "${SEEN[$key]+x}" ]]; then
    SEEN["$key"]=1
    allow_rule "$ssh_port" "tcp" "SSH"
  fi
done

enable_flag=0
while true; do
  read -rp "Do you want to enable UFW now? [y/n]: " answer
  case "$answer" in
    [Yy]) enable_flag=1; break ;;
    [Nn]) enable_flag=0; break ;;
    *) echo -e "${RED}Invalid input. Please enter 'y' or 'n'.${RESET}" ;;
  esac
done

if [[ "$enable_flag" -eq 1 ]]; then
  if ! ufw --force enable >/dev/null 2>&1; then
    echo -e "${RED}UFW failed to enable. Review 'ufw status verbose' and system logs before retrying.${RESET}" >&2
    exit 1
  fi
fi

print_border_top() {
  echo "$BORDER_TOP"
}

print_border_bottom() {
  echo "$BORDER_BOTTOM"
}

print_blank_line() {
  printf "│ %-70s │\n" ""
}

print_plain_line() {
  local text="$1"
  printf "│ %-70s │\n" "$text"
}

print_colored_full_line() {
  local plain="$1"
  local color="$2"
  local len=${#plain}
  local pad=$(( INNER_WIDTH - 1 - len ))
  (( pad < 0 )) && pad=0
  printf "│ ${color}%s${RESET}%*s│\n" "$plain" "$pad" ""
}

print_label_value_line() {
  local label="$1"
  local value="$2"
  local len_plain=$(( ${#label} + ${#value} ))
  local pad=$(( INNER_WIDTH - 1 - len_plain ))
  (( pad < 0 )) && pad=0
  printf "│ %s${CYAN}%s${RESET}%*s│\n" "$label" "$value" "$pad" ""
}

echo ""
print_border_top

if [[ "$enable_flag" -eq 1 ]]; then
  print_colored_full_line "UFW has been successfully enabled." "$GREEN"
  print_blank_line
else
  print_colored_full_line "UFW is currently disabled." "$RED"
  print_plain_line "Rules were prepared but UFW was not enabled."
  print_blank_line
fi

print_plain_line "Summary of ensured rules:"
print_label_value_line "  Total rules : " "$total_rules"
print_label_value_line "  TCP rules   : " "$tcp_rules"
print_label_value_line "  UDP rules   : " "$udp_rules"
print_label_value_line "  Skipped bound listeners : " "$skipped_bound_listeners"
print_blank_line
print_plain_line "Interface/loopback-bound listeners are not auto-opened."
print_plain_line "Review rules with: sudo ufw status numbered"

print_border_bottom
echo ""
