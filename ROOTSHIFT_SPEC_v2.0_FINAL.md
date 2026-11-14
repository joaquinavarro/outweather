# ROOTSHIFT — Especificación final de implementación

**Versión:** 2.0 · **Estado:** FINAL — lista para implementar
**Sustituye a:** `ROOTSHIFT_ESPECIFICACION.md` v1.0 (borrador). Este archivo es la única fuente de verdad.
**Producto:** aplicación web de simulación de rotaciones agrícolas resilientes con datos NASA y USDA.
**Piloto:** Estados Unidos (Kansas). **UI:** inglés (en-US) por defecto, español (es-ES) soportado.

---

## 0. Cómo leer este documento

### 0.1 Etiquetas de trazabilidad

| Etiqueta | Significado |
|---|---|
| `[N]` | Requisito de las notas originales del equipo. No modificable sin el equipo. |
| `[D]` | Decisión cerrada por el equipo (respuestas D1–D20). **Vinculante.** |
| `[P]` | Propuesta técnica del especificador: fórmula, umbral, peso o default. Ajustable en configuración sin cambiar la arquitectura. |

### 0.2 Registro de decisiones cerradas

Las 20 decisiones del borrador están resueltas. Resumen ejecutivo; el detalle de lo que implica cada una está en §19.

| ID | Decisión | Resuelto como | Efecto en esta versión |
|---|---|---|---|
| D1 | Escala de análisis | **B — polígono** | La parcela es un polígono obligatorio; área, zonas de riego y zócalos se derivan de él |
| D2 | Datos de suelo | **B — NASA + suplemento** | Suplemento = **SSURGO + STATSGO2** (USDA-NRCS), no SoilGrids |
| D3 | Modelo de rendimiento | **B — FAO-33** | `Y = Ym·[1−Ky(1−ETa/ETm)]·f_heat·f_frost`; ETa de OpenET/MOD16 |
| D4 | Optimizador | **C — DP + Monte Carlo + búsqueda local** | §10.7.7 |
| D5 | Escenarios futuros | **B — sí, con futuros** | Fuente: **GAEZ v4 (RCP4.5 / RCP8.5, 2050s)**, no NEX-GDDP |
| D6 | Catálogo de cultivos | **Recomendación** | 9 cultivos + barbecho de Kansas (Anexo A) |
| D7 | Región piloto | **B — región concreta** | **Kansas, EE. UU.** (§3.4) |
| D8 | Origen de `Ym` | **B — estadísticas/GAEZ** | `Ym` = rendimiento alcanzable GAEZ; USDA NASS para validar |
| D9 | Módulo económico | **A — no** | Sin precios, sin margen, sin coste de materiales en € |
| D10 | Nivel de riego | **B — indicativo con números** | Caudal, zonas, calendario, materiales; sin proyecto ejecutivo |
| D11 | Enfermedades | **Catálogo + modelo + validación; sin diagnóstico por imagen** | §10.10 |
| D12 | Catástrofes | **Recomendación** | 6 calculables + granizo e incendio solo protocolo (sin FIRMS) |
| D13 | Arquitectura | **Recomendada** | Next.js + FastAPI + PostGIS, híbrido precomputado |
| D14 | Cuentas | **Sin cuenta** | Sesión anónima, 30 días, sin email |
| D15 | Explicaciones | **A — plantillas deterministas** | Sin LLM en runtime |
| D16 | Idioma | **en-US por defecto, internacional** | i18n `en-US` + `es-ES`; unidades métricas |
| D17 | Horizonte de rotación | **Recomendación + configurable** | 8 temporadas por defecto, rango 4–12 |
| D18 | Demo precargada | **Sí** | `DATA_MODE=demo` obligatorio |
| D19 | Marcas | **NASA + Universidad de Alicante visibles** | §14.7 |
| D20 | Métrica de éxito | **C — producción + fallo + recuperación** | `E[P]`, `P_fail`, `T_recovery` |

### 0.3 Cambios respecto a la v1.0

| Área | v1.0 | v2.0 |
|---|---|---|
| Región | España mediterránea | **Kansas, EE. UU.** |
| Suelo | SoilGrids (ISRIC) | **SSURGO + STATSGO2** (USDA-NRCS) |
| Precipitación | POWER | **IMERG** (diario + 30 min) |
| ET | FAO-56 (única vía) | **OpenET → MOD16A2GF → FAO-56** (cadena de precedencia) |
| Futuros | NEX-GDDP-CMIP6 (SSP) | **GAEZ v4** (RCP4.5 / RCP8.5, 2050s) |
| Salud del suelo | Proxies NDVI | **NEE de SPL4CMDL + NPP de MOD17** + RUSLE |
| Nutrientes | No existía | **Balance N-P-K** con Ag Data Commons |
| Economía | Coste de riego | **Ninguna** |
| Cuentas | Opcionales | **Ninguna** |
| Idioma de la UI | Español | **Inglés (en-US)**, español soportado |
| Atribución | Genérica | **Logos NASA + Universidad de Alicante** |

### 0.4 Idioma de este documento

El documento está redactado en español para el equipo. **Todo el copy de producto (§13) está en inglés**, que es el idioma por defecto de la interfaz. Cada cadena de UI lleva su clave i18n (`ui.f1.title`), de modo que la versión española sea una traducción, no una reescritura.

### 0.5 Convenciones

- Unidades SI + agronómicas: mm, °C, ha, kg/ha, m³, L/s. La UI puede mostrar acres y bushels solo como conversión de presentación; **el cálculo es siempre métrico**.
- Coordenadas WGS84 (EPSG:4326). Áreas en proyección métrica local (UTM 14N para Kansas).
- Fechas ISO-8601. Temporadas agrícolas: `2026` (año de cosecha) o `2026S`/`2026W` si hay doble cultivo.
- Código en inglés. Contenido de producto en inglés por defecto.

---

## 1. Resumen ejecutivo

**ROOTSHIFT** permite a un agricultor **probar sus decisiones de rotación contra varios futuros climáticos** antes de comprometer la cosecha. No pronostica el tiempo: simula escenarios con datos históricos y con las proyecciones de GAEZ, y muestra qué secuencia de cultivos mantiene la producción el mayor tiempo posible y falla menos.

| # | Funcionalidad `[N]` | Output `[N]` | Motor | Prioridad |
|---|---|---|---|---|
| F1 | Diseño de rotación resiliente | Panel del diseño sugerido + comparación | §10.7, §10.8, §10.9 | **P0** |
| F2 | Control de enfermedades | Panel de riesgo + recomendaciones | §10.10 | P1 |
| F3 | Diseño de riego sostenible | Sistema + mapa de zonas | §10.11 | P1 |
| F4 | Vista geográfica temporal | Mapa + deslizador año/mes | §13.6 | P2 |
| F5 | Actuación ante catástrofes | Panel de peligros + protocolos | §10.12 | **P0** |

**La historia en 3 minutos:** el usuario dibuja su parcela en Kansas → la app lee 25 años de lluvia IMERG, la humedad de raíz de SMAP, la ET real de OpenET y el suelo de SSURGO → propone una rotación distinta a la suya → un abanico de producción demuestra que, bajo la peor sequía registrada y bajo RCP8.5 en 2050, esa rotación produce más y falla menos → y tres frases explican *por qué*, cada una con su fuente.

**Arquitectura en una frase:** Next.js 15 + FastAPI + PostGIS + TiTiler, con los cálculos en funciones puras, los datos NASA/USDA precomputados por parcela y una capa de procedencia que acompaña a cada cifra (§8, §10.13).

---

## 2. Problema, visión y principios

### 2.1 Problema

El agricultor decide **qué sembrar** con información del pasado y del precio, pero su resultado depende de variables que no controla: lluvia, calor, heladas, agua subterránea. ROOTSHIFT ataca esa asimetría: convierte la decisión en un experimento reproducible contra varios futuros.

La rotación es la palanca que actúa simultáneamente sobre el agua, el suelo, el carbono y las enfermedades. Por eso es el núcleo del producto y no un módulo más.

### 2.2 Principios rectores (no negociables)

1. **No se predice, se simula.** `[N]` Nunca "lloverá X mm"; siempre "en 7 de cada 10 años la lluvia de abril superó 40 mm".
2. **Siempre varios futuros.** `[N]` Todo resultado es una distribución (p10/p50/p90), nunca un número único.
3. **Todo número tiene procedencia.** Producto, variable, resolución, periodo y fecha de descarga, visibles (§10.13).
4. **Honestidad de escala.** El clima es de comarca (0,5° para POWER, 0,1° para IMERG); la parcela entra por el polígono y por las capas de 30 m (HLS, NASADEM). Se declara en la UI (§7.5).
5. **El agricultor manda.** Puede editar la rotación propuesta; la app puntúa, no bloquea.
6. **Sin diagnóstico ni receta.** En enfermedades se estima riesgo y se sugiere manejo; no se prescribe producto ni dosis.
7. **Datos con jerarquía declarada.** Cada variable tiene una fuente primaria y una cadena de respaldo explícita (§7.4). Nunca se rellena un hueco con un valor inventado: se degrada la confianza.

### 2.3 Propuesta de valor

> *A farmer can choose what to plant this year. ROOTSHIFT lets them test that choice against the droughts of the past — and of several possible futures — before risking the crop.*

---

## 3. Alcance

### 3.1 Dentro del alcance

- Registro de **una finca** con **una o varias parcelas polígono** `[D1]`.
- Perfil agronómico: cultivos actuales, preferidos, excluidos; práctica de riego; recursos.
- Descarga y procesamiento de los 20 productos de §7 para la parcela.
- Indicadores históricos (1991–presente según producto).
- Simulación de escenarios históricos y de clima futuro GAEZ.
- Optimización y puntuación de rotaciones (F1), con balance N-P-K.
- Riesgo de enfermedades (F2), diseño de riego (F3), mapa temporal (F4), peligros y protocolos (F5).
- Exportación PDF/CSV por funcionalidad.

### 3.2 Fuera del alcance

- Pronóstico meteorológico operativo (1–15 días).
- Telemetría IoT, maquinaria, drones, sensores de campo.
- Contabilidad, precios, márgenes, cadena de suministro `[D9]`.
- Recomendación de materias activas, dosis o marcas de fitosanitarios `[D11]`.
- Diagnóstico de enfermedades por imagen `[D11]`.
- Gestión ganadera, piscicultura, silvicultura.
- Cuentas de usuario, email, contraseñas `[D14]`.
- App móvil nativa (solo web responsive).
- Tiempo real (actualización diaria/semanal, no por segundo).

### 3.3 Política de idioma y unidades `[D16]`

| Elemento | Regla |
|---|---|
| Idioma por defecto | `en-US` |
| Idiomas soportados | `en-US`, `es-ES` |
| Detección | `Accept-Language` y selector explícito en el header |
| Unidades de cálculo | Siempre métricas (ha, mm, °C, kg/ha) |
| Unidades de presentación | Métricas por defecto; conmutador a acres/bushels **solo visual** |
| Formatos numéricos | `en-US`: `1,234.5` · `es-ES`: `1.234,5` |
| Cadenas | Claves i18n obligatorias; prohibido texto duro en componentes |

### 3.4 Región piloto `[D7]`

**Kansas, Estados Unidos.** Tres contextos productivos para la demo:

| Demo | Condado (referencia) | Sistema | Por qué está en la demo |
|---|---|---|---|
| Farm A | Finney | Regadío, pivote central, maíz | Caso de agua limitada por acuífero |
| Farm B | Greeley | Secano, trigo–sorgo–barbecho | Caso de sequía estructural |
| Farm C | Republic | Secano, maíz–soja | Caso de rotación clásica y carbono |

Estos condados son **puntos de partida configurables**, no una afirmación sobre sus prácticas reales: la configuración vive en `config/regions/us_ks.yaml` y cambiarla no requiere tocar código.

**Regla de portabilidad:** ninguna parte del motor puede contener un condado, un cultivo o una enfermedad codificados a mano. Todo sale de `config/` y `data/catalog/`. Añadir otro estado de EE. UU. debe ser un archivo YAML.

---

## 4. Usuarios y recorridos

### 4.1 Perfiles

| Perfil | Necesidad | Uso |
|---|---|---|
| **Agricultor de secano** (primario) | Qué rotar para no perder la cosecha en año seco | Anual, antes de sembrar |
| **Agricultor de regadío** (primario) | Ajustar rotación y riego al agua disponible | Anual + mensual |
| **Agrónomo / cooperativa** (secundario) | Comparar alternativas y explicarlas | Repetido, varias parcelas |
| **Jurado / evaluador** | Entender el valor en 3 minutos | Sesión guiada con finca demo |

### 4.2 Onboarding (5 pasos, objetivo < 3 min)

1. **Location** — buscar municipio, colocar pin o **dibujar el polígono** (obligatorio). Se muestra la celda climática y el área calculada.
2. **What you grow** — cultivos actuales y superficie.
3. **What you want** — preferidos y excluidos (opcional).
4. **What you have** — agua, sistema de riego, maquinaria, insumos.
5. **Generate** — progreso por etapas reales.

### 4.3 Recorridos secundarios

- **Compare:** el usuario arrastra cultivos en la rotación propuesta y ve recalcularse las métricas en < 3 s.
- **Drill down:** desde una tarjeta de riesgo se abre la serie temporal y las reglas que dispararon la alerta.
- **Export:** PDF de una página por funcionalidad, con fuente y descargos.

---

## 5. Glosario y modelo de dominio

### 5.1 Glosario

| Término | Definición operativa |
|---|---|
| **Parcel** | Polígono con uso y rotación propios. Unidad de cálculo. |
| **Farm** | Unidad de gestión; agrupa parcelas y recursos. |
| **Climate cell** | Celda de la cuadrícula de POWER asociada al centroide. |
| **Season** | Ventana de cultivo. En Kansas, por defecto 1 por año (mar–nov). |
| **Rotation** | Secuencia ordenada de cultivos por temporada, horizonte N. |
| **Scenario** | Año o conjunto de años coherentes sobre el que se evalúa una rotación. |
| **ETa / ETm** | ET real / ET máxima del cultivo. Su ratio alimenta FAO-33. |
| **ADD** | *Agricultural Drought Days*: días con humedad de raíz bajo el percentil 20. |
| **NEE** | Intercambio neto de carbono del ecosistema (negativo = sumidero). |
| **RUSLE** | Ecuación universal de pérdida de suelo revisada. |
| **IRS** | Índice de Resiliencia ROOTSHIFT, 0–100. Índice propio, no estándar. |
| **Playbook** | Protocolo antes/durante/después de un peligro. |
| **Artifact** | Salida calculada y persistida con `model_version` y `params_hash`. |

### 5.2 Jerarquía de cálculo

```
              ┌──────────────────────────────────────────┐
              │  PARCEL CONTEXT (se calcula una vez)      │
              │  clima · lluvia · ET · suelo · humedad    │
              │  · carbono · vegetación · erosión         │
              └───────────────┬──────────────────────────┘
      ┌───────────┬───────────┼───────────┬────────────┐
      ▼           ▼           ▼           ▼            ▼
  F1 Rotation  F2 Disease  F3 Irrigation  F5 Hazards  F4 Timeline
      │           │           │           │            │
      └───────────┴─────┬─────┴───────────┘            │
                        ▼                              │
                IRS + Dashboard ◄──────────────────────┘
```

**Regla:** F2, F3, F4 y F5 **consumen** el contexto; no vuelven a descargar datos ni recalculan ET. `providers/` es la única puerta a internet.

---

## 6. Entradas del sistema

### 6.1 `FarmProfile` v2 (contrato vinculante)

```jsonc
{
  "name": "North 80",
  "region_id": "us_ks",                          // config/regions/*
  "location": { "lat": 38.05, "lon": -100.92, "elevation_m": 800 },
  "parcels": [                                   // [D1] polígono obligatorio
    {
      "name": "Field 1",
      "boundary": { "type": "Polygon", "coordinates": [[[-100.925,38.048],[-100.915,38.048],[-100.915,38.055],[-100.925,38.055],[-100.925,38.048]]] },
      "area_ha": 32.4
    }
  ],
  "current_crops": [
    { "parcel_index": 0, "crop_id": "corn", "season": "2025", "area_ha": 32.4 }
  ],
  "preferred_crops": ["soybean"],
  "excluded_crops": [],
  "production_system": "conventional",           // conventional | organic
  "irrigation": {
    "status": "irrigated",                       // rainfed | irrigated
    "system": "center_pivot",                    // none | center_pivot | sdi | furrow | micro
    "flow_l_s": 40,
    "annual_limit_m3": 180000,
    "energy": "grid",
    "hours_per_day": 20
  },
  "resources": {
    "machinery": ["tractor_200hp", "planter", "combine", "sprayer"],
    "labor": { "permanent": 2, "seasonal": 1 },
    "fertility": { "n_kg_ha": 180, "p2o5_kg_ha": 60, "k2o_kg_ha": 40 },  // opcional
    "cover_crop_seed": true,
    "storage_t": 500
  },
  "constraints": {
    "horizon_seasons": 8,                        // [D17] 4..12
    "must_include": [],
    "max_crops": 4
  },
  "preferences": {
    "objective": "balanced",                     // production | resilience | water | balanced
    "risk_tolerance": "medium",                  // low | medium | high
    "units": "metric"                            // metric | imperial (solo presentación)
  }
}
```

### 6.2 Validaciones (servidor, no solo UI)

| Regla | Error |
|---|---|
| ≥ 1 parcela con `boundary` válido, no auto-intersectante, área 0,1–10 000 ha | `INVALID_BOUNDARY` |
| Centroide en tierra y dentro de EE. UU. si `region_id` es US | `LOCATION_OUT_OF_REGION` |
| `crop_id` existe en el catálogo de la región | `UNKNOWN_CROP` |
| Σ `area_ha` de cultivos ≤ Σ área de parcelas × 1,02 | `AREA_OVERFLOW` |
| `preferred ∩ excluded = ∅` | `CONFLICTING_CROPS` |
| `horizon_seasons ∈ [4, 12]` | `INVALID_HORIZON` |
| `irrigation.status = irrigated` ⇒ `flow_l_s > 0` o `annual_limit_m3 > 0` | `MISSING_WATER_CAPACITY` |
| POWER con ≥ 15 años y IMERG con ≥ 15 años en la celda | `INSUFFICIENT_CLIMATE_DATA` |

### 6.3 Ubicación `[N]`

Tres modos, todos producen geometría:

1. **Buscar** municipio/dirección (Nominatim/OSM), colocar pin y dibujar.
2. **Mi ubicación** con permiso explícito.
3. **Importar** GeoJSON/KML o dibujar con MapLibre Draw.

**Privacidad:** las coordenadas se guardan con 3 decimales (≈110 m) porque no hay cuentas `[D14]`; el cálculo usa la geometría completa solo durante la sesión.

### 6.4 Cultivos `[N]`

