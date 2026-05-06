// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const repoRoot = path.resolve(__dirname, "..");
const frontendRoot = path.join(repoRoot, "frontend");
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

function createServer() {
  return http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
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
