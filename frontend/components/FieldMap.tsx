"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  TileLayer,
  ZoomControl,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import type { Locale } from "@/lib/i18n";
import { ringAreaHa, type Ring } from "@/lib/geo";

function MapCapture({ onReady }: { onReady: (m: L.Map) => void }) {
  const map = useMap();
  useEffect(() => {
    onReady(map);
  }, [map, onReady]);
  return null;
}

function Bounds({ ring }: { ring: Ring | null }) {
  const map = useMap();
  const first = useRef(true);
  useEffect(() => {
    if (!ring || ring.length < 4) return;
    const latlngs = ring.map(([lon, lat]) => [lat, lon] as [number, number]);
    const bounds = L.latLngBounds(latlngs);
    map.fitBounds(bounds, { padding: [70, 70], maxZoom: 16, animate: !first.current });
    first.current = false;
  }, [map, ring]);
  return null;
}

function ClickCatcher({
  active,
  onAdd,
  onClose,
}: {
  active: boolean;
  onAdd: (p: [number, number]) => void;
  onClose: () => void;
}) {
  const map = useMap();
  const points = useRef<L.LatLng[]>([]);
  useMapEvents({
    click(e) {
      if (!active) return;
      if (points.current.length >= 3) {
        const start = points.current[0];
        if (map.distance(e.latlng, start) < 35) {
          onClose();
          return;
        }
      }
      points.current.push(e.latlng);
      onAdd([e.latlng.lng, e.latlng.lat]);
    },
  });
  useEffect(() => {
    points.current = [];
  }, [active]);
  return null;
}

const PencilIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" fill="currentColor" />
  </svg>
);

const TrashIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="currentColor" />
  </svg>
);

