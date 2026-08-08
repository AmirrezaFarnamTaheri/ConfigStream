// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const repoRoot = path.resolve(__dirname, "..");
function parseArgs(argv) {
  const options = {
    browserExecutable: null,
    noJsOnly: false,
    requireRuntimeConfig: false,
    root: path.join(repoRoot, "frontend"),
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--no-js-only") {
      options.noJsOnly = true;
    } else if (arg === "--require-runtime-config") {
      options.requireRuntimeConfig = true;
    } else if (arg === "--browser-executable") {
      index += 1;
      if (index >= argv.length) {
        throw new Error("--browser-executable requires a file path");
      }
      options.browserExecutable = path.resolve(argv[index]);
    } else if (arg.startsWith("--browser-executable=")) {
      options.browserExecutable = path.resolve(
        arg.slice("--browser-executable=".length),
      );
    } else if (arg === "--root") {
      index += 1;
      if (index >= argv.length) {
        throw new Error("--root requires a directory argument");
      }
      options.root = path.resolve(argv[index]);
    } else if (arg.startsWith("--root=")) {
      options.root = path.resolve(arg.slice("--root=".length));
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

let frontendRoot = path.join(repoRoot, "frontend");
const protocolMatrixPath = path.join(repoRoot, "docs", "protocol_matrix.json");
const pages = [
  "index.html",
  "about.html",
  "analytics.html",
  "evidence.html",
  "proxies.html",
  "lab.html",
  "wiki.html",
];

const systemChromiumCandidates =
  process.platform === "win32"
    ? [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
      ]
    : process.platform === "darwin"
      ? [
          "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
          "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
      : [
          "/usr/bin/google-chrome",
          "/usr/bin/google-chrome-stable",
          "/usr/bin/chromium",
          "/usr/bin/chromium-browser",
          "/usr/bin/microsoft-edge",
        ];

const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "application/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".woff2", "font/woff2"],
]);

function labStrategiesPath() {
  return path.join(frontendRoot, "assets", "data", "lab_strategies.json");
}

function browserExecutableFromEnvironment(options) {
  const executable =
    options.browserExecutable ||
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
    process.env.CHROME_BIN ||
    process.env.CHROMIUM_BIN;
  if (!executable) {
    return null;
  }
  const resolved = path.resolve(executable);
  if (!fs.existsSync(resolved)) {
    throw new Error(`Configured browser executable does not exist: ${resolved}`);
  }
  return resolved;
}

function systemChromiumExecutable() {
  return systemChromiumCandidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function isMissingManagedBrowserError(error) {
  return (
    error &&
    typeof error.message === "string" &&
    error.message.includes("Executable doesn't exist")
  );
}

async function launchChromium(options) {
  const configuredExecutable = browserExecutableFromEnvironment(options);
  if (configuredExecutable) {
    return chromium.launch({ executablePath: configuredExecutable });
  }

  try {
    return await chromium.launch();
  } catch (error) {
    const fallbackExecutable = systemChromiumExecutable();
    if (!fallbackExecutable || !isMissingManagedBrowserError(error)) {
      throw error;
    }
    console.warn(
      `Managed Playwright Chromium is unavailable; using ${fallbackExecutable}`,
    );
    return chromium.launch({ executablePath: fallbackExecutable });
  }
}

function createServer(overrides = {}) {
  return http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
    const override = overrides[requestPath];
    if (override) {
      if (typeof override === "function") {
        override(request, response);
        return;
      }
      response.writeHead(override.status || 200, {
        "content-type": override.contentType || "application/json; charset=utf-8",
      });
      response.end(override.body);
      return;
    }

    const relativePath = requestPath === "/" ? "/index.html" : requestPath;
    const target = path.normalize(
      path.join(frontendRoot, decodeURIComponent(relativePath)),
    );

    if (target !== frontendRoot && !target.startsWith(frontendRoot + path.sep)) {
      response.writeHead(403);
      response.end("forbidden");
      return;
    }

    fs.readFile(target, (error, data) => {
      if (error) {
        response.writeHead(404);
        response.end("not found");
        return;
      }

      response.writeHead(200, {
        "content-type":
          mimeTypes.get(path.extname(target)) || "application/octet-stream",
      });
      response.end(data);
    });
  });
}

function publicCanonicalProtocols() {
  const matrix = JSON.parse(fs.readFileSync(protocolMatrixPath, "utf8"));
  return matrix.protocols
    .filter((entry) => entry.public && entry.kind === "canonical")
    .map((entry) => entry.id);
}

