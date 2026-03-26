#!/usr/bin/env node

import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_BASE_URL = "http://127.0.0.1:8089";
const DEFAULT_OUTPUT_DIR = "exports/testing-view-pdfs";
const DEFAULT_TIMEOUT_MS = 45000;
const DEBUG_PORT = 9222;

function parseArgs(argv) {
  const options = {
    accessCode: process.env.TESTING_VIEW_ACCESS_CODE || "",
    baseUrl: DEFAULT_BASE_URL,
    outputDir: DEFAULT_OUTPUT_DIR,
    planIds: [],
    testServes: 4,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--access-code") {
      options.accessCode = String(argv[index + 1] || "");
      index += 1;
      continue;
    }
    if (arg === "--base-url") {
      options.baseUrl = String(argv[index + 1] || "");
      index += 1;
      continue;
    }
    if (arg === "--output-dir") {
      options.outputDir = String(argv[index + 1] || "");
      index += 1;
      continue;
    }
    if (arg === "--plan-id") {
      const value = Number(argv[index + 1] || 0);
      if (value > 0) {
        options.planIds.push(value);
      }
      index += 1;
      continue;
    }
    if (arg === "--test-serves") {
      const value = Number(argv[index + 1] || 0);
      if (value > 0) {
        options.testServes = Math.round(value);
      }
      index += 1;
      continue;
    }
    if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!options.accessCode.trim()) {
    throw new Error("Missing testing access code. Use --access-code or TESTING_VIEW_ACCESS_CODE.");
  }
  if (!options.planIds.length) {
    throw new Error("Provide at least one --plan-id value.");
  }
  options.baseUrl = options.baseUrl.replace(/\/+$/, "");
  return options;
}