| Campo | Origen `[N]` | Uso |
|---|---|---|
| `current_crops` | "los que tiene actualmente y desea optimizar" | **Baseline** obligatorio; se simula con el mismo motor |
| `recommended_crops` | "los que recomienda la app" | **Salida**, no entrada: catálogo + filtro de viabilidad (§10.7.4) |
| `preferred_crops` | "los que tenga preferencia el usuario" | Restricción blanda (desempate y peso en objetivo) |
| `excluded_crops` | derivado `[D]` | Restricción dura |

Los cultivos no viables aparecen deshabilitados con el motivo: *"Requires 2,100 GDD; your area provides 1,780."*

### 6.5 Qué NO se pide

DNI, teléfono, email, coordenadas catastrales, datos bancarios, historial de rendimientos. Máximo **14 campos visibles** en el camino principal.

---

## 7. Datos: catálogo definitivo y contrato de extracción

### 7.1 Reglas de selección

1. **Producto declarado, no inferido.** Solo se usa lo listado en §7.2. Prohibido añadir un dataset nuevo sin actualizar este documento.
2. **Una variable, una fuente primaria.** Cada magnitud tiene una única fuente primaria y una cadena de respaldo (§7.4). Mezclar fuentes sin declararlo invalida el resultado.
3. **Zonal, no puntual.** Toda variable ráster se agrega sobre el **polígono de la parcela** (§9.3), nunca sobre el centroide, salvo POWER (que es intrínsecamente puntual).
4. **QA obligatorio.** Si el producto trae capa de calidad, se aplica un umbral y se cuenta la cobertura válida. Sin QA no hay confianza.
5. **Escala declarada.** Cada capa lleva su resolución en la UI (§7.5).

### 7.2 Tabla maestra (23 productos)

`ID` = identificador interno. `short_name` = clave de búsqueda en CMR/Earthdata; **es la referencia autoritativa**, no el DOI.

| ID | Producto | `short_name` | Qué se extrae exactamente | Resolución · periodo | Uso en ROOTSHIFT |
|---|---|---|---|---|---|
| **P01** | SMAP L4 Soil Moisture | `SPL4SMGP` | `sm_rootzone`, `sm_surface`, `soil_temp_layer1`, `evapotranspiration` | 9 km · 3 h · desde 2015-03-31 | Humedad de raíz, **ADD**, percentiles de sequía agrícola |
| **P02** | SMAP L3 Enhanced | `SPL3SMP_E` | `soil_moisture_am`, `soil_moisture_pm`, `retrieval_qual_flag` | 9 km · diario · desde 2015 | Estado del suelo para laboreo/siembra; validación de P01 |
| **P03** | SMAP L4 Carbon | `SPL4CMDL` | `nee_pft{n}_mean`, `gpp_pft{n}_mean`, `rh_pft{n}_mean`, `soc_pft{n}_mean` | 9 km · diario · desde 2015 | **Balance de carbono**: sumidero o fuente; salud del suelo |
| **P04** | GPM IMERG Final Daily | `GPM_3IMERGDF` | `precipitation` (mm/día) | 0,1° · diario · desde 1998 | **Lluvia primaria**: SPI, Rx1day, CDD, totales de temporada |
| **P05** | GPM IMERG Final 30-min | `GPM_3IMERGHH` | `precipitation` (mm/h), `precipitationQualityIndex` | 0,1° · 30 min · desde 1998 | Intensidad → **erosividad R** de RUSLE; picos de inundación |
| **P06** | MODIS Vegetation Indices | `MOD13Q1` | `250m_16_days_NDVI`, `250m_16_days_EVI`, `250m_16_days_pixel_reliability` | 250 m · 16 d · desde 2000-02 | VCI, fenología, suelo desnudo, capa F4 |
| **P07** | MODIS Land Surface Temp. | `MOD11A2` | `LST_Day_1km`, `LST_Night_1km`, `QC_Day`, `QC_Night` | 1 km · 8 d · desde 2000-02 | Estrés térmico y heladas radiativas observadas; capa F4 |
| **P08** | MODIS ET (gap-filled) | `MOD16A2GF` | `ET_500m`, `PET_500m`, `LE_500m`, `PLE_500m`, `ET_QC_500m` | 500 m · 8 d · desde 2000 | **ETa y ETm** de respaldo; déficit `PET−AET`; ratio `AET/PET` |
| **P09** | MODIS NPP/GPP anual | `MOD17A3HGF` | `Npp_500m`, `Gpp_500m`, `Npp_QC` | 500 m · anual · desde 2001 | Residuos y materia orgánica aportados por cada rotación |
| **P10** | MODIS Land Cover | `MCD12Q1` | `LC_Type1` (IGBP), `QC` | 500 m · anual · desde 2001 | Máscara de cultivo, factor C de RUSLE, número de curva |
| **P11** | HLS Landsat | `HLSL30` | `B02`–`B07`, `Fmask`, `HLS_QA` | 30 m · 2–3 d (L8+L9+S2) · desde 2013-04 | NDVI y **NDTI** (residuos), suelo desnudo, rotación real |
| **P12** | NASADEM | `NASADEM_HGT` | `NASADEM_HGT` (elevación, sin huecos) | 30 m · estático (2000) | Pendiente, **factor LS** de RUSLE, drenaje, corrección de presión |
| **P13** | GLDAS Noah 2.1 | `GLDAS_NOAH025_3H` | `SoilMoi0_10cm_inst`, `SoilMoi10_40cm_inst`, `SoilMoi40_100cm_inst`, `Qs_acc`, `Qsb_acc`, `Evap_tavg`, `Rainf_tavg` | 0,25° · 3 h · desde 2000 | Humedad profunda y **escorrentía** donde el satélite no llega |
| **P14** | GLDAS CLSM 2.2 + GRACE DA | `GLDAS_CLSM025_DA1_D` | `GWS_tavg`, `TWS_tavg` | 0,25° · diario · desde 2003 | **Agua subterránea** y almacenamiento total; tendencia de acuífero |
| **P15** | NASA POWER (AG) | POWER Daily API | `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `PS` | 0,5° · diario · desde 1981 | GDD, heladas, olas de calor, VPD, **ET0** de respaldo |
| **P16** | SSURGO | Soil Data Access | textura, MO, pH, CEC, drenaje, grupo hidrológico, `kffact`, `wthird_r`, `wfifteen_r` | polígono · estático | **Base edáfica**: TAW, RAW, K de RUSLE, curva de retención |
| **P17** | STATSGO2 | Soil Data Access | mismos campos que P16 | 1:250 000 · estático | Respaldo regional cuando SSURGO tiene huecos |
| **P18** | FAO GAEZ v4 | GAEZ Data Portal | aptitud, **rendimiento alcanzable** (secano/regadío), déficit hídrico, periodo de crecimiento | 5′ (~9 km) · base 1961–2010 + **RCP4.5/8.5 2050s** | `Ym`, filtro de viabilidad, **escenarios futuros** |
| **P19** | OpenET | OpenET API | `et` (mm/día y mensual, ensemble) | 30 m · diario/mensual · desde 1999 | **ETa primaria** por parcela |
| **P20** | USDA Ag Data Commons | catálogo | coeficientes de extracción **N, P₂O₅, K₂O** por unidad de rendimiento; créditos de fijación de leguminosas | tabular · estático | **Balance de nutrientes** de la rotación |
| **P21** | NAIP | USGS EarthExplorer | ortofoto RGB/NIR 1 m | 1 m · 2–3 años | Apoyo a la delineación de parcela y validación de suelo desnudo; basemap F4 |
| **P22** | CoCoRaHS | Data Explorer | `precip_mm` diaria por estación | estación · diario | **Validación de IMERG** a escala local; factor de sesgo opcional |
| **P23** | NASA GIBS | WMS `gibs.earthdata.nasa.gov` | mapas PNG de `MODIS_Terra_L3_NDVI_16Day`, `MODIS_Terra_CorrectedReflectance_TrueColor`, `MODIS_Terra_L3_Land_Surface_Temp_8Day_Day` | ráster renderizado · fecha arbitraria · desde 2000 | **Visualización de F4**: imagen real del campo en el mapa temporal. No entra en ningún cálculo |

> **Nota sobre DOIs.** El equipo aportó DOIs por producto. El implementador debe resolver la versión vigente **por `short_name` en CMR/Earthdata Search** y guardar en `data/catalog/sources.yaml` el `concept_id`, la versión y el DOI realmente usados. Nunca se codifica un DOI a mano en el motor.

> **P23 (GIBS) es excepción declarada.** Se añadió para que F4 muestre **imagen real** del campo (MODIS NDVI, color verdadero y temperatura superficial) sin credenciales. Es un servicio de **visualización**: no entra en ningún cálculo, no altera índices y se acredita como "NASA GIBS" en la propia tarjeta. Las capas WMS verificadas son `MODIS_Terra_L3_NDVI_16Day`, `MODIS_Terra_L3_NDVI_Monthly`, `MODIS_Terra_CorrectedReflectance_TrueColor` y `MODIS_Terra_L3_Land_Surface_Temp_8Day_Day`.

### 7.3 Contratos de extracción
Cada bloque define **qué campo**, **cómo se agrega** y **qué QA se aplica**. Es normativo.

#### P01 · SMAP L4 `SPL4SMGP`

```text
Leer:      sm_rootzone (m3/m3), sm_surface, soil_temp_layer1 (K), evapotranspiration (mm/d)
Escala:    1.0 (ya en unidades físicas)
Temporal:  media diaria de los 8 pasos de 3 h → serie diaria
Espacial:  media de píxeles cuyo centro cae dentro del polígono (9 km ⇒ 1–4 píxeles)
QA:        descartar sm_rootzone fuera de [0, 0.6] m3/m3; descartar si soil_temp_layer1 ≤ 273.15 K (suelo helado)
Salida:    smrz_daily, smrz_pct (percentil por ventana de 15 días y año), add_days
```

#### P02 · SMAP L3 `SPL3SMP_E`

```text
Leer:      soil_moisture_am, soil_moisture_pm, retrieval_qual_flag
QA:        solo retention flag "recommended" (bit 0) y sin flag de RFI
Temporal:  preferir AM (06:00 local) para estado del suelo al amanecer
Espacial:  media zonal
Salida:    smsurf_daily, workability_flag (ver §10.12.4)
Uso extra: validación de P01 (r y sesgo entre sm_surface y sm_rootzone normalizados)
```

#### P03 · SMAP L4 Carbon `SPL4CMDL`

```text
Leer:      nee_pft{n}_mean, gpp_pft{n}_mean, rh_pft{n}_mean  [gC m-2 d-1] con n = 1..8;
           usar el PFT dominante del píxel (soc_pft{n}_mean para el pool de carbono)
Temporal:  suma anual por año civil y por temporada de cultivo; media de 30 días para tendencia
Espacial:  media zonal ponderada por área de PFT
QA:        qa_count_pft > 0; descartar si el PFT dominante no es vegetado
Salida:    nee_annual (gC/m2/año), gpp_annual, rh_annual, carbon_sink_flag (nee < 0)
```

#### P04 · IMERG diario `GPM_3IMERGDF`

> **Nota de implementación (v2.1).** La primera versión implementada usa **IMERG mensual (`GPM_3IMERGM` v07)** vía
> OPeNDAP para SPI/SPEI y los totales anuales, porque un grano diario de 19 MB a 0,5 MB/s hace inviable
> una serie de 24 años (≈87 GB) frente a 61 s por OPeNDAP. Los extremos diarios (`Rx1day`, `CDD`)
> siguen calculándose con POWER y así se declara en la UI (`PRECIP_MIXED`).

```text
Leer:      precipitation (mm/día)
QA:        descartar valores < 0; días sin dato → NaN (no rellenar con 0)
Temporal:  mensual (suma), estacional (suma), anual (suma)
Espacial:  media zonal de píxeles 0,1° con ≥ 70 % de superficie dentro del polígono
Salida:    pr_daily, pr_month, rx1day, rx5day, cdd, spi_3/6/12, pr_anomaly_pct
```

#### P05 · IMERG 30-min `GPM_3IMERGHH`

```text
Leer:      precipitation (mm/h), precipitationQualityIndex
QA:        descartar pasos con quality index por debajo del percentil 10 de la serie
Temporal:  eventos: agrupar pasos consecutivos con P > 0
Espacial:  media zonal
Cálculo:   RUSLE R (§10.12.6): E = 0.29·(1 − 0.72·exp(−0.05·I)) por mm; EI30 = Σ(E·ΔV)·I30
Salida:    r_factor_monthly (MJ·mm·ha-1·h-1), r_factor_annual, i30_max
```

#### P06 · MOD13Q1

```text
Leer:      250m_16_days_NDVI, 250m_16_days_EVI, pixel_reliability
Escala:    ×0.0001;  rellenar −3000 → NaN
QA:        pixel_reliability ∈ {0 "good", 1 "acceptable"} únicamente
Espacial:  media zonal de píxeles con centrado dentro del polígono; exigir ≥ 1 píxel válido
Temporal:  mantener 16 días; remuestrear a mensual por media para la UI
Salida:    ndvi_ts, vci, ndvi_peak_doy, ndvi_amplitude, bare_soil_months
```

#### P07 · MOD11A2

```text
Leer:      LST_Day_1km, LST_Night_1km, QC_Day, QC_Night
Escala:    ×0.02 → K;  convertir a °C
QA:        bits de QC de calidad "good" (bits 0–1 = 00)
Temporal:  8 días → mensual (media)
Salida:    lst_day_c, lst_night_c, frost_nights_observed, heat_days_observed
```

#### P08 · MOD16A2GF

```text
Leer:      ET_500m, PET_500m, ET_QC_500m
Escala:    ×0.1 → kg/m2/8d ≡ mm/8d
QA:        ET_QC_500m "good" (valor 0) o "best" (1); descartar el resto
Temporal:  suma de 8 días → estacional y anual
Espacial:  media zonal
Salida:    eta_mm, etm_mm, et_ratio (AET/PET), water_deficit_mm (PET−AET)
```

#### P09 · MOD17A3HGF

```text
Leer:      Npp_500m, Gpp_500m, Npp_QC
Escala:    ×0.0001 → kg C/m2/año
Temporal:  anual; interpolar años sin dato (máx. 1 año)
Salida:    npp_kgc_m2, gpp_kgc_m2, residue_index (ver §10.9.1)
```

#### P10 · MCD12Q1

```text
Leer:      LC_Type1 (clases IGBP 1–17), QC
Temporal:  anual; usar el año más reciente con QC aceptable
Espacial:  clase modal del polígono
Salida:    landcover_class, crop_fraction (clases 12 "Croplands" y 14 "Cropland/Natural Veg")
Uso:       factor C de RUSLE, número de curva, máscara de "esto no es cultivo"
```

#### P11 · HLS `HLSL30`

```text
Leer:      B02,B03,B04,B05,B06,B07 + Fmask
Escala:    reflectancia ×0.0001
QA:        Fmask sin nubes, sin sombra, sin nieve (bits 0–3 = 0)
Índices:   NDVI = (B05−B04)/(B05+B04)
           NDTI = (B06−B07)/(B06+B07)     ← residuos vs suelo desnudo
           NDWI = (B03−B05)/(B03+B05)
Espacial:  media zonal 30 m (decenas de píxeles por parcela)
Salida:    ndvi_30m, ndti_30m, residue_cover_pct, bare_soil_days
```

#### P12 · NASADEM `NASADEM_HGT`

```text
Leer:      NASADEM_HGT (m)
Derivar:   pendiente y orientación con Horn 3×3 sobre ventana 5×5
Cálculo:   LS = (n+1)/22.13)^m · (sin θ/0.0896)^n  con m=0.5, n=1.3 (Wischmeier-Smith)
           o LS por unidad de flujo acumulado si se dispone de hidrología
Salida:    elevation_m, slope_pct, aspect_deg, ls_factor
```

#### P13 · GLDAS Noah 2.1

```text
Leer:      SoilMoi0_10cm_inst, SoilMoi10_40cm_inst, SoilMoi40_100cm_inst [kg/m2],
           Qs_acc, Qsb_acc [kg/m2], Evap_tavg [W/m2], Rainf_tavg [kg/m2/s]
Conversión: humedad volumétrica = kg/m2 / (profundidad_cm · 10)  (densidad agua 1000 kg/m3)
Temporal:  diario (media de los 8 pasos de 3 h)
Espacial:  vecino más próximo al centroide (0,25° ⇒ 1 píxel)
Salida:    sm_deep_0_100, runoff_mm_day (Qs+Qsb convertido), gldas_et_mm_day
```

#### P14 · GLDAS CLSM DA `GLDAS_CLSM025_DA1_D`

```text
Leer:      GWS_tavg, TWS_tavg   (confirmar nombres exactos en la ficha del producto)
Temporal:  mensual
Espacial:  vecino más próximo; aplicar corrección de tendencia regional si se documenta
Cálculo:   tendencia de Sen + Mann-Kendall sobre la anomalía mensual
Salida:    gws_trend_cm_year, gws_anomaly_pct
```

#### P15 · NASA POWER

```text
Endpoint:  https://power.larc.nasa.gov/api/temporal/daily/point
Parámetros: T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PS
Query:     ?parameters=...&community=AG&longitude=..&latitude=..&start=19810101&end=..&format=JSON&time-standard=LST
Límite:    máx. 20 parámetros por petición; una petición por celda (no por parcela)
Salida:    tmax_c, tmin_c, tdew_c, rh_pct, ws2_ms, rs_mj_m2, ps_kpa
```

#### P16 · SSURGO (Soil Data Access)

**Dos pasos obligatorios.**

```text
Paso 1 — espacial:
POST https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest
{ "query": "SELECT * FROM SDA_Get_Mukey_from_intersection_with_SDU('POLYGON((...))', '4326')",
  "format": "JSON" }
→ lista de mukey con área de intersección
(verificar firma exacta contra la documentación SDA; soilDB::SDA_spatialQuery es la referencia)

Paso 2 — atributos (uno por mukey o en lote):
SELECT mu.mukey, mu.muname,
       ma.hydgrpdcd, ma.drclassdcd, ma.aws0150wta, ma.slope, ma.slopelenusle_r,
       c.comppct_r, c.majcompflag, c.drainagecl,
       ch.hzdept_r, ch.hzdepb_r, ch.sandtotal_r, ch.claytotal_r, ch.siltotal_r,
       ch.om_r, ch.ph1to1h2o_r, ch.cec7_r, ch.ksat_r, ch.kffact,
       ch.wthird_r, ch.wfifteen_r
FROM mapunit mu
JOIN component c      ON c.mukey  = mu.mukey
LEFT JOIN muaggatt ma ON ma.mukey = mu.mukey
LEFT JOIN chorizon ch ON ch.cokey = c.cokey
WHERE mu.mukey IN (:mukeys)
  AND c.comppct_r >= 15
