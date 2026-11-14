import area from "@turf/area";

export type Ring = [number, number][]; // [lon, lat], closed

/** Geodesic area of a closed lon/lat ring, in hectares (Turf). */
export function ringAreaHa(ring: Ring | null): number {
  if (!ring || ring.length < 4) return 0;
  try {
    const sqm = area({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [ring] },
    });
    return Math.max(0, Math.round((sqm / 10000) * 100) / 100);
  } catch {
    return 0;
  }
}

export function ringCentroid(ring: Ring): [number, number] {
  const pts = ring.slice(0, -1);
  return [
    pts.reduce((s, p) => s + p[0], 0) / pts.length,
    pts.reduce((s, p) => s + p[1], 0) / pts.length,
  ];
}