function printHelp() {
  console.log(`Usage:
  node backend/scripts/export_testing_view_pdf.mjs \\
    --access-code TEST2026 \\
    --plan-id 8 [--plan-id 12 ...] \\
    [--test-serves 4] \\
    [--base-url http://127.0.0.1:8089] \\
    [--output-dir exports/testing-view-pdfs]`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function sanitizeFilePart(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "untitled";
}

function parseSetCookieHeader(headerValue) {
  const parts = String(headerValue || "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
  if (!parts.length) {
    throw new Error("No Set-Cookie header found in login response.");
  }

  const [nameValue, ...attributes] = parts;
  const separatorIndex = nameValue.indexOf("=");
  if (separatorIndex <= 0) {
    throw new Error(`Invalid Set-Cookie header: ${headerValue}`);
  }

  const cookie = {
    name: nameValue.slice(0, separatorIndex),
    value: nameValue.slice(separatorIndex + 1),
    path: "/",
    sameSite: undefined,
    secure: false,
    httpOnly: false,
  };

  for (const attribute of attributes) {
    const [rawKey, ...rawValue] = attribute.split("=");
    const key = rawKey.trim().toLowerCase();
    const value = rawValue.join("=").trim();
    if (key === "path" && value) {
      cookie.path = value;
      continue;
    }
    if (key === "samesite" && value) {
      const normalized = value.toLowerCase();
      if (normalized === "lax") cookie.sameSite = "Lax";
      if (normalized === "strict") cookie.sameSite = "Strict";
      if (normalized === "none") cookie.sameSite = "None";
      continue;
    }
    if (key === "secure") {
      cookie.secure = true;
      continue;
    }
    if (key === "httponly") {
      cookie.httpOnly = true;
    }
  }

  return cookie;
}

async function loginForGuestAccess(baseUrl, accessCode) {
  const response = await fetch(`${baseUrl}/api/kitchen-access/testing/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ accessCode }),
    redirect: "manual",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Testing guest login failed (${response.status}): ${text}`);
  }

  const setCookieHeaders = typeof response.headers.getSetCookie === "function"
    ? response.headers.getSetCookie()
    : [];
  const rawCookie = setCookieHeaders[0] || response.headers.get("set-cookie") || "";
  return parseSetCookieHeader(rawCookie);
}

function spawnChrome() {
  const userDataDir = path.join(os.tmpdir(), `retreat-ops-chrome-${process.pid}-${Date.now()}`);
  const chrome = spawn(
    "google-chrome",
    [
      "--headless",
      "--disable-gpu",
      "--no-sandbox",
      `--remote-debugging-port=${DEBUG_PORT}`,
      `--user-data-dir=${userDataDir}`,
      "about:blank",
    ],
    {
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  let stderr = "";
  chrome.stderr.on("data", (chunk) => {
    stderr += String(chunk || "");
  });

  return { chrome, stderrRef: () => stderr, userDataDir };
}

async function waitForJson(url, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw lastError || new Error(`Timed out waiting for ${url}`);
}

class CdpClient {
  constructor(webSocket) {
    this.webSocket = webSocket;
    this.nextId = 1;
    this.pending = new Map();
    this.waiters = [];

    webSocket.addEventListener("message", (event) => {
      const payload = JSON.parse(String(event.data || "{}"));
      if (payload.id) {
        const pending = this.pending.get(payload.id);
        if (!pending) {
          return;
        }
        this.pending.delete(payload.id);
        if (payload.error) {
          pending.reject(new Error(payload.error.message || JSON.stringify(payload.error)));
        } else {
          pending.resolve(payload.result);
        }
        return;
      }
      this.emitEvent(payload);
    });
  }

  emitEvent(payload) {
    this.waiters = this.waiters.filter((waiter) => {
      if (waiter.method !== payload.method) {
        return true;
      }
      if (waiter.predicate && !waiter.predicate(payload.params || {})) {
        return true;
      }
      clearTimeout(waiter.timer);
      waiter.resolve(payload.params || {});
      return false;
    });
  }

  call(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.webSocket.send(JSON.stringify({ id, method, params }));
    });
  }

  waitFor(method, predicate = null, timeoutMs = DEFAULT_TIMEOUT_MS) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.waiters = this.waiters.filter((waiter) => waiter.timer !== timer);
        reject(new Error(`Timed out waiting for event ${method}`));
      }, timeoutMs);
      this.waiters.push({ method, predicate, resolve, reject, timer });
    });
  }

  close() {
    if (this.webSocket.readyState <= 1) {
      this.webSocket.close();
    }
  }
}

