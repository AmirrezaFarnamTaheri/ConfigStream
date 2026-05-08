// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const repoRoot = path.resolve(__dirname, "..");
const frontendRoot = path.join(repoRoot, "frontend");
const protocolMatrixPath = path.join(repoRoot, "docs", "protocol_matrix.json");
const pages = [
  "index.html",
  "about.html",
  "analytics.html",
  "proxies.html",
  "lab.html",
  "wiki.html",
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

function createServer(overrides = {}) {
  return http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
    const override = overrides[requestPath];
    if (override) {
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

async function main() {
  const noJsOnly = process.argv.includes("--no-js-only");
  const server = createServer();
  const port = await listen(server);
  const baseUrl = `http://127.0.0.1:${port}`;
  const allowedHost = new URL(baseUrl).host;
  let browser;

  try {
    browser = await chromium.launch();
    if (!noJsOnly) {
      await exercisePages(browser, baseUrl, allowedHost);
      console.log("same-origin frontend smoke passed");
      await exerciseProtocolRender(browser);
      console.log("protocol render smoke passed");
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
