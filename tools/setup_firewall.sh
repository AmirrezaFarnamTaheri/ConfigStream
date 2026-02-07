# AsanFilter
#!/usr/bin/env bash

GREEN="\033[1;32m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

BORDER_TOP="┌──────────────────────────────────────────────────────────────────────┐"
BORDER_BOTTOM="└──────────────────────────────────────────────────────────────────────┘"
INNER_WIDTH=70

if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}This script must be run as root.${RESET}"
  exit 1
fi

echo "Installing required packages (ufw)..."

if ! command -v ufw >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ufw
fi

if ! command -v ss >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y iproute2
fi

echo "Collecting active TCP/UDP listening ports..."

declare -A SEEN
total_rules=0
tcp_rules=0
udp_rules=0

while read -r proto addr; do
  [[ -z "$proto" || -z "$addr" ]] && continue
  port="${addr##*:}"
  [[ "$port" =~ ^[0-9]+$ ]] || continue

  case "$proto" in
    tcp|tcp6) key="tcp_$port"; rule="tcp" ;;
    udp|udp6) key="udp_$port"; rule="udp" ;;
    *) continue ;;
  esac

  if [[ -z "${SEEN[$key]+x}" ]]; then
    SEEN["$key"]=1
    if ufw allow "$port/$rule" >/dev/null 2>&1; then
      ((total_rules++))
      if [[ "$rule" == "tcp" ]]; then
        ((tcp_rules++))
      else
        ((udp_rules++))
      fi
    fi
  fi
done < <(ss -H -lntu | awk '{print $1" "$5}')

ssh_port=$(grep -iE '^[[:space:]]*Port[[:space:]]+[0-9]+' /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}')
ssh_port=${ssh_port:-22}

if ufw allow "$ssh_port/tcp" >/dev/null 2>&1; then
  ((total_rules++))
  ((tcp_rules++))
fi

enable_flag=0

while true; do
  read -rp "Do you want to enable UFW now? [y/n]: " answer
  case "$answer" in
    [Yy]) enable_flag=1; break ;;
    [Nn]) enable_flag=0; break ;;
    *)
      echo -e "${RED}Invalid input. Please enter 'y' or 'n'.${RESET}"
      ;;
  esac
done

if [[ "$enable_flag" -eq 1 ]]; then
  ufw --force enable >/dev/null 2>&1
fi

clear

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
  print_plain_line "To enable it, run: sudo ufw enable"
  print_blank_line
fi

print_plain_line "Summary of added rules:"
print_label_value_line "  Total rules : " "$total_rules"
print_label_value_line "  TCP rules   : " "$tcp_rules"
print_label_value_line "  UDP rules   : " "$udp_rules"
print_blank_line
print_plain_line "Review rules with: sudo ufw status numbered"

print_border_bottom
echo ""