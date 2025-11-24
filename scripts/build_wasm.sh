#!/bin/bash
set -e

echo "🏗️ Building WASM Module..."
cd src/go/tester

# 1. Build .wasm binary
GOOS=js GOARCH=wasm go build -o ../../../frontend/assets/wasm/tester.wasm wasm_main.go

# 2. Copy JS Glue Code (Required for Go WASM to run)
# We assume 'go' is in path
cp "$(go env GOROOT)/misc/wasm/wasm_exec.js" ../../../frontend/assets/js/

echo "✅ WASM Build Complete."
