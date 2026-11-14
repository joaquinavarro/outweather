// End-to-end for a drawn field: map -> design -> analyse -> overview + 3D.
// Needs internet (POWER + SSURGO for the polygon).
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

await page.goto(URL, { waitUntil: "networkidle" });
await page.waitForSelector(".leaflet-container", { timeout: 30000 });
await page.waitForTimeout(1500);

const search = page.locator(".field-map-search input");
await search.fill("Garden City, Kansas");
await page.locator(".field-map-search button").click();
await page.waitForTimeout(3500);

await page.locator(".field-map-tools .tool").first().click(); // pencil
await page.waitForTimeout(2200);

const box = await page.locator(".leaflet-container").boundingBox();
for (const [fx, fy] of [[0.34, 0.33], [0.52, 0.3], [0.56, 0.52], [0.36, 0.55]]) {
  await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
  await page.waitForTimeout(220);
}
await page.locator(".field-map-tools .tool.ok").click(); // close
await page.waitForTimeout(600);
console.log("ok   polygon drawn:", (await page.locator(".tool-area").textContent()).trim());

await page.getByRole("button", { name: /continue|continuar/i }).click();
await page.getByText(/design your rotation|diseña tu rotación/i).waitFor({ timeout: 10000 });
await page.locator(".crop-chip").first().click();
await page.locator(".crop-chip").nth(1).click();

const t0 = Date.now();
await page.getByRole("button", { name: /analyse|analizar/i }).click();
await page.waitForSelector(".rs-spinner", { timeout: 10000 });
await page.getByText(/your field at a glance|tu parcela de un vistazo/i).waitFor({ timeout: 240000 });
console.log(`ok   drawn field analysed in ${Date.now() - t0} ms`);

const header = await page.locator(".topbar").textContent();
console.log("     " + (header || "").replace(/\s+/g, " ").trim().slice(0, 90));

await page.waitForSelector(".maplibregl-canvas", { timeout: 30000 });
await page.waitForTimeout(4000);
await page.screenshot({ path: path.join(OUT, "35-drawn-overview.png"), fullPage: true });

await browser.close();
if (errors.length) { console.log("\nBrowser errors:"); for (const e of errors.slice(0, 10)) console.log(" -", e); process.exit(1); }
console.log("\nDrawn field flow passed with no console errors.");
