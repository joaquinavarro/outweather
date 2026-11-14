import { chromium } from "playwright";
import path from "node:path";
import fs from "node:fs";

const URL = process.env.WEB_URL || "http://127.0.0.1:8000";
const OUT = path.resolve(process.cwd(), "..", "docs", "screenshots");
fs.mkdirSync(OUT, { recursive: true });

const errors = [];
const browser = await chromium.launch({ channel: "chromium" });
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } });
page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));

const step = async (name, fn) => {
  try { await fn(); console.log("ok   " + name); }
  catch (e) { console.log("FAIL " + name + ": " + e.message); await page.screenshot({ path: path.join(OUT, "fail.png") }); throw e; }
};

await page.goto(URL, { waitUntil: "networkidle" });

await step("map landing is full-screen and minimal", async () => {
  await page.waitForSelector(".leaflet-container", { timeout: 30000 });
  await page.waitForTimeout(2000);
  // tools: pencil, trash, ha readout
  const tools = page.locator(".field-map-tools .tool");
  const n = await tools.count();
  if (n !== 2) throw new Error(`expected 2 tools, got ${n}`);
  await page.screenshot({ path: path.join(OUT, "30-map-landing.png") });
});

await step("demo preset draws and Continue appears", async () => {
  await page.locator(".maplanding-head .chip", { hasText: "North 80" }).first().click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: /continue|continuar/i }).waitFor({ timeout: 10000 });
  await page.screenshot({ path: path.join(OUT, "31-map-drawn.png") });
});

await step("design page shows crops and water", async () => {
  await page.getByRole("button", { name: /continue|continuar/i }).click();
  await page.getByText(/design your rotation|diseña tu rotación/i).waitFor({ timeout: 10000 });
  const chips = await page.locator(".crop-chip").count();
  if (chips < 5) throw new Error(`too few crop chips: ${chips}`);
  await page.screenshot({ path: path.join(OUT, "32-design.png"), fullPage: true });
});

await step("selecting crops then analysing", async () => {
  await page.locator(".crop-chip").nth(0).click();
  await page.locator(".crop-chip").nth(1).click();
  await page.getByRole("button", { name: /analyse|analizar/i }).click();
  await page.waitForSelector(".rs-spinner", { timeout: 10000 });
  await page.screenshot({ path: path.join(OUT, "33-loading.png") });
  await page.getByText(/your field at a glance|tu parcela de un vistazo/i).waitFor({ timeout: 120000 });
});

await step("overview embeds the 3D parcel and 5-tab navbar", async () => {
  const tabs = await page.locator(".tabs .tab").count();
  if (tabs !== 5) throw new Error(`expected 5 tabs, got ${tabs}`);
  await page.waitForSelector(".maplibregl-canvas", { timeout: 30000 });
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(OUT, "34-overview.png"), fullPage: true });
});

await step("3D time bar moves through past years", async () => {
  const slider = page.locator(".field3d-time input[type=range]");
  await slider.waitFor({ state: "visible" });
  const max = await slider.getAttribute("max");
  await slider.fill(String(Math.floor(Number(max) / 2)));
  await page.waitForTimeout(1200);
  const meta = await page.locator(".field3d-time-meta").textContent();
  if (!/SPEI/.test(meta || "")) throw new Error(`meta: ${meta}`);
  console.log("     " + (meta || "").replace(/\s+/g, " ").trim());
});

await step("details toggle reveals the breakdown", async () => {
  await page.locator(".details-summary").click();
  await page.waitForTimeout(400);
  const body = await page.textContent("body");
  if (!body.includes("breakdown") && !body.includes("desglose")) throw new Error("no breakdown");
});

await browser.close();
if (errors.length) { console.log("\nBrowser errors:"); for (const e of errors.slice(0, 10)) console.log(" -", e); process.exit(1); }
console.log("\nNew flow passed with no console errors.");
