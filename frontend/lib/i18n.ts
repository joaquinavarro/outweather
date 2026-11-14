export type Locale = "en-US" | "es-ES";

type Entry = { en: string; es: string };

const dict: Record<string, Entry> = {
  // header / shell
  "app.changeField": { en: "Change field", es: "Cambiar de campo" },
  "app.confidence": { en: "Confidence {value}", es: "Confianza {value}" },
  "app.nav": { en: "Sections", es: "Apartados" },
  "app.kansasPilot": { en: "Kansas pilot", es: "Piloto Kansas" },
  "app.farmLine": { en: "{name} · {county} County, KS · {area} ha", es: "{name} · condado de {county}, KS · {area} ha" },

  // tabs
  "tab.overview": { en: "Overview", es: "Resumen" },
  "tab.rotation": { en: "Rotation", es: "Rotación" },
  "tab.disease": { en: "Disease", es: "Sanidad" },
  "tab.irrigation": { en: "Irrigation", es: "Riego" },
  "tab.timeline": { en: "Time map", es: "Mapa temporal" },
  "tab.hazards": { en: "Hazards", es: "Riesgos" },
  "tab.map3d": { en: "3D field", es: "Parcela 3D" },

  // field map (drawing the parcel)
  "map.search": { en: "Search a place or lat, lon", es: "Busca un lugar o lat, lon" },
  "map.go": { en: "Search", es: "Buscar" },
  "map.area": { en: "Drawn area", es: "Superficie dibujada" },
  "map.draw": { en: "Draw the field", es: "Dibujar la parcela" },
  "map.redraw": { en: "Draw again", es: "Volver a dibujar" },
  "map.close": { en: "Close polygon", es: "Cerrar polígono" },
  "map.cancel": { en: "Cancel", es: "Cancelar" },
  "map.clear": { en: "Clear", es: "Borrar" },
  "map.edit": { en: "Move vertices", es: "Mover vértices" },
  "map.doneEdit": { en: "Done", es: "Listo" },
  "map.vertices": { en: "{n} vertices", es: "{n} vértices" },
  "map.clickHint": { en: " · click on the map to add points", es: " · haz clic en el mapa para añadir puntos" },
  "map.closeHint": {
    en: " · click the first point or press Close",
    es: " · pulsa el primer punto o Cerrar",
  },
  "map.presets": { en: "Demo fields:", es: "Fincas de ejemplo:" },
  "map.continue": { en: "Continue", es: "Continuar" },
  "map.tools": { en: "Field tools", es: "Herramientas de parcela" },
  "map.noArea": { en: "—", es: "—" },

  // rotation design
  "design.title": { en: "Design your rotation", es: "Diseña tu rotación" },
  "design.subtitle": {
    en: "Field of {area} ha. Choose what you plant and how you water it.",
    es: "Parcela de {area} ha. Elige qué plantas y cómo la riegas.",
  },
  "design.back": { en: "Back to the map", es: "Volver al mapa" },
  "design.currentCrop": { en: "Crop you have now", es: "Cultivo actual" },
  "design.noneCrop": { en: "None — I have nothing planted", es: "Ninguno — no tengo nada plantado" },
  "design.water": { en: "Water", es: "Agua" },
  "design.crops": { en: "Crops you want to plant", es: "Cultivos que quieres plantar" },
  "design.none": { en: "None selected yet — tap a crop below.", es: "Ninguno aún: elige un cultivo abajo." },
  "design.proposed": { en: "Proposed for your area", es: "Propuestos para tu zona" },
  "design.recommended": { en: "recommended", es: "recomendado" },
  "design.demoLocked": {
    en: "Demo fields keep their preloaded water and crop settings.",
    es: "Las fincas de ejemplo mantienen su riego y cultivo precargados.",
  },

  // landing: the map is the field selector
  "field.title": { en: "Draw your field", es: "Dibuja tu parcela" },
  "field.help": {
    en: "Draw the boundary on the map. OutWeather fetches NASA POWER climate and USDA soil for exactly that area.",
    es: "Dibuja el contorno en el mapa. OutWeather descarga el clima de NASA POWER y el suelo del USDA para esa zona exacta.",
  },
  "field.name": { en: "Field name", es: "Nombre de la parcela" },
  "field.water": { en: "Water", es: "Agua" },
  "field.irrigated": { en: "Irrigated", es: "Regadío" },
  "field.rainfed": { en: "Rainfed", es: "Secano" },
  "field.currentCrop": { en: "Current crop", es: "Cultivo actual" },
  "field.analyze": { en: "Analyse this field", es: "Analizar esta parcela" },
  "field.analyzeDemo": { en: "Analyse demo field", es: "Analizar finca de ejemplo" },
  "field.needsInternet": { en: "A drawn field needs internet (POWER + SSURGO, ~20 s)", es: "Una parcela dibujada requiere internet (POWER + SSURGO, ~20 s)" },
  "field.demoFast": { en: "Demo fields use preloaded real data and work offline", es: "Las fincas de ejemplo usan datos reales precargados y funcionan sin red" },
  "field.empty": { en: "No polygon yet", es: "Sin polígono todavía" },

  // 3D view
  "v3.title": { en: "The field in 3D", es: "La parcela en 3D" },
  "v3.area": { en: "{value} ha", es: "{value} ha" },
  "v3.year": { en: "Rotation year", es: "Año de la rotación" },
  "v3.draped": { en: "Draped on terrain", es: "Sobre el relieve" },
  "v3.extruded": { en: "Extruded", es: "Volumen 3D" },
  "v3.dark": { en: "Dark map", es: "Mapa oscuro" },
  "v3.satellite": { en: "Satellite", es: "Satélite" },
  "v3.terrainOn": { en: "Relief on", es: "Relieve sí" },
  "v3.terrainOff": { en: "Relief off", es: "Relieve no" },
  "v3.orbit": { en: "Orbit 360°", es: "Órbita 360°" },
  "v3.stopOrbit": { en: "Stop orbit", es: "Parar órbita" },
  "v3.center": { en: "Centre", es: "Centrar" },
  "v3.height": { en: "Height {value} m", es: "Altura {value} m" },
  "v3.terrainNote": {
    en: "Real elevation from open DEM tiles (×{x}). The colour is the crop of the selected year.",
    es: "Relieve real de teselas DEM abiertas (×{x}). El color es el cultivo del año elegido.",
  },
  "v3.noTerrainNote": {
    en: "Flat map. The colour is the crop of the selected year.",
    es: "Mapa plano. El color es el cultivo del año elegido.",
  },

  // landing
  "landing.title1": { en: "A farmer can choose what to plant.", es: "Un agricultor puede elegir qué sembrar." },
  "landing.title2": { en: "Not how much it will rain.", es: "No cuánto va a llover." },
  "landing.lede": {
    en: "OutWeather tests your rotation against the droughts of the past and several possible futures, using NASA climate data, USDA soils and satellite moisture. It does not predict the future. It helps you prepare for several of them.",
    es: "OutWeather prueba tu rotación contra las sequías del pasado y varios futuros posibles, con datos climáticos de la NASA, suelos del USDA y humedad satelital. No predice el futuro: te ayuda a prepararte para varios.",
  },
  "landing.loadingFields": { en: "Loading demo fields…", es: "Cargando fincas de ejemplo…" },
  "landing.run": { en: "Run the simulation", es: "Ejecutar la simulación" },
  "landing.demoNote": {
    en: "Real NASA POWER + SSURGO data · synthetic satellite fixtures for the demo",
    es: "Datos reales de NASA POWER y SSURGO · capas satelitales sintéticas en la demo",
  },
  "landing.scaleNote": {
    en: "Climate is represented at county scale (≈50 km); the field enters through its boundary and through 30 m imagery where available.",
    es: "El clima se representa a escala comarcal (≈50 km); la parcela entra por su polígono y por imágenes de 30 m cuando existen.",
  },
  "custom.title": { en: "Or use your own field", es: "O usa tu propia parcela" },
  "custom.needsInternet": { en: "needs internet", es: "requiere internet" },
  "custom.name": { en: "Field name", es: "Nombre de la parcela" },
  "custom.lat": { en: "Latitude", es: "Latitud" },
  "custom.lon": { en: "Longitude", es: "Longitud" },
  "custom.area": { en: "Area (ha)", es: "Superficie (ha)" },
  "custom.water": { en: "Water", es: "Agua" },
  "custom.irrigated": { en: "Irrigated", es: "Regadío" },
  "custom.rainfed": { en: "Rainfed", es: "Secano" },
  "custom.currentCrop": { en: "Current crop", es: "Cultivo actual" },
  "custom.build": { en: "Build this field", es: "Crear esta parcela" },
  "custom.help": {
    en: "We fetch NASA POWER 1991–2024 and the SSURGO soil for your coordinates (10–25 s), then run the same simulation. Works in Kansas, Nebraska, Oklahoma and Colorado.",
    es: "Descargamos NASA POWER 1991–2024 y el suelo SSURGO de tus coordenadas (10–25 s) y ejecutamos la misma simulación. Funciona en Kansas, Nebraska, Oklahoma y Colorado.",
  },

  // loading
  "loading.title": { en: "Running the simulation", es: "Ejecutando la simulación" },
  "loading.step1": { en: "Reading NASA POWER and USDA SSURGO…", es: "Leyendo NASA POWER y SSURGO del USDA…" },
  "loading.step1custom": {
    en: "Fetching NASA POWER (34 years) and USDA SSURGO for your coordinates… this takes 10–25 s",
    es: "Descargando NASA POWER (34 años) y SSURGO de tus coordenadas… tarda 10–25 s",
  },
  "loading.step2": { en: "Building the agro-climatic context…", es: "Construyendo el contexto agroclimático…" },
  "loading.step3": {
    en: "Evaluating rotations against 8 climate scenarios…",
    es: "Evaluando rotaciones contra 8 escenarios climáticos…",
  },
  "loading.step4": {
    en: "Estimating disease, irrigation and hazard risk…",
    es: "Estimando riesgo de enfermedades, riego y catástrofes…",
  },
  "loading.note": {
    en: "Context comes from 34 years of NASA POWER, USDA SSURGO soils and pre-loaded satellite fixtures. The rotation search evaluates 1,000 climate members per scenario.",
    es: "El contexto viene de 34 años de NASA POWER, suelos SSURGO del USDA y capas satelitales precargadas. La búsqueda de rotaciones evalúa 1.000 miembros climáticos por escenario.",
  },
  "loading.retry": { en: "Back to fields", es: "Volver a las parcelas" },

  // overview
  "ov.title": { en: "Your field at a glance", es: "Tu parcela de un vistazo" },
  "ov.aiTitle": { en: "Intelligent analysis", es: "Análisis inteligente" },
  "ov.aiSummary": {
    en: "With a resilience score of {score}/100 and an estimated {failure}% chance of a difficult season, this field shows how its current rotation may respond to changing conditions. Consider these indicators alongside the local soil and climate context when planning your next steps.",
    es: "Con una resiliencia de {score}/100 y una probabilidad estimada del {failure}% de tener una campaña desfavorable, estos indicadores ofrecen una primera lectura de cómo podría responder la parcela ante condiciones cambiantes. Valóralos junto con el contexto local del suelo y del clima al planificar los próximos pasos.",
  },
  "ov.farmDetails": { en: "Farm details", es: "Detalles de la finca" },
  "ov.irs": { en: "Resilience index", es: "Índice de resiliencia" },
  "ov.irsNote": {
    en: "Composite index built for OutWeather. Not a scientific standard.",
    es: "Índice compuesto creado para OutWeather. No es un estándar científico.",
  },
  "ov.production": { en: "Relative production", es: "Producción relativa" },
  "ov.vsCurrent": { en: "{value}% vs current", es: "{value}% frente a la actual" },
  "ov.pp": { en: "{value} pp vs current", es: "{value} pp frente a la actual" },
  "ov.failure": { en: "Chance of a bad season", es: "Probabilidad de campaña mala" },
  "ov.recovery": { en: "Recovery {value} yr", es: "Recuperación {value} años" },
  "ov.threeDry": { en: "3 dry years in a row {value}%", es: "3 años secos seguidos {value}%" },
  "ov.irsDelta": { en: "{value} resilience vs current", es: "{value} de resiliencia frente a la actual" },
  "ov.before": { en: "before", es: "antes" },
  "ov.recoveryShort": { en: "Recovery", es: "Recuperación" },
  "ov.threeDryShort": { en: "3 dry years in a row", es: "3 años secos seguidos" },
  "ov.current": { en: "Current conditions", es: "Condiciones actuales" },
  "ov.rainfall": { en: "Rainfall p10–p90", es: "Lluvia p10–p90" },
  "ov.droughtDays": { en: "Drought days", es: "Días de sequía" },
  "ov.soil": { en: "Soil", es: "Suelo" },
  "ov.aridity": { en: "Aridity index", es: "Índice de aridez" },
  "ov.group": { en: "group {value}", es: "grupo {value}" },
  "ov.median": { en: "{value} mm/yr median", es: "{value} mm/año mediana" },
  "unit.index": { en: "index", es: "índice" },
  "unit.days": { en: "days", es: "días" },
  "unit.yr": { en: "yr", es: "años" },
  "spei.near normal": { en: "near normal", es: "cerca de lo normal" },
  "spei.moderate drought": { en: "moderate drought", es: "sequía moderada" },
  "spei.severe drought": { en: "severe drought", es: "sequía severa" },
  "spei.extreme drought": { en: "extreme drought", es: "sequía extrema" },
  "spei.abnormally dry": { en: "abnormally dry", es: "anormalmente seco" },
  "spei.moderately wet": { en: "moderately wet", es: "moderadamente húmedo" },
  "spei.very wet": { en: "very wet", es: "muy húmedo" },
  "spei.extremely wet": { en: "extremely wet", es: "extremadamente húmedo" },
  "spei.unknown": { en: "unknown", es: "desconocido" },
  "ov.why": { en: "Why this rotation", es: "Por qué esta rotación" },
  "ov.openRotation": { en: "Open rotation", es: "Abrir rotación" },
  "ov.breakdown": { en: "Index breakdown", es: "Desglose del índice" },

  "irs.water": { en: "Water", es: "Agua" },
  "irs.stability": { en: "Stability", es: "Estabilidad" },
  "irs.soil": { en: "Soil", es: "Suelo" },
  "irs.diversity": { en: "Diversity", es: "Diversidad" },
  "irs.health": { en: "Health", es: "Sanidad" },
  "irs.hazard": { en: "Hazard", es: "Riesgo" },
  "irs.highly_resilient": { en: "Highly resilient", es: "Muy resiliente" },
  "irs.resilient": { en: "Resilient", es: "Resiliente" },
  "irs.vulnerable": { en: "Vulnerable", es: "Vulnerable" },
  "irs.highly_vulnerable": { en: "Highly vulnerable", es: "Muy vulnerable" },
  "irs.critical": { en: "Critical", es: "Crítico" },
  "irs.desc.highly_resilient": {
    en: "Holds up across most of the futures tested.",
    es: "Resiste bien en la mayoría de los futuros evaluados.",
  },
  "irs.desc.resilient": {
    en: "Holds up in most scenarios; water or diversity are the weak points.",
    es: "Resiste en la mayoría de escenarios; flojea en agua o diversidad.",
  },
  "irs.desc.vulnerable": {
    en: "Works in normal years; loses production in bad ones.",
    es: "Funciona en años normales; pierde producción en los malos.",
  },
  "irs.desc.highly_vulnerable": {
    en: "High chance of failure under drought or heat.",
    es: "Alta probabilidad de fallo con sequía o calor.",
  },
  "irs.desc.critical": {
    en: "This system is not sustainable under the scenarios tested.",
    es: "Este sistema no es sostenible en los escenarios evaluados.",
  },

  // rotation
  "rot.title": { en: "Proposed rotation · {n} seasons", es: "Rotación propuesta · {n} campañas" },
  "rot.across": { en: "Across scenarios", es: "En los escenarios" },
  "rot.scenNote": {
    en: "S0 historical · S1 severe · S2 three dry years · S6/S7 2050s RCP",
    es: "S0 histórico · S1 sequía severa · S2 tres años secos · S6/S7 RCP de 2050",
  },
  "rot.vs": { en: "Proposed vs current", es: "Propuesta frente a actual" },
  "rot.metric": { en: "Metric", es: "Métrica" },
  "rot.proposed": { en: "Proposed", es: "Propuesta" },
  "rot.current": { en: "Current", es: "Actual" },
  "rot.prodIndex": { en: "Production index", es: "Índice de producción" },
  "rot.p10": { en: "p10 index", es: "Índice p10" },
  "rot.p90": { en: "p90 index", es: "Índice p90" },
  "rot.cv": { en: "Variation (CV)", es: "Variación (CV)" },
  "rot.badChance": { en: "Bad season chance", es: "Probabilidad de campaña mala" },
  "rot.recovery": { en: "Recovery after worst year", es: "Recuperación tras el peor año" },
  "rot.legumes": { en: "Legume seasons", es: "Campañas con leguminosa" },
  "rot.nutrients": { en: "Nutrient balance", es: "Balance de nutrientes" },
  "rot.nRemoval": { en: "N removal", es: "Extracción de N" },
  "rot.nFix": { en: "N fixation credit", es: "Crédito de fijación de N" },
  "rot.nApplied": { en: "N applied (declared)", es: "N aportado (declarado)" },
  "rot.nBalance": { en: "N balance", es: "Balance de N" },
  "rot.pBalance": { en: "P₂O₅ balance", es: "Balance de P₂O₅" },
  "rot.kBalance": { en: "K₂O balance", es: "Balance de K₂O" },
  "rot.removalOnly": {
    en: "Removal only — add your applied N to see the full balance.",
    es: "Solo extracción: añade el N aportado para ver el balance completo.",
  },
  "rot.why": { en: "Why", es: "Por qué" },
  "rot.editHint": {
    en: "Click a season to change its crop — the metrics recalculate in a second.",
    es: "Haz clic en una campaña para cambiar el cultivo: las métricas se recalculan en un segundo.",
  },
  "rot.saving": { en: "Recalculating…", es: "Recalculando…" },
  "rot.edited": { en: "Edited manually", es: "Editada a mano" },
  "rot.reset": { en: "Restore optimised", es: "Restaurar optimizada" },
  "rot.warnings": { en: "Constraint warnings", es: "Avisos de restricciones" },
  "rot.editFailed": { en: "Could not recalculate", es: "No se pudo recalcular" },
  "rot.exportPdf": { en: "Export PDF", es: "Exportar PDF" },
  "rot.exportCsv": { en: "Export CSV", es: "Exportar CSV" },
  "rot.exporting": { en: "Preparing…", es: "Preparando…" },
  "rot.exportFailed": { en: "Export failed", es: "Error al exportar" },
  "rot.evaluated": { en: "{n} crops evaluated", es: "{n} cultivos evaluados" },
  "rot.caveat": {
    en: "Simulated results, not predictions. Potential yields come from a regional table in the demo; GAEZ v4 supplies them in production. A technical adviser should review any change.",
    es: "Resultados simulados, no predicciones. En la demo los rendimientos potenciales vienen de una tabla regional; en producción los aporta GAEZ v4. Cualquier cambio debería revisarlo un técnico.",
  },

  // findings
  "finding.WATER_GAP_COVERED": {
    en: "The proposed rotation cuts seasonal irrigation demand by {pct}% versus the current one.",
    es: "La rotación propuesta reduce la demanda estacional de riego un {pct}% frente a la actual.",
  },
  "finding.LEGUME_BREAK": {
    en: "Adds {count} legume season(s) to the rotation, breaking the cereal disease cycle.",
    es: "Añade {count} campaña(s) con leguminosa, rompiendo el ciclo de enfermedades del cereal.",
  },
  "finding.FAMILY_BREAK": {
    en: "No two consecutive seasons share a plant family.",
    es: "Ninguna campaña consecutiva repite familia botánica.",
  },
  "finding.PRODUCTION_SHIFT": {
    en: "Relative production changes by {pct}% versus the current rotation.",
    es: "La producción relativa cambia un {pct}% frente a la rotación actual.",
  },
  "finding.NUTRIENT_DEFICIT": {
    en: "Nitrogen removal exceeds declared inputs plus fixation by {deficit} kg N/ha.",
    es: "La extracción de nitrógeno supera los aportes declarados más la fijación en {deficit} kg N/ha.",
  },
  "finding.CARBON_GAIN": {
    en: "The surrounding landscape is a net carbon sink over the reference period.",
    es: "El entorno es un sumidero neto de carbono en el periodo de referencia.",
  },
  "finding.DROUGHT_SENSITIVITY": {
    en: "Under a three-year drought the proposed rotation holds an index of {proposed} versus {current} today.",
    es: "Con tres años secos, la rotación propuesta mantiene un índice de {proposed} frente a {current} actual.",
  },

  // caveats
  "caveat.SOIL_REGIONAL": {
    en: "Soil from a regional survey or default profile; local variability is not represented.",
    es: "Suelo de un estudio regional o perfil por defecto; no se representa la variabilidad local.",
  },
  "caveat.SYNTHETIC_SATELLITES": {
    en: "Satellite layers are synthetic fixtures (SMAP soil moisture, MODIS NDVI/LST/NPP, GLDAS runoff, GAEZ multipliers). Climate and soil are real.",
    es: "Las capas satelitales son sintéticas (humedad SMAP, NDVI/LST/NPP de MODIS, escorrentía GLDAS, multiplicadores GAEZ). El clima y el suelo son reales.",
  },
  "caveat.SHORT_SERIES": {
    en: "Short climate series: percentiles are fragile.",
    es: "Serie climática corta: los percentiles son frágiles.",
  },
  "caveat.PRECIP_MIXED": {
    en: "Monthly precipitation comes from GPM IMERG (real); daily extremes (Rx1day, dry spells) still come from POWER.",
    es: "La precipitación mensual viene de GPM IMERG (real); los extremos diarios (Rx1day, rachas secas) siguen viniendo de POWER.",
  },
  "caveat.NOT_A_DIAGNOSIS": { en: "Climate-based risk estimate. Not a diagnosis.", es: "Estimación de riesgo climático. No es un diagnóstico." },
  "caveat.LEAF_WETNESS_PROXY": {
    en: "Leaf wetness is estimated from daily data (no hourly POWER in the catalog).",
    es: "El mojado foliar se estima con datos diarios (no hay POWER horario en el catálogo).",
  },
  "caveat.THRESHOLDS_PRELIMINARY": {
    en: "Thresholds are preliminary pending agronomist validation.",
    es: "Los umbrales son preliminares, pendientes de validación agronómica.",
  },
  "caveat.HAIL_WILDFIRE_NO_DATA": {
    en: "Hail and wildfire have no supporting dataset in the project catalog: protocol only.",
    es: "El granizo y el incendio no tienen dataset de apoyo en el catálogo: solo protocolo.",
  },
  "caveat.RETURN_PERIOD_CAP": {
    en: "Return periods are capped at 50 years with 24 years of record.",
    es: "Los periodos de retorno se limitan a 50 años con 24 años de registro.",
  },

  // disease
  "dis.title": { en: "Disease risk", es: "Riesgo de enfermedades" },
  "dis.none": {
    en: "No crops selected yet. Choose your current crop and the crops you want to plant in the Design step to see their disease risk.",
    es: "Aún no hay cultivos seleccionados. Elige tu cultivo actual y los que quieres plantar en el paso de Diseño para ver su riesgo de enfermedades.",
  },
  "dis.badge": { en: "Climate-based estimate · not a diagnosis", es: "Estimación climática · no es un diagnóstico" },
  "dis.disease": { en: "Disease", es: "Enfermedad" },
  "dis.pathogen": { en: "Pathogen", es: "Patógeno" },
  "dis.risk": { en: "Risk", es: "Riesgo" },
  "dis.level": { en: "Level", es: "Nivel" },
  "dis.action": { en: "What to do", es: "Qué hacer" },
  "dis.low": { en: "low", es: "bajo" },
  "dis.medium": { en: "medium", es: "medio" },
  "dis.high": { en: "high", es: "alto" },
  "dis.very high": { en: "very high", es: "muy alto" },

  // irrigation
  "irr.title": { en: "Recommended system", es: "Sistema recomendado" },
  "irr.flow": { en: "Design flow", es: "Caudal de diseño" },
  "irr.efficiency": { en: "Efficiency", es: "Eficiencia" },
  "irr.zones": { en: "Zones", es: "Zonas" },
  "irr.supply": {
    en: "Supply available {supply} L/s · season volume {volume} m³{limit}",
    es: "Caudal disponible {supply} L/s · volumen de campaña {volume} m³{limit}",
  },
  "irr.limit": { en: " of {limit} m³ allowed", es: " de {limit} m³ permitidos" },
  "irr.overRight": {
    en: "The season demand exceeds the declared water right. Reduce the irrigated area or the demand of the rotation.",
    es: "La demanda de la campaña supera el derecho de agua declarado. Reduce la superficie regada o la demanda de la rotación.",
  },
  "irr.rainfed": {
    en: "No irrigation water declared. This is a dryland plan: capture rainfall, keep residue, rotate to lower-demand crops.",
    es: "No hay agua de riego declarada. Este es un plan de secano: captar lluvia, mantener rastrojo y rotar a cultivos de menor demanda.",
  },
  "irr.zonesTitle": { en: "Zones", es: "Zonas" },
  "irr.schedule": { en: "Season schedule", es: "Calendario de la campaña" },
  "irr.peak": { en: "Peak {value} mm in month {month}", es: "Pico de {value} mm en el mes {month}" },
  "irr.month": { en: "Month", es: "Mes" },
  "irr.etc": { en: "ETc (mm)", es: "ETc (mm)" },
  "irr.nir": { en: "NIR (mm)", es: "NIR (mm)" },
  "irr.materials": { en: "Materials", es: "Materiales" },

  // timeline
  "tl.title": { en: "Time map", es: "Mapa temporal" },
  "tl.ndvi": { en: "NDVI", es: "NDVI" },
  "tl.truecolor": { en: "True color", es: "Color real" },
  "tl.lst": { en: "Surface temp", es: "Temp. superficial" },
  "tl.attribution": {
    en: "Imagery: NASA GIBS / {note} · {date}",
    es: "Imagen: NASA GIBS / {note} · {date}",
  },
  "tl.offline": {
    en: "imagery unavailable offline, showing the modelled parcel",
    es: "imagen no disponible sin red; se muestra la parcela modelada",
  },
  "tl.outline": { en: "Outline: your field", es: "Contorno: tu parcela" },
  "tl.series": { en: "{name} series", es: "Serie de {name}" },
  "tl.selected": { en: "Selected month", es: "Mes seleccionado" },
  "tl.mean": {
    en: "mean {mean} · min {min} · max {max} {unit}",
    es: "media {mean} · mín {min} · máx {max} {unit}",
  },
  "tl.modelled": {
    en: "Modelled zonal series for the field ({n} months).",
    es: "Serie zonal modelada para la parcela ({n} meses).",
  },
  "tl.nightTemp": { en: "Night surface temperature", es: "Temperatura superficial nocturna" },

  // hazards
  "hz.title": { en: "Hazards for this field", es: "Riesgos de esta parcela" },
  "hz.current": { en: "SPEI-3 {spei} · {days} drought days", es: "SPEI-3 {spei} · {days} días de sequía" },
  "hz.protocolOnly": { en: "protocol only", es: "solo protocolo" },
  "hz.perYear": { en: "{value}%/yr", es: "{value}%/año" },
  "hz.returnPeriod": { en: "Return period {value} yr", es: "Periodo de retorno {value} años" },
  "hz.viewProtocol": { en: "View protocol", es: "Ver protocolo" },
  "hz.hideProtocol": { en: "Hide protocol", es: "Ocultar protocolo" },
  "hz.before": { en: "before", es: "antes" },
  "hz.during": { en: "during", es: "durante" },
  "hz.after": { en: "after", es: "después" },
  "hz.if": { en: "if {trigger}", es: "si {trigger}" },
  "hz.workWindows": { en: "Field work windows", es: "Ventanas de labor" },
  "hz.workNote": {
    en: "Days suitable for machinery, derived from rainfall and soil moisture",
    es: "Días aptos para maquinaria, a partir de lluvia y humedad del suelo",
  },
  "hz.windowCount": {
    en: "{n} windows this year (≥ 3 consecutive days).",
    es: "{n} ventanas este año (≥ 3 días consecutivos).",
  },
  "hz.noWindows": { en: "No suitable windows in the last year.", es: "Sin ventanas aptas en el último año." },
  "hz.day": { en: "day {from}–{to} · {days}d", es: "día {from}–{to} · {days}d" },

  // footer
  "footer.dataBy": { en: "Data provided by NASA", es: "Datos proporcionados por la NASA" },
  "footer.university": { en: "Universidad de Alicante", es: "Universidad de Alicante" },
  "footer.disclaimer": {
    en: "OutWeather is a simulation tool. It is not affiliated with, or endorsed by, NASA, USDA or the University of Alicante. Data are used under their respective open licenses. Results are not agronomic advice.",
    es: "OutWeather es una herramienta de simulación. No está afiliada ni respaldada por la NASA, el USDA ni la Universidad de Alicante. Los datos se usan bajo sus licencias abiertas. Los resultados no son asesoramiento agronómico.",
  },

  // errors
  "error.generic": { en: "Something went wrong.", es: "Algo ha salido mal." },
};

export function makeT(locale: Locale) {
  return (key: string, vars?: Record<string, unknown>): string => {
    const entry = dict[key];
    let text = entry ? (locale === "es-ES" ? entry.es : entry.en) : key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        text = text.split(`{${k}}`).join(String(v));
      }
    }
    return text;
  };
}

export function findingText(locale: Locale, finding: any): string {
  const t = makeT(locale);
  const key = `finding.${finding.code}`;
  const params = finding.params || {};
  if (dict[key]) return t(key, params);
  return finding.text || finding.code;
}

export function caveatText(locale: Locale, code: string | undefined, fallback: string): string {
  if (!code) return fallback;
  const key = `caveat.${code}`;
  if (!dict[key]) return fallback;
  return makeT(locale)(key);
}

export function levelText(locale: Locale, level: string): string {
  return makeT(locale)(`dis.${level}`);
}