async function connectToPageClient() {
  const targets = await waitForJson(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
  const pageTarget = Array.isArray(targets)
    ? targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl)
    : null;
  if (!pageTarget) {
    throw new Error("Could not find a Chrome page target.");
  }
  const webSocket = new WebSocket(pageTarget.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Timed out connecting to Chrome CDP.")), 10000);
    webSocket.addEventListener("open", () => {
      clearTimeout(timer);
      resolve();
    });
    webSocket.addEventListener("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
  return new CdpClient(webSocket);
}

async function waitForCondition(client, expression, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const result = await client.call("Runtime.evaluate", {
        expression,
        returnByValue: true,
        awaitPromise: true,
      });
      if (result?.result?.value) {
        return result.result.value;
      }
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw lastError || new Error(`Timed out waiting for condition: ${expression}`);
}

async function exportPlanPdf(client, options, cookie, planId) {
  await client.call("Page.enable");
  await client.call("Runtime.enable");
  await client.call("Network.enable");

  const setCookieResult = await client.call("Network.setCookie", {
    name: cookie.name,
    value: cookie.value,
    url: options.baseUrl,
    path: cookie.path,
    secure: cookie.secure,
    httpOnly: cookie.httpOnly,
    sameSite: cookie.sameSite,
  });
  if (!setCookieResult?.success) {
    throw new Error(`Failed to set guest access cookie for plan ${planId}.`);
  }

  const viewUrl = new URL(`${options.baseUrl}/kitchen-test-view.html`);
  viewUrl.searchParams.set("plan", String(planId));
  viewUrl.searchParams.set("api", options.baseUrl);
  viewUrl.searchParams.set("test_serves", String(options.testServes));

  const loadEvent = client.waitFor("Page.loadEventFired");
  await client.call("Page.navigate", { url: viewUrl.toString() });
  await loadEvent;

  await waitForCondition(
    client,
    "(() => Boolean(document.getElementById('retreatPlanSelect') && !document.querySelector('.kitchen-access-overlay')))()",
  );
  await waitForCondition(
    client,
    "(() => Boolean(document.getElementById('selectAllDishes') && !document.getElementById('selectAllDishes').disabled))()",
  );

  await client.call("Runtime.evaluate", {
    expression: `
      (() => {
        const testServes = document.getElementById("testServes");
        if (testServes) {
          testServes.value = ${JSON.stringify(String(options.testServes))};
          testServes.dispatchEvent(new Event("change", { bubbles: true }));
        }
        const selectAll = document.getElementById("selectAllDishes");
        if (selectAll) {
          selectAll.click();
        }
        const picker = document.getElementById("pickerCard");
        if (picker) {
          picker.classList.add("collapsed");
        }
        return {
          title: document.getElementById("retreatTitle")?.textContent || document.title,
          selected: document.getElementById("selectedDishCount")?.textContent || "0",
        };
      })()
    `,
    returnByValue: true,
    awaitPromise: true,
  });

  const renderState = await waitForCondition(
    client,
    `(() => {
      const recipes = document.querySelectorAll(".recipe-card").length;
      const meals = document.querySelectorAll(".meal-section").length;
      const printRecipes = document.querySelectorAll(".print-recipe").length;
      const printVisible = document.getElementById("printOutput")?.getAttribute("aria-hidden") === "false";
      if (!recipes || !meals || printRecipes !== recipes || !printVisible) {
        return null;
      }
      return {
        retreatTitle: document.getElementById("retreatTitle")?.textContent || "Testing View",
        recipes,
        meals,
      };
    })()`,
  );

  const pdf = await client.call("Page.printToPDF", {
    printBackground: true,
    preferCSSPageSize: true,
  });

  const fileStem = [
    sanitizeFilePart(renderState.retreatTitle),
    `plan-${planId}`,
    `serves-${options.testServes}`,
  ].join("-");
  const outputPath = path.resolve(options.outputDir, `${fileStem}.pdf`);
  await fs.writeFile(outputPath, Buffer.from(pdf.data, "base64"));

  return {
    outputPath,
    renderState,
    viewUrl: viewUrl.toString(),
  };
}

async function removeDirQuietly(targetPath) {
  if (!targetPath) {
    return;
  }
  await fs.rm(targetPath, { recursive: true, force: true });
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  await fs.mkdir(options.outputDir, { recursive: true });

  const cookie = await loginForGuestAccess(options.baseUrl, options.accessCode);
  const chromeProcess = spawnChrome();
  let client = null;

  try {
    await waitForJson(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
    client = await connectToPageClient();

    const results = [];
    for (const planId of options.planIds) {
      const result = await exportPlanPdf(client, options, cookie, planId);
      results.push(result);
      console.log(
        JSON.stringify(
          {
            planId,
            file: result.outputPath,
            recipes: result.renderState.recipes,
            meals: result.renderState.meals,
            url: result.viewUrl,
          },
          null,
          2,
        ),
      );
    }
  } finally {
    if (client) {
      client.close();
    }
    chromeProcess.chrome.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => chromeProcess.chrome.once("exit", resolve)),
      sleep(5000),
    ]);
    if (!chromeProcess.chrome.killed) {
      chromeProcess.chrome.kill("SIGKILL");
    }
    await removeDirQuietly(chromeProcess.userDataDir);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exitCode = 1;
});