function buildProtocolFixture() {
  return publicCanonicalProtocols().map((protocol, index) => ({
    id: `protocol-fixture-${protocol}`,
    protocol,
    host: `${protocol.replace(/[^a-z0-9-]/gi, "-")}.fixture.example`,
    port: 10000 + index,
    country_code: index % 2 === 0 ? "US" : "DE",
    city: `Fixture ${index + 1}`,
    latency: 50 + index,
    is_working: index % 3 !== 0,
    process: "native",
    config: `${protocol}://fixture.example/${index}`,
    history: [50 + index, 55 + index],
  }));
}

function labStrategyIds() {
  const manifest = JSON.parse(fs.readFileSync(labStrategiesPath(), "utf8"));
  return manifest.strategies.map((strategy) => strategy.id);
}

function assertRuntimeConfig(root) {
  const runtimeConfigPath = path.join(root, "assets", "js", "runtime-config.js");
  if (!fs.existsSync(runtimeConfigPath)) {
    throw new Error("Missing deploy runtime config: assets/js/runtime-config.js");
  }
  const content = fs.readFileSync(runtimeConfigPath, "utf8");
  const forbiddenMarkers = [
    "79e/79e/",
    "PLACEHOLDER_PUBLIC_KEY",
    "PLACEHOLDER_KEY_INJECTED_BY_CI",
  ];
  for (const marker of forbiddenMarkers) {
    if (content.includes(marker)) {
      throw new Error(`Deploy runtime config still contains placeholder marker: ${marker}`);
    }
  }
  if (/PUBLIC_KEY:\s*""/.test(content)) {
    throw new Error("Deploy runtime config is missing PUBLIC_KEY");
  }
  if (/STEGO_KEY:\s*""/.test(content)) {
    throw new Error("Deploy runtime config is missing STEGO_KEY");
  }
}

function isExpectedProtocolSmokeConsoleError(message) {
  return (
    message.includes("Browser-limited reachability check failed to load") ||
    message.includes("WebAssembly") ||
    message.includes("Incorrect response MIME type") ||
    message.includes("/ws/updates") ||
    message.includes("[WS] Error") ||
    message.includes("WebSocket connection") ||
    message.includes("Failed to load resource")
  );
}

async function listen(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      resolve(server.address().port);
    });
  });
}

