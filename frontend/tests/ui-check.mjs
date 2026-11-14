// Full regression over the new flow: map -> design -> results -> all tabs.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const URL = process.env.WEB_URL || "http://127.0.0.1:8000";
const OUT = path.resolve(process.cwd(), "..", "docs", "screenshots");
fs.mkdirSync(OUT, { recursive: true });

const errors = [];
const browser = await chromium.launch({ channel: "chromium" });
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } });
page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) errors.push(`http ${r.status()}: ${r.url().slice(0, 110)}`); });

const step = async (name, fn) => {
  try { await fn(); console.log(`ok   ${name}`); }
  catch (e) { console.log(`FAIL ${name}: ${e.message}`); await page.screenshot({ path: path.join(OUT, "error.png"), fullPage: true }); throw e; }
};

const runDemo = async (label) => {
  await page.waitForSelector(".leaflet-container", { timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.locator(".maplanding-head .chip", { hasText: label }).first().click();
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: /continue|continuar/i }).click();
  await page.getByText(/design your rotation|diseña tu rotación/i).waitFor({ timeout: 10000 });
  await page.locator(".crop-chip").first().click();
  await page.getByRole("button", { name: /analyse|analizar/i }).click();
  await page.waitForSelector(".rs-spinner", { timeout: 10000 });
  await page.getByText(/your field at a glance|tu parcela de un vistazo/i).waitFor({ timeout: 180000 });
};

await step("map landing", async () => {
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForSelector(".leaflet-container", { timeout: 30000 });
  await page.screenshot({ path: path.join(OUT, "01-landing.png") });
});

await step("demo field runs through design", async () => {
  await runDemo("North 80");
  await page.screenshot({ path: path.join(OUT, "03-overview.png"), fullPage: true });
});

await step("5-tab navbar", async () => {
  const tabs = await page.locator(".tabs .tab").count();
  if (tabs !== 5) throw new Error(`expected 5 tabs, got ${tabs}`);
  await page.waitForSelector(".maplibregl-canvas", { timeout: 30000 });
  await page.waitForTimeout(3000);
});

await step("rotation tab", async () => {
  await page.getByRole("button", { name: /rotation|rotación/i, exact: true }).click();
  await page.getByRole("heading", { name: /proposed rotation|rotación propuesta/i }).waitFor({ timeout: 10000 });
  await page.screenshot({ path: path.join(OUT, "04-rotation.png"), fullPage: true });
});

await step("irrigation tab", async () => {
  await page.getByRole("button", { name: /irrigation|riego/i, exact: true }).click();
  await page.getByText(/zones|zonas|Irrigation design|diseño de riego/i).first().waitFor({ timeout: 10000 });
});

await step("disease tab", async () => {
  await page.getByRole("button", { name: /disease|sanidad/i, exact: true }).click();
  await page.waitForSelector(".data", { timeout: 10000 });
});

await step("hazards tab", async () => {
  await page.getByRole("button", { name: /hazards|riesgos/i, exact: true }).click();
  await page.waitForSelector(".card", { timeout: 10000 });
});

await step("rotation edit recomputes", async () => {
  await page.getByRole("button", { name: /rotation|rotación/i, exact: true }).click();
  await page.locator(".timeline-row").first().click();
  const select = page.locator(".timeline-row select").first();
  await select.waitFor({ state: "visible", timeout: 10000 });
  const current = await select.inputValue();
  await select.selectOption(current === "corn" ? "soybean" : "corn");
  await page.getByText("Edited manually").waitFor({ timeout: 60000 });
  await page.getByRole("button", { name: /restore optimised|restaurar optimizada/i }).click();
  await page.getByText("Edited manually").waitFor({ state: "hidden", timeout: 60000 });
});

await step("exports the PDF", async () => {
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 60000 }),
    page.getByRole("button", { name: /export pdf/i }).click(),
  ]);
  const bytes = fs.readFileSync(await download.path());
  if (bytes.subarray(0, 5).toString() !== "%PDF-") throw new Error("not a PDF");
  console.log(`     pdf ${bytes.length} bytes`);
});

await step("switches to Spanish", async () => {
  await page.getByRole("button", { name: "ES", exact: true }).click();
  await page.waitForTimeout(600);
  const body = await page.textContent("body");
  for (const needle of ["Resumen", "Rotación", "Riego", "Sanidad", "Riesgos"]) {
    if (!body.includes(needle)) throw new Error(`missing ES tab "${needle}"`);
  }
});

await browser.close();
if (errors.length) { console.log("\nBrowser errors:"); for (const e of errors.slice(0, 12)) console.log(" -", e); process.exit(1); }
console.log("\nAll UI checks passed with no console errors.");
