#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
  printf "%b%s%b\n" "$1" "$2" "$NC"
}

log "$YELLOW" "🔒 Security Audit"

audit_issues=0

log "$YELLOW" "1. Checking Python dependencies"
if command -v pip-audit >/dev/null 2>&1; then
  if pip-audit --skip-editable; then
    log "$GREEN" "   ✅ No known vulnerabilities"
  else
    log "$RED" "   ❌ Vulnerabilities reported"
    audit_issues=$((audit_issues + 1))
  fi
else
  log "$YELLOW" "   ⚠️ pip-audit not installed (pip install pip-audit)"
fi

log "$YELLOW" "2. Scanning for hardcoded secrets"
if git grep -n "password\|secret\|token" -- ':(exclude)*.md' | grep -v "example\|test"; then
  log "$RED" "   ❌ Potential secrets detected"
  audit_issues=$((audit_issues + 1))
else
  log "$GREEN" "   ✅ No obvious secrets"
fi

log "$YELLOW" "3. SSL verification checks"
if grep -R "verify=False\|ssl=False" src/ >/dev/null 2>&1; then
  log "$RED" "   ❌ Disabled SSL verification found"
  audit_issues=$((audit_issues + 1))
else
  log "$GREEN" "   ✅ SSL verification enabled"
fi

log "$YELLOW" "4. Permission-sensitive files"
for file in .env .env.local config.json; do
  if [ -f "$file" ]; then
    perms=$(stat -c %a "$file" 2>/dev/null || stat -f %A "$file")
    log "$YELLOW" "   ℹ️ $file permissions: $perms"
  fi
done

log "$YELLOW" "5. Dependency pinning"
if grep -q "==" pyproject.toml; then
  log "$GREEN" "   ✅ Locked dependencies present"
else
  log "$YELLOW" "   ⚠️ Consider pinning dependencies"
fi

log "$YELLOW" "6. Bandit static analysis"
if command -v bandit >/dev/null 2>&1; then
  if bandit -q -r src/configstream; then
    log "$GREEN" "   ✅ Bandit checks passed"
  else
    log "$RED" "   ❌ Bandit reported findings"
    audit_issues=$((audit_issues + 1))
  fi
else
  log "$YELLOW" "   ⚠️ bandit not installed (pip install bandit)"
fi

if [ "$audit_issues" -eq 0 ]; then
  log "$GREEN" "Security audit passed"
  exit 0
else
  log "$RED" "Security audit found $audit_issues issue(s)"
  exit 1
fi