const SearchIcon = () => (
  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" strokeWidth="1.8" />
    <path d="m16 16 4.3 4.3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export default function FieldMap({
  ring,
  onChange,
  locale,
  t,
  busy,
  onContinue,
}: {
  ring: Ring | null;
  onChange: (ring: Ring | null) => void;
  locale: Locale;
  t: any;
  busy?: boolean;
  onContinue?: () => void;
}) {
  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<Ring>([]);
  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [map, setMap] = useState<L.Map | null>(null);

  const vertexIcon = useMemo(
    () => L.divIcon({ className: "rs-vertex", iconSize: [14, 14], iconAnchor: [7, 7] }),
    [],
  );
  const firstIcon = useMemo(
    () => L.divIcon({ className: "rs-vertex rs-vertex-first", iconSize: [16, 16], iconAnchor: [8, 8] }),
    [],
  );

  const closeRing = useCallback(
    (pts: Ring) => {
      if (pts.length < 3) return;
      const closed: Ring = [...pts, pts[0]];
      onChange(closed);
      setDrawing(false);
      setPoints([]);
      setEditing(true);
    },
    [onChange],
  );

  const startDrawing = () => {
    setEditing(false);
    setPoints([]);
    setDrawing(true);
    if (map && map.getZoom() < 11) {
      map.flyTo(map.getCenter(), 13, { duration: 0.9 });
    }
  };

  const cancel = () => {
    setDrawing(false);
    setPoints([]);
  };

  const moveVertex = (index: number, latlng: L.LatLng) => {
    if (!ring) return;
    const next = ring.map((p) => [...p]) as Ring;
    next[index] = [latlng.lng, latlng.lat];
    next[next.length - 1] = next[0];
    onChange(next);
  };

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    const value = query.trim();
    if (!value || !map) return;
    const coords = value.match(/^([-+]?[0-9]*\.?[0-9]+)[,\s]+([-+]?[0-9]*\.?[0-9]+)$/);
    if (coords) {
      map.flyTo([parseFloat(coords[1]), parseFloat(coords[2])], 14, { duration: 1.2 });
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(value)}`,
        { headers: { "Accept-Language": locale } },
      );
      const data = await res.json();
      if (data?.[0]) map.flyTo([parseFloat(data[0].lat), parseFloat(data[0].lon)], 14, { duration: 1.4 });
    } catch {
      /* geocoding is a convenience */
    } finally {
      setSearching(false);
    }
  };

  const areaHa = ring ? ringAreaHa(ring) : 0;

  return (
    <div className="field-map field-map-full">
      <MapContainer
        center={[38.5, -98.5]}
        zoom={6}
        zoomControl={false}
        style={{ width: "100%", height: "100%", background: "#0a0f0b" }}
      >
        <MapCapture onReady={setMap} />
        <TileLayer
          attribution='Imagery &copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          maxZoom={19}
        />
        <ZoomControl position="bottomright" />
        <Bounds ring={ring} />
        <ClickCatcher
          active={drawing}
          onAdd={(p) => setPoints((prev) => [...prev, p])}
          onClose={() => closeRing(points)}
        />

        {ring && ring.length >= 4 && !drawing && (
          <Polygon
            positions={ring.map(([lon, lat]) => [lat, lon] as [number, number])}
            pathOptions={{ color: "#7bc96f", fillColor: "#7bc96f", fillOpacity: 0.22, weight: 2.5 }}
          />
        )}

        {ring &&
          ring.length >= 4 &&
          editing &&
          !drawing &&
          ring.slice(0, -1).map(([lon, lat], idx) => (
            <Marker
              key={`v-${idx}-${lon}-${lat}`}
              position={[lat, lon]}
              icon={vertexIcon}
              draggable
              eventHandlers={{
                drag: (e) => moveVertex(idx, (e.target as L.Marker).getLatLng()),
              }}
            />
          ))}

        {drawing && points.length > 0 && (
          <>
            <Polyline
              positions={points.map(([lon, lat]) => [lat, lon] as [number, number])}
              pathOptions={{ color: "#7bc96f", weight: 2.5, dashArray: "6 6" }}
            />
            {points.map(([lon, lat], idx) => (
              <Marker
                key={`p-${idx}`}
                position={[lat, lon]}
                icon={idx === 0 ? firstIcon : vertexIcon}
                eventHandlers={{
                  click: () => {
                    if (idx === 0 && points.length >= 3) closeRing(points);
                  },
                }}
              />
            ))}
          </>
        )}
      </MapContainer>

      <form className="field-map-search" onSubmit={search}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("map.search")}
          aria-label={t("map.search")}
        />
        <button
          type="submit"
          className="tool search-submit"
          disabled={searching}
          aria-label={t("map.go")}
          title={t("map.go")}
        >
          {searching ? <span className="search-loading">…</span> : <SearchIcon />}
        </button>
      </form>

      <div className="field-map-tools" role="toolbar" aria-label={t("map.tools")}>
        {!drawing ? (
          <>
            <button className="tool" onClick={startDrawing} disabled={busy} title={t("map.draw")} aria-label={t("map.draw")}>
              <PencilIcon />
            </button>
            <button
              className="tool"
              onClick={() => onChange(null)}
              disabled={!ring}
              title={t("map.clear")}
              aria-label={t("map.clear")}
            >
              <TrashIcon />
            </button>
          </>
        ) : (
          <>
            <button className="tool ok" disabled={points.length < 3} onClick={() => closeRing(points)} title={t("map.close")} aria-label={t("map.close")}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z" fill="currentColor" /></svg>
            </button>
            <button className="tool" onClick={cancel} title={t("map.cancel")} aria-label={t("map.cancel")}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z" fill="currentColor" /></svg>
            </button>
          </>
        )}
        <span className="tool-area mono" aria-live="polite">
          {areaHa ? `${areaHa.toLocaleString(undefined, { maximumFractionDigits: 1 })} ha` : t("map.noArea")}
        </span>
        {areaHa > 0 && onContinue && (
          <button type="button" className="tool-continue" onClick={onContinue}>
            {t("map.continue")}
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
