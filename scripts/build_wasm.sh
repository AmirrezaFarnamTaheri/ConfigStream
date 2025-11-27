#!/bin/bash
set -e

echo "🏗️ Building WASM Module..."
cd src/go/tester

# 1. Build .wasm binary
GOOS=js GOARCH=wasm go build -o ../../../frontend/assets/wasm/tester.wasm wasm_main.go

# 2. Copy JS Glue Code (Required for Go WASM to run)
# We assume 'go' is in path.
# Go 1.24+ may place wasm_exec.js in lib/wasm instead of misc/wasm
GOROOT=$(go env GOROOT)

if [ -f "$GOROOT/lib/wasm/wasm_exec.js" ]; then
    WASM_EXEC="$GOROOT/lib/wasm/wasm_exec.js"
elif [ -f "$GOROOT/misc/wasm/wasm_exec.js" ]; then
    WASM_EXEC="$GOROOT/misc/wasm/wasm_exec.js"
else
    # Fallback: try to find it under GOROOT (fixes issue with some Go toolchain layouts)
    WASM_EXEC=$(find "$GOROOT" -name wasm_exec.js -print -quit)
    if [ -z "$WASM_EXEC" ]; then
        echo "Error: wasm_exec.js not found in $GOROOT"
        exit 1
    fi
fi

echo "Copying wasm_exec.js from $WASM_EXEC"
cp "$WASM_EXEC" ../../../frontend/assets/js/

echo "✅ WASM Build Complete."
