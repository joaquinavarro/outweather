// MapLibre ships its worker as a separate module. Next bundles the main library
// but not the worker, so we copy it into /public and point setWorkerUrl at it.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const source = path.join(root, "node_modules", "maplibre-gl", "dist", "maplibre-gl-worker.mjs");
const targetDir = path.join(root, "public");
const target = path.join(targetDir, "maplibre-gl-worker.mjs");

if (!fs.existsSync(source)) {
  console.warn("[copy-worker] maplibre worker not found, skipping");
  process.exit(0);
}
fs.mkdirSync(targetDir, { recursive: true });
fs.copyFileSync(source, target);
console.log(`[copy-worker] public/maplibre-gl-worker.mjs (${Math.round(fs.statSync(target).size / 1024)} KB)`);
