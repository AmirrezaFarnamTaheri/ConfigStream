#!/bin/bash
set -e

echo "🏗️ Building WASM Module..."

# Check Go version (ensure 1.21+)
if command -v go &> /dev/null; then
    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    echo "Detected Go version: $GO_VERSION"

    # Simple version check (major.minor)
    IFS='.' read -r -a parts <<< "$GO_VERSION"
    if [ "${parts[0]}" -lt 1 ] || ([ "${parts[0]}" -eq 1 ] && [ "${parts[1]}" -lt 21 ]); then
        echo "❌ Go version 1.21+ required. Found $GO_VERSION"
        exit 1
    fi
else
    echo "❌ Go is not installed."
    exit 1
fi

cd src/go/tester

# 1. Build .wasm binary
# [FIX] Added tags to ensure frontend supports uTLS, Reality, QUIC, etc.
GOOS=js GOARCH=wasm go build -tags "with_quic,with_dhcp,with_wireguard,with_ech,with_utls,with_reality_server,with_clash_api,with_gvisor" -o ../../../frontend/assets/wasm/tester.wasm wasm_main.go

# 2. Copy JS Glue Code (Required for Go WASM to run)
GOROOT=$(go env GOROOT)
WASM_EXEC_PATH=""

# Check possible locations
if [ -f "$GOROOT/lib/wasm/wasm_exec.js" ]; then
    WASM_EXEC_PATH="$GOROOT/lib/wasm/wasm_exec.js"
elif [ -f "$GOROOT/misc/wasm/wasm_exec.js" ]; then
    WASM_EXEC_PATH="$GOROOT/misc/wasm/wasm_exec.js"
else
    # Fallback search
    echo "⚠️  wasm_exec.js not found in standard locations. Searching..."
    WASM_EXEC_PATH=$(find "$GOROOT" -name wasm_exec.js | head -n 1)
fi

if [ -z "$WASM_EXEC_PATH" ] || [ ! -f "$WASM_EXEC_PATH" ]; then
    echo "❌ Error: Could not find wasm_exec.js in GOROOT: $GOROOT"
    exit 1
fi

echo "📋 Found wasm_exec.js at: $WASM_EXEC_PATH"
cp "$WASM_EXEC_PATH" ../../../frontend/assets/js/

echo "✅ WASM Build Complete."
