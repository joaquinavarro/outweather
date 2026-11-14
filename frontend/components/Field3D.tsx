"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Locale } from "@/lib/i18n";
import { type Ring } from "@/lib/geo";

export type TimePoint = { year: number; spei: number };

function speiColor(v: number): string {
  if (v >= 0.5) return "#3e9b5f";
  if (v >= -0.5) return "#7bc96f";
  if (v >= -1.0) return "#d9b23a";
  if (v >= -1.5) return "#de7b3c";
  return "#c8433b";
}

function speiLabel(v: number, locale: Locale): string {
  const es = locale === "es-ES";
  if (v >= 0.5) return es ? "húmedo" : "wet";
  if (v >= -0.5) return es ? "normal" : "normal";
  if (v >= -1.0) return es ? "sequía leve" : "mild drought";
  if (v >= -1.5) return es ? "sequía moderada" : "moderate drought";
  return es ? "sequía severa" : "severe drought";
}

export default function Field3D({
  boundary,
  years,
  locale,
  t,
}: {
  boundary: Ring | null;
  years: TimePoint[];
  locale: Locale;
  t: any;
}) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [idx, setIdx] = useState(-1);
  const [orbiting, setOrbiting] = useState(false);
  const orbitRef = useRef<number | null>(null);

  const points = years;
  const safeIdx = idx < 0 ? Math.max(points.length - 1, 0) : Math.min(idx, Math.max(points.length - 1, 0));
  const current = points[safeIdx];
  const color = current ? speiColor(current.spei) : "#7bc96f";

  const style = useMemo<maplibregl.StyleSpecification>(
    () => ({
      version: 8,
      sources: {
        "esri-satellite": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Esri World Imagery",
        },
        "terrain-dem": {
          type: "raster-dem",
          tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
          tileSize: 256,
          encoding: "terrarium",
          maxzoom: 15,
        },
      },
      layers: [
        { id: "esri-satellite", type: "raster", source: "esri-satellite" },
      ],
    }),
    [],
  );

  useEffect(() => {
    if (!container.current || map.current) return;
    try {
      maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
    } catch {
      /* older bundles inline the worker */
    }
    const instance = new maplibregl.Map({
      container: container.current,
      style,
      center: [-98.5, 38.5],
      zoom: 13,
      pitch: 62,
      bearing: -25,
      maxPitch: 85,
      attributionControl: false,
    });
    instance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    instance.on("load", () => {
      setReady(true);
      try {
        instance.setTerrain({ source: "terrain-dem", exaggeration: 1.6 });
        instance.setSky({
          "sky-color": "#183528",
          "horizon-color": "#2b523d",
          "fog-color": "#183528",
          "fog-ground-blend": 0.4,
        });
      } catch {
        /* terrain/sky are cosmetic */
      }
    });
    map.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      if (orbitRef.current) cancelAnimationFrame(orbitRef.current);
      instance.remove();
      map.current = null;
    };
  }, [style]);

  const fitField = useCallback(() => {
    const instance = map.current;
    if (!instance || !boundary || boundary.length < 4) return;
    const bounds = boundary.reduce(
      (b, [lon, lat]) => b.extend([lon, lat] as [number, number]),
      new maplibregl.LngLatBounds([boundary[0][0], boundary[0][1]], [boundary[0][0], boundary[0][1]]),
    );
    instance.fitBounds(bounds, {
      padding: { top: 80, bottom: 90, left: 80, right: 80 },
      pitch: 62,
      bearing: -25,
      maxZoom: 16.5,
      duration: 1100,
    });
  }, [boundary]);

  const drawParcel = useCallback(() => {
    const instance = map.current;
    if (!instance || !ready) return;
    const data: any = {
      type: "FeatureCollection",
      features:
        boundary && boundary.length >= 4
          ? [{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [boundary] } }]
          : [],
    };
    const existing = instance.getSource("field-source") as maplibregl.GeoJSONSource | undefined;
    if (existing) {
      existing.setData(data);
    } else {
      instance.addSource("field-source", { type: "geojson", data });
      instance.addLayer({
        id: "field-fill",
        type: "fill",
        source: "field-source",
        paint: { "fill-color": color, "fill-opacity": 0.55 },
      });
      instance.addLayer({
        id: "field-outline",
        type: "line",
        source: "field-source",
        paint: { "line-color": "#ffffff", "line-width": 2.5, "line-opacity": 0.9 },
      });
    }
    if (instance.getLayer("field-fill")) {
      instance.setPaintProperty("field-fill", "fill-color", color);
    }
  }, [ready, boundary, color]);

  useEffect(() => {
    drawParcel();
  }, [drawParcel]);

  useEffect(() => {
    if (ready && boundary) fitField();
  }, [ready, boundary, fitField]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    if (!orbiting) {
      if (orbitRef.current) cancelAnimationFrame(orbitRef.current);
      orbitRef.current = null;
      return;
    }
    const step = () => {
      if (!map.current) return;
      map.current.setBearing((map.current.getBearing() + 0.25) % 360);
      orbitRef.current = requestAnimationFrame(step);
    };
    orbitRef.current = requestAnimationFrame(step);
    return () => {
      if (orbitRef.current) cancelAnimationFrame(orbitRef.current);
    };
  }, [orbiting]);

  return (
    <div className="field3d">
      <div className="field3d-canvas" ref={container}>
        <div className="field3d-toolbar">
          <button className={`chip ${orbiting ? "active" : ""}`} onClick={() => setOrbiting((v) => !v)}>
            {orbiting ? t("v3.stopOrbit") : t("v3.orbit")}
          </button>
          <button className="chip" onClick={fitField}>
            {t("v3.center")}
          </button>
        </div>

        <div className="field3d-time">
          <div className="field3d-time-head">
            <span className="kpi-label">{t("v3.year")}</span>
            <span className="mono" style={{ fontWeight: 700 }}>
              {current ? current.year : "—"}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(0, points.length - 1)}
            value={safeIdx}
            onChange={(e) => setIdx(Number(e.target.value))}
            className="slider"
            aria-label={t("v3.year")}
          />
          <div className="field3d-time-meta">
            <span className="swatch" style={{ background: color }} />
            <span className="small">
              {current ? `SPEI-12 ${current.spei >= 0 ? "+" : ""}${current.spei.toFixed(1)} · ${speiLabel(current.spei, locale)}` : "—"}
            </span>
          </div>
          <div className="tiny muted" style={{ display: "flex", justifyContent: "space-between" }}>
            <span>{points[0]?.year}</span>
            <span>{points[points.length - 1]?.year}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
