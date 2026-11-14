"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { api, downloadFile, reportUrl, waitForJob } from "@/lib/api";
import { caveatText, findingText, levelText, makeT, type Locale } from "@/lib/i18n";
import { ringAreaHa, type Ring } from "@/lib/geo";
import { ParcelMap, ScenarioBars, ScoreGauge } from "@/components/charts";

const FieldMap = dynamic(() => import("@/components/FieldMap"), {
  ssr: false,
  loading: () => <div className="map-loading" aria-busy="true" />,
});
const Field3D = dynamic(() => import("@/components/Field3D"), {
  ssr: false,
  loading: () => <div className="map-loading" aria-busy="true" />,
});

type Phase = "map" | "design" | "loading" | "ready";
type Tab = "overview" | "rotation" | "irrigation" | "disease" | "hazards";

const TABS: { id: Tab; key: string }[] = [
  { id: "overview", key: "tab.overview" },
  { id: "rotation", key: "tab.rotation" },
  { id: "irrigation", key: "tab.irrigation" },
  { id: "disease", key: "tab.disease" },
  { id: "hazards", key: "tab.hazards" },
];

const FAMILY_COLORS: Record<string, string> = {
  poaceae: "#667f57",
  fabaceae: "#957449",
  asteraceae: "#81674f",
  brassicaceae: "#73835f",
};

const riskClass = (level: string) =>
  level === "very high" ? "risk-pill risk-very high" : `risk-pill risk-${level}`;

