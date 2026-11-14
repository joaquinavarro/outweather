// Offline fallback check for F4: with the provider layer blocked, the time map
// must fall back to the modelled parcel and say so.
import { chromium } from "playwright";

const browser = await chromium.launch({ channel: "chromium" });
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));

await page.goto("http://localhost:3000", { waitUntil: "domcontentloaded" });
await page.locator(".farm-card").first().click();
await page.getByRole("button", { name: /run the simulation/i }).click();
await page.getByText("Resilience index").waitFor({ timeout: 120000 });
await page.getByRole("button", { name: "Time map", exact: true }).click();
await page.waitForTimeout(2500);

const body = await page.textContent("body");
const hasFallbackNote = body.includes("imagery unavailable offline");
const svgCount = await page.locator(".zone-map").count();
await page.screenshot({ path: "../docs/screenshots/07c-imagery-offline-fallback.png", fullPage: true });
await browser.close();

console.log("fallback note:", hasFallbackNote, "| parcel svg:", svgCount, "| page errors:", errors.length);
if (!hasFallbackNote || svgCount < 1) {
  console.error("offline fallback did not render");
  process.exit(1);
}
