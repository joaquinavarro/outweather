"use client";

import React from "react";

export function ScoreGauge({ value, label, size = 132 }: { value: number; label: string; size?: number }) {
  const r = 54;
  const cx = 66;
  const cy = 66;
  const start = Math.PI * 0.75;
  const sweep = Math.PI * 1.5;
  const clamped = Math.max(0, Math.min(100, value));
  const end = start + (sweep * clamped) / 100;

  const arc = (from: number, to: number, stroke: string, width = 10) => {
    const x1 = cx + r * Math.cos(from);
    const y1 = cy + r * Math.sin(from);
    const x2 = cx + r * Math.cos(to);
    const y2 = cy + r * Math.sin(to);
    const large = to - from > Math.PI ? 1 : 0;
    return (
      <path
        d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`}
        stroke={stroke}
        strokeWidth={width}
        fill="none"
        strokeLinecap="round"
      />
    );
  };

  return (
    <svg width={size} height={size * 0.82} viewBox="0 0 132 108" role="img" aria-label={`Resilience index ${value} out of 100`}>
      {arc(start, start + sweep, "#385742", 10)}
      {arc(start, end, value >= 60 ? "var(--rs-accent)" : value >= 40 ? "var(--rs-risk-2)" : "var(--rs-risk-3)", 10)}
      <text x="66" y="62" textAnchor="middle" fill="var(--rs-text)" fontSize="26" fontWeight="650">
        {Math.round(value)}
      </text>
      <text x="66" y="79" textAnchor="middle" fill="var(--rs-muted)" fontSize="9">
        / 100
      </text>
      <text x="66" y="97" textAnchor="middle" fill="var(--rs-muted)" fontSize="9.5">
        {label}
      </text>
    </svg>
  );
}

export function ScenarioBars({ scenarios }: { scenarios: Record<string, any> }) {
  const order = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"];
  const rows = order.filter((k) => scenarios?.[k]).map((k) => ({ id: k, ...scenarios[k] }));
  if (!rows.length) return null;

  // dynamic domain so the differences between scenarios are visible
  const lows = rows.map((r) => r.p10_index ?? 0);
  const highs = rows.map((r) => r.p90_index ?? 100);
  const domainLo = Math.max(0, Math.min(...lows) - 4);
  const domainHi = Math.min(100, Math.max(...highs) + 2);
  const span = Math.max(1, domainHi - domainLo);
  const pos = (v: number) => ((v - domainLo) / span) * 100;

  return (
    <div>
      {rows.map((r) => {
        const lo = pos(r.p10_index ?? domainLo);
        const hi = pos(r.p90_index ?? domainHi);
        const mid = pos(r.p50_index ?? 50);
        const value = r.p50_index ?? 50;
        const color = value >= 60 ? "var(--rs-accent)" : value >= 40 ? "var(--rs-risk-2)" : "var(--rs-risk-3)";
        return (
          <div className="bar-row" key={r.id}>
            <div className="bar-label" title={`${r.id} · CV ${r.cv} · fail ${Math.round((r.p_fail ?? 0) * 100)}%`}>
              {r.id}
            </div>
            <div className="bar-track" style={{ position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  left: `${lo}%`,
                  width: `${Math.max(1, hi - lo)}%`,
                  top: 0,
                  bottom: 0,
                  background: color,
                  opacity: 0.35,
                  borderRadius: 999,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `${mid}%`,
                  top: -2,
                  width: 3,
                  height: 13,
                  background: color,
                  borderRadius: 2,
                }}
              />
            </div>
            <div className="bar-value">{Math.round(value)}</div>
          </div>
        );
      })}
      <div className="tiny muted" style={{ marginTop: 6 }}>
        Bars show p10–p90, the tick is p50. Axis {Math.round(domainLo)}–{Math.round(domainHi)}.
        Index is relative yield × 100.
      </div>
    </div>
  );
}

export function BarRow({
  label,
  value,
  max = 100,
  color = "var(--rs-accent)",
  suffix,
}: {
  label: string;
  value: number;
  max?: number;
  color?: string;
  suffix?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="bar-row">
      <div className="bar-label">{label}</div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="bar-value">{suffix ?? Math.round(value)}</div>
    </div>
  );
}

export function Sparkline({
  points,
  height = 64,
  color = "var(--rs-accent)",
  marker,
}: {
  points: { t: string; mean: number }[];
  height?: number;
  color?: string;
  marker?: number;
}) {
  if (!points?.length) return null;
  const values = points.map((p) => p.mean);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 600;
  const h = height;
  const step = w / Math.max(1, points.length - 1);
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${i * step} ${h - ((p.mean - min) / span) * (h - 8) - 4}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="fan" preserveAspectRatio="none" role="img" aria-label="Time series">
      <path d={d} fill="none" stroke={color} strokeWidth="1.8" />
      {marker !== undefined && points[marker] && (
        <circle
          cx={marker * step}
          cy={h - ((points[marker].mean - min) / span) * (h - 8) - 4}
          r="3.4"
          fill={color}
        />
      )}
    </svg>
  );
}

export function ParcelMap({
  boundary,
  zones,
  color = "var(--rs-accent)",
  value,
}: {
  boundary: number[][];
  zones?: any[];
  color?: string;
  value?: number | null;
}) {
  if (!boundary?.length) return null;
  const xs = boundary.map((p) => p[0]);
  const ys = boundary.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const pad = 0.15;
  const spanX = (maxX - minX) * (1 + pad * 2) || 1;
  const spanY = (maxY - minY) * (1 + pad * 2) || 1;
  const W = 520;
  const H = 320;
  const sx = (x: number) => ((x - minX + spanX * pad) / spanX) * W;
  const sy = (y: number) => H - ((y - minY + spanY * pad) / spanY) * H;

  const poly = boundary.map((p) => `${sx(p[0])},${sy(p[1])}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="zone-map" role="img" aria-label="Parcel map">
      <defs>
        <pattern id="grid" width="26" height="26" patternUnits="userSpaceOnUse">
          <path d="M 26 0 L 0 0 0 26" fill="none" stroke="#355340" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={W} height={H} fill="url(#grid)" />
      {zones?.map((z, i) => {
        const zx = z.boundary?.map((p: number[]) => `${sx(p[0])},${sy(p[1])}`).join(" ");
        if (!zx) return null;
        return (
          <polygon
            key={z.id || i}
            points={zx}
            fill={i % 2 === 0 ? "rgba(128,170,163,0.18)" : "rgba(159,187,141,0.16)"}
            stroke="#789274"
            strokeWidth="1"
          />
        );
      })}
      <polygon points={poly} fill={value != null ? `rgba(77,112,79,${0.15 + (value / 100) * 0.5})` : "rgba(77,112,79,0.16)"} stroke={color} strokeWidth="2" />
      {zones?.map((z, i) => {
        if (!z.boundary?.length) return null;
        const cx = z.boundary.reduce((a: number, p: number[]) => a + p[0], 0) / z.boundary.length;
        const cy = z.boundary.reduce((a: number, p: number[]) => a + p[1], 0) / z.boundary.length;
        return (
          <text key={`t${i}`} x={sx(cx)} y={sy(cy)} fill="var(--rs-muted)" fontSize="11" textAnchor="middle">
            {z.id}
          </text>
        );
      })}
    </svg>
  );
}