async function closeServer(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function exercisePages(browser, baseUrl, allowedHost, options = {}) {
  const blockedUrls = [];
  const context = await browser.newContext({
    javaScriptEnabled: options.javaScriptEnabled !== false,
  });
  const page = await context.newPage();

  await page.route("**/*", (route) => {
    const requestUrl = route.request().url();
    const parsed = new URL(requestUrl);
    if (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.host !== allowedHost
    ) {
      blockedUrls.push(requestUrl);
      return route.abort();
    }

    return route.continue();
  });

  if (options.javaScriptEnabled !== false) {
    await page.addInitScript(() => {
      const style = document.createElement("style");
      style.innerHTML =
        "*,*::before,*::after{animation:none!important;transition:none!important;opacity:1!important}";
      document.head.appendChild(style);
    });
  }

  for (const pageName of pages) {
    await page.goto(`${baseUrl}/${pageName}`, {
      waitUntil: "domcontentloaded",
      timeout: 10000,
    });
    await page.locator(".header-logo-text").waitFor({
      state: "visible",
      timeout: 10000,
    });
    await page.locator("#main-nav").waitFor({
      state: "visible",
      timeout: 10000,
    });
  }

  await context.close();

  if (blockedUrls.length > 0) {
    throw new Error(`External requests blocked: ${blockedUrls.join(", ")}`);
  }
}

async function exerciseProtocolRender(browser) {
  const fixture = buildProtocolFixture();
  const metadata = {
    last_updated_utc: "2026-05-08T00:00:00Z",
    total_proxies: fixture.length,
    total_working: fixture.filter((proxy) => proxy.is_working).length,
    protocols: Object.fromEntries(fixture.map((proxy) => [proxy.protocol, 1])),
  };
  const server = createServer({
    "/proxies.json": {
      body: JSON.stringify(fixture),
    },
    "/api/proxies": {
      body: JSON.stringify(fixture),
    },
    "/metadata.json": {
      body: JSON.stringify(metadata),
    },
    "/api/stats": {
      body: JSON.stringify(metadata),
    },
  });
  const port = await listen(server);
  const baseUrl = `http://127.0.0.1:${port}`;
  const allowedHost = new URL(baseUrl).host;
  const blockedUrls = [];
  const consoleErrors = [];
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !isExpectedProtocolSmokeConsoleError(message.text())
    ) {
      consoleErrors.push(message.text());
    }
  });

  await page.route("**/*", (route) => {
    const requestUrl = route.request().url();
    const parsed = new URL(requestUrl);
    if (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.host !== allowedHost
    ) {
      blockedUrls.push(requestUrl);
      return route.abort();
    }

    return route.continue();
  });

  await page.addInitScript(() => {
    const style = document.createElement("style");
    style.innerHTML =
      "*,*::before,*::after{animation:none!important;transition:none!important;opacity:1!important}";
    document.head.appendChild(style);
  });

  try {
    await page.goto(`${baseUrl}/proxies.html`, {
      waitUntil: "domcontentloaded",
      timeout: 10000,
    });
    await page.locator("#proxiesTableBody tr").first().waitFor({
      state: "visible",
      timeout: 10000,
    });

    const renderedProtocols = await page
      .locator("#proxiesTableBody .badge-protocol")
      .evaluateAll((badges) => badges.map((badge) => badge.textContent.trim()));
    const expectedProtocols = fixture.map((proxy) => proxy.protocol.toUpperCase());
    const missingProtocols = expectedProtocols.filter(
      (protocol) => !renderedProtocols.includes(protocol),
    );

    if (missingProtocols.length > 0) {
      throw new Error(
        `Missing rendered protocol badges: ${missingProtocols.join(", ")}`,
      );
    }

    const dropdownProtocols = await page
      .locator("#filterProtocol option")
      .evaluateAll((options) =>
        options
          .map((option) => option.textContent.trim())
          .filter((text) => text && text !== "All Protocols"),
      );
    const missingDropdownProtocols = expectedProtocols.filter(
      (protocol) => !dropdownProtocols.includes(protocol),
    );
    if (missingDropdownProtocols.length > 0) {
      throw new Error(
        `Missing protocol filter options: ${missingDropdownProtocols.join(", ")}`,
      );
    }

    if (consoleErrors.length > 0) {
      throw new Error(`Console errors: ${consoleErrors.join(" | ")}`);
    }

    if (blockedUrls.length > 0) {
      throw new Error(`External requests blocked: ${blockedUrls.join(", ")}`);
    }
  } finally {
    await context.close();
    await closeServer(server);
  }
}

async function exerciseLabXss(browser) {
  const payload = `<img src=x onerror="window.__configstreamXss = true">`;
  let labTestCalls = 0;
  const server = createServer({
    "/api/lab/test-chain": (_request, response) => {
      labTestCalls += 1;
      const body = labTestCalls === 1
        ? { success: false, error: payload }
        : { success: true, latency: payload, exit_ip: payload };
      response.writeHead(200, {
        "content-type": "application/json; charset=utf-8",
      });
      response.end(JSON.stringify(body));
    },
  });
  const port = await listen(server);
  const baseUrl = `http://127.0.0.1:${port}`;
  const allowedHost = new URL(baseUrl).host;
  const blockedUrls = [];
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.route("**/*", (route) => {
    const requestUrl = route.request().url();
    const parsed = new URL(requestUrl);
    if (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.host !== allowedHost
    ) {
      blockedUrls.push(requestUrl);
      return route.abort();
    }

    return route.continue();
  });

  try {
    await page.goto(`${baseUrl}/lab.html`, {
      waitUntil: "domcontentloaded",
      timeout: 10000,
    });
    await page.locator("#proxyUri").waitFor({ state: "visible", timeout: 10000 });
    await assertLabStrategies(page);

    await page.locator("#localProxyType").evaluate((select) => {
      select.closest("details").open = true;
    });
    await page.selectOption("#localProxyType", "socks5");
    await page.fill("#localProxyAddr", `127.0.0.1:1080${payload}`);
    await page.click("#testLocalProxy");
    await assertNoLabInjection(page, "#localProxyResult", "local proxy input");

    const proxyUri =
      `vless://11111111-1111-4111-8111-111111111111@example.com:443#${encodeURIComponent(payload)}`;
    await page.fill("#proxyUri", proxyUri);
    await page.click("#step1Next");
    await assertNoLabInjection(page, "#step1Result", "parsed proxy remark");
    await page.locator("#step-2.active").waitFor({ state: "visible", timeout: 10000 });

    await page.click("#step2Next");
    await page.locator("#step-3.active").waitFor({ state: "visible", timeout: 10000 });

    await page.selectOption("#chainType", "custom");
    await page.fill("#customOutboundsJson", payload);
    await page.click("#step3Next");
    await assertNoLabInjection(page, "#step3Result", "custom JSON error");

    await page.selectOption("#chainType", "fragment");
    await page.click("#step3Next");
    await page.locator("#step-4.active").waitFor({ state: "visible", timeout: 10000 });
    const step4Mode = await page.locator("#step4Mode").innerText();
    if (!step4Mode.includes("Live test mode.")) {
      throw new Error("Lab Step 4 did not expose live test mode on backend-capable hosting");
    }
    await page.click("#step4Test");
    await page.locator("#step4Result").waitFor({ state: "visible", timeout: 10000 });
    await assertNoLabInjection(page, "#step4Result", "live-test API error");

    await page.click("#step4Test");
    await page.locator("#step4Next:not([disabled])").waitFor({
      state: "visible",
      timeout: 10000,
    });
    await assertNoLabInjection(page, "#step4Result", "live-test API success");
    await page.click("#step4Next");
    await page.locator("#step-5.active").waitFor({ state: "visible", timeout: 10000 });

    await page.selectOption("#exportFormat", "qr");
    await page.click("#step5Export");
    await page.locator("#qrOutput").waitFor({ state: "visible", timeout: 10000 });
    const qrText = await page.locator("#qrOutput").innerText();
    if (!qrText.includes("Offline QR payload")) {
      throw new Error("Lab QR export did not render the offline payload panel");
    }
    await assertNoLabInjection(page, "#qrOutput", "offline QR payload");

    if (blockedUrls.length > 0) {
      throw new Error(`External requests blocked: ${blockedUrls.join(", ")}`);
    }
  } finally {
    await context.close();
    await closeServer(server);
  }
}