ORDER BY mu.mukey, c.comppct_r DESC, ch.hzdept_r
```

**Agregación:**

```text
1. Componente dominante por mukey = mayor comppct_r con majcompflag = 'Yes' si existe.
2. θFC = wthird_r/100 ; θWP = wfifteen_r/100   (media ponderada por espesor de horizonte 0–100 cm)
3. Textura = clase USDA derivada de sand/clay (triángulo textural)
4. K = kffact medio ponderado (0–100 cm)
5. Grupo hidrológico = hydgrpdcd (A/B/C/D); si es mixto ("B/D"), tomar el más restrictivo y anotarlo
6. Ponderación final entre mukeys = área de intersección con el polígono
Salida: theta_fc, theta_wp, awc_mm (aws0150wta), texture_class, om_pct, ph, cec, k_factor, hydgrp
```

#### P17 · STATSGO2

Idéntico a P16 (mismo esquema de tablas) con `areasymbol`/`mukey` de escala regional. Se usa solo si SSURGO no devuelve componentes con `comppct_r ≥ 15`. Se marca `soil_source="STATSGO2"` y baja la confianza.

#### P18 · GAEZ v4

```text
Capas a extraer (por cultivo y por régimen secano/regadío):
  - suitability index / clase de aptitud
  - attainable yield (kg/ha)
  - water deficit (mm)
  - growing period (días)
Escenarios:  baseline (clima 1961–2010) · futuro 2050s RCP4.5 · futuro 2050s RCP8.5
Espacial:    5 arc-min (~9 km) → vecino más próximo al centroide; si el portal publica
             30 arc-sec para la capa, usarla y anotarlo
Salida:      gaez_yield_kg_ha, gaez_suitability, gaez_water_deficit_mm,
             gaez_yield_multiplier_2050s (futuro/base), gaez_water_multiplier_2050s
```

> **Aviso de versión:** GAEZ v4 usa RCP (AR5), no SSP. Los escenarios futuros de ROOTSHIFT se etiquetan **RCP4.5** y **RCP8.5**, nunca "SSP". Registrar en `sources.yaml` el ESM y el horizonte exactos que publique el portal.

#### P19 · OpenET

```text
Endpoint:  API de etdata.org (clave gratuita); alternativa: Data Explorer para verificación manual
Consulta:  geometría de la parcela + rango mensual (y diario si se necesita)
Campo:     et (mm) del ensemble; guardar también la dispersión entre modelos si la API la expone
Cobertura: 48 estados contiguos (ampliación dic. 2025); 30 m en el oeste, ~0,1 ha en el este
QA:        descartar meses sin dato; no interpolar más de 1 mes
Salida:    eta_openet_mm (mensual y estacional)
Regla:     si la parcela no tiene cobertura, se cae a P08 y se marca et_source="MOD16A2GF"
```

#### P20 · USDA Ag Data Commons

```text
Contenido requerido: coeficientes de extracción de nutrientes (kg N, P2O5, K2O por kg de grano
o por unidad de rendimiento) y créditos de fijación de leguminosas.
Formato:   tabla YAML normalizada en data/catalog/nutrients.yaml
Campos:    crop_id, n_removal_kg_per_t, p2o5_removal_kg_per_t, k2o_removal_kg_per_t,
           n_fixation_kg_per_ha, source_doi, confidence
Regla:     cada fila debe citar su dataset y año; sin cita, la fila no se usa
Salida:    nutrient balance (§10.8)
```

#### P21 · NAIP

```text
Uso:       (a) basemap de alta resolución en F4; (b) apoyo visual para dibujar el polígono;
           (c) validación de "suelo desnudo" frente a NDTI de P11
No se usa: como variable de cálculo
Acceso:    USGS EarthExplorer (descarga) o servicio de tiles; respetar límites de uso
```

#### P22 · CoCoRaHS

```text
Leer:      estaciones a ≤ 25 km del centroide; serie diaria de precipitación
QA:        exigir ≥ 80 % de días con dato en el periodo comparado
Cálculo:   r de Pearson y sesgo medio IMERG vs CoCoRaHS por mes
Opcional:  si r ≥ 0.7, factor de corrección multiplicativo f = clamp(mean_obs/mean_imerg, 0.7, 1.4)
           aplicado a pr_daily, marcando pr_source="IMERG+CoCoRaHS"
Salida:    imerg_validation (r, bias, n), pr_bias_factor
```

### 7.4 Cadena de precedencia por variable

**Ninguna variable se calcula sin pasar por esta tabla.** El orden es obligatorio.

| Variable | Primaria | Respaldo 1 | Respaldo 2 | Último recurso |
|---|---|---|---|---|
| Precipitación diaria | P04 IMERG Final | P04 IMERG Early | P15 POWER `PRECTOTCORR` | — (falla) |
| Temperatura, VPD, viento, radiación | P15 POWER | — | — | — (falla) |
| ET real (ETa) | P19 OpenET | P08 MOD16A2GF `ET_500m` | Balance FAO-56 | — |
| ET máxima (ETm) | P08 `PET_500m` | `Kc·ET0` (FAO-56) | — | — |
| Humedad de raíz | P01 SMAP L4 | P13 GLDAS 40–100 cm | Depósito FAO-56 | — |
| Humedad superficial | P02 SMAP L3 | P13 GLDAS 0–10 cm | P01 `sm_surface` | — |
| Agua subterránea | P14 GLDAS CLSM DA | — | — | Indicador omitido (`null`) |
| Escorrentía | P13 GLDAS | Número de curva (P16 + P10) | 0 | — |
| Suelo (textura, θFC, θWP, K) | P16 SSURGO | P17 STATSGO2 | Entrada del usuario | Franco limoso por defecto (`soil_source="default"`) |
| Rendimiento potencial `Ym` | P18 GAEZ (secano/regadío) | USDA NASS del condado | Tabla regional | Media estatal NASS |
| Vegetación | P06 MOD13Q1 | P11 HLS NDVI | — | — |
| Residuos / cobertura | P11 NDTI | P06 NDVI como proxy | — | — |
| Carbono del suelo | P03 SPL4CMDL | P09 NPP | — | Indicador omitido |
| Nitrogeno/PPK | P20 Ag Data Commons | Entrada del usuario | — | Balance omitido |
| Clima futuro | P18 GAEZ RCP | — | — | Sin escenario futuro (`null` + aviso) |

### 7.5 Límites de escala (declaración obligatoria en la UI)

| Dato | Resolución | Equivalente | Consecuencia |
|---|---|---|---|
| POWER | 0,5° | ≈ 50 × 55 km | Las temperaturas son de comarca, no de parcela |
| IMERG | 0,1° | ≈ 11 × 11 km | Lluvia de comarca; puede diferir de la lluvia del campo |
| GLDAS | 0,25° | ≈ 25 × 27 km | Solo sirve para tendencias y capas profundas |
| SMAP | 9 km | ≈ 9 × 9 km | Humedad media de un mosaico de parcelas |
| MOD13Q1 | 250 m | ≈ 6 ha/píxel | 5–10 píxeles por parcela de 80 acres |
| MOD16A2GF | 500 m | ≈ 25 ha/píxel | 1–3 píxeles: tendencia, no manejo fino |
| OpenET | 30 m | ≈ 0,09 ha/píxel | Escala de parcela real |
| HLS / NASADEM | 30 m | ≈ 0,09 ha/píxel | Escala de parcela real |
| SSURGO | polígono catastral | m; escala 1:12 000–1:24 000 | Unidad cartográfica, no muestra de suelo |

**Copy obligatorio en el dashboard:**

> *"Climate is represented at county scale (≈50 km); your field enters through its boundary and through 30 m imagery where available."*

### 7.6 Atribución, licencias y marcas `[D19]`

- **NASA**: logotipo y nombre visibles en el pie de todas las pantallas y en la portada del PDF, junto a *"Data provided by NASA"*. Uso conforme a las **NASA Media Usage Guidelines**; prohibido sugerir que la NASA patrocina o avala el producto.
- **Universidad de Alicante**: logotipo y nombre visibles en el pie y en la portada del PDF.
- **USDA-NRCS** (SSURGO/STATSGO2) y **FAO** (GAEZ): mención textual y enlace, sin logotipo salvo autorización expresa.
- **Descargo obligatorio**, en el pie y en el PDF:

> *"ROOTSHIFT is a simulation tool. It is not affiliated with, or endorsed by, NASA, USDA or the University of Alicante. Data are used under their respective open licenses. Results are not agronomic advice."*

- Cada tarjeta lleva `<SourceBadge />` con el producto, la resolución y el periodo.

---

## 8. Arquitectura de software

### 8.1 Componentes

```
┌───────────────────────────────────────────────────────────────────────┐
│                    BROWSER · Next.js 15 (TypeScript)                  │
│  Onboarding · Dashboard · F1 Rotation · F2 Disease · F3 Irrigation    │
│  F4 Time Map · F5 Hazards · i18n (en-US default, es-ES)               │
│  MapLibre GL JS + deck.gl · Recharts/visx · Tailwind + shadcn/ui      │
└───────────────┬───────────────────────────────────────────────────────┘
                │ HTTPS/JSON + SSE
┌───────────────▼───────────────────────────────────────────────────────┐
│                     FastAPI (Python 3.12)                             │
│  routers: farms · context · rotation · nutrients · diseases ·         │
│           irrigation · hazards · timeline · jobs · explain            │
└──────┬─────────────────────┬──────────────────────┬───────────────────┘
       │                     │                      │
┌──────▼───────┐   ┌─────────▼──────────┐   ┌───────▼─────────┐
│ ENGINE       │   │ REPOSITORIES       │   │ WORKER (RQ)     │
│ pure funcs   │   │ PostgreSQL 16      │   │ ingest · zonal  │
│ §10           │   │ + PostGIS 3.4      │   │ stats · optimize│
└──────┬───────┘   │ Redis · MinIO      │   └───────┬─────────┘
       │           └────────────────────┘           │
┌──────▼────────────────────────────────────────────▼───────────────────┐
│ PROVIDERS (only door to internet)                                     │
│ power · smap_l4 · smap_l3 · smap_carbon · imerg_daily · imerg_30min   │
│ modis_vi · modis_lst · modis_et · modis_npp · modis_lc · hls · dem    │
│ gldas · gldas_da · ssurgo · statsgo · gaez · openet · agdatacommons   │
│ naip · cocorahs                                                        │
│ (earthaccess · httpx · rioxarray · xarray · geopandas)                │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                     ┌───────────▼───────────┐
                     │ TiTiler (XYZ / COG)   │  capas F4
                     └───────────────────────┘
```

### 8.2 Stack

| Capa | Elección | Motivo |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TS + Tailwind + shadcn/ui | Velocidad de hackathon, SSR, i18n |
| Mapas | MapLibre GL JS + deck.gl + Mapbox GL Draw | Sin API key; dibujo de polígonos |
| Gráficos | Recharts + visx | Abanicos y heatmaps accesibles |
| API | FastAPI + Pydantic v2 | OpenAPI, tipado, async |
| Ciencia | numpy, pandas, xarray, rioxarray, scipy, geopandas, shapely, pyproj, numba | Estándar geo-científico |
| Datos | `earthaccess`, `httpx`, `netCDF4`, `rasterio` | Earthdata y ráster |
| BD | PostgreSQL 16 + PostGIS 3.4 | Geometrías, índices espaciales, JSONB |
| Caché / cola | Redis 7 + RQ | Simple |
| Ráster | TiTiler sobre COG | Tiles bajo demanda |
| Objetos | MinIO (S3) | COG y Parquet |
| Contenedores | Docker Compose | `docker compose up` y a correr |
| Tests | pytest + httpx + Playwright | Unitario, contrato, E2E |

### 8.3 Estructura de carpetas

```
rootshift/
├─ apps/
│  ├─ web/
│  │  ├─ app/[locale]/...
│  │  ├─ components/            # §13.1
│  │  └─ messages/en-US.json · es-ES.json
│  └─ api/
│     ├─ app/
│     │  ├─ routers/
│     │  ├─ schemas/
│     │  ├─ domain/             # ⚠️ FUNCIONES PURAS, sin I/O
│     │  │  ├─ climate.py water.py drought.py yield_model.py
│     │  │  ├─ rotation.py nutrients.py resilience.py disease.py
│     │  │  └─ irrigation.py hazards.py erosion.py
│     │  ├─ providers/          # un cliente por producto
│     │  ├─ repositories/
│     │  ├─ jobs/
│     │  └─ config/            # regions/ scoring/ rotation_effects/
│     └─ tests/
├─ pipeline/                    # CLI de ingesta y precomputo
├─ data/
│  ├─ catalog/                  # crops · diseases · nutrients · hazards · sources
│  ├─ fixtures/                 # 3 fincas demo precalculadas
│  └─ cache/
└─ docker-compose.yml
```

**Regla de dependencia:** `domain/` no importa `providers/`, `repositories/`, `FastAPI` ni `httpx`. Si un test de `domain/` necesita red, el diseño está mal.

### 8.4 Flujo "generate farm"

```
UI                 API                  WORKER                 PROVIDERS
 │ POST /farms       │                     │                       │
 ├──────────────────►│ valida + crea       │                       │
 │ 202 {job_id}      ├────────────────────►│                       │
 │◄──────────────────┤                     ├─ SSURGO (polígono) ──►│
 │ GET /jobs (SSE)   │                     ├─ POWER (celda) ──────►│
 │                   │                     ├─ IMERG d + 30min ────►│
 │                   │                     ├─ SMAP L4/L3/Carbon ──►│
 │                   │                     ├─ MODIS VI/LST/ET/NPP ►│
 │                   │                     ├─ OpenET (parcela) ───►│
 │                   │                     ├─ GLDAS + CLSM DA ────►│
 │                   │                     ├─ GAEZ (base+2050s) ──►│
 │                   │                     ├─ HLS + NASADEM ──────►│
 │                   │                     ├─ CoCoRaHS (valid.) ──►│
 │                   │                     │  zonal stats → Parquet│
 │                   │                     ├─ contexto §10.2–10.6  │
 │                   │                     ├─ rotación §10.7       │
 │                   │                     ├─ nutrientes §10.8     │
 │                   │                     ├─ IRS §10.9 · F2 · F5  │
 │ 200 artifacts     │◄────────────────────┤  persist + provenance │
 │◄──────────────────┤                     │                       │