export default function Page() {
  const [locale, setLocale] = useState<Locale>("en-US");
  const [phase, setPhase] = useState<Phase>("map");
  const [demos, setDemos] = useState<any[]>([]);
  const [crops, setCrops] = useState<any[]>([]);
  const [regionCrops, setRegionCrops] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [farm, setFarm] = useState<any>(null);
  const [ctx, setCtx] = useState<any>(null);
  const [rot, setRot] = useState<any>(null);
  const [disease, setDisease] = useState<any>(null);
  const [hazards, setHazards] = useState<any>(null);
  const [irrigation, setIrrigation] = useState<any>(null);
  const [tab, setTab] = useState<Tab>("overview");

  // map / design state
  const [ring, setRing] = useState<Ring | null>(null);
  const [demoId, setDemoId] = useState<string | null>(null);
  const [mustInclude, setMustInclude] = useState<string[]>([]);
  const [currentCrop, setCurrentCrop] = useState("corn");
  const [water, setWater] = useState<"rainfed" | "irrigated">("rainfed");

  const t = useMemo(() => makeT(locale), [locale]);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("rs_locale") : null;
    if (stored === "es-ES" || stored === "en-US") setLocale(stored as Locale);
    api
      .region()
      .then((r) => {
        setDemos(r.data.demo_farms || []);
        setRegionCrops(r.data.crops || []);
      })
      .catch((e) => setError(String(e.message || e)));
    api
      .catalogCrops()
      .then((r) => setCrops(r.data || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") document.documentElement.lang = locale;
    if (typeof window !== "undefined") window.localStorage.setItem("rs_locale", locale);
  }, [locale]);

  const generate = useCallback(
    async (payload: any) => {
      setPhase("loading");
      setError(null);
      try {
        const created = await api.createFarm(payload);
        const farmId = created.data.farm_id;
        setFarm({ ...created.data, farm_id: farmId });

        const context = await api.context(farmId);
        setCtx(context.data);

        // Disease risk covers every crop the farmer selected for the farm: the
        // current crop(s) plus the preferred crops picked in the design panel.
        const selectedCrops = Array.from(
          new Set(
            [
              ...((context.data.farm?.current_crops || []).map((c: any) => c.crop_id)),
              ...((payload.must_include || []) as string[]),
            ].filter(Boolean),
          ),
        );

        const [rotJob, dz, hz, ir] = await Promise.all([
          api.optimize(farmId, {}),
          api.diseases(farmId, selectedCrops),
          api.hazards(farmId),
          api.irrigation(farmId, {}),
        ]);
        const rotResult = await waitForJob(rotJob.data.job_id);
        setRot(rotResult.result);
        setDisease(dz.data);
        setHazards(hz.data);
        setIrrigation(ir.data);

        setPhase("ready");
        setTab("overview");
      } catch (e: any) {
        setError(String(e.message || e));
        setPhase("design");
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [locale],
  );

  const resetRotation = useCallback(async () => {
    if (!farm?.farm_id) return;
    try {
      const job = await api.optimize(farm.farm_id, {});
      const result = await waitForJob(job.data.job_id, () => {});
      setRot(result.result);
    } catch (e: any) {
      setError(String(e.message || e));
    }
  }, [farm]);

  const proceedFromMap = (r: Ring | null, id: string | null) => {
    setRing(r);
    setDemoId(id);
    const demo = demos.find((d) => d.id === id);
    if (demo) {
      setWater(demo.irrigation?.status === "irrigated" ? "irrigated" : "rainfed");
      setCurrentCrop(demo.current_crops?.[0]?.crop_id || "corn");
      setMustInclude([]);
    } else {
      setWater("rainfed");
      setCurrentCrop("corn");
      setMustInclude([]);
    }
    setPhase("design");
  };

  const runDesign = () => {
    const demo = demos.find((d) => d.id === demoId);
    const payload = demo
      ? { demo_farm_id: demo.id, objective: "balanced", must_include: mustInclude }
      : {
          boundary: ring,
          irrigation_status: water,
          irrigation_system: water === "irrigated" ? "center_pivot" : "none",
          current_crop_id: currentCrop || "",
          must_include: mustInclude,
          objective: "balanced",
        };
    generate(payload);
  };

  const LocaleSwitch = (
    <div className="locale-switch-fixed" role="group" aria-label="Language">
      {(["en-US", "es-ES"] as Locale[]).map((id) => (
        <button
          key={id}
          className={`tab ${locale === id ? "active" : ""}`}
          onClick={() => setLocale(id)}
          aria-pressed={locale === id}
        >
          {id === "en-US" ? "EN" : "ES"}
        </button>
      ))}
    </div>
  );

  if (phase === "map") {
    return (
      <MapLanding
        ring={ring}
        onRingChange={setRing}
        onContinue={() => proceedFromMap(ring, demoId)}
        t={t}
        locale={locale}
        localeSwitch={LocaleSwitch}
      />
    );
  }

  if (phase === "design") {
    return (
      <DesignView
        demo={demos.find((d) => d.id === demoId)}
        ring={ring}
        crops={crops}
        regionCrops={regionCrops}
        mustInclude={mustInclude}
        setMustInclude={setMustInclude}
        currentCrop={currentCrop}
        setCurrentCrop={setCurrentCrop}
        water={water}
        setWater={setWater}
        onAnalyse={runDesign}
        onBack={() => setPhase("map")}
        error={error}
        t={t}
        locale={locale}
        localeSwitch={LocaleSwitch}
      />
    );
  }

  if (phase === "loading") {
    return (
      <div className="spinner-screen" role="status" aria-label={t("loading.title")}>
        {LocaleSwitch}
        <div className="rs-spinner" />
      </div>
    );
  }

  return (
    <div className="shell">
      {LocaleSwitch}
      <header className="topbar app-navbar">
        <Brand farm={farm} t={t} />
        <nav className="tabs app-tabs" aria-label={t("app.nav")}>
          {TABS.map((item) => (
            <button
              key={item.id}
              className={`tab ${tab === item.id ? "active" : ""}`}
              onClick={() => setTab(item.id)}
              aria-current={tab === item.id ? "page" : undefined}
            >
              {t(item.key)}
            </button>
          ))}
        </nav>
        <div className="app-nav-actions">
          <span className={`badge ${ctx?.confidence >= 70 ? "ok" : "warn"}`}>
            {t("app.confidence", { value: ctx?.confidence ?? "—" })}
          </span>
          <button className="btn" onClick={() => setPhase("map")}>
            {t("app.changeField")}
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        {tab === "overview" && (
          <Overview ctx={ctx} rot={rot} farm={farm} onGo={setTab} t={t} locale={locale} />
        )}
        {tab === "rotation" && (
          <RotationView
            rot={rot}
            ctx={ctx}
            t={t}
            locale={locale}
            farmId={farm?.farm_id}
            onRotChange={setRot}
            onReset={resetRotation}
          />
        )}
        {tab === "irrigation" && <IrrigationView data={irrigation} t={t} locale={locale} />}
        {tab === "disease" && <DiseaseView data={disease} t={t} locale={locale} />}
        {tab === "hazards" && <HazardsView data={hazards} t={t} locale={locale} />}
      </main>

      <Footer t={t} />
    </div>
  );
}

function Brand({ farm, t, showSubtitle = true }: { farm?: any; t: any; showSubtitle?: boolean }) {
  return (
    <a href="/" className="brand" style={{ textDecoration: "none", color: "inherit" }}>
      <div className="brand-mark">
        <Image src="/outweather-mark.png" width={52} height={52} alt="" className="brand-logo" priority />
      </div>
      <div>
        <div className="brand-name">OutWeather</div>
        {showSubtitle && (
          <div className="brand-sub">
            {farm
              ? t("app.farmLine", { name: farm.name, county: farm.county, area: farm.area_ha })
              : t("app.kansasPilot")}
          </div>
        )}
      </div>
    </a>
  );
}

// ---------------------------------------------------------------------------
// Phase 1 — map (draw the field)
// ---------------------------------------------------------------------------

function MapLanding({
  ring,
  onRingChange,
  onContinue,
  t,
  locale,
  localeSwitch,
}: {
  ring: Ring | null;
  onRingChange: (r: Ring | null) => void;
  onContinue: () => void;
  t: any;
  locale: Locale;
  localeSwitch: any;
}) {
  return (
    <div className="maplanding">
      <header className="maplanding-head">
        <Brand t={t} showSubtitle={false} />
        {localeSwitch}
      </header>

      <div className="maplanding-map">
        <FieldMap ring={ring} onChange={onRingChange} locale={locale} t={t} onContinue={onContinue} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase 2 — rotation design
// ---------------------------------------------------------------------------

function DesignView({
  demo,
  ring,
  crops,
  regionCrops,
  mustInclude,
  setMustInclude,
  currentCrop,
  setCurrentCrop,
  water,
  setWater,
  onAnalyse,
  onBack,
  error,
  t,
  locale,
  localeSwitch,
}: {
  demo: any;
  ring: Ring | null;
  crops: any[];
  regionCrops: string[];
  mustInclude: string[];
  setMustInclude: (ids: string[]) => void;
  currentCrop: string;
  setCurrentCrop: (id: string) => void;
  water: "rainfed" | "irrigated";
  setWater: (w: "rainfed" | "irrigated") => void;
  onAnalyse: () => void;
  onBack: () => void;
  error: string | null;
  t: any;
  locale: Locale;
  localeSwitch: any;
}) {
  const areaHa = ringAreaHa(ring);
  const cropName = (id: string) => {
    const c = crops.find((c) => c.crop_id === id);
    return c ? (locale === "es-ES" ? c.name_es || c.name_en : c.name_en) : id;
  };
  const recommended = regionCrops.length ? regionCrops : crops.map((c) => c.crop_id);
  const familyOf = (id: string) => crops.find((c) => c.crop_id === id)?.family;

  const toggle = (id: string) => {
    if (mustInclude.includes(id)) setMustInclude(mustInclude.filter((c) => c !== id));
    else setMustInclude([...mustInclude, id]);
  };

  return (
    <div className="landing">
      {localeSwitch}
      <div className="landing-inner">
        <div className="hero" style={{ marginTop: 18 }}>
          <h1>{t("design.title")}</h1>
          <p>{t("design.subtitle", { area: areaHa ? areaHa.toFixed(1) : "—" })}</p>
        </div>

        <div className="grid g2">
          <div className="card">
            <div className="card-head">
              <h2>{t("design.currentCrop")}</h2>
            </div>
            <select
              value={currentCrop}
              onChange={(e) => setCurrentCrop(e.target.value)}
              disabled={!!demo}
              style={{ width: "100%", padding: "10px 12px", background: "var(--rs-bg)", color: "var(--rs-text)", border: "1px solid var(--rs-border)", borderRadius: 8, fontSize: 14 }}
            >
              <option value="">{t("design.noneCrop")}</option>
              {recommended.map((id) => (
                <option key={id} value={id}>
                  {cropName(id)}
                </option>
              ))}
            </select>

            <div className="card-head" style={{ marginTop: 22 }}>
              <h2>{t("design.water")}</h2>
            </div>
            <div className="seg" role="radiogroup" aria-label={t("design.water")}>
              <button
                className={`seg-item ${water === "rainfed" ? "active" : ""}`}
                onClick={() => setWater("rainfed")}
                disabled={!!demo}
              >
                {t("field.rainfed")}
              </button>
              <button
                className={`seg-item ${water === "irrigated" ? "active" : ""}`}
                onClick={() => setWater("irrigated")}
                disabled={!!demo}
              >
                {t("field.irrigated")}
              </button>
            </div>
            {demo && <div className="tiny muted" style={{ marginTop: 8 }}>{t("design.demoLocked")}</div>}
          </div>

          <div className="card">
            <div className="card-head">
              <h2>{t("design.crops")}</h2>
              <span className="badge">{mustInclude.length}</span>
            </div>
            <div className="crop-chips">
              {mustInclude.length === 0 && (
                <span className="tiny muted">{t("design.none")}</span>
              )}
              {mustInclude.map((id) => (
                <button
                  key={id}
                  className="crop-chip active"
                  onClick={() => toggle(id)}
                  style={{ borderColor: FAMILY_COLORS[familyOf(id)] || "var(--rs-accent)" }}
                >
                  {cropName(id)}
                </button>
              ))}
            </div>

            <div className="card-head" style={{ marginTop: 22 }}>
              <h2>{t("design.proposed")}</h2>
            </div>
            <div className="crop-chips">
              {recommended.map((id) => (
                <button
                  key={id}
                  className={`crop-chip ${mustInclude.includes(id) ? "active" : ""}`}
                  onClick={() => toggle(id)}
                  style={{ borderColor: FAMILY_COLORS[familyOf(id)] || "var(--rs-border)" }}
                >
                  {cropName(id)}
                  <span className="tiny">{t("design.recommended")}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && <div className="caveat" style={{ marginTop: 18 }}>{error}</div>}

        <div className="design-actions">
          <button className="btn design-back" onClick={onBack}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M19 12H5m0 0 7-7m-7 7 7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {t("design.back")}
          </button>
          <button className="btn primary" onClick={onAnalyse}>
            {t("field.analyze")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Phase 3 — loading (spinner only)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Phase 4 — overview (synthesised, with the 3D parcel embedded)
// ---------------------------------------------------------------------------

function Overview({
  ctx,
  rot,
  farm,
  onGo,
  t,
  locale,
}: {
  ctx: any;
  rot: any;
  farm: any;
  onGo: (tab: Tab) => void;
  t: any;
  locale: Locale;
}) {
  if (!ctx || !rot) return null;
  const irs = rot.irs;
  const m = rot.metrics;
  const b = rot.baseline?.metrics || {};
  const irsDelta = rot.delta?.irs_delta ?? 0;
  const code = irs.label_code || "vulnerable";
  const years = Object.entries(ctx.drought?.spei12_by_year || {})
    .map(([y, v]: any) => ({ year: +y, spei: +v }))
    .sort((a, b) => a.year - b.year);

  return (
    <>
      <div className="grid overview-hero">
        <div className="card">
          <div className="card-head">
            <h2>{t("ov.title")}</h2>
          </div>
          <div style={{ display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
            <ScoreGauge value={irs.value} label={t(`irs.${code}`)} />
            <div style={{ flex: 1, minWidth: 220 }}>
              <div className="kpi-label">{t(`irs.desc.${code}`)}</div>
              <div className={`badge ${irsDelta >= 0 ? "ok" : "warn"}`} style={{ margin: "10px 0 14px" }}>
                {irsDelta >= 0 ? "▲" : "▼"} {t("ov.irsDelta", { value: irsDelta >= 0 ? `+${irsDelta}` : irsDelta })}
              </div>
              <div className="grid g2" style={{ gap: 12 }}>
                <Compare label={t("ov.production")} now={m.production_index} before={b.production_index} better="up" fmt={(v: number) => `${v}`} unit={t("unit.index")} t={t} />
                <Compare label={t("ov.failure")} now={m.p_fail} before={b.p_fail} better="down" fmt={pctFmt} unit="%" t={t} />
                <Compare label={t("ov.recoveryShort")} now={m.recovery_years} before={b.recovery_years} better="down" fmt={(v: number) => `${v}`} unit={t("unit.yr")} t={t} />
                <Compare label={t("ov.threeDryShort")} now={m.p_drought3} before={b.p_drought3} better="down" fmt={pctFmt} unit="%" t={t} />
              </div>
            </div>
          </div>
          <section className="smart-analysis" aria-labelledby="smart-analysis-title">
            <h3 id="smart-analysis-title">{t("ov.aiTitle")}</h3>
            <p>
              {t("ov.aiSummary", {
                score: Math.round(irs.value),
                failure: Math.round(m.p_fail * 100),
              })}
            </p>
          </section>
        </div>

        <div className="card">
          <div className="card-head">
            <h2>{t("v3.title")}</h2>
            <span className="badge">{t("v3.area", { value: farm?.area_ha ?? "—" })}</span>
          </div>
          <Field3D
            boundary={(farm?.boundary as Ring) || null}
            years={years}
            locale={locale}
            t={t}
          />
        </div>
      </div>

      <section className="card details">
        <h2 className="details-title">{t("ov.farmDetails")}</h2>
        <div className="grid g2" style={{ marginTop: 14 }}>
          <div>
            <div className="card-head">
              <h3>{t("ov.current")}</h3>
            </div>
            <div className="grid g3">
              <Kpi label={t("ov.rainfall")} value={`${ctx.climate.annual_precip.p10}–${ctx.climate.annual_precip.p90}`} unit="mm" />
              <Kpi label={t("ov.droughtDays")} value={ctx.drought.add_days} unit={t("unit.days")} />
              <Kpi label={t("ov.soil")} value={ctx.soil.texture_class} unit={t("ov.group", { value: ctx.soil.hydgrp })} />
            </div>
            <div style={{ marginTop: 18 }}>
              <div className="card-head">
                <h3>{t("ov.why")}</h3>
              </div>
              {rot.findings.map((f: any) => (
                <div key={f.code} className={`finding ${f.severity === "positive" ? "pos" : "warn"}`}>
                  <div className="finding-icon">{f.severity === "positive" ? "✓" : "▲"}</div>
                  <div>{findingText(locale, f)}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="card-head">
              <h3>{t("ov.breakdown")}</h3>
            </div>
            {Object.entries(irs.components).map(([k, v]: any) => (
              <div className="bar-row" key={k}>
                <div className="bar-label">
                  {t(`irs.${k}`)} <span className="tiny">({irs.weights[k]})</span>
                </div>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${v}%`,
                      background: v >= 60 ? "var(--rs-accent)" : v >= 40 ? "var(--rs-risk-2)" : "var(--rs-risk-3)",
                    }}
                  />
                </div>
                <div className="bar-value">{Math.round(v)}</div>
              </div>
            ))}
            <button className="btn" style={{ marginTop: 14 }} onClick={() => onGo("rotation")}>
              {t("ov.openRotation")}
            </button>
          </div>
        </div>

        {ctx.caveats?.length > 0 && (
          <div className="caveat" style={{ marginTop: 16 }}>
            {ctx.caveats.map((c: string, i: number) => (
              <div key={i}>· {caveatText(locale, (ctx.caveat_codes || [])[i], c)}</div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function Kpi({ label, value, unit }: { label: string; value: any; unit?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value mono" style={{ fontSize: 19 }}>
        {value}
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
    </div>
  );
}

const pctFmt = (v: number) => (v < 0.01 ? "<1" : String(Math.round(v * 100)));

function Compare({
  label,
  now,
  before,
  better,
  fmt,
  unit,
  t,
}: {
  label: string;
  now: number;
  before: number;
  better: "up" | "down";
  fmt: (v: number) => string;
  unit?: string;
  t: any;
}) {
  const improved = better === "up" ? now >= before : now <= before;
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value mono" style={{ fontSize: 19 }}>
        {fmt(now)}
        {unit && <span className="kpi-unit">{unit}</span>}
        <span className={`compare-arrow ${improved ? "delta-up" : "delta-down"}`}>
          {improved ? "▲" : "▼"}
        </span>
      </div>
      <div className="tiny muted">
        {t("ov.before")} {fmt(before)}
        {unit ? ` ${unit}` : ""}
      </div>
    </div>
  );
}

function RotationView({
  rot,
  ctx,
  t,
  locale,
  farmId,
  onRotChange,
  onReset,
}: {
  rot: any;
  ctx: any;
  t: any;
  locale: Locale;
  farmId?: string;
  onRotChange?: (next: any) => void;
  onReset?: () => void;
}) {
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [editK, setEditK] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const applyEdit = async (k: number, cropId: string) => {
    if (!farmId || !rot?.rotation_id || !onRotChange) return;
    const ids = rot.sequence.map((s: any) => s.crop_id);
    if (ids[k - 1] === cropId) {
      setEditK(null);
      return;
    }
    ids[k - 1] = cropId;
    setSaving(true);
    setEditError(null);
    try {
      const updated = await api.updateRotation(farmId, rot.rotation_id, ids);
      onRotChange(updated.data);
      setEditK(null);
    } catch (e: any) {
      setEditError(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const doExport = async (kind: "pdf" | "csv") => {
    if (!farmId || !rot?.rotation_id) return;
    setExporting(kind);
    setExportError(null);
    try {
      const name = `outweather-${(ctx?.farm?.name || "field").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${kind}`;
      await downloadFile(reportUrl(farmId, kind, rot.rotation_id, locale), name);
    } catch (e: any) {
      setExportError(String(e.message || e));
    } finally {
      setExporting(null);
    }
  };

  if (!rot) return null;
  const m = rot.metrics;
  const b = rot.baseline.metrics;
  const legumeCount = rot.sequence.filter((s: any) => s.is_legume).length;
  const baseLegumes = rot.baseline.sequence.filter((s: any) => s.is_legume).length;
  const maxNir = Math.max(1, ...rot.sequence.map((s: any) => s.nir_mm || 0));
  const cropName = (s: any) =>
    locale === "es-ES" && s.crop_name_es ? s.crop_name_es : s.crop_name;

  const rows = [
    [t("rot.prodIndex"), m.production_index, b.production_index],
    [t("rot.p10"), m.p10_index, b.p10_index],
    [t("rot.p90"), m.p90_index, b.p90_index],
    [t("rot.cv"), m.cv, b.cv],
    [t("rot.badChance"), `${Math.round(m.p_fail * 100)}%`, `${Math.round(b.p_fail * 100)}%`],
    [t("rot.recovery"), `${m.recovery_years}`, `${b.recovery_years}`],
    [t("rot.legumes"), legumeCount, baseLegumes],
  ];

  return (
    <>
      <div className="card">
        <div className="card-head">
          <h2>{t("rot.title", { n: rot.sequence.length })}</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="badge ok">
              IRS {rot.irs.value} ({rot.delta.irs_delta >= 0 ? "+" : ""}
              {rot.delta.irs_delta})
            </span>
            {rot.edited && <span className="badge warn">{t("rot.edited")}</span>}
            <button className="btn" onClick={() => doExport("pdf")} disabled={!!exporting}>
              {exporting === "pdf" ? t("rot.exporting") : t("rot.exportPdf")}
            </button>
            <button className="btn" onClick={() => doExport("csv")} disabled={!!exporting}>
              {exporting === "csv" ? t("rot.exporting") : t("rot.exportCsv")}
            </button>
            {rot.edited && onReset && (
              <button className="btn" onClick={onReset}>
                {t("rot.reset")}
              </button>
            )}
          </div>
        </div>
        {exportError && (
          <div className="caveat" style={{ marginBottom: 10 }}>
            {t("rot.exportFailed")}: {exportError}
          </div>
        )}
        {editError && (
          <div className="caveat" style={{ marginBottom: 10 }}>
            {t("rot.editFailed")}: {editError}
          </div>
        )}
        <div className="tiny muted" style={{ marginBottom: 10 }}>
          {saving ? t("rot.saving") : t("rot.editHint")}
        </div>
        {rot.warnings?.length > 0 && (
          <div className="caveat" style={{ marginBottom: 10 }}>
            <b>{t("rot.warnings")}</b>
            {rot.warnings.map((w: any, i: number) => (
              <div key={i}>
                · {locale === "es-ES" ? w.message_es || w.message : w.message}
              </div>
            ))}
          </div>
        )}
        <div>
          {rot.sequence.map((s: any) => (
            <div
              className="timeline-row"
              key={s.k}
              style={{ marginBottom: 6, cursor: "pointer" }}
              onClick={() => !saving && setEditK(editK === s.k ? null : s.k)}
            >
              <div className="small muted mono">{s.season}</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <div
                  className="season-pill"
                  style={{
                    background: FAMILY_COLORS[s.family] || "#7bc96f",
                    width: `${Math.max(18, ((s.nir_mm || 0) / maxNir) * 82)}%`,
                  }}
                  title={`${cropName(s)} · ${s.nir_mm ?? "—"} mm · ${s.yield_t_ha ?? "—"} t/ha`}
                >
                  {cropName(s)}
                </div>
                {editK === s.k ? (
                  <select
                    autoFocus
                    defaultValue={s.crop_id}
                    disabled={saving}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => applyEdit(s.k, e.target.value)}
                    onBlur={() => setEditK(null)}
                    aria-label={`${t("rot.metric")} ${s.season}`}
                    style={{
                      background: "var(--rs-bg)",
                      color: "var(--rs-text)",
                      border: "1px solid var(--rs-accent)",
                      borderRadius: 8,
                      padding: "4px 8px",
                      fontSize: 12,
                    }}
                  >
                    {(ctx?.crops || []).map((c: any) => (
                      <option key={c.crop_id} value={c.crop_id}>
                        {locale === "es-ES" ? c.name_es : c.name_en}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="tiny muted">
                    {s.nir_mm ? `${Math.round(s.nir_mm)} mm` : ""} · {s.family}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid g2">
        <div className="card">
          <div className="card-head">
            <h2>{t("rot.across")}</h2>
            <span className="tiny muted">{t("rot.scenNote")}</span>
          </div>
          <ScenarioBars scenarios={rot.scenarios} />
        </div>

        <div className="card">
          <div className="card-head">
            <h2>{t("rot.vs")}</h2>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("rot.metric")}</th>
                <th className="num">{t("rot.proposed")}</th>
                <th className="num">{t("rot.current")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, a, bb]: any) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td className="num">{a}</td>
                  <td className="num muted">{bb}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid g2">
        <div className="card">
          <div className="card-head">
            <h2>{t("rot.nutrients")}</h2>
            <span className="badge">{rot.nutrients.n_status}</span>
          </div>
          <table className="data">
            <tbody>
              <tr><td>{t("rot.nRemoval")}</td><td className="num">{rot.nutrients.n_removal_kg_ha} kg/ha</td></tr>
              <tr><td>{t("rot.nFix")}</td><td className="num">{rot.nutrients.n_fixation_kg_ha} kg/ha</td></tr>
              <tr><td>{t("rot.nApplied")}</td><td className="num">{rot.nutrients.n_input_kg_ha} kg/ha</td></tr>
              <tr><td><b>{t("rot.nBalance")}</b></td><td className="num"><b>{rot.nutrients.n_balance_kg_ha} kg/ha</b></td></tr>
              <tr><td>{t("rot.pBalance")}</td><td className="num">{rot.nutrients.p2o5_balance_kg_ha} kg/ha</td></tr>
              <tr><td>{t("rot.kBalance")}</td><td className="num">{rot.nutrients.k2o_balance_kg_ha} kg/ha</td></tr>
            </tbody>
          </table>
          {!rot.nutrients.inputs_declared && (
            <div className="tiny muted" style={{ marginTop: 8 }}>{t("rot.removalOnly")}</div>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h2>{t("rot.why")}</h2>
            <span className="tiny muted">{t("rot.evaluated", { n: rot.candidates })}</span>
          </div>
          {rot.findings.map((f: any) => (
            <div key={f.code} className={`finding ${f.severity === "positive" ? "pos" : "warn"}`}>
              <div className="finding-icon">{f.severity === "positive" ? "✓" : "▲"}</div>
              <div>
                <div>{findingText(locale, f)}</div>
                <div className="tiny muted mono">
                  {Object.entries(f.evidence || {}).map(([k, v]: any) => `${k}: ${v}`).join(" · ")}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function DiseaseView({ data, t, locale }: { data: any; t: any; locale: Locale }) {
  if (!data) return null;
  const diseaseName = (d: any) => (locale === "es-ES" ? d.name_es || d.name : d.name_en || d.name);
  const actions = (d: any) => (locale === "es-ES" ? d.actions_es || d.actions : d.actions);

  return (
    <>
      <div className="card">
        <div className="card-head">
          <h2>{t("dis.title")}</h2>
        </div>
        {(!data.crops || data.crops.length === 0) && (
          <div className="small muted" style={{ padding: "4px 0" }}>{t("dis.none")}</div>
        )}
        {data.crops?.map((crop: any) => (
          <div key={crop.crop_id} style={{ marginBottom: 22 }}>
            <h3 style={{ marginBottom: 8 }}>{locale === "es-ES" ? crop.crop_name : crop.crop_name_en}</h3>
            <table className="data">
              <thead>
                <tr>
                  <th>{t("dis.disease")}</th>
                  <th>{t("dis.pathogen")}</th>
                  <th className="num">{t("dis.risk")}</th>
                  <th>{t("dis.level")}</th>
                  <th>{t("dis.action")}</th>
                </tr>
              </thead>
              <tbody>
                {crop.diseases.map((d: any) => (
                  <tr key={d.disease_id}>
                    <td>{diseaseName(d)}</td>
                    <td className="muted small"><i>{d.pathogen}</i></td>
                    <td className="num">{d.risk_index}</td>
                    <td>
                      <span className={riskClass(d.level)}>{levelText(locale, d.level)}</span>
                    </td>
                    <td className="small muted">{(actions(d)?.cultural || [])[0]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
      <div className="caveat" style={{ marginTop: 16 }}>
        {data.caveats?.map((c: string, i: number) => (
          <div key={i}>· {caveatText(locale, (data.caveat_codes || [])[i], c)}</div>
        ))}
      </div>
    </>
  );
}

function IrrigationView({ data, t, locale }: { data: any; t: any; locale: Locale }) {
  if (!data) return null;
  const rainfed = data.system?.id === "rainfed";
  const schedule = data.schedule;
  const sysName = (s: any) => (locale === "es-ES" ? s?.name_es || s?.name : s?.name);
  const caveats = (locale === "es-ES" ? data.caveats_es : data.caveats) || data.caveats || [];

  return (
    <>
      <div className="grid g2">
        <div className="card">
          <div className="card-head">
            <h2>{t("irr.title")}</h2>
            <span className="badge ok">{data.system?.score ?? "—"}/100</span>
          </div>
          <div className="kpi-value">{sysName(data.system)}</div>
          {!rainfed && (
            <>
              <div className="grid g3" style={{ marginTop: 14 }}>
                <Kpi label={t("irr.flow")} value={data.design_flow_l_s} unit="L/s" />
                <Kpi label={t("irr.efficiency")} value={data.system?.efficiency} unit="η" />
                <Kpi label={t("irr.zones")} value={data.zones?.length ?? 0} unit="" />
              </div>
              <div className="small muted" style={{ marginTop: 12 }}>
                {t("irr.supply", {
                  supply: data.supply_flow_l_s,
                  volume: data.volume_m3?.toLocaleString?.() ?? data.volume_m3,
                  limit: data.annual_limit_m3
                    ? t("irr.limit", { limit: data.annual_limit_m3.toLocaleString() })
                    : "",
                })}
              </div>
              {data.within_water_right === false && (
                <div className="caveat" style={{ marginTop: 10 }}>{t("irr.overRight")}</div>
              )}
            </>
          )}
          {rainfed && <div className="small muted" style={{ marginTop: 10 }}>{t("irr.rainfed")}</div>}
          <div style={{ marginTop: 14 }}>
            {(data.alternatives || []).map((a: any) => (
              <div className="bar-row" key={a.id}>
                <div className="bar-label">{sysName(a)}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${a.score}%`, background: "#3d6b4a" }} />
                </div>
                <div className="bar-value">{a.score}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h2>{t("irr.zonesTitle")}</h2>
            <span className="tiny muted">{data.parcel?.area_ha} ha</span>
          </div>
          <ParcelMap boundary={data.parcel?.boundary || []} zones={data.zones} />
        </div>
      </div>

      {schedule && (
        <div className="card">
          <div className="card-head">
            <h2>{t("irr.schedule")}</h2>
            <span className="badge">{t("irr.peak", { value: schedule.peak_nir_mm, month: schedule.peak_month })}</span>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("irr.month")}</th>
                {schedule.etc_mm.map((_: any, i: number) => (
                  <th className="num" key={i}>{i + 1}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t("irr.etc")}</td>
                {schedule.etc_mm.map((v: any, i: number) => <td className="num" key={i}>{v}</td>)}
              </tr>
              <tr>
                <td>{t("irr.nir")}</td>
                {schedule.nir_mm.map((v: any, i: number) => <td className="num" key={i}>{v}</td>)}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {data.materials && (
        <div className="card">
          <div className="card-head"><h2>{t("irr.materials")}</h2></div>
          <table className="data">
            <tbody>
              {data.materials.map((m: any) => (
                <tr key={m.item}>
                  <td>{locale === "es-ES" ? m.item_es || m.item : m.item}</td>
                  <td className="num">{m.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="caveat">{caveats.join(" ")}</div>
    </>
  );
}

function HazardsView({ data, t, locale }: { data: any; t: any; locale: Locale }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!data) return null;

  const name = (h: any) => (locale === "es-ES" ? h.name_es || h.name : h.name);
  const playbook = (h: any) => (locale === "es-ES" ? h.playbook_es || h.playbook : h.playbook);

  return (
    <>
      <div className="card">
        <div className="card-head">
          <h2>{t("hz.title")}</h2>
          <span className="badge">
            {t("hz.current", { spei: data.current?.spei3, days: data.current?.add_days })}
          </span>
        </div>
        <div className="grid g2">
          {data.hazards.map((h: any) => (
            <div key={h.hazard} className="card" style={{ background: "var(--rs-surface-2)" }}>
              <div className="card-head">
                <h3>{name(h)}</h3>
                <span className={riskClass(h.calculable ? (h.p_annual >= 0.2 ? "high" : h.p_annual >= 0.1 ? "medium" : "low") : "low")}>
                  {h.calculable
                    ? t("hz.perYear", { value: Math.round((h.p_annual || 0) * 100) })
                    : t("hz.protocolOnly")}
                </span>
              </div>
              <div className="small muted">
                {h.calculable
                  ? [
                      h.return_period_years
                        ? t("hz.returnPeriod", { value: h.return_period_years })
                        : null,
                      locale === "es-ES" ? h.status_es || h.status : h.status,
                    ]
                      .filter(Boolean)
                      .join(" · ")
                  : locale === "es-ES"
                    ? h.source_es || h.source
                    : h.source}
              </div>
              <button
                className="btn"
                style={{ marginTop: 10 }}
                onClick={() => setOpen(open === h.hazard ? null : h.hazard)}
              >
                {open === h.hazard ? t("hz.hideProtocol") : t("hz.viewProtocol")}
              </button>
              {open === h.hazard && (
                <div style={{ marginTop: 12 }}>
                  {(["before", "during", "after"] as const).map((stage) => (
                    <div key={stage} style={{ marginBottom: 10 }}>
                      <div className="tiny muted" style={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
                        {t(`hz.${stage}`)}
                      </div>
                      {(playbook(h)?.[stage] || []).map((s: any, i: number) =>
                        typeof s === "string" ? (
                          <div key={i} className="small" style={{ marginTop: 4 }}>
                            {s}
                          </div>
                        ) : (
                          <div key={s.step ?? i} className="small" style={{ marginTop: 4 }}>
                            {s.step}. {s.action}
                            {s.trigger ? (
                              <span className="tiny muted mono"> · {t("hz.if", { trigger: s.trigger })}</span>
                            ) : null}
                          </div>
                        )
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>{t("hz.workWindows")}</h2>
          <span className="tiny muted">{t("hz.workNote")}</span>
        </div>
        <div className="small muted">
          {data.workability?.windows?.length
            ? t("hz.windowCount", { n: data.workability.windows.length })
            : t("hz.noWindows")}
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
          {(data.workability?.windows || []).slice(0, 12).map((w: any) => (
            <span key={`${w.start_doy}-${w.end_doy}`} className="badge">
              {t("hz.day", { from: w.start_doy, to: w.end_doy, days: w.days })}
            </span>
          ))}
        </div>
      </div>
    </>
  );
}

function Footer({ t }: { t: any }) {
  return (
    <footer className="brand-footer">
      <span className="logo-chip">NASA</span>
      <span>{t("footer.dataBy")}</span>
      <span className="logo-chip">UA</span>
      <span>{t("footer.university")}</span>
      <p className="disclaimer">{t("footer.disclaimer")}</p>
    </footer>
  );
}