async function assertLabStrategies(page) {
  const expectedStrategies = labStrategyIds();
  const renderedStrategies = await page
    .locator("#chainType option")
    .evaluateAll((options) => options.map((option) => option.value));
  const missingStrategies = expectedStrategies.filter(
    (strategy) => !renderedStrategies.includes(strategy),
  );
  const unexpectedStrategies = renderedStrategies.filter(
    (strategy) => !expectedStrategies.includes(strategy),
  );

  if (missingStrategies.length > 0 || unexpectedStrategies.length > 0) {
    throw new Error(
      `Lab strategy dropdown mismatch. Missing: ${missingStrategies.join(", ")}; unexpected: ${unexpectedStrategies.join(", ")}`,
    );
  }
}

async function assertNoLabInjection(page, selector, label) {
  const result = page.locator(selector);
  await result.waitFor({ state: "visible", timeout: 10000 });
  // Allow svg for QR output, block otherwise
  const blockedTags = selector === "#qrOutput" ? "img,script,iframe" : "img,script,svg,iframe";
  const injectedNodes = await result.locator(blockedTags).count();
  if (injectedNodes > 0) {
    throw new Error(`Lab ${label} rendered injected nodes`);
  }

  const xssExecuted = await page.evaluate(
    () => Boolean(window.__configstreamXss),
  );
  if (xssExecuted) {
    throw new Error(`Lab ${label} executed injected script`);
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  frontendRoot = options.root;
  if (!fs.existsSync(frontendRoot) || !fs.statSync(frontendRoot).isDirectory()) {
    throw new Error(`Frontend root does not exist: ${frontendRoot}`);
  }
  if (options.requireRuntimeConfig) {
    assertRuntimeConfig(frontendRoot);
  }
  const server = createServer();
  const port = await listen(server);
  const baseUrl = `http://127.0.0.1:${port}`;
  const allowedHost = new URL(baseUrl).host;
  let browser;

  try {
    browser = await launchChromium(options);
    if (!options.noJsOnly) {
      await exercisePages(browser, baseUrl, allowedHost);
      console.log("same-origin frontend smoke passed");
      await exerciseProtocolRender(browser);
      console.log("protocol render smoke passed");
      await exerciseLabXss(browser);
      console.log("lab xss smoke passed");
    }

    await exercisePages(browser, baseUrl, allowedHost, {
      javaScriptEnabled: false,
    });
    console.log("same-origin no-js frontend smoke passed");
  } finally {
    if (browser) {
      await browser.close();
    }
    await closeServer(server);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