```

**Presupuestos:** contexto desde caché < 400 ms; generación en frío ≤ 90 s (hay 22 proveedores, no 9); recálculo de rotación editada < 3 s.

### 8.5 Modos de ejecución

| Modo | Variable | Comportamiento |
|---|---|---|
| `live` | `DATA_MODE=live` | Descarga real con caché |
| `cached` | `DATA_MODE=cached` (default) | Solo caché; si falta, error controlado |
| `demo` | `DATA_MODE=demo` | Sirve `data/fixtures/*.json`; **cero red** `[D18]` |

El modo `demo` es **obligatorio**: la demo del hackathon no puede depender del wifi.

---

## 9. Pipeline de datos

### 9.1 Etapas

1. **Geometría.** Polígono → validación → área (UTM 14N) → centroide.
2. **Suelo.** SSURGO paso 1 (mukeys) → paso 2 (atributos) → agregación ponderada → θFC, θWP, TAW, K, grupo hidrológico.
3. **Clima puntual.** POWER por celda (una petición, caché).
4. **Ráster.** Para cada producto: búsqueda CMR → subset por bbox de la parcela → recorte al polígono → estadísticos zonales → serie.
5. **QA.** Aplicar el contrato de §7.3; calcular `valid_fraction`.
6. **Indicadores.** §10 → tablas de series.
7. **Persistencia.** Parquet por parcela + filas de índice en PostGIS.
8. **Fixtures.** Empaquetar 3 parcelas demo en JSON.

### 9.2 Estadísticos zonales (norma)

```python
# Para cada producto ráster y cada fecha/composite:
mask  = rasterize(polygon)                      # all_touched=False
vals  = band[mask & valid_qa]                   # solo píxeles válidos y con QA
if vals.size == 0: → NaN  (nunca 0)
stat  = mean(vals)  si cobertura ≥ 0.7
       media de los válidos (con aviso) si 0.3 ≤ cobertura < 0.7
       NaN si cobertura < 0.3
guardar: value, n_pixels, valid_fraction, product, composite_date
```

- Productos de **agregación lineal** (NDVI, LST, ET, NPP): media.
- Productos de **precipitación**: media (no suma) de píxeles, porque el píxel ya es un total diario.
- Productos de **clase** (MCD12Q1, GAEZ suitability): moda.
- **Nunca** se mezclan resoluciones en un mismo cálculo sin declararlo.

### 9.3 Caché y TTL

```python
cache_key = f"{product}:{geom_hash}:{start}:{end}:{sha1(params)[:12]}:{version}"
geom_hash = sha1(polygon.wkb)[:16]   # una parcela distinta ⇒ caché distinta
```

| Producto | TTL | Motivo |
|---|---|---|
| POWER histórico | 365 d | No cambia |
| POWER año en curso | 7 d | NRT |
| IMERG Early | 1 d | Latencia |
| IMERG Final | 90 d | Reproceso |
| SMAP L4 / L3 / Carbon | 2 d / 2 d / 15 d | Latencia |
| MODIS VI / LST / ET / NPP | 30 d | Compuestos |
| MCD12Q1 | 365 d | Anual |
| HLS | 15 d | Reproceso |
| NASADEM, SSURGO, STATSGO2, GAEZ | ∞ | Estáticos |
| OpenET | 30 d | Mensual consolidado |
| CoCoRaHS | 30 d | Observacional |

### 9.4 Cortesía con las APIs

- POWER: máx. **20 parámetros** por llamada; **una llamada por celda**; POWER bloquea clientes que insisten en la misma celda.
- Earthdata: `earthaccess.login(strategy="environment")`; `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` en `.env`, nunca en git.
- GES DISC / LP DAAC / NSIDC: **subsetting** por bbox; nunca descargar un tile completo.
- SDA: máximo 50 mukeys por consulta; reintentar con backoff.
- OpenET / GAEZ / Ag Data Commons: clave en `.env`; respetar cuotas; cachear agresivamente (son estáticos o mensuales).
- Reintentos: 3 intentos, 2/4/8 s, solo en 429/5xx. `User-Agent` identificable.

### 9.5 Controles de calidad (bloqueantes)

| Check | Regla | Acción |
|---|---|---|
| Cobertura temporal | ≥ 85 % de días/composites en el periodo | `degraded` |
| Cobertura espacial | `valid_fraction` ≥ 0.3 por composite | `NaN` |
| Coherencia térmica | `Tmin ≤ T ≤ Tmax` | clamp + incidencia |
| Rangos físicos | RH 0–100, P ≥ 0, SM 0–0.6 m³/m³ | `NaN` + incidencia |
| Fill values | `-999`, `-9999`, `-32767` | `NaN` |
| Zona horaria | POWER en **LST** | fijar `time-standard=LST` |
| Geo | polígono dentro de EE. UU. si región US | error de validación |
| Suelo | SSURGO devuelve ≥ 1 componente con `comppct_r ≥ 15` | si no → STATSGO2 |
| Unicidad | una fila por fecha | assert |

### 9.6 Matriz de precomputo

| Cálculo | ¿Precomputado? | Se recalcula cuando |
|---|---|---|
| ET0 diaria, GDD, heladas, VPD | Sí, por celda | Nunca (histórico) |
| SPI / SPEI | Sí, por celda | Nunca |
| Percentiles de humedad SMAP | Sí, por parcela | Nunca |
| RUSLE R (mensual) | Sí, por parcela | Nunca |
| Carbono (NEE/NPP anual) | Sí, por parcela | Nunca |
| Balance hídrico por cultivo | No | Al generar o editar rotación |
| Escenarios históricos S0–S5 | Sí, por parcela | Nunca |
| Multiplicadores GAEZ 2050s | Sí, por celda+cultivo | Al descargar nueva versión GAEZ |
| Rotación óptima | No | Al generar o editar |
| Nutrientes | No | Al generar o editar |
| Riesgo de enfermedad | No | Al generar |
| Diseño de riego | No | Al generar |
| Tiles F4 | Sí, por capa+fecha | Al añadir fecha nueva |

---

## 10. Motor de cálculo

> Todas las fórmulas están cerradas. Las marcadas `[P]` son parámetros en `config/*.yaml`, nunca constantes en el código.

### 10.1 Convenciones

| Elemento | Decisión |
|---|---|
| Paso temporal | Diario para clima, humedad y balance; 8/16 días para MODIS; mensual para índices de sequía; estacional para rendimiento |
| Periodo de simulación | **2001-01-01 → 2024-12-31** (24 años: es el periodo con IMERG + MODIS completos) |
| Normales climáticas | **1991–2020** para POWER; **2001–2020** para precipitación IMERG |
| Línea base de humedad | **2015–2024** (SMAP) |
| Año agrícola | Kansas: 1 temporada por año, siembra mar–may, cosecha ago–oct. Configurable por región |
| `NaN` | Interpolación lineal si el hueco ≤ 7 días; si es mayor, se excluye y baja la confianza |
| Redondeo | Cálculo en `float64`; presentación con 1–2 decimales |
| Semilla | `SEED=42` en toda simulación Monte Carlo |
| Versión | `MODEL_VERSION="2.0.0"`; cambiar una fórmula obliga a subir versión e invalidar caché |

### 10.2 Base meteorológica (POWER)

#### 10.2.1 Grados día (GDD)

$$
GDD_d=\max\!\Bigl(0,\ \frac{\min(T_{max},T_{opt})+T_{min}}{2}-T_{base}\Bigr)
$$

Acumulado desde siembra hasta `gdd_to_maturity` (Anexo A). Se usa para ventanas fenológicas, viabilidad y sincronización con MOD13Q1.

#### 10.2.2 Heladas

| Indicador | Definición |
|---|---|
| `last_frost_doy` | último día de primavera con `Tmin < 0 °C`, por año |
| `first_frost_doy` | primer día de otoño con `Tmin < 0 °C`, por año |
| `frost_free_days` | media de `first_frost − last_frost` en 30 años |
| `p_frost_month[m]` | `P(Tmin < t_frost_crop)` empírica por mes |
| `lst_frost_nights` | noches con `LST_Night` < 0 °C en MOD11A2 (helada radiativa observada) |

Fechas al 50 % y al 10 % de probabilidad por interpolación de la distribución empírica. **Doble fuente:** POWER da la helada de aire; MOD11A2 da la helada de superficie. Si difieren en más de 10 días, se avisa: es el caso típico de inversión térmica.

#### 10.2.3 Estrés térmico y VPD

$$
VPD_d=e_s-e_a\ [\text{kPa}],\qquad
HSE=\sum_{d\in W_{flor}}\max(0,\ T_{max,d}-T_{crit})\ [\text{°C·d}]
$$

`W_flor` = ±15 días alrededor de la floración media. `T_crit` por cultivo (Anexo A). Se contrasta con `heat_days_observed` de MOD11A2.

#### 10.2.4 ET0 de respaldo (FAO-56 Penman-Monteith)

Se calcula **siempre** (es barata y sirve de contraste), pero **solo se usa** si no hay ET satelital (§10.3.1).

$$
ET_0=\frac{0.408\,\Delta\,(R_n-G)+\gamma\,\frac{900}{T+273}\,u_2\,(e_s-e_a)}{\Delta+\gamma\,(1+0.34\,u_2)}
$$

$$
e^\circ(T)=0.6108\exp\!\Bigl(\tfrac{17.27T}{T+237.3}\Bigr),\quad
e_s=\tfrac{e^\circ(T_{max})+e^\circ(T_{min})}{2},\quad
e_a=e^\circ(T_{dew}),\quad
\Delta=\tfrac{4098\,e^\circ(T)}{(T+237.3)^2}
$$

$$
\gamma=0.000665\,P,\quad
R_{ns}=(1-0.23)R_s,\quad
R_{nl}=\sigma\tfrac{(T_{max}+273.16)^4+(T_{min}+273.16)^4}{2}(0.34-0.14\sqrt{e_a})\Bigl(1.35\tfrac{R_s}{R_{so}}-0.35\Bigr)
$$

$$
R_{so}=(0.75+2\cdot10^{-5}z)R_a,\quad
R_a=\tfrac{1440}{\pi}G_{sc}d_r[\omega_s\sin\varphi\sin\delta+\cos\varphi\cos\delta\sin\omega_s],\quad G\approx0
$$

`u2 = WS2M` (POWER ya entrega viento a 2 m; **no** aplicar corrección logarítmica). Validación: ejemplos del cap. 4 de FAO-56, tolerancia ±2 %.

### 10.3 Agua

#### 10.3.1 Cadena de ET (decisión central del producto)

$$
ET_a=\begin{cases}
\text{P19 OpenET} & \text{si hay dato mensual para la parcela}\\
\text{P08 MOD16A2GF } ET_{500m} & \text{si hay cobertura y QA}\\
\text{Balance FAO-56 (§10.3.3)} & \text{en el resto}
\end{cases}
\qquad
ET_m=\begin{cases}
\text{P08 } PET_{500m} & \text{si hay dato}\\
K_c\cdot ET_0 & \text{en el resto}
\end{cases}
$$

Cada resultado guarda `et_source ∈ {openet, mod16, fao56}` y ese valor entra en la procedencia y en la confianza.

**Ratio de estrés hídrico:**

$$
\rho_{ET}=\mathrm{clamp}\Bigl(\frac{ET_a}{ET_m},\ 0,\ 1\Bigr)
$$

`ρ_ET = 1` ⇒ sin estrés; `ρ_ET < 0,5` ⇒ estrés severo. Se calcula por temporada de cultivo (siembra → cosecha), no por año civil.

#### 10.3.2 Parámetros del suelo (SSURGO)

$$
TAW=1000\,(\theta_{FC}-\theta_{WP})\,Z_r\ [\text{mm}],\qquad RAW=p\cdot TAW
$$

- `θFC = wthird_r/100`, `θWP = wfifteen_r/100`, ponderados por espesor de horizonte 0–100 cm.
- Si falta `wthird_r`/`wfifteen_r`, se estiman por pedotransferencia a partir de arena/arcilla (Saxton & Rawls) y se marca `ptf_used=true`.
- `Z_r` de la tabla de cultivo (Anexo A); `p` de FAO-56 tabla 22.

#### 10.3.3 Balance hídrico de respaldo

$$
D_i=D_{i-1}-(P_i-RO_i)-I_i+ET_{c,adj,i}+DP_i,\qquad ET_{c,adj}=K_sK_cET_0
$$

$$
K_s=\begin{cases}1 & D\le RAW\\ \dfrac{TAW-D}{TAW-RAW} & D>RAW\end{cases}\qquad K_s\in[0,1]
$$

- `D_i < 0` ⇒ `DP_i = −D_i`, `D_i = 0`.
- Inicialización: `D_0 = 1000·Z_r·(θFC − sm_rootzone_0)` con SMAP; si no hay, `D_0 = 0,5·TAW` y `init_assumed=true`.
- Escorrentía `RO`: **GLDAS primario**; si no hay, número de curva `Q=(P−0.2S)^2/(P+0.8S)`, `S=25400/CN−254`, con `CN` de MCD12Q1 + grupo hidrológico SSURGO.

#### 10.3.4 Evidencia observada que acompaña al balance

| Indicador | Fuente | Fórmula |
|---|---|---|
| `et_ratio` | P08 | `AET/PET` estacional |
| `water_deficit_mm` | P08 | `Σ(PET−AET)` estacional |
| `add_days` | P01 | ver §10.4.2 |
| `gws_trend` | P14 | Sen sobre anomalía mensual |
| `runoff_total_mm` | P13 | `Σ(Qs+Qsb)` |

Estos cuatro indicadores son **la prueba** de que el balance no está inventando: si el modelo dice "estrés severo" y `et_ratio` observado es 0,85, hay un problema que la UI debe mostrar, no esconder.

### 10.4 Sequía y estado del suelo

#### 10.4.1 SPI y SPEI (sobre IMERG)

- **SPI**: totales móviles de 3/6/12 meses sobre P04 (2001–2020), ajuste gamma por máxima verosimilitud, corrección de ceros, cuantil normal.
- **SPEI**: `D_m = P_m − PET_m` con `PET_m = Σ ET_0` (POWER), ajuste log-logístico de 3 parámetros por L-momentos.

Clasificación estándar: ≥2 extremo húmedo · 1,5–1,99 muy húmedo · 1–1,49 moderado húmedo · −0,99–0,99 normal · −1 a −1,49 sequía moderada · −1,5 a −1,99 severa · ≤ −2 extrema.

Con 20–24 años de IMERG, se advierte: *"Percentiles based on 20 years; treat extreme values with caution."*

#### 10.4.2 ADD — *Agricultural Drought Days* `[P]`

Definición operativa:

$$
pct_d=\text{percentil de } sm_{rz,d} \text{ dentro de la ventana } \pm 7 \text{ días, años 2015–2024}
$$

$$
ADD=\#\{d\in\text{temporada}:\ pct_d<20\}
$$

| `ADD` (días) | Estado |
|---|---|
| 0–7 | Sin sequía agrícola |
| 8–21 | Sequía moderada |
| 22–45 | Sequía severa |
| > 45 | Sequía extrema |

Se complementa con `sm_rz_pct` del día (percentil puntual) y con el déficit de P08.

#### 10.4.3 VCI y fenología (MOD13Q1)

$$
VCI=100\cdot\frac{NDVI-NDVI_{min}}{NDVI_{max}-NDVI_{min}}
$$

`NDVI_min/max` por píxel y por periodo de 16 días en 2001–2020. `VCI < 35` ⇒ estrés vegetativo. Se extrae además `ndvi_peak_doy` (fenología observada) para comprobar que la ventana de siembra declarada coincide con la realidad del campo.

#### 10.4.4 Otros

| Indicador | Fuente | Uso |
|---|---|---|
| `cdd` | P04 | Días secos consecutivos |
| `rx1day`, `rx5day` | P04 | Extremos de lluvia |
| `groundwater_status` | P14 | `trend < −5 mm/año` ⇒ *declining*; `> +5` ⇒ *rising*; si no, *stable* |
| `drought_freq` | P04 | `P(SPEI12 < −1)` |
| `drought_trend` | P04 | Mann-Kendall + Sen sobre SPEI12 |

### 10.5 Rendimiento (FAO-33 con ET observada)

#### 10.5.1 Ecuación central `[D3]`

$$
1-\frac{Y_a}{Y_m}=K_y\Bigl(1-\rho_{ET}\Bigr)
\quad\Longrightarrow\quad
Y_{rel,water}=1-K_y\bigl(1-\rho_{ET}\bigr)\in[0,1]
$$

`ρ_ET` viene de §10.3.1 (OpenET o MOD16), **no** de un modelo de suelo. `Ky` por cultivo (FAO-33, Anexo A).

#### 10.5.2 Factores térmicos

$$
f_{heat}=1-k_h\min\!\Bigl(1,\tfrac{HSE}{HSE_{ref}}\Bigr)\ge0.5,\qquad
f_{frost}=1-k_f\min\!\Bigl(1,\tfrac{FSE}{FSE_{ref}}\Bigr)\ge0.3
$$

Defaults `[P]`: `k_h = 0.5`, `k_f = 0.7`; `HSE_ref`, `FSE_ref` por cultivo.

#### 10.5.3 Rendimiento simulado

$$
Y_{sim}=Y_m\cdot Y_{rel,water}\cdot f_{heat}\cdot f_{frost}\cdot f_{rot}
$$

`f_rot` = efecto de la rotación (§10.7.5), no fertilidad medida.

#### 10.5.4 `Ym` — rendimiento alcanzable `[D8]`

$$
Y_m=\begin{cases}
\text{GAEZ attainable yield (regadío)} & \text{si irrigation.status = irrigated}\\
\text{GAEZ attainable yield (secano)} & \text{si rainfed}
\end{cases}
$$

Respaldo: USDA NASS del condado (media 5 años) × 1,25. Último recurso: media estatal NASS × 1,25. `ym_source` se guarda y se muestra.

**Prohibido:** presentar `Y_sim` como predicción. Se muestra como rango p10–p90 de los escenarios y con la etiqueta *"simulated"*.

#### 10.5.5 Validación con satélite

$$
iNDVI=\sum_{t\in temporada}NDVI_t,\qquad
z=\frac{iNDVI-\mu_{2001-2020}}{\sigma_{2001-2020}}
$$

Se usa para comprobar que el modelo reproduce la **dirección** de las anomalías históricas (≥ 70 % de años con signo correcto, §16.3). **Nunca** se extrapola a futuro.

### 10.6 Escenarios

#### 10.6.1 Principio

Un escenario es un conjunto de años coherentes, no un año concreto. Una rotación se evalúa sobre `S = 1000` escenarios. **Números aleatorios comunes:** todos los candidatos se evalúan sobre el mismo conjunto (`seed=42`), o la comparación es ruido.

#### 10.6.2 Catálogo `[D5]`

| ID | Nombre | Construcción | Fuente |
|---|---|---|---|
| **S0** | Historical | Bootstrap de años completos 2001–2024 | P04 + P15 |
| **S1** | Severe drought | Años con `SPEI12 ≤ −1,5` o `ADD` en el decil superior, con reemplazo | P04 + P01 |
| **S2** | Multi-year drought | Bloques de 3 años consecutivos del quintil más seco | P04 |
| **S3** | Heat at flowering | S0 con `+ΔT` sobre `W_flor`, `ΔT ∈ {3, 5} °C` | P15 |
| **S4** | Extreme rainfall | S0 con `Rx1day × 1,5` | P04 |
| **S5** | Late frost | S0 con la última helada desplazada `+14` días | P15 |
| **S6** | 2050s · RCP4.5 | Multiplicadores GAEZ 2050s / baseline | P18 |
| **S7** | 2050s · RCP8.5 | Multiplicadores GAEZ 2050s / baseline | P18 |

> **Corrección respecto al borrador:** GAEZ v4 proyecta con **RCP (AR5)**, no con SSP (CMIP6). Los escenarios futuros se etiquetan RCP4.5 y RCP8.5 en toda la UI.

#### 10.6.3 Multiplicadores GAEZ (S6 / S7)

GAEZ no entrega series diarias, sino superficies de aptitud y rendimiento alcanzable. Por tanto **no se simula día a día con GAEZ**; se aplican multiplicadores por cultivo:

$$
\mu^{Y}_{c}=\frac{Y^{GAEZ}_{c,2050s}}{Y^{GAEZ}_{c,base}},\qquad
\mu^{W}_{c}=\frac{D^{GAEZ}_{c,2050s}}{D^{GAEZ}_{c,base}}
$$

$$
Y_m'=Y_m\cdot\mu^{Y}_{c},\qquad
NIR'=NIR\cdot\mathrm{clamp}(\mu^{W}_{c},0.5,2.0)
$$

**Limitación declarada en la UI:** *"2050s scenario applies crop-level climate multipliers from FAO GAEZ v4; it is not a daily climate simulation."* Es la forma honesta de usar el dato que hay.

#### 10.6.4 Métricas de salida

| Métrica | Fórmula | Para qué |
|---|---|---|
| `E[P]` | media de producción anual | Producción esperada |
| `P10/P50/P90` | percentiles | Abanico |
| `CV` | `σ/μ` | Inestabilidad |
| `CVaR10` | media del 10 % peor | Año malo |
| `P_fail` | `P(Y_s < 0,6·Y_m)` | Probabilidad de cosecha inaceptable |
| `years_above` | `P(Y ≥ 0,7·Y_m)` | Fiabilidad productiva |
| `T_recovery` | años hasta volver a `≥0,9·Y_m` tras el peor escenario | **"el mayor tiempo posible"** `[N]` |
| `P_drought3` | `P(3 años consecutivos < 0,7·Y_m)` | Robustez estructural |

`E[P]`, `P_fail` y `T_recovery` son la métrica de éxito del pitch `[D20]`.

### 10.7 Motor de rotación (F1)

#### 10.7.1 Representación

Secuencia `r = (c_1, …, c_N)`, `c_k ∈ C ∪ {fallow}`, con `N = horizon_seasons` (default **8**, rango 4–12) `[D17]`.

En Kansas la región define `seasons_per_year = 1`, de modo que 8 temporadas = 8 años. Si el agricultor practica doble cultivo (trigo + soja), la región puede declarar `seasons_per_year = 2` para esa parcela.

**Cultivos perennes (alfalfa):** no rotan anualmente. Se modelan como un bloque de `stand_length_seasons` (2–4) temporadas consecutivas, con un `break` obligatorio después. El optimizador decide *cuándo* entra el bloque, no si rota cada año.

```jsonc
{ "index": 1, "season": "2026", "crop_id": "corn", "area_ha": 32.4,
  "window": { "sow_doy": 110, "harvest_doy": 285 }, "stand_seasons": 1 }
```

#### 10.7.2 Variables de decisión

| Variable | Tipo | Descripción |
|---|---|---|
| `x[c,k]` | binaria | cultivo `c` en temporada `k` |
| `a[c,k]` | continua | superficie (ha) |
| `s[k]` | binaria | barbecho |
| `start[stand,k]` | binaria | inicio de un bloque perenne en `k` |

`Σ_c a[c,k] + a_fallow[k] = A_parcela` para toda `k`.

#### 10.7.3 Restricciones duras

| ID | Restricción | Parámetro | Fundamento |
|---|---|---|---|
| **R1** | Un cultivo (o barbecho) por temporada | — | Coherencia física |
| **R2** | Misma familia botánica separada por ≥ `g` temporadas | `g = 2` | Romper ciclo de patógenos |
| **R3** | Misma especie nunca en temporadas consecutivas | — | Suelo, nematodos, malezas |
| **R4** | Una leguminosa cada `f` temporadas, si existe alguna viable | `f = 3` | Fijación de N, ruptura de ciclo |
| **R5** | Demanda hídrica de la temporada ≤ oferta disponible (p80 de escenarios) | `η = 0,9` | No proponer lo imposible |
| **R6** | `must_include` aparece al menos una vez | — | Preferencia |
| **R7** | `excluded_crops` nunca aparece | — | Preferencia |
| **R8** | Especies distintas ≤ `max_crops` | `4` | Operabilidad |
| **R9** | La temporada admite el ciclo (GDD y ventana libre de heladas) | Anexo A | Viabilidad |
| **R10** | Si `RUSLE > 15 t/ha/año`, el barbecho lleva cubierta | — | Sostenibilidad |
| **R11** | Bloque perenne con `stand_length_seasons` y descanso posterior | 2–4 | Agronomía de alfalfa |

**R5:**

$$
NIR_k=\sum_{d\in k}\max(0,\ K_cET_{0,d}-P_{ef,d})\ \le\ \eta\cdot\bigl(V_{riego,k}+V_{lluvia,util,k}\bigr)
$$

con `V_riego,k` limitado además por `irrigation.annual_limit_m3` (derecho de agua). `P_ef,d` es la lluvia efectiva diaria, obtenida repartiendo el valor mensual de §10.11.2. Se evalúa en el **percentil 80** de los escenarios: una rotación que solo funciona en años húmedos es inválida.

#### 10.7.4 Filtro de viabilidad (candidatos)

```python
for crop in region_crops:
    if crop.id in excluded: continue
    if not soil_compatible(crop, soil): continue        # pH, textura, drenaje
    if not climate_compatible(crop, cell): continue      # GDD + heladas
    if not gaez_suitable(crop, cell): continue           # P18 aptitud
    if not water_feasible(crop, cell, water_limit): continue
    C.append(crop)
```

`climate_compatible`: `GDD_disponible ≥ 0,9·gdd_to_maturity` y `P(helada en ventana sensible) ≤ 0,3`.
Los descartes se muestran con motivo: *"Sunflower needs 2,100 GDD; your area provides 1,780."*
Si `C` tiene menos de 2 cultivos → `NO_VIABLE_ROTATION` con sugerencia de relajar restricciones.

#### 10.7.5 Efecto de rotación (`f_rot`)

No es fertilidad medida: es un multiplicador agronómico declarado en `config/rotation_effects.yaml`.

| Predecesor → sucesor | `f_rot` |
|---|---|
| Leguminosa → cereal | **1,10** |
| Leguminosa → leguminosa | 0,90 |
| Cereal → leguminosa | 1,00 |
| Cereal → cereal (distinta especie) | 0,95 |
| Cereal → cereal (misma especie) | 0,80 |
| Misma familia | 0,75 |
| Barbecho → cualquiera | 1,05 |
| Cultivo de cobertura → cualquiera | 1,05 |
| Perenne (alfalfa) → cualquiera | 1,12 |
| Cualquiera → perenne | 1,00 |

#### 10.7.6 Función objetivo

$$
J=w_P\hat{P}_{norm}+w_R\,IRS_{norm}+w_W(1-W_{norm})+w_D D_{norm}-w_F P_{fail}-w_C CV
$$

| `objective` | `w_P` | `w_R` | `w_W` | `w_D` | `w_F` | `w_C` |
|---|---|---|---|---|---|---|
| `production` | 0,45 | 0,15 | 0,10 | 0,10 | 0,15 | 0,05 |
| `balanced` | 0,25 | 0,25 | 0,15 | 0,10 | 0,15 | 0,10 |
| `resilience` | 0,15 | 0,40 | 0,15 | 0,10 | 0,15 | 0,05 |
| `water` | 0,15 | 0,20 | 0,40 | 0,10 | 0,10 | 0,05 |

`risk_tolerance` modula `w_F`: `low ×1,5 · medium ×1 · high ×0,6`. Normalización min–max **sobre los candidatos evaluados**.

#### 10.7.7 Algoritmo `[D4]`

**Etapa A — DP aditivo.** Si el rendimiento depende del cultivo y de su predecesor inmediato, la secuencia es una cadena y hay óptimo por programación dinámica:

```python
# Y[c,k,e] precomputado; M[cp,c] = f_rot
best = {(c, e): Y[c, 0, e] * M[None, c] for c in C for e in range(S)}
for k in range(1, N):
    nxt = {}
    for c in C:
        for e in range(S):
            nxt[(c, e)] = max(best[(cp, e)] + Y[c, k, e] * M[cp, c] for cp in C)
    best = nxt
# k-best DP para recuperar las K = 20 mejores secuencias
```

Coste `O(N·C²·S)` = 8·100·1000 = 800 000 operaciones por parcela: instantáneo.

**Etapa B — Monte Carlo.** Las 20 mejores se evalúan con el modelo completo (agua, calor, helada, IRS, `P_fail`, `CV`, `T_recovery`) sobre `S = 1000` escenarios. Vectorizado. Objetivo < 8 s.

**Etapa C — búsqueda local.** `swap` e `insert` sobre las 5 mejores, 2 rondas de hill climbing. < 3 s.

**Alternativa (no elegida):** MILP exacto con `PuLP`/`OR-Tools` para la asignación de superficie. Se documenta como trabajo futuro, no se implementa.

#### 10.7.8 Salida

```jsonc
{
  "rotation_id": "rot_8f3a",
  "sequence": [ { "k": 1, "season": "2026", "crop_id": "soybean", "area_ha": 32.4 }, "…" ],
  "metrics": { "expected_production_t": 148.2, "p10_t": 96.4, "p90_t": 181.0,
               "cv": 0.18, "p_fail": 0.09, "recovery_years": 1.4, "irs": 71 },
  "baseline": { "rotation_id": "rot_current", "metrics": { "…": 0 } },
  "delta_vs_baseline": { "production_pct": 14.2, "p_fail_delta": -0.11, "irs_delta": 19 },
  "nutrients": { "n_balance_kg_ha": -18.0, "n_fixation_credit_kg_ha": 56.0, "…": 0 },
  "findings": [
    { "code": "WATER_GAP_COVERED", "severity": "positive",
      "text": "The proposed rotation cuts July irrigation demand by 22% (118 → 92 mm) by replacing corn with soybean.",
      "evidence": { "indicator": "nir_july_mm", "current": 118, "proposed": 92 } },
    { "code": "LEGUME_BREAK", "severity": "positive",
      "text": "Puts a legume in the rotation every 3 seasons, breaking the cereal disease cycle.",
      "evidence": { "rule": "R4", "value": 3 } },
    { "code": "DROUGHT_SENSITIVITY", "severity": "warning",
      "text": "Under S2 (three dry years) production drops 34%, versus 41% for the current rotation.",
      "evidence": { "scenario": "S2", "proposed": 0.66, "current": 0.59 } }
  ],
  "provenance": [ "…" ]
}
```

Códigos mínimos de hallazgo: `WATER_GAP_COVERED`, `LEGUME_BREAK`, `FAMILY_BREAK`, `DROUGHT_SENSITIVITY`, `HEAT_EXPOSURE`, `FROST_RISK`, `DISEASE_PRESSURE`, `CARBON_GAIN`, `EROSION_REDUCED`, `NUTRIENT_DEFICIT`, `DIVERSITY_UP`, `DIVERSITY_DOWN`.

Generador **determinista** (plantillas + reglas), sin LLM `[D15]`.

### 10.8 Balance de nutrientes `[D3, P20]`

#### 10.8.1 Extracción

$$
R_{N,k}=\sum_c Y_{sim,c,k}\cdot\kappa^{N}_{c},\qquad
R_{P,k}=\sum_c Y_{sim,c,k}\cdot\kappa^{P_2O_5}_{c},\qquad
R_{K,k}=\sum_c Y_{sim,c,k}\cdot\kappa^{K_2O}_{c}
$$

`κ` = coeficiente de extracción (kg de nutriente por tonelada de grano) de `nutrients.yaml` (P20), con su `source_doi`.

#### 10.8.2 Aporte de leguminosas

$$
F_{N,k}=\sum_{c\in\text{leguminosas}} A_{c,k}\cdot\phi_c
$$

`φ_c` = crédito de fijación (kg N/ha), p. ej. soja ≈ 50–60 % de su demanda; alfalfa mayor. Valores en `nutrients.yaml`, cada uno con cita.

#### 10.8.3 Balance

$$
B_{N,k}=I_{N,k}+F_{N,k}-R_{N,k}
$$

`I_N` = aporte declarado por el usuario (`resources.fertility`); si falta, `B_N` es **solo extracción** y así se muestra: *"Removal only — add your applied N to see the balance."*

**Salida:** `n_balance_kg_ha` por temporada y por rotación, `p_balance`, `k_balance`, y una recomendación cualitativa (`balanced`, `deficit`, `surplus`). **Nunca** se recomienda una dosis de fertilizante: es asesoramiento.

### 10.9 Índice de Resiliencia ROOTSHIFT (IRS)

> **Declaración obligatoria:** el IRS es un índice compuesto propio. **No es un estándar científico.** La UI lo dice en el tooltip.

#### 10.9.1 Subíndices (0–100)

**1. `I_water` — garantía hídrica (peso 0,25)**

$$
I_{water}=100\cdot\Bigl(0{,}5\cdot\overline{\rho_{ET}}+0{,}3\cdot\text{cov}+0{,}2\cdot g_{gw}\Bigr)
$$

`ρ_ET` = ratio ETa/ETm medio de la rotación; `cov` = fracción de escenarios con la demanda cubierta; `g_gw` = 1 si `groundwater_status = stable/rising`, 0,5 si `declining` con tendencia > −10 mm/año, 0 si peor.

**2. `I_stability` — estabilidad productiva (peso 0,20)**

$$
I_{stab}=100\cdot\bigl(1-\min(1,\tfrac{CV}{0{,}5})\bigr)\cdot(1-P_{fail})
$$

**3. `I_soil` — salud del suelo (peso 0,20)**

$$
I_{soil}=100\cdot\bigl(0{,}25\,c_{NEE}+0{,}20\,r_{NPP}+0{,}25\,e_{RUSLE}+0{,}15\,l_{leg}+0{,}15\,b_{N}\bigr)
$$

| Componente | Normalización |
|---|---|
| `c_NEE` | `1` si el NEE anual medio de la rotación es < 0 (sumidero); `0,5` si `abs(NEE)` < 20 gC/m²/año; `0` si fuente neta |
| `r_NPP` | `min(1, NPP_medio / NPP_ref)` con `NPP_ref = 600 gC/m²/año` `[P]` |
| `e_RUSLE` | `1 − min(1, A/15 t·ha⁻¹·año⁻¹)` |
| `l_leg` | `min(1, nº leguminosas / ceil(N/3))` |
| `b_N` | `1` si `B_N ≥ 0`; `0,5` si déficit < 20 kg N/ha; `0` si mayor |

**4. `I_diversity` — diversidad (peso 0,15)**

$$
I_{div}=100\cdot\frac{H}{\ln(S_{max})},\qquad H=-\sum_c p_c\ln p_c
$$

**5. `I_health` — presión de enfermedades (peso 0,10)**

$$
I_{health}=100-\overline{FI}
$$

**6. `I_hazard` — exposición (peso 0,10)**

$$
I_{haz}=100\cdot\Bigl(1-\min\bigl(1,\textstyle\sum_h p_h l_h\bigr)\Bigr)
$$

#### 10.9.2 Índice final

| Subíndice | Peso |
|---|---|
| `I_water` | 0,25 |
| `I_stability` | 0,20 |
| `I_soil` | 0,20 |
| `I_diversity` | 0,15 |
| `I_health` | 0,10 |
| `I_hazard` | 0,10 |

Pesos en `config/scoring.yaml`. Cambiarlos invalida caché (`params_hash`).

#### 10.9.3 Interpretación (copy exacto, en inglés)

| Rango | Etiqueta | Frase |
|---|---|---|
| 80–100 | Highly resilient | "Holds up across most of the futures tested." |
| 60–79 | Resilient | "Holds up in most scenarios; water or diversity are the weak points." |
| 40–59 | Vulnerable | "Works in normal years; loses production in bad ones." |
| 20–39 | Highly vulnerable | "High chance of failure under drought or heat." |
| 0–19 | Critical | "This system is not sustainable under the scenarios tested." |

Siempre se muestra el desglose con la contribución `w_i·I_i` en barras apiladas.

### 10.10 Motor de enfermedades (F2) `[D11]`

#### 10.10.1 Qué calcula

**Favorabilidad climática** para que una enfermedad progrese en un cultivo, en una ventana. **No** detecta, no diagnostica, no estima pérdida económica.

#### 10.10.2 Duración de mojado foliar (LWD)

No hay POWER horario en el catálogo, así que se usa un **proxy diario** `[P]`:

$$
LWD_d\approx 12\cdot\mathbb{1}[RH_{2m}\ge85]\cdot\mathbb{1}[T_{min}-T_{dew}\le2]+2\cdot\mathbb{1}[P_d>1]+2\cdot\mathbb{1}[LST_{night}\le T_{dew}]
$$

El tercer término usa MOD11A2 (helada de superficie ⇒ rocío probable) y es lo que compensa no tener datos horarios. Se marca `lwd_method="daily_proxy"` y la confianza baja a **media** automáticamente.

#### 10.10.3 Favorabilidad

$$
g_T=\text{trapecio}(T_{med};T^{dis}_{min},T_{opt,lo},T_{opt,hi},T^{dis}_{max})\in[0,1]
$$

$$
g_W=\min\!\Bigl(1,\tfrac{LWD_d}{LWD_{req}}\Bigr),\qquad
g_I=\begin{cases}1{,}00&\text{huésped en la parcela los 12 meses previos}\\0{,}60&\text{huésped en 500 m}\\0{,}30&\text{sin huésped conocido}\end{cases}
$$

$$
FI_d=g_T\,g_W\,g_I,\qquad
FI=100\bigl(1-e^{-\lambda\sum_d FI_d}\bigr),\quad \lambda=0{,}03
$$

| `FI` | Nivel | Color |
|---|---|---|
| 0–24 | Low | verde |
| 25–49 | Medium | amarillo |
| 50–74 | High | naranja |
| 75–100 | Very high | rojo |

#### 10.10.4 Catálogo inicial (12 pares)

Valores `[P]`, **pendientes de validación agronómica** antes de la demo (la validación está aprobada en D11).

| Cultivo | Enfermedad | Patógeno | T mín | T ópt | T máx | Horas mojado | Peso |
|---|---|---|---|---|---|---|---|
| Corn | Gray leaf spot | *Cercospora zeae-maydis* | 15 | 22–30 | 35 | 12 | 0,8 |
| Corn | Northern corn leaf blight | *Exserohilum turcicum* | 10 | 18–27 | 32 | 8 | 0,7 |
| Corn | Tar spot | *Phyllachora maydis* | 8 | 16–22 | 28 | 12 | 0,7 |
| Soybean | Sudden death syndrome | *Fusarium virguliforme* | 15 | 20–25 | 30 | 12 | 0,8 |
| Soybean | White mold | *Sclerotinia sclerotiorum* | 12 | 18–24 | 30 | 16 | 0,8 |
| Soybean | Frogeye leaf spot | *Cercospora sojina* | 18 | 25–30 | 35 | 8 | 0,6 |
| Winter wheat | Fusarium head blight | *Fusarium graminearum* | 15 | 20–28 | 32 | 12 | 0,9 |
| Winter wheat | Septoria tritici blotch | *Zymoseptoria tritici* | 5 | 15–20 | 25 | 16 | 0,7 |
| Winter wheat | Leaf rust | *Puccinia triticina* | 5 | 15–22 | 28 | 6 | 0,7 |
| Grain sorghum | Anthracnose | *Colletotrichum sublineola* | 15 | 22–28 | 35 | 10 | 0,6 |
| Grain sorghum | Gray leaf spot | *Cercospora sorghi* | 15 | 22–30 | 35 | 12 | 0,6 |
| Alfalfa | Spring black stem | *Phoma medicaginis* | 5 | 15–22 | 28 | 12 | 0,6 |

Esquema completo en `data/catalog/diseases.yaml` (Anexo B).

#### 10.10.5 Salida y reglas de UI

- Título: **"Disease risk"**, nunca "Diseases detected".
- Acción química acompañada siempre de: *"No products or rates are prescribed. Follow the label and consult an agronomist."*
- Cada riesgo muestra ventana y 2–3 factores desencadenantes.

### 10.11 Motor de riego (F3) `[D10]`

#### 10.11.1 Principio

Recomendación **indicativa** con números, sin proyecto ejecutivo: *"Indicative design. A technical project is required for construction."*

#### 10.11.2 Necesidad neta

$$
P_{ef}=\begin{cases}\dfrac{P(125-0{,}2P)}{125} & P\le250\ \text{mm}\\ 125+0{,}1P & P>250\ \text{mm}\end{cases}
$$

`P` mensual; se reparte a los días proporcionalmente. `NIR_k = Σ_d max(0, Kc·ET0,d − P_ef,d)`; `V = NIR·A·10` (m³).

**Restricción de derecho de agua:** `Σ_k V_k ≤ annual_limit_m3`. Si se supera, se avisa y se reduce la superficie regable propuesta.

#### 10.11.3 Selección de sistema (matriz ponderada)

| Factor | Peso | Center pivot | Pivot LEPA | SDI (goteo) | Furrow | Micro |
|---|---|---|---|---|---|---|
| Eficiencia `η` | 25 | 0,82 | 0,92 | 0,90 | 0,60 | 0,88 |
| Inversión | 20 | media | media-alta | alta | baja | alta |
| Adaptación a pendiente | 15 | alta | alta | alta | baja | alta |
| Adaptación a viento | 15 | media | media | alta | alta | alta |
| Textura arenosa | 10 | media | media | alta | baja | alta |
| Mano de obra | 10 | baja | baja | baja | alta | media |
| Energía requerida | 5 | media | media | baja | nula | baja |

`score(S) = 100 − Σ β_j·d_j(S)`; desempate por menor inversión. Con `irrigation.status = rainfed` → **solo** plan de secano.

#### 10.11.4 Dimensionamiento

$$
Q\ [\text{L/s}]=\frac{NIR_{evento}\,[\text{mm}]\cdot A\,[\text{ha}]\cdot2{,}7778}{\eta\cdot T_{riego}\,[\text{h}]}
$$

$$
P_{kW}=\frac{9{,}81\cdot Q_{m^3/s}\cdot H_m}{\eta_{bomba}}
$$

**Pivot central:** comprobar que la **tasa de aplicación** no supera la velocidad de infiltración del suelo (SSURGO `ksat_r`); si la supera, bajar `Q` o dividir en sectores. Número de pivotes = `ceil(A / A_pivot)`, con `A_pivot` configurable (por defecto 52 ha ≈ 1/4 de sección).

**Gotas:** `n_emisores_ha = 10 000/(e_lateral·e_emisor)`.

**Validaciones:** `Q ≤ flow_l_s`; `T ≤ hours_per_day`; turnos = `ceil(Q/flow)`.

#### 10.11.5 Captación de lluvia (solo si no hay agua)

$$
V_{capt}=A_{capt}\cdot P_{diseño}\cdot C_{esc}\cdot\eta_{alm}/1000\ [\text{m}^3]
$$

`C_esc` 0,85 cubierta · 0,50 suelo con cubierta · 0,35 suelo desnudo. `P_diseño` = p70 mensual. Fiabilidad simulada sobre 24 años de lluvia diaria; si `P(déficit anual) > 30 %`, recomendar reducir superficie.

#### 10.11.6 Mapa y materiales `[N]`

1. Zonas hidráulicas automáticas (máx. 4) por `shapely.ops.split` sobre el eje mayor. **Excepción pivot:** una zona circular por pivote + esquinas como zona separada.
2. Punto de agua editable (pozo/nave/depósito).
3. Si `slope > 8 %` (NASADEM), marcar "requires pressure zoning".
4. Tabla de materiales con cantidades: metros de lateral, emisores, válvulas, filtros, programador, depósito. **Sin marcas y sin precios** `[D9]`.

### 10.12 Catástrofes y operaciones (F5)

#### 10.12.1 Catálogo

| ID | Peligro | Indicador | Fuente | ¿Calculable? |
|---|---|---|---|---|
| `drought` | Sequía | SPEI-12, ADD, `sm_rz_pct` | P04 + P01 | **Sí** |
| `flood` | Inundación | Rx1day, escorrentía, pendiente | P04 + P13 + P12 | **Sí** |
| `frost` | Helada | `P(Tmin<Tcrit)`, `LST_night` | P15 + P07 | **Sí** |
| `heat` | Ola de calor | `P(Tmax>Tcrit)` en floración | P15 + P07 | **Sí** |
| `wind` | Viento fuerte | `P(WS2M·1,8 > 25 m/s)` | P15 | **Sí** |
| `erosion` | Erosión | RUSLE `A = R·K·LS·C·P` | P05+P12+P16+P10 | **Sí** |
| `hail` | Granizo | — | — | **No: solo protocolo** |
| `wildfire` | Incendio | — | — | **No: solo protocolo** |

> **Cambio respecto al borrador:** sin FIRMS en el catálogo, el incendio deja de ser calculable y pasa a protocolo. No se inventa una probabilidad.

La tarjeta de un peligro no calculable muestra: *"Insufficient data — action protocol only."*

#### 10.12.2 Probabilidad y periodo de retorno

Gumbel por L-momentos sobre máximos anuales (`n = 24`):

$$
F(x)=\exp[-\exp(-(x-\mu)/\beta)],\qquad T=\frac{1}{1-F(x)}
$$

Se reporta `T` y `P = 1/T` con IC bootstrap (1 000 remuestreos). **Con 24 años no se reportan `T > 50 años`.**

#### 10.12.3 Susceptibilidad a inundación

$$
SI_{flood}=100(0{,}40s_{rain}+0{,}25s_{runoff}+0{,}25s_{slope}+0{,}10s_{soil})
$$

`s_rain` = percentil de Rx1day; `s_runoff` = percentil de escorrentía GLDAS del mes; `s_slope` = `1 − min(1, pendiente/10 %)`; `s_soil` = grupo hidrológico D=1 · C=0,66 · B=0,33 · A=0.

#### 10.12.4 Ventanas de labor (nuevo, derivado de P02)

El agricultor también necesita saber **cuándo puede entrar al campo**. Se calcula con SMAP L3:

$$
\text{workable}_d=\mathbb{1}[sm_{surf}\le sm_{crit}]\ \wedge\ \mathbb{1}[\textstyle\sum_{i=d-2}^{d}P_i\le 5\ \text{mm}]
$$

`sm_crit` = percentil 60 de la serie histórica de ese píxel. Salida: `workable_windows` (lista de ventanas de ≥ 3 días) por mes, visible en F1 y F5. Es información que ningún dashboard climático da y que el agricultor usa mañana mismo.

#### 10.12.5 Playbooks

```jsonc
{
  "hazard": "drought",
  "p_annual": 0.22, "return_period_years": 4.5,
  "exposed_window": "2026-03-01/2026-07-31",
  "expected_loss_rel": 0.35,
  "playbook": {
    "before": [ { "step": 1, "action": "Switch to a shorter-season hybrid if March SPEI-3 < −0.8", "trigger": "spei_3 < -0.8", "lead_time_days": 45 } ],
    "during": [ { "step": 1, "action": "Prioritize available water at flowering", "trigger": "add_days > 21", "lead_time_days": 0 } ],
    "after":  [ { "step": 1, "action": "Avoid tillage while dry; plant cover after the first rain", "trigger": "always", "lead_time_days": 0 } ]
  }
}
```

Cada paso: acción en imperativo, disparador medible y antelación. Prohibido "keep an eye on the weather".

#### 10.12.6 RUSLE

$$
A=R\cdot K\cdot LS\cdot C\cdot P
$$

- `R` de P05 (EI30 mensual acumulado, §7.3).
- `K` de P16 (`kffact`).
- `LS` de P12 (Horn + fórmula de pendiente-longitud) o `slopelenusle_r` de SSURGO si está disponible.
- `C` de la rotación: barbecho desnudo 0,45 · cultivo en hilera 0,25 · cereal 0,15 · cubierta 0,05.
- `P` = 1 (sin prácticas de conservación declaradas); si el usuario declara terrazas, 0,5.

Salida en t/ha/año y comparación con el umbral de tolerancia (≈ 5–11 t/ha/año según el suelo; por defecto **7** `[P]`).

### 10.13 Confianza y procedencia

#### 10.13.1 Confianza

$$
Conf=100\cdot f_{cov}\cdot f_{series}\cdot f_{scen}\cdot f_{assum}\cdot f_{source}
$$

| Factor | Valor |
|---|---|
| `f_cov` | fracción de días/composites válidos |
| `f_series` | `min(1, años/24)` |
| `f_scen` | `min(1, S/1000)` |
| `f_assum` | 1,0 sin supuestos · 0,9 con uno · 0,75 con ≥ 2 |
| `f_source` | 1,0 fuentes primarias · 0,9 con un respaldo · 0,75 con dos · 0,6 con `soil_source=default` |

| `Conf` | UI |
|---|---|
| ≥ 80 | High confidence |
| 60–79 | Medium confidence |
| 40–59 | Low confidence |
| < 40 | Indicative only |

#### 10.13.2 Procedencia (obligatoria en toda cifra)

```jsonc
{
  "product": "GPM IMERG Final",
  "short_name": "GPM_3IMERGDF",
  "variable": "precipitation",
  "unit": "mm/day",
  "resolution": "0.1 deg",
  "period": "2001-01-01/2024-12-31",
  "concept_id": "C2723754864-GES_DISC",
  "version": "07",
  "retrieved_at": "2026-11-14T09:12:03Z",
  "model_version": "2.0.0",
  "params_hash": "a91f3c2e7b10"
}
```

#### 10.13.3 `caveats` automáticos

| Condición | Texto (en) |
|---|---|
| `et_source = mod16` o `fao56` | "Actual ET from a coarser source (500 m / model); field-level ET not available." |
| `soil_source = STATSGO2` | "Soil from regional survey (1:250,000); local variability not represented." |
| `soil_source = default` | "Soil properties assumed (silt loam); results are indicative." |
| `ptf_used` | "Field capacity estimated by pedotransfer function." |
| `ym_source = nass_county` | "Potential yield from county statistics, not field data." |
| `year < 2001` | "Simulation period starts in 2001 (IMERG/MODIS coverage)." |
| `S6/S7` | "2050s scenario uses crop-level GAEZ multipliers, not a daily simulation." |
| `lwd_method = daily_proxy` | "Leaf wetness estimated from daily data; disease risk confidence is medium." |
| `DATA_MODE = demo` | "Pre-loaded demo data." |

---

## 11. API HTTP

### 11.1 Convenciones

- Base `/api/v1`, JSON UTF-8, `snake_case`.
- **Sin cuentas** `[D14]`: cookie de sesión `rs_session` (`httpOnly`, `Secure`, `SameSite=Lax`, 30 días). No hay login, no hay password, no hay email.
- Idempotencia: `POST /farms` acepta `Idempotency-Key`.
- Sobre de respuesta:

```jsonc
{
  "data": { },
  "meta": {
    "request_id": "req_01H…", "model_version": "2.0.0",
    "generated_at": "2026-11-14T09:12:03Z", "duration_ms": 842,
    "data_mode": "cached", "confidence": 78,
    "caveats": ["Actual ET from a coarser source (500 m)."],
    "sources": [ ]
  }
}
```

- Errores:

```jsonc
{ "error": { "code": "INSUFFICIENT_CLIMATE_DATA",
             "message": "The cell has fewer than 15 years of IMERG data.",
             "details": { "years_available": 6 }, "request_id": "req_01H…" } }
```

| HTTP | `code` |
|---|---|
| 400 | `VALIDATION_ERROR`, `INVALID_BOUNDARY`, `LOCATION_OUT_OF_REGION`, `CONFLICTING_CROPS` |
| 404 | `NOT_FOUND` |
| 422 | `NO_VIABLE_ROTATION`, `INSUFFICIENT_CLIMATE_DATA`, `SOIL_NOT_FOUND` |
| 429 | `RATE_LIMITED` |
| 502 | `UPSTREAM_ERROR` (NASA/USDA/FAO/OpenET) |
| 503 | `DATA_UNAVAILABLE` |

### 11.2 Endpoints

| Método | Ruta | Devuelve |
|---|---|---|
| `POST` | `/farms` | `202 {farm_id, job_id}` |
| `GET` | `/farms/{id}` | Perfil + estado |
| `GET` | `/farms/{id}/context` | Contexto agroclimático (§10.2–10.6) |
| `GET` | `/farms/{id}/soil` | Perfil SSURGO agregado |
| `POST` | `/farms/{id}/rotation:optimize` | `202 {job_id}` → `RotationResult` |
| `GET` | `/farms/{id}/rotations/{rid}` | Rotación guardada |
| `PUT` | `/farms/{id}/rotations/{rid}` | Edita secuencia y recalcula (< 3 s) |
| `GET` | `/farms/{id}/nutrients?rotation_id=` | Balance N-P-K |
| `GET` | `/farms/{id}/diseases?crop_id=&from=&to=` | `DiseaseRiskReport` |
| `POST` | `/farms/{id}/irrigation` | `IrrigationDesign` |
| `GET` | `/farms/{id}/hazards` | Lista de peligros + estado actual |
| `GET` | `/farms/{id}/hazards/{hazard}/playbook` | Playbook |
| `GET` | `/farms/{id}/operations?month=` | Ventanas de labor |
| `GET` | `/farms/{id}/timeline?layer=&from=&to=` | Serie para F4 |
| `GET` | `/tiles/{layer}/{z}/{x}/{y}.png` | Tiles TiTiler |
| `GET` | `/jobs/{id}` · `/jobs/{id}/events` | Estado · SSE |
| `GET` | `/catalog/crops?lat=&lon=` | Catálogo con viabilidad |
| `GET` | `/health` | `{status, version, data_mode, db, redis}` |

**`GET /context` (ejemplo):**

```jsonc
{
  "data": {
    "parcels": [{ "id": "prc_1", "area_ha": 32.4, "centroid": { "lat": 38.05, "lon": -100.92 } }],
    "climate": { "cell": "38.0_-101.0", "aridity_index": 0.38, "class": "semi-arid",
                 "frost_free_days": 165, "last_frost_p50_doy": 105 },
    "precipitation": { "annual_mm": { "p10": 380, "p50": 520, "p90": 690 },
                       "rx1day_mm": 46, "cdd_days": 34, "spei_12": -1.10,
                       "validation": { "cocorahs_r": 0.81, "bias": -0.06 } },
    "water": { "et_ratio": 0.78, "water_deficit_mm": 142,
               "et_source": "openet", "groundwater_status": "declining",
               "gws_trend_mm_year": -8.4, "add_days": 28 },
    "soil": { "texture": "silt loam", "theta_fc": 0.31, "theta_wp": 0.14,
              "taw_100cm_mm": 170, "hydgrp": "B", "k_factor": 0.37, "source": "SSURGO" },
    "carbon": { "nee_gc_m2_year": -42, "npp_gc_m2_year": 610, "sink": true },
    "hazards": [ { "hazard": "drought", "p_annual": 0.22, "return_period_years": 4.5 } ]
  },
  "meta": { }
}
```

### 11.3 Límites

| Límite | Valor |
|---|---|
| Rate limit | 60 req/min por IP |
| Payload | 1 MB |
| Parcelas por finca | 5 |
| Vértices por polígono | 10 000 |
| Jobs concurrentes | 2 |
| Timeout de job | 240 s (22 proveedores) |
| Retención anónima | 30 días |

---

## 12. Modelo de datos

### 12.1 DDL

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE farm (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   uuid NOT NULL,
  name         text NOT NULL,
  region_id    text NOT NULL,
  location     geography(Point,4326) NOT NULL,
  production_system text DEFAULT 'conventional',
  irrigation   jsonb NOT NULL DEFAULT '{}',
  resources    jsonb NOT NULL DEFAULT '{}',
  constraints  jsonb NOT NULL DEFAULT '{}',
  preferences  jsonb NOT NULL DEFAULT '{}',
  data_mode    text NOT NULL DEFAULT 'live',
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE parcel (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id     uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  name        text,
  boundary    geography(Polygon,4326) NOT NULL,
  area_ha     numeric(10,2) NOT NULL,
  centroid    geography(Point,4326) NOT NULL,
  climate_cell_id text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX parcel_geom_idx ON parcel USING GIST (boundary);
CREATE INDEX parcel_farm_idx ON parcel (farm_id);

CREATE TABLE soil_profile (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id   uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  source      text NOT NULL CHECK (source IN ('SSURGO','STATSGO2','user','default')),
  mukey_list  text[],
  theta_fc    numeric(5,4), theta_wp numeric(5,4),
  awc_mm      numeric(7,2),
  texture_class text, sand_pct numeric(5,2), clay_pct numeric(5,2), silt_pct numeric(5,2),
  om_pct      numeric(5,2), ph numeric(4,2), cec numeric(6,2),
  hydgrp      text, k_factor numeric(6,4), slope_pct numeric(6,2),
  ptf_used    boolean DEFAULT false,
  payload     jsonb NOT NULL,
  retrieved_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE climate_cell (
  id          text PRIMARY KEY,
  center      geography(Point,4326) NOT NULL,
  data_start  date, data_end date,
  quality     jsonb,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE crop (
  id          text PRIMARY KEY,
  name_en     text NOT NULL,
  name_sci    text,
  family      text NOT NULL,
  cycle_type  text NOT NULL CHECK (cycle_type IN ('annual','perennial')),
  stand_seasons int DEFAULT 1,
  is_legume   boolean NOT NULL DEFAULT false,
  params      jsonb NOT NULL,
  catalog_version text NOT NULL
);

CREATE TABLE farm_crop (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id    uuid NOT NULL REFERENCES farm(id) ON DELETE CASCADE,
  parcel_id  uuid REFERENCES parcel(id) ON DELETE CASCADE,
  crop_id    text NOT NULL REFERENCES crop(id),
  season     text NOT NULL,
  area_ha    numeric(10,2) NOT NULL,
  origin     text NOT NULL CHECK (origin IN ('current','preferred','recommended'))
);

CREATE TABLE indicator_daily (
  parcel_id uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  date      date NOT NULL,
  et0_mm real, tmax_c real, tmin_c real, pr_mm real, rh_pct real, vpd_kpa real,
  gdd real, sm_rz real, sm_rz_pct real, add_day boolean,
  et_source text, pr_source text,
  PRIMARY KEY (parcel_id, date)
);

CREATE TABLE indicator_composite (      -- 8 días / 16 días / mensual
  parcel_id uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  date      date NOT NULL,
  product   text NOT NULL,              -- NDVI | LST | ET | PET | NPP | NEE
  value     real, valid_fraction real,
  PRIMARY KEY (parcel_id, product, date)
);

CREATE TABLE scenario_set (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id   uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  kind        text NOT NULL,            -- S0..S7
  n_members   int NOT NULL,
  seed        int NOT NULL,
  multiplier_set jsonb,                 -- GAEZ S6/S7
  storage_uri text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rotation (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id   uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  kind        text NOT NULL CHECK (kind IN ('current','optimized','manual')),
  objective   text, horizon_seasons int NOT NULL,
  metrics     jsonb NOT NULL,
  nutrients   jsonb,
  findings    jsonb NOT NULL DEFAULT '[]',
  params_hash text NOT NULL, model_version text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rotation_item (
  rotation_id uuid NOT NULL REFERENCES rotation(id) ON DELETE CASCADE,
  k           int NOT NULL,
  season      text NOT NULL,
  crop_id     text REFERENCES crop(id),
  area_ha     numeric(10,2) NOT NULL,
  is_cover    boolean DEFAULT false,
  stand_seasons int DEFAULT 1,
  PRIMARY KEY (rotation_id, k)
);

CREATE TABLE simulation (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rotation_id     uuid NOT NULL REFERENCES rotation(id) ON DELETE CASCADE,
  scenario_set_id uuid NOT NULL REFERENCES scenario_set(id),
  metrics         jsonb NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE disease_report (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  crop_id text NOT NULL, season text NOT NULL,
  payload jsonb NOT NULL, created_at timestamptz DEFAULT now()
);

CREATE TABLE irrigation_design (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  system text NOT NULL, payload jsonb NOT NULL, created_at timestamptz DEFAULT now()
);

CREATE TABLE hazard_assessment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  parcel_id uuid NOT NULL REFERENCES parcel(id) ON DELETE CASCADE,
  hazard text NOT NULL, p_annual numeric(6,4), return_period_years numeric(8,2),
  susceptibility numeric(5,2), calculable boolean NOT NULL, payload jsonb, created_at timestamptz DEFAULT now()
);

CREATE TABLE data_fetch_log (
  id bigserial PRIMARY KEY,
  product text NOT NULL, short_name text, concept_id text,
  parcel_id uuid, range_start date, range_end date,
  params_hash text NOT NULL, status text NOT NULL,
  http_status int, bytes bigint, duration_ms int, fetched_at timestamptz DEFAULT now()
);
CREATE INDEX ON data_fetch_log (product, parcel_id, fetched_at DESC);

CREATE TABLE artifact_provenance (
  id bigserial PRIMARY KEY,
  artifact_type text NOT NULL, artifact_id uuid NOT NULL,
  provenance jsonb NOT NULL, created_at timestamptz DEFAULT now()
);

CREATE TABLE job (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  farm_id uuid REFERENCES farm(id) ON DELETE CASCADE,
  kind text NOT NULL, status text NOT NULL DEFAULT 'queued',
  progress numeric(4,3) DEFAULT 0, stage text, error jsonb,
  created_at timestamptz DEFAULT now(), finished_at timestamptz
);

CREATE TABLE data_source_registry (        -- una fila por producto y versión
  id bigserial PRIMARY KEY,
  product text NOT NULL, short_name text, concept_id text,
  version text, doi text, license text, attribution text,
  registered_at timestamptz DEFAULT now()
);
```

### 12.2 Reglas de integridad

- `parcel.boundary` obligatorio y válido; `area_ha` calculada en servidor (nunca confiar en el cliente).
- `rotation_item.area_ha` suma ≤ `parcel.area_ha`.
- `artifact_provenance` es **append-only**.
- Borrar `farm` arrastra todo en cascada.
- `data_source_registry` es la única fuente de atribución: la UI lee de aquí, no de textos duros.

### 12.3 Almacenamiento de series

- Series diarias por parcela: Parquet en MinIO `s3://rootshift/parcels/{id}/daily.parquet` (~8 800 filas).
- Escenarios: Parquet `zstd`, una columna por miembro.
- Ráster: COG en MinIO para TiTiler.

---

## 13. Especificación de interfaz (UI/UX)

### 13.1 Sistema de diseño

| Token | Valor | Uso |
|---|---|---|
| `--rs-bg` | `#0B0F0C` | Fondo (legible a pleno sol) |
| `--rs-surface` | `#141A15` | Tarjetas |
| `--rs-border` | `#243027` | Bordes |
| `--rs-text` | `#E8F0EA` | Texto |
| `--rs-muted` | `#9AA79D` | Secundario |
| `--rs-accent` | `#7BC96F` | Acción primaria |
| `--rs-water` | `#4FA3D1` | Agua |
| `--rs-soil` | `#B08968` | Suelo |
| `--rs-risk-1` | `#3E9B5F` | Low |
| `--rs-risk-2` | `#D9B23A` | Medium |
| `--rs-risk-3` | `#DE7B3C` | High |
| `--rs-risk-4` | `#C8433B` | Very high |

**Regla:** el riesgo nunca se comunica solo con color: siempre `color + icon + text` (✓ Low, ! Medium, ▲ High, ✖ Very high). Verificable en escala de grises.

**Tipografía:** Inter, 14 px base, 1.5 de interlineado, cifras tabulares.

**Componentes obligatorios:**

| Componente | Contrato |
|---|---|
| `<SourceBadge product shortName resolution period />` | Obligatorio junto a toda cifra |
| `<ConfidenceChip value />` | High / Medium / Low / Indicative |
| `<CaveatBanner caveats />` | Colapsa si hay > 2 |
| `<MetricCard label value unit delta />` | Deltas con flecha y color |
| `<ScenarioFanChart series />` | p10–p90 + mediana |
| `<RiskCalendar matrix />` | Mes × enfermedad |
| `<ZoneMap zones waterPoint pivots />` | Zonas, punto de agua, círculos de pivote |
| `<TimeSlider from to value />` | Año-mes, teclado, play |
| `<FindingCard finding />` | Hallazgo + evidencia |
| `<WorkabilityStrip windows />` | Ventanas de labor del mes |
| `<JobProgress job />` | Etapa + barra + ETA |
| `<EmptyState title action />` | Vacío accionable |
| `<BrandFooter />` | Logos NASA + UA + descargo |

**Estados por pantalla:** `loading` (skeleton), `empty`, `error` (accionable), `degraded` (banner), `success`.

### 13.2 Dashboard

```
┌────────────────────────────────────────────────────────────────────────┐
│ ROOTSHIFT      North 80 · Finney County, KS · 80.0 ac (32.4 ha)   EN ▾ │
├────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────────────────────────────────────┐  │
│  │  IRS  71/100 │  │ "Holds up in most scenarios; water is the       │  │
│  │  ●●●●●○○    │  │  weak point."           [See breakdown ▾]      │  │
│  │  Resilient   │  │  High confidence (82)                          │  │
│  └──────────────┘  └────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│ Drought now: moderate (SPEI-12 −1.10) · 28 agricultural drought days  │
├────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│ │ Rotation │ │ Disease  │ │Irrigation│ │Time map  │ │ Hazards  │      │
│ │ +14% prod│ │ 2 alerts │ │ Pivot    │ │ 24 years │ │ 3 high   │      │
│ │ [Open]   │ │ [Open]   │ │ 2 zones  │ │ [Open]   │ │ [Open]   │      │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├────────────────────────────────────────────────────────────────────────┤
│ Climate is represented at county scale (≈50 km); your field enters     │
│ through its boundary and 30 m imagery.                                 │
│ [NASA logo] Data provided by NASA  ·  [UA logo] Universidad de Alicante│
└────────────────────────────────────────────────────────────────────────┘
```

### 13.3 F1 — Rotation panel

```
┌───────────────────────────────────────────────┬────────────────────────┐
│ Proposed rotation (8 seasons)                 │ IRS  71 ▲ +19         │
│                                               │ Production +14.2%      │
│ 2026   soybean    ██████                      │ P(fail) 9% ▼ −11 pp    │
│ 2027   corn       ███████                     │ Recovery 1.4 yr        │
│ 2028   soybean    ██████                      │                        │
│ 2029   winter wheat ████                      │ [Compare] [Edit]       │
│ 2030   grain sorghum ███                      │ [Export PDF]           │
│ …                                             │                        │
├───────────────────────────────────────────────┴────────────────────────┤
│ Annual production fan (8 years)                                        │
│   190 ┤        ╭─╮                                                     │
│   140 ┤   ╭────╯ ╰──╮        p90                                       │
│    95 ┤───╯         ╰────    p50                                       │
│    48 ┤   ·  ·  ·  ·  ·      p10                                       │
│       └──────────────────────────────                                  │
├────────────────────────────────────────────────────────────────────────┤
│ Nutrients    N  −18 kg/ha   P₂O₅  −7    K₂O  −5                        │
│              Legume N credit +56 kg/ha                                 │
├────────────────────────────────────────────────────────────────────────┤
│ Why:                                                                   │
│ ✓ Cuts July irrigation demand 22% (118 → 92 mm) by replacing corn      │
│ ✓ Adds a legume every 3 seasons, breaking the cereal disease cycle     │
│ ▲ Under S2 (3 dry years) production drops 34% vs 41% today             │
├────────────────────────────────────────────────────────────────────────┤
│ Field work windows this month:  Mar 4–9 · Mar 18–24   [details]        │
└────────────────────────────────────────────────────────────────────────┘
```

**Elementos:** Gantt (color por familia), tarjeta de métricas con deltas, abanico con pestañas S0/S2/S7, balance de nutrientes, hallazgos (máx. 5), acciones (Compare/Edit/Export/Assumptions), tabla de detalle por temporada, y `<WorkabilityStrip />`.

**Edición manual:** arrastrar cultivo → `PUT /rotation` → recálculo en < 3 s. Las violaciones de R1–R11 se muestran como *warnings* amarillos, sin bloquear.

### 13.4 F2 — Disease panel

```
┌────────────────────────────────────────────────────────────────────────┐
│ Disease risk · Corn · 2026 season                                      │
│ (Climate-based estimate. Not a diagnosis.)                             │
├────────────────────────────────────────────────────────────────────────┤
│  Month      J  F  M  A  M  J  J  A  S  O  N  D                         │
│  Gray leaf  ·  ·  ·  ·  ░  ▓  █  █  ▓  ·  ·  ·                         │
│  NCLB       ·  ·  ·  ░  ░  ▓  ▓  ░  ·  ·  ·  ·                         │
│  Tar spot   ·  ·  ·  ·  ·  ░  ▓  ▓  ·  ·  ·  ·                         │
│                                            █ High  ▓ Medium  ░ Low    │
├────────────────────────────────────────────────────────────────────────┤
│ ▲ Gray leaf spot — 63/100 (high)      Window: Jul 10 – Aug 28          │
│   Drivers: 16 days with >14 h leaf wetness · mean T 24 °C · corn residue│
│   [How to reduce risk ▾]                                               │
│     · Rotate to a non-host for at least 2 seasons                      │
│     · Bury or remove residue                                           │
│     · Scout from V8 if rain > 10 mm                                    │
│     · Products: follow the label and consult an agronomist             │
└────────────────────────────────────────────────────────────────────────┘
```

### 13.5 F3 — Irrigation panel

```
┌──────────────────────────────────────────────┬─────────────────────────┐
│ [MAP]  pivot circles + zones                 │ Recommended            │
│   ╭────╮   ╭────╮                            │ ● Center pivot  82/100 │
│   │ P1 │   │ P2 │      ◉ well                │   η = 0.82             │
│   ╰────╯   ╰────╯                            │   Q = 38 L/s (have 40) │
│   [corners zone]                             │   Application 6 mm/h   │
│   [Layers] [Edit water point]                │   vs infiltration 12 ✓ │
│                                              │ Alternatives: SDI 74   │
│                                              │ Furrow 58              │
├──────────────────────────────────────────────┴─────────────────────────┤
│ Month      Mar Apr May Jun Jul Aug Sep Oct                             │
│ ETc (mm)    34  62  98 132 145 120  78  42                             │
│ NIR (mm)    10  38  72 100 118  96  50  12                             │
│ Pump hours   6  18  30  38  42  36  22   8                             │
│ Water used: 148,000 m³ of 180,000 allowed ✓                            │
├────────────────────────────────────────────────────────────────────────┤
│ Materials: 1,240 m lateral · 640 emitters · 2 valves · filter · timer  │
│ ⚠ Indicative design. A technical project is required for construction. │
└────────────────────────────────────────────────────────────────────────┘
```

### 13.6 F4 — Time map (secondary)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer: [NDVI ▾]   Date: ◀──●────────────▶  2023-06   [▶ Play]          │
│        ├─────────────────────────────────────────────┤                │
│        2000-02                          2025-12                        │
├────────────────────────────────────────────────────────────────────────┤
│                 [FULL-WIDTH MAP · parcel highlighted]                  │
│                 legend · scale · attribution                           │
├────────────────────────────────────────────────────────────────────────┤
│ Parcel series:  ▁▂▃▅▆▇▆▅▄▃▂▁   (sparkline, current point marked)      │
└────────────────────────────────────────────────────────────────────────┘
```

- Capas: `NDVI` (P06), `Land surface temp` (P07), `ET` (P08), `OpenET` (P19), `Soil moisture` (P01/P02), `Land cover` (P10), `NAIP` (P21 basemap), `Hillshade` (P12).
- Granularidad **año y mes** `[N]`; teclado accesible (`aria-valuetext="June 2023"`).
- Si no hay observación válida: se muestra el composite anterior + aviso *"No valid observation in June 2023 (cloud cover). Showing May 2023."*
- Modo demo: 24 fechas precomputadas.

### 13.7 F5 — Hazards panel

```
┌────────────────────────────────────────────────────────────────────────┐
│ Risks for your field              Current status (last 30 days)        │
├────────────────────────────────────────────────────────────────────────┤
│ ▲ Drought    P 22%/yr · T 4.5 yr   SPEI-3 −0.4 · 28 ADD · SM 34%      │
│   [View protocol ▾]                                                    │
│ ▲ Heat       P 18%/yr · T 5.6 yr   last 30 d: 6 d > 35 °C             │
│   [View protocol ▾]                                                    │
│ ! Flood      P  6%/yr · T 16 yr    Rx1day 2025: 48 mm                 │
│   [View protocol ▾]                                                    │
│ ! Erosion    4.8 t/ha/yr (tolerance 7)                                │
│   [View protocol ▾]                                                    │
│ · Hail       insufficient data     [Protocol only ▾]                   │
│ · Wildfire   insufficient data     [Protocol only ▾]                   │
└────────────────────────────────────────────────────────────────────────┘
```

Detalle en drawer con pestañas **Before / During / After**; botón de descarga del protocolo; número de emergencias (911) siempre visible.

### 13.8 Onboarding

| Paso | Contenido | Validación en vivo |
|---|---|---|
| 1 | Búsqueda de municipio / pin / **dibujo del polígono** | "Climate cell 38.0/−101.0 · 24 years of data · 80.0 ac" |
| 2 | Cultivos actuales + superficie | Suma de áreas vs área de parcela |
| 3 | Preferidos / excluidos | Chips con viabilidad |
| 4 | Agua, riego, maquinaria, fertilidad | "No flow declared → assuming 30 L/s" |
| 5 | Generate | Progreso por etapas reales |

### 13.9 Responsive y accesibilidad

- Breakpoints 640/768/1024/1280. La demo es de escritorio, pero F2 y el mapa funcionan a 375 px.
- WCAG 2.1 AA: contraste ≥ 4,5:1, foco visible, teclado completo, `aria-label` en iconos, tablas con `<caption>`.
- Todo gráfico tiene alternativa tabular ("View data").
- `prefers-reduced-motion` desactiva el play y las animaciones.
- `<html lang>` dinámico según locale.

---

## 14. Requisitos no funcionales

### 14.1 Rendimiento

| Operación | Objetivo |
|---|---|
| LCP | < 2,5 s |
| `GET /context` (caché) | p95 < 400 ms |
| `PUT /rotation` | p95 < 3 s |
| Generación completa | ≤ 90 s (22 proveedores) |
| Cambio de capa F4 | < 1 s |
| Tiles | < 500 ms |

### 14.2 Fiabilidad

- **Modo demo sin red garantizado** `[D18]`.
- Los 22 proveedores se ejecutan con **degradación parcial**: si falla uno, el resto continúa y el resultado se marca `degraded`.
- Si faltan más de 4 productos críticos (P01, P04, P15, P16, P18), el job falla con `INSUFFICIENT_DATA` y explica cuál falta.
- Reintentos con backoff; timeout por proveedor de 20 s.
- Jobs con timeout global de 240 s.

### 14.3 Seguridad

- Validación Pydantic en todos los endpoints; límite de vértices y área.
- Sin secretos en el frontend; claves en `.env` (nunca en git; `.gitignore` + chequeo en CI).
- CORS restringido; CSP básica; sin `eval`.
- Rate limit por IP y por sesión.
- Sanitización de GeoJSON antes de rasterizar.

### 14.4 Privacidad `[D14]`

- **No hay cuentas.** Sesión anónima de 30 días.
- Coordenadas guardadas con 3 decimales (≈110 m).
- La ubicación no se publica, no se comparte y no se usa para entrenar.
- Borrado de finca = borrado en cascada y purga de artefactos y caché.
- Sin analytics de terceros por defecto. Si se añade, debe ser cookieless y declarado.

### 14.5 Accesibilidad

WCAG 2.1 AA. Ver §13.9.

### 14.6 Observabilidad

- Logs JSON con `request_id`, `product`, `parcel_id`.
- Métricas: latencia por endpoint, tasa de error por proveedor, aciertos de caché, jobs fallidos.
- `meta.duration_ms` y `meta.data_mode` en toda respuesta.

### 14.7 Marcas y descargos `[D19]`

**Obligatorio en el pie de todas las pantallas y en la portada del PDF:**

```html
<footer class="brand-footer">
  <img src="/logos/nasa.svg"  alt="NASA"  height="28" />
  <span>Data provided by NASA</span>
  <img src="/logos/ua.svg"    alt="Universidad de Alicante" height="28" />
  <span>Universidad de Alicante</span>
  <p class="disclaimer">
    ROOTSHIFT is a simulation tool. It is not affiliated with, or endorsed by,
    NASA, USDA or the University of Alicante. Data are used under their respective
    open licenses. Results are not agronomic advice.
  </p>
</footer>
```

- Los logotipos se sirven como SVG locales (nunca hotlink).
- Uso de la marca NASA conforme a las *NASA Media Usage Guidelines*: sin sugerir aval; el descargo es obligatorio, no opcional.
- USDA-NRCS y FAO se acreditan textualmente con enlace.
- Licencia del código: MIT (o la que decida el equipo).

---

## 15. Plan de implementación

### 15.1 Fases

| Fase | Entregable | DoD | Esfuerzo |
|---|---|---|---|
| **F0 · Spike de datos** | Script: polígono → SSURGO + POWER + IMERG → ET0 y serie de lluvia | Gráfico de ET0 vs MOD16 PET con r > 0,7 | 6 h |
| **F1 · Contexto** | `GET /context` con §10.2–10.6 | Test dorado de ET0; SPI/SPEI reproducibles; `et_source` declarado | 12 h |
| **F2 · Rotación + nutrientes** | §10.7, §10.8 + panel F1 | Rotación válida en < 90 s; baseline comparable; ≥ 3 hallazgos; balance N-P-K | 16 h |
| **F3 · Catástrofes** | §10.12 + F5 | 6 peligros calculados + 2 protocolos; ventanas de labor | 8 h |
| **F4 · Enfermedades** | §10.10 + F2 | 12 pares con ventana y acciones; validación agronómica anotada | 8 h |
| **F5 · Riego** | §10.11 + F3 | Sistema + zonas (pivote circular) + calendario + materiales | 8 h |
| **F6 · Mapa temporal** | F4 + 24 fechas demo | 4 capas, deslizador accesible, offline | 8 h |
| **F7 · Pulido y demo** | Logos, i18n, PDF, ensayo | Demo 3 min sin red en 2 máquinas | 8 h |

**Total:** 74 h de trabajo efectivo ≈ 19 h de reloj para 4 personas.

### 15.2 Orden de construcción de los proveedores

No se construyen los 23 a la vez. Orden por dependencia:

1. **P15 POWER** y **P04 IMERG** → sin ellos no hay nada.
2. **P16 SSURGO** → TAW y K.
3. **P01/P02 SMAP** → humedad y ADD.
4. **P18 GAEZ** → `Ym` y futuros (bloquea F1).
5. **P08/P19 ET** → ratio ETa/ETm (bloquea el modelo de rendimiento).
6. **P06/P10 MODIS VI/LC** → VCI, C factor.
7. **P05, P12, P13, P14** → erosión, escorrentía, acuífero.
8. **P03, P09** → carbono (mejora del IRS, no bloquea).
9. **P11, P17, P20, P21, P22** → HLS, STATSGO2, nutrientes, NAIP, CoCoRaHS.
10. **P07** → LST (mejora F2 y F4).

### 15.3 Corte mínimo defendible (MVP)

Si el tiempo aprieta, **no se puede quitar**:

1. Onboarding con polígono y finca demo.
2. `GET /context` con ET, lluvia, suelo y sequía.
3. F1 con rotación propuesta, comparación vs actual y **3 hallazgos explicativos**.
4. F5 con 4 peligros y protocolo.
5. Modo demo sin red con 2 fincas.
6. Logos y descargos.

F2, F3 y F4 son diferenciales. Si se cae F1, no hay producto.

### 15.4 Reparto de trabajo (equipo de 4)

| Rol | Responsabilidad |
|---|---|
| **Data/Geo** | 22 proveedores, estadísticos zonales, SSURGO, TiTiler |
| **Ciencia** | §10 completo + tests dorados + validación con CoCoRaHS/OpenET/NASS |
| **Backend** | FastAPI, jobs, PostGIS, caché, contratos |
| **Frontend** | UI, mapas, gráficos, i18n, logos |
| (5.º) **Storytelling** | Guion, PDF, validación agronómica, ensayo |

### 15.5 Brief para el agente de codificación

```text
Build ROOTSHIFT according to ROOTSHIFT_SPEC_v2.0_FINAL.md. This file is the
single source of truth. Do not add datasets, endpoints or formulas that are not
in it.

Order:
1. F0 data spike: polygon -> SSURGO (2-step SDA) + POWER + IMERG -> ET0 series.
2. Context engine §10.2-10.6 behind GET /context.
3. F1 rotation §10.7 + nutrients §10.8 + IRS §10.9.
4. F5 hazards §10.12 (6 calculable + 2 protocol-only) + workability windows.
5. F2 disease §10.10 (12 pairs, daily leaf-wetness proxy).
6. F3 irrigation §10.11 (center pivot first: Kansas).
7. F4 time map §13.6 (24 demo dates).

Hard rules:
- domain/ = pure functions, no I/O, one unit test each.
- Every number returned must carry Provenance (§10.13.2) and, when applicable,
  a Caveat (§10.13.3).
- Implement the precedence chain of §7.4 exactly. If a source is missing,
  return null + caveat; never impute silently.
- Respect the JSON contracts of §6.1 and §11 byte for byte.
- UI copy is English, taken verbatim from §13. i18n keys required.
- DATA_MODE=demo must work with the network unplugged.
- Do not implement: accounts, prices, chemical doses, image diagnosis,
  wildfire probability, SSP scenarios (GAEZ uses RCP).

Done when: a user draws a Kansas field and in < 90 s gets a rotation different
from their own, with IRS, baseline comparison, >= 3 findings and a nutrient
balance; and the app runs offline.
```

---

## 16. Pruebas y validación

### 16.1 Pirámide

| Nivel | Qué | Herramienta |
|---|---|---|
| Unitario (60 %) | Fórmulas §10 con casos calculados a mano | pytest |
| Propiedades (10 %) | Monotonía, rangos, invarianza | hypothesis |
| Contrato (15 %) | Esquemas §11 | pytest + schemas |
| Integración (10 %) | Proveedores con fixtures grabados | pytest-recording |
| E2E (5 %) | 5 flujos | Playwright |

### 16.2 Tests dorados (bloqueantes)

| ID | Test | Tolerancia |
|---|---|---|
| T1 | ET0 FAO-56 vs ejemplos cap. 4 | ±2 % |
| T2 | Balance: 100 mm sobre suelo seco bajan D en 100 mm | exacto |
| T3 | `Ks=1` si `D≤RAW`; `Ks=0` si `D≥TAW` | exacto |
| T4 | SPEI sintético con sequía inyectada < −1,5 | ±0,1 |
| T5 | `ρ_ET=1` ⇒ `Y_rel=1`; `ρ_ET=0` ⇒ `Y_rel=1−Ky` | exacto |
| T6 | ADD: serie sintética con 30 días bajo p20 ⇒ ADD=30 | exacto |
| T7 | RUSLE R de un aguacero sintético conocido | ±5 % |
| T8 | Gumbel: cuantil 10 años de serie sintética | ±5 % |
| T9 | Rotación generada nunca viola R1–R11 (200 perfiles) | 0 violaciones |
| T10 | IRS ∈ [0,100] siempre | exacto |
| T11 | Balance N-P-K: extracción = Σ(yield·κ) | exacto |
| T12 | Multiplicador GAEZ aplicado una sola vez | exacto |

### 16.3 Validación con datos reales (evidencia para el jurado)

| Validación | Método | Criterio |
|---|---|---|
| Lluvia | IMERG vs CoCoRaHS, 5 estaciones, 2015–2024 | r > 0,7; desviación < 20 % |
| ET | OpenET vs MOD16A2GF en 5 parcelas | r > 0,6; sin sesgo sistemático > 25 % |
| Humedad | SMAP L4 vs GLDAS 0–100 cm normalizados | r > 0,5 |
| Rendimiento | `Y_sim` vs NASS del condado, 10 años | dirección correcta ≥ 70 % de años |
| Erosión | RUSLE vs rango publicado para el condado | dentro del orden de magnitud |
| Rotación | Revisión de un agrónomo | "agronomically plausible" por escrito |

**Estos resultados van al pitch.** Un producto que muestra su validación es mucho más creíble que uno que solo muestra gráficos.

### 16.4 Ensayo de demo

- 3 ensayos cronometrados, uno con wifi apagado, uno en otro portátil, uno con un usuario nuevo.

---

## 17. Riesgos y mitigaciones

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | 22 proveedores ⇒ más puntos de fallo | **Alta** | Alto | Modo `demo`; degradación parcial; fixtures grabados |
| R2 | SSURGO/SDA limita consultas o cae | Media | Alto | Caché permanente por `mukey`; STATSGO2; suelo por defecto declarado |
| R3 | Escala de 0,5°/9 km no representa la parcela y el jurado lo señala | Media | Alto | Declararlo en §7.5 y en la UI; usar OpenET/HLS a 30 m como contraste |
| R4 | GAEZ no entrega series diarias y el escenario 2050s parece trampa | **Alta** | Medio | Multiplicadores declarados + aviso explícito (§10.6.3) |
| R5 | Umbrales de enfermedad incorrectos | Alta | Medio | Validación agronómica; etiqueta "preliminary"; no prescribir |
| R6 | 74 h de plan se comen el tiempo del hackathon | Alta | Alto | Corte MVP §15.3; F1 primero |
| R7 | El IRS parece arbitrario | Media | Medio | Desglose visible + pesos en config + declaración de índice propio |
| R8 | Confusión legal (asesoramiento) | Media | Medio | Descargos + lenguaje de simulación |
| R9 | Credenciales Earthdata/OpenET filtradas | Baja | Alto | `.env` ignorado + chequeo en CI + rotación |
| R10 | "¿Qué es nuevo?" ⇒ "un dashboard" | Media | Alto | Motor de escenarios + explicación + ventanas de labor + balance de nutrientes |
| R11 | Los logotipos se usan mal (sugerir aval) | Media | Alto | Descargo obligatorio + guías de uso NASA en el pie |
| R12 | Dependencia de un solo condado demo | Media | Alto | 3 condados con climas distintos |

---

## 18. Anexos

### Anexo A — Parámetros de cultivo (Kansas)

Esquema en `crops.yaml`; valores `[P]`, **verificar contra FAO-56 (tabla 12) y FAO-33** y citar la fuente en `source`.

| Cultivo | Familia | Temporada | `kc.ini` | `kc.mid` | `kc.end` | GDD base | GDD madurez | `ky` | `zr_max` | `p` | `T_frost` | `T_heat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Corn | Poaceae | S | 0,30 | 1,20 | 0,35 | 10 | 1 500 | 1,25 | 1,7 | 0,55 | 0 | 35 |
| Soybean | Fabaceae | S | 0,40 | 1,15 | 0,50 | 10 | 1 300 | 0,85 | 1,3 | 0,50 | 0 | 35 |
| Winter wheat | Poaceae | W | 0,40 | 1,15 | 0,30 | 0 | 2 100 | 1,15 | 1,5 | 0,55 | −12 | 32 |
| Grain sorghum | Poaceae | S | 0,30 | 1,05 | 0,55 | 10 | 1 500 | 0,90 | 1,7 | 0,55 | 0 | 38 |
| Alfalfa | Fabaceae | perenne | 0,40 | 0,95 | 0,90 | 5 | — | 1,00 | 2,0 | 0,55 | −5 | 35 |
| Oats | Poaceae | S | 0,30 | 1,15 | 0,25 | 5 | 1 200 | 1,00 | 1,5 | 0,50 | −4 | 30 |
| Sunflower | Asteraceae | S | 0,35 | 1,10 | 0,35 | 7 | 1 400 | 1,00 | 1,5 | 0,45 | −2 | 34 |
| Cereal rye (cover) | Poaceae | cover | 0,30 | 1,00 | — | 0 | — | — | 1,2 | 0,55 | −15 | — |

```yaml
- id: corn
  name_en: "Corn"
  name_sci: "Zea mays"
  family: poaceae
  cycle_type: annual
  stand_seasons: 1
  is_legume: false
  kc: { ini: 0.30, mid: 1.20, end: 0.35 }
  stage_days: { ini: 25, dev: 40, mid: 55, late: 30 }
  zr_max_m: 1.7
  p_depletion: 0.55
  gdd_base_c: 10
  gdd_to_maturity: 1500
  ky: 1.25
  t_frost_critical_c: 0
  t_heat_critical_c: 35
  flowering_window_days: 20
  hse_ref: 60
  fse_ref: 20
  sowing_window: [ { doy_from: 105, doy_to: 135 } ]
  source: "FAO-56 Table 12; FAO-33 Table 22 — verify"
```

### Anexo B — Enfermedades (`diseases.yaml`)

```yaml
- id: gray_leaf_spot_corn
  name_en: "Gray leaf spot"
  pathogen: "Cercospora zeae-maydis"
  crops: [corn]
  cardinal_temp: { min: 15, opt_lo: 22, opt_hi: 30, max: 35 }
  wetness_hours_required: 12
  susceptible_stages: [v8, tasseling, silking]
  inoculum_sources: [crop_residue]
  actions:
    cultural: ["Rotate to a non-host for at least 2 seasons", "Bury or remove residue", "Choose a hybrid with better resistance"]
    monitoring: ["Scout from V8 if rainfall > 10 mm"]
    chemical: ["Follow the label and consult an agronomist; no rates are prescribed"]
  severity_weight: 0.8
  confidence: preliminary
  source: "extension literature — pending agronomist review"
```

### Anexo C — Nutrientes (`nutrients.yaml`)

```yaml
- crop_id: corn
  n_removal_kg_per_t: 15.5
  p2o5_removal_kg_per_t: 6.4
  k2o_removal_kg_per_t: 4.4
  n_fixation_kg_per_ha: 0
  source_doi: "TBD — USDA Ag Data Commons dataset"
  confidence: medium
- crop_id: soybean
  n_removal_kg_per_t: 55.0
  p2o5_removal_kg_per_t: 12.0
  k2o_removal_kg_per_t: 25.0
  n_fixation_kg_per_ha: 56.0
  source_doi: "TBD — USDA Ag Data Commons dataset"
  confidence: medium
```

> Los valores de arriba son **ilustrativos del formato**. Deben sustituirse por los del dataset de Ag Data Commons que el equipo seleccione, con su DOI. Sin DOI, la fila no se carga (regla §7.3 P20).

### Anexo D — Símbolos

| Símbolo | Unidad | Significado |
|---|---|---|
| `ET0` | mm/d | ET de referencia |
| `ETa` / `ETm` | mm | ET real / máxima de la temporada |
| `ρ_ET` | — | `ETa/ETm` |
| `Kc`, `Ks`, `Ky` | — | Coef. de cultivo, de estrés, de respuesta al agua |
| `TAW`, `RAW`, `D` | mm | Agua total disponible, fácilmente disponible, agotamiento |
| `NIR`, `Pe` | mm | Necesidad neta de riego, lluvia efectiva |
| `GDD`, `HSE`, `FSE` | °C·d | Grados día, exposición a calor, exposición a helada |
| `ADD` | d | Agricultural drought days |
| `NEE`, `NPP`, `GPP` | gC/m²/año | Carbono |
| `R`, `K`, `LS`, `C`, `P` | — | Factores RUSLE |
| `FI` | 0–100 | Favorabilidad de enfermedad |
| `IRS` | 0–100 | Índice de Resiliencia ROOTSHIFT |

### Anexo E — Siglas

NASA · USDA-NRCS · SSURGO · STATSGO2 · SMAP · SPL4SMGP/L3/CMDL · GPM/IMERG · MODIS · MOD13Q1 · MOD11A2 · MOD16A2GF · MOD17A3HGF · MCD12Q1 · HLS/HLSL30 · NASADEM · GLDAS · CLSM · GAEZ · OpenET · NAIP · CoCoRaHS · CMR · DAAC · LP DAAC · GES DISC · NSIDC · PO.DAAC · RUSLE · FAO-33/56 · RCP · GDD · NEE · NPP · ADD · IRS.

### Anexo F — Referencias

- NASA POWER · Daily API: <https://power.larc.nasa.gov/docs/services/api/temporal/daily/>
- SMAP L4 Soil Moisture (NSIDC): <https://nsidc.org/data/spl4smgp>
- SMAP L3 Enhanced (NSIDC): <https://nsidc.org/data/spl3smp_e>
- SMAP L4 Carbon (NSIDC): <https://nsidc.org/data/spl4cmdl>
- GPM IMERG (GES DISC): <https://disc.gsfc.nasa.gov/datacollection/GPM_3IMERGDF_07.html>
- MOD13Q1 v061 (LP DAAC): <https://doi.org/10.5067/MODIS/MOD13Q1.061>
- MOD11A2 v061: <https://doi.org/10.5067/MODIS/MOD11A2.061>
- MOD16A2GF v061: <https://doi.org/10.5067/MODIS/MOD16A2GF.061>
- MOD17A3HGF v061: <https://doi.org/10.5067/MODIS/MOD17A3HGF.061>
- MCD12Q1 v061: <https://doi.org/10.5067/MODIS/MCD12Q1.061>
- HLS v2.0 (LP DAAC): <https://doi.org/10.5067/HLS/HLSL30.002>
- NASADEM (LP DAAC): <https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001>
- GLDAS Noah 2.1 (GES DISC): <https://disc.gsfc.nasa.gov/datacollection/GLDAS_NOAH025_3H_2.1.html>
- GLDAS CLSM DA 2.2: <https://disc.gsfc.nasa.gov/datacollection/GLDAS_CLSM025_DA1_D_2.2.html>
- FAO GAEZ v4: <https://www.fao.org/gaez/gaezv4/en>
- OpenET: <https://etdata.org>
- SSURGO / Soil Data Access: <https://websoilsurvey.nrcs.usda.gov>
- STATSGO2: <https://datagateway.nrcs.usda.gov>
- USDA Ag Data Commons: <https://agdatacommons.nal.usda.gov>
- NAIP: <https://earthexplorer.usgs.gov>
- CoCoRaHS: <https://www.cocorahs.org>
- FAO-56 (Allen et al., 1998) · FAO-33 (Doorenbos & Kassam, 1979) · Renard et al. (1997) RUSLE · Vicente-Serrano et al. (2010) SPEI · Kogan (1995) VCI.

---

## 19. Decisiones cerradas y confirmaciones pendientes

### 19.1 Qué implica cada decisión cerrada

| ID | Consecuencia operativa |
|---|---|
| **D1 = B** | `parcel.boundary` obligatorio; área calculada en servidor; zonas de riego y F4 dependen del polígono. Si el usuario no dibuja, no hay app. |
| **D2 = B** | Suplemento edáfico = **SSURGO + STATSGO2**. La cadena clima-vegetación es 100 % NASA; el suelo es USDA y se declara. Prohibido SoilGrids. |
| **D3 = B** | FAO-33 con `ρ_ET` observado. `Ky` es el parámetro crítico; sin `Ky` citado, no hay rendimiento. |
| **D4 = C** | DP aditivo + Monte Carlo + búsqueda local. No se implementa MILP. |
| **D5 = B** | Escenarios S6/S7 con GAEZ RCP4.5/RCP8.5 2050s. Multiplicadores, no series diarias. |
| **D6** | 9 cultivos + barbecho (Anexo A) + cobertura (cereal rye). |
| **D7 = B** | Kansas; 3 condados demo; todo parametrizado en `config/regions/us_ks.yaml`. |
| **D8 = B** | `Ym` de GAEZ (regadío/secano); NASS para validar; nunca `Ym` inventado. |
| **D9 = A** | Cero economía: ni precios, ni márgenes, ni coste de materiales. |
| **D10 = B** | Riego con números (Q, zonas, calendario, materiales), sin proyecto. |
| **D11** | 12 pares cultivo-enfermedad, modelo de favorabilidad, validación agronómica. Sin imagen. |
| **D12** | 6 peligros calculables + granizo e incendio solo protocolo. |
| **D13** | Next.js + FastAPI + PostGIS + TiTiler; híbrido precomputado. |
| **D14** | Sin cuentas; sesión anónima 30 días; coordenadas a 3 decimales. |
| **D15 = A** | Explicaciones por plantillas deterministas; sin LLM en runtime. |
| **D16** | `en-US` por defecto, `es-ES` disponible; métrico en cálculo. |
| **D17** | 8 temporadas por defecto, configurable 4–12. |
| **D18** | `DATA_MODE=demo` obligatorio con 3 fincas. |
| **D19** | Logos NASA + UA visibles + descargo de no afiliación. |
| **D20 = C** | `E[P]` + `P_fail` + `T_recovery` como métricas de portada. |

### 19.2 Tres correcciones derivadas de la lista de datasets

Estas no son decisiones nuevas: son consecuencias técnicas de los datos elegidos, y conviene que el equipo las conozca antes de la demo.

**C-1 · GAEZ usa RCP, no SSP.**
La respuesta a D5 pedía "2 SSP". GAEZ v4 proyecta con **RCP (AR5: 2.6 / 4.5 / 6.0 / 8.5)**. Se implementan **RCP4.5 y RCP8.5**, y toda la UI dice "RCP", nunca "SSP". Si el jurado pregunta por SSP, la respuesta es: *"nuestro escenario futuro viene de GAEZ v4, que usa RCP; migrar a SSP requeriría NEX-GDDP-CMIP6, que no está en el catálogo"*.

**C-2 · Sin FIRMS, el incendio deja de ser probabilístico.**
La lista no incluye FIRMS. D12 decía "7 calculables"; con el catálogo real son **6 calculables** (sequía, inundación, helada, calor, viento, erosión) y **2 solo protocolo** (granizo, incendio). No se inventa una probabilidad de incendio.

**C-3 · OpenET ya cubre los 48 estados.**
La nota original decía "solo oeste de EE. UU."; desde diciembre de 2025 OpenET cubre los 48 estados contiguos (30 m en el oeste, ~0,1 ha en el este). Se implementa con cobertura real de la API y respaldo MOD16A2GF donde falte.

### 19.3 Confirmaciones pendientes (3)

Ninguna bloquea el arranque: las tres tienen valor por defecto y viven en configuración.

| ID | Qué confirmar | Default asumido | Dónde se cambia |
|---|---|---|---|
| **CF-1** | Condados exactos de la demo | Finney, Greeley, Republic (KS) | `config/regions/us_ks.yaml` |
| **CF-2** | Versión/horizonte de GAEZ y RCP definitivos | GAEZ v4 · 2050s · RCP4.5 + RCP8.5 | `config/scenarios.yaml` |
| **CF-3** | Lista final de 9 cultivos | Anexo A | `data/catalog/crops.yaml` |

### 19.4 Tabla de validación del equipo

| Decisión | Responsable | Fecha | Conforme |
|---|---|---|---|
| D1–D20 (registro §19.1) | | | ☐ |
| C-1 RCP en vez de SSP | | | ☐ |
| C-2 6 peligros calculables | | | ☐ |
| C-3 Cobertura OpenET | | | ☐ |
| CF-1 condados | | | ☐ |
| CF-2 GAEZ | | | ☐ |
| CF-3 cultivos | | | ☐ |

---

*Fin de la especificación v2.0. Cambiar §7 (datos), §10 (fórmulas) o §11 (contratos) obliga a subir la versión y a revisar los tests dorados.*
